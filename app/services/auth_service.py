"""Authentication and user management service."""
from app import db
from app.models.user import User, ResidentProfile


def get_user_by_email(email: str):
    return User.query.filter_by(email=email.lower().strip()).first()


def create_user(name: str, email: str, password: str, role: str = 'resident',
                flat_no: str = None, phone: str = None) -> User:
    """Create a new user with an optional resident profile and sync to Supabase."""
    user = User(name=name, email=email.lower().strip(), role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    if role == 'resident' and flat_no:
        profile = ResidentProfile(user_id=user.id, flat_no=flat_no, phone=phone or '')
        db.session.add(profile)

    db.session.commit()

    # Sync to Supabase in real-time (for residents)
    if role == 'resident' and flat_no:
        import os
        import uuid
        import requests
        
        supabase_url = os.environ.get('SUPABASE_URL', 'https://miqdestfirvcfmqlclqc.supabase.co')
        supabase_key = os.environ.get('SUPABASE_KEY', 'sb_publishable_gRrkx4WWNgNF1m_sxiQtTA_5aL8Qj6e')
        
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        profile_uuid = str(uuid.uuid4())
        resident_uuid = str(uuid.uuid4())
        
        profile_payload = {
            "id": profile_uuid,
            "full_name": name,
            "role": "resident",
            "apartment_number": flat_no,
            "phone": phone or "",
            "is_active": True
        }
        
        try:
            # Sync Profile
            r1 = requests.post(f"{supabase_url}/rest/v1/profiles", json=profile_payload, headers=headers, timeout=5)
            if r1.status_code in [200, 201]:
                # Sync Resident Profile linked to the profile
                resident_payload = {
                    "id": resident_uuid,
                    "profile_id": profile_uuid,
                    "tower": "A", # Default tower
                    "flat_number": flat_no,
                    "occupancy_status": "owner"
                }
                r2 = requests.post(f"{supabase_url}/rest/v1/residents", json=resident_payload, headers=headers, timeout=5)
                if r2.status_code not in [200, 201]:
                    print(f"Supabase Resident Sync failed with status {r2.status_code}: {r2.text}")
            else:
                print(f"Supabase Profile Sync failed with status {r1.status_code}: {r1.text}")
        except Exception as e:
            print(f"Supabase Resident Sync error (ignoring to keep local operational): {e}")

    return user


def update_user(user: User, **kwargs) -> User:
    """Update user fields."""
    for k, v in kwargs.items():
        if k == 'password':
            user.set_password(v)
        elif hasattr(user, k):
            setattr(user, k, v)
    db.session.commit()
    return user


def toggle_user_active(user: User) -> bool:
    """Toggle the active status of a user."""
    user.active = not user.active
    db.session.commit()
    return user.active


def get_all_users():
    return User.query.order_by(User.created_at.desc()).all()
