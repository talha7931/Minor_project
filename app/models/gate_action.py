"""Gate action log model."""
from datetime import datetime
from app import db


class GateAction(db.Model):
    """Log of gate open/close actions."""
    __tablename__ = 'gate_actions'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(10), nullable=False)  # open | close
    triggered_by = db.Column(db.String(20))  # anpr | manual | auto
    reason = db.Column(db.String(200))
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    operator = db.relationship('User')

    def __repr__(self):
        return f'<GateAction {self.action} @ {self.timestamp}>'
