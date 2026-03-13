"""
System status API — glass-box visibility of trading mode and module status.

APEX Phase 2 additions:
- /gpu endpoint: nvidia-smi introspection for GPU health monitoring
- Keeps /status exactly as before
"""
import logging
import subprocess
from typing import Any, Dict

from fastapi import APIRouter

from app.modules.social_news_engine import get_status as social_news_status
from app.modules.chart_patterns import get_status as chart_patterns_status
from app.modules.ml_engine import get_status as ml_engine_status
from app.modules.execution_engine import get_status as execution_status, get_trading_mode

log = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET "" — summary for Sidebar / Dashboard (activeAgents, healthy)
# Frontend calls GET /api/v1/system (no trailing path); without this, 404.
# ---------------------------------------------------------------------------
@router.get("")
async def system_summary():
    """Return short system summary for sidebar/UI. Use /status for full breakdown."""
    return await _system_summary_impl()


@router.get("/")
async def system_summary_slash():
    """Same as GET "" for clients that request /api/v1/system/."""
    return await _system_summary_impl()


async def _system_summary_impl():
    try:
        status = await system_status()
        modules = status.get("modules") or {}
        mod_list = list(modules.values()) if isinstance(modules, dict) else []
        ready = 0
        for m in mod_list:
            if isinstance(m, dict) and m.get("status") == "ready":
                ready += 1
            elif not isinstance(m, dict):
                ready += 1
        total = len(mod_list)
        healthy = total > 0 and ready >= total
        return {
            "activeAgents": ready,
            "healthy": healthy,
            "trading_mode": status.get("trading_mode", "live"),
        }
    except Exception as e:
        log.warning("system summary failed: %s", e)
        return {"activeAgents": 0, "healthy": False, "trading_mode": "live"}


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------
@router.get("/status")
async def system_status():
    """
    Return system-wide status for glass-box UI:
    - trading_mode: paper | live
    - modules: status of each component (symbol_universe, social_news, chart_patterns, ml_engine, execution)
    """
    return {
        "trading_mode": get_trading_mode(),
        "modules": {
            "symbol_universe": {
                "status": "ready",
                "description": "Stock/symbol database and watchlists",
            },
            "social_news_engine": social_news_status(),
            "chart_patterns": chart_patterns_status(),
            "ml_engine": ml_engine_status(),
            "execution_engine": execution_status(),
        },
    }


# ---------------------------------------------------------------------------
# /gpu  (APEX Phase 2 — nvidia-smi introspection)
# ---------------------------------------------------------------------------
def _run_nvidia_smi(args: list[str] | None = None) -> Dict[str, Any]:
    """Run nvidia-smi with optional args and return structured output."""
    cmd = ["nvidia-smi"] + (args or [])
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return {
                "available": False,
                "error": result.stderr.strip() or "nvidia-smi returned non-zero exit code",
            }
        return {
            "available": True,
            "output": result.stdout.strip(),
        }
    except FileNotFoundError:
        return {"available": False, "error": "nvidia-smi not found on PATH"}
    except subprocess.TimeoutExpired:
        return {"available": False, "error": "nvidia-smi timed out (>10s)"}
    except Exception as exc:
        log.debug("nvidia-smi error: %s", exc)
        return {"available": False, "error": "nvidia-smi execution error"}


def _parse_gpu_query() -> Dict[str, Any]:
    """Use nvidia-smi --query-gpu for structured GPU metrics."""
    fields = "name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw"
    result = _run_nvidia_smi([
        "--query-gpu=" + fields,
        "--format=csv,noheader,nounits",
    ])
    if not result.get("available"):
        return result

    gpus = []
    for line in result["output"].splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 8:
            gpus.append({
                "name": parts[0],
                "driver_version": parts[1],
                "memory_total_mb": _safe_float(parts[2]),
                "memory_used_mb": _safe_float(parts[3]),
                "memory_free_mb": _safe_float(parts[4]),
                "gpu_utilization_pct": _safe_float(parts[5]),
                "temperature_c": _safe_float(parts[6]),
                "power_draw_w": _safe_float(parts[7]),
            })

    return {
        "available": True,
        "gpu_count": len(gpus),
        "gpus": gpus,
    }


