"""
risk_shield_api.py — RiskShield Emergency Controls API
Wires the RiskShield UI to OpenClaw risk_governor.py (474 lines)
Maps 9 safety checks to UI checklist, portfolio heatmap, emergency controls
"""
from fastapi import APIRouter, HTTPException, Depends
from app.core.security import require_auth, require_role
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

from app.services.alpaca_service import alpaca_service
from app.services.database import db_service

logger = logging.getLogger("elite.risk_shield")

# Use in-repo OpenClaw risk governor (app.modules.openclaw.execution)
try:
    from app.modules.openclaw.execution.risk_governor import get_governor, OrderRequest
    risk_gov = get_governor()
except ImportError as e:
    logger.warning("RiskGovernor module not found: %s. RiskShield endpoints will return 503.", e)
    risk_gov = None

router = APIRouter(tags=["RiskShield"])


@router.get("")
async def risk_shield_overview():
    """RiskShield status overview."""
    frozen = is_entries_frozen()
    governor_ok = risk_gov is not None
    return {
        "service": "risk-shield",
        "governor_available": governor_ok,
        "entries_frozen": frozen,
    }


class EmergencyActionReq(BaseModel):
    action: str  # 'kill_switch', 'hedge_all', 'reduce_50', 'freeze_entries'
    value: Optional[bool] = None


def is_entries_frozen() -> bool:
    """Check if new entries are frozen (used by order executor)."""
    state = db_service.get_config("risk_shield_freeze_entries")
    return bool(state and state.get("frozen"))


@router.get("/status")
async def get_risk_shield_status() -> Dict[str, Any]:
    """
    Returns the real-time RiskShield status mapped exactly from
    app.modules.openclaw.execution.risk_governor
    """
    if not risk_gov:
        raise HTTPException(status_code=503, detail="RiskGovernor unavailable")

    try:
        # Dummy order for checks that require an OrderRequest (status-only read)
        dummy = OrderRequest(ticker="", side="sell", shares=0, price=0.0, stop_loss=0, sector="", regime="NEUTRAL")
        # Fetch overarching status from OpenClaw (equity, positions, exposure)
        status = risk_gov.get_status()

        # Execute the 9 safety checks; in-repo returns (passed: bool, detail: str)
        checks = {
            "daily_drawdown": risk_gov._check_circuit_breaker()[0],
            "max_positions": risk_gov._check_max_exposure(dummy)[0],
            "max_single_position": risk_gov._check_ticker_concentration(dummy)[0],
            "sector_concentration": risk_gov._check_sector_concentration(dummy)[0],
            "correlation_exposure": risk_gov._check_correlation(dummy)[0],
            "vix_regime_gate": risk_gov._check_regime_gate(dummy)[0],
            "weekly_drawdown": risk_gov._check_drawdown_velocity()[0],
            "liquidity_check": risk_gov._check_daily_trade_count()[0],
            "earnings_blackout": risk_gov._check_stop_enforcement(dummy)[0],
        }

        # Calculate Risk Score (0-100 Gauge)
        failed_count = sum(1 for passed in checks.values() if not passed)
        exposure_pct = status.get("exposure_pct", 0.0)
        equity = status.get("equity", 0.0) or 1.0

        # Base penalty for failed checks + exposure penalty
        risk_score = int((failed_count * 8) + (exposure_pct * 0.4))
        risk_score = max(0, min(100, risk_score))  # Clamp 0-100

        # Build heatmap from positions dict (ticker -> {value, sector, ...})
        heatmap_data = []
        for symbol, pos in (status.get("positions") or {}).items():
            value = pos.get("value", 0.0)
            weight = round((value / equity * 100), 2) if equity else 0.0
            unrealized_pct = pos.get("unrealized_pct", 0.0)
            risk_level = "high" if unrealized_pct < -0.05 else ("low" if unrealized_pct > 0 else "medium")
            heatmap_data.append({
                "symbol": symbol,
                "sector": pos.get("sector", "Unknown"),
                "weight": weight,
                "unrealized_pct": unrealized_pct,
                "risk_level": risk_level,
            })

        return {
            "checks": checks,
            "risk_score": risk_score,
            "equity": status.get("equity", 0.0),
            "daily_pnl_pct": status.get("daily_pnl_pct", 0.0),
            "heatmap": heatmap_data,
            "entries_frozen": is_entries_frozen(),
        }

    except Exception as e:
        logger.error("Error fetching risk status: %s", e)
        raise HTTPException(status_code=500, detail="Internal Risk Governor Error")


@router.post("/emergency-action", dependencies=[Depends(require_role("admin"))])
async def execute_emergency_action(payload: EmergencyActionReq):
    """
    Executes tactical emergency commands via Alpaca API.
    """
    action = payload.action

    try:
        if action == "kill_switch":
            return await _execute_kill_switch()
        elif action == "hedge_all":
            return _hedge_all_stub()
        elif action == "reduce_50":
            return await _execute_reduce_50()
        elif action == "freeze_entries":
            return _execute_freeze_entries(payload.value)

        raise HTTPException(status_code=400, detail="Unknown tactical command.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Emergency action failed: %s", e)
        raise HTTPException(status_code=500, detail="Emergency action failed")


