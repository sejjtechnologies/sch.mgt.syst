import os
from models import db
from app import app

# Test database connection
def test_db_connection():
    try:
        with app.app_context():
            # Try a simple query
            result = db.session.execute(db.text('SELECT 1 as test'))
            row = result.fetchone()
            print(f"✅ Database connection successful: {row[0]}")

            # Check if pupil_marks table exists
            result = db.session.execute(db.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pupil_marks');"))
            exists = result.fetchone()[0]
            print(f"✅ pupil_marks table exists: {exists}")

            if exists:
                # Check record count
                result = db.session.execute(db.text('SELECT COUNT(*) FROM pupil_marks;'))
                count = result.fetchone()[0]
                print(f"✅ Total records in pupil_marks: {count}")

                if count > 0:
                    # Show recent records
                    result = db.session.execute(db.text('SELECT id, pupil_id, term, exam_type, english, mathematics FROM pupil_marks ORDER BY created_at DESC LIMIT 2;'))
                    records = result.fetchall()
                    print("✅ Recent records:")
                    for record in records:
                        print(f"   ID: {record[0]}, Pupil: {record[1]}, Term: {record[2]}, Exam: {record[3]}, Eng: {record[4]}, Math: {record[5]}")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        return False

    return True

if __name__ == "__main__":
    print("🔍 Testing database connection...")
    success = test_db_connection()
    if success:
        print("🎉 All database tests passed!")
    else:
        print("💥 Database tests failed!")