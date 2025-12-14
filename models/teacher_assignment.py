from datetime import datetime
import uuid

from . import db


class TeacherAssignment(db.Model):
    """Model for storing teacher assignments to classes and streams"""

    __tablename__ = 'teacher_assignments'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign keys
    teacher_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    class_id = db.Column(db.String(36), db.ForeignKey('classes.id'), nullable=False, index=True)
    stream_id = db.Column(db.String(36), db.ForeignKey('streams.id'), nullable=False, index=True)

    # Assignment details
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teacher = db.relationship('User', backref=db.backref('assignments', lazy=True))
    school_class = db.relationship('SchoolClass', backref=db.backref('assignments', lazy=True))
    stream = db.relationship('Stream', backref=db.backref('assignments', lazy=True))

    def __repr__(self):
        return f"<TeacherAssignment teacher={self.teacher_id} class={self.class_id} stream={self.stream_id}>"

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'class_id': self.class_id,
            'stream_id': self.stream_id,
            'assigned_date': self.assigned_date.isoformat() if self.assigned_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }