"""
LLM Health API — provider status, rate limits, and quota monitoring.

Endpoints:
    GET  /api/v1/llm/health          → Full health dashboard for all providers
    GET  /api/v1/llm/health/{name}   → Single provider detail
    GET  /api/v1/llm/health/events   → Recent rate limit / error events

WebSocket channel: "llm_health" — push events:
    llm.rate_limited, llm.auth_failure, llm.overloaded,
    llm.quota_warning, llm.all_exhausted,
    llm.provider_recovered, llm.provider_degraded
"""

from fastapi import APIRouter, HTTPException
from app.services.llm_health_monitor import get_llm_health_monitor

router = APIRouter()


@router.get("/")
async def llm_health_dashboard():
    """Full LLM provider health dashboard.

    Returns system-level health plus per-provider status including:
    - Current status (healthy/rate_limited/auth_failure/degraded/offline)
    - Health percentage (0-100)
    - Rate limit remaining/limit from headers
    - Consecutive failures
    - Recent error events
    - Circuit breaker state
    - Auth validity
    """
    monitor = get_llm_health_monitor()
    status = monitor.get_status()

    # Add action items for degraded providers
    actions = []
    for name, p in status["providers"].items():
        if p["status"] == "auth_failure":
            actions.append({
                "provider": name,
                "severity": "critical",
                "action": f"Check {p['display_name']} API key in Settings → Data Sources",
                "detail": p.get("auth_error", "Authentication failed"),
            })
        elif p["status"] == "rate_limited":
            actions.append({
                "provider": name,
                "severity": "warning",
                "action": f"{p['display_name']} is rate limited — requests are falling back to alternate providers",
                "detail": p.get("last_error", ""),
            })
        elif p["status"] == "degraded":
            actions.append({
                "provider": name,
                "severity": "warning",
                "action": f"{p['display_name']} circuit breaker open — auto-recovery in 5 min",
                "detail": f"{p['consecutive_failures']} consecutive failures",
            })

    status["actions"] = actions
    return status


@router.get("/events")
async def llm_health_events():
    """Recent rate limit and error events across all providers."""
    monitor = get_llm_health_monitor()
    status = monitor.get_status()

    all_events = []
    for name, p in status["providers"].items():
        for evt in p.get("recent_events", []):
            all_events.append(evt)

    # Sort by timestamp descending
    all_events.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
    return {"events": all_events[:50], "total": len(all_events)}


@router.get("/{provider_name}")
async def llm_provider_detail(provider_name: str):
    """Detailed status for a single LLM provider."""
    monitor = get_llm_health_monitor()
    detail = monitor.get_provider_status(provider_name)
    if not detail:
        raise HTTPException(404, f"Provider '{provider_name}' not found. Available: ollama, perplexity, anthropic")
    return detail
