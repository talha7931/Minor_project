"""Authentication and user management service."""
from app import db
from app.models.user import User, ResidentProfile


def get_user_by_email(email: str):
    return User.query.filter_by(email=email.lower().strip()).first()


def create_user(name: str, email: str, password: str, role: str = 'resident',
                flat_no: str = None, phone: str = None) -> User:
    """Create a new user with an optional resident profile."""
    user = User(name=name, email=email.lower().strip(), role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    if role == 'resident' and flat_no:
        profile = ResidentProfile(user_id=user.id, flat_no=flat_no, phone=phone or '')
        db.session.add(profile)

    db.session.commit()
    return user


def update_user(user: User, **kwargs) -> User:
    """Update user fields."""
    for k, v in kwargs.items():
        if k == 'password':
            user.set_password(v)
        elif hasattr(user, k):
            setattr(user, k, v)
    db.session.commit()
    return user


def toggle_user_active(user: User) -> bool:
    """Toggle the active status of a user."""
    user.active = not user.active
    db.session.commit()
    return user.active


def get_all_users():
    return User.query.order_by(User.created_at.desc()).all()
