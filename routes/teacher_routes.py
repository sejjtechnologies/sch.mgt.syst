from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models.user import User
from models.school_class import SchoolClass
from models.stream import Stream
from models.teacher_assignment import TeacherAssignment
from models.register_pupil import Pupil, AcademicYear, PupilMarks
from models import db
from datetime import datetime
import pytz

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')


@teacher_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'teacher':
        flash('Access denied')
        return redirect(url_for('index'))

    return render_template('teacher/dashboard.html')


@teacher_bp.route('/view_pupils')
def view_pupils():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'teacher':
        flash('Access denied')
        return redirect(url_for('index'))

    teacher_id = session.get('user_id')

    # Get all classes and streams assigned to this teacher
    teacher_assignments = TeacherAssignment.query.filter_by(
        teacher_id=teacher_id,
        is_active=True
    ).all()

    # If teacher has no assignments, show no assignment page
    if not teacher_assignments:
        # Get teacher info for the template
        from models.user import User
        teacher = User.query.get(teacher_id)
        return render_template('teacher/no_assignment.html', teacher=teacher)

    # Collect all class-stream combinations for this teacher
    teacher_classes_streams = []
    for assignment in teacher_assignments:
        class_obj = SchoolClass.query.get(assignment.class_id)
        stream_obj = Stream.query.get(assignment.stream_id)
        if class_obj and stream_obj:
            teacher_classes_streams.append({
                'class_name': class_obj.name,
                'stream_name': stream_obj.name,
                'class_id': assignment.class_id,
                'stream_id': assignment.stream_id
            })

    # Fetch all pupils in the teacher's assigned classes and streams
    pupils = []
    for assignment in teacher_classes_streams:
        class_pupils = Pupil.query.filter_by(
            class_admitted=assignment['class_id'],
            stream=assignment['stream_id'],
            enrollment_status='active'
        ).all()
        pupils.extend(class_pupils)

    # If no pupils found in assigned classes/streams, show no assignment page
    if not pupils:
        # Get teacher info for the template
        from models.user import User
        teacher = User.query.get(teacher_id)
        return render_template('teacher/no_assignment.html', teacher=teacher)

    # Remove duplicates (in case a pupil appears in multiple assignments)
    seen_ids = set()
    unique_pupils = []
    for pupil in pupils:
        if pupil.id not in seen_ids:
            seen_ids.add(pupil.id)
            unique_pupils.append(pupil)

    # Sort pupils alphabetically by last name, then first name
    sorted_pupils = sorted(unique_pupils, key=lambda p: (p.last_name.lower(), p.first_name.lower()))

    # Create pupil records with class and stream names
    pupil_records = []
    for pupil in sorted_pupils:
        # Find the assignment for this pupil to get the names
        pupil_class_name = None
        pupil_stream_name = None
        for assignment in teacher_classes_streams:
            if assignment['class_id'] == pupil.class_admitted and assignment['stream_id'] == pupil.stream:
                pupil_class_name = assignment['class_name']
                pupil_stream_name = assignment['stream_name']
                break

        pupil_records.append({
            'id': pupil.id,
            'admission_number': pupil.admission_number,
            'first_name': pupil.first_name,
            'last_name': pupil.last_name,
            'gender': pupil.gender,
            'dob': pupil.dob,
            'nationality': pupil.nationality,
            'enrollment_status': pupil.enrollment_status,
            'class_name': pupil_class_name,
            'stream_name': pupil_stream_name,
            'academic_year': pupil.academic_year.name if pupil.academic_year else None
        })

    # Get all academic years for display
    all_academic_years = AcademicYear.query.order_by(AcademicYear.name.desc()).all()
    academic_year_names = [ay.name for ay in all_academic_years]
    current_year = academic_year_names[0] if academic_year_names else None

    return render_template('teacher/view_pupils.html',
                         records=pupil_records,
                         teacher_assignments=teacher_classes_streams,
                         academic_years=academic_year_names,
                         current_year=current_year)


