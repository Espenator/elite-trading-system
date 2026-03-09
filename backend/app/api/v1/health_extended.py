"""Enhanced health check endpoints for WebSocket and brain service.

These endpoints provide detailed diagnostics for:
- WebSocket connection health
- Brain service gRPC connectivity
- Combined system diagnostics

Endpoints:
- GET /health/websocket - WebSocket connection status
- GET /health/brain - Brain service gRPC connectivity
- GET /health/diagnostics - Full system diagnostics
"""

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from typing import Dict, Any
import asyncio
import time

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/websocket")
async def websocket_health():
    """WebSocket health check.

    Returns connection statistics, rate limiting status, and subscription info.
    """
    from app.websocket_manager import (
        get_connection_count,
        _subscriptions,
        _last_pong,
        _WS_MSG_RATE,
        _WS_MAX_CONNECTIONS,
        _WS_MAX_MSGS_PER_MIN,
    )

    now = time.time()
    connection_count = get_connection_count()

    # Calculate stale connections (no pong in >90s)
    stale_count = 0
    healthy_count = 0
    for ws, last_pong_time in _last_pong.items():
        if now - last_pong_time > 90:
            stale_count += 1
        else:
            healthy_count += 1

    # Channel subscription counts
    channel_subs = {}
    for ws, channels in _subscriptions.items():
        for channel in channels:
            channel_subs[channel] = channel_subs.get(channel, 0) + 1

    # Rate limiting stats
    rate_limited_count = 0
    for ws, timestamps in _WS_MSG_RATE.items():
        recent = [t for t in timestamps if now - t < 60]
        if len(recent) >= _WS_MAX_MSGS_PER_MIN:
            rate_limited_count += 1

    health_status = {
        "status": "healthy" if connection_count > 0 else "no_connections",
        "connections": {
            "total": connection_count,
            "healthy": healthy_count,
            "stale": stale_count,
            "max_allowed": _WS_MAX_CONNECTIONS,
        },
        "subscriptions": {
            "channels": channel_subs,
            "total_subscriptions": sum(channel_subs.values()),
        },
        "rate_limiting": {
            "max_msgs_per_min": _WS_MAX_MSGS_PER_MIN,
            "currently_limited": rate_limited_count,
        },
        "timestamp": now,
    }

    return health_status


@router.get("/brain")
async def brain_service_health():
    """Brain service gRPC connectivity check.

    Tests connection to brain service and returns:
    - Connection status
    - Circuit breaker state
    - Latency metrics (if available)
    - Last successful call timestamp
    """
    from app.services.brain_client import get_brain_client
    import os

    brain_enabled = os.getenv("BRAIN_ENABLED", "false").lower() in ("true", "1", "yes")
    brain_host = os.getenv("BRAIN_HOST", "localhost")
    brain_port = int(os.getenv("BRAIN_PORT", "50051"))

    if not brain_enabled:
        return {
            "status": "disabled",
            "message": "Brain service is disabled (BRAIN_ENABLED=false)",
            "enabled": False,
        }

    client = get_brain_client()

    # Get circuit breaker state
    circuit_state = client.circuit_breaker.state if hasattr(client, "circuit_breaker") else "unknown"
    consecutive_failures = (
        client.circuit_breaker.consecutive_failures
        if hasattr(client, "circuit_breaker")
        else 0
    )

    # Attempt a lightweight connectivity test
    connectivity_test = "not_tested"
    latency_ms = None
    error = None

    try:
        # Simple test: call infer with minimal data (will be cached/fast)
        start = time.time()
        result = await asyncio.wait_for(
            client.infer(
                symbol="TEST",
                timeframe="1d",
                feature_json="{}",
                regime="neutral",
                context="health_check",
            ),
            timeout=3.0,
        )
        latency_ms = (time.time() - start) * 1000

        if "error" in result or result.get("confidence", 0) < 0:
            connectivity_test = "degraded"
            error = result.get("error", "Low confidence response")
        else:
            connectivity_test = "healthy"
    except asyncio.TimeoutError:
        connectivity_test = "timeout"
        error = "Health check timed out after 3s"
    except Exception as e:
        connectivity_test = "error"
        error = str(e)

    health_status = {
        "status": connectivity_test,
        "enabled": brain_enabled,
        "connection": {
            "host": brain_host,
            "port": brain_port,
            "url": f"grpc://{brain_host}:{brain_port}",
        },
        "circuit_breaker": {
            "state": circuit_state,
            "consecutive_failures": consecutive_failures,
        },
        "latency_ms": latency_ms,
        "error": error,
    }

    # Return 503 if brain is enabled but not healthy
    if brain_enabled and connectivity_test not in ("healthy", "not_tested"):
        return JSONResponse(status_code=503, content=health_status)

    return health_status


