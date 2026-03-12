"""ExecutionDecision — single required object for any broker/API order submission.

No path may call Alpaca (or publish order.submitted for live) without an
ExecutionDecision that has passed all hard gates: council approved, sizing ok,
risk checks passed, instrument/mode allowed, feature flags permit.
"""
from dataclasses import dataclass, field
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
    # Trade execution router pre-trade checks
    DECISION_ID_MISSING = "decision_id_missing"
    DECISION_EXPIRED = "decision_expired"
    VETOED = "vetoed"
    MARKET_CLOSED = "market_closed"
    BROKER_ERROR = "broker_error"


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
    # Optional for tracing and learning-loop matching (outcome → council decision)
    trace_id: Optional[str] = None
    event_id: Optional[str] = None
    council_decision_id: str = ""

    def to_order_payload(self, order_id: str = "", client_order_id: str = "") -> Dict[str, Any]:
        """Build the order.submitted event payload from this decision."""
        payload = {
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
        if self.council_decision_id:
            payload["council_decision_id"] = self.council_decision_id
        return payload


@dataclass
class ValidationResult:
    """Result of pre-trade validation (router). Fail-closed: any failure means no submit."""

    valid: bool
    error_code: Optional[str] = None  # ExecutionDenyReason.value
    error_message: Optional[str] = None


@dataclass
class ExecutionResult:
    """Structured result of an execution attempt (submit or reject). For audit and idempotency."""

    council_decision_id: str
    success: bool
    order_id: str = ""
    client_order_id: str = ""
    symbol: str = ""
    side: str = ""
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    mode: str = "paper"  # paper | live
    requested_at: float = 0.0
    resolved_at: float = 0.0
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "council_decision_id": self.council_decision_id,
            "success": self.success,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "mode": self.mode,
            "requested_at": self.requested_at,
            "resolved_at": self.resolved_at,
        }
        if self.error_code:
            d["error_code"] = self.error_code
        if self.error_message:
            d["error_message"] = self.error_message
        if self.payload:
            d["payload"] = self.payload
        return d
