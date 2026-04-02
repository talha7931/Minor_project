"""Alert model."""
from datetime import datetime
from app import db


class Alert(db.Model):
    """System alert for security events."""
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(30))       # blacklisted | unknown | ocr_mismatch | camera_offline
    severity = db.Column(db.String(10), default='medium')  # low | medium | high | critical
    message = db.Column(db.Text, nullable=False)
    related_plate = db.Column(db.String(20))
    resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime)

    def resolve(self):
        self.resolved = True
        self.resolved_at = datetime.utcnow()

    def __repr__(self):
        return f'<Alert [{self.severity}] {self.type}: {self.related_plate}>'
