import os
import zipfile
from flask import Flask, jsonify, render_template, send_from_directory, request, session
from flask_migrate import Migrate
from sqlalchemy import text
from models import db
from dotenv import load_dotenv  # <-- Added
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

# ---------------------------------------------------------------------------
# Load environment variables from .env
# ---------------------------------------------------------------------------
load_dotenv()  # <-- Load .env automatically

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

# Check if system is configured
SYSTEM_CONFIGURED = bool(DATABASE_URL)

if not SYSTEM_CONFIGURED:
    print("⚠️  System not configured - showing setup prompts")
    # Don't raise error - let the app show setup prompts instead

# ---------------------------------------------------------------------------
# Flask app setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = SECRET_KEY

if SYSTEM_CONFIGURED:
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Serverless-safe SQLAlchemy options (NO fixed pool sizes)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
    }

    # Initialize database & migrations
    db.init_app(app)
    migrate = Migrate(app, db)
else:
    # System not configured - skip database initialization
    print("⚠️  Skipping database initialization - system not configured")

# ---------------------------------------------------------------------------
# Register blueprints
# ---------------------------------------------------------------------------

if SYSTEM_CONFIGURED:
    try:
        from routes.user_routes import user_bp
        app.register_blueprint(user_bp)
    except Exception as e:
        print(f"⚠ Could not register user routes: {e}")

    try:
        from routes.secretary_routes import secretary_bp
        app.register_blueprint(secretary_bp)
    except Exception as e:
        print(f"⚠ Could not register secretary routes: {e}")

    try:
        from routes.admin_routes import admin_bp
        app.register_blueprint(admin_bp)
    except Exception as e:
        print(f"⚠ Could not register admin routes: {e}")

    try:
        from routes.headteacher_routes import headteacher_bp
        app.register_blueprint(headteacher_bp)
    except Exception as e:
        print(f"⚠ Could not register headteacher routes: {e}")

    try:
        from routes.teacher_routes import teacher_bp
        app.register_blueprint(teacher_bp)
    except Exception as e:
        print(f"⚠ Could not register teacher routes: {e}")

    try:
        from routes.bursar_routes import bursar_bp
        app.register_blueprint(bursar_bp)
    except Exception as e:
        print(f"⚠ Could not register bursar routes: {e}")

    try:
        from routes.parent_routes import parent_bp
        app.register_blueprint(parent_bp)
    except Exception as e:
        print(f"⚠ Could not register parent routes: {e}")
else:
    print("⚠️  Skipping blueprint registration - system not configured")

# ---------------------------------------------------------------------------
# Automatic Backup System
# ---------------------------------------------------------------------------

def model_to_dict(model_instance):
    """Convert a SQLAlchemy model instance to a dictionary"""
    result = {}
    for column in model_instance.__table__.columns:
        value = getattr(model_instance, column.name)
        # Convert datetime objects to strings
        if hasattr(value, 'isoformat'):
            value = value.isoformat()
        result[column.name] = value
    return result

def create_automatic_backup():
    """Create an automatic backup according to schedule"""
    if not SYSTEM_CONFIGURED:
        print("⚠️  Skipping automatic backup - system not configured")
        return

    try:
        from models.system_settings import SystemSetting
        from models.user import User
        from models.register_pupil import Pupil
        from models.bursar import BursarSettings, FeeCategory, FeeStructure, StudentFee, Payment, PaymentMethod
        from models.school_class import SchoolClass
        from models.stream import Stream
        from models.teacher_assignment import TeacherAssignment
        from models.attendance import Attendance
        from datetime import datetime
        import json
        import os

        print("🔄 Starting automatic backup...")

        # Create backups directory if it doesn't exist
        backup_dir = os.path.join(os.getcwd(), 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'auto_backup_{timestamp}.zip'
        backup_path = os.path.join(backup_dir, backup_filename)

        # Create zip file containing database data and important files
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:

            # Export all database data as JSON
            data_backup = {
                'backup_info': {
                    'timestamp': timestamp,
                    'type': 'automatic',
                    'version': '1.0'
                },
                'users': [model_to_dict(user) for user in User.query.all()],
                'pupils': [model_to_dict(pupil) for pupil in Pupil.query.all()],
                'school_classes': [model_to_dict(cls) for cls in SchoolClass.query.all()],
                'streams': [model_to_dict(stream) for stream in Stream.query.all()],
                'teacher_assignments': [model_to_dict(ta) for ta in TeacherAssignment.query.all()],
                'attendances': [model_to_dict(att) for att in Attendance.query.all()],
                'bursar_settings': [model_to_dict(bs) for bs in BursarSettings.query.all()],
                'fee_categories': [model_to_dict(fc) for fc in FeeCategory.query.all()],
                'fee_structures': [model_to_dict(fs) for fs in FeeStructure.query.all()],
                'student_fees': [model_to_dict(sf) for sf in StudentFee.query.all()],
                'payments': [model_to_dict(payment) for payment in Payment.query.all()],
                'payment_methods': [model_to_dict(pm) for pm in PaymentMethod.query.all()],
                'system_settings': [model_to_dict(ss) for ss in SystemSetting.query.all()]
            }

            # Write data to JSON file in zip
            zipf.writestr('database_data.json', json.dumps(data_backup, indent=2, default=str))

            # Add database file if using SQLite (as additional backup)
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
            readme_content = f"""School Management System - Automatic Backup
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Type: Automatic Scheduled Backup

This backup contains:
- Complete database data export (JSON format)
- Database file (if SQLite)
- Migration files
- Uploaded files and documents

Data includes:
- User accounts and profiles
- Pupil records and information
- School classes and streams
- Teacher assignments
- Attendance records
- Bursar settings and fee structures
- Payment records and methods
- System settings and configuration

To restore this backup, use the restore functionality in the admin panel.
"""

            zipf.writestr('README.txt', readme_content)

        print(f"✅ Automatic backup completed: {backup_filename} ({os.path.getsize(backup_path)} bytes)")

        # Clean up old automatic backups (keep only last 10)
        try:
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith('auto_backup_') and f.endswith('.zip')]
            backup_files.sort(key=lambda x: os.path.getctime(os.path.join(backup_dir, x)), reverse=True)

            if len(backup_files) > 10:
                for old_file in backup_files[10:]:
                    old_path = os.path.join(backup_dir, old_file)
                    os.remove(old_path)
                    print(f"🗑️  Cleaned up old automatic backup: {old_file}")

        except Exception as e:
            print(f"⚠️  Error cleaning up old backups: {e}")

    except Exception as e:
        print(f"❌ Error creating automatic backup: {e}")

