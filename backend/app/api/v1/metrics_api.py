"""Comprehensive Metrics API — E5 Production Observability.

GET /api/v1/metrics          -> JSON metrics from all services
GET /api/v1/metrics/prometheus -> Prometheus text exposition format
GET /api/v1/metrics/pipeline -> Pipeline-specific metrics (signals, council, fills)
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
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])
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


@router.post("/emergency-flatten")
async def trigger_emergency_flatten(reason: str = "api_trigger"):
    """Trigger emergency flatten of all positions.

    E2: Closes all open positions with retry + Slack alert.
    """
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


@router.post("/ws-circuit-breaker/reset")
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
