"""Seed default classes (P1-P7) and streams (RED, GREEN, BLUE, ORANGE).

Run with:

    python scripts/seed_defaults.py

This script is idempotent and will only create missing records.
"""
import sys
from pathlib import Path

# When this script is executed as `python scripts/seed_defaults.py` the
# interpreter's sys.path[0] is the `scripts/` directory, so `app` (at the
# project root) isn't importable. Add the project root to sys.path so
# imports work whether run from the project root or from other places.
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app import app
from models import db, Stream, SchoolClass


def seed():
    with app.app_context():
        created = {'streams': [], 'classes': []}

        # Streams
        for name in ['RED', 'GREEN', 'BLUE', 'ORANGE']:
            if not Stream.query.filter_by(name=name).first():
                s = Stream(name=name)
                db.session.add(s)
                created['streams'].append(name)

        # Classes P1..P7
        for i in range(1, 8):
            name = f'P{i}'
            if not SchoolClass.query.filter_by(name=name).first():
                c = SchoolClass(name=name, level=i)
                db.session.add(c)
                created['classes'].append(name)

        if created['streams'] or created['classes']:
            db.session.commit()

        print('Created streams:', created['streams'])
        print('Created classes:', created['classes'])
        print('Existing streams:', [s.name for s in Stream.query.order_by(Stream.name).all()])
        print('Existing classes:', [c.name for c in SchoolClass.query.order_by(SchoolClass.level).all()])


if __name__ == '__main__':
    seed()
