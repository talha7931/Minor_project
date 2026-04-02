"""Visitor pass model."""
from datetime import datetime
from app import db


class VisitorPass(db.Model):
    """Temporary visitor entry pass requested by a resident."""
    __tablename__ = 'visitor_passes'

    id = db.Column(db.Integer, primary_key=True)
    resident_id = db.Column(db.Integer, db.ForeignKey('resident_profiles.id'), nullable=False)
    visitor_name = db.Column(db.String(100), nullable=False)
    vehicle_plate = db.Column(db.String(20))
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_to = db.Column(db.DateTime, nullable=False)
    approved = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    resident = db.relationship('ResidentProfile', back_populates='visitor_passes')

    @property
    def is_active(self):
        now = datetime.utcnow()
        return self.approved and self.valid_from <= now <= self.valid_to

    @property
    def is_expired(self):
        return datetime.utcnow() > self.valid_to

    def __repr__(self):
        return f'<VisitorPass {self.visitor_name} plate={self.vehicle_plate}>'
