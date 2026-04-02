"""
ANPR (Automatic Number Plate Recognition) service.

Architecture:
  PlateDetector     -> Finds plate region in image (ROI)
  OCRReader         -> Reads text from plate region
  PlatePostProcessor -> Normalizes and validates OCR output
  AuthorizationEngine -> Checks plate against DB and determines access

Mock mode:
  Returns realistic sample data for testing without real ANPR hardware.
  Set ANPR_MODE=live to switch to real inference (see UPGRADE POINT comments).

UPGRADE POINTS:
  - Replace MockPlateDetector with YOLOv8-based detector
  - Replace MockOCRReader with EasyOCR reader
"""
import io
import random
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.utils.helpers import normalize_plate, is_valid_indian_plate

logger = logging.getLogger(__name__)

SAMPLE_PLATES = [
    'MH12AB1234', 'DL3CAF1234', 'KA05MG2222',
    'TN22CC9999', 'GJ01CD7777', 'UP32GH4567',
    'RJ14EF3333', 'MP09IJ8888', 'HR26CD8888',
    'WB02KL5678',
]


@dataclass
class ANPRResult:
    """Result of a complete ANPR pipeline run."""
    raw_plate: str = ''
    normalized_plate: str = ''
    confidence: float = 0.0
    is_valid_format: bool = False
    detection_time_ms: float = 0.0
    snapshot_path: str = ''
    error: str = ''
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MockPlateDetector:
    """
    Stub plate detector that returns a random sample plate.

    UPGRADE POINT: Replace this class with a YOLOv8-based plate detector.
    Example:
        from ultralytics import YOLO
        model = YOLO('yolov8n-plate.pt')
        results = model(frame)
        roi = crop_roi(frame, results.boxes[0])
    """

    def detect(self, frame_bytes: bytes) -> bytes | None:
        """Return ROI bytes (here we just pass the full frame through)."""
        return frame_bytes  # Real: crop plate region from frame


class MockOCRReader:
    """
    Stub OCR reader that returns a random sample plate number.

    UPGRADE POINT: Replace this class with EasyOCR.
    Example:
        import easyocr
        reader = easyocr.Reader(['en'])
        results = reader.readtext(plate_roi)
        text = ''.join([r[1] for r in results])
    """

    def read(self, roi_bytes: bytes) -> tuple[str, float]:
        """Return (plate_text, confidence_0_to_100)."""
        plate = random.choice(SAMPLE_PLATES)
        confidence = random.uniform(72.0, 98.0)
        return plate, confidence


class PlatePostProcessor:
    """Normalize and validate raw OCR text."""

    def process(self, raw_text: str) -> tuple[str, bool]:
        """Return (normalized_plate, is_valid)."""
        normalized = normalize_plate(raw_text)
        valid = is_valid_indian_plate(normalized)
        return normalized, valid


class AuthorizationEngine:
    """Check plate against registered vehicles and visitor passes."""

    def authorize(self, normalized_plate: str) -> dict:
        """
        Return authorization result dict:
          status: authorized | visitor | blocked | unknown
          vehicle_id: int or None
          message: str
        """
        from app.services.vehicle_service import get_vehicle_by_plate, get_active_visitor_pass

        vehicle = get_vehicle_by_plate(normalized_plate)
        if vehicle:
            if vehicle.blacklisted:
                return {
                    'status': 'blocked',
                    'vehicle_id': vehicle.id,
                    'message': f'Blacklisted vehicle: {normalized_plate}',
                }
            if vehicle.authorized:
                return {
                    'status': 'authorized',
                    'vehicle_id': vehicle.id,
                    'message': f'Authorized resident vehicle: {normalized_plate}',
                }

        visitor_pass = get_active_visitor_pass(normalized_plate)
        if visitor_pass:
            return {
                'status': 'visitor',
                'vehicle_id': None,
                'message': f'Valid visitor pass for {visitor_pass.visitor_name}',
            }

        return {
            'status': 'unknown',
            'vehicle_id': None,
            'message': f'Unknown vehicle: {normalized_plate}',
        }


