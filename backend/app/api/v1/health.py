"""Unified Health API — aggregated health for all data sources and services.

GET /api/v1/health           -> Overall system health + per-source detail
GET /api/v1/health/alerts    -> Slack alerter status + recent alerts
GET /api/v1/health/incidents -> Recent health incidents
"""

import logging
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("")
async def system_health():
    """Aggregated health across all data sources and services."""
    try:
        from app.services.data_source_health_aggregator import get_health_aggregator
        agg = get_health_aggregator()
        return agg.get_health()
    except Exception as e:
        logger.warning("Health aggregator unavailable: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Health aggregator unavailable: {e}",
        )


@router.get("/alerts")
async def alert_status():
    """Slack alerter status and configuration."""
    try:
        from app.services.slack_alerter import get_slack_alerter
        alerter = get_slack_alerter()
        return alerter.get_status()
    except Exception as e:
        logger.warning("Slack alerter status unavailable: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Slack alerter status unavailable: {e}",
        )


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
        raise HTTPException(
            status_code=503,
            detail=f"Health incidents unavailable: {e}",
        )
