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
