#!/usr/bin/env python3
"""
Test script to verify pupil report template renders all grades correctly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template
from datetime import datetime

# Create a test Flask app
app = Flask(__name__)

def test_template_rendering():
    """Test that the template renders all grades correctly"""
    with app.app_context():
        # Sample marks data with all grade fields
        marks_data = [{
            'exam_type': 'Beginning of Term',
            'english': 79,
            'mathematics': 74,
            'science': 82,
            'social_studies': 80,
            'english_grade': 'B+',
            'mathematics_grade': 'B+',
            'science_grade': 'A',
            'social_studies_grade': 'A',
            'total': 315,
            'average': 78.8,
            'overall_grade': 'B+',
            'position': 1,
            'class_position': 1,
            'stream_student_count': 101,
            'class_student_count': 404,
            'english_remark': 'Very Good',
            'mathematics_remark': 'Very Good',
            'science_remark': 'Excellent',
            'social_studies_remark': 'Excellent',
            'remarks': 'Very good performance. Aim for excellence.'
        }]

        # Mock pupil object
        class MockPupil:
            def __init__(self):
                self.first_name = 'Mugisha'
                self.last_name = 'Kevin'
                self.admission_number = 'AD/2025/001'
                self.gender = 'Male'
                self.class_admitted = 1  # P1
                self.stream = 1  # BLUE

        pupil = MockPupil()

        try:
            # Render the template
            rendered_html = render_template(
                'teacher/pupil_report_template.html',
                pupil=pupil,
                report_type='term1_beginning',
                marks_data=marks_data,
                datetime=datetime,
                class_name='P1',
                stream_name='BLUE'
            )

            # Check if all grades are present in the rendered HTML
            grades_to_check = [
                'english_grade': 'B+',
                'mathematics_grade': 'B+',
                'science_grade': 'A',
                'social_studies_grade': 'A',
                'overall_grade': 'B+'
            ]

            print("Checking rendered HTML for grade visibility:")
            all_grades_found = True

            for grade_field, expected_value in grades_to_check.items():
                if expected_value in rendered_html:
                    print(f"✓ {grade_field}: {expected_value} found in HTML")
                else:
                    print(f"✗ {grade_field}: {expected_value} NOT found in HTML")
                    all_grades_found = False

            # Check for grade badge spans
            grade_badge_count = rendered_html.count('grade-badge')
            print(f"\nGrade badge spans found: {grade_badge_count}")

            if all_grades_found and grade_badge_count >= 5:  # 4 subjects + 1 overall
                print("\n✓ SUCCESS: All grades are present in the rendered template!")
                return True
            else:
                print(f"\n✗ FAILURE: Missing grades or insufficient grade badges (expected >=5, got {grade_badge_count})")
                return False

        except Exception as e:
            print(f"Error rendering template: {e}")
            return False

if __name__ == "__main__":
    success = test_template_rendering()
    sys.exit(0 if success else 1)