"""Gate simulation and control service."""
from datetime import datetime
from app import db
from app.models.gate_action import GateAction

# In-memory gate state (in production this would connect to hardware GPIO)
_gate_state = {'status': 'closed', 'last_action': None}


def get_gate_status() -> dict:
    """Return current gate state."""
    return dict(_gate_state)


def trigger_gate(action: str, triggered_by: str = 'auto',
                 reason: str = '', operator_id: int = None) -> GateAction:
    """
    Simulate opening or closing the gate.
    On Raspberry Pi, replace simulation with GPIO calls here.
    """
    global _gate_state
    _gate_state['status'] = 'open' if action == 'open' else 'closed'
    _gate_state['last_action'] = datetime.utcnow().isoformat()

    gate_action = GateAction(
        action=action,
        triggered_by=triggered_by,
        reason=reason,
        operator_id=operator_id,
    )
    db.session.add(gate_action)
    db.session.commit()
    return gate_action


def open_gate(triggered_by='auto', reason='', operator_id=None) -> GateAction:
    return trigger_gate('open', triggered_by, reason, operator_id)


def close_gate(triggered_by='auto', reason='', operator_id=None) -> GateAction:
    return trigger_gate('close', triggered_by, reason, operator_id)


def get_recent_gate_actions(limit=20):
    return GateAction.query.order_by(GateAction.timestamp.desc()).limit(limit).all()
