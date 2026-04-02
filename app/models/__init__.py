"""Database models package."""
from app import db
from .user import User, ResidentProfile
from .vehicle import Vehicle
from .entry_log import EntryLog
from .visitor_pass import VisitorPass
from .alert import Alert
from .gate_action import GateAction
from .camera_config import CameraConfig
from .system_setting import SystemSetting

__all__ = [
    'User', 'ResidentProfile', 'Vehicle', 'EntryLog',
    'VisitorPass', 'Alert', 'GateAction', 'CameraConfig', 'SystemSetting'
]
