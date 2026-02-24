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
# /status  (unchanged)
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