# Global scheduler instance
backup_scheduler = None

def scheduled_backup():
    """Wrapper function to run backup with app context"""
    with app.app_context():
        create_automatic_backup()

# Global scheduler instance
backup_scheduler = None

def setup_backup_scheduler():
    """Setup the automatic backup scheduler"""
    global backup_scheduler

    if not SYSTEM_CONFIGURED:
        print("⚠️  Skipping backup scheduler setup - system not configured")
        return

    try:
        from utils.settings import SystemSettings

        # Check if automatic backups are enabled
        auto_backup_enabled = SystemSettings.get('backups', 'enabled', True)
        if not auto_backup_enabled:
            # If backups are disabled, remove any existing jobs
            if backup_scheduler:
                try:
                    backup_scheduler.remove_job('daily_backup')
                except:
                    pass
                try:
                    backup_scheduler.remove_job('weekly_backup')
                except:
                    pass
                try:
                    backup_scheduler.remove_job('monthly_backup')
                except:
                    pass
                print("⚠️  Automatic backups disabled - removed scheduled jobs")
            return

        # Create scheduler if it doesn't exist
        if backup_scheduler is None:
            backup_scheduler = BackgroundScheduler()
            backup_scheduler.start()
            print("✅ Automatic backup scheduler initialized")

        # Remove existing jobs before adding new ones
        try:
            backup_scheduler.remove_job('daily_backup')
        except:
            pass
        try:
            backup_scheduler.remove_job('weekly_backup')
        except:
            pass
        try:
            backup_scheduler.remove_job('monthly_backup')
        except:
            pass

        # Get backup settings
        backup_frequency = SystemSettings.get('backups', 'frequency', 'weekly')
        backup_time = SystemSettings.get('backups', 'time', '02:00')

        # Parse time
        try:
            hour, minute = map(int, backup_time.split(':'))
        except:
            hour, minute = 2, 0  # Default to 2:00 AM

        # Schedule based on frequency
        if backup_frequency == 'daily':
            backup_scheduler.add_job(
                func=scheduled_backup,
                trigger=CronTrigger(hour=hour, minute=minute),
                id='daily_backup',
                name='Daily Automatic Backup',
                replace_existing=True
            )
            print(f"📅 Daily automatic backup scheduled for {hour:02d}:{minute:02d}")

        elif backup_frequency == 'weekly':
            backup_scheduler.add_job(
                func=scheduled_backup,
                trigger=CronTrigger(day_of_week='sun', hour=hour, minute=minute),
                id='weekly_backup',
                name='Weekly Automatic Backup',
                replace_existing=True
            )
            print(f"📅 Weekly automatic backup scheduled for Sunday {hour:02d}:{minute:02d}")

        elif backup_frequency == 'monthly':
            backup_scheduler.add_job(
                func=scheduled_backup,
                trigger=CronTrigger(day=1, hour=hour, minute=minute),
                id='monthly_backup',
                name='Monthly Automatic Backup',
                replace_existing=True
            )
            print(f"📅 Monthly automatic backup scheduled for 1st of month {hour:02d}:{minute:02d}")

    except Exception as e:
        print(f"❌ Error setting up backup scheduler: {e}")

# Initialize backup scheduler if system is configured
if SYSTEM_CONFIGURED:
    with app.app_context():
        setup_backup_scheduler()

# ---------------------------------------------------------------------------
# Context processors for global template variables
# ---------------------------------------------------------------------------

@app.context_processor
def inject_system_settings():
    """Make system settings available in all templates"""
    print(f"DEBUG: Context processor called for request to {request.path}")
    if SYSTEM_CONFIGURED:
        try:
            from models.system_settings import SystemSetting
            # Load settings directly from database
            school_name_setting = SystemSetting.query.filter_by(category='general', key='school_name', is_active=True).first()
            abbr_name_setting = SystemSetting.query.filter_by(category='general', key='abbreviated_school_name', is_active=True).first()
            school_address_setting = SystemSetting.query.filter_by(category='general', key='school_address', is_active=True).first()
            school_phone_setting = SystemSetting.query.filter_by(category='general', key='school_phone', is_active=True).first()
            school_email_setting = SystemSetting.query.filter_by(category='general', key='school_email', is_active=True).first()

            school_name = school_name_setting.typed_value if school_name_setting else ''
            abbr_name = abbr_name_setting.typed_value if abbr_name_setting else ''
            school_address = school_address_setting.typed_value if school_address_setting else ''
            school_phone = school_phone_setting.typed_value if school_phone_setting else ''
            school_email = school_email_setting.typed_value if school_email_setting else ''

            print(f"DEBUG: Loaded school_name='{school_name}', abbr_name='{abbr_name}'")

            settings = {
                'system_settings': {
                    'school_name': school_name,
                    'abbreviated_school_name': abbr_name,
                    'school_address': school_address,
                    'school_phone': school_phone,
                    'school_email': school_email,
                    # Add other settings as needed
                }
            }
            print(f"DEBUG: Returning settings: {settings['system_settings']['school_name']}")
            return settings
        except Exception as e:
            print(f"⚠ Could not load system settings: {e}")
            import traceback
            traceback.print_exc()
            return {'system_settings': {}}
    return {'system_settings': {}}


@app.before_request
def check_maintenance_mode():
    """Check if maintenance mode is enabled and block non-admin access"""
    if not SYSTEM_CONFIGURED:
        return  # Skip for unconfigured systems

    # Skip maintenance check for static files, service worker, debug routes, login, logout, and admin routes
    if (request.path.startswith('/static/') or
        request.path.startswith('/admin/') or
        request.path in ['/sw.js', '/favicon.ico', '/debug', '/db-test', '/login', '/logout', '/']):
        return

    try:
        from utils.settings import SystemSettings
        maintenance_mode = SystemSettings.get_maintenance_mode()
        user_role = session.get('user_role', '').lower()
        print(f"DEBUG: Maintenance check - path: {request.path}, maintenance_mode: {maintenance_mode}, user_role: {user_role}")
        if maintenance_mode:
            # Allow admin users access to all routes, even in maintenance mode
            if user_role == 'admin':
                return
            # Block non-admin users
            maintenance_message = SystemSettings.get_maintenance_message()
            print(f"DEBUG: Blocking access for non-admin user")
            return render_template('maintenance.html', maintenance_message=maintenance_message)
    except Exception as e:
        print(f"⚠ Could not check maintenance mode: {e}")
        # If we can't check maintenance mode, allow access to prevent lockout

@app.route("/debug")
def debug():
    from utils.settings import SystemSettings
    return {
        "SYSTEM_CONFIGURED": SYSTEM_CONFIGURED,
        "DATABASE_URL_SET": bool(os.getenv("DATABASE_URL")),
        "SECRET_KEY_SET": bool(os.getenv("SECRET_KEY")),
        "DATABASE_URL_PREFIX": os.getenv("DATABASE_URL", "")[:20] + "..." if os.getenv("DATABASE_URL") else "Not set",
        "FLASK_ENV": os.getenv("FLASK_ENV", "Not set"),
        "VERCEL_ENV": os.getenv("VERCEL_ENV", "Not set"),
        "MAINTENANCE_MODE": SystemSettings.get_maintenance_mode(),
        "MAINTENANCE_MESSAGE": SystemSettings.get_maintenance_message(),
        "SESSION_USER_ROLE": session.get('user_role', 'Not set')
    }

@app.route("/")
def index():
    if not SYSTEM_CONFIGURED:
        # Show setup/installation page for unconfigured systems
        return render_template("setup.html")
    return render_template("index.html")


@app.route("/sw.js")
def service_worker():
    """Serve service worker from root"""
    try:
        return send_from_directory(app.root_path, "sw.js")
    except FileNotFoundError:
        return "Service worker not found", 404


@app.route("/favicon.ico")
def favicon():
    """Serve favicon to avoid 404s"""
    return send_from_directory(
        os.path.join(app.root_path, "static", "images"), "school_192.png"
    )


@app.route("/db-test")
def db_test():
    """Simple DB connectivity test"""
    if not SYSTEM_CONFIGURED:
        return jsonify({"db": "not_configured", "message": "Database not configured yet"}), 503

    try:
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
        return jsonify({"db": "connected", "test_result": int(result)})
    except Exception as e:
        return jsonify({"db": "error", "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Local development only
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5000
    print(f"Running on http://{host}:{port}/")
    app.run(host=host, port=port, debug=True)
