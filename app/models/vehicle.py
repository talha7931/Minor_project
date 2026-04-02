"""Vehicle model."""
from datetime import datetime
from app import db


class Vehicle(db.Model):
    """Registered vehicle belonging to a resident."""
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    resident_id = db.Column(db.Integer, db.ForeignKey('resident_profiles.id'), nullable=False)
    plate_number = db.Column(db.String(20), nullable=False, unique=True, index=True)
    vehicle_type = db.Column(db.String(30), default='car')  # car | bike | truck | other
    color = db.Column(db.String(30))
    brand = db.Column(db.String(50))
    authorized = db.Column(db.Boolean, default=True)
    blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    resident = db.relationship('ResidentProfile', back_populates='vehicles')
    entry_logs = db.relationship('EntryLog', back_populates='matched_vehicle')

    def __repr__(self):
        return f'<Vehicle {self.plate_number}>'
