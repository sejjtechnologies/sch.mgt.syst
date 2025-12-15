from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, get_flashed_messages
from datetime import timedelta
import json
from datetime import datetime
import uuid

from models import db, Pupil, Stream, SchoolClass

secretary_bp = Blueprint('secretary', __name__)


@secretary_bp.route('/secretary/dashboard')
def dashboard():
    return render_template('secretary/dashboard.html')


@secretary_bp.route('/secretary/register', methods=['GET'])
def register_form():
    # Fetch streams/classes and pass to template so dropdowns can be rendered server-side
    stream_objs = Stream.query.order_by(Stream.name).all()
    class_objs = SchoolClass.query.order_by(SchoolClass.level).all()

    # Ensure defaults exist if empty (mirror API behaviour)
    if not stream_objs:
        defaults = ['RED', 'GREEN', 'BLUE', 'ORANGE']
        for name in defaults:
            db.session.add(Stream(name=name))
        db.session.commit()
        stream_objs = Stream.query.order_by(Stream.name).all()

    if not class_objs:
        for i in range(1, 8):
            db.session.add(SchoolClass(name=f'P{i}', level=i))
        db.session.commit()
        class_objs = SchoolClass.query.order_by(SchoolClass.level).all()

    # Prepare simple serializable lists and JSON for use in client JS if desired
    streams = [s.to_dict() for s in stream_objs]
    classes = [c.to_dict() for c in class_objs]

    # Check for flashed messages from a prior POST (PRG pattern)
    flashed = get_flashed_messages(with_categories=True)
    success = None
    error = None
    transient = False
    if flashed:
        # take the first flashed message
        cat, msg = flashed[0]
        if cat == 'success':
            success = msg
        else:
            error = msg
        transient = True

    return render_template(
        'secretary/register_pupils.html',
        streams=streams,
        classes=classes,
        all_streams=stream_objs,
        all_classes=class_objs,
        streams_json=json.dumps(streams),
        classes_json=json.dumps(classes),
        success=success,
        error=error,
        transient=transient,
    )


@secretary_bp.route('/secretary/register', methods=['POST'])
def register_submit():
    data = request.form or {}

    def get(k):
        return (data.get(k) or '').strip()

    first_name = get('first_name')
    last_name = get('last_name')
    gender = get('gender') or None
    dob_raw = get('dob')
    nationality = get('nationality') or None
    village = get('village') or None
    subcounty = get('subcounty') or None
    district = get('district') or None
    religion = get('religion') or None
    guardian_first = get('guardian_first') or None
    guardian_last = get('guardian_last') or None
    guardian_phone = get('guardian_phone') or None
    guardian_relationship = get('guardian_relationship') or None
    guardian_occupation = get('guardian_occupation') or None
    class_admitted = get('class_admitted') or None
    stream = get('stream') or None
    previous_school = get('previous_school') or None
    admission_date_raw = get('admission_date')

    # Parse dates
    dob = None
    if dob_raw:
        try:
            dob = datetime.strptime(dob_raw, '%Y-%m-%d').date()
        except Exception:
            dob = None

    admission_date = None
    if admission_date_raw:
        try:
            admission_date = datetime.strptime(admission_date_raw, '%Y-%m-%d').date()
        except Exception:
            admission_date = None

    # Create pupil instance (identifiers generated below)
    pupil = Pupil(
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        dob=dob,
        nationality=nationality,
        village=village,
        subcounty=subcounty,
        district=district,
        religion=religion,
        guardian_first=guardian_first,
        guardian_last=guardian_last,
        guardian_phone=guardian_phone,
        guardian_relationship=guardian_relationship,
        guardian_occupation=guardian_occupation,
        class_admitted=class_admitted,
        stream=stream,
        previous_school=previous_school,
        admission_date=admission_date,
    )

    # Generate sequential admission_number and roll_number like AD/2025/001 and ROLL/2025/001
    year = datetime.utcnow().year

    # Start from current count+1 so numbering naturally resets when rows are deleted
    seq = db.session.query(Pupil).count() + 1

    def _make_numbers(seq_val):
        adm = f"AD/{year}/{seq_val:03d}"
        roll = f"ROLL/{year}/{seq_val:03d}"
        return adm, roll

    # Find next unused sequence (covers race/gaps safely)
    adm_num, roll_num = _make_numbers(seq)
    while db.session.query(Pupil).filter((Pupil.admission_number == adm_num) | (Pupil.roll_number == roll_num)).first():
        seq += 1
        adm_num, roll_num = _make_numbers(seq)

    pupil.admission_number = adm_num
    pupil.roll_number = roll_num

    try:
        db.session.add(pupil)
        db.session.commit()

        # Prepare data for re-rendering the register form with a transient success message
        stream_objs = Stream.query.order_by(Stream.name).all()
        class_objs = SchoolClass.query.order_by(SchoolClass.level).all()
        streams = [s.to_dict() for s in stream_objs]
        classes = [c.to_dict() for c in class_objs]

        success_msg = f"Pupil registered — Admission: {pupil.admission_number} Roll: {pupil.roll_number}"
        # Use PRG: flash message and redirect to GET to avoid double-submits on refresh
        flash(success_msg, 'success')
        return redirect(url_for('secretary.register_form'))
    except Exception as e:
        db.session.rollback()

        # On error, re-render the form with an error message (also transient)
        stream_objs = Stream.query.order_by(Stream.name).all()
        class_objs = SchoolClass.query.order_by(SchoolClass.level).all()
        streams = [s.to_dict() for s in stream_objs]
        classes = [c.to_dict() for c in class_objs]

        flash(f'Error registering pupil: {e}', 'danger')
        return redirect(url_for('secretary.register_form'))


