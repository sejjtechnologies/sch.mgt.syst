from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models.user import User
from models.school_class import SchoolClass
from models.stream import Stream
from models.teacher_assignment import TeacherAssignment
from models import db
from datetime import datetime
import pytz
import re
from collections import defaultdict
from utils.settings import SystemSettings

headteacher_bp = Blueprint('headteacher', __name__, url_prefix='/headteacher')


@headteacher_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'headteacher':
        flash('Access denied')
        return redirect(url_for('index'))

    return render_template('headteacher/dashboard.html')


@headteacher_bp.route('/assign_classes_streams')
def assign_classes_streams():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'headteacher':
        flash('Access denied')
        return redirect(url_for('index'))

    # Fetch all teachers (users with role 'teacher')
    teachers = User.query.filter_by(role='teacher', is_active=True).all()

    # Fetch all classes
    classes = SchoolClass.query.all()

    # Fetch all streams
    streams = Stream.query.all()

    # Fetch existing assignments
    assignments = TeacherAssignment.query.filter_by(is_active=True).all()

    # Create a dictionary of existing assignments for easy lookup
    existing_assignments = {}
    for assignment in assignments:
        key = f"{assignment.class_id}_{assignment.stream_id}"
        existing_assignments[key] = assignment.teacher_id

    return render_template(
        'headteacher/assign_classes_&_streams.html',
        teachers=teachers,
        classes=classes,
        streams=streams,
        existing_assignments=existing_assignments
    )


@headteacher_bp.route('/save_assignments', methods=['POST'])
def save_assignments():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'headteacher':
        return jsonify({'success': False, 'message': 'Access denied'})

    try:
        assignments_data = request.get_json()

        seen_class_stream = set()
        seen_teacher = set()

        for assignment in assignments_data:
            teacher_id = assignment.get('teacher_id')
            class_id = assignment.get('class_id')
            stream_id = assignment.get('stream_id')

            if not all([teacher_id, class_id, stream_id]):
                return jsonify({'success': False, 'message': 'Missing assignment data'})

            class_stream_key = f"{class_id}_{stream_id}"
            if class_stream_key in seen_class_stream:
                return jsonify({
                    'success': False,
                    'message': 'Duplicate assignment: Same class and stream cannot have multiple teachers'
                })

            if teacher_id in seen_teacher:
                return jsonify({
                    'success': False,
                    'message': 'Duplicate assignment: Same teacher cannot be assigned to multiple classes/streams'
                })

            seen_class_stream.add(class_stream_key)
            seen_teacher.add(teacher_id)

        db.session.begin()

        TeacherAssignment.query.update({'is_active': False})
        print(f"DEBUG: Deactivated all existing assignments")

        for assignment in assignments_data:
            print(f"DEBUG: Creating assignment - teacher_id: {assignment.get('teacher_id')}, class_id: {assignment.get('class_id')}, stream_id: {assignment.get('stream_id')}")
            new_assignment = TeacherAssignment(
                teacher_id=assignment.get('teacher_id'),
                class_id=assignment.get('class_id'),
                stream_id=assignment.get('stream_id'),
                assigned_date=datetime.utcnow(),
                is_active=True
            )
            db.session.add(new_assignment)

        db.session.commit()
        print(f"DEBUG: Successfully saved {len(assignments_data)} assignments")

        return jsonify({'success': True, 'message': 'Assignments saved successfully'})

    except Exception as e:
        db.session.rollback()
        print(f"Error saving assignments: {e}")
        return jsonify({'success': False, 'message': f'Error saving assignments: {str(e)}'})


@headteacher_bp.route('/view_assignments')
def view_assignments():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'headteacher':
        flash('Access denied')
        return redirect(url_for('index'))

    assignments = TeacherAssignment.query.filter_by(is_active=True)\
        .join(User, TeacherAssignment.teacher_id == User.id)\
        .join(SchoolClass, TeacherAssignment.class_id == SchoolClass.id)\
        .join(Stream, TeacherAssignment.stream_id == Stream.id)\
        .add_columns(
            User.first_name,
            User.last_name,
            User.email,
            SchoolClass.name.label('class_name'),
            Stream.name.label('stream_name'),
            TeacherAssignment.assigned_date,
            TeacherAssignment.created_at
        ).all()

    system_tz = pytz.timezone(SystemSettings.get_timezone())
    formatted_assignments = []

    for assignment in assignments:
        date_to_format = assignment.assigned_date or assignment.created_at

        if date_to_format:
            if date_to_format.tzinfo is None:
                date_to_format = pytz.utc.localize(date_to_format)
            system_time = date_to_format.astimezone(system_tz)
            formatted_date = system_time.strftime('%b %d, %Y %I:%M %p')
        else:
            formatted_date = 'N/A'

        formatted_assignments.append({
            'teacher_name': f"{assignment.first_name} {assignment.last_name}",
            'teacher_email': assignment.email,
            'class_name': assignment.class_name,
            'stream_name': assignment.stream_name,
            'assigned_date': formatted_date
        })

    grouped_assignments = defaultdict(list)
    for assignment in formatted_assignments:
        grouped_assignments[assignment['class_name']].append(assignment)

    def class_sort_key(class_name):
        """
        Extract numeric value from class name.
        P1 -> 1, P2 -> 2 ... fallback to large number if not found
        """
        match = re.search(r'\d+', class_name)
        return int(match.group()) if match else 999

    organized_assignments = []

    for class_name in sorted(grouped_assignments.keys(), key=class_sort_key):
        streams_sorted = sorted(
            grouped_assignments[class_name],
            key=lambda x: x['stream_name']
        )
        organized_assignments.extend(streams_sorted)

    return render_template(
        'headteacher/view_assignments.html',
        assignments=organized_assignments
    )
