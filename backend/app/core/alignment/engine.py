# backend/app/core/alignment/engine.py
"""
Alignment Engine - Orchestrator for all 6 Constitutive Alignment Patterns.

This is the single entry point for running alignment checks on any
trade proposal. It coordinates:

  1. Signal Identity (types.py) - Structured signal decomposition
  2. Bright-Line Enforcer - Constitutional hard limits
  3. Model Metacognition - Reasoning self-examination
  4. Trading Bible DNA - Philosophy compliance
  5. Outcome Constellation - Multi-metric diagnostics
  6. Swarm Critique - Multi-perspective review

The engine runs checks in order of severity:
  Bright lines first (hard block) -> Bible -> Metacognition -> Critique
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.alignment.bible import TradingBibleChecker, BibleCheckResult
from app.core.alignment.bright_lines import BrightLineEnforcer, BrightLineReport
from app.core.alignment.constellation import OutcomeConstellation
from app.core.alignment.critique import SwarmCritique, CritiqueReport
from app.core.alignment.metacognition import ModelMetacognition, MetacognitionReport
from app.core.alignment.types import (
    EnforcementDecision,
    Severity,
    SignalIdentity,
    TradeIntent,
)

logger = logging.getLogger(__name__)


@dataclass
class AlignmentVerdict:
    """Final verdict from the full alignment pipeline."""
    approved: bool
    action: str  # PROCEED / REDUCE_CONFIDENCE / BLOCK
    severity: Severity
    adjusted_confidence: float
    bright_line_report: Optional[BrightLineReport] = None
    bible_report: Optional[BibleCheckResult] = None
    metacognition_report: Optional[MetacognitionReport] = None
    critique_report: Optional[CritiqueReport] = None
    flags: List[str] = field(default_factory=list)
    recommendation: str = ""
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API/WebSocket responses."""
        return {
            "approved": self.approved,
            "action": self.action,
            "severity": self.severity.value,
            "adjusted_confidence": self.adjusted_confidence,
            "flags": self.flags,
            "recommendation": self.recommendation,
            "checked_at": self.checked_at.isoformat(),
            "bright_lines_passed": self.bright_line_report.passed if self.bright_line_report else None,
            "bible_aligned": self.bible_report.aligned if self.bible_report else None,
            "critique_approved": self.critique_report.approved if self.critique_report else None,
            "critique_votes": f"{self.critique_report.votes_for}/{self.critique_report.votes_for + self.critique_report.votes_against}" if self.critique_report else None,
        }


