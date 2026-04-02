"""Application configuration."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    # Always use SQLite for this project (ignores Replit's PostgreSQL DATABASE_URL)
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{BASE_DIR}/instance/gate_system.db'
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
