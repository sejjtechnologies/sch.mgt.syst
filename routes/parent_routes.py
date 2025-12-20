from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from models import db
from models.register_pupil import Pupil, AcademicYear, PupilMarks
from models.bursar import Payment, StudentFee, FeeStructure
from models.attendance import Attendance
from models.user import User
from models.school_class import SchoolClass
from models.stream import Stream
from datetime import datetime, timedelta
import calendar

parent_bp = Blueprint('parent', __name__, url_prefix='/parent')

@parent_bp.route('/dashboard')
def dashboard():
    """Parent dashboard - search and view pupil information"""
    if 'user_id' not in session or session.get('user_role', '').lower() != 'parent':
        flash('Access denied')
        return redirect(url_for('index'))

    return render_template('parent/dashboard.html')

@parent_bp.route('/api/search_pupils')
def search_pupils():
    """Search pupils by first name, last name, admission number, or roll number"""
    if 'user_id' not in session or session.get('user_role', '').lower() != 'parent':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'success': True, 'pupils': []})

    # Search pupils by various fields
    pupils = Pupil.query.filter(
        db.or_(
            Pupil.first_name.ilike(f'%{query}%'),
            Pupil.last_name.ilike(f'%{query}%'),
            Pupil.admission_number.ilike(f'%{query}%'),
            Pupil.roll_number.ilike(f'%{query}%')
        )
    ).limit(10).all()

    results = []
    for pupil in pupils:
        # Get class and stream names
        class_name = None
        stream_name = None

        if pupil.class_admitted:
            class_obj = db.session.get(SchoolClass, pupil.class_admitted)
            class_name = class_obj.name if class_obj else pupil.class_admitted

        if pupil.stream:
            stream_obj = db.session.get(Stream, pupil.stream)
            stream_name = stream_obj.name if stream_obj else pupil.stream

        results.append({
            'id': pupil.id,
            'first_name': pupil.first_name,
            'last_name': pupil.last_name,
            'admission_number': pupil.admission_number,
            'roll_number': pupil.roll_number,
            'class_admitted': class_name,
            'stream': stream_name,
            'full_name': f"{pupil.first_name} {pupil.last_name}"
        })

    return jsonify({'success': True, 'pupils': results})

@parent_bp.route('/api/pupil/<pupil_id>')
def get_pupil_details(pupil_id):
    """Get detailed information for a specific pupil"""
    if 'user_id' not in session or session.get('user_role', '').lower() != 'parent':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    pupil = Pupil.query.get(pupil_id)
    if not pupil:
        return jsonify({'success': False, 'message': 'Pupil not found'}), 404

    # Get fees balance
    fees_balance = get_pupil_fees_balance(pupil_id)

    # Get recent payments
    recent_payments = Payment.query.filter_by(pupil_id=pupil_id).order_by(Payment.payment_date.desc()).limit(5).all()
    payments_data = []
    for payment in recent_payments:
        payments_data.append({
            'amount': payment.amount,
            'payment_date': payment.payment_date.strftime('%Y-%m-%d'),
            'receipt_number': payment.receipt_number,
            'payment_method': payment.payment_method,
            'term': payment.term
        })

    # Get attendance summary
    attendance_summary = get_pupil_attendance_summary(pupil_id)

    # Get pupil reports (marks)
    pupil_reports = get_pupil_reports(pupil_id)

    # Get class and stream names
    class_name = None
    stream_name = None

    if pupil.class_admitted:
        class_obj = db.session.get(SchoolClass, pupil.class_admitted)
        class_name = class_obj.name if class_obj else pupil.class_admitted

    if pupil.stream:
        stream_obj = db.session.get(Stream, pupil.stream)
        stream_name = stream_obj.name if stream_obj else pupil.stream

    pupil_data = {
        'id': pupil.id,
        'first_name': pupil.first_name,
        'last_name': pupil.last_name,
        'admission_number': pupil.admission_number,
        'roll_number': pupil.roll_number,
        'class_admitted': class_name,
        'stream': stream_name,
        'academic_year': pupil.academic_year.name if pupil.academic_year else None,
        'fees_balance': fees_balance,
        'recent_payments': payments_data,
        'attendance_summary': attendance_summary,
        'reports': pupil_reports
    }

    return jsonify({'success': True, 'pupil': pupil_data})

