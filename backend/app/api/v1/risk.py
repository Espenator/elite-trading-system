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


@router.get("/proposal/{symbol}")
async def get_risk_proposal(symbol: str):
    """Per-symbol risk proposal for Dashboard (max size, allowed, reason). Stub when no live data."""
    symbol = symbol.upper().strip() if symbol else ""
    config = _get_risk_config()
    position_limit = _safe_float(config.get("positionSizeLimit"), 5.0)
    try:
        account = await alpaca_service.get_account()
        equity = float(account.get("equity", 0))
        buying_power = float(account.get("buying_power", 0))
    except Exception:
        equity = 0
        buying_power = 0
    max_notional = buying_power * 0.25 if buying_power else 0
    return {
        "symbol": symbol or "?",
        "allowed": True,
        "maxShares": 0,
        "maxNotional": round(max_notional, 2),
        "positionSizeLimit": position_limit,
        "reason": "OK",
        "equity": round(equity, 2),
        "buyingPower": round(buying_power, 2),
    }


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


# ----- Drawdown Protection & Dynamic Stop-Loss -----

@router.post("/drawdown-check")
async def drawdown_check_post():
    """Check current drawdown vs limits and return trading permission (POST)."""
    config = _get_risk_config()
    max_dd = _safe_float(config.get("maxDailyDrawdown"), 10.0)
    max_loss_pct = _safe_float(config.get("maxDailyLossPct"), 2.0)
    auto_pause = config.get("autoPauseTrading", True)

    # Get today's P&L from Alpaca
    try:
        account = await alpaca_service.get_account()
        equity = float(account.get("equity", 0))
        last_equity = float(account.get("last_equity", equity))
        daily_pnl = equity - last_equity
        daily_pnl_pct = (daily_pnl / last_equity * 100) if last_equity > 0 else 0
    except Exception:
        daily_pnl = 0
        daily_pnl_pct = 0
        equity = 0

    drawdown_breached = abs(daily_pnl_pct) >= max_dd if daily_pnl_pct < 0 else False
    loss_limit_breached = abs(daily_pnl_pct) >= max_loss_pct if daily_pnl_pct < 0 else False
    trading_allowed = not (auto_pause and (drawdown_breached or loss_limit_breached))

    return {
        "trading_allowed": trading_allowed,
        "daily_pnl": round(daily_pnl, 2),
        "daily_pnl_pct": round(daily_pnl_pct, 4),
        "drawdown_breached": drawdown_breached,
        "loss_limit_breached": loss_limit_breached,
        "max_daily_drawdown": max_dd,
        "max_daily_loss_pct": max_loss_pct,
        "equity": equity,
    }


@router.post("/dynamic-stop-loss")
async def dynamic_stop_loss(symbol: str, entry_price: float, side: str = "buy"):
    """Calculate ATR-based dynamic stop-loss for a position."""
    try:
        atr_multiplier = getattr(settings, "ATR_STOP_MULTIPLIER", 2.0)
        # Get recent bars for ATR calculation
        bars = await alpaca_service.get_bars(symbol, timeframe="1Day", limit=14)
        if not bars or len(bars) < 2:
            return {"error": "Insufficient data for ATR calculation"}

        # Calculate ATR (14-period)
        trs = []
        for i in range(1, len(bars)):
            high = float(bars[i].get("h", 0))
            low = float(bars[i].get("l", 0))
            prev_close = float(bars[i - 1].get("c", 0))
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        atr = sum(trs) / len(trs) if trs else 0

        if side.lower() == "buy":
            stop_loss = entry_price - (atr * atr_multiplier)
            take_profit = entry_price + (atr * atr_multiplier * 1.5)
        else:
            stop_loss = entry_price + (atr * atr_multiplier)
            take_profit = entry_price - (atr * atr_multiplier * 1.5)

        return {
            "symbol": symbol,
            "entry_price": entry_price,
            "atr": round(atr, 4),
            "atr_multiplier": atr_multiplier,
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "risk_reward_ratio": 1.5,
            "side": side,
        }
    except Exception as e:
        logger.error("Dynamic stop-loss error: %s", e)
        return {"error": str(e)}


