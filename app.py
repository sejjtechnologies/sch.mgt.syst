import os
from flask import Flask, jsonify, render_template, send_from_directory
from flask_migrate import Migrate
from sqlalchemy import text
from models import db
from dotenv import load_dotenv  # <-- Added

# ---------------------------------------------------------------------------
# Load environment variables from .env
# ---------------------------------------------------------------------------
load_dotenv()  # <-- Load .env automatically

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the environment")

# ---------------------------------------------------------------------------
# Flask app setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Serverless-safe SQLAlchemy options (NO fixed pool sizes)
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
}

# ---------------------------------------------------------------------------
# Initialize database & migrations
# ---------------------------------------------------------------------------

db.init_app(app)
migrate = Migrate(app, db)

# ---------------------------------------------------------------------------
# Register blueprints
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
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
