"""Vehicle and authorization management service."""
from datetime import datetime
from app import db
from app.models.vehicle import Vehicle
from app.models.visitor_pass import VisitorPass
from app.utils.helpers import normalize_plate


def add_vehicle(resident_id: int, plate_number: str, vehicle_type: str = 'car',
                color: str = '', brand: str = '') -> Vehicle:
    """Register a new vehicle for a resident."""
    normalized = normalize_plate(plate_number)
    vehicle = Vehicle(
        resident_id=resident_id,
        plate_number=normalized,
        vehicle_type=vehicle_type,
        color=color,
        brand=brand,
        authorized=True,
        blacklisted=False,
    )
    db.session.add(vehicle)
    db.session.commit()
    return vehicle


def get_vehicle_by_plate(plate: str):
    normalized = normalize_plate(plate)
    return Vehicle.query.filter_by(plate_number=normalized).first()


def get_vehicles_for_resident(resident_id: int):
    return Vehicle.query.filter_by(resident_id=resident_id).all()


def toggle_blacklist(vehicle: Vehicle) -> bool:
    vehicle.blacklisted = not vehicle.blacklisted
    if vehicle.blacklisted:
        vehicle.authorized = False
    db.session.commit()
    return vehicle.blacklisted


def get_active_visitor_pass(plate: str):
    """Return an active visitor pass for this plate if one exists."""
    normalized = normalize_plate(plate)
    now = datetime.utcnow()
    return VisitorPass.query.filter(
        VisitorPass.vehicle_plate == normalized,
        VisitorPass.approved == True,
        VisitorPass.valid_from <= now,
        VisitorPass.valid_to >= now,
    ).first()


def create_visitor_pass(resident_id: int, visitor_name: str, vehicle_plate: str,
                        valid_from: datetime, valid_to: datetime,
                        notes: str = '') -> VisitorPass:
    normalized = normalize_plate(vehicle_plate) if vehicle_plate else ''
    vp = VisitorPass(
        resident_id=resident_id,
        visitor_name=visitor_name,
        vehicle_plate=normalized,
        valid_from=valid_from,
        valid_to=valid_to,
        approved=True,
        notes=notes,
    )
    db.session.add(vp)
    db.session.commit()
    return vp


def get_all_vehicles():
    return Vehicle.query.order_by(Vehicle.created_at.desc()).all()