@secretary_bp.route('/api/streams', methods=['GET'])
def api_streams():
    # Ensure some default streams exist
    streams = Stream.query.order_by(Stream.name).all()
    if not streams:
        defaults = ['A', 'B', 'C', 'D']
        for name in defaults:
            s = Stream(name=name)
            db.session.add(s)
        db.session.commit()
        streams = Stream.query.order_by(Stream.name).all()

    return jsonify([s.to_dict() for s in streams])


@secretary_bp.route('/api/classes', methods=['GET'])
def api_classes():
    classes = SchoolClass.query.order_by(SchoolClass.level).all()
    if not classes:
        # Create basic primary classes P1..P7
        for i in range(1, 8):
            name = f'P{i}'
            c = SchoolClass(name=name, level=i)
            db.session.add(c)
        db.session.commit()
        classes = SchoolClass.query.order_by(SchoolClass.level).all()

    return jsonify([c.to_dict() for c in classes])


@secretary_bp.route('/secretary/manage', methods=['GET'])
def manage_pupils():
    pupils = Pupil.query.order_by(Pupil.created_at.desc()).all()

    # Build lookup maps to avoid N+1 queries
    class_objs = {c.id: c.name for c in SchoolClass.query.all()}
    stream_objs = {s.id: s.name for s in Stream.query.all()}

    # Calculate totals per class and stream
    from sqlalchemy import func

    # Total pupils per class
    class_totals = db.session.query(
        Pupil.class_admitted,
        func.count(Pupil.id).label('total_pupils')
    ).filter(Pupil.enrollment_status == 'active').group_by(Pupil.class_admitted).all()

    # Total pupils per stream
    stream_totals = db.session.query(
        Pupil.stream,
        func.count(Pupil.id).label('total_pupils')
    ).filter(Pupil.enrollment_status == 'active').group_by(Pupil.stream).all()

    # Total pupils in the whole school
    total_school_pupils = db.session.query(func.count(Pupil.id)).filter(Pupil.enrollment_status == 'active').scalar() or 0

    # Group streams by class for better display
    class_stream_totals = {}
    for class_id, class_name in class_objs.items():
        streams_in_class = []
        for stream_id, stream_name in stream_objs.items():
            # Count pupils in this specific class and stream combination
            count = db.session.query(func.count(Pupil.id)).filter(
                Pupil.class_admitted == class_id,
                Pupil.stream == stream_id,
                Pupil.enrollment_status == 'active'
            ).scalar() or 0

            if count > 0:
                streams_in_class.append({
                    'stream': stream_name,
                    'total': count
                })

        if streams_in_class:
            class_stream_totals[class_name] = streams_in_class

    # Convert to dictionaries for template
    class_totals_dict = {}
    for class_id, total in class_totals:
        if class_id and class_id in class_objs:
            class_totals_dict[class_objs[class_id]] = total

    stream_totals_dict = {}
    for stream_id, total in stream_totals:
        if stream_id and stream_id in stream_objs:
            stream_totals_dict[stream_objs[stream_id]] = total

    pupils_data = []
    for p in pupils:
        # Resolve class/stream names from stored ids (if present)
        class_name = class_objs.get(p.class_admitted) if p.class_admitted else p.class_admitted
        stream_name = stream_objs.get(p.stream) if p.stream else p.stream

        # Format timestamps to East Africa Time (UTC+3) with am/pm
        created_local = None
        if p.created_at:
            try:
                created_local = (p.created_at + timedelta(hours=3)).strftime('%Y-%m-%d %I:%M %p')
            except Exception:
                created_local = p.created_at.isoformat()

        pupils_data.append({
            'id': p.id,
            'admission_number': p.admission_number,
            'roll_number': p.roll_number,
            'first_name': p.first_name,
            'last_name': p.last_name,
            'gender': p.gender,
            'dob': p.dob.strftime('%Y-%m-%d') if getattr(p, 'dob', None) else None,
            'nationality': p.nationality,
            'religion': p.religion,
            'previous_school': p.previous_school,
            'class_admitted': class_name,
            'stream': stream_name,
            'guardian_first': p.guardian_first,
            'guardian_last': p.guardian_last,
            'guardian_phone': p.guardian_phone,
            'village': p.village,
            'subcounty': p.subcounty,
            'district': p.district,
            'enrollment_status': p.enrollment_status,
            'created_at': created_local,
        })

    # Render server-side table
    return render_template('secretary/manage_pupils.html',
                         pupils=pupils_data,
                         class_totals=class_totals_dict,
                         stream_totals=stream_totals_dict,
                         total_school_pupils=total_school_pupils,
                         class_stream_totals=class_stream_totals)


