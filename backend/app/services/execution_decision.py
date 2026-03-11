"""ExecutionDecision — single required object for any broker/API order submission.

No path may call Alpaca (or publish order.submitted for live) without an
ExecutionDecision that has passed all hard gates: council approved, sizing ok,
risk checks passed, instrument/mode allowed, feature flags permit.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ExecutionDenyReason(str, Enum):
    """Explicit reasons for execution gate denial (observable, testable)."""
    COUNCIL_HOLD = "council_hold"
    COUNCIL_NOT_READY = "council_not_ready"
    MOCK_SOURCE = "mock_source"
    DAILY_LIMIT = "daily_limit"
    COOLDOWN = "cooldown"
    DRAWDOWN = "drawdown"
    DEGRADED = "degraded"
    SIZING_HOLD = "sizing_hold"
    SIZING_REJECTED = "sizing_rejected"
    PORTFOLIO_HEAT = "portfolio_heat"
    QTY_INVALID = "qty_invalid"
    EQUITY_UNAVAILABLE = "equity_unavailable"
    MISSING_SYMBOL_PRICE = "missing_symbol_price"
    FLAG_DISABLED = "flag_disabled"
    VIABILITY_DENIED = "viability_denied"  # slippage/liquidity > edge threshold
    KILL_SWITCH_ACTIVE = "kill_switch_active"
    PORTFOLIO_RISK_LIMIT = "portfolio_risk_limit"
    REGIME_BLOCKED = "regime_blocked"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class ExecutionDecision:
    """Approved decision to execute one order. Required by order_executor for any submit.

    All gates have passed: council verdict approved, sizing within limits,
    risk checks passed and timestamp-fresh, instrument/mode allowed, flags permit.
    """
    symbol: str
    side: str  # buy | sell
    qty: int
    price: float
    direction: str  # buy | sell | hold
    execution_ready: bool
    signal_score: float
    council_confidence: float
    regime: str
    kelly_pct: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    sizing_metadata: Dict[str, Any]
    risk_checks_passed: bool
    verdict_timestamp: float
    # Optional for tracing
    trace_id: Optional[str] = None
    event_id: Optional[str] = None

    def to_order_payload(self, order_id: str = "", client_order_id: str = "") -> Dict[str, Any]:
        """Build the order.submitted event payload from this decision."""
        return {
            "order_id": order_id,
            "client_order_id": client_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "price": self.price,
            "signal_score": self.signal_score,
            "council_confidence": self.council_confidence,
            "kelly_pct": self.kelly_pct,
            "regime": self.regime,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "sizing_metadata": self.sizing_metadata,
            "sizing_gate_passed": True,
        }
