"""
Outcome resolver: record signal outcomes and feed accuracy back (flywheel).
Stores resolved outcomes in config; ML engine can use for retrain weighting or metrics.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from app.services.database import db_service

logger = logging.getLogger(__name__)

CONFIG_KEY = "ml_outcome_resolver"
# Shape: { "resolved": [ {"symbol", "date", "signal_date", "outcome": 0|1, "resolved_at": iso } ], "accuracy_30d": 0.65, "accuracy_90d": 0.62 }


def _get_store():
    return db_service.get_config(CONFIG_KEY) or {
        "resolved": [],
        "accuracy_30d": None,
        "accuracy_90d": None,
    }


def _set_store(data: dict):
    db_service.set_config(CONFIG_KEY, data)


def record_outcome(
    symbol: str,
    signal_date: str,
    outcome: Optional[int] = None,
    prediction: Optional[int] = None,
    resolved_at: Optional[str] = None,
):
    """Record one resolved outcome (0 = down, 1 = up). Optional prediction (0/1) for accuracy.

    If outcome is None, the entry is recorded as pending (not yet resolved).
    """
    from datetime import datetime, timezone

    store = _get_store()
    resolved = store.get("resolved") or []
    resolved.append(
        {
            "symbol": symbol.upper(),
            "signal_date": signal_date,
            "outcome": (1 if outcome else 0) if outcome is not None else None,
            "prediction": prediction if prediction is not None else None,
            "resolved_at": resolved_at or datetime.now(timezone.utc).isoformat(),
        }
    )
    store["resolved"] = resolved[-2000:]
    _recompute_accuracy(store)
    _set_store(store)


def _recompute_accuracy(store: dict):
    """Update accuracy_30d and accuracy_90d from resolved list (prediction vs outcome when available)."""
    resolved = store.get("resolved") or []
    if not resolved:
        store["accuracy_30d"] = None
        store["accuracy_90d"] = None
        return
    try:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        cut_30 = (now - timedelta(days=30)).isoformat()
        cut_90 = (now - timedelta(days=90)).isoformat()
        r30 = [
            r
            for r in resolved
            if (r.get("resolved_at") or "") >= cut_30
            and r.get("prediction") is not None
        ]
        r90 = [
            r
            for r in resolved
            if (r.get("resolved_at") or "") >= cut_90
            and r.get("prediction") is not None
        ]

        def acc(xs):
            if not xs:
                return None
            correct = sum(1 for x in xs if x.get("prediction") == x.get("outcome"))
            return round(correct / len(xs), 4)

        store["accuracy_30d"] = acc(r30)
        store["accuracy_90d"] = acc(r90)
    except Exception:
        store["accuracy_30d"] = None
        store["accuracy_90d"] = None


def get_flywheel_metrics() -> dict:
    """Return metrics for flywheel API and ML status."""
    store = _get_store()
    resolved = store.get("resolved") or []
    return {
        "resolved_count": len(resolved),
        "accuracy_30d": store.get("accuracy_30d"),
        "accuracy_90d": store.get("accuracy_90d"),
        "pending_resolution": 0,  # Could be derived from open signals vs resolved
    }
