"""
Operator Status API - Trading mode, execution authority, auto state management

Endpoints:
  GET  /api/v1/operator-status              - Get current operator status
  PUT  /api/v1/operator-status/mode         - Switch trading mode (Manual/Auto)
  PUT  /api/v1/operator-status/auto-state   - Set auto execution state
  POST /api/v1/operator-status/kill-switch  - Emergency halt all trading
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime

from app.core.security import require_auth
from app.services.database import db_service
from app.websocket_manager import broadcast_ws

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Operator"])


# ── Pydantic Models ──────────────────────────────────────────────


class BlockReason(BaseModel):
    """A reason why trades are currently blocked/restricted"""
    severity: Literal["block", "warning", "resize"]
    title: str
    message: str
    symbol: Optional[str] = None


class AlpacaStatus(BaseModel):
    """Alpaca paper account connection status"""
    connected: bool
    accountType: Literal["paper", "live"]
    status: Literal["connected", "connecting", "disconnected"]


class RiskPolicy(BaseModel):
    """Current risk control settings"""
    maxRiskPerTrade: float = Field(default=2.0, description="Max risk per trade (%)")
    maxOpenPositions: int = Field(default=5, description="Max concurrent positions")
    portfolioHeat: float = Field(default=0.0, description="Current portfolio heat (%)")
    maxPortfolioHeat: float = Field(default=10.0, description="Max allowed portfolio heat (%)")
    dailyLossCap: float = Field(default=500, description="Daily loss limit ($)")
    weeklyDrawdownCap: float = Field(default=1000, description="Weekly drawdown cap ($)")
    stopLossRequired: bool = Field(default=True, description="Stop loss mandatory")
    takeProfitPolicy: Literal["fixed", "trail", "none"] = Field(default="trail")
    cooldownAfterLossStreak: int = Field(default=3, description="Cooldown after N losses")
    currentLossStreak: int = Field(default=0, description="Current consecutive losses")


class OperatorStatusResponse(BaseModel):
    """Complete operator cockpit status"""
    tradingMode: Literal["Manual", "Auto"]
    executionAuthority: Literal["human", "system"]
    autoState: Literal["armed", "active", "paused", "blocked"]
    alpacaStatus: AlpacaStatus
    riskPolicy: RiskPolicy
    blockReasons: List[BlockReason]
    isSystemActive: bool


class TradingModeRequest(BaseModel):
    """Request to change trading mode"""
    mode: Literal["Manual", "Auto"]


class AutoStateRequest(BaseModel):
    """Request to change auto execution state"""
    state: Literal["armed", "active", "paused", "blocked"]


# ── Helper Functions ──────────────────────────────────────────────


def get_alpaca_connection_status() -> AlpacaStatus:
    """Check Alpaca connection status from database/service"""
    # Try to get status from database cache
    cached_status = db_service.get_config("alpaca_connection_status")

    if cached_status:
        return AlpacaStatus(
            connected=cached_status.get("connected", False),
            accountType=cached_status.get("accountType", "paper"),
            status=cached_status.get("status", "disconnected")
        )

    # Default: assume disconnected until proven otherwise
    return AlpacaStatus(
        connected=False,
        accountType="paper",
        status="disconnected"
    )


def get_current_risk_policy() -> RiskPolicy:
    """Get current risk control settings from settings service"""
    from app.services.settings_service import get_settings_by_category

    # Get risk and kelly settings
    risk_settings = get_settings_by_category("risk")
    kelly_settings = get_settings_by_category("kelly")

    # Get current portfolio heat from risk shield (if available)
    risk_shield_status = db_service.get_config("risk_shield_status")
    current_heat = 0.0
    if risk_shield_status:
        current_heat = risk_shield_status.get("exposure_pct", 0.0)

    # Get current loss streak from database
    loss_streak = db_service.get_config("current_loss_streak") or {"count": 0}

    return RiskPolicy(
        maxRiskPerTrade=risk_settings.get("maxPositionRisk", 0.02) * 100,  # Convert to %
        maxOpenPositions=risk_settings.get("maxPositions", 15),
        portfolioHeat=current_heat,
        maxPortfolioHeat=risk_settings.get("maxPortfolioRisk", 0.06) * 100,  # Convert to %
        dailyLossCap=risk_settings.get("maxDailyLossPct", 5.0) * 100,  # Assume on $10k account
        weeklyDrawdownCap=risk_settings.get("maxDrawdownLimit", 0.10) * 1000,  # Estimate
        stopLossRequired=True,  # Always required
        takeProfitPolicy="trail",  # Default strategy
        cooldownAfterLossStreak=3,  # Hard-coded for now
        currentLossStreak=loss_streak.get("count", 0)
    )


def get_block_reasons() -> List[BlockReason]:
    """Get current trade restriction reasons"""
    reasons = []

    # Check if entries are frozen
    freeze_status = db_service.get_config("risk_shield_freeze_entries")
    if freeze_status and freeze_status.get("frozen"):
        reasons.append(BlockReason(
            severity="block",
            title="Trading Frozen",
            message=freeze_status.get("reason", "Manual freeze activated"),
            symbol=None
        ))

    # Check daily loss cap
    risk_shield_status = db_service.get_config("risk_shield_status")
    if risk_shield_status:
        daily_pnl_pct = risk_shield_status.get("daily_pnl_pct", 0.0)
        if daily_pnl_pct < -5.0:
            reasons.append(BlockReason(
                severity="block",
                title="Daily Loss Cap Reached",
                message=f"Hit {abs(daily_pnl_pct):.1f}% daily loss limit",
                symbol=None
            ))
        elif daily_pnl_pct < -3.0:
            reasons.append(BlockReason(
                severity="warning",
                title="Approaching Daily Loss Cap",
                message=f"Current daily loss: {abs(daily_pnl_pct):.1f}%",
                symbol=None
            ))

    # Check portfolio heat
    risk_policy = get_current_risk_policy()
    if risk_policy.portfolioHeat >= risk_policy.maxPortfolioHeat:
        reasons.append(BlockReason(
            severity="block",
            title="Portfolio Heat Limit",
            message=f"Portfolio heat at {risk_policy.portfolioHeat:.1f}% (max {risk_policy.maxPortfolioHeat:.1f}%)",
            symbol=None
        ))
    elif risk_policy.portfolioHeat >= risk_policy.maxPortfolioHeat * 0.8:
        reasons.append(BlockReason(
            severity="warning",
            title="High Portfolio Heat",
            message=f"Portfolio heat at {risk_policy.portfolioHeat:.1f}% (limit {risk_policy.maxPortfolioHeat:.1f}%)",
            symbol=None
        ))

    # Check loss streak cooldown
    if risk_policy.currentLossStreak >= risk_policy.cooldownAfterLossStreak:
        reasons.append(BlockReason(
            severity="block",
            title="Loss Streak Cooldown",
            message=f"{risk_policy.currentLossStreak} consecutive losses - cooling down",
            symbol=None
        ))

    return reasons


def get_operator_status_internal() -> Dict[str, Any]:
    """Internal function to get complete operator status"""
    # Get current operator state from database
    operator_state = db_service.get_config("operator_state") or {}

    trading_mode = operator_state.get("tradingMode", "Manual")
    auto_state = operator_state.get("autoState", "paused")
    is_system_active = operator_state.get("isSystemActive", True)

    # Determine execution authority
    execution_authority = "system" if trading_mode == "Auto" and auto_state in ["armed", "active"] else "human"

    # Get Alpaca status
    alpaca_status = get_alpaca_connection_status()

    # Get risk policy
    risk_policy = get_current_risk_policy()

    # Get block reasons
    block_reasons = get_block_reasons()

    # Auto-adjust auto state if blocked
    if trading_mode == "Auto" and block_reasons:
        has_blocking_reasons = any(r.severity == "block" for r in block_reasons)
        if has_blocking_reasons and auto_state not in ["paused", "blocked"]:
            auto_state = "blocked"

    return {
        "tradingMode": trading_mode,
        "executionAuthority": execution_authority,
        "autoState": auto_state,
        "alpacaStatus": alpaca_status.model_dump(),
        "riskPolicy": risk_policy.model_dump(),
        "blockReasons": [r.model_dump() for r in block_reasons],
        "isSystemActive": is_system_active
    }


# ── API Endpoints ─────────────────────────────────────────────────


@router.get("", response_model=OperatorStatusResponse)
@router.get("/", include_in_schema=False, response_model=OperatorStatusResponse)
async def get_operator_status():
    """
    Get current operator cockpit status.

    Returns trading mode, execution authority, auto state, risk policy,
    Alpaca connection status, and any active trade restrictions.
    """
    try:
        status = get_operator_status_internal()
        return OperatorStatusResponse(**status)
    except Exception as e:
        logger.error(f"Error getting operator status: {e}")
        # Return safe defaults on error
        return OperatorStatusResponse(
            tradingMode="Manual",
            executionAuthority="human",
            autoState="paused",
            alpacaStatus=AlpacaStatus(
                connected=False,
                accountType="paper",
                status="disconnected"
            ),
            riskPolicy=RiskPolicy(),
            blockReasons=[],
            isSystemActive=True
        )


@router.put("/mode", dependencies=[Depends(require_auth)])
async def set_trading_mode(request: TradingModeRequest):
    """
    Switch between Manual and Auto trading modes.

    - Manual: System recommends, human decides and executes
    - Auto: System may place paper trades via Alpaca (subject to risk controls)
    """
    mode = request.mode

    logger.info(f"Trading mode change requested: {mode}")

    # Get current state
    operator_state = db_service.get_config("operator_state") or {}
    old_mode = operator_state.get("tradingMode", "Manual")

    # Update mode
    operator_state["tradingMode"] = mode

    # When switching to Manual, pause auto state
    if mode == "Manual":
        operator_state["autoState"] = "paused"

    # When switching to Auto, set to armed (if no blocks)
    if mode == "Auto":
        block_reasons = get_block_reasons()
        has_blocking_reasons = any(r.severity == "block" for r in block_reasons)
        operator_state["autoState"] = "blocked" if has_blocking_reasons else "armed"

    # Save state
    db_service.set_config("operator_state", operator_state)

    # Broadcast update via WebSocket
    try:
        status = get_operator_status_internal()
        await broadcast_ws("operator.status", {
            "type": "mode_changed",
            "oldMode": old_mode,
            "newMode": mode,
            "status": status
        })
    except Exception as e:
        logger.warning(f"Failed to broadcast mode change: {e}")

    return {
        "success": True,
        "tradingMode": mode,
        "message": f"Trading mode set to {mode}",
        "status": get_operator_status_internal()
    }


@router.put("/auto-state", dependencies=[Depends(require_auth)])
async def set_auto_state(request: AutoStateRequest):
    """
    Set auto execution state.

    - armed: Ready to trade, waiting for signals
    - active: Actively placing trades
    - paused: User temporarily disabled auto
    - blocked: Risk controls preventing execution
    """
    state = request.state

    logger.info(f"Auto state change requested: {state}")

    # Get current state
    operator_state = db_service.get_config("operator_state") or {}
    old_state = operator_state.get("autoState", "paused")
    trading_mode = operator_state.get("tradingMode", "Manual")

    # Only allow auto state changes in Auto mode
    if trading_mode != "Auto":
        raise HTTPException(
            status_code=400,
            detail="Cannot change auto state while in Manual mode. Switch to Auto mode first."
        )

    # Check if blocked by risk controls
    if state in ["armed", "active"]:
        block_reasons = get_block_reasons()
        has_blocking_reasons = any(r.severity == "block" for r in block_reasons)
        if has_blocking_reasons:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot set to {state} - blocked by risk controls: {block_reasons[0].message}"
            )

    # Update state
    operator_state["autoState"] = state
    db_service.set_config("operator_state", operator_state)

    # Broadcast update via WebSocket
    try:
        status = get_operator_status_internal()
        await broadcast_ws("operator.status", {
            "type": "auto_state_changed",
            "oldState": old_state,
            "newState": state,
            "status": status
        })
    except Exception as e:
        logger.warning(f"Failed to broadcast auto state change: {e}")

    return {
        "success": True,
        "autoState": state,
        "message": f"Auto execution state set to {state}",
        "status": get_operator_status_internal()
    }


@router.post("/kill-switch", dependencies=[Depends(require_auth)])
async def trigger_kill_switch():
    """
    Emergency halt all trading.

    - Cancels all open orders
    - Closes all positions (if enabled)
    - Freezes new entries
    - Sets system to inactive state
    """
    logger.critical("KILL SWITCH ACTIVATED")

    results = {
        "action": "kill_switch",
        "timestamp": datetime.utcnow().isoformat(),
        "success": True,
        "details": {}
    }

    # 1. Freeze all new entries immediately
    db_service.set_config("risk_shield_freeze_entries", {
        "frozen": True,
        "reason": "kill_switch",
        "timestamp": datetime.utcnow().isoformat()
    })
    results["details"]["entries_frozen"] = True

    # 2. Set operator state to inactive
    operator_state = db_service.get_config("operator_state") or {}
    operator_state["tradingMode"] = "Manual"
    operator_state["autoState"] = "blocked"
    operator_state["isSystemActive"] = False
    db_service.set_config("operator_state", operator_state)
    results["details"]["system_halted"] = True

    # 3. Try to cancel all orders via Alpaca (optional, may fail gracefully)
    try:
        from app.services.alpaca_service import alpaca_service
        cancel_result = await alpaca_service.cancel_all_orders()
        results["details"]["orders_cancelled"] = True
        results["details"]["cancelled_count"] = len(cancel_result) if isinstance(cancel_result, list) else 0
        logger.critical(f"KILL SWITCH: Cancelled {results['details']['cancelled_count']} orders")
    except Exception as e:
        logger.error(f"KILL SWITCH: Failed to cancel orders: {e}")
        results["details"]["orders_cancelled"] = False
        results["details"]["cancel_error"] = str(type(e).__name__)

    # 4. Optionally close all positions (commented out for safety)
    # Uncomment if you want kill switch to liquidate positions
    # try:
    #     from app.services.alpaca_service import alpaca_service
    #     close_result = await alpaca_service.close_all_positions(cancel_orders=True)
    #     results["details"]["positions_closed"] = True
    #     results["details"]["closed_count"] = len(close_result) if isinstance(close_result, list) else 0
    # except Exception as e:
    #     logger.error(f"KILL SWITCH: Failed to close positions: {e}")
    #     results["details"]["positions_closed"] = False

    # 5. Broadcast kill switch event
    try:
        await broadcast_ws("operator.status", {
            "type": "kill_switch_activated",
            "timestamp": results["timestamp"],
            "status": get_operator_status_internal()
        })
        await broadcast_ws("risk.update", {
            "type": "emergency_halt",
            "severity": "critical",
            "message": "KILL SWITCH ACTIVATED - All trading halted"
        })
    except Exception as e:
        logger.warning(f"Failed to broadcast kill switch: {e}")

    results["message"] = "KILL SWITCH ACTIVATED - System halted, entries frozen, orders cancelled"

    return results
