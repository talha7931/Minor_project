"""JSON API routes for real-time frontend updates."""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.services.log_service import get_recent_logs, today_stats
from app.services.gate_service import get_gate_status
from app.services.alert_service import get_active_alerts, unresolved_count
from app.utils.helpers import format_datetime, time_ago, status_badge

api_bp = Blueprint('api', __name__)


def _log_to_dict(log):
    return {
        'id': log.id,
        'timestamp': format_datetime(log.timestamp),
        'time_ago': time_ago(log.timestamp),
        'plate': log.normalized_plate or log.plate_text or '-',
        'confidence': f'{log.confidence:.1f}%',
        'status': log.status,
        'status_label': log.status_label,
        'gate_action': log.gate_action or 'none',
        'source': log.source,
        'badge_class': status_badge(log.status),
    }


@api_bp.route('/recent-events')
@login_required
def recent_events():
    """Return the last 20 entry log events as JSON."""
    logs = get_recent_logs(20)
    return jsonify([_log_to_dict(l) for l in logs])


@api_bp.route('/gate-status')
@login_required
def gate_status():
    return jsonify(get_gate_status())


@api_bp.route('/stats')
@login_required
def stats():
    data = today_stats()
    data['alert_count'] = unresolved_count()
    return jsonify(data)


@api_bp.route('/alerts')
@login_required
def alerts():
    active = get_active_alerts(10)
    return jsonify([{
        'id': a.id,
        'type': a.type,
        'severity': a.severity,
        'message': a.message,
        'plate': a.related_plate,
        'time': time_ago(a.created_at),
    } for a in active])


@api_bp.route('/sync-log', methods=['POST'])
def sync_log():
    """Receive a plate scan from the camera codebase or Supabase and log it locally."""
    from app.models.vehicle import Vehicle
    from app.services.log_service import create_log
    from app.services.alert_service import create_alert
    from app.services.gate_service import open_gate
    
    data = request.json or {}
    raw_plate = data.get('plate_number_raw', '')
    normalized_plate = data.get('plate_number_normalized', '').upper()
    confidence = float(data.get('ocr_confidence', 0.0))
    supabase_decision = data.get('decision', 'unknown')
    snapshot_url = data.get('snapshot_url', '')
    gate_name = data.get('gate_name', 'Main Gate')
    
    # Map Supabase Status Enum to Flask App Statuses
    status_mapping = {
        'authorized': 'authorized',
        'visitor_allowed': 'visitor',
        'blacklisted': 'blocked',
        'denied': 'blocked',
        'pending': 'unknown',
        'unknown': 'unknown'
    }
    flask_status = status_mapping.get(supabase_decision, 'unknown')
    
    # Find matching vehicle
    vehicle = Vehicle.query.filter_by(plate_number=normalized_plate).first()
    matched_vehicle_id = vehicle.id if vehicle else None
    
    # Gate Action
    gate_action = 'none'
    if flask_status in ['authorized', 'visitor']:
        open_gate(triggered_by='anpr', reason=f"ANPR Matched: {normalized_plate} at {gate_name}")
        gate_action = 'open'
    
    # Create Local Entry Log
    log = create_log(
        plate_text=raw_plate,
        normalized_plate=normalized_plate,
        confidence=confidence,
        status=flask_status,
        source='anpr',
        gate_action=gate_action,
        matched_vehicle_id=matched_vehicle_id,
        snapshot_path=snapshot_url, # Store public URL as the path
        notes=f"Synced from Camera: {gate_name}"
    )
    
    # Handle alerts
    if flask_status == 'blocked':
        create_alert(
            alert_type='blacklisted',
            severity='high',
            message=f"Blacklisted vehicle {normalized_plate} detected at {gate_name}.",
            related_plate=normalized_plate
        )
    elif flask_status == 'unknown':
        create_alert(
            alert_type='unknown',
            severity='medium',
            message=f"Unknown vehicle {normalized_plate} detected at {gate_name}.",
            related_plate=normalized_plate
        )
        
    return jsonify({
        'success': True,
        'message': 'Log synced successfully!',
        'local_log_id': log.id
    }), 201
