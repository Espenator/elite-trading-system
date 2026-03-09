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
    """Return this device's identity and system info for the Electron shell and Settings UI.

    DEPRECATED: Use /machine for machine-awareness features.
    This endpoint is maintained for backward compatibility.
    """
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


# /machine — Machine identity and deployment mode
# ---------------------------------------------------------------------------
@router.get("/machine")
async def machine_info():
    """Return comprehensive machine identity and deployment configuration.

    Returns:
        - machine_id: Hostname or custom identifier
        - machine_name: Friendly display name
        - machine_role: "pc1", "pc2", or "standalone"
        - deployment_mode: "single_pc" or "dual_pc"
        - peer_host: IP or hostname of peer machine
        - peer_online: True if peer is reachable
        - fallback_mode: True if dual-PC mode but peer offline
        - gpu_enabled: True if GPU is enabled
        - detection_method: How machine role was determined
        - system_info: Platform details
    """
    import os
    import platform

    try:
        from app.services.machine_identity import get_machine_identity
        machine_identity = get_machine_identity()

        # Refresh peer online status
        await machine_identity.check_peer_online()

        status = machine_identity.get_status()

        # Add system info
        status["system_info"] = {
            "platform": platform.system().lower(),
            "arch": platform.machine(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
        }

        return status

    except Exception as e:
        log.exception("Failed to get machine identity: %s", e)
        import socket
        return {
            "machine_id": socket.gethostname(),
            "machine_name": socket.gethostname(),
            "machine_role": "standalone",
            "deployment_mode": "single_pc",
            "peer_host": None,
            "peer_online": False,
            "fallback_mode": False,
            "gpu_enabled": True,
            "detection_method": "error_fallback",
            "error": str(e),
            "system_info": {
                "platform": platform.system().lower(),
                "arch": platform.machine(),
                "python_version": platform.python_version(),
                "cpu_count": os.cpu_count(),
            }
        }


@router.post("/machine/test-peer")
async def test_peer_connection():
    """Manually test peer machine connectivity.

    Performs an immediate health check and returns the result.
    Useful for troubleshooting peer connectivity issues.
    """
    try:
        from app.services.machine_identity import get_machine_identity
        machine_identity = get_machine_identity()

        if not machine_identity.peer_host:
            return {
                "success": False,
                "message": "No peer configured",
                "peer_host": None,
            }

        # Perform health check
        peer_online = await machine_identity.check_peer_online()

        return {
            "success": peer_online,
            "message": "Peer is online" if peer_online else "Peer is offline or unreachable",
            "peer_host": machine_identity.peer_host,
            "peer_online": peer_online,
            "fallback_mode": machine_identity.fallback_mode,
        }

    except Exception as e:
        log.exception("Failed to test peer connection: %s", e)
        return {
            "success": False,
            "message": f"Error testing peer connection: {str(e)}",
            "peer_host": None,
        }
