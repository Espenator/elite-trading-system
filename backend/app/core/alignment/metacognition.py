# backend/app/core/alignment/metacognition.py
"""
Pattern 3: Model Metacognition

Forces the model to examine its OWN reasoning before acting.
If the model is reasoning toward bright-line violations,
the reasoning is wrong -- not the limits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.alignment.types import (
    MetacognitionReport,
    Severity,
    TradeIntent,
)

logger = logging.getLogger(__name__)


@dataclass
class ReasoningTrace:
    """Captures one step of model reasoning for audit."""
    step: str
    observation: str
    concern_level: float = 0.0  # 0.0 = no concern, 1.0 = high concern


class ModelMetacognition:
    """
    Forces structured self-examination of model reasoning.

    The model must articulate WHY it wants to take an action,
    what could go wrong, and whether its reasoning is being
    influenced by recent outcomes (recency bias).
    """

    # Patterns that suggest the model is rationalizing
    RATIONALIZATION_MARKERS = [
        "despite",         # "despite the drawdown, we should..."
        "just this once",  # Classic override attempt
        "exception",       # Trying to bypass rules
        "override",        # Direct override language
        "ignore the",      # Ignoring signals
        "momentum",        # Chasing without structure
        "can't miss",      # FOMO language
        "guaranteed",      # Nothing is guaranteed
        "sure thing",      # Overconfidence
        "double down",     # Averaging down without plan
    ]

    def __init__(self) -> None:
        self._reasoning_history: List[Dict[str, Any]] = []

    def examine(
        self,
        intent: TradeIntent,
        model_reasoning: str,
        recent_outcomes: Optional[List[float]] = None,
        current_drawdown_pct: float = 0.0,
    ) -> MetacognitionReport:
        """Examine model reasoning for alignment issues.

        Args:
            intent: The structured trade intent from the model.
            model_reasoning: Free-text reasoning from the model.
            recent_outcomes: List of recent P&L values for recency check.
            current_drawdown_pct: Current portfolio drawdown.

        Returns:
            MetacognitionReport with severity, flags, and recommendation.
        """
        flags: List[str] = []
        confidence_adj = 0.0
        traces: List[ReasoningTrace] = []

        # 1. Check for rationalization language
        rationalization_flags = self._detect_rationalization(model_reasoning)
        if rationalization_flags:
            flags.extend(rationalization_flags)
            confidence_adj -= 0.1 * len(rationalization_flags)
            traces.append(ReasoningTrace(
                step="rationalization_check",
                observation=f"Found {len(rationalization_flags)} rationalization markers",
                concern_level=min(1.0, 0.2 * len(rationalization_flags)),
            ))

        # 2. Check for recency bias
        if recent_outcomes and len(recent_outcomes) >= 3:
            recency_flag = self._detect_recency_bias(recent_outcomes, intent)
            if recency_flag:
                flags.append(recency_flag)
                confidence_adj -= 0.15
                traces.append(ReasoningTrace(
                    step="recency_bias_check",
                    observation=recency_flag,
                    concern_level=0.6,
                ))

        # 3. Check confidence vs drawdown coherence
        if current_drawdown_pct > 0.05 and intent.confidence > 0.8:
            flags.append("high_confidence_during_drawdown")
            confidence_adj -= 0.2
            traces.append(ReasoningTrace(
                step="drawdown_confidence_check",
                observation=f"Confidence {intent.confidence:.0%} seems high during {current_drawdown_pct:.1%} drawdown",
                concern_level=0.7,
            ))

        # 4. Check intent completeness
        completeness_issues = self._check_intent_completeness(intent)
        if completeness_issues:
            flags.extend(completeness_issues)
            traces.append(ReasoningTrace(
                step="completeness_check",
                observation=f"Missing: {', '.join(completeness_issues)}",
                concern_level=0.4,
            ))

        # 5. Determine severity
        if len(flags) == 0:
            severity = Severity.LOW
            action = "PROCEED"
        elif len(flags) <= 2:
            severity = Severity.MEDIUM
            action = "REDUCE_CONFIDENCE"
        elif any("rationalization" in f for f in flags):
            severity = Severity.HIGH
            action = "BLOCK"
        else:
            severity = Severity.HIGH
            action = "REDUCE_CONFIDENCE"

        report = MetacognitionReport(
            severity=severity,
            flags=flags,
            confidence_adjustment=confidence_adj,
            action=action,
            recommendation=self._build_recommendation(flags, traces),
        )

        # Log for audit
        self._reasoning_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent_symbol": intent.symbol,
            "flags": flags,
            "severity": severity.value,
            "action": action,
        })

        if flags:
            logger.info(
                "METACOGNITION: %s flags on %s -> %s",
                len(flags), intent.symbol, action,
            )

        return report

    def get_reasoning_history(self) -> List[Dict[str, Any]]:
        """Return reasoning audit trail."""
        return list(self._reasoning_history)

    # ------------------------------------------------------------------
    # Private detection methods
    # ------------------------------------------------------------------

    def _detect_rationalization(self, reasoning: str) -> List[str]:
        """Scan reasoning text for rationalization patterns."""
        lower = reasoning.lower()
        found = []
        for marker in self.RATIONALIZATION_MARKERS:
            if marker in lower:
                found.append(f"rationalization:{marker}")
        return found

    @staticmethod
    def _detect_recency_bias(
        recent_outcomes: List[float],
        intent: TradeIntent,
    ) -> Optional[str]:
        """Check if intent correlates suspiciously with recent outcomes."""
        recent_avg = sum(recent_outcomes[-3:]) / 3

        # After losses: is model getting more aggressive? (revenge trading)
        if recent_avg < 0 and intent.direction == "long" and intent.confidence > 0.7:
            return "possible_revenge_trading_after_losses"

        # After wins: is model getting overconfident?
        if recent_avg > 0 and intent.confidence > 0.9:
            return "possible_overconfidence_after_wins"

        return None

    @staticmethod
    def _check_intent_completeness(intent: TradeIntent) -> List[str]:
        """Verify the intent has all required reasoning fields."""
        issues = []
        if not intent.symbol:
            issues.append("missing_symbol")
        if not intent.thesis:
            issues.append("missing_thesis")
        if intent.confidence <= 0.0 or intent.confidence > 1.0:
            issues.append("invalid_confidence")
        if not intent.invalidation_condition:
            issues.append("missing_invalidation")
        return issues

    @staticmethod
    def _build_recommendation(
        flags: List[str],
        traces: List[ReasoningTrace],
    ) -> str:
        if not flags:
            return "Reasoning appears sound. Proceed with normal confidence."
        parts = ["Metacognition concerns:"]
        for t in traces:
            if t.concern_level > 0.3:
                parts.append(f"  - [{t.step}] {t.observation}")
        return "\n".join(parts)
