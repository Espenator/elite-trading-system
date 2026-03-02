# backend/app/core/alignment/bright_lines.py
"""
Pattern 2: Bright-Line Enforcer

Hard-coded, non-negotiable trading limits that NO model output,
confidence score, or optimization process can override.

These are constitutional constraints -- not parameters.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.alignment.types import (
    EnforcementDecision,
    Severity,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants: These are CONSTITUTIONAL -- not tunable parameters
# ---------------------------------------------------------------------------
MAX_POSITION_SIZE_PCT = 0.10       # 10% of portfolio per position
MAX_PORTFOLIO_HEAT_PCT = 0.25      # 25% total risk exposure
DRAWDOWN_CIRCUIT_BREAKER_PCT = 0.15  # 15% drawdown halts all new entries
CRISIS_HALT_DRAWDOWN_PCT = 0.25    # 25% drawdown halts ALL trading
MAX_CORRELATED_EXPOSURE_PCT = 0.30 # 30% in correlated assets
MIN_TRADE_INTERVAL_SECONDS = 60    # No rapid-fire trading
MAX_DAILY_TRADES = 20              # Daily trade cap
MAX_LEVERAGE = 2.0                 # Maximum leverage allowed


class ViolationType(str, Enum):
    POSITION_SIZE = "position_size"
    PORTFOLIO_HEAT = "portfolio_heat"
    DRAWDOWN_CIRCUIT = "drawdown_circuit"
    CRISIS_HALT = "crisis_halt"
    CORRELATED_EXPOSURE = "correlated_exposure"
    RAPID_FIRE = "rapid_fire"
    DAILY_TRADE_CAP = "daily_trade_cap"
    LEVERAGE = "leverage"


@dataclass
class Violation:
    """Record of a bright-line violation."""
    violation_type: ViolationType
    limit: float
    actual: float
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BrightLineReport:
    """Result of bright-line enforcement check."""
    passed: bool
    violations: List[Violation] = field(default_factory=list)
    decision: Optional[EnforcementDecision] = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def flags(self) -> List[str]:
        return [v.violation_type.value for v in self.violations]


class BrightLineEnforcer:
    """
    Constitutional enforcement layer.

    These limits are HARD-CODED. They exist to protect capital
    from model errors, bugs, and adversarial optimization.

    If you find yourself wanting to make these configurable,
    you are optimizing against the guardrails -- stop.
    """

    def __init__(self) -> None:
        self._violation_log: List[Violation] = []
        self._daily_trade_count: int = 0
        self._last_trade_time: Optional[datetime] = None
        self._day_marker: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enforce(
        self,
        proposed_position_pct: float,
        current_heat_pct: float,
        current_drawdown_pct: float,
        correlated_exposure_pct: float = 0.0,
        leverage: float = 1.0,
    ) -> BrightLineReport:
        """Run all bright-line checks against a proposed trade.

        Returns a BrightLineReport. If passed=False the trade MUST be blocked.
        There is no override mechanism by design.
        """
        violations: List[Violation] = []

        # 1. Position size
        if proposed_position_pct > MAX_POSITION_SIZE_PCT:
            violations.append(Violation(
                violation_type=ViolationType.POSITION_SIZE,
                limit=MAX_POSITION_SIZE_PCT,
                actual=proposed_position_pct,
                message=f"Position {proposed_position_pct:.1%} exceeds {MAX_POSITION_SIZE_PCT:.0%} limit",
            ))

        # 2. Portfolio heat
        if current_heat_pct > MAX_PORTFOLIO_HEAT_PCT:
            violations.append(Violation(
                violation_type=ViolationType.PORTFOLIO_HEAT,
                limit=MAX_PORTFOLIO_HEAT_PCT,
                actual=current_heat_pct,
                message=f"Portfolio heat {current_heat_pct:.1%} exceeds {MAX_PORTFOLIO_HEAT_PCT:.0%} limit",
            ))

        # 3. Drawdown circuit breaker
        if current_drawdown_pct >= DRAWDOWN_CIRCUIT_BREAKER_PCT:
            violations.append(Violation(
                violation_type=ViolationType.DRAWDOWN_CIRCUIT,
                limit=DRAWDOWN_CIRCUIT_BREAKER_PCT,
                actual=current_drawdown_pct,
                message=f"Drawdown {current_drawdown_pct:.1%} triggered circuit breaker",
            ))

        # 4. Crisis halt
        if current_drawdown_pct >= CRISIS_HALT_DRAWDOWN_PCT:
            violations.append(Violation(
                violation_type=ViolationType.CRISIS_HALT,
                limit=CRISIS_HALT_DRAWDOWN_PCT,
                actual=current_drawdown_pct,
                message=f"CRISIS: Drawdown {current_drawdown_pct:.1%} -- ALL trading halted",
            ))

        # 5. Correlated exposure
        if correlated_exposure_pct > MAX_CORRELATED_EXPOSURE_PCT:
            violations.append(Violation(
                violation_type=ViolationType.CORRELATED_EXPOSURE,
                limit=MAX_CORRELATED_EXPOSURE_PCT,
                actual=correlated_exposure_pct,
                message=f"Correlated exposure {correlated_exposure_pct:.1%} exceeds limit",
            ))

        # 6. Leverage
        if leverage > MAX_LEVERAGE:
            violations.append(Violation(
                violation_type=ViolationType.LEVERAGE,
                limit=MAX_LEVERAGE,
                actual=leverage,
                message=f"Leverage {leverage:.1f}x exceeds {MAX_LEVERAGE:.1f}x max",
            ))

        # 7. Rapid-fire check
        rapid_fire = self._check_rapid_fire()
        if rapid_fire:
            violations.append(rapid_fire)

        # 8. Daily trade cap
        daily_cap = self._check_daily_cap()
        if daily_cap:
            violations.append(daily_cap)

        # Build decision
        passed = len(violations) == 0
        severity = Severity.CRITICAL if any(
            v.violation_type in (ViolationType.CRISIS_HALT, ViolationType.DRAWDOWN_CIRCUIT)
            for v in violations
        ) else Severity.HIGH if violations else Severity.LOW

        decision = EnforcementDecision(
            severity=severity,
            flags=[v.violation_type.value for v in violations],
            action="BLOCK" if not passed else "PROCEED",
            recommendation=self._build_recommendation(violations) if violations else "All bright-line checks passed.",
        )

        if not passed:
            self._violation_log.extend(violations)
            for v in violations:
                logger.warning("BRIGHT_LINE_VIOLATION: %s", v.message)

        return BrightLineReport(
            passed=passed,
            violations=violations,
            decision=decision,
        )

    def record_trade(self) -> None:
        """Call after a trade is executed to update rate-limit counters."""
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        if self._day_marker != today:
            self._day_marker = today
            self._daily_trade_count = 0
        self._daily_trade_count += 1
        self._last_trade_time = now

    def get_violation_history(self) -> List[Dict[str, Any]]:
        """Return violation log for diagnostics."""
        return [
            {
                "type": v.violation_type.value,
                "limit": v.limit,
                "actual": v.actual,
                "message": v.message,
                "timestamp": v.timestamp.isoformat(),
            }
            for v in self._violation_log
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_rapid_fire(self) -> Optional[Violation]:
        if self._last_trade_time is None:
            return None
        elapsed = (datetime.now(timezone.utc) - self._last_trade_time).total_seconds()
        if elapsed < MIN_TRADE_INTERVAL_SECONDS:
            return Violation(
                violation_type=ViolationType.RAPID_FIRE,
                limit=MIN_TRADE_INTERVAL_SECONDS,
                actual=elapsed,
                message=f"Only {elapsed:.0f}s since last trade (min {MIN_TRADE_INTERVAL_SECONDS}s)",
            )
        return None

    def _check_daily_cap(self) -> Optional[Violation]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._day_marker != today:
            return None
        if self._daily_trade_count >= MAX_DAILY_TRADES:
            return Violation(
                violation_type=ViolationType.DAILY_TRADE_CAP,
                limit=MAX_DAILY_TRADES,
                actual=self._daily_trade_count,
                message=f"Daily trade cap reached: {self._daily_trade_count}/{MAX_DAILY_TRADES}",
            )
        return None

    @staticmethod
    def _build_recommendation(violations: List[Violation]) -> str:
        parts = ["BLOCKED: "]
        for v in violations:
            parts.append(f"  - {v.message}")
        return "\n".join(parts)