@router.get("/diagnostics")
async def comprehensive_diagnostics():
    """Comprehensive system diagnostics.

    Combines all health checks into a single endpoint for debugging.
    Returns detailed status for all subsystems.
    """
    from app.websocket_manager import get_connection_count
    from app.data.duckdb_storage import duckdb_store
    from app.services.alpaca_service import alpaca_service
    import os

    # Gather all diagnostics
    diagnostics = {
        "timestamp": time.time(),
        "environment": {
            "python_version": os.sys.version,
            "host": os.getenv("HOST", "unknown"),
            "port": int(os.getenv("PORT", "8000")),
            "debug": os.getenv("DEBUG", "false").lower() in ("true", "1"),
            "trading_mode": os.getenv("TRADING_MODE", "unknown"),
        },
        "database": {},
        "websocket": {},
        "brain_service": {},
        "integrations": {},
        "event_pipeline": {},
    }

    # Database status
    try:
        db_health = duckdb_store.health_check()
        diagnostics["database"] = {
            "status": "ok" if db_health.get("total_tables", 0) > 0 else "degraded",
            "total_tables": db_health.get("total_tables", 0),
            "total_rows": db_health.get("total_rows", 0),
        }
    except Exception as e:
        diagnostics["database"] = {"status": "error", "error": str(e)}

    # WebSocket status
    try:
        ws_health = await websocket_health()
        diagnostics["websocket"] = {
            "status": ws_health["status"],
            "connections": ws_health["connections"]["total"],
            "healthy": ws_health["connections"]["healthy"],
        }
    except Exception as e:
        diagnostics["websocket"] = {"status": "error", "error": str(e)}

    # Brain service status
    try:
        brain_health = await brain_service_health()
        diagnostics["brain_service"] = {
            "status": brain_health["status"],
            "enabled": brain_health["enabled"],
        }
        if "latency_ms" in brain_health:
            diagnostics["brain_service"]["latency_ms"] = brain_health["latency_ms"]
    except Exception as e:
        diagnostics["brain_service"] = {"status": "error", "error": str(e)}

    # Integration status
    diagnostics["integrations"] = {
        "alpaca": "configured" if alpaca_service._is_configured() else "not_configured",
        "unusual_whales": "configured" if os.getenv("UNUSUAL_WHALES_API_KEY") else "not_configured",
        "finviz": "configured" if os.getenv("FINVIZ_API_KEY") else "not_configured",
        "fred": "configured" if os.getenv("FRED_API_KEY") else "not_configured",
        "news_api": "configured" if os.getenv("NEWS_API_KEY") else "not_configured",
    }

    # Event pipeline status (if available)
    try:
        from app.main import _message_bus, _event_signal_engine, _council_gate

        diagnostics["event_pipeline"] = {
            "message_bus": "running" if _message_bus else "not_started",
            "signal_engine": "running" if _event_signal_engine else "not_started",
            "council_gate": "running" if _council_gate else "not_started",
        }
    except Exception:
        diagnostics["event_pipeline"] = {"status": "unavailable"}

    return diagnostics
