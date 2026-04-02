# GateANPR — Residential Society Gate Entry System

A complete full-stack ANPR (Automatic Number Plate Recognition) gate management system for residential societies and colonies.

## Features

- **3 Role-Based Dashboards**: Admin, Security, Resident
- **ANPR Pipeline**: Modular plate detection → OCR → normalization → authorization
- **Live Camera Support**: Webcam, uploaded frames, or Raspberry Pi camera (Picamera2)
- **Gate Simulation**: Auto-open/close based on vehicle authorization
- **Entry Logging**: Full searchable log with CSV export
- **Visitor Passes**: Residents can create temporary passes
- **Alerts**: Auto-alerts for blacklisted/unknown vehicles
- **Indian Plate Format Validation**

---

## Quick Start (Replit)

1. **Install dependencies** (handled automatically by Replit)
2. **Set up environment**:
   ```
   cp .env.example .env
   ```
3. **Seed the demo database**:
   ```
   python seed.py
   ```
4. **Run the app**:
   ```
   python run.py
   ```

The app runs on `http://0.0.0.0:5000`

---

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@gate.com | Admin@123 |
| Security | guard@gate.com | Guard@123 |
| Resident 1 | resident1@gate.com | Res@1234 |
| Resident 2 | resident2@gate.com | Res@1234 |

---

## Camera Modes

Set `CAMERA_MODE` in `.env`:

| Mode | Description |
|------|-------------|
| `upload` | Upload image files for testing (default, Replit) |
| `webcam` | USB webcam via OpenCV |
| `picamera2` | Raspberry Pi camera (Pi only) |

---

## Raspberry Pi Setup

1. Install OS: Raspberry Pi OS (Bookworm)
2. Enable camera interface:
   ```bash
   sudo raspi-config  # Interface Options → Camera → Enable
   ```
3. Install Picamera2:
   ```bash
   sudo apt install python3-picamera2
   ```
4. Install app dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Set in `.env`:
   ```
   CAMERA_MODE=picamera2
   ANPR_MODE=live
   ```
6. Run:
   ```bash
   python run.py
   ```

---

## ANPR Upgrade Path

The system uses a **mock ANPR engine** by default (returns sample plates for testing). To upgrade to real inference:

### Plate Detection (YOLOv8)
Edit `app/services/anpr_service.py` → `MockPlateDetector.detect()`:
```python
from ultralytics import YOLO
model = YOLO('yolov8n-plate.pt')
results = model(frame)
roi = crop_roi(frame, results.boxes[0])
```

### OCR (EasyOCR)
Edit `MockOCRReader.read()`:
```python
import easyocr
reader = easyocr.Reader(['en'])
results = reader.readtext(plate_roi)
text = ''.join([r[1] for r in results])
confidence = results[0][2] * 100
```

Then set `ANPR_MODE=live` in `.env`.

---

## Project Structure

```
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # Flask Blueprints
│   ├── services/            # Business logic layer
│   ├── utils/               # Decorators and helpers
│   ├── static/              # CSS, JS
│   └── templates/           # Jinja2 templates
├── instance/                # SQLite database (auto-created)
├── snapshots/               # Captured frame images
├── seed.py                  # Demo data seeder
├── run.py                   # Entry point
├── requirements.txt
└── .env.example
```

---

## Environment Variables

See `.env.example` for all available options.

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (change me) | Flask session secret |
| `CAMERA_MODE` | `upload` | Camera source |
| `ANPR_MODE` | `mock` | ANPR engine mode |
| `FRAME_SKIP` | `5` | Process every N-th frame |
| `DUPLICATE_WINDOW_SECONDS` | `10` | Suppress duplicate plate reads |
| `AUTO_ALLOW_AUTHORIZED` | `true` | Auto open gate for residents |
| `AUTO_DENY_BLACKLISTED` | `true` | Auto deny and alert for blacklisted |
