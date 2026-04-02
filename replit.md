# GateANPR — Residential Society Gate Entry System

## Overview
A complete full-stack ANPR (Automatic Number Plate Recognition) gate management system built with Flask, SQLite, and Jinja2 templates. Designed for residential societies/colonies with Raspberry Pi camera support.

## Architecture
- **Backend**: Python Flask with SQLAlchemy ORM
- **Database**: SQLite (`instance/gate_system.db`)
- **Frontend**: Server-rendered Jinja2 templates with dark-mode CSS
- **Auth**: Flask-Login with role-based access (admin/security/resident)
- **Port**: 5000 (0.0.0.0)

## Project Structure
```
app/
  __init__.py         Flask app factory
  config.py           Configuration (SQLite, camera, ANPR settings)
  models/             SQLAlchemy models (User, Vehicle, EntryLog, Alert, etc.)
  routes/             Flask Blueprints (auth, admin, security, resident, api)
  services/           Business logic (anpr, camera, gate, log, vehicle, alert)
  utils/              Decorators (role guards) and helpers
  templates/          Jinja2 templates (base.html + 3 dashboard sets)
  static/css/         main.css (dark theme)
  static/js/          main.js (sidebar, clock, refresh)
instance/             SQLite database (auto-created)
snapshots/            Saved gate entry snapshots
seed.py               Demo data seeder
run.py                Entry point
requirements.txt
```

## Running the App
```bash
python seed.py    # seed demo data (run once)
python run.py     # start on port 5000
```

## Demo Credentials
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@gate.com | Admin@123 |
| Security | guard@gate.com | Guard@123 |
| Resident 1 | resident1@gate.com | Res@1234 |
| Resident 2 | resident2@gate.com | Res@1234 |

## Dashboards
1. **Admin** (`/admin/`) — Residents, vehicles, logs, alerts, settings, CSV export
2. **Security** (`/security/`) — Live ANPR monitor, gate control, incident log
3. **Resident** (`/resident/`) — My vehicles, history, visitor passes, alerts

## ANPR Pipeline
- `app/services/anpr_service.py` — MockPlateDetector + MockOCRReader (upgrade to YOLOv8 + EasyOCR)
- `app/services/camera_service.py` — UploadSource / WebcamSource / PiCameraSource (Picamera2)
- Set `CAMERA_MODE=picamera2` and `ANPR_MODE=live` for Raspberry Pi deployment

## Key Dependencies
- flask, flask-login, flask-sqlalchemy, flask-wtf
- opencv-python-headless, Pillow, numpy
- python-dotenv, werkzeug

## Camera Modes
- `upload` — file upload for Replit/dev testing (default)
- `webcam` — USB webcam via OpenCV
- `picamera2` — Raspberry Pi libcamera (Pi only, requires picamera2 package)
