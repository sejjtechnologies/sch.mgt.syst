from dotenv import load_dotenv
import os
from flask import Flask

load_dotenv()
from models import db, User

DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL not set')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

with app.app_context():
    db.init_app(app)
    # Ensure tables are available
    try:
        users = User.query.all()
        print(f"Users found: {len(users)}")
        for u in users:
            print(f"- {u.email} | {u.role} | active={u.is_active}")
    except Exception as e:
        print('Error querying users:', e)
