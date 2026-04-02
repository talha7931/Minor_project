"""Authentication routes: login and logout."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    """Root redirect based on login state and role."""
    if current_user.is_authenticated:
        return _dashboard_redirect()
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _dashboard_redirect()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.active:
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return _dashboard_redirect()
        else:
            flash('Invalid email or password, or account is deactivated.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


def _dashboard_redirect():
    role_map = {
        'admin': 'admin.overview',
        'security': 'security.monitor',
        'resident': 'resident.my_vehicles',
    }
    target = role_map.get(current_user.role, 'auth.login')
    return redirect(url_for(target))
