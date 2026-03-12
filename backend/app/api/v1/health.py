"""Unified Health API — aggregated health for all data sources and services.

GET /api/v1/health           -> Comprehensive status: DuckDB, Alpaca, Brain gRPC,
                                MessageBus queue depth, last council eval, data sources
GET /api/v1/health/alerts    -> Slack alerter status + recent alerts
GET /api/v1/health/incidents -> Recent health incidents
"""

import logging
import time
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/health", tags=["health"])
logger = logging.getLogger(__name__)


async def _check_duckdb() -> Dict[str, Any]:
    """DuckDB connection status."""
    try:
        from app.data.duckdb_storage import duckdb_store
        health = duckdb_store.health_check()
        return {
            "status": "ok",
            "connected": True,
            "total_rows": health.get("total_rows", 0),
            "total_tables": health.get("total_tables", 0),
        }
    except Exception as e:
        return {"status": "error", "connected": False, "error": str(e)[:200]}


async def _check_alpaca() -> Dict[str, Any]:
    """Alpaca API connectivity."""
    try:
        from app.services.alpaca_service import alpaca_service
        clock = await alpaca_service.get_clock()
        return {
            "status": "ok",
            "connected": bool(clock),
            "is_open": clock.get("is_open", False) if clock else None,
        }
    except Exception as e:
        return {"status": "error", "connected": False, "error": str(e)[:200]}


async def _check_brain_grpc() -> Dict[str, Any]:
    """Brain service gRPC connectivity."""
    try:
        from app.services.brain_client import get_brain_client
        client = get_brain_client()
        if not getattr(client, "enabled", False):
            return {"status": "disabled", "connected": False}
        # Lightweight connectivity check
        if hasattr(client, "_circuit") and client._circuit.can_execute():
            return {"status": "ok", "connected": True}
        return {"status": "degraded", "connected": False, "reason": "circuit_open"}
    except Exception as e:
        return {"status": "error", "connected": False, "error": str(e)[:200]}


def _messagebus_queue_depth() -> Dict[str, Any]:
    """MessageBus queue depth."""
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        q = getattr(bus, "_queue", None)
        depth = q.qsize() if q is not None else 0
        metrics = bus.get_metrics() if hasattr(bus, "get_metrics") else {}
        return {
            "queue_depth": depth,
            "running": metrics.get("running", False),
        }
    except Exception as e:
        return {"queue_depth": -1, "error": str(e)[:200]}


def _last_council_eval() -> Dict[str, Any]:
    """Last council evaluation timestamp."""
    try:
        from app.core.metrics import get_last_council_eval_timestamp, get_council_latency_percentiles
        ts = get_last_council_eval_timestamp()
        percentiles = get_council_latency_percentiles()
        return {
            "last_eval_timestamp": ts,
            "last_eval_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)) if ts else None,
            "latency_p95_ms": percentiles.get("p95"),
            "latency_sample_count": percentiles.get("sample_count", 0),
        }
    except Exception as e:
        return {"last_eval_timestamp": None, "error": str(e)[:200]}


@router.get("")
async def system_health():
    """Comprehensive health: DuckDB, Alpaca, Brain gRPC, MessageBus, last council eval + data sources."""
    result: Dict[str, Any] = {}

    # Core infrastructure checks
    result["duckdb"] = await _check_duckdb()
    result["alpaca"] = await _check_alpaca()
    result["brain_grpc"] = await _check_brain_grpc()
    result["message_bus"] = _messagebus_queue_depth()
    result["council"] = _last_council_eval()

    # Existing data source aggregator
    try:
        from app.services.data_source_health_aggregator import get_health_aggregator
        agg = get_health_aggregator()
        result["data_sources"] = agg.get_health()
        result["overall_status"] = result["data_sources"].get("overall_status", "unknown")
    except Exception as e:
        result["data_sources"] = {"error": "Service unavailable"}
        result["overall_status"] = "degraded"

    # Derive overall if not set
    if result.get("overall_status") == "unknown":
        core_ok = (
            result["duckdb"].get("connected") and
            result["alpaca"].get("connected")
        )
        result["overall_status"] = "ok" if core_ok else "degraded"

    return result


@router.get("/alerts")
async def alert_status():
    """Slack alerter status and configuration."""
    try:
        from app.services.slack_alerter import get_slack_alerter
        alerter = get_slack_alerter()
        return alerter.get_status()
    except Exception as e:
        logger.warning("Slack alerter status unavailable: %s", e)
        return {"enabled": False, "error": "Service unavailable"}


@router.get("/incidents")
async def recent_incidents():
    """Recent health incidents (last 10)."""
    try:
        from app.services.data_source_health_aggregator import get_health_aggregator
        agg = get_health_aggregator()
        health = agg.get_health()
        return {
            "incidents": health.get("recent_incidents", []),
            "overall_status": health.get("overall_status", "unknown"),
        }
    except Exception as e:
        logger.warning("Health incidents unavailable: %s", e)
        return {"incidents": [], "error": "Service unavailable"}
