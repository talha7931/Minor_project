"""Camera configuration model."""
from app import db


class CameraConfig(db.Model):
    """Camera source and capture settings."""
    __tablename__ = 'camera_configs'

    id = db.Column(db.Integer, primary_key=True)
    source_type = db.Column(db.String(20), default='upload')  # webcam | upload | picamera2
    resolution_w = db.Column(db.Integer, default=640)
    resolution_h = db.Column(db.Integer, default=480)
    fps = db.Column(db.Integer, default=15)
    enabled = db.Column(db.Boolean, default=True)
    frame_skip = db.Column(db.Integer, default=5)
    jpeg_quality = db.Column(db.Integer, default=75)

    def __repr__(self):
        return f'<CameraConfig {self.source_type} {self.resolution_w}x{self.resolution_h}>'
