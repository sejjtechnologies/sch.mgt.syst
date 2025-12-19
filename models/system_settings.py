from models import db
from datetime import datetime

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # 'general', 'maintenance', 'backups', etc.
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, nullable=True)
    value_type = db.Column(db.String(20), nullable=False, default='string')  # 'string', 'boolean', 'integer', 'float'
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Ensure unique combination of category and key
    __table_args__ = (db.UniqueConstraint('category', 'key', name='unique_system_category_key'),)

    def __repr__(self):
        return f'<SystemSetting {self.category}.{self.key} = {self.value}>'

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
        setting = SystemSetting.query.filter_by(category=category, key=key).first()
        if setting:
            setting.typed_value = value
            if description:
                setting.description = description
            setting.updated_at = datetime.utcnow()
        else:
            setting = SystemSetting(
                category=category,
                key=key,
                description=description
            )
            setting.typed_value = value
            db.session.add(setting)
        return setting