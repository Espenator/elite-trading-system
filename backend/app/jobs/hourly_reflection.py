"""Hourly Reflection Job — applies temporal decay to heuristics and logs summary.

Runs every hour:
1. Applies temporal decay to heuristic engine patterns
2. Computes cognitive mode from recent council decisions
3. Persists reflection snapshot for the Learning Summary panel
"""
import logging
import datetime

log = logging.getLogger(__name__)


def run() -> dict:
    """Execute hourly reflection. Returns summary dict."""
    ts = datetime.datetime.utcnow().isoformat()
    result = {"status": "ok", "timestamp": ts, "decayed": 0, "active_heuristics": 0}

    # 1. Apply temporal decay to heuristics
    try:
        from app.knowledge.heuristic_engine import get_heuristic_engine
        he = get_heuristic_engine()
        decayed = he.apply_temporal_decay()
        active = he.get_active_heuristics()
        result["decayed"] = decayed
        result["active_heuristics"] = len(active)
        log.info("Hourly reflection: decayed %d heuristics, %d active", decayed, len(active))
    except Exception as e:
        log.warning("Heuristic decay failed: %s", e)
        result["heuristic_error"] = str(e)

    # 2. Persist snapshot for dashboard
    try:
        from app.services.database import db_service
        snapshots = db_service.get_config("reflection_snapshots") or []
        snapshots.append(result)
        db_service.save_config("reflection_snapshots", snapshots[-168:])  # keep 7 days
    except Exception:
        pass

    return result
