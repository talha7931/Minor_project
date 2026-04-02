"""Resident dashboard routes."""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.vehicle import Vehicle
from app.models.visitor_pass import VisitorPass
from app.models.alert import Alert
from app.services.vehicle_service import add_vehicle, create_visitor_pass, get_vehicles_for_resident
from app.services.log_service import get_logs_for_resident
from app.utils.decorators import resident_required

resident_bp = Blueprint('resident', __name__)


@resident_bp.before_request
@login_required
def require_login():
    pass


def _get_profile():
    """Helper to get current user's resident profile."""
    if not current_user.resident_profile:
        flash('No resident profile found. Contact admin.', 'danger')
        return None
    return current_user.resident_profile


@resident_bp.route('/vehicles')
@resident_required
def my_vehicles():
    profile = _get_profile()
    if not profile:
        return redirect(url_for('auth.logout'))
    vehicles = get_vehicles_for_resident(profile.id)
    return render_template('resident/vehicles.html', vehicles=vehicles, profile=profile)


@resident_bp.route('/vehicles/add', methods=['POST'])
@resident_required
def add_vehicle_route():
    profile = _get_profile()
    if not profile:
        return redirect(url_for('auth.logout'))

    plate = request.form.get('plate_number', '').strip().upper()
    vtype = request.form.get('vehicle_type', 'car')
    color = request.form.get('color', '').strip()
    brand = request.form.get('brand', '').strip()

    if not plate:
        flash('Plate number is required.', 'danger')
        return redirect(url_for('resident.my_vehicles'))

    if Vehicle.query.filter_by(plate_number=plate).first():
        flash('This plate is already registered.', 'warning')
        return redirect(url_for('resident.my_vehicles'))

    add_vehicle(profile.id, plate, vtype, color, brand)
    flash(f'Vehicle {plate} added. Admin will review and activate shortly.', 'success')
    return redirect(url_for('resident.my_vehicles'))


@resident_bp.route('/history')
@resident_required
def history():
    profile = _get_profile()
    if not profile:
        return redirect(url_for('auth.logout'))
    logs = get_logs_for_resident(profile.id, limit=50)
    return render_template('resident/history.html', logs=logs)


@resident_bp.route('/visitor-passes')
@resident_required
def visitor_passes():
    profile = _get_profile()
    if not profile:
        return redirect(url_for('auth.logout'))
    passes = VisitorPass.query.filter_by(resident_id=profile.id).order_by(
        VisitorPass.created_at.desc()
    ).all()
    return render_template('resident/visitor_passes.html', passes=passes)


@resident_bp.route('/visitor-passes/add', methods=['POST'])
@resident_required
def add_visitor_pass():
    profile = _get_profile()
    if not profile:
        return redirect(url_for('auth.logout'))

    visitor_name = request.form.get('visitor_name', '').strip()
    vehicle_plate = request.form.get('vehicle_plate', '').strip()
    valid_from_str = request.form.get('valid_from', '')
    valid_to_str = request.form.get('valid_to', '')
    notes = request.form.get('notes', '').strip()

    if not all([visitor_name, valid_from_str, valid_to_str]):
        flash('Visitor name and date range are required.', 'danger')
        return redirect(url_for('resident.visitor_passes'))

    try:
        valid_from = datetime.strptime(valid_from_str, '%Y-%m-%dT%H:%M')
        valid_to = datetime.strptime(valid_to_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('resident.visitor_passes'))

    if valid_to <= valid_from:
        flash('End date must be after start date.', 'danger')
        return redirect(url_for('resident.visitor_passes'))

    create_visitor_pass(profile.id, visitor_name, vehicle_plate, valid_from, valid_to, notes)
    flash(f'Visitor pass created for {visitor_name}.', 'success')
    return redirect(url_for('resident.visitor_passes'))


@resident_bp.route('/alerts')
@resident_required
def my_alerts():
    profile = _get_profile()
    if not profile:
        return redirect(url_for('auth.logout'))
    # Show alerts for plates belonging to this resident
    vehicle_plates = [v.plate_number for v in profile.vehicles]
    alerts = Alert.query.filter(
        Alert.related_plate.in_(vehicle_plates)
    ).order_by(Alert.created_at.desc()).limit(30).all() if vehicle_plates else []
    return render_template('resident/alerts.html', alerts=alerts)
