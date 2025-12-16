from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, FeeCategory, FeeStructure, StudentFee, Payment, PaymentMethod, Pupil, AcademicYear, SchoolClass, User, Stream, Term
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_

bursar_bp = Blueprint('bursar', __name__, url_prefix='/bursar')

# Require bursar role for all routes
def bursar_required(f):
    def wrapper(*args, **kwargs):
        print(f"BURSAR CHECK: user_id in session={('user_id' in session)}, user_role={session.get('user_role', 'None')}")  # Debug print
        if 'user_id' not in session or session.get('user_role', '').lower() != 'bursar':
            print("BURSAR CHECK FAILED: Redirecting to index")  # Debug print
            flash('Access denied')
            return redirect(url_for('index'))
        print("BURSAR CHECK PASSED")  # Debug print
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@bursar_bp.route('/dashboard')
@bursar_required
def dashboard():
    """Bursar dashboard with key metrics and quick actions"""
    # Get current academic year
    current_academic_year = AcademicYear.query.filter_by(is_active=True).first()

    # Quick stats
    total_students = Pupil.query.filter_by(academic_year_id=current_academic_year.id, enrollment_status='active').count() if current_academic_year else 0

    # Today's payments
    today = date.today()
    todays_payments = Payment.query.filter_by(payment_date=today).all()
    todays_total = sum(p.amount for p in todays_payments) if todays_payments else 0.0

    # Outstanding fees calculation
    outstanding_count = 0
    if current_academic_year:
        # Get all active students for current academic year
        students = Pupil.query.filter_by(academic_year_id=current_academic_year.id, enrollment_status='active').all()

        if students:
            # Aggregate fee structures per class
            fee_structs = FeeStructure.query.filter_by(academic_year_id=current_academic_year.id).all()
            assigned_by_class = {}
            for fs in fee_structs:
                assigned_by_class.setdefault(fs.class_id, 0)
                assigned_by_class[fs.class_id] += (fs.term1_amount or 0) + (fs.term2_amount or 0) + (fs.term3_amount or 0)

            # Get payments totals for all students
            student_ids = [s.id for s in students]
            payments_q = db.session.query(Payment.pupil_id, func.coalesce(func.sum(Payment.amount), 0))\
                            .filter(Payment.pupil_id.in_(student_ids))\
                            .filter(Payment.academic_year_id == current_academic_year.id)\
                            .group_by(Payment.pupil_id).all()
            payments_dict = {r[0]: float(r[1]) for r in payments_q}

            # Count students with outstanding fees
            for student in students:
                total_assigned = assigned_by_class.get(student.class_admitted, 0)
                total_paid = payments_dict.get(student.id, 0.0)
                outstanding = max(0, total_assigned - total_paid)
                if outstanding > 0:
                    outstanding_count += 1

    return render_template('bursar/dashboard.html',
                         total_students=total_students,
                         todays_payments_count=len(todays_payments),
                         todays_total=todays_total,
                         outstanding_count=outstanding_count)

@bursar_bp.route('/fee_structure')
@bursar_required
def fee_structure():
    """Manage fee structures"""
    current_academic_year = AcademicYear.query.filter_by(is_active=True).first()
    classes = SchoolClass.query.all()
    academic_years = AcademicYear.query.order_by(AcademicYear.name.desc()).all()
    fee_categories = FeeCategory.query.filter_by(is_active=True).all()
    terms = Term.query.filter_by(is_active=True).order_by(Term.term_number).all()

    # Get existing fee structures
    fee_structures = FeeStructure.query.filter_by(
        academic_year_id=current_academic_year.id if current_academic_year else None,
        is_active=True
    ).all()

    return render_template('bursar/fee_structure.html',
                         classes=classes,
                         academic_years=academic_years,
                         fee_categories=fee_categories,
                         terms=terms,
                         fee_structures=fee_structures,
                         current_academic_year=current_academic_year)

