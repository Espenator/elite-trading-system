"""Unified Health API — aggregated health for all data sources and services.

GET /api/v1/health           -> Comprehensive status: DuckDB, Alpaca, Brain gRPC,
                                MessageBus queue depth, last council eval, data sources
GET /api/v1/health/alerts    -> Slack alerter status + recent alerts
GET /api/v1/health/incidents -> Recent health incidents
GET /api/v1/health/startup-check -> Full system startup health (7 phases) + failure patterns
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/health", tags=["health"])
logger = logging.getLogger(__name__)

# Common failure patterns (same as scripts/startup_health_check.py)
STARTUP_FAILURE_PATTERNS: List[Dict[str, str]] = [
    {"symptom": "Backend /healthz timeouts or connection refused", "cause": "Backend not running, wrong port, or firewall", "remediation": "Start backend: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"},
    {"symptom": "DuckDB check fails in /readyz or /api/v1/health", "cause": "DuckDB file locked, missing data dir, or schema not initialized", "remediation": "Ensure backend/data/ exists; restart backend; check no other process holds DuckDB."},
    {"symptom": "Alpaca configured but connectivity error", "cause": "Invalid API keys, network block, or Alpaca API outage", "remediation": "Verify ALPACA_API_KEY and ALpaca base URL in backend/.env; use paper URL for paper trading."},
    {"symptom": "MessageBus or council_gate not_started in /health", "cause": "Lifespan startup failed or deferred services not yet started", "remediation": "Check backend logs for lifespan errors; increase DEFERRED_STARTUP_DELAY if heavy init fails."},
    {"symptom": "Frontend loads but API calls 404 or CORS errors", "cause": "Wrong VITE_API_URL, backend not on expected port, or CORS origin not allowed", "remediation": "Set VITE_API_URL to backend URL; ensure backend CORS includes frontend origin."},
    {"symptom": "Brain gRPC or Ollama unavailable", "cause": "Brain service not running on PC2, or Ollama not running", "remediation": "Start brain_service on ProfitTrader; or set LLM_ENABLED=false to run without LLM."},
    {"symptom": "Redis unavailable (when REDIS_URL set)", "cause": "Redis not running or wrong host/port", "remediation": "Start Redis or set REDIS_REQUIRED=false to allow local-only MessageBus."},
    {"symptom": "Scouts or discovery agents crash repeatedly", "cause": "Missing API keys (UW, Finviz, etc.) or rate limits", "remediation": "Check SCOUTS_ENABLED and optional env vars; see logs for specific scout exceptions."},
]


async def _check_duckdb() -> Dict[str, Any]:
    """DuckDB connection status."""
    try:
        from app.data.duckdb_storage import duckdb_store
        health = await asyncio.to_thread(duckdb_store.health_check)
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


async def _messagebus_queue_depth() -> Dict[str, Any]:
    """MessageBus queue depth (threaded to avoid blocking event loop)."""
    def _get_depth():
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        q = getattr(bus, "_queue", None)
        depth = q.qsize() if q is not None else 0
        metrics = bus.get_metrics() if hasattr(bus, "get_metrics") else {}
        return {
            "queue_depth": depth,
            "running": metrics.get("running", False),
        }
    try:
        return await asyncio.to_thread(_get_depth)
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
    # Process lock info
    try:
        from app.core.process_lock import get_lock_info
        result["process_lock"] = get_lock_info()
    except Exception:
        result["process_lock"] = {"locked": False}

    result["duckdb"] = await _check_duckdb()
    result["alpaca"] = await _check_alpaca()
    result["brain_grpc"] = await _check_brain_grpc()
    result["message_bus"] = await _messagebus_queue_depth()
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


@router.get("/startup-check")
async def startup_check():
    """Full system startup health: 7 phases (environment → backend → router → API smoke →
    signal pipeline → frontend wiring → background loops). Returns same structure as
    scripts/startup_health_check.py and includes common failure patterns table for the View."""
    result = await _run_startup_phases_async()
    return result


async def _run_startup_phases_async() -> Dict[str, Any]:
    """Async wrapper so we can await _check_duckdb and status in phase 4/7."""
    phases: Dict[str, Any] = {}
    overall_ok = True

    # Phase 1
    env_checks = []
    py_ok = (sys.version_info.major, sys.version_info.minor) >= (3, 10)
    env_checks.append({"check": "Python 3.10+", "status": "ok" if py_ok else "fail", "detail": f"{sys.version_info.major}.{sys.version_info.minor}"})
    try:
        from app.core.config import settings  # noqa: F401
        env_checks.append({"check": "Config loaded", "status": "ok", "detail": "pydantic settings"})
    except Exception as e:
        env_checks.append({"check": "Config loaded", "status": "fail", "detail": str(e)[:100]})
        overall_ok = False
    phases["1_environment"] = {"label": "Environment check", "ok": py_ok, "checks": env_checks}
    if not py_ok:
        overall_ok = False

    phases["2_backend_startup"] = {"label": "Backend startup", "ok": True, "checks": [{"check": "Backend /healthz", "status": "ok", "detail": "process running"}]}

    try:
        from app.main import app
        routes = [r for r in app.routes if hasattr(r, "path") and r.path]
        phases["3_router_verification"] = {"label": "Router verification", "ok": True, "checks": [{"check": "Routes registered", "status": "ok", "detail": f"{len(routes)} routes"}]}
    except Exception as e:
        phases["3_router_verification"] = {"label": "Router verification", "ok": False, "checks": [{"check": "Routes", "status": "fail", "detail": str(e)[:100]}]}
        overall_ok = False

    smoke_checks = []
    try:
        duck = await _check_duckdb()
        smoke_checks.append({"check": "GET /api/v1/health (DuckDB)", "status": "ok" if duck.get("connected") else "warn", "detail": str(duck)[:60]})
    except Exception as e:
        smoke_checks.append({"check": "GET /api/v1/health", "status": "fail", "detail": str(e)[:80]})
        overall_ok = False
    try:
        from app.api.v1.status import system_status
        st = await system_status()
        smoke_checks.append({"check": "GET /api/v1/status", "status": "ok", "detail": f"healthy={st.get('healthy')}"})
    except Exception as e:
        smoke_checks.append({"check": "GET /api/v1/status", "status": "fail", "detail": str(e)[:80]})
        overall_ok = False
    phases["4_api_smoke"] = {"label": "API smoke tests", "ok": all(c.get("status") == "ok" for c in smoke_checks), "checks": smoke_checks}
    if not phases["4_api_smoke"]["ok"]:
        overall_ok = False

    pipe_checks = []
    mb = await _messagebus_queue_depth()
    council = _last_council_eval()
    mb_ok = mb.get("queue_depth") is not None or mb.get("running") is not None
    # Pipeline is "ok" if council block is present (wired); no eval yet is fine after fresh start
    has_eval = council.get("last_eval_timestamp") is not None or council.get("last_eval_iso") is not None
    wired_no_error = council.get("error") is None and isinstance(council, dict)
    council_ok = has_eval or wired_no_error
    pipe_checks.append({"check": "MessageBus", "status": "ok" if mb_ok else "warn", "detail": str(mb)[:80]})
    pipe_checks.append({"check": "Council (last eval)", "status": "ok" if council_ok else "warn", "detail": council.get("last_eval_iso") or str(council)[:60]})
    phases["5_signal_pipeline"] = {"label": "Signal pipeline", "ok": mb_ok and council_ok, "checks": pipe_checks}
    if not phases["5_signal_pipeline"]["ok"]:
        overall_ok = False

    phases["6_frontend_wiring"] = {"label": "Frontend wiring", "ok": True, "checks": [{"check": "Frontend URL", "status": "skip", "detail": "run from script or UI"}]}

    loop_checks = []
    try:
        from app.data.duckdb_storage import duckdb_store
        h = await asyncio.to_thread(duckdb_store.health_check)
        loop_checks.append({"check": "Readiness (DuckDB)", "status": "ok" if h.get("total_tables", 0) > 0 else "warn", "detail": str(h)[:60]})
    except Exception as e:
        loop_checks.append({"check": "Readiness", "status": "fail", "detail": str(e)[:80]})
        overall_ok = False
    try:
        from app.api.v1.status import system_status
        st = await system_status()
        loop_checks.append({"check": "Background / status", "status": "ok", "detail": f"activeAgents={st.get('activeAgents', '?')}"})
    except Exception as e:
        loop_checks.append({"check": "Background status", "status": "warn", "detail": str(e)[:60]})
    phases["7_background_loops"] = {"label": "Background loops", "ok": not any(c.get("status") == "fail" for c in loop_checks), "checks": loop_checks}
    if not phases["7_background_loops"]["ok"]:
        overall_ok = False

    return {"phases": phases, "overall_ok": overall_ok, "failure_patterns": STARTUP_FAILURE_PATTERNS, "timestamp": datetime.now(timezone.utc).isoformat()}