class ANPRPipeline:
    """
    Full ANPR processing pipeline.

    Pipeline steps:
      1. Receive frame bytes
      2. Detect plate ROI
      3. Run OCR
      4. Normalize and validate plate text
      5. Authorize against DB
      6. Return ANPRResult
    """

    def __init__(self, mode: str = 'mock'):
        self.mode = mode
        self.detector = MockPlateDetector()
        self.ocr = MockOCRReader()
        self.post_processor = PlatePostProcessor()
        self.auth_engine = AuthorizationEngine()

    def process_frame(self, frame_bytes: bytes,
                      save_snapshot: bool = True,
                      snapshot_dir: Path = None) -> ANPRResult:
        """Run the full pipeline on a single frame."""
        start = time.time()
        result = ANPRResult()

        try:
            # Step 1: Detect plate ROI
            roi = self.detector.detect(frame_bytes)
            if roi is None:
                result.error = 'No plate detected'
                return result

            # Step 2: OCR
            raw_text, confidence = self.ocr.read(roi)
            result.raw_plate = raw_text
            result.confidence = round(confidence, 2)

            # Step 3: Post-processing
            normalized, is_valid = self.post_processor.process(raw_text)
            result.normalized_plate = normalized
            result.is_valid_format = is_valid

            # Step 4: Save snapshot
            if save_snapshot and snapshot_dir and frame_bytes:
                snapshot_dir = Path(snapshot_dir)
                snapshot_dir.mkdir(parents=True, exist_ok=True)
                filename = f'{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}_{normalized}.jpg'
                path = snapshot_dir / filename
                path.write_bytes(frame_bytes)
                result.snapshot_path = str(path)

        except Exception as e:
            logger.error('ANPR pipeline error: %s', e)
            result.error = str(e)
        finally:
            result.detection_time_ms = round((time.time() - start) * 1000, 1)

        return result

    def process_and_log(self, frame_bytes: bytes, snapshot_dir: Path = None,
                        duplicate_window: int = 10,
                        operator_id: int = None) -> dict:
        """
        Run pipeline and automatically log the result.
        Returns a dict with result + log record.
        """
        from app.services.log_service import is_duplicate, create_log
        from app.services.gate_service import open_gate, close_gate
        from app.services.alert_service import create_alert
        from flask import current_app

        anpr = self.process_frame(frame_bytes, snapshot_dir=snapshot_dir)
        if anpr.error or not anpr.normalized_plate:
            return {'success': False, 'error': anpr.error or 'No plate detected'}

        # Suppress duplicates
        if is_duplicate(anpr.normalized_plate, window_seconds=duplicate_window):
            return {'success': False, 'error': 'Duplicate read suppressed', 'plate': anpr.normalized_plate}

        # Authorize
        auth = self.auth_engine.authorize(anpr.normalized_plate)
        status = auth['status']
        gate_action = 'none'

        auto_allow = current_app.config.get('AUTO_ALLOW_AUTHORIZED', True)
        auto_deny = current_app.config.get('AUTO_DENY_BLACKLISTED', True)

        if status == 'authorized' and auto_allow:
            open_gate(triggered_by='anpr', reason=f'Auto: {anpr.normalized_plate}')
            gate_action = 'open'
        elif status == 'visitor':
            open_gate(triggered_by='anpr', reason=f'Visitor: {anpr.normalized_plate}')
            gate_action = 'open'
        elif status == 'blocked' and auto_deny:
            gate_action = 'denied'
            create_alert(
                alert_type='blacklisted',
                message=f'Blacklisted vehicle detected: {anpr.normalized_plate}',
                related_plate=anpr.normalized_plate,
                severity='high',
            )
        elif status == 'unknown':
            create_alert(
                alert_type='unknown',
                message=f'Unknown vehicle at gate: {anpr.normalized_plate}',
                related_plate=anpr.normalized_plate,
                severity='medium',
            )

        log = create_log(
            plate_text=anpr.raw_plate,
            normalized_plate=anpr.normalized_plate,
            confidence=anpr.confidence,
            status=status,
            source='anpr',
            gate_action=gate_action,
            matched_vehicle_id=auth.get('vehicle_id'),
            snapshot_path=anpr.snapshot_path,
            operator_id=operator_id,
        )

        return {
            'success': True,
            'plate': anpr.normalized_plate,
            'confidence': anpr.confidence,
            'status': status,
            'gate_action': gate_action,
            'log_id': log.id,
            'message': auth['message'],
        }
