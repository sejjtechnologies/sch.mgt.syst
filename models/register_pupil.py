from datetime import datetime
import uuid

from . import db


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
            'stream': self.stream,
            'previous_school': self.previous_school,
            'admission_date': self.admission_date.isoformat() if self.admission_date else None,
            'roll_number': self.roll_number,
            'admission_number': self.admission_number,
            'enrollment_status': self.enrollment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
