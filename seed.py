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

        # ---- Resident 2 ----
        r2 = User(name='Priya Mehta', email='resident2@gate.com', role='resident')
        r2.set_password('Res@1234')
        db.session.add(r2)
        db.session.flush()
        p2 = ResidentProfile(user_id=r2.id, flat_no='B-203', phone='+91 87654 32109')
        db.session.add(p2)
        db.session.flush()

        v3 = Vehicle(resident_id=p2.id, plate_number='KA05MG2222',
                     vehicle_type='car', color='Silver', brand='Maruti Swift',
                     authorized=True, blacklisted=False)
        # Blacklisted vehicle
        v4 = Vehicle(resident_id=p2.id, plate_number='DL3CAF9999',
                     vehicle_type='car', color='Red', brand='Unknown',
                     authorized=False, blacklisted=True)
        db.session.add_all([v3, v4])
        db.session.flush()

        # ---- Visitor pass ----
        now = datetime.utcnow()
        vp = VisitorPass(
            resident_id=p1.id,
            visitor_name='Amit Verma (Plumber)',
            vehicle_plate='UP32GH4567',
            valid_from=now - timedelta(hours=1),
            valid_to=now + timedelta(hours=5),
            approved=True,
            notes='Scheduled plumbing repair visit',
        )
        db.session.add(vp)

        # ---- Sample entry logs ----
        log_data = [
            ('MH12AB1234', 'MH12AB1234', 95.2, 'authorized', 'open'),
            ('KA05MG2222', 'KA05MG2222', 88.5, 'authorized', 'open'),
            ('DL3CAF9999', 'DL3CAF9999', 91.0, 'blocked', 'denied'),
            ('UP32GH4567', 'UP32GH4567', 83.3, 'visitor', 'open'),
            ('TN22CC9999', 'TN22CC9999', 54.1, 'unknown', 'none'),
            ('MH12CD5678', 'MH12CD5678', 97.1, 'authorized', 'open'),
        ]
        for i, (raw, norm, conf, status, gate) in enumerate(log_data):
            ts = now - timedelta(minutes=i * 15 + 5)
            vid = None
            if status == 'authorized':
                vehicle_match = Vehicle.query.filter_by(plate_number=norm).first()
                vid = vehicle_match.id if vehicle_match else None
            log = EntryLog(
                timestamp=ts,
                plate_text=raw,
                normalized_plate=norm,
                confidence=conf,
                status=status,
                source='anpr',
                gate_action=gate,
                matched_vehicle_id=vid,
            )
            db.session.add(log)

        # ---- Alerts ----
        alerts = [
            Alert(type='blacklisted', severity='high',
                  message='Blacklisted vehicle DL3CAF9999 attempted entry.',
                  related_plate='DL3CAF9999', resolved=False),
            Alert(type='unknown', severity='medium',
                  message='Unknown vehicle TN22CC9999 detected at gate.',
                  related_plate='TN22CC9999', resolved=False),
            Alert(type='ocr_mismatch', severity='low',
                  message='Low-confidence read for plate TN22CC9999 (54%)',
                  related_plate='TN22CC9999', resolved=True),
        ]
        db.session.add_all(alerts)

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
        print('\n✅ Demo data seeded successfully!')
        print('\n--- Demo Credentials ---')
        print('Admin:     admin@gate.com    / Admin@123')
        print('Security:  guard@gate.com    / Guard@123')
        print('Resident1: resident1@gate.com / Res@1234')
        print('Resident2: resident2@gate.com / Res@1234')


if __name__ == '__main__':
    seed()
