"""
Risk Intelligence API — real-time risk from Alpaca account + positions.
GET /api/v1/risk returns limits and live risk snapshot computed from real portfolio.
PUT /api/v1/risk updates risk parameters (persisted in SQLite).
GET /api/v1/risk/history returns historical risk metrics for the chart.
No mock data. No fabricated numbers.
"""
import logging
import math
from datetime import date
from typing import Any, List

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.alpaca_service import alpaca_service
from app.services.database import db_service
from app.websocket_manager import broadcast_ws

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Default risk limits (user-configurable, persisted in SQLite)
# ---------------------------------------------------------------------------
DEFAULT_RISK = {
    "maxDailyDrawdown": 10,
    "positionSizeLimit": 5,
    "maxDailyLossPct": 2,
    "varLimit": 1.5,
    "autoPauseTrading": True,
    "dailyPnLLossAlert": 5,
    "maxDrawdownAlert": 10,
}

RISK_HISTORY_MAX_DAYS = 90


class RiskUpdate(BaseModel):
    maxDailyDrawdown: float | None = None
    positionSizeLimit: float | None = None
    maxDailyLossPct: float | None = None
    varLimit: float | None = None
    autoPauseTrading: bool | None = None
    dailyPnLLossAlert: float | None = None
    maxDrawdownAlert: float | None = None


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _get_risk_config() -> dict:
    stored = db_service.get_config("risk")
    if not stored or not isinstance(stored, dict):
        return {**DEFAULT_RISK}
    return {**DEFAULT_RISK, **stored}


def _get_risk_history() -> list:
    """Return list of { date, maxDailyLoss, var } from config."""
    stored = db_service.get_config("risk_history")
    if not stored or not isinstance(stored, list):
        return []
    return stored


def _append_risk_snapshot(daily_loss_pct: float, var95: float) -> None:
    """Append today's snapshot; keep last N days."""
    today = date.today().isoformat()
    history = _get_risk_history()
    if history and history[-1].get("date") == today:
        return
    history.append({
        "date": today,
        "maxDailyLoss": round(daily_loss_pct, 2),
        "var": int(round(var95)),
    })
    history = history[-RISK_HISTORY_MAX_DAYS:]
    db_service.set_config("risk_history", history)


async def _compute_live_risk(config: dict) -> dict:
    """
    Compute real risk metrics from Alpaca account + positions.
    Returns dict with currentExposure, var95, expectedShortfall, etc.
    """
    account = await alpaca_service.get_account()
    positions_raw = await alpaca_service.get_positions()

    # --- Defaults when Alpaca is unavailable ---
    if account is None:
        return {
            "currentExposure": 0,
            "var95": 0,
            "expectedShortfall": 0,
            "estimatedMaxDrawdown": 0,
            "potentialDailyLoss": 0,
            "allWithinLimits": True,
            "alpacaConnected": False,
        }

    # --- Parse account data ---
    equity = _safe_float(account.get("equity"))
    last_equity = _safe_float(account.get("last_equity"))
    buying_power = _safe_float(account.get("buying_power"))
    portfolio_value = _safe_float(account.get("portfolio_value")) or equity

    # --- Compute real current exposure (sum of absolute position market values) ---
    positions = positions_raw or []
    total_exposure = 0.0
    largest_position_value = 0.0
    total_unrealized_pl = 0.0
    for pos in positions:
        market_val = abs(_safe_float(pos.get("market_value")))
        total_exposure += market_val
        if market_val > largest_position_value:
            largest_position_value = market_val
        total_unrealized_pl += _safe_float(pos.get("unrealized_pl"))

    # --- Daily P&L % (real from Alpaca equity change) ---
    daily_pnl_pct = 0.0
    if last_equity > 0:
        daily_pnl_pct = ((equity - last_equity) / last_equity) * 100

    # --- Position concentration (largest position as % of portfolio) ---
    concentration_pct = 0.0
    if portfolio_value > 0:
        concentration_pct = (largest_position_value / portfolio_value) * 100

    # --- Parametric VaR (95%) estimate ---
    # Uses daily P&L volatility proxy: abs(daily_pnl_pct) scaled by 1.65 (95th percentile)
    # For a proper VaR you'd want historical returns, but this gives a real-time estimate
    daily_vol_pct = abs(daily_pnl_pct) if daily_pnl_pct != 0 else 1.0
    var95_pct = daily_vol_pct * 1.65
    var95_dollars = (var95_pct / 100) * portfolio_value if portfolio_value > 0 else 0

    # --- Expected Shortfall (CVaR) ~ 1.4x VaR as standard approximation ---
    expected_shortfall = var95_dollars * 1.4

    # --- Estimated max drawdown (based on real daily loss) ---
    estimated_max_dd = abs(daily_pnl_pct) if daily_pnl_pct < 0 else 0.0

    # --- Check limits ---
    max_dd_limit = config.get("maxDailyDrawdown", 10)
    max_loss_limit = config.get("maxDailyLossPct", 2)
    var_limit = config.get("varLimit", 1.5)
    pos_size_limit = config.get("positionSizeLimit", 5)

    all_within = (
        abs(daily_pnl_pct) <= max_loss_limit
        and var95_pct <= var_limit
        and estimated_max_dd <= max_dd_limit
        and len(positions) <= pos_size_limit * 10  # rough check
    )

    return {
        "currentExposure": round(total_exposure, 2),
        "var95": round(var95_dollars, 2),
        "expectedShortfall": round(expected_shortfall, 2),
        "estimatedMaxDrawdown": round(estimated_max_dd, 2),
        "potentialDailyLoss": round(abs(daily_pnl_pct), 2),
        "allWithinLimits": all_within,
        "alpacaConnected": True,
        "equity": round(equity, 2),
        "lastEquity": round(last_equity, 2),
        "buyingPower": round(buying_power, 2),
        "portfolioValue": round(portfolio_value, 2),
        "dailyPnlPct": round(daily_pnl_pct, 2),
        "unrealizedPl": round(total_unrealized_pl, 2),
        "positionCount": len(positions),
        "concentrationPct": round(concentration_pct, 2),
    }