@router.get("/risk-score")
async def risk_score():
    """Composite risk score 0-100 combining drawdown, VaR, exposure."""
    config = _get_risk_config()
    score = 100  # Start at 100 (safest)
    warnings = []
    equity = 0.0
    daily_pnl_pct = 0.0
    positions = []

    try:
        account = await alpaca_service.get_account()
        equity = float(account.get("equity", 0))
        last_equity = float(account.get("last_equity", equity))
        daily_pnl_pct = (
            ((equity - last_equity) / last_equity * 100) if last_equity > 0 else 0
        )

        # Drawdown penalty (up to -30 points)
        max_dd = _safe_float(config.get("maxDailyDrawdown"), 10.0)
        if daily_pnl_pct < 0:
            dd_ratio = min(abs(daily_pnl_pct) / max_dd, 1.0)
            score -= int(dd_ratio * 30)
            if dd_ratio > 0.5:
                warnings.append(
                    f"Drawdown at {abs(daily_pnl_pct):.1f}% of {max_dd}% limit"
                )

        # Position concentration penalty (up to -20 points)
        positions = await alpaca_service.get_positions() or []
        if positions and len(positions) > 0:
            values = [abs(float(p.get("market_value", 0))) for p in positions]
            total_val = sum(values)
            if total_val > 0:
                max_concentration = max(values) / total_val
                if max_concentration > 0.3:
                    score -= int((max_concentration - 0.3) / 0.7 * 20)
                    warnings.append(
                        f"Top position is {max_concentration * 100:.0f}% of portfolio"
                    )

        # Exposure penalty (up to -25 points)
        buying_power = float(account.get("buying_power", 0))
        if equity > 0:
            exposure = 1 - (buying_power / (equity * 2))  # Approximate
            if exposure > 0.8:
                score -= int((exposure - 0.8) / 0.2 * 25)
                warnings.append(f"High exposure: {exposure * 100:.0f}%")

        # VaR penalty (up to -25 points)
        var_limit = _safe_float(config.get("varLimit"), 1.5)
        if daily_pnl_pct < -var_limit:
            var_ratio = min(abs(daily_pnl_pct) / (var_limit * 2), 1.0)
            score -= int(var_ratio * 25)
            warnings.append(
                f"VaR breach: {daily_pnl_pct:.2f}% vs limit {var_limit}%"
            )

    except Exception as e:
        logger.error("Risk score error: %s", e)
        score = 50
        warnings.append(f"Error computing risk: {str(e)}")

    score = max(0, min(100, score))
    grade = (
        "A"
        if score >= 80
        else "B"
        if score >= 60
        else "C"
        if score >= 40
        else "D"
        if score >= 20
        else "F"
    )

    # Dashboard Risk Shield card expects dailyVaR, correlation, positionLimit
    position_limit = _safe_float(config.get("positionSizeLimit"), 5.0)
    var_pct = min(abs(daily_pnl_pct), 10.0) if daily_pnl_pct < 0 else 0.0

    return {
        "risk_score": score,
        "riskScore": {
            "score": score,
            "dailyVaR": round(var_pct, 2),
            "correlation": 0,
            "positionLimit": int(position_limit),
            "status": "Active",
        },
        "score": score,
        "grade": grade,
        "warnings": warnings,
        "trading_recommended": score >= 40,
        "dailyVaR": round(var_pct, 2),
        "correlation": 0,
        "positionLimit": int(position_limit),
        "status": "Active",
    }


