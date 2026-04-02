"""Security dashboard routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import login_required, current_user
from app import db
from app.models.entry_log import EntryLog
from app.services.gate_service import open_gate, close_gate, get_gate_status, get_recent_gate_actions
from app.services.alert_service import get_active_alerts, unresolved_count
from app.services.log_service import create_log, get_recent_logs
from app.services.anpr_service import ANPRPipeline
from app.utils.decorators import security_required
from flask import current_app
from pathlib import Path

security_bp = Blueprint('security', __name__)


@security_bp.before_request
@login_required
def require_login():
    pass


@security_bp.route('/')
@security_required
def monitor():
    recent = get_recent_logs(20)
    alerts = get_active_alerts(10)
    gate = get_gate_status()
    return render_template(
        'security/monitor.html',
        recent_logs=recent,
        alerts=alerts,
        gate=gate,
    )


@security_bp.route('/events')
@security_required
def events():
    recent = get_recent_logs(20)
    gate_actions = get_recent_gate_actions(10)
    return render_template('security/events.html', recent_logs=recent, gate_actions=gate_actions)


@security_bp.route('/gate/open', methods=['POST'])
@security_required
def gate_open():
    reason = request.form.get('reason', 'Manual override by security')
    log_id = request.form.get('log_id')
    open_gate(triggered_by='manual', reason=reason, operator_id=current_user.id)
    if log_id:
        log = db.session.get(EntryLog, int(log_id))
        if log:
            log.status = 'manual_allow'
            log.gate_action = 'open'
            db.session.commit()
    flash('Gate opened.', 'success')
    return redirect(url_for('security.monitor'))


@security_bp.route('/gate/close', methods=['POST'])
@security_required
def gate_close():
    close_gate(triggered_by='manual', reason='Manual close by security', operator_id=current_user.id)
    flash('Gate closed.', 'success')
    return redirect(url_for('security.monitor'))


@security_bp.route('/manual-deny', methods=['POST'])
@security_required
def manual_deny():
    log_id = request.form.get('log_id')
    reason = request.form.get('reason', 'Manually denied by security')
    if log_id:
        log = db.session.get(EntryLog, int(log_id))
        if log:
            log.status = 'manual_deny'
            log.gate_action = 'denied'
            log.notes = reason
            db.session.commit()
            flash(f'Entry denied for {log.normalized_plate}.', 'warning')
    return redirect(url_for('security.monitor'))


@security_bp.route('/process-frame', methods=['POST'])
@security_required
def process_frame():
    """Accept an uploaded image frame, run ANPR, return result JSON."""
    if 'frame' not in request.files:
        return jsonify({'success': False, 'error': 'No frame provided'}), 400

    file = request.files['frame']
    frame_bytes = file.read()
    if not frame_bytes:
        return jsonify({'success': False, 'error': 'Empty file'}), 400

    pipeline = ANPRPipeline(mode=current_app.config.get('ANPR_MODE', 'mock'))
    snapshot_dir = Path(current_app.config['SNAPSHOT_DIR'])
    dup_window = current_app.config.get('DUPLICATE_WINDOW_SECONDS', 10)

    result = pipeline.process_and_log(
        frame_bytes=frame_bytes,
        snapshot_dir=snapshot_dir,
        duplicate_window=dup_window,
        operator_id=current_user.id,
    )
    return jsonify(result)


@security_bp.route('/incident', methods=['POST'])
@security_required
def log_incident():
    """Quick incident log from security dashboard."""
    plate = request.form.get('plate', '').strip()
    notes = request.form.get('notes', '').strip()
    if not notes:
        flash('Notes are required for incident log.', 'warning')
        return redirect(url_for('security.monitor'))
    create_log(
        plate_text=plate,
        normalized_plate=plate.upper(),
        confidence=0.0,
        status='unknown',
        source='manual',
        notes=notes,
        operator_id=current_user.id,
    )
    flash('Incident logged.', 'success')
    return redirect(url_for('security.monitor'))