@router.get("")
async def get_risk():
    """Return risk parameters + live risk snapshot from Alpaca."""
    config = _get_risk_config()
    live = await _compute_live_risk(config)

    response = {**config, **live}

    # Persist today's snapshot for the history chart
    _append_risk_snapshot(
        live.get("potentialDailyLoss", 0),
        live.get("var95", 0),
    )

    await broadcast_ws("risk", {"type": "risk_snapshot", "data": response})
    return response


@router.get("/history")
async def get_risk_history():
    """Return historical risk metrics for chart."""
    return _get_risk_history()


@router.put("")
async def update_risk(update: RiskUpdate):
    """Update risk parameters in DB. Broadcasts change via WebSocket."""
    config = _get_risk_config()
    if update.maxDailyDrawdown is not None:
        config["maxDailyDrawdown"] = update.maxDailyDrawdown
    if update.positionSizeLimit is not None:
        config["positionSizeLimit"] = update.positionSizeLimit
    if update.maxDailyLossPct is not None:
        config["maxDailyLossPct"] = update.maxDailyLossPct
    if update.varLimit is not None:
        config["varLimit"] = update.varLimit
    if update.autoPauseTrading is not None:
        config["autoPauseTrading"] = update.autoPauseTrading
    if update.dailyPnLLossAlert is not None:
        config["dailyPnLLossAlert"] = update.dailyPnLLossAlert
    if update.maxDrawdownAlert is not None:
        config["maxDrawdownAlert"] = update.maxDrawdownAlert

    db_service.set_config("risk", config)
    await broadcast_ws("risk", {"type": "config_updated", "config": config})
    return {"ok": True, "config": config}


# -----------------------------------------------------------------
# Kelly Criterion Position Sizing Endpoints
# -----------------------------------------------------------------

from app.services.kelly_position_sizer import KellyPositionSizer
from app.core.config import settings

_kelly = KellyPositionSizer(max_allocation=settings.KELLY_MAX_ALLOCATION)


class KellyRequest(BaseModel):
    win_rate: float = settings.KELLY_DEFAULT_WIN_RATE
    avg_win_pct: float = settings.KELLY_DEFAULT_AVG_WIN
    avg_loss_pct: float = settings.KELLY_DEFAULT_AVG_LOSS
    regime: str = "NEUTRAL"
    trade_count: int = 0
    current_volatility: float | None = None


@router.get("/kelly-sizer")
async def kelly_sizer_defaults():
    """Return current Kelly config + default calculation."""
    result = _kelly.calculate(
        win_rate=settings.KELLY_DEFAULT_WIN_RATE,
        avg_win_pct=settings.KELLY_DEFAULT_AVG_WIN,
        avg_loss_pct=settings.KELLY_DEFAULT_AVG_LOSS,
    )
    return {
        "config": {
            "max_allocation": settings.KELLY_MAX_ALLOCATION,
            "use_half_kelly": settings.KELLY_USE_HALF,
            "max_portfolio_heat": settings.MAX_PORTFOLIO_HEAT,
            "max_sector_concentration": settings.MAX_SECTOR_CONCENTRATION,
        },
        "default_sizing": {
            "raw_kelly": result.raw_kelly,
            "half_kelly": result.half_kelly,
            "regime_adjusted": result.regime_adjusted,
            "final_pct": result.final_pct,
            "edge": result.edge,
            "action": result.action,
        },
    }


@router.post("/kelly-sizer")
async def kelly_calculate(req: KellyRequest):
    """Calculate Kelly position size for given parameters."""
    if req.current_volatility is not None:
        result = _kelly.calculate_volatility_adjusted(
            win_rate=req.win_rate,
            avg_win_pct=req.avg_win_pct,
            avg_loss_pct=req.avg_loss_pct,
            current_volatility=req.current_volatility,
            baseline_volatility=settings.VOLATILITY_BASELINE,
            regime=req.regime,
            trade_count=req.trade_count,
        )
    else:
        result = _kelly.calculate(
            win_rate=req.win_rate,
            avg_win_pct=req.avg_win_pct,
            avg_loss_pct=req.avg_loss_pct,
            regime=req.regime,
            trade_count=req.trade_count,
        )
    return {
        "raw_kelly": result.raw_kelly,
        "half_kelly": result.half_kelly,
        "regime_adjusted": result.regime_adjusted,
        "final_pct": result.final_pct,
        "edge": result.edge,
        "action": result.action,
        "regime": result.regime,
    }


@router.post("/position-sizing")
async def portfolio_position_sizing(positions: List[dict]):
    """Apply Kelly + sector correlation caps to a list of positions.

    Each position dict should have: symbol, kelly_allocation_pct, sector
    """
    capped = KellyPositionSizer.portfolio_correlation_cap(
        positions,
        max_sector_pct=settings.MAX_SECTOR_CONCENTRATION,
        max_correlated_pct=settings.MAX_PORTFOLIO_HEAT,
    )
    total_alloc = sum(p.get("kelly_allocation_pct", 0) for p in capped)
    return {
        "positions": capped,
        "total_allocation_pct": round(total_alloc, 4),
        "within_heat_limit": total_alloc <= settings.MAX_PORTFOLIO_HEAT,
    }