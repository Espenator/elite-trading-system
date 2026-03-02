# backend/app/core/alignment/critique.py
"""
Pattern 6: Swarm Critique Protocol

Multi-perspective review of trade proposals before execution.
Simulates adversarial review by assigning different "roles"
that challenge the trade from different angles.

No trade should pass without surviving structured critique.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.alignment.types import Severity, TradeIntent

logger = logging.getLogger(__name__)


class CritiqueRole(str, Enum):
    """Roles in the critique swarm."""
    RISK_OFFICER = "risk_officer"        # Focuses on what could go wrong
    DEVIL_ADVOCATE = "devil_advocate"    # Argues against the trade
    REGIME_ANALYST = "regime_analyst"    # Checks regime alignment
    CORRELATION_HAWK = "correlation_hawk"  # Checks portfolio overlap
    TIMING_CRITIC = "timing_critic"      # Questions entry timing


@dataclass
class Critique:
    """A single critique from one swarm role."""
    role: CritiqueRole
    concern: str
    severity: Severity
    recommendation: str
    pass_vote: bool  # Does this role approve the trade?


@dataclass
class CritiqueReport:
    """Aggregated result of swarm critique."""
    approved: bool
    votes_for: int = 0
    votes_against: int = 0
    critiques: List[Critique] = field(default_factory=list)
    consensus_action: str = "PROCEED"
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def approval_rate(self) -> float:
        total = self.votes_for + self.votes_against
        return self.votes_for / total if total > 0 else 0.0


class SwarmCritique:
    """
    Multi-perspective trade review protocol.

    Each role independently evaluates the trade proposal.
    Approval requires majority vote. Any CRITICAL severity
    concern triggers automatic rejection regardless of votes.
    """

    APPROVAL_THRESHOLD = 0.6  # 60% of roles must approve

    def __init__(self) -> None:
        self._critique_history: List[Dict[str, Any]] = []

    def review(
        self,
        intent: TradeIntent,
        current_positions: Optional[List[str]] = None,
        current_heat_pct: float = 0.0,
        current_drawdown_pct: float = 0.0,
        market_regime: str = "unknown",
        recent_trade_count: int = 0,
    ) -> CritiqueReport:
        """Run full swarm critique on a trade proposal."""
        current_positions = current_positions or []
        critiques: List[Critique] = []

        # Each role evaluates independently
        critiques.append(self._risk_officer_review(
            intent, current_heat_pct, current_drawdown_pct,
        ))
        critiques.append(self._devil_advocate_review(intent))
        critiques.append(self._regime_analyst_review(intent, market_regime))
        critiques.append(self._correlation_hawk_review(
            intent, current_positions,
        ))
        critiques.append(self._timing_critic_review(
            intent, recent_trade_count,
        ))

        # Tally votes
        votes_for = sum(1 for c in critiques if c.pass_vote)
        votes_against = sum(1 for c in critiques if not c.pass_vote)

        # Any CRITICAL = automatic rejection
        has_critical = any(
            c.severity == Severity.CRITICAL for c in critiques
        )

        approval_rate = votes_for / len(critiques) if critiques else 0.0
        approved = (
            not has_critical
            and approval_rate >= self.APPROVAL_THRESHOLD
        )

        if has_critical:
            action = "BLOCK"
        elif not approved:
            action = "REDUCE_CONFIDENCE"
        else:
            action = "PROCEED"

        report = CritiqueReport(
            approved=approved,
            votes_for=votes_for,
            votes_against=votes_against,
            critiques=critiques,
            consensus_action=action,
        )

        # Log for audit
        self._critique_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": intent.symbol,
            "approved": approved,
            "votes": f"{votes_for}/{len(critiques)}",
            "action": action,
        })

        if not approved:
            logger.info(
                "SWARM_CRITIQUE: %s REJECTED (%d/%d votes, critical=%s)",
                intent.symbol, votes_for, len(critiques), has_critical,
            )

        return report

    def get_critique_history(self) -> List[Dict[str, Any]]:
        """Return critique audit trail."""
        return list(self._critique_history)

    # ------------------------------------------------------------------
    # Role implementations
    # ------------------------------------------------------------------

    @staticmethod
    def _risk_officer_review(
        intent: TradeIntent,
        heat_pct: float,
        drawdown_pct: float,
    ) -> Critique:
        """Risk Officer: What could go wrong?"""
        if drawdown_pct > 0.10:
            return Critique(
                role=CritiqueRole.RISK_OFFICER,
                concern=f"Portfolio in {drawdown_pct:.1%} drawdown. New positions risky.",
                severity=Severity.HIGH,
                recommendation="Wait for drawdown recovery before new entries.",
                pass_vote=False,
            )
        if heat_pct > 0.20:
            return Critique(
                role=CritiqueRole.RISK_OFFICER,
                concern=f"Portfolio heat at {heat_pct:.1%}. Near capacity.",
                severity=Severity.MEDIUM,
                recommendation="Reduce position size or skip this trade.",
                pass_vote=False,
            )
        if intent.confidence > 0.95:
            return Critique(
                role=CritiqueRole.RISK_OFFICER,
                concern="Suspiciously high confidence. Overconfidence risk.",
                severity=Severity.MEDIUM,
                recommendation="Reduce confidence adjustment by 10-15%.",
                pass_vote=True,
            )
        return Critique(
            role=CritiqueRole.RISK_OFFICER,
            concern="Risk parameters within acceptable bounds.",
            severity=Severity.LOW,
            recommendation="Proceed with standard sizing.",
            pass_vote=True,
        )

    @staticmethod
    def _devil_advocate_review(intent: TradeIntent) -> Critique:
        """Devil's Advocate: Why should we NOT take this trade?"""
        concerns = []

        if not intent.invalidation_condition:
            concerns.append("No invalidation defined -- when are we wrong?")
        if not intent.thesis:
            concerns.append("No thesis -- what is the edge?")
        if intent.confidence < 0.5:
            concerns.append(f"Low confidence ({intent.confidence:.0%}) -- why bother?")

        if concerns:
            return Critique(
                role=CritiqueRole.DEVIL_ADVOCATE,
                concern=" | ".join(concerns),
                severity=Severity.HIGH if not intent.thesis else Severity.MEDIUM,
                recommendation="Address concerns before entry.",
                pass_vote=False,
            )
        return Critique(
            role=CritiqueRole.DEVIL_ADVOCATE,
            concern="Trade thesis is reasonably complete.",
            severity=Severity.LOW,
            recommendation="Proceed -- thesis and invalidation defined.",
            pass_vote=True,
        )

    @staticmethod
    def _regime_analyst_review(
        intent: TradeIntent, regime: str,
    ) -> Critique:
        """Regime Analyst: Does this trade fit the current regime?"""
        if regime == "unknown":
            return Critique(
                role=CritiqueRole.REGIME_ANALYST,
                concern="Regime unknown. Extra caution warranted.",
                severity=Severity.MEDIUM,
                recommendation="Reduce size due to regime uncertainty.",
                pass_vote=True,  # Soft pass with warning
            )
        # Simplified regime check
        if regime == "crisis" or regime == "high_volatility":
            return Critique(
                role=CritiqueRole.REGIME_ANALYST,
                concern=f"Current regime '{regime}' is high-risk.",
                severity=Severity.HIGH,
                recommendation="Avoid new positions or use minimal size.",
                pass_vote=False,
            )
        return Critique(
            role=CritiqueRole.REGIME_ANALYST,
            concern=f"Regime '{regime}' is compatible with trading.",
            severity=Severity.LOW,
            recommendation="Proceed with regime-appropriate strategy.",
            pass_vote=True,
        )

    @staticmethod
    def _correlation_hawk_review(
        intent: TradeIntent,
        current_positions: List[str],
    ) -> Critique:
        """Correlation Hawk: Are we piling into correlated positions?"""
        if intent.symbol in current_positions:
            return Critique(
                role=CritiqueRole.CORRELATION_HAWK,
                concern=f"Already holding {intent.symbol}. Adding = concentration risk.",
                severity=Severity.MEDIUM,
                recommendation="Consider if this is scaling in or doubling down.",
                pass_vote=False,
            )
        if len(current_positions) > 8:
            return Critique(
                role=CritiqueRole.CORRELATION_HAWK,
                concern=f"Already holding {len(current_positions)} positions.",
                severity=Severity.MEDIUM,
                recommendation="Close a position before opening new ones.",
                pass_vote=False,
            )
        return Critique(
            role=CritiqueRole.CORRELATION_HAWK,
            concern="Position diversity acceptable.",
            severity=Severity.LOW,
            recommendation="Proceed.",
            pass_vote=True,
        )

    @staticmethod
    def _timing_critic_review(
        intent: TradeIntent,
        recent_trade_count: int,
    ) -> Critique:
        """Timing Critic: Is the timing right?"""
        if recent_trade_count > 10:
            return Critique(
                role=CritiqueRole.TIMING_CRITIC,
                concern=f"Already {recent_trade_count} trades today. Overtrading?",
                severity=Severity.MEDIUM,
                recommendation="Slow down. Quality over quantity.",
                pass_vote=False,
            )
        return Critique(
            role=CritiqueRole.TIMING_CRITIC,
            concern="Trade frequency within normal bounds.",
            severity=Severity.LOW,
            recommendation="Timing acceptable.",
            pass_vote=True,
        )
