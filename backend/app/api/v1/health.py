"""Unified Health API — aggregated health for all data sources and services.

GET /api/v1/health           -> Comprehensive status: DuckDB, Alpaca, Brain gRPC,
                                MessageBus queue depth, last council timestamp
GET /api/v1/health/alerts    -> Slack alerter status + recent alerts
GET /api/v1/health/incidents -> Recent health incidents
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/health", tags=["health"])
logger = logging.getLogger(__name__)


def _check_duckdb() -> Dict[str, Any]:
    """DuckDB connection status."""
    try:
        from app.data.duckdb_storage import duckdb_store
        health = duckdb_store.health_check()
        return {
            "status": "healthy",
            "connected": True,
            "total_tables": health.get("total_tables", 0),
            "total_rows": health.get("total_rows", 0),
        }
    except Exception as e:
        return {"status": "unhealthy", "connected": False, "error": str(e)}


async def _check_alpaca() -> Dict[str, Any]:
    """Alpaca API connectivity."""
    try:
        from app.services.alpaca_service import get_alpaca_service
        svc = get_alpaca_service()
        if svc is None:
            return {"status": "unavailable", "connected": False, "error": "service not initialized"}
        account = await svc.get_account()
        if account is None:
            return {"status": "degraded", "connected": False, "error": "get_account returned None"}
        status = account.get("status", "unknown") if isinstance(account, dict) else getattr(account, "status", "unknown")
        return {"status": "healthy", "connected": True, "account_status": status}
    except Exception as e:
        return {"status": "unhealthy", "connected": False, "error": str(e)}


def _check_brain_grpc() -> Dict[str, Any]:
    """Brain service gRPC connectivity (PC2)."""
    try:
        from app.services.brain_client import get_brain_client
        client = get_brain_client()
        if not getattr(client, "enabled", False):
            return {"status": "disabled", "connected": False}
        # Optional: actual ping if client exposes it
        if hasattr(client, "ping") and callable(client.ping):
            ok = client.ping()
            return {"status": "healthy" if ok else "unhealthy", "connected": ok}
        return {"status": "healthy", "connected": True}
    except Exception as e:
        return {"status": "unhealthy", "connected": False, "error": str(e)}


def _messagebus_queue_depth() -> Dict[str, Any]:
    """MessageBus queue depth and capacity."""
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        qsize = bus._queue.qsize() if hasattr(bus, "_queue") and bus._queue else 0
        qmax = bus._queue.maxsize if hasattr(bus, "_queue") and bus._queue else 0
        return {
            "queue_depth": qsize,
            "queue_max": qmax,
            "usage_pct": round(100 * qsize / max(qmax, 1), 1),
        }
    except Exception as e:
        return {"queue_depth": 0, "queue_max": 0, "error": str(e)}


def _last_council_timestamp() -> Dict[str, Any]:
    """Last council evaluation timestamp (for health / staleness)."""
    try:
        from app.council.council_gate import get_council_gate
        gate = get_council_gate()
        if gate is None:
            return {"last_evaluation_ts": None, "iso": None}
        ts = gate.get_last_council_ts() if hasattr(gate, "get_last_council_ts") else getattr(gate, "_last_council_ts", None)
        if ts is None:
            return {"last_evaluation_ts": None, "iso": None}
        return {
            "last_evaluation_ts": ts,
            "iso": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"last_evaluation_ts": None, "iso": None, "error": str(e)}


@router.get("")
async def system_health():
    """Comprehensive health: DuckDB, Alpaca, Brain gRPC, MessageBus, last council evaluation."""
    result: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duckdb": _check_duckdb(),
        "alpaca": await _check_alpaca(),
        "brain_grpc": _check_brain_grpc(),
        "messagebus": _messagebus_queue_depth(),
        "last_council_evaluation": _last_council_timestamp(),
    }
    # Merge in data source aggregator if available
    try:
        from app.services.data_source_health_aggregator import get_health_aggregator
        agg = get_health_aggregator()
        data_health = agg.get_health()
        result["data_sources"] = {
            "overall_status": data_health.get("overall_status", "unknown"),
            "total_sources": data_health.get("total_sources", 0),
            "healthy": data_health.get("healthy", 0),
            "degraded": data_health.get("degraded", 0),
            "unavailable": data_health.get("unavailable", 0),
        }
        result["overall_status"] = data_health.get("overall_status", "unknown")
    except Exception as e:
        logger.debug("Health aggregator unavailable: %s", e)
        result["data_sources"] = {"error": "unavailable"}
        # Derive overall from core checks
        core_ok = (
            result["duckdb"].get("connected") is True
            and result["alpaca"].get("connected") is True
        )
        result["overall_status"] = "healthy" if core_ok else "degraded"
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


# ── Programmatic sub-checks for automation / load balancers ─────────────────

@router.get("/broker")
async def health_broker():
    """Broker (Alpaca) connectivity only. For programmatic health checks."""
    return await _check_alpaca()


@router.get("/brain")
def health_brain():
    """Brain service (gRPC) connectivity only."""
    return _check_brain_grpc()


@router.get("/database")
def health_database():
    """Database (DuckDB) availability only."""
    return _check_duckdb()


@router.get("/data-sources")
def health_data_sources():
    """Data provider freshness and status (aggregated)."""
    try:
        from app.services.data_source_health_aggregator import get_health_aggregator
        agg = get_health_aggregator()
        health = agg.get_health()
        return {
            "overall_status": health.get("overall_status", "unknown"),
            "total_sources": health.get("total_sources", 0),
            "healthy": health.get("healthy", 0),
            "degraded": health.get("degraded", 0),
            "unavailable": health.get("unavailable", 0),
            "recent_incidents": health.get("recent_incidents", [])[:10],
        }
    except Exception as e:
        logger.warning("Data sources health unavailable: %s", e)
        return {"overall_status": "unavailable", "error": str(e)}


@router.get("/readiness")
async def health_readiness():
    """Readiness: app can serve traffic. Returns 200 if critical deps OK, 503 otherwise.

    Checks: database, broker connectivity, brain service (if enabled), data source freshness.
    Use for Kubernetes readiness probe or programmatic checks.
    """
    from fastapi.responses import JSONResponse

    checks: Dict[str, Any] = {}
    ready = True

    db = _check_duckdb()
    checks["database"] = db
    if not db.get("connected"):
        ready = False

    broker = await _check_alpaca()
    checks["broker"] = broker
    if broker.get("status") == "unhealthy" or broker.get("connected") is False:
        ready = False

    brain = _check_brain_grpc()
    checks["brain"] = brain
    # Brain is optional; do not fail readiness if brain is down (app can run without it)

    try:
        from app.services.data_source_health_aggregator import get_health_aggregator
        agg = get_health_aggregator()
        data_health = agg.get_health()
        checks["data_sources"] = {
            "overall_status": data_health.get("overall_status", "unknown"),
            "healthy": data_health.get("healthy", 0),
            "degraded": data_health.get("degraded", 0),
            "unavailable": data_health.get("unavailable", 0),
        }
        if data_health.get("overall_status") == "unavailable":
            ready = False
    except Exception:
        checks["data_sources"] = {"error": "unavailable"}

    status_code = 200 if ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if ready else "not_ready",
            "checks": checks,
        },
    )
