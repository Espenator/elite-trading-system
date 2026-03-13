"""Comprehensive Metrics API — E5 Production Observability.

GET /api/v1/metrics          -> JSON metrics from all services
GET /api/v1/metrics/prometheus -> Prometheus text exposition format
GET /api/v1/metrics/pipeline -> Pipeline-specific metrics (signals, council, fills)
POST /api/v1/metrics/auto-execute -> Set Manual (enabled=false) vs Automated (enabled=true) trading mode
POST /api/v1/metrics/emergency-flatten -> Trigger emergency flatten

Aggregates metrics from:
  - app.core.metrics (counters + gauges)
  - MessageBus (event throughput, DLQ)
  - OrderExecutor (signals, executions, rejections)
  - PositionManager (managed positions, exits)
  - AlpacaStreamService (bars, snapshots, WS status)
  - SignalEngine (signal generation rate)
  - CouncilGate (verdict latency, approval rate)
  - SessionScanner (gaps, earnings)
"""

import logging
import os
import secrets
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


class AutoExecuteBody(BaseModel):
    """Request body for POST /metrics/auto-execute."""
    enabled: bool = False
logger = logging.getLogger(__name__)


@router.get("")
def get_metrics():
    """Return comprehensive JSON metrics from all services."""
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": None,
    }

    # Core metrics (counters + gauges)
    try:
        from app.core.metrics import get_metrics as _get_core_metrics
        result["core"] = _get_core_metrics()
    except Exception as e:
        logger.warning("Core metrics unavailable: %s", e)
        result["core"] = {"error": "unavailable"}

    # MessageBus metrics
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        result["message_bus"] = bus.get_metrics()
    except Exception as e:
        logger.warning("MessageBus metrics unavailable: %s", e)
        result["message_bus"] = {"error": "unavailable"}

    # OrderExecutor metrics
    try:
        import app.main as _main
        _executor_instance = getattr(_main, "_order_executor", None)
        if _executor_instance:
            result["order_executor"] = {
                "running": _executor_instance._running,
                "signals_received": _executor_instance._signals_received,
                "signals_executed": _executor_instance._signals_executed,
                "signals_rejected": _executor_instance._signals_rejected,
                "daily_trade_count": _executor_instance._daily_trade_count,
                "total_notional": round(_executor_instance._total_notional, 2),
                "auto_execute": _executor_instance.auto_execute,
                "recent_orders": len(_executor_instance._orders),
            }
            uptime = time.time() - (_executor_instance._start_time or time.time())
            result["uptime_seconds"] = round(uptime, 1)
        else:
            result["order_executor"] = {"status": "not_started"}
    except Exception as e:
        logger.warning("OrderExecutor metrics unavailable: %s", e)
        result["order_executor"] = {"error": "unavailable"}

    # PositionManager metrics
    try:
        from app.services.position_manager import get_position_manager
        pm = get_position_manager()
        result["position_manager"] = pm.get_status()
    except Exception as e:
        logger.warning("PositionManager metrics unavailable: %s", e)
        result["position_manager"] = {"error": "unavailable"}

    # AlpacaStreamService metrics
    try:
        from app.services.alpaca_stream_service import AlpacaStreamService
        # Access via main.py's global — stream services are stored there
        import app.main as _main
        streams = []
        for attr in ("_trading_stream", "_discovery_stream"):
            svc = getattr(_main, attr, None)
            if svc and isinstance(svc, AlpacaStreamService):
                streams.append(svc.get_status())
        result["alpaca_streams"] = streams if streams else {"status": "not_found"}
    except Exception as e:
        logger.warning("Alpaca streams metrics unavailable: %s", e)
        result["alpaca_streams"] = {"error": "unavailable"}

    # SessionScanner metrics
    try:
        from app.services.session_scanner import get_session_scanner
        scanner = get_session_scanner()
        result["session_scanner"] = scanner.get_status()
    except Exception as e:
        logger.warning("SessionScanner metrics unavailable: %s", e)
        result["session_scanner"] = {"error": "unavailable"}

    # CouncilGate metrics
    try:
        from app.services.council_gate import get_council_gate
        gate = get_council_gate()
        if hasattr(gate, "get_metrics"):
            result["council_gate"] = gate.get_metrics()
        elif hasattr(gate, "get_status"):
            result["council_gate"] = gate.get_status()
        else:
            result["council_gate"] = {"status": "available"}
    except Exception as e:
        logger.warning("CouncilGate metrics unavailable: %s", e)
        result["council_gate"] = {"error": "unavailable"}

    # SignalEngine metrics
    try:
        from app.services.signal_engine import get_signal_engine
        engine = get_signal_engine()
        if hasattr(engine, "get_metrics"):
            result["signal_engine"] = engine.get_metrics()
        elif hasattr(engine, "get_status"):
            result["signal_engine"] = engine.get_status()
        else:
            result["signal_engine"] = {"status": "available"}
    except Exception as e:
        logger.warning("SignalEngine metrics unavailable: %s", e)
        result["signal_engine"] = {"error": "unavailable"}

    # Pipeline summary (derived)
    try:
        oe = result.get("order_executor", {})
        signals_recv = oe.get("signals_received", 0)
        signals_exec = oe.get("signals_executed", 0)
        signals_rej = oe.get("signals_rejected", 0)
        uptime = result.get("uptime_seconds", 0) or 1

        result["pipeline_summary"] = {
            "signals_per_minute": round(signals_recv / max(uptime / 60, 1), 2),
            "fill_rate_pct": round(
                (signals_exec / max(signals_recv, 1)) * 100, 1
            ),
            "rejection_rate_pct": round(
                (signals_rej / max(signals_recv, 1)) * 100, 1
            ),
            "active_positions": result.get("position_manager", {}).get(
                "managed_positions", 0
            ),
        }
    except Exception:
        result["pipeline_summary"] = {}

    # E5: Additional production metrics
    try:
        # council_latency_ms percentiles
        from app.core.metrics import get_gauges
        gauges = get_gauges()
        council_latencies = []
        for key, val in gauges.items():
            if key[0] == "council_latency_ms":
                council_latencies.append(val)
        if council_latencies:
            sorted_lat = sorted(council_latencies)
            n = len(sorted_lat)
            result["council_latency_percentiles"] = {
                "p50": sorted_lat[int(n * 0.5)] if n > 0 else 0,
                "p95": sorted_lat[int(n * 0.95)] if n > 0 else 0,
                "p99": sorted_lat[int(n * 0.99)] if n > 0 else 0,
                "sample_count": n,
            }
        else:
            result["council_latency_percentiles"] = {"p50": 0, "p95": 0, "p99": 0, "sample_count": 0}
    except Exception:
        result["council_latency_percentiles"] = {"error": "unavailable"}

    # E5: Weight learner stats
    try:
        from app.council.weight_learner import get_weight_learner
        wl = get_weight_learner()
        result["weight_learner"] = {
            "updates_today": getattr(wl, "_updates_today", 0),
            "total_decisions_recorded": len(getattr(wl, "_decision_history", [])),
            "active_agents": len(getattr(wl, "_weights", {})),
        }
    except Exception:
        result["weight_learner"] = {"error": "unavailable"}

    # E5: MessageBus queue depth
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        result["messagebus_queue_depth"] = bus._queue.qsize() if hasattr(bus, "_queue") and bus._queue else 0
    except Exception:
        result["messagebus_queue_depth"] = 0

    return result


