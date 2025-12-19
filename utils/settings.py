"""
System-wide settings utility for accessing bursar settings across the application.
"""
from models import BursarSettings, db

class SystemSettings:
    """Utility class for accessing system settings"""

    _cache = {}
    _cache_loaded = False

    @classmethod
    def _load_cache(cls):
        """Load all settings into cache"""
        if not cls._cache_loaded:
            all_settings = BursarSettings.query.filter_by(is_active=True).all()
            for setting in all_settings:
                if setting.category not in cls._cache:
                    cls._cache[setting.category] = {}
                cls._cache[setting.category][setting.key] = setting.typed_value
            cls._cache_loaded = True

    @classmethod
    def get(cls, category, key, default=None):
        """Get a setting value"""
        cls._load_cache()
        return cls._cache.get(category, {}).get(key, default)

    @classmethod
    def get_category(cls, category):
        """Get all settings for a category"""
        cls._load_cache()
        return cls._cache.get(category, {})

    @classmethod
    def set(cls, category, key, value, description=None):
        """Set a setting value"""
        BursarSettings.upsert_setting(category, key, value, description)
        db.session.commit()
        # Invalidate cache
        cls._cache_loaded = False

    @classmethod
    def invalidate_cache(cls):
        """Invalidate the settings cache"""
        cls._cache_loaded = False

    # Convenience methods for common settings
    @classmethod
    def get_school_name(cls):
        return cls.get('general', 'school_name', '')

    @classmethod
    def get_currency(cls):
        return cls.get('general', 'currency', 'KES')

    @classmethod
    def get_timezone(cls):
        return cls.get('general', 'timezone', 'Africa/Nairobi')

    @classmethod
    def get_academic_year(cls):
        return cls.get('general', 'academic_year', '')

    @classmethod
    def get_email_notifications_enabled(cls):
        return cls.get('notifications', 'email_notifications', False)

    @classmethod
    def get_payment_reminders_enabled(cls):
        return cls.get('notifications', 'payment_reminders', True)

    @classmethod
    def get_overdue_alerts_enabled(cls):
        return cls.get('notifications', 'overdue_alerts', True)

    @classmethod
    def get_reminder_days(cls):
        return cls.get('notifications', 'reminder_days', 7)

    @classmethod
    def get_password_min_length(cls):
        return cls.get('security', 'password_min_length', 8)

    @classmethod
    def get_session_timeout(cls):
        return cls.get('security', 'session_timeout', 30)

    @classmethod
    def get_two_factor_auth_enabled(cls):
        return cls.get('security', 'two_factor_auth', False)

    @classmethod
    def get_login_attempts_limit(cls):
        return cls.get('security', 'login_attempts', 5)

    @classmethod
    def get_default_report_format(cls):
        return cls.get('reports', 'default_format', 'pdf')

    @classmethod
    def get_auto_generate_reports(cls):
        return cls.get('reports', 'auto_generate', False)

    @classmethod
    def get_include_charts_in_reports(cls):
        return cls.get('reports', 'include_charts', True)

    @classmethod
    def get_report_frequency(cls):
        return cls.get('reports', 'report_frequency', 'monthly')

    @classmethod
    def format_currency(cls, amount, currency=None):
        """Format amount with currency symbol"""
        if currency is None:
            currency = cls.get_currency()

        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0.0

        currency_symbols = {
            'KES': 'KSh',
            'UGX': 'UGX',
            'TZS': 'TSh',
            'USD': '$',
            'EUR': '€',
            'GBP': '£'
        }

        symbol = currency_symbols.get(currency, currency)
        return f"{symbol} {amount:,.2f}"

    @classmethod
    def format_currency_no_symbol(cls, amount):
        """Format amount without currency symbol"""
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0
        return f"{amount:,.2f}"