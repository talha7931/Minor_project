"""Admin dashboard routes."""
import io
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app import db
from app.models.user import User, ResidentProfile
from app.models.vehicle import Vehicle
from app.models.entry_log import EntryLog
from app.models.alert import Alert
from app.models.system_setting import SystemSetting
from app.services.auth_service import create_user, toggle_user_active
from app.services.vehicle_service import add_vehicle, toggle_blacklist, get_all_vehicles
from app.services.log_service import search_logs, today_stats, export_logs_csv
from app.services.alert_service import get_all_alerts, resolve_alert, unresolved_count
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
@login_required
def require_login():
    pass


@admin_bp.route('/')
@admin_required
def overview():
    stats = today_stats()
    alert_count = unresolved_count()
    total_vehicles = Vehicle.query.count()
    total_residents = User.query.filter_by(role='resident').count()
    recent_logs = EntryLog.query.order_by(EntryLog.timestamp.desc()).limit(10).all()
    return render_template(
        'admin/overview.html',
        stats=stats,
        alert_count=alert_count,
        total_vehicles=total_vehicles,
        total_residents=total_residents,
        recent_logs=recent_logs,
    )


@admin_bp.route('/residents')
@admin_required
def residents():
    users = User.query.filter_by(role='resident').order_by(User.created_at.desc()).all()
    return render_template('admin/residents.html', users=users)


@admin_bp.route('/residents/add', methods=['GET', 'POST'])
@admin_required
def add_resident():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        flat_no = request.form.get('flat_no', '').strip()
        phone = request.form.get('phone', '').strip()
        if not all([name, email, password, flat_no]):
            flash('All fields are required.', 'danger')
        elif User.query.filter_by(email=email.lower()).first():
            flash('Email already in use.', 'danger')
        else:
            create_user(name, email, password, role='resident', flat_no=flat_no, phone=phone)
            flash(f'Resident {name} added successfully.', 'success')
            return redirect(url_for('admin.residents'))
    return render_template('admin/add_resident.html')


@admin_bp.route('/residents/<int:user_id>/toggle')
@admin_required
def toggle_resident(user_id):
    user = db.session.get(User, user_id)
    if user:
        toggle_user_active(user)
        flash(f'User {user.name} {"activated" if user.active else "deactivated"}.', 'info')
    return redirect(url_for('admin.residents'))


@admin_bp.route('/vehicles')
@admin_required
def vehicles():
    all_vehicles = get_all_vehicles()
    residents = ResidentProfile.query.all()
    return render_template('admin/vehicles.html', vehicles=all_vehicles, residents=residents)


@admin_bp.route('/vehicles/add', methods=['POST'])
@admin_required
def add_vehicle_route():
    resident_id = request.form.get('resident_id')
    plate = request.form.get('plate_number', '').strip()
    vtype = request.form.get('vehicle_type', 'car')
    color = request.form.get('color', '').strip()
    brand = request.form.get('brand', '').strip()
    if not resident_id or not plate:
        flash('Resident and plate number are required.', 'danger')
    elif Vehicle.query.filter_by(plate_number=plate.upper()).first():
        flash('Plate number already registered.', 'warning')
    else:
        add_vehicle(int(resident_id), plate, vtype, color, brand)
        flash(f'Vehicle {plate.upper()} added.', 'success')
    return redirect(url_for('admin.vehicles'))


@admin_bp.route('/vehicles/<int:vehicle_id>/toggle-blacklist')
@admin_required
def toggle_vehicle_blacklist(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if vehicle:
        status = toggle_blacklist(vehicle)
        label = 'blacklisted' if status else 'removed from blacklist'
        flash(f'Vehicle {vehicle.plate_number} {label}.', 'warning' if status else 'success')
    return redirect(url_for('admin.vehicles'))


@admin_bp.route('/logs')
@admin_required
def logs():
    plate = request.args.get('plate', '')
    status = request.args.get('status', '')
    date_from_str = request.args.get('date_from', '')
    date_to_str = request.args.get('date_to', '')
    page = int(request.args.get('page', 1))
    per_page = 25

    date_from = datetime.strptime(date_from_str, '%Y-%m-%d') if date_from_str else None
    date_to = datetime.strptime(date_to_str, '%Y-%m-%d') if date_to_str else None

    all_logs, total = search_logs(
        plate=plate, status=status,
        date_from=date_from, date_to=date_to,
        limit=per_page, offset=(page - 1) * per_page
    )
    pages = (total + per_page - 1) // per_page
    return render_template(
        'admin/logs.html',
        logs=all_logs, total=total, page=page, pages=pages,
        plate=plate, status=status,
        date_from=date_from_str, date_to=date_to_str,
    )


@admin_bp.route('/logs/export')
@admin_required
def export_logs():
    plate = request.args.get('plate', '')
    status = request.args.get('status', '')
    all_logs, _ = search_logs(plate=plate, status=status, limit=10000)
    csv_data = export_logs_csv(all_logs)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=entry_logs.csv'}
    )


@admin_bp.route('/alerts')
@admin_required
def alerts():
    all_alerts = get_all_alerts(limit=100)
    return render_template('admin/alerts.html', alerts=all_alerts)


@admin_bp.route('/alerts/<int:alert_id>/resolve')
@admin_required
def resolve_alert_route(alert_id):
    resolve_alert(alert_id)
    flash('Alert resolved.', 'success')
    return redirect(url_for('admin.alerts'))


@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        for key in ['auto_allow_authorized', 'auto_deny_blacklisted',
                    'duplicate_window_seconds', 'anpr_mode', 'camera_mode']:
            val = request.form.get(key)
            if val is not None:
                SystemSetting.set(key, val)
        flash('Settings saved.', 'success')
        return redirect(url_for('admin.settings'))
    all_settings = {
        s.key: s.value for s in SystemSetting.query.all()
    }
    users = User.query.order_by(User.role, User.name).all()
    return render_template('admin/settings.html', settings=all_settings, users=users)
