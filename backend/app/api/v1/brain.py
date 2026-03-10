"""Brain health API: ideas/sec, signals/sec, council stats, order stats, queue depths, degraded mode."""
from __future__ import annotations

import time
from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter()

# Age in seconds beyond which market data is considered stale for degraded mode
MARKET_DATA_STALE_SEC = 300  # 5 min


@router.get("/health")
async def brain_health() -> Dict[str, Any]:
    """Aggregate brain health: throughput, council pass/veto/hold, orders, queue depths, last event timestamps."""
    out: Dict[str, Any] = {
        "ideas_per_sec": 0.0,
        "signals_per_sec": 0.0,
        "council_eval_per_sec": 0.0,
        "council_pass_ratio": 0.0,
        "council_veto_ratio": 0.0,
        "council_hold_ratio": 0.0,
        "order_submitted": 0,
        "order_filled": 0,
        "order_rejected": 0,
        "queue_depths": {},
        "dropped_counts": {},
        "last_event_timestamps": {},
        "timestamp": time.time(),
    }
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        if hasattr(bus, "_metrics"):
            m = bus._metrics
            total_ideas = m.get("swarm.idea", 0)
            total_signals = m.get("signal.generated", 0)
            total_council = m.get("council.verdict", 0)
            total_submitted = m.get("order.submitted", 0)
            total_filled = m.get("order.filled", 0)
            total_cancelled = m.get("order.cancelled", 0)
            out["order_submitted"] = total_submitted
            out["order_filled"] = total_filled
            out["order_rejected"] = total_cancelled
            uptime = getattr(bus, "_start_time", None)
            if uptime:
                sec = max(1, time.time() - uptime)
                out["ideas_per_sec"] = round(total_ideas / sec, 4)
                out["signals_per_sec"] = round(total_signals / sec, 4)
                out["council_eval_per_sec"] = round(total_council / sec, 4)
        if hasattr(bus, "_queue"):
            out["queue_depths"]["message_bus"] = bus._queue.qsize()
    except Exception:
        pass
    try:
        import app.main as main_mod
        cg = getattr(main_mod, "_council_gate", None)
        if cg and hasattr(cg, "get_status"):
            st = cg.get_status()
            inv = max(1, st.get("councils_invoked", 1))
            out["council_pass_ratio"] = round(st.get("councils_passed", 0) / inv, 3)
            out["council_veto_ratio"] = round(st.get("councils_vetoed", 0) / inv, 3)
            out["council_hold_ratio"] = round(st.get("councils_held", 0) / inv, 3)
            out["last_event_timestamps"]["council_gate"] = st.get("uptime_seconds", 0)
    except Exception:
        pass
    try:
        from app.services.idea_triage import get_idea_triage_service
        triage = get_idea_triage_service()
        if hasattr(triage, "get_status"):
            st = triage.get_status()
            out["dropped_counts"]["triage"] = st.get("dropped", 0) or st.get("dropped_count", 0)
    except Exception:
        pass
    return out


def get_degraded_status() -> Dict[str, Any]:
    """Compute global degraded mode for operator truth (trading safety).
    Returns degraded=True if any critical data source is stale or unavailable.
    Used by OrderExecutor to refuse AUTO execution when degraded (unless override).
    """
    reasons: List[str] = []
    details: Dict[str, Any] = {}
    now = time.time()

    # Market data: require recent bar/quote in PriceCache (or skip if cache not used)
    try:
        from app.services.price_cache_service import get_price_cache
        cache = get_price_cache()
        last_ts = cache.get_last_update_time()
        if last_ts is None:
            reasons.append("market_data_stale")
            details["market_data_stale"] = {"reason": "no_cached_prices", "age_sec": None}
        elif (now - last_ts) > MARKET_DATA_STALE_SEC:
            reasons.append("market_data_stale")
            details["market_data_stale"] = {"reason": "cached_prices_too_old", "age_sec": round(now - last_ts, 1)}
    except Exception as e:
        reasons.append("market_data_stale")
        details["market_data_stale"] = {"reason": "price_cache_unavailable", "error": str(e)}

    # Risk: optional — add risk_stale if risk service exposes last_update and it's old
    try:
        from app.services.database import db_service
        cfg = db_service.get_config("risk") or {}
        last_ts = cfg.get("last_update_ts") or cfg.get("last_updated")
        if last_ts:
            try:
                age = now - float(last_ts)
                if age > 600:
                    reasons.append("risk_stale")
                    details["risk_stale"] = {"age_sec": round(age, 1)}
            except (TypeError, ValueError):
                pass
    except Exception:
        pass

    # LLM: optional — if LLM health monitor reports unavailable
    try:
        from app.services.llm_health_monitor import get_llm_health_monitor
        mon = get_llm_health_monitor()
        if hasattr(mon, "is_healthy") and not mon.is_healthy():
            reasons.append("llm_unavailable")
            details["llm_unavailable"] = {"reason": "health_check_failed"}
    except Exception:
        pass

    # WS: optional — no frontend connected (informational)
    try:
        from app.websocket_manager import get_connection_count
        cnt = get_connection_count()
        if cnt == 0:
            reasons.append("ws_disconnected")
            details["ws_disconnected"] = {"subscriber_count": 0}
    except Exception:
        pass

    degraded = len(reasons) > 0
    return {
        "degraded": degraded,
        "reasons": reasons,
        "details": details,
        "timestamp": now,
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
    }


@router.get("/degraded")
async def brain_degraded() -> Dict[str, Any]:
    """Return real-time degraded mode status for operator awareness and UI banner.
    When degraded=True, OrderExecutor refuses AUTO execution unless DEGRADED_MODE_OVERRIDE is set.
    """
    return get_degraded_status()
