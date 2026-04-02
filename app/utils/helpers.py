"""Utility helper functions."""
import re
from datetime import datetime


INDIAN_PLATE_PATTERN = re.compile(
    r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$'
)


def normalize_plate(raw_text: str) -> str:
    """Normalize raw OCR text to Indian plate format (e.g., MH12AB1234)."""
    if not raw_text:
        return ''
    cleaned = re.sub(r'[^A-Z0-9]', '', raw_text.upper().strip())
    return cleaned


def is_valid_indian_plate(plate: str) -> bool:
    """Check if a plate matches the standard Indian number plate format."""
    return bool(INDIAN_PLATE_PATTERN.match(plate))


def format_datetime(dt: datetime) -> str:
    """Format a datetime object for display."""
    if not dt:
        return '-'
    return dt.strftime('%d %b %Y, %I:%M %p')


def time_ago(dt: datetime) -> str:
    """Return human-readable time elapsed since dt."""
    if not dt:
        return ''
    now = datetime.utcnow()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return f'{seconds}s ago'
    elif seconds < 3600:
        return f'{seconds // 60}m ago'
    elif seconds < 86400:
        return f'{seconds // 3600}h ago'
    else:
        return f'{seconds // 86400}d ago'


def confidence_color(confidence: float) -> str:
    """Return a CSS class based on OCR confidence value."""
    if confidence >= 85:
        return 'success'
    elif confidence >= 60:
        return 'warning'
    return 'danger'


def status_badge(status: str) -> str:
    """Return CSS badge class for a given entry status."""
    mapping = {
        'authorized': 'badge-authorized',
        'visitor': 'badge-visitor',
        'blocked': 'badge-blocked',
        'unknown': 'badge-unknown',
        'manual_allow': 'badge-manual-allow',
        'manual_deny': 'badge-manual-deny',
    }
    return mapping.get(status, 'badge-secondary')
