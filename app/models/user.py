"""User and ResidentProfile models."""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class User(UserMixin, db.Model):
    """User account model supporting admin, security, and resident roles."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='resident')  # admin | security | resident
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    resident_profile = db.relationship('ResidentProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_security(self):
        return self.role == 'security'

    def is_resident(self):
        return self.role == 'resident'

    def __repr__(self):
        return f'<User {self.email} [{self.role}]>'


class ResidentProfile(db.Model):
    """Additional profile info for resident users."""
    __tablename__ = 'resident_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    flat_no = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20))

    user = db.relationship('User', back_populates='resident_profile')
    vehicles = db.relationship('Vehicle', back_populates='resident', cascade='all, delete-orphan')
    visitor_passes = db.relationship('VisitorPass', back_populates='resident', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ResidentProfile flat={self.flat_no}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
