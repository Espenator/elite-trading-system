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
@router.get("/event-bus/status")
async def event_bus_status():
    """
    Event-bus / MessageBus status for Agent Command Center Blackboard Live Feed.
    Returns topic list and subscriber counts when available; stub when no event-bus.
    """
    return {"topics": [], "subscribers": 0}


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
        return {"available": False, "error": str(exc)}


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
    """Return event bus metrics: topics, subscriber counts, message rates."""
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        metrics = bus.get_metrics()
        topics = []
        events_by_topic = metrics.get("events_by_topic", {})
        subs_by_topic = metrics.get("subscribers_by_topic", {})
        for topic in sorted(set(list(events_by_topic.keys()) + list(subs_by_topic.keys()))):
            topics.append({
                "topic": topic,
                "subs": subs_by_topic.get(topic, 0),
                "msgRate": events_by_topic.get(topic, 0),
                "lastMsg": f"{events_by_topic.get(topic, 0)} events processed",
            })
        return {"running": metrics.get("running", False), "topics": topics}
    except Exception as e:
        log.debug("event-bus status failed: %s", e)
        return {"running": False, "topics": []}


# ---------------------------------------------------------------------------
# Glass Box: Master system mode toggle
# ---------------------------------------------------------------------------
@router.post("/mode")
async def set_system_mode(payload: Dict[str, Any]):
    """Set master system mode: AUTO / SHADOW / PAUSED / LEARNING-ONLY.

    Body: { "mode": "AUTO" | "SHADOW" | "PAUSED" | "LEARNING_ONLY" }

    - AUTO: full autonomous trading
    - SHADOW: signals + council run but no real orders
    - PAUSED: pipeline halted, monitoring only
    - LEARNING_ONLY: council runs for learning, no execution
    """
    import os

    valid_modes = {"AUTO", "SHADOW", "PAUSED", "LEARNING_ONLY"}
    mode = (payload.get("mode") or "").upper().replace("-", "_")
    if mode not in valid_modes:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}. Must be one of {valid_modes}")

    os.environ["SYSTEM_MODE"] = mode

    # Apply to order executor
    applied = {}
    try:
        import app.main as main_mod
        executor = getattr(main_mod, "_order_executor", None)
        if executor:
            executor.auto_execute = (mode == "AUTO")
            applied["auto_execute"] = executor.auto_execute
    except Exception:
        pass

    # Apply to council gate
    try:
        import app.main as main_mod
        gate = getattr(main_mod, "_council_gate", None)
        if gate and mode == "PAUSED":
            gate._paused = True
            applied["council_gate_paused"] = True
        elif gate:
            gate._paused = False
            applied["council_gate_paused"] = False
    except Exception:
        pass

    log.info("System mode changed to: %s", mode)
    return {"status": "ok", "mode": mode, "applied": applied}


@router.get("/mode")
async def get_system_mode():
    """Return current system mode."""
    import os
    mode = os.environ.get("SYSTEM_MODE", "SHADOW")
    return {"mode": mode}


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
