"""Human-in-the-Loop (HITL) Escalation Gates.

Configurable gates that STOP the system and require human approval before
executing certain trades. This builds trust during the learning period and
prevents catastrophic autonomous decisions.

Gates (all configurable):
    1. Trade size gate: "Ask me before any trade > $X"
    2. Confidence gate: "Ask me if confidence < Y%"
    3. Learning period gate: "Always ask me during first N days of live trading"
    4. Novel regime gate: "Ask me when entering a regime the system hasn't seen"
    5. Drawdown gate: "Ask me after N consecutive losses"
    6. Concentration gate: "Ask me if >Z% of portfolio in one sector"

When a gate fires, the trade is held in a PENDING_APPROVAL state and
published to WebSocket/notification for human review.

Usage:
    from app.council.hitl_gate import get_hitl_gate
    gate = get_hitl_gate()
    result = gate.check(decision_packet, portfolio_context)
    if result.requires_approval:
        await gate.request_approval(result)
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HITLConfig:
    """Configurable HITL gate thresholds."""
    enabled: bool = True

    # Gate 1: Trade size
    max_trade_value_usd: float = 5000.0  # Ask before trades > $5000

    # Gate 2: Confidence
    min_confidence_for_auto: float = 0.60  # Ask if confidence < 60%

    # Gate 3: Learning period
    learning_period_days: int = 30  # Always ask during first 30 days
    learning_start_timestamp: float = 0.0  # Set when live trading begins

    # Gate 4: Novel regime
    known_regimes: List[str] = field(default_factory=lambda: [
        "bullish", "bearish", "sideways", "volatile",
    ])

    # Gate 5: Drawdown / losing streak
    max_consecutive_losses: int = 5  # Ask after 5 consecutive losses

    # Gate 6: Concentration
    max_sector_concentration: float = 0.40  # Ask if >40% in one sector


@dataclass
class GateResult:
    """Result of HITL gate check."""
    requires_approval: bool = False
    gates_triggered: List[str] = field(default_factory=list)
    gate_details: Dict[str, Any] = field(default_factory=dict)
    decision_id: str = ""
    symbol: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requires_approval": self.requires_approval,
            "gates_triggered": self.gates_triggered,
            "gate_details": self.gate_details,
            "decision_id": self.decision_id,
            "symbol": self.symbol,
        }


MAX_PENDING_APPROVALS = 100
MAX_APPROVAL_HISTORY = 500


class HITLGate:
    """Human-in-the-loop gate system."""

    def __init__(self, config: HITLConfig = None):
        self.config = config or HITLConfig()
        self._pending_approvals: Dict[str, GateResult] = {}
        self._consecutive_losses = 0
        self._approval_history: List[Dict[str, Any]] = []

    def check(
        self,
        decision: Dict[str, Any],
        portfolio_context: Dict[str, Any] = None,
    ) -> GateResult:
        """Check all HITL gates for a council decision.

        Args:
            decision: DecisionPacket dict with symbol, direction, confidence, etc.
            portfolio_context: Optional portfolio state (positions, sector allocation, etc.)

        Returns:
            GateResult indicating whether human approval is needed
        """
        if not self.config.enabled:
            return GateResult()

        decision_id = decision.get("council_decision_id", "")
        if not decision_id:
            import uuid
            decision_id = f"hitl_{uuid.uuid4().hex[:12]}"
        result = GateResult(
            decision_id=decision_id,
            symbol=decision.get("symbol", ""),
        )

        # Skip gate checks for hold decisions
        if decision.get("final_direction") == "hold":
            return result

        # Gate 1: Trade size
        trade_value = self._estimate_trade_value(decision, portfolio_context)
        if trade_value > self.config.max_trade_value_usd:
            result.requires_approval = True
            result.gates_triggered.append("trade_size")
            result.gate_details["trade_size"] = {
                "estimated_value": trade_value,
                "threshold": self.config.max_trade_value_usd,
            }

        # Gate 2: Low confidence
        confidence = decision.get("final_confidence", 0)
        if confidence < self.config.min_confidence_for_auto:
            result.requires_approval = True
            result.gates_triggered.append("low_confidence")
            result.gate_details["low_confidence"] = {
                "confidence": confidence,
                "threshold": self.config.min_confidence_for_auto,
            }

        # Gate 3: Learning period
        if self.config.learning_start_timestamp > 0:
            days_live = (time.time() - self.config.learning_start_timestamp) / 86400
            if days_live < self.config.learning_period_days:
                result.requires_approval = True
                result.gates_triggered.append("learning_period")
                result.gate_details["learning_period"] = {
                    "days_live": round(days_live, 1),
                    "required_days": self.config.learning_period_days,
                }

        # Gate 4: Novel regime
        regime = decision.get("metadata", {}).get("regime", "unknown")
        if regime and regime.lower() not in [r.lower() for r in self.config.known_regimes]:
            result.requires_approval = True
            result.gates_triggered.append("novel_regime")
            result.gate_details["novel_regime"] = {
                "regime": regime,
                "known_regimes": self.config.known_regimes,
            }

        # Gate 5: Consecutive losses
        if self._consecutive_losses >= self.config.max_consecutive_losses:
            result.requires_approval = True
            result.gates_triggered.append("losing_streak")
            result.gate_details["losing_streak"] = {
                "consecutive_losses": self._consecutive_losses,
                "threshold": self.config.max_consecutive_losses,
            }

        # Gate 6: Sector concentration
        if portfolio_context:
            sector_alloc = portfolio_context.get("sector_allocation", {})
            for sector, pct in sector_alloc.items():
                if pct > self.config.max_sector_concentration:
                    result.requires_approval = True
                    result.gates_triggered.append("sector_concentration")
                    result.gate_details["sector_concentration"] = {
                        "sector": sector,
                        "allocation": pct,
                        "threshold": self.config.max_sector_concentration,
                    }
                    break

        if result.requires_approval:
            # Cap pending approvals to prevent unbounded memory
            if len(self._pending_approvals) >= MAX_PENDING_APPROVALS:
                oldest_key = next(iter(self._pending_approvals))
                self._pending_approvals.pop(oldest_key, None)
            self._pending_approvals[result.decision_id] = result
            logger.info(
                "HITL gate triggered for %s: %s",
                result.symbol, ", ".join(result.gates_triggered),
            )

        return result

    def record_outcome(self, is_win: bool):
        """Record a trade outcome for the losing streak gate."""
        if is_win:
            self._consecutive_losses = 0
        else:
            self._consecutive_losses += 1

    def approve(self, decision_id: str, approver: str = "human") -> bool:
        """Approve a pending decision."""
        if decision_id in self._pending_approvals:
            result = self._pending_approvals.pop(decision_id)
            self._approval_history.append({
                "decision_id": decision_id,
                "symbol": result.symbol,
                "action": "approved",
                "approver": approver,
                "gates": result.gates_triggered,
                "timestamp": time.time(),
            })
            # Cap history to prevent unbounded growth
            self._approval_history = self._approval_history[-MAX_APPROVAL_HISTORY:]
            logger.info("HITL: Decision %s APPROVED by %s", decision_id[:8], approver)
            return True
        return False

    def reject(self, decision_id: str, reason: str = "", rejector: str = "human") -> bool:
        """Reject a pending decision."""
        if decision_id in self._pending_approvals:
            result = self._pending_approvals.pop(decision_id)
            self._approval_history.append({
                "decision_id": decision_id,
                "symbol": result.symbol,
                "action": "rejected",
                "rejector": rejector,
                "reason": reason,
                "gates": result.gates_triggered,
                "timestamp": time.time(),
            })
            # Cap history to prevent unbounded growth
            self._approval_history = self._approval_history[-MAX_APPROVAL_HISTORY:]
            logger.info("HITL: Decision %s REJECTED by %s: %s", decision_id[:8], rejector, reason)
            return True
        return False

    def get_pending(self) -> List[Dict[str, Any]]:
        """Get all pending approval requests."""
        return [r.to_dict() for r in self._pending_approvals.values()]

    async def request_approval(self, result: GateResult):
        """Publish approval request to WebSocket/notification."""
        try:
            from app.core.message_bus import get_message_bus
            bus = get_message_bus()
            if bus._running:
                await bus.publish("hitl.approval_needed", {
                    "type": "hitl_approval_needed",
                    **result.to_dict(),
                    "timestamp": time.time(),
                })
        except Exception as e:
            logger.debug("HITL notification failed: %s", e)

    def update_config(self, updates: Dict[str, Any]):
        """Update HITL configuration."""
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        logger.info("HITL config updated: %s", updates)

    def start_learning_period(self):
        """Mark the start of live trading learning period."""
        self.config.learning_start_timestamp = time.time()
        logger.info("HITL: Learning period started (%d days)", self.config.learning_period_days)

    def _estimate_trade_value(self, decision: Dict, portfolio: Dict = None) -> float:
        """Estimate the dollar value of a proposed trade."""
        if portfolio and portfolio.get("account_value"):
            # Use position scale from homeostasis if available
            scale = decision.get("metadata", {}).get("position_scale", 1.0)
            # Default to 2% of portfolio per trade
            return portfolio["account_value"] * 0.02 * scale
        return 0.0  # Can't estimate without portfolio context

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "pending_count": len(self._pending_approvals),
            "consecutive_losses": self._consecutive_losses,
            "config": {
                "max_trade_value_usd": self.config.max_trade_value_usd,
                "min_confidence_for_auto": self.config.min_confidence_for_auto,
                "learning_period_days": self.config.learning_period_days,
                "max_consecutive_losses": self.config.max_consecutive_losses,
                "max_sector_concentration": self.config.max_sector_concentration,
            },
            "approval_history_count": len(self._approval_history),
        }


# Singleton
_gate: Optional[HITLGate] = None


def get_hitl_gate() -> HITLGate:
    global _gate
    if _gate is None:
        _gate = HITLGate()
    return _gate
