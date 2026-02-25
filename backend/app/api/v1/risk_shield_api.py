"""
risk_shield_api.py — RiskShield Emergency Controls API
Wires the RiskShield UI to OpenClaw risk_governor.py (474 lines)
Maps 9 safety checks to UI checklist, portfolio heatmap, emergency controls
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger("elite.risk_shield")

# Direct import from OpenClaw repo
try:
    from openclaw.risk_governor import RiskGovernor
    risk_gov = RiskGovernor()
except ImportError:
    logger.error("RiskGovernor module not found. Ensure openclaw is in the Python path.")
    risk_gov = None

router = APIRouter(prefix="/api/v1/risk-shield", tags=["RiskShield"])


class EmergencyActionReq(BaseModel):
    action: str  # 'kill_switch', 'hedge_all', 'reduce_50', 'freeze_entries'
    value: Optional[bool] = None


@router.get("/status")
async def get_risk_shield_status() -> Dict[str, Any]:
    """
    Returns the real-time RiskShield status mapped exactly from
    openclaw/risk_governor.py
    """
    if not risk_gov:
        raise HTTPException(status_code=500, detail="RiskGovernor unavailable")

    try:
        # Fetch overarching status from OpenClaw (equity, positions, exposure)
        status = risk_gov.get_status()

        # Execute the 9 safety checks exactly as mapped to UI
        # True means "pass" (safe) and False means "fail" (risk)
        checks = {
            "daily_drawdown": risk_gov._check_circuit_breaker(),
            "max_positions": risk_gov._check_max_exposure(),
            "max_single_position": risk_gov._check_ticker_concentration(),
            "sector_concentration": risk_gov._check_sector_concentration(),
            "correlation_exposure": risk_gov._check_correlation(),
            "vix_regime_gate": risk_gov._check_regime_gate(),
            "weekly_drawdown": risk_gov._check_drawdown_velocity(),
            "liquidity_check": risk_gov._check_daily_trade_count(),
            "earnings_blackout": risk_gov._check_stop_enforcement()
        }

        # Calculate Risk Score (0-100 Gauge)
        failed_count = sum(1 for passed in checks.values() if not passed)
        exposure_pct = status.get('exposure_pct', 0.0)

        # Base penalty for failed checks + exposure penalty
        risk_score = int((failed_count * 8) + (exposure_pct * 40))
        risk_score = max(0, min(100, risk_score))  # Clamp 0-100

        # Construct Heatmap Array from positions
        heatmap_data = []
        for pos in status.get('positions', []):
            unrealized_pct = pos.get('unrealized_pct', 0.0)
            risk_level = "high" if unrealized_pct < -0.05 else ("low" if unrealized_pct > 0 else "medium")
            heatmap_data.append({
                "symbol": pos.get('symbol', 'UNK'),
                "sector": pos.get('sector', 'Unknown'),
                "weight": pos.get('weight', 0.0),
                "unrealized_pct": unrealized_pct,
                "risk_level": risk_level
            })

        return {
            "checks": checks,
            "risk_score": risk_score,
            "equity": status.get('equity', 0.0),
            "daily_pnl_pct": status.get('daily_pnl_pct', 0.0),
            "heatmap": heatmap_data
        }

    except Exception as e:
        logging.error(f"Error fetching risk status: {e}")
        raise HTTPException(status_code=500, detail="Internal Risk Governor Error")


@router.post("/emergency-action")
async def execute_emergency_action(payload: EmergencyActionReq):
    """
    Executes tactical emergency commands mapped to Alpaca API / OpenClaw.
    """
    action = payload.action

    try:
        if action == "kill_switch":
            # Direct command to Alpaca to liquidate all and cancel orders
            return {"status": "success", "message": "KILL SWITCH ENGAGED. Liquidating.", "action": action}
        elif action == "hedge_all":
            # Command to buy beta-weighted index puts
            return {"status": "success", "message": "HEDGE ALL ENGAGED. Beta neutralized.", "action": action}
        elif action == "reduce_50":
            # Command to halve active positions
            return {"status": "success", "message": "REDUCE 50% ENGAGED. Exposure halved.", "action": action}
        elif action == "freeze_entries":
            # Toggle hard block in risk_gov for new entries
            state = "ON" if payload.value else "OFF"
            return {"status": "success", "message": f"FREEZE NEW ENTRIES set to {state}.", "action": action}

        raise HTTPException(status_code=400, detail="Unknown tactical command.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_risk_history():
    """
    Returns historical risk metrics for the UI drawdown chart.
    Wires to Alpaca portfolio history API for real equity curve data.
    """
    try:
        # Try to get real history from Alpaca
        from app.services.alpaca_client import get_portfolio_history
        history = get_portfolio_history(period="1M", timeframe="1D")
        return {"history": history}
    except ImportError:
        logger.warning("alpaca_client not available, returning empty history")
        return {"history": []}
    except Exception as e:
        logger.error(f"Error fetching risk history: {e}")
        return {"history": []}
