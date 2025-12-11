from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from models import db, User

user_bp = Blueprint('user', __name__)


@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        # Redirect to the homepage which contains the login form
        return redirect(url_for('index'))

    # POST: authenticate
    data = request.form or request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return render_template('index.html', error='Email and password are required')

    user = User.query.filter_by(email=email).first()
    if not user:
        return render_template('index.html', error='Invalid credentials', transient=True)

    if not user.check_password(password):
        return render_template('index.html', error='Invalid credentials', transient=True)

    # Login success: store minimal session info
    session['user_id'] = user.id
    session['user_role'] = user.role
    session['user_name'] = user.first_name

    # Choose dashboard template based on role
    role = (user.role or 'staff').lower()
    allowed_dashboards = {
        'admin': 'admin/dashboard.html',
        'teacher': 'teacher/dashboard.html',
        'parent': 'parent/dashboard.html',
        'secretary': 'secretary/dashboard.html',
        'bursar': 'bursar/dashboard.html',
        'headteacher': 'headteacher/dashboard.html',
        'staff': 'admin/dashboard.html',
    }

    template = allowed_dashboards.get(role, 'admin/dashboard.html')

    # Pass first_name and email to the dashboard template
    return render_template(template, first_name=user.first_name, email=user.email)


@user_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@user_bp.route('/api/role-firstnames', methods=['GET'])
def role_firstnames():
    """Return a JSON mapping of role -> list of first names (useful for demos).
    Query param `role` can be provided to filter a single role.
    """
    role = request.args.get('role')
    query = User.query
    if role:
        query = query.filter_by(role=role)

    users = query.all()
    result = {}
    for u in users:
        result.setdefault(u.role, []).append(u.first_name)

    return jsonify(result)
