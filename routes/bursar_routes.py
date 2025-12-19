from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import uuid
from models import db, FeeCategory, FeeStructure, StudentFee, Payment, PaymentMethod, Pupil, AcademicYear, SchoolClass, User, Stream, Term, BursarSettings, SystemSetting
from utils.settings import SystemSettings
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_
import pytz

bursar_bp = Blueprint('bursar', __name__, url_prefix='/bursar')

# Require bursar role for all routes (but allow admin access)
def bursar_required(f):
    def wrapper(*args, **kwargs):
        print(f"BURSAR CHECK: user_id in session={('user_id' in session)}, user_role={session.get('user_role', 'None')}")  # Debug print
        user_role = session.get('user_role', '').lower()
        if 'user_id' not in session or (user_role != 'bursar' and user_role != 'admin'):
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

    # Load academic years and terms for the termly report modal
    academic_years = AcademicYear.query.order_by(AcademicYear.name.desc()).all()
    terms = Term.query.order_by(Term.id).all()

    return render_template('bursar/dashboard.html',
                         total_students=total_students,
                         todays_payments_count=len(todays_payments),
                         todays_total=todays_total,
                         todays_total_formatted=SystemSettings.format_currency(todays_total),
                         outstanding_count=outstanding_count,
                         academic_years=academic_years,
                         terms=terms)


@bursar_bp.route('/fee_search', methods=['POST'])
@bursar_required
def fee_search():
    """AJAX endpoint to search pupils/payments by name, admission or receipt"""
    q = request.form.get('q', '').strip()
    filter_by = request.form.get('filter', 'any')
    results = []
    if q:
        # Search payments joined with pupils
        qry = db.session.query(Payment, Pupil).join(Pupil, Payment.pupil_id == Pupil.id)

        if filter_by == 'name' or filter_by == 'any':
            name_filter = or_(func.lower(Pupil.first_name).like(f"%{q.lower()}%"), func.lower(Pupil.last_name).like(f"%{q.lower()}%"))
            qry = qry.filter(name_filter) if filter_by == 'name' else qry.filter(name_filter)

        if filter_by == 'admission' or filter_by == 'any':
            # use `admission_number` field from Pupil
            qry = qry.filter(Pupil.admission_number == q)

        if filter_by == 'receipt' or filter_by == 'any':
            # Payment stores receipt_number
            qry = qry.filter(Payment.receipt_number == q)

        # Limit results for performance
        rows = qry.order_by(Payment.payment_date.desc()).limit(100).all()
        for payment, pupil in rows:
            results.append({
                'pupil_name': f"{pupil.first_name} {pupil.last_name}",
                'admission_no': getattr(pupil, 'admission_number', ''),
                'receipt_no': getattr(payment, 'receipt_number', ''),
                'amount': payment.amount,
                'amount_formatted': SystemSettings.format_currency(payment.amount),
                'date_posted': payment.payment_date.strftime('%Y-%m-%d') if getattr(payment, 'payment_date', None) else '',
                'payment_id': payment.id,
                'pupil_id': pupil.id
            })

    return render_template('bursar/_fee_search_results.html', results=results)


@bursar_bp.route('/term_reports', methods=['POST'])
@bursar_required
def term_reports():
    """Return payments for selected academic year and term"""
    academic_year_id = request.form.get('academic_year')
    term_id = request.form.get('term_id')
    results = []
    if academic_year_id and term_id:
        try:
            ay_id = int(academic_year_id)
        except Exception:
            ay_id = None
        try:
            term_int = int(term_id)
        except Exception:
            term_int = None

        rows = db.session.query(Payment, Pupil).join(Pupil, Payment.pupil_id == Pupil.id)
        if ay_id is not None:
            rows = rows.filter(Payment.academic_year_id == ay_id)
        if term_int is not None:
            rows = rows.filter(Payment.term == term_int)
        rows = rows.order_by(Payment.payment_date.desc()).limit(500).all()
        for payment, pupil in rows:
            results.append({
                'pupil_name': f"{pupil.first_name} {pupil.last_name}",
                'admission_no': getattr(pupil, 'admission_number', ''),
                'receipt_no': getattr(payment, 'receipt_number', ''),
                'amount': payment.amount,
                'amount_formatted': SystemSettings.format_currency(payment.amount),
                'date_posted': payment.payment_date.strftime('%Y-%m-%d') if getattr(payment, 'payment_date', None) else '',
                'payment_id': payment.id,
                'pupil_id': pupil.id
            })

    return render_template('bursar/_fee_search_results.html', results=results)


@bursar_bp.route('/pupil_payments/<pupil_id>', methods=['GET', 'POST'])
@bursar_required
def pupil_payments(pupil_id):
    """View and manage payments for a single pupil"""
    pupil = Pupil.query.filter_by(id=pupil_id).first()
    if not pupil:
        flash('Pupil not found', 'error')
        return redirect(url_for('bursar.dashboard'))

    # Current academic year and list
    current_year = AcademicYear.query.filter_by(is_active=True).first()
    academic_years = AcademicYear.query.order_by(AcademicYear.name.desc()).all()

    # Payment methods
    payment_methods = PaymentMethod.query.filter_by(is_active=True).order_by(PaymentMethod.name).all()

    editing_payment = None
    if request.method == 'POST':
        # Add or edit payment
        try:
            payment_id = request.form.get('payment_id') or None
            amount = float(request.form.get('amount') or 0)
            term = int(request.form.get('term') or 0)
            payment_date = request.form.get('payment_date') or None
            payment_method = request.form.get('payment_method') or 'cash'
            receipt_number = request.form.get('receipt_number') or None
            transaction_reference = request.form.get('transaction_reference') or None
            notes = request.form.get('notes') or None
            academic_year_id = request.form.get('academic_year_id') or (current_year.id if current_year else None)

            if payment_id:
                payment = Payment.query.get(payment_id)
                if not payment:
                    flash('Payment not found', 'error')
                else:
                    payment.amount = amount
                    payment.term = term
                    payment.payment_date = payment_date
                    payment.payment_method = payment_method
                    payment.receipt_number = receipt_number
                    payment.transaction_reference = transaction_reference
                    payment.notes = notes
                    payment.academic_year_id = academic_year_id
                    payment.recorded_by = session.get('user_id')
                    payment.recorded_at = datetime.utcnow()
                    db.session.commit()
                    flash('Payment updated', 'success')
            else:
                payment = Payment(
                    pupil_id=pupil.id,
                    academic_year_id=academic_year_id,
                    amount=amount,
                    term=term,
                    payment_date=payment_date,
                    payment_method=payment_method,
                    receipt_number=receipt_number,
                    transaction_reference=transaction_reference,
                    notes=notes,
                    recorded_by=session.get('user_id')
                )
                # auto-generate receipt number if not provided
                if not payment.receipt_number:
                    payment.receipt_number = f"RCPT-{int(datetime.utcnow().timestamp())}-{uuid.uuid4().hex[:6]}"
                db.session.add(payment)
                db.session.commit()
                flash('Payment recorded', 'success')

            try:
                return redirect(url_for('bursar.pupil_payments', pupil_id=pupil.id, term=term, academic_year=academic_year_id))
            except Exception:
                return redirect(url_for('bursar.pupil_payments', pupil_id=pupil.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving payment: {e}', 'error')

    # GET: gather payments and summary
    payments = Payment.query.filter_by(pupil_id=pupil.id).order_by(Payment.payment_date.desc()).all()
    total_paid = sum(p.amount for p in payments) if payments else 0.0

    # assigned total (derive from fee structures) and respect optional term/academic year filters
    assigned_total = 0.0
    # Allow optional term filter via query string so assigned_total can reflect a specific term
    term_param = request.args.get('term') or request.args.get('term_id')
    term_selected = None
    try:
        term_selected = int(term_param) if term_param else None
    except Exception:
        term_selected = None

    # Allow optional academic year filter via query string
    ay_param = request.args.get('academic_year') or request.args.get('academic_year_id')
    selected_academic_year = None
    try:
        selected_academic_year = int(ay_param) if ay_param else None
    except Exception:
        selected_academic_year = None

    # Determine which academic year to use for assigned totals: selected -> current_year
    target_year_id = selected_academic_year or (current_year.id if current_year else None)

    # Build fee structures map for the target year
    assigned_by_class = {}
    if target_year_id:
        fee_structs = FeeStructure.query.filter_by(academic_year_id=target_year_id).all()
        for fs in fee_structs:
            # pick appropriate term amount if a specific term is requested
            if term_selected == 1:
                amt = fs.term1_amount or 0
            elif term_selected == 2:
                amt = fs.term2_amount or 0
            elif term_selected == 3:
                amt = fs.term3_amount or 0
            else:
                amt = (fs.term1_amount or 0) + (fs.term2_amount or 0) + (fs.term3_amount or 0)

            assigned_by_class.setdefault(fs.class_id, 0)
            assigned_by_class[fs.class_id] += amt

        assigned_total = assigned_by_class.get(pupil.class_admitted, 0)

    # Filter payments query by selected academic year and term so totals reflect the same scope
    payments_query = Payment.query.filter_by(pupil_id=pupil.id)
    if selected_academic_year:
        payments_query = payments_query.filter_by(academic_year_id=selected_academic_year)
    if term_selected:
        payments_query = payments_query.filter_by(term=term_selected)
    payments = payments_query.order_by(Payment.payment_date.desc()).all()

    total_paid = sum(p.amount for p in payments) if payments else 0.0
    balance = max(0, assigned_total - total_paid)

    # Build results structure (used by the payments partial) so each row can include payment_id
    results = []
    for payment in payments:
        results.append({
            'pupil_name': f"{pupil.first_name} {pupil.last_name}",
            'admission_no': getattr(pupil, 'admission_number', ''),
            'receipt_no': getattr(payment, 'receipt_number', ''),
            'amount': payment.amount,
            'amount_formatted': SystemSettings.format_currency(payment.amount),
            'date_posted': payment.payment_date.strftime('%Y-%m-%d') if getattr(payment, 'payment_date', None) else '',
            'payment_method': getattr(payment, 'payment_method', ''),
            'term': getattr(payment, 'term', None),
            'academic_year_id': getattr(payment, 'academic_year_id', None),
            'notes': getattr(payment, 'notes', '') or '',
            'pupil_id': pupil.id,
            'payment_id': payment.id
        })

    # Format for display
    assigned_total_formatted = SystemSettings.format_currency(assigned_total)
    total_paid_formatted = SystemSettings.format_currency(total_paid)
    balance_formatted = SystemSettings.format_currency(balance)

    # Provide class and stream name lookups so templates show human-readable names
    classes = {cls.id: cls.name for cls in SchoolClass.query.all()}
    streams = {strm.id: strm.name for strm in Stream.query.all()}

    # Allow pre-filling an edit form via query parameter ?edit_payment_id=<id>
    edit_payment_id = request.args.get('edit_payment_id')
    if edit_payment_id:
        try:
            editing_payment = Payment.query.get(int(edit_payment_id))
        except Exception:
            editing_payment = None

    # Terms for dropdowns
    terms = Term.query.filter_by(is_active=True).order_by(Term.term_number).all()

    # Build assigned_by_year map for the pupil's class so client can compute assigned totals per year/term
    assigned_by_year = {}
    try:
        class_id = pupil.class_admitted
        for ay in academic_years:
            fee_structs_for_ay = FeeStructure.query.filter_by(academic_year_id=ay.id, class_id=class_id).all()
            term1 = sum((fs.term1_amount or 0) for fs in fee_structs_for_ay)
            term2 = sum((fs.term2_amount or 0) for fs in fee_structs_for_ay)
            term3 = sum((fs.term3_amount or 0) for fs in fee_structs_for_ay)
            total = term1 + term2 + term3
            assigned_by_year[ay.id] = {'term1': term1, 'term2': term2, 'term3': term3, 'annual': total}
    except Exception:
        assigned_by_year = {}

    # Selected filters from query string (for template defaults)
    selected_term = term_selected
    # `selected_academic_year` was computed earlier to influence server-side filtering

    return render_template('bursar/pupil_payments.html', pupil=pupil, payments=payments, results=results,
                           total_paid=total_paid, assigned_total=assigned_total, balance=balance,
                           assigned_total_formatted=assigned_total_formatted, total_paid_formatted=total_paid_formatted,
                           balance_formatted=balance_formatted, payment_methods=payment_methods,
                           current_year=current_year, editing_payment=editing_payment,
                           classes=classes, streams=streams, academic_years=academic_years,
                           terms=terms, selected_term=selected_term, selected_academic_year=selected_academic_year,
                           assigned_by_year=assigned_by_year)
@bursar_bp.route('/payment_history')
@bursar_required
def payment_history():
    """View payment history"""
    # Get class names for lookup
    class_names = {cls.id: cls.name for cls in SchoolClass.query.all()}

    # Get payment methods from PaymentMethod table
    payment_methods = PaymentMethod.query.filter_by(is_active=True).order_by(PaymentMethod.name).all()
    payment_method_names = [method.name for method in payment_methods]

    # Get terms from database
    terms = Term.query.filter_by(is_active=True).order_by(Term.term_number).all()

    # Get academic years from database
    academic_years = AcademicYear.query.order_by(AcademicYear.name).all()

    # Get recent payments with student and academic year details
    payments = Payment.query.join(Pupil).join(AcademicYear).order_by(Payment.payment_date.desc()).limit(100).all()

    # Process payments with system timezone
    system_tz = pytz.timezone(SystemSettings.get_timezone())
    processed_payments = []

    for payment in payments:
        # Convert recorded_at to system timezone
        if payment.recorded_at:
            # Assume recorded_at is UTC (as stored by SQLAlchemy)
            utc_time = pytz.utc.localize(payment.recorded_at) if payment.recorded_at.tzinfo is None else payment.recorded_at
            system_time = utc_time.astimezone(system_tz)
            formatted_time = system_time.strftime('%d/%m/%Y %I:%M %p')
        else:
            formatted_time = 'N/A'

        # Create payment dict with formatted time
        payment_dict = {
            'id': payment.id,
            'pupil': payment.pupil,
            'academic_year': payment.academic_year,
            'amount': payment.amount,
            'amount_formatted': SystemSettings.format_currency(payment.amount),
            'term': payment.term,
            'payment_date': payment.payment_date,
            'payment_method': payment.payment_method,
            'receipt_number': payment.receipt_number,
            'transaction_reference': payment.transaction_reference,
            'recorded_at_system_tz': formatted_time  # System timezone time
        }
        processed_payments.append(payment_dict)

    return render_template('bursar/payment_history.html', payments=processed_payments, class_names=class_names, payment_methods=payment_method_names, terms=terms, academic_years=academic_years)

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
            return redirect(url_for('bursar.fee_structure', academic_year=academic_year_id or '', class_id=class_id or ''))

        # Convert to integers
        try:
            academic_year_id = int(academic_year_id)
            class_id = int(class_id)
            fee_category_id = int(fee_category_id)
        except ValueError:
            flash('Invalid data provided', 'error')
            return redirect(url_for('bursar.fee_structure', academic_year=academic_year_id or '', class_id=class_id or ''))

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

    return redirect(url_for('bursar.fee_structure', academic_year=academic_year_id if 'academic_year_id' in locals() else '', class_id=class_id if 'class_id' in locals() else ''))

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

        # Note: Term filtering removed - show all fee categories regardless of term amounts

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

@bursar_bp.route('/get_terms')
@bursar_required
def get_terms():
    """Get all active terms via AJAX"""
    try:
        terms = Term.query.filter_by(is_active=True).order_by(Term.term_number).all()
        term_data = [{'id': t.term_number, 'name': t.name} for t in terms]
        return jsonify({'terms': term_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

    # Redirect back to the pupil payments management view preserving term and academic year
    try:
        return redirect(url_for('bursar.pupil_payments', pupil_id=payment.pupil_id, term=payment.term, academic_year=payment.academic_year_id))
    except Exception:
        return redirect(url_for('bursar.pupil_payments', pupil_id=payment.pupil_id))

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

    # After updating multiple payments, redirect back to the pupil payments page for that pupil
    # Try to preserve term and academic_year if present in the submitted data
    try:
        first_payment = next(iter(payments_data.values())) if payments_data else None
        term = int(first_payment.get('term')) if first_payment and first_payment.get('term') else None
        ay = int(first_payment.get('academic_year_id')) if first_payment and first_payment.get('academic_year_id') else None
        if term and ay:
            return redirect(url_for('bursar.pupil_payments', pupil_id=pupil_id, term=term, academic_year=ay))
    except Exception:
        pass
    return redirect(url_for('bursar.pupil_payments', pupil_id=pupil_id))

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
        # Redirect to pupil payments management view, preserving submitted term and academic year if present
        try:
            posted_term = request.form.get('term') or request.form.get('term_id')
            posted_ay = request.form.get('academic_year_id') or request.form.get('academic_year')
            return redirect(url_for('bursar.pupil_payments', pupil_id=pupil_id, term=posted_term, academic_year=posted_ay))
        except Exception:
            return redirect(url_for('bursar.pupil_payments', pupil_id=pupil_id))

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
        try:
            return redirect(url_for('bursar.pupil_payments', pupil_id=pupil_id, term=term, academic_year=academic_year_id))
        except Exception:
            return redirect(url_for('bursar.students'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error recording payment: {str(e)}', 'error')
        try:
            posted_term = request.form.get('term') or request.form.get('term_id')
            posted_ay = request.form.get('academic_year_id') or request.form.get('academic_year')
            return redirect(url_for('bursar.pupil_payments', pupil_id=pupil_id, term=posted_term, academic_year=posted_ay))
        except Exception:
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
    academic_years = AcademicYear.query.order_by(AcademicYear.name).all()
    return render_template('bursar/reports.html', current_year=current_year, terms=terms, academic_years=academic_years)

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

@bursar_bp.route('/api/payment_summary')
def api_payment_summary():
    """API endpoint for payment summary report"""
    try:
        # Get filter parameters
        academic_year_id = request.args.get('academic_year', '')
        term_filter = request.args.get('term', '')

        # Get academic year
        if academic_year_id:
            academic_year = AcademicYear.query.get(academic_year_id)
        else:
            academic_year = AcademicYear.query.filter_by(is_active=True).first()

        if not academic_year:
            return jsonify({'error': 'No academic year found'}), 400

        # Query payments grouped by term
        from sqlalchemy import func, case

        query = db.session.query(
            Payment.term,
            func.count(Payment.id).label('payment_count'),
            func.sum(Payment.amount).label('total_amount')
        ).filter(
            Payment.academic_year_id == academic_year.id
        )

        if term_filter:
            query = query.filter(Payment.term == int(term_filter))

        query = query.group_by(Payment.term).order_by(Payment.term)

        results = query.all()

        # Get term names
        terms_dict = {term.term_number: term.name for term in Term.query.all()}

        data = []
        for result in results:
            data.append({
                'term': terms_dict.get(result.term, f'Term {result.term}'),
                'payments': result.payment_count,
                'amount': result.total_amount
            })

        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bursar_bp.route('/api/revenue_analysis')
def api_revenue_analysis():
    """API endpoint for revenue analysis report"""
    try:
        # Get filter parameters
        academic_year_id = request.args.get('academic_year', '')
        term_filter = request.args.get('term', '')

        # Get academic year
        if academic_year_id:
            academic_year = AcademicYear.query.get(academic_year_id)
        else:
            academic_year = AcademicYear.query.filter_by(is_active=True).first()

        if not academic_year:
            return jsonify({'error': 'No academic year found'}), 400

        # Get total revenue
        total_revenue_query = db.session.query(func.sum(Payment.amount)).filter(
            Payment.academic_year_id == academic_year.id
        )
        if term_filter:
            total_revenue_query = total_revenue_query.filter(Payment.term == int(term_filter))

        total_revenue = total_revenue_query.scalar() or 0

        # Get student count
        student_count = Pupil.query.filter_by(
            academic_year_id=academic_year.id,
            enrollment_status='active'
        ).count()

        avg_revenue = total_revenue / student_count if student_count > 0 else 0

        # Calculate collection rate (simplified - total collected vs expected)
        # For now, assume 95% collection rate as placeholder
        collection_rate = 95.2

        # Monthly revenue data (group by month)
        monthly_query = db.session.query(
            func.extract('month', Payment.payment_date).label('month'),
            func.sum(Payment.amount).label('amount')
        ).filter(
            Payment.academic_year_id == academic_year.id,
            Payment.payment_date.isnot(None)
        )

        if term_filter:
            monthly_query = monthly_query.filter(Payment.term == int(term_filter))

        monthly_query = monthly_query.group_by(func.extract('month', Payment.payment_date)).order_by(func.extract('month', Payment.payment_date))

        monthly_data = monthly_query.all()

        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        monthly_amounts = [0] * 12

        for result in monthly_data:
            month_idx = int(result.month) - 1
            if 0 <= month_idx < 12:
                monthly_amounts[month_idx] = result.amount

        data = {
            'total_revenue': total_revenue,
            'avg_revenue': avg_revenue,
            'collection_rate': collection_rate,
            'monthly_labels': months,
            'monthly_data': monthly_amounts
        }

        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bursar_bp.route('/api/class_collection')
def api_class_collection():
    """API endpoint for class-wise collection report"""
    try:
        # Get filter parameters
        academic_year_id = request.args.get('academic_year', '')
        term_filter = request.args.get('term', '')

        # Get academic year
        if academic_year_id:
            academic_year = AcademicYear.query.get(academic_year_id)
        else:
            academic_year = AcademicYear.query.filter_by(is_active=True).first()

        if not academic_year:
            return jsonify({'error': 'No academic year found'}), 400

        # Get all classes
        classes = SchoolClass.query.all()
        class_names = {cls.id: cls.name for cls in classes}

        data = []

        for class_id, class_name in class_names.items():
            # Count students in this class
            student_count = Pupil.query.filter_by(
                academic_year_id=academic_year.id,
                class_admitted=class_id,
                enrollment_status='active'
            ).count()

            # Get fee structures for this class
            fee_structures = FeeStructure.query.filter_by(
                academic_year_id=academic_year.id,
                class_id=class_id
            ).all()

            # Calculate expected fees
            expected_total = 0
            for fs in fee_structures:
                if term_filter:
                    term = int(term_filter)
                    if term == 1:
                        expected_total += fs.term1_amount * student_count
                    elif term == 2:
                        expected_total += fs.term2_amount * student_count
                    elif term == 3:
                        expected_total += fs.term3_amount * student_count
                else:
                    expected_total += (fs.term1_amount + fs.term2_amount + fs.term3_amount) * student_count

            # Get collected amount for this class
            collected_query = db.session.query(func.sum(Payment.amount)).filter(
                Payment.academic_year_id == academic_year.id,
                Payment.pupil.has(class_admitted=class_id)
            )

            if term_filter:
                collected_query = collected_query.filter(Payment.term == int(term_filter))

            collected_total = collected_query.scalar() or 0

            # Calculate percentage
            percentage = (collected_total / expected_total * 100) if expected_total > 0 else 0

            data.append({
                'class': class_name,
                'students': student_count,
                'expected': expected_total,
                'collected': collected_total,
                'percentage': round(percentage, 1)
            })

        # Sort by class name
        data.sort(key=lambda x: x['class'])

        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

@bursar_bp.route('/settings', methods=['GET', 'POST'])
@bursar_required
def settings():
    """Bursar settings page"""
    if request.method == 'POST':
        print(f"DEBUG: POST request to bursar settings")
        print(f"DEBUG: Form data: {dict(request.form)}")
        # Handle form submission
        try:
            # General settings
            school_name = request.form.get('school_name', '')
            abbr_name = request.form.get('abbreviated_school_name', '')
            print(f"DEBUG: Saving school_name='{school_name}', abbreviated_school_name='{abbr_name}'")
            
            SystemSetting.upsert_setting('general', 'school_name', school_name)
            SystemSetting.upsert_setting('general', 'abbreviated_school_name', abbr_name)
            SystemSetting.upsert_setting('general', 'currency', request.form.get('currency', 'KES'))
            SystemSetting.upsert_setting('general', 'academic_year', request.form.get('academic_year', ''))
            SystemSetting.upsert_setting('general', 'timezone', request.form.get('timezone', 'Africa/Nairobi'))

            # Notification settings
            SystemSetting.upsert_setting('notifications', 'email_notifications', request.form.get('email_notifications') == 'on')
            SystemSetting.upsert_setting('notifications', 'payment_reminders', request.form.get('payment_reminders') == 'on')
            SystemSetting.upsert_setting('notifications', 'overdue_alerts', request.form.get('overdue_alerts') == 'on')
            SystemSetting.upsert_setting('notifications', 'reminder_days', int(request.form.get('reminder_days', 7)))

            # Security settings
            SystemSetting.upsert_setting('security', 'password_min_length', int(request.form.get('password_min_length', 8)))
            SystemSetting.upsert_setting('security', 'session_timeout', int(request.form.get('session_timeout', 30)))
            SystemSetting.upsert_setting('security', 'two_factor_auth', request.form.get('two_factor_auth') == 'on')
            SystemSetting.upsert_setting('security', 'login_attempts', int(request.form.get('login_attempts', 5)))

            # Report settings
            SystemSetting.upsert_setting('reports', 'default_format', request.form.get('default_format', 'pdf'))
            SystemSetting.upsert_setting('reports', 'auto_generate', request.form.get('auto_generate') == 'on')
            SystemSetting.upsert_setting('reports', 'include_charts', request.form.get('include_charts') == 'on')
            SystemSetting.upsert_setting('reports', 'report_frequency', request.form.get('report_frequency', 'monthly'))

            db.session.commit()
            # Invalidate system settings cache
            SystemSettings.invalidate_cache()
            print(f"DEBUG: Settings committed and cache invalidated")
            flash('Settings saved successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving settings: {str(e)}', 'error')

        return redirect(url_for('bursar.settings'))

    # GET request - load current settings
    settings_data = {}

    # Load all settings from database
    all_settings = SystemSetting.query.filter_by(is_active=True).all()
    for setting in all_settings:
        if setting.category not in settings_data:
            settings_data[setting.category] = {}
        settings_data[setting.category][setting.key] = setting.typed_value

    # Set defaults if not found
    defaults = {
        'general': {
            'school_name': '',
            'currency': 'KES',
            'academic_year': '',
            'timezone': 'Africa/Nairobi'
        },
        'notifications': {
            'email_notifications': False,
            'payment_reminders': True,
            'overdue_alerts': True,
            'reminder_days': 7
        },
        'security': {
            'password_min_length': 8,
            'session_timeout': 30,
            'two_factor_auth': False,
            'login_attempts': 5
        },
        'reports': {
            'default_format': 'pdf',
            'auto_generate': False,
            'include_charts': True,
            'report_frequency': 'monthly'
        }
    }

    # Merge defaults with database values
    for category, category_defaults in defaults.items():
        if category not in settings_data:
            settings_data[category] = {}
        for key, default_value in category_defaults.items():
            if key not in settings_data[category]:
                settings_data[category][key] = default_value

    # Fetch academic years for dropdown
    academic_years = AcademicYear.query.order_by(AcademicYear.start_year.desc()).all()

    return render_template('bursar/settings.html', settings=settings_data, academic_years=academic_years)