class AlignmentEngine:
    """
    Orchestrates all alignment checks for trade proposals.

    Usage:
        engine = AlignmentEngine()
        verdict = engine.evaluate(
            intent=trade_intent,
            proposed_position_pct=0.05,
            current_heat_pct=0.15,
            current_drawdown_pct=0.03,
        )
        if not verdict.approved:
            # Do NOT trade
            log(verdict.recommendation)
    """

    def __init__(self) -> None:
        self.bright_lines = BrightLineEnforcer()
        self.metacognition = ModelMetacognition()
        self.bible_checker = TradingBibleChecker()
        self.constellation = OutcomeConstellation()
        self.swarm_critique = SwarmCritique()

    def evaluate(
        self,
        intent: TradeIntent,
        proposed_position_pct: float,
        current_heat_pct: float,
        current_drawdown_pct: float,
        correlated_exposure_pct: float = 0.0,
        leverage: float = 1.0,
        model_reasoning: str = "",
        recent_outcomes: Optional[List[float]] = None,
        cited_principles: Optional[List[str]] = None,
        current_positions: Optional[List[str]] = None,
        market_regime: str = "unknown",
        recent_trade_count: int = 0,
    ) -> AlignmentVerdict:
        """Run the full alignment pipeline.

        Order of checks (fail-fast):
        1. Bright lines (hard block - no override)
        2. Trading Bible (hard constraint violations block)
        3. Metacognition (reasoning examination)
        4. Swarm Critique (multi-perspective review)

        Returns AlignmentVerdict with final decision.
        """
        all_flags: List[str] = []
        confidence = intent.confidence

        # ----- 1. BRIGHT LINES (Constitutional - no override) -----
        bl_report = self.bright_lines.enforce(
            proposed_position_pct=proposed_position_pct,
            current_heat_pct=current_heat_pct,
            current_drawdown_pct=current_drawdown_pct,
            correlated_exposure_pct=correlated_exposure_pct,
            leverage=leverage,
        )
        if not bl_report.passed:
            all_flags.extend(bl_report.flags)
            logger.warning(
                "ALIGNMENT_ENGINE: BLOCKED by bright lines for %s",
                intent.symbol,
            )
            return AlignmentVerdict(
                approved=False,
                action="BLOCK",
                severity=Severity.CRITICAL,
                adjusted_confidence=0.0,
                bright_line_report=bl_report,
                flags=all_flags,
                recommendation=bl_report.decision.veto_reason if bl_report.decision else "Bright-line violation.",
            )

        # ----- 2. TRADING BIBLE -----
        bible_report = self.bible_checker.check_trade(
            cited_principles=cited_principles or [],
            has_thesis=bool(intent.thesis),
            has_stop_loss=bool(intent.stop),
            has_invalidation=bool(intent.invalidation_condition),
            is_during_drawdown=current_drawdown_pct > 0.05,
            is_increasing_size=intent.meta.get("is_increasing_size", False),
            is_revenge_trade=intent.meta.get("is_revenge_trade", False),
        )
        if bible_report.hard_violations:
            all_flags.extend([f"bible:{v}" for v in bible_report.hard_violations])
            logger.warning(
                "ALIGNMENT_ENGINE: BLOCKED by Bible for %s: %s",
                intent.symbol, bible_report.hard_violations,
            )
            return AlignmentVerdict(
                approved=False,
                action="BLOCK",
                severity=Severity.HIGH,
                adjusted_confidence=0.0,
                bright_line_report=bl_report,
                bible_report=bible_report,
                flags=all_flags,
                recommendation=bible_report.recommendation,
            )

        # ----- 3. METACOGNITION -----
        meta_report = self.metacognition.examine(
            intent=intent,
            model_reasoning=model_reasoning,
            recent_outcomes=recent_outcomes,
            current_drawdown_pct=current_drawdown_pct,
        )
        if meta_report.flags:
            all_flags.extend([f"meta:{f}" for f in meta_report.flags])
        confidence += meta_report.confidence_adjustment
        confidence = max(0.0, min(1.0, confidence))

        if meta_report.action == "BLOCK":
            return AlignmentVerdict(
                approved=False,
                action="BLOCK",
                severity=meta_report.severity,
                adjusted_confidence=0.0,
                bright_line_report=bl_report,
                bible_report=bible_report,
                metacognition_report=meta_report,
                flags=all_flags,
                recommendation=meta_report.recommendation,
            )

        # ----- 4. SWARM CRITIQUE -----
        critique_report = self.swarm_critique.review(
            intent=intent,
            current_positions=current_positions,
            current_heat_pct=current_heat_pct,
            current_drawdown_pct=current_drawdown_pct,
            market_regime=market_regime,
            recent_trade_count=recent_trade_count,
        )
        if not critique_report.approved:
            all_flags.append(f"critique:rejected:{critique_report.votes_for}/{critique_report.votes_for + critique_report.votes_against}")

        if critique_report.consensus_action == "REDUCE_CONFIDENCE":
            confidence *= 0.8  # 20% penalty

        # ----- FINAL VERDICT -----
        if critique_report.consensus_action == "BLOCK":
            approved = False
            action = "BLOCK"
            severity = Severity.HIGH
        elif not critique_report.approved:
            approved = False
            action = "REDUCE_CONFIDENCE"
            severity = Severity.MEDIUM
        elif all_flags:
            approved = True
            action = "PROCEED_WITH_CAUTION"
            severity = Severity.MEDIUM
        else:
            approved = True
            action = "PROCEED"
            severity = Severity.LOW

        verdict = AlignmentVerdict(
            approved=approved,
            action=action,
            severity=severity,
            adjusted_confidence=round(confidence, 4),
            bright_line_report=bl_report,
            bible_report=bible_report,
            metacognition_report=meta_report,
            critique_report=critique_report,
            flags=all_flags,
            recommendation=self._build_final_recommendation(
                approved, all_flags, confidence,
            ),
        )

        logger.info(
            "ALIGNMENT_ENGINE: %s -> %s (confidence: %.2f, flags: %d)",
            intent.symbol, action, confidence, len(all_flags),
        )

        return verdict

    @staticmethod
    def _build_final_recommendation(
        approved: bool,
        flags: List[str],
        confidence: float,
    ) -> str:
        if approved and not flags:
            return f"All alignment checks passed. Confidence: {confidence:.0%}"
        if approved:
            return (
                f"Approved with caution. {len(flags)} flag(s) noted. "
                f"Adjusted confidence: {confidence:.0%}"
            )
        return (
            f"REJECTED. {len(flags)} flag(s): "
            + ", ".join(flags[:5])
            + ("..." if len(flags) > 5 else "")
        )