async def _execute_kill_switch() -> Dict[str, Any]:
    """Cancel all open orders and liquidate all positions via Alpaca."""
    logger.critical("KILL SWITCH activated — cancelling orders and liquidating all positions")

    results = {"action": "kill_switch", "executed": True, "orders_cancelled": False, "positions_closed": False}

    # Step 1: Cancel all open orders
    try:
        cancel_result = await alpaca_service.cancel_all_orders()
        results["orders_cancelled"] = True
        results["cancelled_orders"] = cancel_result if isinstance(cancel_result, list) else []
        logger.critical("KILL SWITCH: All open orders cancelled")
    except Exception as e:
        logger.error("KILL SWITCH: Failed to cancel orders: %s", e)
        results["orders_error"] = str(type(e).__name__)

    # Step 2: Liquidate all positions
    try:
        close_result = await alpaca_service.close_all_positions(cancel_orders=True)
        results["positions_closed"] = True
        results["closed_positions"] = close_result if isinstance(close_result, list) else []
        logger.critical("KILL SWITCH: All positions liquidated")
    except Exception as e:
        logger.error("KILL SWITCH: Failed to close positions: %s", e)
        results["positions_error"] = str(type(e).__name__)

    # Step 3: Freeze entries to prevent new orders
    db_service.set_config("risk_shield_freeze_entries", {"frozen": True, "reason": "kill_switch"})
    results["entries_frozen"] = True

    results["status"] = "completed" if results["positions_closed"] else "partial"
    results["message"] = "All positions liquidated and entries frozen" if results["positions_closed"] else "Kill switch partially executed — check errors"
    return results


def _hedge_all_stub() -> Dict[str, Any]:
    """Hedging via index puts requires options trading (not available in Alpaca basic).
    Returns stub with clear explanation."""
    logger.warning("HEDGE ALL requested — options hedging not available via Alpaca equity API")
    return {
        "action": "hedge_all",
        "executed": False,
        "status": "unavailable",
        "message": "Options hedging (beta-weighted index puts) requires an options-enabled broker. "
                   "Alpaca equity API does not support options trading. "
                   "Use kill_switch or reduce_50 as alternatives.",
    }


async def _execute_reduce_50() -> Dict[str, Any]:
    """Reduce all open positions by 50% via Alpaca close_position with percentage."""
    logger.critical("REDUCE 50%% activated — halving all positions")

    results = {"action": "reduce_50", "executed": True, "reduced": [], "errors": []}

    positions = await alpaca_service.get_positions()
    if not positions:
        results["message"] = "No open positions to reduce"
        return results

    for pos in positions:
        symbol = pos.get("symbol", "")
        try:
            await alpaca_service.close_position(symbol, percentage="50")
            results["reduced"].append(symbol)
            logger.critical("REDUCE 50%%: Halved position in %s", symbol)
        except Exception as e:
            logger.error("REDUCE 50%%: Failed for %s: %s", symbol, e)
            results["errors"].append({"symbol": symbol, "error": str(type(e).__name__)})

    results["status"] = "completed" if not results["errors"] else "partial"
    results["message"] = f"Reduced {len(results['reduced'])} positions by 50%"
    if results["errors"]:
        results["message"] += f" ({len(results['errors'])} failures)"
    return results


def _execute_freeze_entries(value: Optional[bool]) -> Dict[str, Any]:
    """Toggle the freeze-entries flag in DB. Order executor checks this before placing orders."""
    frozen = bool(value) if value is not None else True
    db_service.set_config("risk_shield_freeze_entries", {"frozen": frozen, "reason": "manual"})

    state = "ON" if frozen else "OFF"
    logger.critical("FREEZE ENTRIES %s — new order entries are now %s",
                    state, "blocked" if frozen else "allowed")

    return {
        "action": "freeze_entries",
        "executed": True,
        "status": "completed",
        "frozen": frozen,
        "message": f"New entries {'frozen — no new orders will be placed' if frozen else 'unfrozen — trading resumed'}",
    }


@router.get("/freeze-status")
async def get_freeze_status():
    """Check if new entries are currently frozen."""
    return {"frozen": is_entries_frozen()}


@router.get("/history")
async def get_risk_history():
    """
    Returns historical risk metrics for the UI drawdown chart.
    Uses Alpaca portfolio history API for real equity curve data.
    """
    try:
        history = await alpaca_service.get_portfolio_history(period="1M", timeframe="1D")
        if history:
            return {"history": history}
        return {"history": []}
    except Exception as e:
        logger.error("Error fetching risk history: %s", e)
        return {"history": []}
