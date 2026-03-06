"""Governance Logger Job — audit trail of system mode changes and operator actions.

Runs every 15 minutes:
1. Logs current system mode and operator override state
2. Records agent enable/disable status
3. Persists governance audit trail for compliance
"""
import logging
import datetime
import os

log = logging.getLogger(__name__)


def run() -> dict:
    """Execute governance snapshot. Returns audit dict."""
    ts = datetime.datetime.utcnow().isoformat()
    result = {
        "status": "ok",
        "timestamp": ts,
        "system_mode": os.environ.get("SYSTEM_MODE", "SHADOW"),
    }

    # Record agent overrides
    try:
        from app.api.v1.council import _agent_overrides
        result["agent_overrides"] = dict(_agent_overrides)
    except Exception:
        result["agent_overrides"] = {}

    # Record council gate status
    try:
        import app.main as main_mod
        gate = getattr(main_mod, "_council_gate", None)
        if gate:
            result["gate_status"] = gate.get_status()
    except Exception:
        pass

    # Record current weights
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        result["agent_weights"] = learner.get_weights()
        result["weight_updates"] = learner.update_count
    except Exception:
        pass

    # Persist governance log
    try:
        from app.services.database import db_service
        gov_log = db_service.get_config("governance_log") or []
        gov_log.append(result)
        db_service.save_config("governance_log", gov_log[-960:])  # keep 10 days at 15min intervals
    except Exception:
        pass

    return result
