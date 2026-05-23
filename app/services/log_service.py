"""Entry log creation, retrieval and export service."""
import csv
import io
from datetime import datetime, timedelta
from app import db
from app.models.entry_log import EntryLog


def create_log(plate_text: str, normalized_plate: str, confidence: float,
               status: str, source: str = 'anpr', gate_action: str = 'none',
               matched_vehicle_id: int = None, snapshot_path: str = '',
               notes: str = '', operator_id: int = None) -> EntryLog:
    """Create an entry log record."""
    log = EntryLog(
        plate_text=plate_text,
        normalized_plate=normalized_plate,
        confidence=confidence,
        status=status,
        source=source,
        gate_action=gate_action,
        matched_vehicle_id=matched_vehicle_id,
        snapshot_path=snapshot_path,
        notes=notes,
        operator_id=operator_id,
    )
    db.session.add(log)
    db.session.commit()
    return log


class SupabaseEntryLog:
    """Helper wrapper to map Supabase entry logs to the local Flask EntryLog interface."""
    def __init__(self, data):
        self.id = data.get('id', '')
        
        # Parse Supabase timestamp into standard Python datetime object
        scanned_at = data.get('scanned_at')
        if scanned_at:
            try:
                # Strip timezone suffix to work with standard datetime.fromisoformat
                clean_ts = scanned_at.split('+')[0].split('Z')[0]
                self.timestamp = datetime.fromisoformat(clean_ts)
            except Exception:
                self.timestamp = datetime.utcnow()
        else:
            self.timestamp = datetime.utcnow()
            
        self.plate_text = data.get('plate_number_raw', '')
        self.normalized_plate = data.get('plate_number_normalized', '')
        self.confidence = float(data.get('ocr_confidence', 0.0))
        self.snapshot_path = data.get('snapshot_url', '')
        
        # Map Supabase decisions to local status
        decision = data.get('decision', 'unknown')
        status_map = {
            'authorized': 'authorized',
            'visitor_allowed': 'visitor',
            'blacklisted': 'blocked',
            'denied': 'blocked',
            'pending': 'unknown',
            'unknown': 'unknown'
        }
        self.status = status_map.get(decision, 'unknown')
        self.source = data.get('source', 'camera')
        self.gate_action = 'open' if self.status in ['authorized', 'visitor'] else 'none'
        self.notes = data.get('reason', '')
        
    @property
    def status_label(self):
        labels = {
            'authorized': 'Authorized',
            'visitor': 'Visitor',
            'blocked': 'Blocked',
            'unknown': 'Unknown',
            'manual_allow': 'Manual Allow',
            'manual_deny': 'Manual Deny',
        }
        return labels.get(self.status, self.status.title())


def get_recent_logs(limit=20):
    """Retrieve recent plate scan entries directly from Supabase, falling back to SQLite if offline."""
    import os
    import requests
    
    supabase_url = os.environ.get('SUPABASE_URL', 'https://miqdestfirvcfmqlclqc.supabase.co')
    supabase_key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1pcWRlc3RmaXJ2Y2ZtcWxjbHFjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcwMzQ3MCwiZXhwIjoyMDkxMjc5NDcwfQ.TxNsVFMXAGdAj7HNlJTL6LrGcFyV-TcFo3i7vHA-XmU')
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Query recent scans from Supabase ordered by scanned_at descending
        r = requests.get(
            f"{supabase_url}/rest/v1/entry_logs?order=scanned_at.desc&limit={limit}",
            headers=headers,
            timeout=3
        )
        if r.status_code == 200:
            return [SupabaseEntryLog(row) for row in r.json()]
    except Exception as e:
        print(f"Supabase recent logs fetch error (falling back to local SQLite): {e}")
        
    # Local fallback
    return EntryLog.query.order_by(EntryLog.timestamp.desc()).limit(limit).all()


def get_logs_for_resident(resident_id: int, limit=50):
    """Return logs for vehicles belonging to a specific resident."""
    from app.models.vehicle import Vehicle
    vehicle_ids = [v.id for v in Vehicle.query.filter_by(resident_id=resident_id).all()]
    if not vehicle_ids:
        return []
    return EntryLog.query.filter(
        EntryLog.matched_vehicle_id.in_(vehicle_ids)
    ).order_by(EntryLog.timestamp.desc()).limit(limit).all()


def search_logs(plate=None, status=None, date_from=None, date_to=None,
                limit=100, offset=0):
    """Search logs with optional filters."""
    q = EntryLog.query
    if plate:
        q = q.filter(EntryLog.normalized_plate.ilike(f'%{plate}%'))
    if status:
        q = q.filter(EntryLog.status == status)
    if date_from:
        q = q.filter(EntryLog.timestamp >= date_from)
    if date_to:
        q = q.filter(EntryLog.timestamp <= date_to)
    total = q.count()
    logs = q.order_by(EntryLog.timestamp.desc()).offset(offset).limit(limit).all()
    return logs, total


def is_duplicate(normalized_plate: str, window_seconds: int = 10) -> bool:
    """Check if this plate was already logged within the duplicate window."""
    cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
    exists = EntryLog.query.filter(
        EntryLog.normalized_plate == normalized_plate,
        EntryLog.timestamp >= cutoff,
    ).first()
    return exists is not None


def today_stats() -> dict:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total = EntryLog.query.filter(EntryLog.timestamp >= today_start).count()
    denied = EntryLog.query.filter(
        EntryLog.timestamp >= today_start,
        EntryLog.status.in_(['blocked', 'manual_deny'])
    ).count()
    authorized = EntryLog.query.filter(
        EntryLog.timestamp >= today_start,
        EntryLog.status.in_(['authorized', 'visitor', 'manual_allow'])
    ).count()
    return {'total': total, 'authorized': authorized, 'denied': denied}


def export_logs_csv(logs) -> str:
    """Export a list of EntryLog objects as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'ID', 'Timestamp', 'Raw Plate', 'Normalized Plate',
        'Confidence', 'Status', 'Source', 'Gate Action', 'Notes'
    ])
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else '',
            log.plate_text or '',
            log.normalized_plate or '',
            f'{log.confidence:.1f}%',
            log.status,
            log.source,
            log.gate_action or '',
            log.notes or '',
        ])
    return output.getvalue()