@router.get("/prometheus", response_class=PlainTextResponse)
def get_prometheus_metrics():
    """Return metrics in Prometheus text exposition format."""
    try:
        from app.core.metrics import format_prometheus
        return format_prometheus()
    except Exception as e:
        logger.warning("Prometheus metrics error: %s", e)
        return "# Error: metrics unavailable\n"


@router.get("/pipeline")
def get_pipeline_metrics():
    """Pipeline-specific metrics: signal_count/min, council_latency, fill_rate."""
    try:
        from app.core.metrics import get_counters, get_gauges
        counters = get_counters()
        gauges = get_gauges()

        # Extract pipeline-relevant metrics
        pipeline = {}
        for key, val in counters.items():
            name = key[0]
            if any(kw in name for kw in ("signal", "council", "execution", "order")):
                labels = {}
                i = 1
                while i < len(key):
                    labels[key[i]] = key[i + 1]
                    i += 2
                pipeline[f"counter:{name}" + (f":{labels}" if labels else "")] = val

        for key, val in gauges.items():
            name = key[0]
            if any(kw in name for kw in ("signal", "council", "execution", "position", "latency")):
                labels = {}
                i = 1
                while i < len(key):
                    labels[key[i]] = key[i + 1]
                    i += 2
                pipeline[f"gauge:{name}" + (f":{labels}" if labels else "")] = val

        return {"pipeline_metrics": pipeline, "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        logger.warning("Pipeline metrics error: %s", e)
        return {"error": "Service unavailable"}


@router.post("/auto-execute")
async def set_auto_execute_mode(
    body: AutoExecuteBody = Body(...),
    authorization: str = Header(None),
):
    """Set automated trading mode (Manual vs Automated).

    When enabled=true: OrderExecutor submits real orders from council verdicts (AI/Embodier trades).
    When enabled=false: Shadow mode — council runs but orders are not sent (manual trading only).
    Requires Bearer token auth.
    """
    from app.core.config import settings
    expected_token = (settings.API_AUTH_TOKEN or "").strip()
    if not expected_token:
        raise HTTPException(status_code=403, detail="API_AUTH_TOKEN not configured")
    if not authorization or not secrets.compare_digest((authorization or "").strip(), f"Bearer {expected_token}"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    enabled = body.enabled
    try:
        import app.main as _main
        _executor_instance = getattr(_main, "_order_executor", None)
        if not _executor_instance:
            return {"error": "OrderExecutor not initialized", "status": "failed"}
        result = await _executor_instance.set_auto_execute(bool(enabled))
        return result
    except Exception as e:
        logger.exception("Set auto-execute API error")
        return {"error": str(e), "status": "failed"}


@router.post("/emergency-flatten")
async def trigger_emergency_flatten(
    reason: str = "api_trigger",
    authorization: str = Header(None),
):
    """Trigger emergency flatten of all positions.

    E2: Closes all open positions with retry + Slack alert.
    Requires Bearer token auth via Authorization header.
    """
    # E2a: Verify Bearer token (use same token as require_auth — API_AUTH_TOKEN)
    from app.core.config import settings
    expected_token = (settings.API_AUTH_TOKEN or "").strip()
    if not expected_token:
        raise HTTPException(status_code=403, detail="API_AUTH_TOKEN not configured")
    if not authorization or not secrets.compare_digest((authorization or "").strip(), f"Bearer {expected_token}"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        import app.main as _main
        _executor_instance = getattr(_main, "_order_executor", None)
        if not _executor_instance:
            return {"error": "OrderExecutor not initialized", "status": "failed"}
        result = await _executor_instance.emergency_flatten(reason=reason)
        return result
    except Exception as e:
        logger.exception("Emergency flatten API error")
        return {"error": "Internal server error", "status": "failed"}


@router.post("/ws-circuit-breaker/reset", dependencies=[Depends(require_auth)])
def reset_ws_circuit_breaker():
    """Reset the WebSocket circuit breaker to allow reconnection attempts.

    E4: After 10 consecutive WS failures, call this to reset.
    """
    try:
        import app.main as _main
        results = []
        for attr in ("_trading_stream", "_discovery_stream"):
            svc = getattr(_main, attr, None)
            if svc and hasattr(svc, "reset_ws_circuit_breaker"):
                results.append({attr: svc.reset_ws_circuit_breaker()})
        return {"results": results} if results else {"error": "No stream services found"}
    except Exception as e:
        logger.warning("WS circuit breaker reset error: %s", e)
        return {"error": "Service unavailable"}
