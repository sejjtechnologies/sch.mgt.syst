from datetime import datetime
import uuid

from . import db


class AcademicYear(db.Model):
    """Academic year model for storing academic year periods"""

    __tablename__ = 'academic_years'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(16), nullable=False, unique=True)  # e.g. '2025/26'
    start_year = db.Column(db.Integer, nullable=True)
    end_year = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AcademicYear {self.name}>"


class Pupil(db.Model):
    """Pupil model for secretary registration form

    Fields mirror the inputs in `templates/secretary/register_pupils.html`.
    """

    __tablename__ = 'pupils'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Basic info
    first_name = db.Column(db.String(120), nullable=False, index=True)
    last_name = db.Column(db.String(120), nullable=False, index=True)
    gender = db.Column(db.String(20), nullable=True, index=True)
    dob = db.Column(db.Date, nullable=True)
    nationality = db.Column(db.String(80), nullable=True, index=True)

    # Address split
    village = db.Column(db.String(255), nullable=True)
    subcounty = db.Column(db.String(255), nullable=True)
    district = db.Column(db.String(255), nullable=True)
    religion = db.Column(db.String(80), nullable=True)

    # Guardian
    guardian_first = db.Column(db.String(120), nullable=True)
    guardian_last = db.Column(db.String(120), nullable=True)
    guardian_phone = db.Column(db.String(30), nullable=True)
    guardian_relationship = db.Column(db.String(80), nullable=True)
    guardian_occupation = db.Column(db.String(120), nullable=True)

    # Admission
    class_admitted = db.Column(db.String(80), nullable=True, index=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=True, index=True)
    stream = db.Column(db.String(120), nullable=True, index=True)
    previous_school = db.Column(db.String(255), nullable=True)
    admission_date = db.Column(db.Date, nullable=True)

    # System-generated identifiers
    roll_number = db.Column(db.String(60), unique=True, nullable=True, index=True)
    admission_number = db.Column(db.String(60), unique=True, nullable=True, index=True)
    enrollment_status = db.Column(db.String(30), nullable=True, default='active')

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    academic_year = db.relationship('AcademicYear', backref='pupils')

    def __repr__(self):
        return f"<Pupil {self.first_name} {self.last_name} ({self.admission_number or 'no-adm'})>"

    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'gender': self.gender,
            'dob': self.dob.isoformat() if self.dob else None,
            'nationality': self.nationality,
            'village': self.village,
            'subcounty': self.subcounty,
            'district': self.district,
            'religion': self.religion,
            'guardian_first': self.guardian_first,
            'guardian_last': self.guardian_last,
            'guardian_phone': self.guardian_phone,
            'guardian_relationship': self.guardian_relationship,
            'guardian_occupation': self.guardian_occupation,
            'class_admitted': self.class_admitted,
            'academic_year': self.academic_year.name if self.academic_year else None,
            'stream': self.stream,
            'previous_school': self.previous_school,
            'admission_date': self.admission_date.isoformat() if self.admission_date else None,
            'roll_number': self.roll_number,
            'admission_number': self.admission_number,
            'enrollment_status': self.enrollment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PupilMarks(db.Model):
    """Pupil marks model for storing examination results"""

    __tablename__ = 'pupil_marks'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.String(36), db.ForeignKey('pupils.id'), nullable=False, index=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False, index=True)

    # Exam details
    term = db.Column(db.Integer, nullable=False)  # 1, 2, or 3
    exam_type = db.Column(db.String(50), nullable=False)  # 'Beginning of term', 'Mid_term', 'End of term'

    # Subject marks (out of 100 each)
    english = db.Column(db.Integer, nullable=True)
    mathematics = db.Column(db.Integer, nullable=True)
    science = db.Column(db.Integer, nullable=True)
    social_studies = db.Column(db.Integer, nullable=True)

    # Calculated fields
    total_marks = db.Column(db.Integer, nullable=True)  # Sum of all subjects (max 400)
    average = db.Column(db.Float, nullable=True)  # Average percentage
    position_in_stream = db.Column(db.Integer, nullable=True)  # Position in stream
    position_in_class = db.Column(db.Integer, nullable=True)  # Position in whole class
    stream_student_count = db.Column(db.Integer, nullable=True)  # Total students in stream
    class_student_count = db.Column(db.Integer, nullable=True)  # Total students in class

    # Remarks
    english_remark = db.Column(db.String(255), nullable=True)
    mathematics_remark = db.Column(db.String(255), nullable=True)
    science_remark = db.Column(db.String(255), nullable=True)
    social_studies_remark = db.Column(db.String(255), nullable=True)
    general_comment = db.Column(db.Text, nullable=True)

    # Grades (calculated and stored)
    english_grade = db.Column(db.String(5), nullable=True)
    mathematics_grade = db.Column(db.String(5), nullable=True)
    science_grade = db.Column(db.String(5), nullable=True)
    social_studies_grade = db.Column(db.String(5), nullable=True)
    overall_grade = db.Column(db.String(5), nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pupil = db.relationship('Pupil', backref='marks')
    academic_year = db.relationship('AcademicYear', backref='marks')

    def __repr__(self):
        return f"<PupilMarks {self.pupil_id} Term{self.term} {self.exam_type}>"

    def calculate_totals(self):
        """Calculate total marks and average"""
        subjects = [self.english, self.mathematics, self.science, self.social_studies]
        valid_marks = [mark for mark in subjects if mark is not None]

        if valid_marks:
            self.total_marks = sum(valid_marks)
            self.average = round(sum(valid_marks) / len(valid_marks), 2)
        else:
            self.total_marks = None
            self.average = None

    def calculate_grades(self):
        """Calculate and store grades for each subject and overall"""
        def get_grade(mark):
            if mark is None:
                return None
            elif mark >= 80:
                return 'A'
            elif mark >= 70:
                return 'B+'
            elif mark >= 65:
                return 'B'
            elif mark >= 60:
                return 'C+'
            elif mark >= 55:
                return 'C'
            elif mark >= 50:
                return 'D+'
            elif mark >= 45:
                return 'D'
            elif mark >= 40:
                return 'E'
            else:
                return 'F'

        def get_overall_grade(average):
            if average is None:
                return None
            elif average >= 80:
                return 'A'
            elif average >= 70:
                return 'B+'
            elif average >= 65:
                return 'B'
            elif average >= 60:
                return 'C+'
            elif average >= 55:
                return 'C'
            elif average >= 50:
                return 'D+'
            elif average >= 45:
                return 'D'
            elif average >= 40:
                return 'E'
            else:
                return 'F'

        # Calculate individual subject grades
        self.english_grade = get_grade(self.english)
        self.mathematics_grade = get_grade(self.mathematics)
        self.science_grade = get_grade(self.science)
        self.social_studies_grade = get_grade(self.social_studies)

        # Calculate overall grade based on average
        self.overall_grade = get_overall_grade(self.average)

    def generate_remarks(self):
        """Generate remarks based on marks"""
        def get_remark(mark):
            if mark is None:
                return None
            elif mark >= 80:
                return "Excellent"
            elif mark >= 70:
                return "Very Good"
            elif mark >= 60:
                return "Good"
            elif mark >= 50:
                return "Fair"
            elif mark >= 40:
                return "Poor"
            else:
                return "Very Poor"

        self.english_remark = get_remark(self.english)
        self.mathematics_remark = get_remark(self.mathematics)
        self.science_remark = get_remark(self.science)
        self.social_studies_remark = get_remark(self.social_studies)

        # General comment based on average
        if self.average is not None:
            if self.average >= 80:
                self.general_comment = "Outstanding performance. Keep it up!"
            elif self.average >= 70:
                self.general_comment = "Very good performance. Aim for excellence."
            elif self.average >= 60:
                self.general_comment = "Good performance. Room for improvement."
            elif self.average >= 50:
                self.general_comment = "Fair performance. Need to work harder."
            else:
                self.general_comment = "Poor performance. Significant improvement needed."
        else:
            self.general_comment = None