@teacher_bp.route('/manage_marks')
def manage_marks():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'teacher':
        flash('Access denied')
        return redirect(url_for('index'))

    teacher_id = session.get('user_id')

    # Get all classes and streams assigned to this teacher
    teacher_assignments = TeacherAssignment.query.filter_by(
        teacher_id=teacher_id,
        is_active=True
    ).all()

    # If teacher has no assignments, show no assignment page
    if not teacher_assignments:
        # Get teacher info for the template
        from models.user import User
        teacher = User.query.get(teacher_id)
        return render_template('teacher/no_assignment.html', teacher=teacher)

    # Collect all class-stream combinations for this teacher
    teacher_classes_streams = []
    for assignment in teacher_assignments:
        class_obj = SchoolClass.query.get(assignment.class_id)
        stream_obj = Stream.query.get(assignment.stream_id)
        if class_obj and stream_obj:
            teacher_classes_streams.append({
                'class_name': class_obj.name,
                'stream_name': stream_obj.name,
                'class_id': assignment.class_id,
                'stream_id': assignment.stream_id
            })

    # Fetch all pupils in the teacher's assigned classes and streams
    pupils = []
    for assignment in teacher_classes_streams:
        class_pupils = Pupil.query.filter_by(
            class_admitted=assignment['class_id'],
            stream=assignment['stream_id'],
            enrollment_status='active'
        ).all()
        pupils.extend(class_pupils)

    # If no pupils found, show no assignment page
    if not pupils:
        # Get teacher info for the template
        from models.user import User
        teacher = User.query.get(teacher_id)
        return render_template('teacher/no_assignment.html', teacher=teacher)

    # Remove duplicates (in case a pupil appears in multiple assignments)
    seen_ids = set()
    unique_pupils = []
    for pupil in pupils:
        if pupil.id not in seen_ids:
            seen_ids.add(pupil.id)
            unique_pupils.append(pupil)

    # Sort pupils alphabetically by last name, then first name
    sorted_pupils = sorted(unique_pupils, key=lambda p: (p.last_name.lower(), p.first_name.lower()))

    # Create pupil records with class and stream names
    pupil_records = []
    for pupil in sorted_pupils:
        # Find the assignment for this pupil to get the names
        pupil_class_name = None
        pupil_stream_name = None
        for assignment in teacher_classes_streams:
            if assignment['class_id'] == pupil.class_admitted and assignment['stream_id'] == pupil.stream:
                pupil_class_name = assignment['class_name']
                pupil_stream_name = assignment['stream_name']
                break

        pupil_records.append({
            'id': pupil.id,
            'admission_number': pupil.admission_number,
            'first_name': pupil.first_name,
            'last_name': pupil.last_name,
            'class_name': pupil_class_name,
            'stream_name': pupil_stream_name
        })

    # Get academic years for dropdown
    academic_years = AcademicYear.query.order_by(AcademicYear.name.desc()).all()

    # Default selections
    current_academic_year = academic_years[0] if academic_years else None
    default_term = 1
    default_exam_type = 'Beginning of term'

    return render_template('teacher/manage_marks.html',
                         records=pupil_records,
                         teacher_assignments=teacher_classes_streams,
                         academic_years=academic_years,
                         current_academic_year=current_academic_year,
                         default_term=default_term,
                         default_exam_type=default_exam_type)


