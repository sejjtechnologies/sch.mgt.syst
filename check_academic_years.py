#!/usr/bin/env python3
"""
Script to connect to Neon database and display academic years data.
Loads environment variables from .env file.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def main():
    # Load environment variables from .env file
    load_dotenv()

    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment variables")
        print("Make sure you have a .env file with DATABASE_URL=postgresql://...")
        sys.exit(1)

    print(f"Connecting to database: {database_url[:50]}...")

    try:
        # Create engine
        engine = create_engine(database_url)

        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()

        # Query academic_years table
        print("\n=== ACADEMIC YEARS TABLE ===")

        # Check if table exists
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'academic_years'
            );
        """))

        table_exists = result.scalar()
        if not table_exists:
            print("❌ academic_years table does not exist")
            return

        # Get table structure
        print("\nTable structure:")
        result = session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'academic_years'
            ORDER BY ordinal_position;
        """))

        columns = result.fetchall()
        for col in columns:
            print(f"  - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")

        # Get all academic years
        print("\nAcademic Years Data:")
        result = session.execute(text("""
            SELECT id, name, start_year, end_year, is_active, created_at
            FROM academic_years
            ORDER BY name DESC;
        """))

        rows = result.fetchall()
        if not rows:
            print("📭 No academic years found in the table")
        else:
            print(f"📊 Found {len(rows)} academic year(s):")
            print("-" * 80)
            print(f"{'ID':<3} {'Name':<10} {'Start':<6} {'End':<6} {'Active':<7} {'Created'}")
            print("-" * 80)

            for row in rows:
                active = "✅" if row[4] else "❌"
                created = row[5].strftime("%Y-%m-%d") if row[5] else "N/A"
                print(f"{row[0]:<3} {row[1]:<10} {row[2] or 'N/A':<6} {row[3] or 'N/A':<6} {active:<7} {created}")

        # Check pupils table for academic_year_id usage
        print("\n=== PUPILS ACADEMIC YEAR USAGE ===")

        result = session.execute(text("""
            SELECT
                COUNT(*) as total_pupils,
                COUNT(CASE WHEN academic_year_id IS NOT NULL THEN 1 END) as with_academic_year,
                COUNT(CASE WHEN academic_year_id IS NULL THEN 1 END) as without_academic_year
            FROM pupils;
        """))

        stats = result.fetchone()
        print(f"Total pupils: {stats[0]}")
        print(f"Pupils with academic year: {stats[1]}")
        print(f"Pupils without academic year: {stats[2]}")

        # Show sample of pupils with academic years
        if stats[1] > 0:
            print("\nSample pupils with academic years:")
            result = session.execute(text("""
                SELECT p.first_name, p.last_name, ay.name as academic_year
                FROM pupils p
                LEFT JOIN academic_years ay ON p.academic_year_id = ay.id
                WHERE p.academic_year_id IS NOT NULL
                LIMIT 5;
            """))

            for row in result:
                print(f"  - {row[0]} {row[1]}: {row[2]}")

        print("\n✅ Database connection successful!")
        print("✅ Query completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    main()