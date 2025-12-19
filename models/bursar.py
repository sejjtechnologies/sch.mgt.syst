from models import db
from datetime import datetime

class FeeCategory(db.Model):
    """Fee categories like tuition, transport, meals, etc."""
    __tablename__ = 'fee_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with fee structures
    fee_structures = db.relationship('FeeStructure', backref='category', lazy=True)

    def __repr__(self):
        return f'<FeeCategory {self.name}>'


class Term(db.Model):
    """Academic terms"""
    __tablename__ = 'terms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    term_number = db.Column(db.Integer, nullable=False, unique=True)  # 1, 2, 3
    description = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Term {self.name}>'


class FeeStructure(db.Model):
    """Fee structure defining amounts per class and category"""
    __tablename__ = 'fee_structures'

    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)
    class_id = db.Column(db.String(36), db.ForeignKey('classes.id'), nullable=False)
    stream_id = db.Column(db.String(36), db.ForeignKey('streams.id'), nullable=False)
    fee_category_id = db.Column(db.Integer, db.ForeignKey('fee_categories.id'), nullable=False)

    # Fee amounts
    term1_amount = db.Column(db.Float, nullable=False, default=0.0)
    term2_amount = db.Column(db.Float, nullable=False, default=0.0)
    term3_amount = db.Column(db.Float, nullable=False, default=0.0)
    annual_amount = db.Column(db.Float, nullable=False, default=0.0)  # Total annual fee

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    academic_year = db.relationship('AcademicYear', backref='fee_structures')
    school_class = db.relationship('SchoolClass', backref='fee_structures')
    stream = db.relationship('Stream', backref='fee_structures')

    def __repr__(self):
        return f'<FeeStructure {self.school_class.name} - {self.category.name}>'


class StudentFee(db.Model):
    """Fees assigned to individual students"""
    __tablename__ = 'student_fees'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.String(36), db.ForeignKey('pupils.id'), nullable=False)
    fee_structure_id = db.Column(db.Integer, db.ForeignKey('fee_structures.id'), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)

    # Fee status per term
    term1_assigned = db.Column(db.Boolean, default=False)
    term2_assigned = db.Column(db.Boolean, default=False)
    term3_assigned = db.Column(db.Boolean, default=False)

    # Exemptions/discounts
    term1_exemption = db.Column(db.Float, default=0.0)
    term2_exemption = db.Column(db.Float, default=0.0)
    term3_exemption = db.Column(db.Float, default=0.0)
    exemption_reason = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pupil = db.relationship('Pupil', backref='student_fees')
    fee_structure = db.relationship('FeeStructure', backref='student_fees')

    def __repr__(self):
        return f'<StudentFee {self.pupil.first_name} {self.pupil.last_name}>'


class Payment(db.Model):
    """Payment records"""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.String(36), db.ForeignKey('pupils.id'), nullable=False)
    student_fee_id = db.Column(db.Integer, db.ForeignKey('student_fees.id'), nullable=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)

    # Payment details
    amount = db.Column(db.Float, nullable=False)
    term = db.Column(db.Integer, nullable=False)  # 1, 2, or 3
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # cash, bank_transfer, mobile_money, etc.

    # Additional info
    receipt_number = db.Column(db.String(50), unique=True, nullable=True)
    transaction_reference = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Recorded by
    recorded_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    pupil = db.relationship('Pupil', backref='payments')
    student_fee = db.relationship('StudentFee', backref='payments')
    academic_year = db.relationship('AcademicYear', backref='payments')
    recorder = db.relationship('User', backref='recorded_payments')

    def __repr__(self):
        return f'<Payment {self.pupil.first_name} {self.pupil.last_name} - {self.amount}>'


class PaymentMethod(db.Model):
    """Available payment methods"""
    __tablename__ = 'payment_methods'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PaymentMethod {self.name}>'


class BursarSettings(db.Model):
    """Bursar system settings"""
    __tablename__ = 'bursar_settings'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # 'general', 'notifications', 'security', 'reports'
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, nullable=True)
    value_type = db.Column(db.String(20), nullable=False, default='string')  # 'string', 'boolean', 'integer', 'float'
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Ensure unique combination of category and key
    __table_args__ = (db.UniqueConstraint('category', 'key', name='unique_category_key'),)

    def __repr__(self):
        return f'<BursarSettings {self.category}.{self.key} = {self.value}>'

    @property
    def typed_value(self):
        """Return the value converted to its proper type"""
        if self.value_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == 'integer':
            try:
                return int(self.value)
            except (ValueError, TypeError):
                return 0
        elif self.value_type == 'float':
            try:
                return float(self.value)
            except (ValueError, TypeError):
                return 0.0
        else:
            return self.value

    @typed_value.setter
    def typed_value(self, val):
        """Set the value and update value_type accordingly"""
        if isinstance(val, bool):
            self.value_type = 'boolean'
            self.value = 'true' if val else 'false'
        elif isinstance(val, int):
            self.value_type = 'integer'
            self.value = str(val)
        elif isinstance(val, float):
            self.value_type = 'float'
            self.value = str(val)
        else:
            self.value_type = 'string'
            self.value = str(val) if val is not None else None

    @staticmethod
    def upsert_setting(category, key, value, description=None):
        """Insert or update a setting"""
        setting = BursarSettings.query.filter_by(category=category, key=key).first()
        if setting:
            setting.typed_value = value
            if description:
                setting.description = description
            setting.updated_at = datetime.utcnow()
        else:
            setting = BursarSettings(
                category=category,
                key=key,
                description=description
            )
            setting.typed_value = value
            db.session.add(setting)
        return setting