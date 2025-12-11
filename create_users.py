"""Create initial users in the database from `.env` configuration.

This script:
- loads DATABASE_URL from .env
- initializes Flask+SQLAlchemy
- creates tables (if missing)
- inserts a set of seed users (skips emails that already exist)

Run:
    venv/Scripts/Activate.ps1
    python create_users.py
"""

import os
from dotenv import load_dotenv
from flask import Flask

# load early
load_dotenv()

from models import db, User
from werkzeug.security import generate_password_hash

DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL not set in .env')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Seed users to create
SEED_USERS = [
    {"first_name": "Admin", "last_name": "Admin2", "email": "admin@gmail.com", "password": "admin", "role": "Admin", "is_active": True},
    {"first_name": "Teacher", "last_name": "User", "email": "teacher@gmail.com", "password": "teacher", "role": "Teacher", "is_active": True},
    {"first_name": "Parent", "last_name": "User", "email": "parent@gmail.com", "password": "parent", "role": "Parent", "is_active": True},
    {"first_name": "Secretary", "last_name": "User", "email": "secretary@gmail.com", "password": "secretary", "role": "Secretary", "is_active": True},
    {"first_name": "Bursar", "last_name": "User", "email": "bursar@gmail.com", "password": "bursar", "role": "Bursar", "is_active": True},
    {"first_name": "Head", "last_name": "Teacher", "email": "headteacher@gmail.com", "password": "headteacher", "role": "Headteacher", "is_active": True},
]


def main():
    db.init_app(app)
    with app.app_context():
        print('Creating tables (if not present)')
        db.create_all()

        created = []
        skipped = []
        for u in SEED_USERS:
            email = u['email'].lower()
            existing = User.query.filter_by(email=email).first()
            if existing:
                skipped.append(email)
                print(f"Skipping existing user: {email}")
                continue

            user = User(
                first_name=u['first_name'],
                last_name=u['last_name'],
                email=email,
                role=u['role'],
                is_active=bool(u.get('is_active', True)),
            )
            try:
                # Debug: show the raw password and length to diagnose failures
                try:
                    raw_pw = u['password']
                    print(f"Setting password for {email}: {repr(raw_pw)} (len={len(raw_pw)})")
                except Exception:
                    print(f"Setting password for {email}: <unreadable>")

                # Special-case: allow admin to use short password 'admin' by hashing directly
                if email == 'admin@gmail.com' and u.get('password') == 'admin':
                    user.password_hash = generate_password_hash('admin', method='pbkdf2:sha256')
                    print(f"Bypassed validation and set raw 'admin' password for {email}")
                else:
                    user.set_password(u['password'])
            except Exception as ex:
                print(f"Failed to set password for {email}: {ex}")
                continue

            try:
                user.validate_email()
            except Exception as ex:
                print(f"Invalid email for {email}: {ex}")
                continue

            db.session.add(user)
            created.append(email)

        try:
            db.session.commit()
        except Exception as ex:
            print(f"Failed to commit users: {ex}")
            db.session.rollback()

        print('\nSummary:')
        print(f'  Created: {len(created)} -> {created}')
        print(f'  Skipped: {len(skipped)} -> {skipped}')


if __name__ == '__main__':
    main()
