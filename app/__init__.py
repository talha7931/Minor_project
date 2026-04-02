"""Flask application factory."""
import os
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from .config import config

BASE_DIR = Path(__file__).parent.parent

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config.get(config_name, config['default']))

    # Ensure required directories exist
    Path(app.config['SNAPSHOT_DIR']).mkdir(parents=True, exist_ok=True)
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    (BASE_DIR / 'instance').mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    with app.app_context():
        from .models import user as user_models  # noqa: ensure models registered
        from .routes.auth import auth_bp
        from .routes.admin import admin_bp
        from .routes.security import security_bp
        from .routes.resident import resident_bp
        from .routes.api import api_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(security_bp, url_prefix='/security')
        app.register_blueprint(resident_bp, url_prefix='/resident')
        app.register_blueprint(api_bp, url_prefix='/api')

        db.create_all()

    return app
