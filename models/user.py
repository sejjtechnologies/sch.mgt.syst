from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from email_validator import validate_email, EmailNotValidError
from datetime import datetime
import uuid

db = SQLAlchemy()


class User(db.Model):
    """User model for storing user accounts with roles and authentication"""

    __tablename__ = 'users'

    # Primary key
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # User information
    first_name = db.Column(db.String(100), nullable=False, index=True)
    last_name = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Role (admin, teacher, staff, etc.)
    role = db.Column(db.String(50), nullable=False, default='staff', index=True)

    # Status and metadata
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

    def set_password(self, password):
        """
        Hash and set the user password using Werkzeug
        
        Args:
            password (str): Plain text password
        
        Returns:
            bool: True if password was set successfully
        """
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long")

        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        return True

    def check_password(self, password):
        """
        Verify a password against the stored hash
        
        Args:
            password (str): Plain text password to verify
        
        Returns:
            bool: True if password matches, False otherwise
        """
        if not password:
            return False
        return check_password_hash(self.password_hash, password)

    def validate_email(self):
        """
        Validate email format using email_validator
        
        Returns:
            bool: True if email is valid
        
        Raises:
            EmailNotValidError: If email is invalid
        """
        try:
            # Validate and normalize the email address
            valid = validate_email(self.email, check_deliverability=False)
            self.email = valid.email
            return True
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email address: {str(e)}")

    def get_full_name(self):
        """Get the user's full name"""
        return f"{self.first_name} {self.last_name}".strip()

    def to_dict(self):
        """Convert user to dictionary (for JSON responses)"""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }


# Role constants
class UserRoles:
    """Constants for user roles"""
    ADMIN = 'admin'
    TEACHER = 'teacher'
    STAFF = 'staff'
    PRINCIPAL = 'principal'

    CHOICES = [
        (ADMIN, 'Administrator'),
        (TEACHER, 'Teacher'),
        (STAFF, 'Staff'),
        (PRINCIPAL, 'Principal'),
    ]
