import os
from flask import Flask, jsonify, render_template
from sqlalchemy import text
from dotenv import load_dotenv
from models import db, User

# Load .env
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Configure SQLAlchemy engine options for connection pooling
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_pre_ping': True,
}

# Keep Werkzeug access logs visible at INFO so startup banner appears
import logging
logging.getLogger('werkzeug').setLevel(logging.INFO)

if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL is not set in the environment. Check your .env')

# Initialize database
db.init_app(app)

# Register routes (blueprints)
try:
    from routes.user_routes import user_bp
    app.register_blueprint(user_bp)
    # user routes registered
except Exception as e:
    print(f"⚠ Could not register user routes: {e}")

try:
    from routes.secretary_routes import secretary_bp
    app.register_blueprint(secretary_bp)
    # secretary routes registered
except Exception as e:
    print(f"⚠ Could not register secretary routes: {e}")

# Create tables for all models when the app starts, but avoid running twice with the
# Flask reloader (WERKZEUG_RUN_MAIN). Only run on the reloader main process or when
# not in debug mode.
import os
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    with app.app_context():
        try:
            db.create_all()
            print("✓ Database tables created successfully")
        except Exception as e:
            print(f"⚠ Warning: Could not create tables: {e}")



@app.route('/')
def index():
    return render_template('index.html')


# Optional: respond to service-worker requests to avoid 404 spam for /sw.js
@app.route('/sw.js')
def service_worker():
    # Return empty 204 (no content); replace with actual service worker file if used
    return ('', 204)


@app.route('/db-test')
def db_test():
    try:
        # Lightweight health check using SQLAlchemy session via Flask-SQLAlchemy
        with db.engine.connect() as conn:
            result = conn.execute(text('SELECT 1')).scalar()
        return jsonify({'db': 'connected', 'test_result': int(result)})
    except Exception as e:
        return jsonify({'db': 'error', 'error': str(e)}), 500


if __name__ == '__main__':
    # Use Flask's built-in server for quick testing only
    host = '127.0.0.1'
    port = 5000
    print(f"Running on http://{host}:{port}/")
    app.run(host=host, port=port, debug=True)