def get_pupil_fees_balance(pupil_id):
    """Calculate total fees balance for a pupil
    
    Balance = Total fees owed - Total payments made
    
    If pupil has assigned StudentFee records, calculate from those.
    Otherwise, calculate from class fee structures.
    """
    try:
        # Get total payments made by pupil
        total_paid = db.session.query(db.func.sum(Payment.amount)).filter_by(pupil_id=pupil_id).scalar() or 0.0

        # Get the pupil
        pupil = Pupil.query.get(pupil_id)
        if not pupil:
            return 0.0

        # Check if pupil has assigned student fees
        student_fees = StudentFee.query.filter_by(pupil_id=pupil_id, is_active=True).all()

        total_owed = 0.0

        if student_fees:
            # Calculate from assigned student fees
            for student_fee in student_fees:
                fee_structure = student_fee.fee_structure

                # Calculate amount owed for each assigned term
                if student_fee.term1_assigned:
                    term1_amount = fee_structure.term1_amount - student_fee.term1_exemption
                    total_owed += max(0, term1_amount)

                if student_fee.term2_assigned:
                    term2_amount = fee_structure.term2_amount - student_fee.term2_exemption
                    total_owed += max(0, term2_amount)

                if student_fee.term3_assigned:
                    term3_amount = fee_structure.term3_amount - student_fee.term3_exemption
                    total_owed += max(0, term3_amount)
        else:
            # No assigned student fees, calculate from class fee structures
            # Get current academic year (assuming the latest active one)
            current_academic_year = AcademicYear.query.filter_by(is_active=True).order_by(AcademicYear.id.desc()).first()

            if current_academic_year and pupil.class_admitted:
                # Get all fee structures for this class/academic year (ignore stream initially)
                fee_structures = FeeStructure.query.filter_by(
                    academic_year_id=current_academic_year.id,
                    class_id=pupil.class_admitted,
                    is_active=True
                ).all()

                # Group by stream to find the most appropriate fee structure
                stream_specific = [fs for fs in fee_structures if fs.stream_id == pupil.stream]
                if stream_specific:
                    # Use stream-specific fees
                    fee_structures = stream_specific
                else:
                    # Use class-wide fees (find one stream's fees as representative)
                    if fee_structures:
                        # Use fees from the first stream found for this class
                        first_stream = fee_structures[0].stream_id
                        fee_structures = [fs for fs in fee_structures if fs.stream_id == first_stream]

                # Sum up all term amounts (assuming all terms are applicable)
                for fee_structure in fee_structures:
                    total_owed += fee_structure.term1_amount
                    total_owed += fee_structure.term2_amount
                    total_owed += fee_structure.term3_amount

        # Balance = Amount owed - Amount paid
        balance = total_owed - total_paid

        return round(max(0, balance), 2)  # Don't show negative balances

    except Exception as e:
        print(f"Error calculating fees balance: {e}")
        return 0.0

def get_pupil_attendance_summary(pupil_id):
    """Get attendance summary for different periods"""
    try:
        today = datetime.now().date()

        # Daily attendance (last 7 days)
        week_ago = today - timedelta(days=7)
        daily_attendance = Attendance.query.filter(
            Attendance.pupil_id == pupil_id,
            Attendance.attendance_date >= week_ago,
            Attendance.attendance_date <= today
        ).order_by(Attendance.attendance_date.desc()).all()

        # Weekly attendance (current month)
        month_start = today.replace(day=1)
        weekly_attendance = Attendance.query.filter(
            Attendance.pupil_id == pupil_id,
            Attendance.attendance_date >= month_start,
            Attendance.attendance_date <= today
        ).all()

        # Termly attendance (current academic year - approximate 3 months)
        term_start = today - timedelta(days=90)
        termly_attendance = Attendance.query.filter(
            Attendance.pupil_id == pupil_id,
            Attendance.attendance_date >= term_start,
            Attendance.attendance_date <= today
        ).all()

        def calculate_stats(attendance_records):
            if not attendance_records:
                return {'present': 0, 'absent': 0, 'total': 0, 'percentage': 0}
            present = sum(1 for a in attendance_records if a.status == 'present')
            absent = sum(1 for a in attendance_records if a.status == 'absent')
            total = present + absent
            percentage = round((present / total * 100), 1) if total > 0 else 0
            return {
                'present': present,
                'absent': absent,
                'total': total,
                'percentage': percentage
            }

        return {
            'daily': calculate_stats(daily_attendance),
            'weekly': calculate_stats(weekly_attendance),
            'termly': calculate_stats(termly_attendance)
        }
    except Exception as e:
        print(f"Error calculating attendance summary: {e}")
        return {
            'daily': {'present': 0, 'absent': 0, 'total': 0, 'percentage': 0},
            'weekly': {'present': 0, 'absent': 0, 'total': 0, 'percentage': 0},
            'termly': {'present': 0, 'absent': 0, 'total': 0, 'percentage': 0}
        }

