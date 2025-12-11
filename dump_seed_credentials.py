"""Print seeded role emails and raw passwords for debugging.

This script reads the `SEED_USERS` constant from `create_users.py` and prints
email, role and the raw password used during seeding. It does NOT read from the
database (which stores hashed passwords).

Run with the project venv Python:

    venv\Scripts\Activate.ps1
    python dump_seed_credentials.py
"""

from pprint import pprint

try:
    from create_users import SEED_USERS
except Exception as e:
    print("Failed to import SEED_USERS from create_users.py:", e)
    SEED_USERS = []

if not SEED_USERS:
    print("No seed users found (SEED_USERS is empty).")
else:
    print("Seeded credentials (email | role | raw_password):")
    for u in SEED_USERS:
        email = u.get('email')
        role = u.get('role')
        pwd = u.get('password')
        print(f"- {email} | {role} | {pwd}")

# Helpful hint: if admin isn't logging in, ensure the password listed here
# matches what you typed in the login form and that the account exists in DB.
