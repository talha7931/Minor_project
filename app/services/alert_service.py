"""Alert creation and management service."""
from app import db
from app.models.alert import Alert


def create_alert(alert_type: str, message: str, related_plate: str = '',
                 severity: str = 'medium') -> Alert:
    """Create a new system alert."""
    alert = Alert(
        type=alert_type,
        severity=severity,
        message=message,
        related_plate=related_plate,
        resolved=False,
    )
    db.session.add(alert)
    db.session.commit()
    return alert


def get_active_alerts(limit=50):
    return Alert.query.filter_by(resolved=False).order_by(
        Alert.created_at.desc()
    ).limit(limit).all()


def get_all_alerts(limit=100):
    return Alert.query.order_by(Alert.created_at.desc()).limit(limit).all()


def resolve_alert(alert_id: int) -> bool:
    alert = db.session.get(Alert, alert_id)
    if alert:
        alert.resolve()
        db.session.commit()
        return True
    return False


def unresolved_count() -> int:
    return Alert.query.filter_by(resolved=False).count()
