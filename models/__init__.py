from .user import User, UserRoles, db
from .register_pupil import Pupil
from .stream import Stream
from .school_class import SchoolClass
from .teacher_assignment import TeacherAssignment

__all__ = ['User', 'UserRoles', 'db', 'Pupil', 'Stream', 'SchoolClass', 'TeacherAssignment']