@secretary_bp.route('/api/pupils', methods=['GET'])
def api_pupils():
    pupils = Pupil.query.order_by(Pupil.created_at.desc()).all()

    # Provide human-friendly class/stream names and localized created_at
    class_objs = {c.id: c.name for c in SchoolClass.query.all()}
    stream_objs = {s.id: s.name for s in Stream.query.all()}
    out = []
    for p in pupils:
        class_name = class_objs.get(p.class_admitted) if p.class_admitted else p.class_admitted
        stream_name = stream_objs.get(p.stream) if p.stream else p.stream
        created_local = None
        if p.created_at:
            try:
                created_local = (p.created_at + timedelta(hours=3)).strftime('%Y-%m-%d %I:%M %p')
            except Exception:
                created_local = p.created_at.isoformat()

        obj = p.to_dict()
        obj['class_admitted'] = class_name
        obj['stream'] = stream_name
        obj['created_at_local'] = created_local
        out.append(obj)

    return jsonify(out)


@secretary_bp.route('/secretary/delete/<uuid:id>', methods=['POST'])
def delete_pupil(id):
    pupil = Pupil.query.get_or_404(str(id))
    db.session.delete(pupil)
    db.session.commit()
    flash('Pupil deleted successfully', 'success')
    return redirect(url_for('secretary.manage_pupils'))


@secretary_bp.route('/secretary/edit/<uuid:id>', methods=['GET'])
def edit_pupil(id):
    pupil = Pupil.query.get_or_404(str(id))
    stream_objs = Stream.query.order_by(Stream.name).all()
    class_objs = SchoolClass.query.order_by(SchoolClass.level).all()

    streams = [s.to_dict() for s in stream_objs]
    classes = [c.to_dict() for c in class_objs]

    # Check for flashed messages
    flashed = get_flashed_messages(with_categories=True)
    success = None
    error = None
    transient = False
    if flashed:
        cat, msg = flashed[0]
        if cat == 'success':
            success = msg
        else:
            error = msg
        transient = True

    return render_template('secretary/edit_pupils.html', pupil=pupil, streams=streams, classes=classes, success=success, error=error, transient=transient)


@secretary_bp.route('/secretary/edit/<uuid:id>', methods=['POST'])
def edit_pupil_submit(id):
    pupil = Pupil.query.get_or_404(str(id))

    # Update fields
    pupil.first_name = request.form.get('first_name', '').strip()
    pupil.last_name = request.form.get('last_name', '').strip()
    pupil.gender = request.form.get('gender', '').strip()
    dob_str = request.form.get('dob', '').strip()
    if dob_str:
        try:
            pupil.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    pupil.nationality = request.form.get('nationality', '').strip()
    pupil.village = request.form.get('village', '').strip()
    pupil.subcounty = request.form.get('subcounty', '').strip()
    pupil.district = request.form.get('district', '').strip()
    pupil.religion = request.form.get('religion', '').strip()
    pupil.guardian_first = request.form.get('guardian_first', '').strip()
    pupil.guardian_last = request.form.get('guardian_last', '').strip()
    pupil.guardian_phone = request.form.get('guardian_phone', '').strip()
    pupil.guardian_relationship = request.form.get('guardian_relationship', '').strip()
    pupil.guardian_occupation = request.form.get('guardian_occupation', '').strip()
    pupil.previous_school = request.form.get('previous_school', '').strip()
    admission_date_str = request.form.get('admission_date', '').strip()
    if admission_date_str:
        try:
            pupil.admission_date = datetime.strptime(admission_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    pupil.enrollment_status = request.form.get('enrollment_status', 'active').strip()

    # Class and stream
    class_id = request.form.get('class_admitted')
    if class_id:
        pupil.class_admitted = class_id
    stream_id = request.form.get('stream')
    if stream_id:
        pupil.stream = stream_id

    try:
        db.session.commit()
        flash('Pupil updated successfully', 'success')
        return redirect(url_for('secretary.manage_pupils'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating pupil: {str(e)}', 'error')
        return redirect(url_for('secretary.edit_pupil', id=id))
