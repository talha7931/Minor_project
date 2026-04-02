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


def get_recent_logs(limit=20):
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