def get_pupil_reports(pupil_id, academic_year_id=None, exam_type=None, term=None):
    """Get reports (marks) for a pupil with optional filtering
    
    Args:
        pupil_id: ID of the pupil
        academic_year_id: Optional academic year ID to filter by
        exam_type: Optional exam type to filter by (e.g., 'Beginning of term', 'Mid_term', 'End of term')
        term: Optional term number to filter by (1, 2, or 3)
    """
    try:
        # Start with base query
        query = PupilMarks.query.filter_by(pupil_id=pupil_id)
        
        # Apply filters if provided
        if academic_year_id is not None:
            query = query.filter_by(academic_year_id=academic_year_id)
        if exam_type:
            query = query.filter_by(exam_type=exam_type)
        if term is not None:
            query = query.filter_by(term=term)
        
        # Get all mark records for this pupil, ordered by date
        pupil_marks = query.order_by(
            PupilMarks.academic_year_id.desc(),
            PupilMarks.term.desc()
        ).all()

        reports = []
        for mark in pupil_marks:
            reports.append({
                'id': mark.id,
                'term': mark.term,
                'exam_type': mark.exam_type,
                'academic_year': mark.academic_year.name if mark.academic_year else None,
                'english': mark.english,
                'mathematics': mark.mathematics,
                'science': mark.science,
                'social_studies': mark.social_studies,
                'total_marks': mark.total_marks,
                'average': mark.average,
                'english_grade': mark.english_grade,
                'mathematics_grade': mark.mathematics_grade,
                'science_grade': mark.science_grade,
                'social_studies_grade': mark.social_studies_grade,
                'overall_grade': mark.overall_grade,
                'position_in_class': mark.position_in_class,
                'position_in_stream': mark.position_in_stream,
                'class_student_count': mark.class_student_count,
                'stream_student_count': mark.stream_student_count,
                'general_comment': mark.general_comment,
                'english_remark': mark.english_remark,
                'mathematics_remark': mark.mathematics_remark,
                'science_remark': mark.science_remark,
                'social_studies_remark': mark.social_studies_remark,
                'created_at': mark.created_at.isoformat() if mark.created_at else None
            })

        return reports

    except Exception as e:
        print(f"Error getting pupil reports: {e}")
        return []

@parent_bp.route('/api/pupil/<pupil_id>/reports')
def get_reports_with_filters(pupil_id):
    """Get filtered reports for a pupil with available filter options
    
    Query parameters:
    - academic_year_id: Filter by academic year ID
    - exam_type: Filter by exam type (Beginning of term, Mid_term, End of term)
    - term: Filter by term (1, 2, or 3)
    """
    if 'user_id' not in session or session.get('user_role', '').lower() != 'parent':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    pupil = Pupil.query.get(pupil_id)
    if not pupil:
        return jsonify({'success': False, 'message': 'Pupil not found'}), 404

    # Get filter parameters from query string
    academic_year_id = request.args.get('academic_year_id', type=int)
    exam_type = request.args.get('exam_type', type=str)
    term = request.args.get('term', type=int)

    # Get filtered reports
    reports = get_pupil_reports(pupil_id, academic_year_id=academic_year_id, 
                               exam_type=exam_type, term=term)
    
    # Get all available academic years for filter dropdown
    available_years = db.session.query(db.distinct(PupilMarks.academic_year_id)).filter(
        PupilMarks.pupil_id == pupil_id
    ).all()
    
    year_list = []
    for year_id in available_years:
        if year_id[0]:
            year_obj = AcademicYear.query.get(year_id[0])
            if year_obj:
                year_list.append({'id': year_obj.id, 'name': year_obj.name})
    
    # Get all available exam types for filter dropdown
    available_exam_types = db.session.query(db.distinct(PupilMarks.exam_type)).filter(
        PupilMarks.pupil_id == pupil_id
    ).all()
    
    exam_types_list = [exam[0] for exam in available_exam_types if exam[0]]
    
    # Get all available terms for filter dropdown
    available_terms = db.session.query(db.distinct(PupilMarks.term)).filter(
        PupilMarks.pupil_id == pupil_id
    ).all()
    
    terms_list = sorted([term[0] for term in available_terms if term[0]])

    return jsonify({
        'success': True,
        'reports': reports,
        'filters': {
            'academic_years': year_list,
            'exam_types': exam_types_list,
            'terms': terms_list
        }
    })