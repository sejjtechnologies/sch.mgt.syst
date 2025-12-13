from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.user import User, db
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'admin':
        flash('Access denied')
        return redirect(url_for('index'))

    roles = ['Teacher', 'Parent', 'Secretary', 'HeadTeacher', 'Bursar']

    password_msg = ''

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'staff')
        is_active = request.form.get('is_active') == 'on'

        # Check required fields
        if not all([first_name, last_name, email, password]):
            flash('All fields are required')
            return redirect(request.url)

        # Password length validation
        if len(password) < 6:
            password_msg = 'Password should be 6 characters and above'
            return render_template('admin/create_user.html', roles=roles, password_msg=password_msg,
                                   first_name=first_name, last_name=last_name, email=email, role=role, is_active=is_active)

        # Check if email exists
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(request.url)

        # Create user
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role,
            is_active=is_active
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('User created successfully')
        return redirect(request.url)

    return render_template('admin/create_user.html', roles=roles, password_msg=password_msg)


@admin_bp.route('/list_users')
def list_users():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'admin':
        flash('Access denied')
        return redirect(url_for('index'))

    users = User.query.all()
    return render_template('admin/list_users.html', users=users)


@admin_bp.route('/edit_user/<user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user_id' not in session or session.get('user_role', '').lower() != 'admin':
        flash('Access denied')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_email = request.form.get('email')
        if user.role.lower() == 'admin' and user.email != new_email:
            password = request.form.get('password')
            if not password or not user.check_password(password):
                flash('Incorrect password required to change email')
                return redirect(request.url)

        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.email = new_email
        if user.role.lower() != 'admin':
            user.role = request.form.get('role')
        user.is_active = request.form.get('is_active') == 'on'

        db.session.commit()
        flash('User updated successfully')
        return redirect(url_for('admin.list_users'))

    if user.role.lower() == 'admin':
        roles = ['Admin', 'Teacher', 'Parent', 'Secretary', 'HeadTeacher', 'Bursar']
    else:
        roles = ['Teacher', 'Parent', 'Secretary', 'HeadTeacher', 'Bursar']

    return render_template('admin/edit_user.html', user=user, roles=roles)


@admin_bp.route('/update_password/<user_id>', methods=['GET', 'POST'])
def update_password(user_id):
    if 'user_id' not in session or session.get('user_role', '').lower() != 'admin':
        flash('Access denied')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        if not new_password or len(new_password) < 6:
            flash('Password must be at least 6 characters')
            return redirect(request.url)

        user.set_password(new_password)
        db.session.commit()
        flash('Password updated successfully')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/update_password.html', user=user)


@admin_bp.route('/delete_user/<user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session.get('user_role', '').lower() != 'admin':
        flash('Access denied')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)

    if user.role.lower() == 'admin':
        flash('Cannot delete admin users')
        return redirect(url_for('admin.list_users'))

    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully')
    return redirect(url_for('admin.list_users'))
