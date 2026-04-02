"""Role-based access control decorators."""
from functools import wraps
from flask import abort
from flask_login import current_user


def admin_required(f):
    """Restrict route to admin users only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated


def security_required(f):
    """Restrict route to security or admin users."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or (
            not current_user.is_security() and not current_user.is_admin()
        ):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def resident_required(f):
    """Restrict route to resident users."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_resident():
            abort(403)
        return f(*args, **kwargs)
    return decorated