def _safe_float(val: str) -> float | None:
    """Convert string to float, returning None on failure."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


@router.get("/event-bus/status")
async def event_bus_status():
    """Return event bus metrics: topics, subscriber counts, message rates, and Redis bridge status."""
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        metrics = bus.get_metrics()
        topics = []
        events_by_topic = metrics.get("events_by_topic", {})
        subs_by_topic = metrics.get("subscribers", {})
        for topic in sorted(set(list(events_by_topic.keys()) + list(subs_by_topic.keys()))):
            topics.append({
                "topic": topic,
                "subs": subs_by_topic.get(topic, 0),
                "msgRate": events_by_topic.get(topic, 0),
                "lastMsg": f"{events_by_topic.get(topic, 0)} events processed",
            })
        return {
            "running": metrics.get("running", False),
            "topics": topics,
            "redis": metrics.get("redis", {"connected": False}),
        }
    except Exception as e:
        log.debug("event-bus status failed: %s", e)
        return {"running": False, "topics": [], "redis": {"connected": False}}


@router.get("/gpu")
async def gpu_status():
    """
    Return GPU health via nvidia-smi.

    Response includes per-GPU metrics:
    - name, driver_version
    - memory_total_mb, memory_used_mb, memory_free_mb
    - gpu_utilization_pct, temperature_c, power_draw_w

    Falls back gracefully if no NVIDIA GPU is present.
    """
    info = _parse_gpu_query()
    log.info("GPU status requested: available=%s", info.get("available"))
    return info


@router.get("/gpu/raw")
async def gpu_raw():
    """Return raw nvidia-smi text output (full dashboard view)."""
    return _run_nvidia_smi()


# ---------------------------------------------------------------------------
# /device  — Device identity for multi-PC setups
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# /rate-limits  (D2 — per-service rate limiter status)
# ---------------------------------------------------------------------------
@router.get("/rate-limits")
async def rate_limits():
    """Return status of all registered per-service rate limiters."""
    try:
        from app.core.rate_limiter import get_all_limiter_statuses
        return {"limiters": get_all_limiter_statuses()}
    except Exception as e:
        log.debug("rate-limits failed: %s", e)
        return {"limiters": []}


# ---------------------------------------------------------------------------
# /circuit-breakers  (D4 — scraper circuit breaker status)
# ---------------------------------------------------------------------------
@router.get("/circuit-breakers")
async def circuit_breakers():
    """Return status of all registered circuit breakers."""
    try:
        from app.core.rate_limiter import get_all_circuit_breaker_statuses
        return {"circuit_breakers": get_all_circuit_breaker_statuses()}
    except Exception as e:
        log.debug("circuit-breakers failed: %s", e)
        return {"circuit_breakers": []}


# ---------------------------------------------------------------------------
# /backfill/status  (D1 — backfill orchestrator status)
# ---------------------------------------------------------------------------
@router.get("/backfill/status")
async def backfill_status():
    """Return backfill orchestrator status including TurboScanner gate."""
    try:
        from app.services.backfill_orchestrator import backfill_orchestrator
        return backfill_orchestrator.get_status()
    except Exception as e:
        log.debug("backfill status failed: %s", e)
        return {"status": "unavailable", "error": "backfill status unavailable"}


# ---------------------------------------------------------------------------
# /dlq  (D3 — Dead-letter queue inspection + replay)
# ---------------------------------------------------------------------------
@router.get("/dlq")
async def dlq_list(limit: int = 50):
    """Return recent dead-letter queue entries."""
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        entries = await bus.get_dlq(limit=limit)
        return {
            "count": len(entries),
            "entries": entries,
        }
    except Exception as e:
        log.debug("dlq list failed: %s", e)
        return {"count": 0, "entries": []}


@router.post("/dlq/replay")
async def dlq_replay(topic: str = None, limit: int = 50):
    """Replay dead-letter queue entries back onto the MessageBus."""
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        count = await bus.replay_dlq(topic=topic, limit=limit)
        return {"replayed": count, "filter_topic": topic}
    except Exception as e:
        log.warning("dlq replay failed: %s", e)
        return {"replayed": 0, "error": "DLQ replay failed"}


@router.delete("/dlq")
async def dlq_clear():
    """Clear the dead-letter queue."""
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        count = bus.clear_dlq()
        return {"cleared": count}
    except Exception as e:
        log.warning("dlq clear failed: %s", e)
        return {"cleared": 0, "error": "DLQ clear failed"}


# ---------------------------------------------------------------------------
# /session-scanner  (D5 — session scanner status)
# ---------------------------------------------------------------------------
@router.get("/session-scanner")
async def session_scanner_status():
    """Return pre-market/after-hours session scanner status."""
    try:
        from app.services.session_scanner import get_session_scanner
        scanner = get_session_scanner()
        return scanner.get_status()
    except Exception as e:
        log.debug("session-scanner status failed: %s", e)
        return {"running": False, "error": "session scanner unavailable"}


# ---------------------------------------------------------------------------
# /swarm-status  — Data swarm session + which sources are firing (post-market check)
# ---------------------------------------------------------------------------
@router.get("/swarm-status")
async def swarm_status():
    """
    Return current trading session and which data sources should be firing.
    Use this to confirm post-market (4 PM–8 PM ET): Alpaca, UW (no flow), FinViz all active.
    """
    import os
    try:
        from app.services.data_swarm import get_session_clock, get_health_monitor
        clock = get_session_clock()
        session = clock.get_current_session()
        active = clock.get_active_sources()
        health = get_health_monitor()
        session_value = session.value if hasattr(session, "value") else str(session)
        firing = [k for k, v in active.items() if v]
        not_firing = [k for k, v in active.items() if not v]
        return {
            "session": session_value,
            "active_sources": active,
            "sources_firing": firing,
            "sources_idle": not_firing,
            "collector_health": health.get_status(),
            "data_freshness_symbols": list(health.get_freshness().keys())[:20],
            "swarm_enabled": os.getenv("DATA_SWARM_ENABLED", "").lower() in ("1", "true", "yes"),
            "message": f"Session={session_value}. Firing: {len(firing)} sources.",
        }
    except Exception as e:
        log.debug("swarm-status failed: %s", e)
        return {
            "session": "unknown",
            "active_sources": {},
            "sources_firing": [],
            "sources_idle": [],
            "swarm_enabled": False,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# /device  — Device identity for multi-PC setups
# ---------------------------------------------------------------------------
@router.get("/device")
async def device_info():
    """Return this device's identity and system info for the Electron shell and Settings UI."""
    import os
    import platform
    import socket

    from app.services.settings_service import get_settings_by_category

    device_settings = get_settings_by_category("device")

    return {
        "deviceName": device_settings.get("deviceName") or socket.gethostname(),
        "deviceRole": device_settings.get("deviceRole", "full"),
        "hostname": socket.gethostname(),
        "platform": platform.system().lower(),
        "arch": platform.machine(),
        "pythonVersion": platform.python_version(),
        "cpuCount": os.cpu_count(),
        "backendPort": device_settings.get("backendPort", 8000),
        "tradingMode": device_settings.get("tradingMode", "live"),
        "peerDevices": device_settings.get("peerDevices", []),
        "brainHost": device_settings.get("brainHost", "localhost"),
        "brainPort": device_settings.get("brainPort", 50051),
    }
