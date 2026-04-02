"""Entry log model."""
from datetime import datetime
from app import db


class EntryLog(db.Model):
    """Log of every vehicle detection / gate event."""
    __tablename__ = 'entry_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    plate_text = db.Column(db.String(20))            # raw OCR text
    normalized_plate = db.Column(db.String(20))      # cleaned/formatted plate
    confidence = db.Column(db.Float, default=0.0)    # OCR confidence 0-100
    snapshot_path = db.Column(db.String(256))        # saved frame image path
    status = db.Column(db.String(30), default='unknown')
    # authorized | visitor | blocked | unknown | manual_allow | manual_deny
    source = db.Column(db.String(20), default='anpr')  # anpr | manual
    gate_action = db.Column(db.String(20))           # open | close | none
    matched_vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    notes = db.Column(db.Text)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    matched_vehicle = db.relationship('Vehicle', back_populates='entry_logs')
    operator = db.relationship('User', foreign_keys=[operator_id])

    @property
    def status_label(self):
        labels = {
            'authorized': 'Authorized',
            'visitor': 'Visitor',
            'blocked': 'Blocked',
            'unknown': 'Unknown',
            'manual_allow': 'Manual Allow',
            'manual_deny': 'Manual Deny',
        }
        return labels.get(self.status, self.status.title())

    def __repr__(self):
        return f'<EntryLog {self.normalized_plate} @ {self.timestamp}>'