@bursar_bp.route('/save_fee_structure', methods=['POST'])
@bursar_required
def save_fee_structure():
    """Save fee structure"""
    try:
        academic_year_id = request.form.get('academic_year_id')
        class_id = request.form.get('class_id')
        fee_category_id = request.form.get('fee_category_id')

        # Validate required fields
        if not academic_year_id or not class_id or not fee_category_id:
            flash('All fields are required', 'error')
            return redirect(url_for('bursar.fee_structure'))

        # Convert to integers
        try:
            academic_year_id = int(academic_year_id)
            class_id = int(class_id)
            fee_category_id = int(fee_category_id)
        except ValueError:
            flash('Invalid data provided', 'error')
            return redirect(url_for('bursar.fee_structure'))

        term1_amount = int(round(float(request.form.get('term1_amount', 0))))
        term2_amount = int(round(float(request.form.get('term2_amount', 0))))
        term3_amount = int(round(float(request.form.get('term3_amount', 0))))
        annual_amount = int(round(float(request.form.get('annual_amount', 0))))

        # Check if fee structure already exists
        existing = FeeStructure.query.filter_by(
            academic_year_id=academic_year_id,
            class_id=class_id,
            fee_category_id=fee_category_id
        ).first()

        if existing:
            existing.term1_amount = int(round(term1_amount))
            existing.term2_amount = int(round(term2_amount))
            existing.term3_amount = int(round(term3_amount))
            existing.annual_amount = int(round(annual_amount))
            existing.updated_at = datetime.utcnow()
        else:
            fee_structure = FeeStructure(
                academic_year_id=academic_year_id,
                class_id=class_id,
                fee_category_id=fee_category_id,
                term1_amount=int(round(term1_amount)),
                term2_amount=int(round(term2_amount)),
                term3_amount=int(round(term3_amount)),
                annual_amount=int(round(annual_amount))
            )
            db.session.add(fee_structure)

        db.session.commit()
        flash('Fee structure saved successfully', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error saving fee structure: {str(e)}', 'error')

    return redirect(url_for('bursar.fee_structure'))

@bursar_bp.route('/get_fee_structure/<academic_year_id>/<class_id>')
@bursar_required
def get_fee_structure(academic_year_id, class_id):
    """Get fee structures for a specific academic year and class via AJAX"""
    try:
        # Convert to proper types
        academic_year_id = int(academic_year_id)
        term_filter = request.args.get('term', '')

        # Get fee structures for the specific academic year and class
        query = FeeStructure.query.filter_by(
            academic_year_id=academic_year_id,
            class_id=class_id,
            is_active=True
        ).join(FeeCategory)

        # Apply term filtering if specified
        if term_filter:
            try:
                term_num = int(term_filter)
                if term_num == 1:
                    query = query.filter(FeeStructure.term1_amount > 0)
                elif term_num == 2:
                    query = query.filter(FeeStructure.term2_amount > 0)
                elif term_num == 3:
                    query = query.filter(FeeStructure.term3_amount > 0)
            except ValueError:
                pass  # Invalid term, show all

        fee_structures = query.all()

        # Get all fee categories for reference
        fee_categories = FeeCategory.query.filter_by(is_active=True).all()

        # Format the data
        fee_data = []
        for fs in fee_structures:
            # Get category name safely
            category_name = fs.category.name if fs.category else "Unknown"
            fee_data.append({
                'id': fs.id,
                'category_name': category_name,
                'term1_amount': int(round(float(fs.term1_amount))),
                'term2_amount': int(round(float(fs.term2_amount))),
                'term3_amount': int(round(float(fs.term3_amount))),
                'annual_amount': int(round(float(fs.annual_amount)))
            })

        return jsonify({
            'fee_structures': fee_data,
            'fee_categories': [{'id': fc.id, 'name': fc.name} for fc in fee_categories]
        })

    except Exception as e:
        print(f"Error in get_fee_structure: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@bursar_bp.route('/update_fee_structures', methods=['POST'])
@bursar_required
def update_fee_structures():
    """Update multiple fee structures via AJAX"""
    try:
        data = request.get_json()
        updates = data.get('updates', [])

        if not updates:
            return jsonify({'success': False, 'error': 'No updates provided'}), 400

        for update in updates:
            fee_id = update.get('id')
            if not fee_id:
                continue

            fee_structure = FeeStructure.query.get(fee_id)
            if fee_structure:
                fee_structure.term1_amount = int(round(float(update.get('term1_amount', 0))))
                fee_structure.term2_amount = int(round(float(update.get('term2_amount', 0))))
                fee_structure.term3_amount = int(round(float(update.get('term3_amount', 0))))
                fee_structure.annual_amount = int(round(float(update.get('annual_amount', 0))))
                fee_structure.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bursar_bp.route('/students')
@bursar_required
def students():
    """View students and their fee status"""
    # Get all academic years for filter
    academic_years = AcademicYear.query.order_by(AcademicYear.name.desc()).all()

    # Filter params from query string
    academic_year_filter = request.args.get('academic_year', '')
    term_filter = request.args.get('term', '')
    class_filter = request.args.get('class_name', '')
    fee_status_filter = request.args.get('fee_status', '')
    search_filter = request.args.get('search', '').strip()

    # Convert to appropriate types
    if academic_year_filter:
        try:
            academic_year_filter = int(academic_year_filter)
        except ValueError:
            academic_year_filter = None

    current_academic_year = AcademicYear.query.filter_by(is_active=True).first()
    classes = SchoolClass.query.all()
    streams = Stream.query.all()
    payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
    terms = Term.query.filter_by(is_active=True).order_by(Term.term_number).all()

    # Create lookup dictionaries for class and stream names
    class_names = {cls.id: cls.name for cls in classes}
    stream_names = {stream.id: stream.name for stream in streams}

    # Base query for students
    students_query = Pupil.query.filter_by(enrollment_status='active')

    # Apply academic year filter
    if academic_year_filter:
        students_query = students_query.filter_by(academic_year_id=academic_year_filter)
    else:
        # Default to current year if no filter
        if current_academic_year:
            students_query = students_query.filter_by(academic_year_id=current_academic_year.id)

    # Apply class filter
    if class_filter:
        students_query = students_query.filter_by(class_admitted=class_filter)

    # Apply search filter
    if search_filter:
        students_query = students_query.filter(
            or_(
                Pupil.first_name.ilike(f'%{search_filter}%'),
                Pupil.last_name.ilike(f'%{search_filter}%'),
                Pupil.admission_number.ilike(f'%{search_filter}%')
            )
        )

    students = students_query.order_by(Pupil.admission_number.asc()).all()

    # Aggregate fee structures per class
    fee_structs = FeeStructure.query.filter_by(academic_year_id=academic_year_filter if academic_year_filter else (current_academic_year.id if current_academic_year else None)).all()
    assigned_by_class = {}
    for fs in fee_structs:
        assigned_by_class.setdefault(fs.class_id, 0)
        # If a term filter is provided, sum only that term, otherwise sum all terms
        if term_filter:
            try:
                t = int(term_filter)
            except ValueError:
                t = None
            if t == 1:
                assigned_by_class[fs.class_id] += (fs.term1_amount or 0)
            elif t == 2:
                assigned_by_class[fs.class_id] += (fs.term2_amount or 0)
            elif t == 3:
                assigned_by_class[fs.class_id] += (fs.term3_amount or 0)
            else:
                assigned_by_class[fs.class_id] += (fs.term1_amount or 0) + (fs.term2_amount or 0) + (fs.term3_amount or 0)
        else:
            assigned_by_class[fs.class_id] += (fs.term1_amount or 0) + (fs.term2_amount or 0) + (fs.term3_amount or 0)

    # Get payments totals for all students
    student_ids = [s.id for s in students]
    payments_q = {}
    if student_ids:
        payment_query = db.session.query(Payment.pupil_id, func.coalesce(func.sum(Payment.amount), 0))\
                        .filter(Payment.pupil_id.in_(student_ids))
        if academic_year_filter:
            payment_query = payment_query.filter(Payment.academic_year_id == academic_year_filter)
        elif current_academic_year:
            payment_query = payment_query.filter(Payment.academic_year_id == current_academic_year.id)
        if term_filter:
            payment_query = payment_query.filter(Payment.term == int(term_filter))
        payments_q = {r[0]: float(r[1]) for r in payment_query.group_by(Payment.pupil_id).all()}

    # Get fee status for each student
    student_fee_data = []
    for student in students:
        # Convert UUIDs to names for display
        class_name = class_names.get(student.class_admitted, student.class_admitted or 'N/A')
        stream_name = stream_names.get(student.stream, student.stream or 'N/A')

        # Calculate actual fee status
        total_assigned = assigned_by_class.get(student.class_admitted, 0)
        total_paid = payments_q.get(student.id, 0.0)
        outstanding = max(0, total_assigned - total_paid)
        if outstanding == 0:
            fee_status = "Fully Paid"
        elif total_paid > 0:
            fee_status = "Partially Paid"
        else:
            fee_status = "Outstanding"

        # Apply fee status filter
        if fee_status_filter:
            if fee_status_filter == 'fully_paid' and fee_status != 'Fully Paid':
                continue
            if fee_status_filter == 'partially_paid' and fee_status != 'Partially Paid':
                continue
            if fee_status_filter == 'outstanding' and fee_status != 'Outstanding':
                continue

        student_fee_data.append({
            'student': student,
            'class_name': class_name,
            'stream_name': stream_name,
            'fee_status': fee_status,
            'total_paid': total_paid,
            'outstanding': outstanding
        })

    return render_template('bursar/students.html',
                         student_fee_data=student_fee_data,
                         academic_years=academic_years,
                         academic_year_names={y.id: y.name for y in academic_years},
                         current_academic_year=current_academic_year,
                         classes=classes,
                         payment_methods=payment_methods,
                         terms=terms,
                         academic_year_filter=str(academic_year_filter) if academic_year_filter else '',
                         term_filter=term_filter,
                         class_filter=class_filter,
                         fee_status_filter=fee_status_filter,
                         search_filter=search_filter)

@bursar_bp.route('/record_payment')
@bursar_required
def record_payment():
    """Record payment page"""
    current_academic_year = AcademicYear.query.filter_by(is_active=True).first()
    academic_years = AcademicYear.query.order_by(AcademicYear.name.desc()).all()
    payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
    terms = Term.query.filter_by(is_active=True).order_by(Term.term_number).all()

    # Get all students with their class and stream info
    students = Pupil.query.join(SchoolClass, Pupil.class_admitted == SchoolClass.id)\
                         .join(Stream, Pupil.stream == Stream.id)\
                         .order_by(Pupil.admission_number)\
                         .all()

    # Create lookup dictionaries for class and stream names
    classes = {cls.id: cls.name for cls in SchoolClass.query.all()}
    streams = {strm.id: strm.name for strm in Stream.query.all()}

    return render_template('bursar/record_payment.html',
                         current_academic_year=current_academic_year,
                         academic_years=academic_years,
                         payment_methods=payment_methods,
                         terms=terms,
                         students=students,
                         classes=classes,
                         streams=streams,
                         date=date)

@bursar_bp.route('/edit_payments/<pupil_id>')
@bursar_required
def edit_payments(pupil_id):
    """Edit payments for a specific student"""
    student = Pupil.query.get_or_404(pupil_id)
    academic_years = AcademicYear.query.order_by(AcademicYear.name.desc()).all()
    payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
    terms = Term.query.filter_by(is_active=True).order_by(Term.term_number).all()

    # Get all payments for this student
    payments = Payment.query.filter_by(pupil_id=pupil_id).order_by(Payment.payment_date.desc()).all()

    return render_template('bursar/edit_payments.html',
                         student=student,
                         payments=payments,
                         academic_years=academic_years,
                         payment_methods=payment_methods,
                         terms=terms)

@bursar_bp.route('/update_payment/<payment_id>', methods=['POST'])
@bursar_required
def update_payment(payment_id):
    """Update an existing payment"""
    payment = Payment.query.get_or_404(payment_id)

    try:
        payment.academic_year_id = int(request.form.get('academic_year_id'))
        payment.amount = float(request.form.get('amount'))
        payment.term = int(request.form.get('term'))
        payment.payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date()
        payment.payment_method = request.form.get('payment_method')
        payment.notes = request.form.get('notes', '')

        db.session.commit()
        flash('Payment updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating payment: {str(e)}', 'error')

    return redirect(url_for('bursar.edit_payments', pupil_id=payment.pupil_id))

@bursar_bp.route('/update_payments/<pupil_id>', methods=['POST'])
@bursar_required
def update_payments(pupil_id):
    """Update multiple payments for a student"""
    try:
        # Parse form data - Flask handles nested form data
        payments_data = {}

        for key, value in request.form.items():
            if key.startswith('payments['):
                # Parse payments[payment_id][field] format
                parts = key.split('[')
                if len(parts) >= 3:
                    payment_id = parts[1].rstrip(']')
                    field = parts[2].rstrip(']')

                    if payment_id not in payments_data:
                        payments_data[payment_id] = {}

                    payments_data[payment_id][field] = value

        # Update each payment
        for payment_id_str, fields in payments_data.items():
            payment_id = int(payment_id_str)
            payment = Payment.query.get_or_404(payment_id)

            # Update payment fields
            payment.academic_year_id = int(fields.get('academic_year_id'))
            payment.amount = float(fields.get('amount'))
            payment.term = int(fields.get('term'))
            payment.payment_date = datetime.strptime(fields.get('payment_date'), '%Y-%m-%d').date()
            payment.payment_method = fields.get('payment_method')
            payment.notes = fields.get('notes', '')

        db.session.commit()
        flash('All payments updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating payments: {str(e)}', 'error')

    return redirect(url_for('bursar.students'))

@bursar_bp.route('/save_payment', methods=['POST'])
@bursar_required
def save_payment():
    """Save payment record"""
    pupil_id = request.form.get('pupil_id')
    academic_year_id = request.form.get('academic_year_id')
    amount = request.form.get('amount')
    term = request.form.get('term')
    payment_method_name = request.form.get('payment_method')
    notes = request.form.get('notes', '')

    # Validate required fields
    if not pupil_id or not academic_year_id or not amount or not term or not payment_method_name:
        flash('All required fields must be provided', 'error')
        return redirect(url_for('bursar.record_payment'))

    try:
        # Parse and validate data types
        pupil_id = str(pupil_id)
        academic_year_id = int(academic_year_id)
        amount = float(amount)
        term = int(term)
        payment_date = date.today()  # Use today's date

        # Create payment record
        payment = Payment(
            pupil_id=pupil_id,
            student_fee_id=None,  # Will be linked to student fee when fee structure is assigned
            academic_year_id=academic_year_id,
            amount=amount,
            term=term,
            payment_date=payment_date,
            payment_method=payment_method_name,
            receipt_number=f"RCP-{payment_date.strftime('%Y%m%d')}-{Payment.query.count() + 1:04d}",
            transaction_reference=f"TXN-{payment_date.strftime('%Y%m%d%H%M%S')}-{Payment.query.count() + 1:04d}",
            notes=notes,
            recorded_by=session.get('user_id')
        )

        db.session.add(payment)
        db.session.commit()

        flash(f'Payment of UGX {amount:,.0f} recorded successfully.', 'success')
        return redirect(url_for('bursar.students'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error recording payment: {str(e)}', 'error')
        return redirect(url_for('bursar.students'))

@bursar_bp.route('/get_today_payments')
def get_today_payments():
    """Get today's payments for display"""
    try:
        today = date.today()
        payments = Payment.query.filter_by(payment_date=today)\
                               .join(Pupil, Payment.pupil_id == Pupil.id)\
                               .order_by(Payment.recorded_at.desc())\
                               .all()

        payments_data = []
        for payment in payments:
            # Convert to East Africa Time (UTC+3)
            recorded_at_eat = payment.recorded_at + timedelta(hours=3)
            payments_data.append({
                'receipt_number': payment.receipt_number,
                'student_name': f"{payment.pupil.first_name} {payment.pupil.last_name}",
                'amount': payment.amount,
                'payment_method': payment.payment_method,
                'recorded_at': recorded_at_eat.strftime('%m/%d/%Y %I:%M %p')
            })

        return jsonify(payments_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bursar_bp.route('/search_student')
@bursar_required
def search_student():
    """Search student for payment"""
    query = request.args.get('q', '')
    current_academic_year = AcademicYear.query.filter_by(is_active=True).first()

    # Get lookup dictionaries for names
    classes = SchoolClass.query.all()
    streams = Stream.query.all()
    class_names = {cls.id: cls.name for cls in classes}
    stream_names = {stream.id: stream.name for stream in streams}

    students = []
    if query:
        students = Pupil.query.filter(
            and_(
                Pupil.academic_year_id == current_academic_year.id if current_academic_year else True,
                Pupil.enrollment_status == 'active',
                or_(
                    Pupil.first_name.ilike(f'%{query}%'),
                    Pupil.last_name.ilike(f'%{query}%'),
                    Pupil.admission_number.ilike(f'%{query}%')
                )
            )
        ).order_by(Pupil.admission_number.asc()).limit(10).all()

    return jsonify([{
        'id': s.id,
        'name': f'{s.first_name} {s.last_name}',
        'admission_number': s.admission_number,
        'roll_number': s.roll_number,
        'class_name': class_names.get(s.class_admitted, s.class_admitted or 'N/A'),
        'stream': stream_names.get(s.stream, s.stream or 'N/A')
    } for s in students])

@bursar_bp.route('/reports')
@bursar_required
def reports():
    """Financial reports"""
    current_year = datetime.now().year
    terms = Term.query.filter_by(is_active=True).order_by(Term.term_number).all()
    return render_template('bursar/reports.html', current_year=current_year, terms=terms)

@bursar_bp.route('/api/outstanding_fees')
def api_outstanding_fees():
    """API endpoint for outstanding fees data"""
    try:
        current_academic_year = AcademicYear.query.filter_by(is_active=True).first()
        if not current_academic_year:
            return jsonify({'error': 'No active academic year'}), 400

        classes = SchoolClass.query.all()
        class_names = {cls.id: cls.name for cls in classes}

        # Get filter parameters
        class_filter = request.args.get('class_name', '')
        term_filter = request.args.get('term', '')
        amount_filter = request.args.get('amount_range', '')

        # Base query
        query = Pupil.query.filter_by(
            academic_year_id=current_academic_year.id,
            enrollment_status='active'
        )

        if class_filter:
            query = query.filter_by(class_admitted=class_filter)

        students = query.all()

        outstanding_data = []
        for student in students:
            # Get fee structures for the student's class
            fee_structures = FeeStructure.query.filter_by(
                academic_year_id=current_academic_year.id,
                class_id=student.class_admitted
            ).all()

            # Calculate total assigned fees for the class
            total_assigned = 0
            for fs in fee_structures:
                if term_filter:
                    term = int(term_filter)
                    if term == 1:
                        total_assigned += fs.term1_amount
                    elif term == 2:
                        total_assigned += fs.term2_amount
                    elif term == 3:
                        total_assigned += fs.term3_amount
                else:
                    # All terms
                    total_assigned += fs.term1_amount + fs.term2_amount + fs.term3_amount

            # Get payments for this student
            payments = Payment.query.filter_by(
                pupil_id=student.id,
                academic_year_id=current_academic_year.id
            ).all()
            total_paid = sum(payment.amount for payment in payments)

            outstanding_amount = max(0, total_assigned - total_paid)

            # Skip if no outstanding and amount filter is set
            if amount_filter and outstanding_amount == 0:
                continue

            # Apply amount range filter
            if amount_filter:
                if amount_filter == '0-50000' and outstanding_amount >= 50000:
                    continue
                elif amount_filter == '50000-100000' and (outstanding_amount < 50000 or outstanding_amount >= 100000):
                    continue
                elif amount_filter == '100000-200000' and (outstanding_amount < 100000 or outstanding_amount >= 200000):
                    continue
                elif amount_filter == '200000+' and outstanding_amount < 200000:
                    continue

            if outstanding_amount > 0:
                # Calculate days overdue (simplified)
                today = date.today()
                # Assume due date is end of current term
                due_date = today - timedelta(days=30)  # Placeholder
                days_overdue = max(0, (today - due_date).days)

                outstanding_data.append({
                    'id': student.id,
                    'name': f"{student.first_name} {student.last_name}",
                    'admission_number': student.admission_number,
                    'class_name': class_names.get(student.class_admitted, 'Unknown'),
                    'term': int(term_filter) if term_filter else 1,  # Placeholder
                    'outstanding_amount': outstanding_amount,
                    'due_date': due_date.strftime('%Y-%m-%d'),
                    'days_overdue': days_overdue
                })

        return jsonify(outstanding_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bursar_bp.route('/outstanding_fees')
@bursar_required
def outstanding_fees():
    """View outstanding fees"""
    current_academic_year = AcademicYear.query.filter_by(is_active=True).first()
    classes = SchoolClass.query.all()
    class_names = {cls.id: cls.name for cls in classes}
    payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
    terms = Term.query.filter_by(is_active=True).order_by(Term.term_number).all()

    # Filter params from query string
    class_filter = request.args.get('class_name', '')
    term_filter = request.args.get('term', '')
    amount_filter = request.args.get('amount_range', '')

    # Pagination params
    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    per_page = 50

    outstanding_data = []
    total_count = 0
    total_pages = 1

    if current_academic_year:
        # Aggregate fee structures per class to avoid N+1
        fee_structs = FeeStructure.query.filter_by(academic_year_id=current_academic_year.id).all()
        assigned_by_class = {}
        for fs in fee_structs:
            assigned_by_class.setdefault(fs.class_id, 0)
            # If a term filter is provided, sum only that term, otherwise sum all terms
            if term_filter:
                try:
                    t = int(term_filter)
                except ValueError:
                    t = None
                if t == 1:
                    assigned_by_class[fs.class_id] += (fs.term1_amount or 0)
                elif t == 2:
                    assigned_by_class[fs.class_id] += (fs.term2_amount or 0)
                elif t == 3:
                    assigned_by_class[fs.class_id] += (fs.term3_amount or 0)
                else:
                    assigned_by_class[fs.class_id] += (fs.term1_amount or 0) + (fs.term2_amount or 0) + (fs.term3_amount or 0)
            else:
                assigned_by_class[fs.class_id] += (fs.term1_amount or 0) + (fs.term2_amount or 0) + (fs.term3_amount or 0)

        classes_with_fees = list(assigned_by_class.keys())

        # Count students eligible (whose class has assigned fees)
        students_base_q = Pupil.query.filter(
            Pupil.academic_year_id == current_academic_year.id,
            Pupil.enrollment_status == 'active',
            Pupil.class_admitted.in_(classes_with_fees)
        )
        # Apply class filter if provided
        if class_filter:
            students_base_q = students_base_q.filter(Pupil.class_admitted == class_filter)
        total_count = students_base_q.count()
        total_pages = max(1, (total_count + per_page - 1) // per_page)

        # Fetch only the page of students needed
        students = students_base_q.order_by(Pupil.admission_number.asc())\
                      .offset((page - 1) * per_page).limit(per_page).all()

        # Get payments totals for these students in a single query
        student_ids = [s.id for s in students]
        payments_q = {}
        if student_ids:
            rows = db.session.query(Payment.pupil_id, func.coalesce(func.sum(Payment.amount), 0))\
                        .filter(Payment.academic_year_id == current_academic_year.id,
                                Payment.pupil_id.in_(student_ids))\
                        .group_by(Payment.pupil_id).all()
            payments_q = {r[0]: float(r[1]) for r in rows}

        # Build outstanding data for the page
        for student in students:
            total_assigned = assigned_by_class.get(student.class_admitted, 0)
            total_paid = payments_q.get(student.id, 0.0)
            outstanding_amount = max(0, total_assigned - total_paid)

            # Apply amount range filter if provided
            if amount_filter:
                try:
                    amt = float(outstanding_amount)
                except Exception:
                    amt = 0.0
                if amount_filter == '0-50000' and not (amt > 0 and amt < 50000):
                    continue
                if amount_filter == '50000-100000' and not (amt >= 50000 and amt < 100000):
                    continue
                if amount_filter == '100000-200000' and not (amt >= 100000 and amt < 200000):
                    continue
                if amount_filter == '200000+' and not (amt >= 200000):
                    continue

            # Skip students with no outstanding amount
            if outstanding_amount <= 0:
                continue

            # Calculate days overdue (simplified)
            today = date.today()
            due_date = today - timedelta(days=30)
            days_overdue = max(0, (today - due_date).days)

            outstanding_data.append({
                'student': student,
                'class_name': class_names.get(student.class_admitted, 'Unknown'),
                'outstanding_amount': outstanding_amount,
                'term': int(term_filter) if term_filter else None,
                'due_date': due_date.strftime('%Y-%m-%d'),
                'days_overdue': days_overdue
            })

    return render_template('bursar/outstanding_fees.html',
                         outstanding_data=outstanding_data,
                         current_academic_year=current_academic_year,
                         classes=class_names,
                         payment_methods=payment_methods,
                         terms=terms,
                         page=page,
                         per_page=per_page,
                         total_count=total_count,
                         total_pages=total_pages,
                         class_filter=class_filter,
                         term_filter=term_filter,
                         amount_filter=amount_filter)

@bursar_bp.route('/payment_methods')
@bursar_required
def payment_methods():
    """Manage payment methods"""
    payment_methods_list = PaymentMethod.query.order_by(PaymentMethod.name).all()

    # Calculate usage count for each payment method
    for method in payment_methods_list:
        method.usage_count = Payment.query.filter_by(payment_method=method.name).count()

    return render_template('bursar/payment_methods.html', payment_methods=payment_methods_list)

@bursar_bp.route('/save_payment_method', methods=['POST'])
@bursar_required
def save_payment_method():
    """Save or update payment method"""
    method_id = request.form.get('method_id')
    name = request.form.get('name')
    is_active = request.form.get('is_active') == 'on'

    if method_id:
        # Update existing
        method = PaymentMethod.query.get_or_404(method_id)
        method.name = name
        method.is_active = is_active
        flash('Payment method updated successfully!', 'success')
    else:
        # Create new
        method = PaymentMethod(name=name, is_active=is_active)
        db.session.add(method)
        flash('Payment method created successfully!', 'success')

    db.session.commit()
    return redirect(url_for('bursar.payment_methods'))

@bursar_bp.route('/delete_payment_method/<method_id>', methods=['POST'])
@bursar_required
def delete_payment_method(method_id):
    """Delete payment method"""
    method = PaymentMethod.query.get_or_404(method_id)

    # Check if method is used in payments
    payment_count = Payment.query.filter_by(payment_method=method.name).count()
    if payment_count > 0:
        flash(f'Cannot delete payment method. It is used in {payment_count} payment(s).', 'error')
        return redirect(url_for('bursar.payment_methods'))

    db.session.delete(method)
    db.session.commit()
    flash('Payment method deleted successfully!', 'success')
    return redirect(url_for('bursar.payment_methods'))