"""Vehicle and authorization management service."""
from datetime import datetime
from app import db
from app.models.vehicle import Vehicle
from app.models.visitor_pass import VisitorPass
from app.utils.helpers import normalize_plate


def add_vehicle(resident_id: int, plate_number: str, vehicle_type: str = 'car',
                color: str = '', brand: str = '') -> Vehicle:
    """Register a new vehicle for a resident and sync to Supabase."""
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

    # Sync to Supabase in real-time
    try:
        from app.models.user import ResidentProfile
        resident = ResidentProfile.query.get(resident_id)
        if resident:
            flat_no = resident.flat_no
            import os
            import requests
            
            supabase_url = os.environ.get('SUPABASE_URL', 'https://miqdestfirvcfmqlclqc.supabase.co')
            supabase_key = os.environ.get('SUPABASE_KEY', 'sb_publishable_gRrkx4WWNgNF1m_sxiQtTA_5aL8Qj6e')
            
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json"
            }
            
            # Find resident UUID in Supabase by flat number
            r = requests.get(f"{supabase_url}/rest/v1/residents?flat_number=eq.{flat_no}", headers=headers, timeout=5)
            supabase_res_id = None
            if r.status_code == 200 and r.json():
                supabase_res_id = r.json()[0]['id']
                
            vehicle_payload = {
                "resident_id": supabase_res_id,
                "plate_number": normalized,
                "plate_display": plate_number, # Formatted e.g. "MH 12 AB 1234"
                "vehicle_type": vehicle_type if vehicle_type in ['car', 'bike', 'truck', 'other'] else 'other',
                "color": color,
                "brand_model": brand,
                "status": "authorized",
                "is_blacklisted": False
            }
            r_post = requests.post(f"{supabase_url}/rest/v1/vehicles", json=vehicle_payload, headers=headers, timeout=5)
            if r_post.status_code not in [200, 201]:
                print(f"Supabase Vehicle Sync failed with status {r_post.status_code}: {r_post.text}")
    except Exception as e:
        print(f"Supabase Vehicle Sync warning (ignoring to keep local operational): {e}")

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

    # Sync to Supabase in real-time
    try:
        from app.models.user import ResidentProfile
        resident = ResidentProfile.query.get(resident_id)
        if resident:
            flat_no = resident.flat_no
            import os
            import requests
            
            supabase_url = os.environ.get('SUPABASE_URL', 'https://miqdestfirvcfmqlclqc.supabase.co')
            supabase_key = os.environ.get('SUPABASE_KEY', 'sb_publishable_gRrkx4WWNgNF1m_sxiQtTA_5aL8Qj6e')
            
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json"
            }
            
            # Find resident UUID in Supabase by flat number
            r = requests.get(f"{supabase_url}/rest/v1/residents?flat_number=eq.{flat_no}", headers=headers, timeout=5)
            supabase_res_id = None
            if r.status_code == 200 and r.json():
                supabase_res_id = r.json()[0]['id']
                
            pass_payload = {
                "resident_id": supabase_res_id,
                "visitor_name": visitor_name,
                "vehicle_plate": normalized if vehicle_plate else None,
                "purpose": notes or "Visitor Pass",
                "valid_from": valid_from.isoformat() + "Z" if hasattr(valid_from, "isoformat") else str(valid_from),
                "valid_until": valid_to.isoformat() + "Z" if hasattr(valid_to, "isoformat") else str(valid_to),
                "allowed_entries": 1,
                "used_entries": 0,
                "status": "active"
            }
            requests.post(f"{supabase_url}/rest/v1/visitor_passes", json=pass_payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"Supabase Visitor Pass Sync warning (ignoring to keep local operational): {e}")

    return vp


def get_all_vehicles():
    return Vehicle.query.order_by(Vehicle.created_at.desc()).all()
