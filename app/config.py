"""Application configuration."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    # Use DATABASE_URL from .env or fallback to SQLite
    db_url = os.environ.get('DATABASE_URL', f'sqlite:///{BASE_DIR}/instance/gate_system.db')
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+pg8000://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)
    
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Camera settings
    CAMERA_MODE = os.environ.get('CAMERA_MODE', 'upload')  # webcam | upload | picamera2

    # ANPR settings
    ANPR_MODE = os.environ.get('ANPR_MODE', 'mock')  # mock | live
    FRAME_SKIP = int(os.environ.get('FRAME_SKIP', 5))
    JPEG_QUALITY = int(os.environ.get('JPEG_QUALITY', 75))
    PROCESSING_WIDTH = int(os.environ.get('PROCESSING_WIDTH', 640))
    PROCESSING_HEIGHT = int(os.environ.get('PROCESSING_HEIGHT', 480))
    DUPLICATE_WINDOW_SECONDS = int(os.environ.get('DUPLICATE_WINDOW_SECONDS', 10))

    # Gate settings
    AUTO_ALLOW_AUTHORIZED = os.environ.get('AUTO_ALLOW_AUTHORIZED', 'true').lower() == 'true'
    AUTO_DENY_BLACKLISTED = os.environ.get('AUTO_DENY_BLACKLISTED', 'true').lower() == 'true'

    # Snapshot directory
    SNAPSHOT_DIR = BASE_DIR / 'snapshots'

    # Upload directory
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
