from datetime import datetime
from . import db


class Attendance(db.Model):
    """Attendance model for tracking daily pupil attendance"""

    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.String(36), db.ForeignKey('pupils.id'), nullable=False, index=True)
    class_id = db.Column(db.String(80), nullable=False, index=True)
    stream_id = db.Column(db.String(120), nullable=False, index=True)
    attendance_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)  # 'present', 'absent'
    teacher_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pupil = db.relationship('Pupil', backref='attendance_records')
    teacher = db.relationship('User', backref='attendance_records')
    academic_year = db.relationship('AcademicYear', backref='attendance_records')

    # Constraints
    __table_args__ = (
        db.UniqueConstraint('pupil_id', 'attendance_date', name='unique_pupil_date_attendance'),
    )

    def __repr__(self):
        return f"<Attendance {self.pupil_id} on {self.attendance_date}: {self.status}>"