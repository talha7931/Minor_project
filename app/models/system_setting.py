"""System settings key-value model."""
from app import db


class SystemSetting(db.Model):
    """Generic key-value store for system settings."""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(200))

    @staticmethod
    def get(key, default=None):
        s = SystemSetting.query.filter_by(key=key).first()
        return s.value if s else default

    @staticmethod
    def set(key, value, description=None):
        s = SystemSetting.query.filter_by(key=key).first()
        if s:
            s.value = str(value)
        else:
            s = SystemSetting(key=key, value=str(value), description=description)
            db.session.add(s)
        db.session.commit()

    def __repr__(self):
        return f'<SystemSetting {self.key}={self.value}>'