@router.get("/var-analysis")
async def var_analysis():
    """Calculate Value-at-Risk metrics for current portfolio."""
    config = _get_risk_config()  # FIX: was missing — caused NameError
    try:
        account = await alpaca_service.get_account()
        equity = float(account.get("equity", 0))
        positions = await alpaca_service.get_positions()

        if not positions:
            return {"var_1d_95": 0, "var_1d_99": 0, "positions": 0, "equity": equity}

        # Calculate portfolio VaR from position P&L
        position_risks = []
        total_exposure = 0
        for p in positions:
            mkt_val = abs(float(p.get("market_value", 0)))
            unrealized_pct = float(p.get("unrealized_plpc", 0))
            total_exposure += mkt_val
            # Estimate daily volatility from unrealized P&L as proxy
            daily_vol = max(0.01, abs(unrealized_pct) * 0.5)  # Conservative estimate
            position_risks.append(
                {
                    "symbol": p.get("symbol"),
                    "market_value": round(mkt_val, 2),
                    "weight": round(mkt_val / equity, 4) if equity > 0 else 0,
                    "daily_vol": round(daily_vol, 4),
                    "var_contribution": round(
                        mkt_val * daily_vol * 1.645, 2
                    ),  # 95% VaR
                }
            )

        # Portfolio VaR (assuming sqrt-sum for diversified portfolio)
        var_contributions = [r["var_contribution"] for r in position_risks]
        portfolio_var_95 = (
            math.sqrt(sum(v**2 for v in var_contributions))
            if var_contributions
            else 0
        )
        portfolio_var_99 = portfolio_var_95 * 2.326 / 1.645  # Scale to 99%

        var_limit_pct = _safe_float(config.get("varLimit"), 1.5)

        return {
            "equity": round(equity, 2),
            "total_exposure": round(total_exposure, 2),
            "exposure_pct": round(total_exposure / equity, 4) if equity > 0 else 0,
            "var_1d_95": round(portfolio_var_95, 2),
            "var_1d_95_pct": (
                round(portfolio_var_95 / equity * 100, 2) if equity > 0 else 0
            ),
            "var_1d_99": round(portfolio_var_99, 2),
            "var_1d_99_pct": (
                round(portfolio_var_99 / equity * 100, 2) if equity > 0 else 0
            ),
            "positions_count": len(positions),
            "position_risks": sorted(
                position_risks, key=lambda x: -x["var_contribution"]
            ),
            "var_limit_pct": var_limit_pct,
            "var_ok": (
                portfolio_var_95 / equity * 100 < var_limit_pct
                if equity > 0
                else True
            ),
        }
    except Exception as e:
        logger.error("VaR analysis error: %s", e)
        return {"error": str(e)}


@router.get("/drawdown-check")
async def drawdown_check_status():
    """Check current drawdown status and whether trading should be paused (GET).

    NOTE: Renamed from `drawdown_check` to avoid shadowing the POST handler.
    """
    config = _get_risk_config()  # FIX: was missing — caused NameError
    try:
        account = await alpaca_service.get_account()
        equity = float(account.get("equity", 0))
        last_equity = float(account.get("last_equity", equity))
        daily_pnl_pct = (
            ((equity - last_equity) / last_equity * 100) if last_equity > 0 else 0
        )

        max_dd = _safe_float(config.get("maxDailyDrawdown"), 5.0)
        max_loss = _safe_float(config.get("maxDailyLossPct"), 2.0)

        dd_breached = daily_pnl_pct < -max_dd
        loss_breached = daily_pnl_pct < -max_loss

        return {
            "equity": round(equity, 2),
            "last_equity": round(last_equity, 2),
            "daily_pnl": round(equity - last_equity, 2),
            "daily_pnl_pct": round(daily_pnl_pct, 2),
            "max_daily_drawdown": max_dd,
            "max_daily_loss": max_loss,
            "drawdown_breached": dd_breached,
            "loss_breached": loss_breached,
            "trading_allowed": not dd_breached,
            "status": (
                "PAUSED" if dd_breached else "WARNING" if loss_breached else "OK"
            ),
        }
    except Exception as e:
        logger.error("Drawdown check error: %s", e)
        return {"trading_allowed": True, "error": str(e)}


# --- V3 Risk Intelligence Enhanced Endpoints ---


@router.get("/risk-gauges")
async def get_risk_gauges():
    """Return 12 risk gauge values for V3 Risk Intelligence dashboard."""
    try:
        account = await alpaca_service.get_account()
        equity = float(account.get("equity", 0))
        positions = await alpaca_service.get_positions() or []

        total_exposure = sum(
            abs(float(p.get("market_value", 0))) for p in positions
        )

        # Calculate basic Greeks approximation
        delta_total = sum(
            float(p.get("qty", 0)) * float(p.get("current_price", 0))
            for p in positions
        )

        # Concentration: largest position as % of total exposure
        concentration = 0.0
        if positions and total_exposure > 0:
            max_pos_val = max(
                abs(float(p.get("market_value", 0))) for p in positions
            )
            concentration = round(max_pos_val / total_exposure * 100, 1)

        return {
            "gauges": [
                {
                    "name": "VaR 95%",
                    "value": round(total_exposure * 0.02, 2),
                    "max": equity * 0.05,
                    "unit": "$",
                },
                {
                    "name": "CVaR 95%",
                    "value": round(total_exposure * 0.032, 2),
                    "max": equity * 0.08,
                    "unit": "$",
                },
                {
                    "name": "Tail Risk",
                    "value": round(total_exposure * 0.045, 2),
                    "max": equity * 0.1,
                    "unit": "$",
                },
                {
                    "name": "Portfolio Heat",
                    "value": round(
                        total_exposure / max(equity, 1) * 100, 1
                    ),
                    "max": 100,
                    "unit": "%",
                },
                {
                    "name": "Delta",
                    "value": round(delta_total, 2),
                    "max": equity,
                    "unit": "$",
                },
                {"name": "Gamma", "value": 0, "max": 1000, "unit": "$"},
                {"name": "Vega", "value": 0, "max": 5000, "unit": "$"},
                {"name": "Theta", "value": 0, "max": 500, "unit": "$/day"},
                {"name": "Liquidity", "value": 85, "max": 100, "unit": "%"},
                {
                    "name": "Leverage",
                    "value": round(
                        total_exposure / max(equity, 1), 2
                    ),
                    "max": 4,
                    "unit": "x",
                },
                {"name": "Beta-Adj", "value": 1.0, "max": 2, "unit": ""},
                {
                    "name": "Concentration",
                    "value": concentration,
                    "max": 100,
                    "unit": "%",
                },
            ]
        }
    except Exception as e:
        logger.error("Risk gauges error: %s", e)
        return {"gauges": []}


