from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from models.user import User, db
from models.bursar import BursarSettings
from models.system_settings import SystemSetting
from werkzeug.security import generate_password_hash
import os
import shutil
from datetime import datetime
import zipfile
from io import BytesIO

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

    # Count users by role
    role_counts = {}
    for user in users:
        role = user.role.lower()
        role_counts[role] = role_counts.get(role, 0) + 1

    return render_template('admin/list_users.html', users=users, role_counts=role_counts)


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


@admin_bp.route('/system_settings', methods=['GET', 'POST'])
def system_settings():
    if 'user_id' not in session or session.get('user_role', '').lower() != 'admin':
        flash('Access denied')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # General Settings
            school_name = request.form.get('school_name', '')
            abbreviated_school_name = request.form.get('abbreviated_school_name', '')
            currency = request.form.get('currency', 'KES')
            academic_year = request.form.get('academic_year', '')
            timezone = request.form.get('timezone', 'Africa/Nairobi')

            SystemSetting.upsert_setting('general', 'school_name', school_name)
            SystemSetting.upsert_setting('general', 'abbreviated_school_name', abbreviated_school_name)
            SystemSetting.upsert_setting('general', 'currency', currency)
            SystemSetting.upsert_setting('general', 'academic_year', academic_year)
            SystemSetting.upsert_setting('general', 'timezone', timezone)

            # Maintenance Mode
            maintenance_mode = request.form.get('maintenance_mode') == 'on'
            maintenance_message = request.form.get('maintenance_message', 'System is under maintenance. Please try again later.')

            SystemSetting.upsert_setting('system', 'maintenance_mode', maintenance_mode)
            SystemSetting.upsert_setting('system', 'maintenance_message', maintenance_message)

            # Backup Settings
            backup_frequency = request.form.get('backup_frequency', 'weekly')
            backup_time = request.form.get('backup_time', '02:00')

            SystemSetting.upsert_setting('backups', 'frequency', backup_frequency)
            SystemSetting.upsert_setting('backups', 'time', backup_time)

            # Log Settings
            log_level = request.form.get('log_level', 'INFO')
            log_retention = int(request.form.get('log_retention', 30))

            SystemSetting.upsert_setting('logs', 'level', log_level)
            SystemSetting.upsert_setting('logs', 'retention_days', log_retention)

            # Performance Settings
            cache_timeout = request.form.get('cache_enabled') == 'on'
            max_upload_size = int(request.form.get('max_upload_size', 10))

            SystemSetting.upsert_setting('performance', 'cache_enabled', cache_timeout)
            SystemSetting.upsert_setting('performance', 'upload_max_size', max_upload_size)

            # Security Settings
            force_https = request.form.get('force_https') == 'on'
            enable_cors = request.form.get('enable_cors') == 'on'

            SystemSetting.upsert_setting('security', 'https_enforced', force_https)
            SystemSetting.upsert_setting('security', 'cors_enabled', enable_cors)

            db.session.commit()
            # Invalidate settings cache
            from utils.settings import SystemSettings
            SystemSettings.invalidate_cache()
            flash('System settings updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating settings: {str(e)}', 'error')

        return redirect(url_for('admin.system_settings'))

    # Load current settings
    settings = {}
    all_settings = SystemSetting.query.filter_by(is_active=True).all()
    for setting in all_settings:
        settings[setting.key] = setting.typed_value

    # Fetch academic years for dropdown
    from models.register_pupil import AcademicYear
    academic_years = AcademicYear.query.order_by(AcademicYear.start_year.desc()).all()

    return render_template('admin/system_settings.html', settings=settings, academic_years=academic_years)


@admin_bp.route('/create_backup', methods=['POST'])
def create_backup():
    """Create a manual database backup"""
    if 'user_id' not in session or session.get('user_role', '').lower() != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    try:
        # Create backups directory if it doesn't exist
        backup_dir = os.path.join(os.getcwd(), 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.zip'
        backup_path = os.path.join(backup_dir, backup_filename)

        # Create zip file containing database and important files
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add database file if using SQLite
            db_url = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
            if db_url and 'sqlite' in db_url:
                db_path = db_url.replace('sqlite:///', '')
                if os.path.exists(db_path):
                    zipf.write(db_path, 'database.db')

            # Add migrations directory
            if os.path.exists('migrations'):
                for root, dirs, files in os.walk('migrations'):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.getcwd())
                        zipf.write(file_path, arcname)

            # Add instance directory (contains uploaded files, etc.)
            if os.path.exists('instance'):
                for root, dirs, files in os.walk('instance'):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.getcwd())
                        zipf.write(file_path, arcname)

            # Add a README file with backup info
            readme_content = f"""School Management System Backup
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Database: {'SQLite' if db_url and 'sqlite' in db_url else 'External Database'}

This backup contains:
- Database schema and data (if using SQLite)
- Migration files
- Uploaded files and documents

To restore:
1. Extract this zip file
2. If using SQLite, replace the database.db file
3. Run database migrations if needed
4. Restore any uploaded files to the instance directory
"""
            zipf.writestr('README.txt', readme_content)

        return jsonify({
            'success': True,
            'message': 'Backup created successfully',
            'filename': backup_filename,
            'size': os.path.getsize(backup_path)
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error creating backup: {str(e)}'}), 500


@admin_bp.route('/list_backups')
def list_backups():
    """List all available backups"""
    if 'user_id' not in session or session.get('user_role', '').lower() != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    try:
        backup_dir = os.path.join(os.getcwd(), 'backups')
        if not os.path.exists(backup_dir):
            return jsonify({'success': True, 'backups': []})

        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.zip'):
                file_path = os.path.join(backup_dir, filename)
                stat = os.stat(file_path)
                backups.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                    'size_formatted': f"{stat.st_size / (1024*1024):.2f} MB"
                })

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)

        return jsonify({'success': True, 'backups': backups})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error listing backups: {str(e)}'}), 500


@admin_bp.route('/download_backup/<filename>')
def download_backup(filename):
    """Download a specific backup file"""
    if 'user_id' not in session or session.get('user_role', '').lower() != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    try:
        backup_dir = os.path.join(os.getcwd(), 'backups')
        file_path = os.path.join(backup_dir, filename)

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Backup file not found'}), 404

        return send_file(file_path, as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error downloading backup: {str(e)}'}), 500


@admin_bp.route('/delete_backup/<filename>', methods=['DELETE'])
def delete_backup(filename):
    """Delete a specific backup file"""
    if 'user_id' not in session or session.get('user_role', '').lower() != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    try:
        backup_dir = os.path.join(os.getcwd(), 'backups')
        file_path = os.path.join(backup_dir, filename)

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Backup file not found'}), 404

        os.remove(file_path)

        return jsonify({'success': True, 'message': 'Backup deleted successfully'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting backup: {str(e)}'}), 500
