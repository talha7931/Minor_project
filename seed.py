"""
Seed script — populates both SQLite and Supabase database with clean demo data.
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

from app.services.auth_service import create_user
from app.services.vehicle_service import add_vehicle


def seed():
    app = create_app()
    with app.app_context():
        print('Dropping and recreating local tables...')
        db.drop_all()
        db.create_all()

        # ---- Admin user ----
        print('Creating Admin...')
        admin = create_user(name='Admin User', email='admin@gate.com', password='Admin@123', role='admin')

        # ---- Security user ----
        print('Creating Security Guard...')
        guard = create_user(name='Gate Guard', email='guard@gate.com', password='Guard@123', role='security')

        # ---- Resident 1 ----
        print('Creating Resident Ravi Sharma...')
        r1 = create_user(
            name='Ravi Sharma', 
            email='resident1@gate.com', 
            password='Res@1234', 
            role='resident', 
            flat_no='A-101', 
            phone='+91 98765 43210'
        )
        p1 = ResidentProfile.query.filter_by(user_id=r1.id).first()

        print('Registering vehicles for Ravi Sharma...')
        v1 = add_vehicle(resident_id=p1.id, plate_number='MH12AB1234', vehicle_type='car', color='White', brand='Honda City')
        v2 = add_vehicle(resident_id=p1.id, plate_number='MH12CD5678', vehicle_type='bike', color='Black', brand='Royal Enfield')

        # ---- Resident 2 (Mohammad Talha) ----
        print('Creating Resident Mohammad Talha...')
        r2 = create_user(
            name='Mohammad Talha',
            email='smohammadtalha0@gmail.com',
            password='Res@5678',
            role='resident',
            flat_no='B-104',
            phone='+91 8856932785'
        )
        p2 = ResidentProfile.query.filter_by(user_id=r2.id).first()

        print('Registering Himalayan 450 for Mohammad Talha...')
        v3 = add_vehicle(resident_id=p2.id, plate_number='MH12AB0001', vehicle_type='bike', color='White', brand='Royal Enfield Himalayan 450')

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
        print('\nDemo data seeded successfully across both SQLite and Supabase!')
        print('\n--- Demo Credentials ---')
        print('Admin:     admin@gate.com    / Admin@123')
        print('Security:  guard@gate.com    / Guard@123')
        print('Resident1: resident1@gate.com / Res@1234')


if __name__ == '__main__':
    seed()