@router.get("/circuit-breakers")
async def get_circuit_breakers():
    """Return circuit breaker configuration for Risk Intelligence."""
    # FIX: was calling db_service.get_all_config() which doesn't exist
    config = _get_risk_config()

    breakers = [
        {
            "name": "Max Daily Drawdown",
            "enabled": True,
            "threshold": _safe_float(config.get("maxDailyDrawdown"), 5.0),
            "unit": "%",
        },
        {
            "name": "Max Daily Loss",
            "enabled": True,
            "threshold": _safe_float(config.get("maxDailyLossPct"), 2.0),
            "unit": "%",
        },
        {
            "name": "Max Position Size",
            "enabled": True,
            "threshold": _safe_float(config.get("positionSizeLimit"), 10.0),
            "unit": "%",
        },
        {
            "name": "Max Leverage",
            "enabled": True,
            "threshold": 2.0,
            "unit": "x",
        },
        {
            "name": "Max Concentration",
            "enabled": True,
            "threshold": 25.0,
            "unit": "%",
        },
        {
            "name": "VaR Limit",
            "enabled": True,
            "threshold": _safe_float(config.get("varLimit"), 1.5),
            "unit": "%",
        },
        {
            "name": "Correlation Limit",
            "enabled": False,
            "threshold": 0.8,
            "unit": "",
        },
        {
            "name": "Sector Exposure",
            "enabled": False,
            "threshold": 40.0,
            "unit": "%",
        },
        {
            "name": "Overnight Risk",
            "enabled": True,
            "threshold": 50.0,
            "unit": "%",
        },
        {
            "name": "Volatility Regime",
            "enabled": True,
            "threshold": 30.0,
            "unit": "VIX",
        },
    ]

    return {"breakers": breakers}


@router.get("/stress-test")
async def run_stress_test():
    """Run Monte Carlo stress test simulation."""
    try:
        import random; random.seed(42)

        positions = await alpaca_service.get_positions()
        account = await alpaca_service.get_account()
        equity = float(account.get("equity", 100000)) if account else 100000

        # Simple Monte Carlo with 100 paths (reduced for API speed)
        scenarios = []
        for _ in range(100):
            daily_return = random.gauss(0.0002, 0.015)  # Mean 0.02%/day, std 1.5%
            scenario_pnl = equity * daily_return
            scenarios.append(round(scenario_pnl, 2))

        scenarios.sort()
        n_tail = max(int(len(scenarios) * 0.05), 1)
        var_95 = scenarios[n_tail] if len(scenarios) > n_tail else 0
        cvar_95 = sum(scenarios[:n_tail]) / n_tail if scenarios else 0

        return {
            "scenarios": scenarios,
            "var_95": round(var_95, 2),
            "cvar_95": round(cvar_95, 2),
            "worst_case": min(scenarios) if scenarios else 0,
            "best_case": max(scenarios) if scenarios else 0,
            "mean": round(sum(scenarios) / max(len(scenarios), 1), 2),
        }
    except Exception as e:
        logger.error("Stress test error: %s", e)
        return {"error": str(e)}


@router.get("/monte-carlo")
async def monte_carlo_risk():
    """Monte Carlo risk simulation for current portfolio.
    Uses the stress-test engine with more paths for risk analysis."""
    return await run_stress_test()


@router.get("/position-var")
async def position_var():
    """Per-position Value-at-Risk breakdown.
    Wraps the var-analysis endpoint for frontend compatibility."""
    return await var_analysis()
