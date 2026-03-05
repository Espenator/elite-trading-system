"""
Strategy Intelligence API — controls + strategies persisted in SQLite.
GET /api/v1/strategy returns strategies and controls from DB.
POST /api/v1/strategy/controls updates emergency controls.
POST /api/v1/strategy adds a new strategy (from agents/config).
PUT /api/v1/strategy/{strategy_id} updates strategy metrics.
No mock data. No fabricated numbers.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from app.core.security import require_auth
from pydantic import BaseModel

from app.services.database import db_service
from app.websocket_manager import broadcast_ws

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_CONTROLS = {
    "masterSwitch": True,
    "pauseAll": False,
    "closeAllPositions": False,
    "regimeOverride": None,  # None = auto-detect, or BULL/BEAR/NEUTRAL/CRISIS
    "kellyEnabled": True,
    "maxPositionPct": 0.10,
    "maxPortfolioHeat": 0.25,
}


class StrategyControls(BaseModel):
    masterSwitch: bool | None = None
    pauseAll: bool | None = None
    closeAllPositions: bool | None = None
    regimeOverride: Optional[str] = None
    kellyEnabled: bool | None = None
    maxPositionPct: Optional[float] = None
    maxPortfolioHeat: Optional[float] = None


class StrategyCreate(BaseModel):
    """Schema for registering a strategy."""
    name: str
    description: str = ""
    status: str = "Inactive"  # Active, Paused, Inactive, Error


class StrategyMetricsUpdate(BaseModel):
    """Schema for updating strategy performance metrics."""
    status: Optional[str] = None
    dailyPL: Optional[float] = None
    winRate: Optional[float] = None
    maxDrawdown: Optional[float] = None


def _get_controls() -> dict:
    stored = db_service.get_config("strategy_controls")
    if not stored or not isinstance(stored, dict):
        return {**DEFAULT_CONTROLS}
    return {**DEFAULT_CONTROLS, **stored}


def _get_strategies() -> list:
    """Return strategies from DB."""
    stored = db_service.get_config("strategies")
    if not stored or not isinstance(stored, list):
        return []
    return stored


def _save_strategies(strategies: list) -> None:
    db_service.set_config("strategies", strategies)


def _next_id(strategies: list) -> int:
    if not strategies:
        return 1
    return max(s.get("id", 0) for s in strategies) + 1


@router.get("")
async def get_strategies():
    """
    Return active strategies and controls from DB.
    Strategies are registered by config/agents, not hardcoded.
    Returns empty list if no strategies registered yet.
    """
    controls = _get_controls()
    strategies = _get_strategies()
    return {"controls": controls, "strategies": strategies}


@router.post("", dependencies=[Depends(require_auth)])
async def create_strategy(data: StrategyCreate):
    """Register a new strategy (from config or agents)."""
    strategies = _get_strategies()
    new_strategy = {
        "id": _next_id(strategies),
        "name": data.name,
        "status": data.status,
        "description": data.description,
        "dailyPL": 0.0,
        "winRate": 0,
        "maxDrawdown": 0.0,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    strategies.append(new_strategy)
    _save_strategies(strategies)
    await broadcast_ws("strategy", {"type": "strategy_created", "strategy": new_strategy})
    logger.info("Strategy registered: %s", data.name)
    return {"ok": True, "strategy": new_strategy}


@router.put("/{strategy_id}", dependencies=[Depends(require_auth)])
async def update_strategy_metrics(strategy_id: int, update: StrategyMetricsUpdate):
    """Update strategy performance metrics (called by execution engine)."""
    strategies = _get_strategies()
    for s in strategies:
        if s.get("id") == strategy_id:
            if update.status is not None:
                s["status"] = update.status
            if update.dailyPL is not None:
                s["dailyPL"] = round(update.dailyPL, 2)
            if update.winRate is not None:
                s["winRate"] = round(update.winRate, 1)
            if update.maxDrawdown is not None:
                s["maxDrawdown"] = round(update.maxDrawdown, 2)
            s["updatedAt"] = datetime.now(timezone.utc).isoformat()
            _save_strategies(strategies)
            await broadcast_ws("strategy", {"type": "strategy_updated", "strategy": s})
            return {"ok": True, "strategy": s}
    raise HTTPException(status_code=404, detail="Strategy not found")


@router.delete("/{strategy_id}", dependencies=[Depends(require_auth)])
async def remove_strategy(strategy_id: int):
    """Remove a strategy by ID."""
    strategies = _get_strategies()
    original_len = len(strategies)
    strategies = [s for s in strategies if s.get("id") != strategy_id]
    if len(strategies) == original_len:
        raise HTTPException(status_code=404, detail="Strategy not found")
    _save_strategies(strategies)
    await broadcast_ws("strategy", {"type": "strategy_removed", "id": strategy_id})
    return {"ok": True}


@router.post("/controls", dependencies=[Depends(require_auth)])
async def update_controls(controls: StrategyControls):
    """Update emergency controls in DB. Broadcasts change via WebSocket."""
    ctrl = _get_controls()
    if controls.masterSwitch is not None:
        ctrl["masterSwitch"] = controls.masterSwitch
    if controls.pauseAll is not None:
        ctrl["pauseAll"] = controls.pauseAll
    if controls.closeAllPositions is not None:
        ctrl["closeAllPositions"] = controls.closeAllPositions
    if controls.regimeOverride is not None:
        ctrl["regimeOverride"] = controls.regimeOverride
    if controls.kellyEnabled is not None:
        ctrl["kellyEnabled"] = controls.kellyEnabled
    if controls.maxPositionPct is not None:
        ctrl["maxPositionPct"] = controls.maxPositionPct
    if controls.maxPortfolioHeat is not None:
        ctrl["maxPortfolioHeat"] = controls.maxPortfolioHeat
    db_service.set_config("strategy_controls", ctrl)
    await broadcast_ws("strategy", {"type": "controls_updated", "controls": ctrl})
    return {"ok": True, "controls": ctrl}


# -----------------------------------------------------------------
# Regime-Aware Strategy Recommendations
# -----------------------------------------------------------------
REGIME_PARAMS = {
    "GREEN": {"kelly_scale": 1.5, "max_pos": 6, "risk_pct": 2.0, "signal_mult": 1.10, "min_edge": 0.03, "desc": "Momentum - full Kelly, higher conviction"},
    "YELLOW": {"kelly_scale": 1.0, "max_pos": 5, "risk_pct": 1.5, "signal_mult": 1.0, "min_edge": 0.05, "desc": "Cautious - reduced sizing, tighter filters"},
    "RED": {"kelly_scale": 0.25, "max_pos": 0, "risk_pct": 0.0, "signal_mult": 0.85, "min_edge": 0.12, "desc": "Defensive - no new positions, protect capital"},
    "RED_RECOVERY": {"kelly_scale": 0.75, "max_pos": 4, "risk_pct": 1.0, "signal_mult": 0.95, "min_edge": 0.08, "desc": "Re-entry - cautious scaling back in"},
    # Legacy aliases for backward compatibility
    "BULL": {"kelly_scale": 1.5, "max_pos": 6, "risk_pct": 2.0, "signal_mult": 1.10, "min_edge": 0.03, "desc": "Alias for GREEN"},
    "NEUTRAL": {"kelly_scale": 1.0, "max_pos": 5, "risk_pct": 1.5, "signal_mult": 1.0, "min_edge": 0.05, "desc": "Alias for YELLOW"},
    "BEAR": {"kelly_scale": 0.25, "max_pos": 0, "risk_pct": 0.0, "signal_mult": 0.85, "min_edge": 0.12, "desc": "Alias for RED"},
    "CRISIS": {"kelly_scale": 0.0, "max_pos": 0, "risk_pct": 0.0, "signal_mult": 0.0, "min_edge": 1.0, "desc": "Full cash, zero exposure"},
}


@router.get("/regime-params")
async def get_regime_params():
    """
    Return current regime and Kelly scaling parameters.
    Aligned with Market Regime page GREEN/YELLOW/RED/RED_RECOVERY states.
    Also sources live regime from OpenClaw bridge when available.
    """
    ctrl = _get_controls()
    override = ctrl.get("regimeOverride")

    # Try to get live regime from OpenClaw bridge
    live_regime = None
    try:
        from app.services.openclaw_bridge_service import openclaw_bridge
        regime_data = await openclaw_bridge.get_regime()
        if regime_data and regime_data.get("state"):
            live_regime = regime_data["state"]
    except Exception:
        pass

    # Priority: manual override > live bridge > DB config > YELLOW default
    if override:
        regime = override
    elif live_regime:
        regime = live_regime
    else:
        regime = "YELLOW"

    params = REGIME_PARAMS.get(regime, REGIME_PARAMS["YELLOW"])
    return {
        "regime": regime,
        "is_override": override is not None,
        "kelly_scale": params["kelly_scale"],
        "kelly_mult": params["kelly_scale"],
        "max_position_pct": params["max_pos"] * 0.01 if isinstance(params["max_pos"], int) and params["max_pos"] > 1 else params["max_pos"],
        "max_positions": params["max_pos"],
        "risk_pct": params.get("risk_pct", 1.0),
        "signal_mult": params.get("signal_mult", 1.0),
        "min_edge_threshold": params["min_edge"],
        "description": params["desc"],
        "kelly_enabled": ctrl.get("kellyEnabled", True),
    }


# ----------------------------------------------------------------
# Pre-Trade Risk Guard: checks drawdown + risk score before execution
# ----------------------------------------------------------------
@router.post("/pre-trade-check/{symbol}", dependencies=[Depends(require_auth)])
async def pre_trade_check(symbol: str = "", side: str = "buy"):
    """
    Gate every trade through drawdown + risk score checks.
    Returns go/no-go with reasons.
    """
    from app.core.config import settings
    import httpx

    ctrl = _get_controls()
    reasons = []
    allowed = True

    # 1. Master switch
    if not ctrl.get("masterSwitch", True):
        allowed = False
        reasons.append("Master switch is OFF")

    # 2. Pause all
    if ctrl.get("pauseAll", False):
        allowed = False
        reasons.append("Trading is paused")

    # 3. Regime guard
    regime = ctrl.get("regimeOverride", "NEUTRAL")
    params = REGIME_PARAMS.get(regime, REGIME_PARAMS["NEUTRAL"])
    if regime == "CRISIS":
        reasons.append(f"CRISIS regime: only slam dunks allowed")

    # 4. Kelly enabled check
    kelly_enabled = ctrl.get("kellyEnabled", True)

    # 5. Risk score gate (call internal risk endpoint)
    try:
        from app.api.v1.risk import risk_score as _risk_score_fn
        risk_data = await _risk_score_fn()
        score = risk_data.get("risk_score", 100)
        if score < getattr(settings, 'MIN_RISK_SCORE', 40):
            allowed = False
            reasons.append(f"Risk score {score} < minimum {settings.MIN_RISK_SCORE}")
    except Exception as e:
        reasons.append(f"Risk score unavailable: {e}")

    # 6. Drawdown check
    try:
        from app.api.v1.risk import drawdown_check_status as _dd_check
        dd_data = await _dd_check()
        if not dd_data.get("trading_allowed", True):
            allowed = False
            reasons.append(f"Drawdown breached: {dd_data.get('daily_pnl_pct', 0):.2f}%")
    except Exception as e:
        reasons.append(f"Drawdown check unavailable: {e}")

    return {
        "allowed": allowed,
        "symbol": symbol,
        "side": side,
        "regime": regime,
        "regime_params": params,
        "kelly_enabled": kelly_enabled,
        "reasons": reasons,
        "recommendation": "PROCEED" if allowed else "BLOCK",
    }


# ── Adaptive Strategy Selection ──────────────────────────────────
# Strategy configs keyed by regime - determines which approach maximizes profit
STRATEGY_BY_REGIME = {
    "BULLISH": {
        "strategy": "momentum_breakout",
        "description": "Ride strong trends with breakout entries",
        "kelly_mult": 1.0,
        "max_positions": 8,
        "stop_type": "trailing",
        "stop_pct": 0.05,
        "min_score": 65,
        "prefer_sectors": ["Technology", "Consumer Cyclical"],
    },
    "RISK_ON": {
        "strategy": "momentum_pullback",
        "description": "Buy pullbacks in uptrending stocks",
        "kelly_mult": 0.9,
        "max_positions": 6,
        "stop_type": "trailing",
        "stop_pct": 0.04,
        "min_score": 70,
        "prefer_sectors": ["Technology", "Healthcare"],
    },
    "NEUTRAL": {
        "strategy": "mean_reversion",
        "description": "Fade extremes, buy oversold, sell overbought",
        "kelly_mult": 0.7,
        "max_positions": 4,
        "stop_type": "fixed",
        "stop_pct": 0.03,
        "min_score": 75,
        "prefer_sectors": ["Utilities", "Consumer Defensive"],
    },
    "RISK_OFF": {
        "strategy": "defensive_yield",
        "description": "Defensive positions, dividends, low-beta",
        "kelly_mult": 0.5,
        "max_positions": 3,
        "stop_type": "fixed",
        "stop_pct": 0.02,
        "min_score": 80,
        "prefer_sectors": ["Utilities", "Consumer Defensive", "Healthcare"],
    },
    "BEARISH": {
        "strategy": "cash_preservation",
        "description": "Minimal exposure, only A+ setups",
        "kelly_mult": 0.3,
        "max_positions": 2,
        "stop_type": "tight",
        "stop_pct": 0.015,
        "min_score": 85,
        "prefer_sectors": ["Consumer Defensive"],
    },
    "CRISIS": {
        "strategy": "full_cash",
        "description": "No new positions, protect capital",
        "kelly_mult": 0.0,
        "max_positions": 0,
        "stop_type": "none",
        "stop_pct": 0.0,
        "min_score": 100,
        "prefer_sectors": [],
    },
}


@router.get("/adaptive-strategy")
async def get_adaptive_strategy():
    """Return the current recommended strategy based on market regime."""
    ctrl = _get_controls()
    regime = ctrl.get("regimeOverride", "NEUTRAL")
    strategy = STRATEGY_BY_REGIME.get(regime, STRATEGY_BY_REGIME["NEUTRAL"])
    return {
        "regime": regime,
        **strategy,
        "portfolio_heat_limit": strategy["max_positions"] * 0.05,
        "suggested_scan_interval": "15m" if regime in ("BULLISH", "RISK_ON") else "1h",
    }


@router.get("/strategy-matrix")
async def get_strategy_matrix():
    """Return all regime-strategy mappings for dashboard display."""
    return {
        "strategies": STRATEGY_BY_REGIME,
        "current_regime": _get_controls().get("regimeOverride", "NEUTRAL"),
    }
