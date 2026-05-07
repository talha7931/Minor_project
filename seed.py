"""
Seed script — populates the database with demo data.
Run: python seed.py
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from app import create_app, db
from app.models.user import User, ResidentProfile
from app.models.vehicle import Vehicle
from app.models.entry_log import EntryLog
from app.models.visitor_pass import VisitorPass
from app.models.alert import Alert
from app.models.camera_config import CameraConfig
from app.models.system_setting import SystemSetting


def seed():
    app = create_app()
    with app.app_context():
        print('Dropping and recreating tables...')
        db.drop_all()
        db.create_all()

        # ---- Admin user ----
        admin = User(name='Admin User', email='admin@gate.com', role='admin')
        admin.set_password('Admin@123')
        db.session.add(admin)

        # ---- Security user ----
        guard = User(name='Gate Guard', email='guard@gate.com', role='security')
        guard.set_password('Guard@123')
        db.session.add(guard)

        db.session.flush()

        # ---- Resident 1 ----
        r1 = User(name='Ravi Sharma', email='resident1@gate.com', role='resident')
        r1.set_password('Res@1234')
        db.session.add(r1)
        db.session.flush()
        p1 = ResidentProfile(user_id=r1.id, flat_no='A-101', phone='+91 98765 43210')
        db.session.add(p1)
        db.session.flush()

        v1 = Vehicle(resident_id=p1.id, plate_number='MH12AB1234',
                     vehicle_type='car', color='White', brand='Honda City',
                     authorized=True, blacklisted=False)
        v2 = Vehicle(resident_id=p1.id, plate_number='MH12CD5678',
                     vehicle_type='bike', color='Black', brand='Royal Enfield',
                     authorized=True, blacklisted=False)
        db.session.add_all([v1, v2])



        # ---- Camera config ----
        cam = CameraConfig(source_type='upload', resolution_w=640, resolution_h=480,
                           fps=15, enabled=True, frame_skip=5, jpeg_quality=75)
        db.session.add(cam)

        # ---- System settings ----
        settings = [
            SystemSetting(key='anpr_mode', value='mock', description='ANPR inference mode'),
            SystemSetting(key='camera_mode', value='upload', description='Camera source type'),
            SystemSetting(key='auto_allow_authorized', value='true'),
            SystemSetting(key='auto_deny_blacklisted', value='true'),
            SystemSetting(key='duplicate_window_seconds', value='10'),
        ]
        db.session.add_all(settings)

        db.session.commit()
        print('\nDemo data seeded successfully!')
        print('\n--- Demo Credentials ---')
        print('Admin:     admin@gate.com    / Admin@123')
        print('Security:  guard@gate.com    / Guard@123')
        print('Resident1: resident1@gate.com / Res@1234')


if __name__ == '__main__':
    seed()