@teacher_bp.route('/save_marks', methods=['POST'])
def save_marks():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'teacher':
        return jsonify({'success': False, 'message': 'Access denied'})

    try:
        data = request.get_json()
        pupil_id = data.get('pupil_id')
        academic_year_id = int(data.get('academic_year_id'))  # Convert to int
        term = int(data.get('term'))  # Convert to int
        exam_type = data.get('exam_type')
        marks = data.get('marks', {})

        # Validate required fields
        if not all([pupil_id, academic_year_id, term, exam_type]):
            return jsonify({'success': False, 'message': 'Missing required fields'})

        # Validate marks are within valid range (0-100)
        for subject, mark in marks.items():
            if mark is not None and (mark < 0 or mark > 100):
                return jsonify({'success': False, 'message': f'Invalid mark for {subject}: {mark}. Marks must be between 0 and 100.'})

        # Get or create marks record
        marks_record = PupilMarks.query.filter_by(
            pupil_id=pupil_id,
            academic_year_id=academic_year_id,
            term=term,
            exam_type=exam_type
        ).first()

        if not marks_record:
            marks_record = PupilMarks(
                pupil_id=pupil_id,
                academic_year_id=academic_year_id,
                term=term,
                exam_type=exam_type
            )
            db.session.add(marks_record)

        # Update marks
        marks_record.english = marks.get('english')
        marks_record.mathematics = marks.get('mathematics')
        marks_record.science = marks.get('science')
        marks_record.social_studies = marks.get('social_studies')

        # Calculate totals and remarks
        marks_record.calculate_totals()
        marks_record.generate_remarks()

        # Calculate positions
        _calculate_positions(marks_record)

        db.session.commit()

        return jsonify({
            'success': True,
            'total_marks': marks_record.total_marks,
            'average': marks_record.average,
            'position_in_stream': marks_record.position_in_stream,
            'position_in_class': marks_record.position_in_class,
            'stream_student_count': marks_record.stream_student_count,
            'class_student_count': marks_record.class_student_count
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


def _calculate_positions(marks_record):
    """Calculate position in stream and class for the marks record"""
    if not marks_record.total_marks:
        return

    # Get all marks for the same academic year, term, and exam type
    all_marks = PupilMarks.query.filter_by(
        academic_year_id=marks_record.academic_year_id,
        term=marks_record.term,
        exam_type=marks_record.exam_type
    ).filter(PupilMarks.total_marks.isnot(None)).all()

    # Group by stream and class
    stream_marks = []
    class_marks = []

    pupil = Pupil.query.get(marks_record.pupil_id)
    if pupil:
        # Stream marks (same class and stream)
        stream_marks = [m for m in all_marks if m.pupil and
                       m.pupil.class_admitted == pupil.class_admitted and
                       m.pupil.stream == pupil.stream]

        # Class marks (same class, all streams)
        class_marks = [m for m in all_marks if m.pupil and
                      m.pupil.class_admitted == pupil.class_admitted]

        # Sort by total marks descending (handle None values)
        def sort_key(marks):
            return (marks.total_marks is not None, marks.total_marks or 0)

        stream_marks.sort(key=sort_key, reverse=True)
        class_marks.sort(key=sort_key, reverse=True)

        # Update positions for ALL students in the stream
        for i, m in enumerate(stream_marks, 1):
            m.position_in_stream = i
            m.stream_student_count = len(stream_marks)

        # Update positions for ALL students in the class
        for i, m in enumerate(class_marks, 1):
            m.position_in_class = i
            m.class_student_count = len(class_marks)

        # Commit all position updates
        db.session.commit()


@teacher_bp.route('/get_marks', methods=['GET'])
def get_marks():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'teacher':
        return jsonify({'success': False, 'message': 'Access denied'})

    try:
        pupil_id = request.args.get('pupil_id')
        academic_year_id = int(request.args.get('academic_year_id'))  # Convert to int
        term = int(request.args.get('term'))  # Convert to int
        exam_type = request.args.get('exam_type')

        if not all([pupil_id, academic_year_id, term, exam_type]):
            return jsonify({'success': False, 'message': 'Missing required fields'})

        marks_record = PupilMarks.query.filter_by(
            pupil_id=pupil_id,
            academic_year_id=academic_year_id,
            term=term,
            exam_type=exam_type
        ).first()

        if marks_record:
            return jsonify({
                'success': True,
                'marks': {
                    'english': marks_record.english,
                    'mathematics': marks_record.mathematics,
                    'science': marks_record.science,
                    'social_studies': marks_record.social_studies
                },
                'total_marks': marks_record.total_marks,
                'average': marks_record.average,
                'position_in_stream': marks_record.position_in_stream,
                'position_in_class': marks_record.position_in_class,
                'stream_student_count': marks_record.stream_student_count,
                'class_student_count': marks_record.class_student_count
            })
        else:
            return jsonify({'success': True, 'marks': None})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@teacher_bp.route('/recalculate_positions', methods=['POST'])
def recalculate_positions():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'teacher':
        return jsonify({'success': False, 'message': 'Access denied'})

    try:
        data = request.get_json()
        academic_year_id = data.get('academic_year_id')
        term = data.get('term')
        exam_type = data.get('exam_type')

        if not all([academic_year_id, term, exam_type]):
            return jsonify({'success': False, 'message': 'Missing required fields'})

        # Get all marks for this academic year, term, and exam type
        all_marks = PupilMarks.query.filter_by(
            academic_year_id=academic_year_id,
            term=int(term),
            exam_type=exam_type
        ).filter(PupilMarks.total_marks.isnot(None)).all()

        if not all_marks:
            return jsonify({'success': False, 'message': 'No marks found to recalculate'})

        # Group by class and stream, then recalculate positions
        updated_count = 0

        # Get unique classes
        classes = set()
        for mark in all_marks:
            if mark.pupil:
                classes.add(mark.pupil.class_admitted)

        for class_id in classes:
            # Get all marks for this class
            class_marks = [m for m in all_marks if m.pupil and m.pupil.class_admitted == class_id]

            # Sort by total marks descending
            def sort_key(marks):
                return (marks.total_marks is not None, marks.total_marks or 0)

            class_marks.sort(key=sort_key, reverse=True)

            # Update class positions
            for i, m in enumerate(class_marks, 1):
                m.position_in_class = i
                m.class_student_count = len(class_marks)
                updated_count += 1

            # Group by stream within this class
            streams = set()
            for mark in class_marks:
                if mark.pupil:
                    streams.add(mark.pupil.stream)

            for stream_id in streams:
                # Get marks for this stream
                stream_marks = [m for m in class_marks if m.pupil and m.pupil.stream == stream_id]
                stream_marks.sort(key=sort_key, reverse=True)

                # Update stream positions
                for i, m in enumerate(stream_marks, 1):
                    m.position_in_stream = i
                    m.stream_student_count = len(stream_marks)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Positions recalculated for {updated_count} marks records'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@teacher_bp.route('/pupil_reports')
def pupil_reports():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'teacher':
        flash('Access denied')
        return redirect(url_for('index'))

    teacher_id = session.get('user_id')

    # Get all classes and streams assigned to this teacher
    teacher_assignments = TeacherAssignment.query.filter_by(
        teacher_id=teacher_id,
        is_active=True
    ).all()

    # If teacher has no assignments, show no assignment page
    if not teacher_assignments:
        from models.user import User
        teacher = User.query.get(teacher_id)
        return render_template('teacher/no_assignment.html', teacher=teacher)

    # Get academic years for filter dropdown
    academic_years = AcademicYear.query.order_by(AcademicYear.start_year.desc()).all()

    return render_template('teacher/pupil_reports.html',
                         teacher_assignments=teacher_assignments,
                         academic_years=academic_years)


@teacher_bp.route('/get_pupils_for_reports', methods=['GET'])
def get_pupils_for_reports():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'teacher':
        return jsonify({'success': False, 'message': 'Access denied'})

    teacher_id = session.get('user_id')
    year_id = request.args.get('year')
    term = request.args.get('term')
    exam_set = request.args.get('exam_set')

    if not all([year_id, term, exam_set]):
        return jsonify({'success': False, 'message': 'Missing required parameters'})

    try:
        # Get all classes and streams assigned to this teacher
        teacher_assignments = TeacherAssignment.query.filter_by(
            teacher_id=teacher_id,
            is_active=True
        ).all()

        if not teacher_assignments:
            return jsonify({'success': False, 'message': 'No class assignments found'})

        # Collect all pupils from assigned classes/streams
        pupils_data = []

        for assignment in teacher_assignments:
            # Get pupils in this class and stream
            pupils = Pupil.query.filter_by(
                class_admitted=str(assignment.class_id),
                stream=str(assignment.stream_id),
                enrollment_status='active'
            ).order_by(Pupil.first_name, Pupil.last_name).all()

            for pupil in pupils:
                # Get class and stream names
                class_obj = SchoolClass.query.get(assignment.class_id)
                stream_obj = Stream.query.get(assignment.stream_id)

                pupils_data.append({
                    'id': pupil.id,
                    'admission_number': pupil.admission_number,
                    'first_name': pupil.first_name,
                    'last_name': pupil.last_name,
                    'class_name': class_obj.name if class_obj else 'Unknown',
                    'stream_name': stream_obj.name if stream_obj else 'Unknown'
                })

        return jsonify({
            'success': True,
            'pupils': pupils_data,
            'total': len(pupils_data)
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@teacher_bp.route('/generate_pupil_report/<pupil_id>/<report_type>')
def generate_pupil_report(pupil_id, report_type):
    if 'user_id' not in session or session.get('user_role', '').lower() != 'teacher':
        flash('Access denied')
        return redirect(url_for('index'))

    # Get pupil details
    pupil = Pupil.query.get(pupil_id)
    if not pupil:
        flash('Pupil not found')
        return redirect(url_for('teacher.pupil_reports'))

    # Get class and stream names
    class_name = 'N/A'
    stream_name = 'N/A'

    if pupil.class_admitted:
        class_obj = SchoolClass.query.get(pupil.class_admitted)
        if class_obj:
            class_name = class_obj.name

    if pupil.stream:
        stream_obj = Stream.query.get(pupil.stream)
        if stream_obj:
            stream_name = stream_obj.name

    # Get pupil's marks based on report type
    marks_data = []

    # Parse report type to determine term and exam type
    if report_type.startswith('term1_'):
        term = 1
        if 'beginning' in report_type:
            exam_type = 'Beginning of term'
        elif 'mid' in report_type:
            exam_type = 'Mid_term'
        elif 'end' in report_type:
            exam_type = 'End of term'
        elif 'both' in report_type:
            # For "both" option, we'll show all three exams: beginning, mid, and end of term
            exam_type = 'Beginning of term'  # We'll handle this specially
    elif report_type.startswith('term2_'):
        term = 2
        if 'beginning' in report_type:
            exam_type = 'Beginning of term'
        elif 'mid' in report_type:
            exam_type = 'Mid_term'
        elif 'end' in report_type:
            exam_type = 'End of term'
        elif 'both' in report_type:
            exam_type = 'Beginning of term'
    elif report_type.startswith('term3_'):
        term = 3
        if 'beginning' in report_type:
            exam_type = 'Beginning of term'
        elif 'mid' in report_type:
            exam_type = 'Mid_term'
        elif 'end' in report_type:
            exam_type = 'End of term'
        elif 'both' in report_type:
            exam_type = 'Beginning of term'

    # Fetch marks data
    if 'term' in locals():
        if 'both' in report_type:
            # For "both" option, get all three exam types: beginning, mid, and end of term
            beginning_marks = PupilMarks.query.filter_by(
                pupil_id=pupil_id,
                academic_year_id=pupil.academic_year_id,
                term=term,
                exam_type='Beginning of term'
            ).first()

            mid_marks = PupilMarks.query.filter_by(
                pupil_id=pupil_id,
                academic_year_id=pupil.academic_year_id,
                term=term,
                exam_type='Mid_term'
            ).first()

            end_marks = PupilMarks.query.filter_by(
                pupil_id=pupil_id,
                academic_year_id=pupil.academic_year_id,
                term=term,
                exam_type='End of term'
            ).first()

            print(f"DEBUG: 'Both' option - Looking for pupil_id={pupil_id}, academic_year_id={pupil.academic_year_id}, term={term}")
            print(f"DEBUG: Beginning marks found: {beginning_marks is not None}")
            print(f"DEBUG: Mid marks found: {mid_marks is not None}")
            print(f"DEBUG: End marks found: {end_marks is not None}")

            if beginning_marks:
                print(f"DEBUG: Beginning marks remarks - english: '{beginning_marks.english_remark}', general: '{beginning_marks.general_comment}'")

            if beginning_marks:
                marks_data.append({
                    'exam_type': 'Beginning of Term',
                    'english': beginning_marks.english or 0,
                    'mathematics': beginning_marks.mathematics or 0,
                    'science': beginning_marks.science or 0,
                    'social_studies': beginning_marks.social_studies or 0,
                    'total': beginning_marks.total_marks or 0,
                    'average': beginning_marks.average or 0,
                    'position': beginning_marks.position_in_stream or 0,
                    'stream_student_count': beginning_marks.stream_student_count or 0,
                    'english_remark': beginning_marks.english_remark or '',
                    'mathematics_remark': beginning_marks.mathematics_remark or '',
                    'science_remark': beginning_marks.science_remark or '',
                    'social_studies_remark': beginning_marks.social_studies_remark or '',
                    'remarks': beginning_marks.general_comment or ''
                })

            if mid_marks:
                marks_data.append({
                    'exam_type': 'Mid Term',
                    'english': mid_marks.english or 0,
                    'mathematics': mid_marks.mathematics or 0,
                    'science': mid_marks.science or 0,
                    'social_studies': mid_marks.social_studies or 0,
                    'total': mid_marks.total_marks or 0,
                    'average': mid_marks.average or 0,
                    'position': mid_marks.position_in_stream or 0,
                    'stream_student_count': mid_marks.stream_student_count or 0,
                    'english_remark': mid_marks.english_remark or '',
                    'mathematics_remark': mid_marks.mathematics_remark or '',
                    'science_remark': mid_marks.science_remark or '',
                    'social_studies_remark': mid_marks.social_studies_remark or '',
                    'remarks': mid_marks.general_comment or ''
                })

            if end_marks:
                marks_data.append({
                    'exam_type': 'End of Term',
                    'english': end_marks.english or 0,
                    'mathematics': end_marks.mathematics or 0,
                    'science': end_marks.science or 0,
                    'social_studies': end_marks.social_studies or 0,
                    'total': end_marks.total_marks or 0,
                    'average': end_marks.average or 0,
                    'position': end_marks.position_in_stream or 0,
                    'stream_student_count': end_marks.stream_student_count or 0,
                    'english_remark': end_marks.english_remark or '',
                    'mathematics_remark': end_marks.mathematics_remark or '',
                    'science_remark': end_marks.science_remark or '',
                    'social_studies_remark': end_marks.social_studies_remark or '',
                    'remarks': end_marks.general_comment or ''
                })
                marks_data.append({
                    'exam_type': 'Beginning of Term',
                    'english': beginning_marks.english or 0,
                    'mathematics': beginning_marks.mathematics or 0,
                    'science': beginning_marks.science or 0,
                    'social_studies': beginning_marks.social_studies or 0,
                    'total': beginning_marks.total_marks or 0,
                    'average': beginning_marks.average or 0,
                    'position': beginning_marks.position_in_stream or 0,
                    'stream_student_count': beginning_marks.stream_student_count or 0,
                    'english_remark': beginning_marks.english_remark or '',
                    'mathematics_remark': beginning_marks.mathematics_remark or '',
                    'science_remark': beginning_marks.science_remark or '',
                    'social_studies_remark': beginning_marks.social_studies_remark or '',
                    'remarks': beginning_marks.general_comment or ''
                })

            if mid_marks:
                marks_data.append({
                    'exam_type': 'Mid Term',
                    'english': mid_marks.english or 0,
                    'mathematics': mid_marks.mathematics or 0,
                    'science': mid_marks.science or 0,
                    'social_studies': mid_marks.social_studies or 0,
                    'total': mid_marks.total_marks or 0,
                    'average': mid_marks.average or 0,
                    'position': mid_marks.position_in_stream or 0,
                    'stream_student_count': mid_marks.stream_student_count or 0,
                    'english_remark': mid_marks.english_remark or '',
                    'mathematics_remark': mid_marks.mathematics_remark or '',
                    'science_remark': mid_marks.science_remark or '',
                    'social_studies_remark': mid_marks.social_studies_remark or '',
                    'remarks': mid_marks.general_comment or ''
                })
        else:
            # Single exam type
            marks = PupilMarks.query.filter_by(
                pupil_id=pupil_id,
                academic_year_id=pupil.academic_year_id,
                term=term,
                exam_type=exam_type
            ).first()

            print(f"DEBUG: Single exam - Looking for pupil_id={pupil_id}, academic_year_id={pupil.academic_year_id}, term={term}, exam_type='{exam_type}'")
            print(f"DEBUG: Marks found: {marks is not None}")

            if marks:
                print(f"DEBUG: Single marks remarks - english: '{marks.english_remark}', math: '{marks.mathematics_remark}', science: '{marks.science_remark}', social: '{marks.social_studies_remark}', general: '{marks.general_comment}'")

            if marks:
                marks_data.append({
                    'exam_type': exam_type,
                    'english': marks.english or 0,
                    'mathematics': marks.mathematics or 0,
                    'science': marks.science or 0,
                    'social_studies': marks.social_studies or 0,
                    'total': marks.total_marks or 0,
                    'average': marks.average or 0,
                    'position': marks.position_in_stream or 0,
                    'stream_student_count': marks.stream_student_count or 0,
                    'english_remark': marks.english_remark or '',
                    'mathematics_remark': marks.mathematics_remark or '',
                    'science_remark': marks.science_remark or '',
                    'social_studies_remark': marks.social_studies_remark or '',
                    'remarks': marks.general_comment or ''
                })

    # For now, just return a simple HTML report
    return render_template('teacher/pupil_report_template.html',
                         pupil=pupil,
                         report_type=report_type,
                         marks_data=marks_data,
                         datetime=datetime,
                         class_name=class_name,
                         stream_name=stream_name)