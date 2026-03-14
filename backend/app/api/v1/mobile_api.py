"""Mobile API — lightweight REST endpoints for iPhone PWA remote control.

Features:
  - Public health check (no auth)
  - Bearer token auth for all other endpoints
  - Dashboard summary (P&L, agents, market status)
  - Open positions list
  - Recent alerts feed
  - Agent status overview
  - Emergency controls: kill_switch / pause / resume
  - System resource overview
"""
from __future__ import annotations

import logging
import secrets
import os
import platform
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

log = logging.getLogger(__name__)
router = APIRouter(tags=["mobile"])

# Bearer token — set MOBILE_API_TOKEN in .env, default is dev token
MOBILE_TOKEN: str = os.getenv("MOBILE_API_TOKEN", "embodier-mobile-2026")


def _require_token(authorization: Optional[str] = Header(None)) -> str:
    """Dependency: validate Bearer token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(token.strip(), MOBILE_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid token")
    return token


# ── Models ────────────────────────────────────────────────────────────────

class EmergencyAction(BaseModel):
    action: str  # "kill_switch" | "pause" | "resume"
    reason: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/health", summary="Public health ping")
async def mobile_health():
    """No auth required — used by PWA to test connectivity."""
    return {
        "status": "ok",
        "service": "embodier-trader",
        "version": "4.1.0",
        "ts": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/dashboard", summary="Condensed dashboard for mobile")
async def get_dashboard(_token: str = Depends(_require_token)):
    """Returns all key metrics on one call — optimised for mobile."""
    # ── agents ──
    active_agents, total_agents = 0, 0
    try:
        from app.modules.agents.agent_manager import get_agent_manager  # type: ignore
        mgr = get_agent_manager()
        if mgr and hasattr(mgr, "get_all_status"):
            statuses = mgr.get_all_status()
            total_agents = len(statuses)
            active_agents = sum(1 for s in statuses.values() if s.get("status") == "running")
    except Exception as e:
        log.debug("mobile %s lookup failed: %s", "agents", e)

    # ── portfolio ──
    total_pnl, daily_pnl, open_positions = 0.0, 0.0, 0
    try:
        from app.modules.portfolio.portfolio_manager import get_portfolio_manager  # type: ignore
        pm = get_portfolio_manager()
        if pm and hasattr(pm, "get_summary"):
            s = pm.get_summary()
            total_pnl = float(s.get("total_pnl", 0))
            daily_pnl = float(s.get("daily_pnl", 0))
            open_positions = int(s.get("open_positions", 0))
    except Exception as e:
        log.debug("mobile %s lookup failed: %s", "portfolio", e)

    # ── market status ──
    now_utc = datetime.now(timezone.utc)
    h, wd = now_utc.hour, now_utc.weekday()
    if wd >= 5:
        market = "weekend"
    elif 9 <= h < 13:   # approx pre-market (UTC)
        market = "pre-market"
    elif 13 <= h < 20:  # NYSE regular (UTC 13:30-20:00)
        market = "open"
    elif 20 <= h < 24:
        market = "after-hours"
    else:
        market = "closed"

    trading_mode = os.getenv("TRADING_MODE", "paper")

    return {
        "ts": now_utc.isoformat(),
        "trading_mode": trading_mode,
        "market_status": market,
        "total_pnl": total_pnl,
        "daily_pnl": daily_pnl,
        "open_positions": open_positions,
        "active_agents": active_agents,
        "total_agents": total_agents,
        "system_health": "healthy",
        "primary_pc": {"name": "ESPENMAIN", "status": "online", "role": "primary"},
        "secondary_pc": {"name": "ProfitTrader", "status": "unknown", "role": "brain"},
    }


@router.get("/positions", summary="Open positions")
async def get_positions(_token: str = Depends(_require_token)):
    try:
        from app.modules.portfolio.portfolio_manager import get_portfolio_manager  # type: ignore
        pm = get_portfolio_manager()
        if pm and hasattr(pm, "get_positions"):
            return {"positions": pm.get_positions()}
    except Exception as e:
        log.debug("mobile %s lookup failed: %s", "positions", e)
    return {"positions": []}


@router.get("/alerts", summary="Recent alert feed")
async def get_alerts(limit: int = 20, _token: str = Depends(_require_token)):
    try:
        from app.modules.alerts.alert_manager import get_alert_manager  # type: ignore
        am = get_alert_manager()
        if am and hasattr(am, "get_recent"):
            return {"alerts": am.get_recent(limit=limit)}
    except Exception as e:
        log.debug("mobile %s lookup failed: %s", "alerts", e)
    return {"alerts": []}


@router.get("/agents", summary="Agent status list")
async def get_agents(_token: str = Depends(_require_token)):
    try:
        from app.modules.agents.agent_manager import get_agent_manager  # type: ignore
        mgr = get_agent_manager()
        if mgr and hasattr(mgr, "get_all_status"):
            return {
                "agents": [
                    {"name": k, "status": v.get("status", "unknown"), "last_run": v.get("last_run")}
                    for k, v in mgr.get_all_status().items()
                ]
            }
    except Exception as e:
        log.debug("mobile %s lookup failed: %s", "agents", e)
    return {"agents": []}


@router.post("/emergency", summary="Kill switch / pause / resume")
async def emergency_action(body: EmergencyAction, _token: str = Depends(_require_token)):
    log.warning("MOBILE EMERGENCY: action=%s reason=%s", body.action, body.reason)

    if body.action == "kill_switch":
        try:
            from app.modules.trading.order_executor import get_order_executor  # type: ignore
            ex = get_order_executor()
            if ex and hasattr(ex, "kill_switch"):
                await ex.kill_switch(reason=body.reason or "Mobile kill switch")
                return {"status": "executed", "action": "kill_switch"}
        except Exception as e:
            log.error("Kill switch failed: %s", e)
            raise HTTPException(500, "Internal server error")
        return {"status": "no_executor", "action": "kill_switch"}

    if body.action in ("pause", "resume"):
        paused = body.action == "pause"
        os.environ["TRADING_PAUSED"] = "1" if paused else "0"
        return {"status": "executed", "action": body.action}

    raise HTTPException(400, f"Unknown action: {body.action}")


@router.get("/system", summary="System resource overview")
async def get_system(_token: str = Depends(_require_token)):
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "hostname": platform.node(),
            "os": platform.system(),
            "cpu_percent": cpu,
            "memory_total_gb": round(mem.total / 1073741824, 1),
            "memory_used_percent": mem.percent,
            "disk_used_percent": disk.percent,
            "uptime_seconds": int(time.time() - psutil.boot_time()),
            "python": platform.python_version(),
        }
    except ImportError:
        return {"hostname": platform.node(), "error": "psutil not installed"}
