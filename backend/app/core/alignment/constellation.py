# backend/app/core/alignment/constellation.py
"""
Pattern 5: Outcome Constellation

Multi-metric diagnostic view of trading outcomes.

CRITICAL: This is NEVER collapsed into a single target that
agents or ML models optimize against. It exists for human
review and drift detection only.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TradeOutcome:
    """Record of a completed trade for constellation analysis."""
    symbol: str
    entry_time: datetime
    exit_time: datetime
    pnl_pct: float
    r_multiple: float  # P&L in R units (risk units)
    hold_duration_hours: float
    regime_at_entry: str = "unknown"
    respected_structure: bool = True
    cited_principles: List[str] = field(default_factory=list)
    alignment_score: float = 1.0  # How well aligned was the trade


class OutcomeConstellation:
    """
    Multi-dimensional diagnostic of trading performance.

    This is NOT a single number to optimize. It is a constellation
    of metrics that humans review to detect drift, style changes,
    and alignment erosion.

    If you find yourself wanting to collapse this into a single
    fitness function -- you are building Goodhart's Law into code.
    """

    def __init__(self) -> None:
        self._outcomes: List[TradeOutcome] = []

    def record_outcome(self, outcome: TradeOutcome) -> None:
        """Record a completed trade outcome."""
        self._outcomes.append(outcome)
        logger.debug(
            "CONSTELLATION: Recorded %s outcome: %.2fR (%.1f%%)",
            outcome.symbol, outcome.r_multiple, outcome.pnl_pct * 100,
        )

    def get_diagnostic(self, lookback: int = 50) -> Dict[str, Any]:
        """Generate multi-metric diagnostic.

        NOT a training target. A diagnostic.
        If this diverges from expectations, investigate -- don't optimize.
        """
        recent = self._outcomes[-lookback:] if self._outcomes else []
        if not recent:
            return self._empty_diagnostic()

        r_values = [o.r_multiple for o in recent]
        pnl_values = [o.pnl_pct for o in recent]

        return {
            # -- R Distribution (core metric) --
            "avg_r": sum(r_values) / len(r_values),
            "median_r": statistics.median(r_values),
            "r_stddev": statistics.stdev(r_values) if len(r_values) > 1 else 0.0,
            "best_r": max(r_values),
            "worst_r": min(r_values),
            "positive_r_pct": sum(1 for r in r_values if r > 0) / len(r_values),

            # -- Timing --
            "avg_hold_hours": sum(o.hold_duration_hours for o in recent) / len(recent),
            "stage_2_entry_rate": self._calc_stage_2_rate(recent),

            # -- Structure Discipline --
            "structure_respect_rate": sum(
                1 for o in recent if o.respected_structure
            ) / len(recent),

            # -- Regime Adaptation --
            "regime_adaptation_speed": self._calc_regime_adaptation(recent),

            # -- Diversification --
            "correlation_diversity": self._calc_diversity(recent),

            # -- Resilience --
            "drawdown_recovery_time": self._calc_recovery_time(recent),

            # -- Alignment --
            "avg_alignment_score": sum(o.alignment_score for o in recent) / len(recent),
            "principle_coverage": self._calc_principle_coverage(recent),

            # -- Meta --
            "total_trades": len(recent),
            "period_pnl_pct": sum(pnl_values),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def detect_drift(
        self, baseline: Dict[str, Any], current: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Compare current constellation to baseline for drift detection."""
        if current is None:
            current = self.get_diagnostic()

        drift_signals = {}
        compare_keys = [
            "avg_r", "positive_r_pct", "structure_respect_rate",
            "avg_alignment_score", "avg_hold_hours",
        ]

        for key in compare_keys:
            if key in baseline and key in current:
                b_val = baseline[key]
                c_val = current[key]
                if b_val != 0:
                    change_pct = (c_val - b_val) / abs(b_val)
                    if abs(change_pct) > 0.20:  # 20% drift threshold
                        drift_signals[key] = {
                            "baseline": b_val,
                            "current": c_val,
                            "change_pct": change_pct,
                            "status": "DRIFT_DETECTED",
                        }

        return {
            "has_drift": len(drift_signals) > 0,
            "drift_count": len(drift_signals),
            "signals": drift_signals,
        }

    # ------------------------------------------------------------------
    # Private calculation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_diagnostic() -> Dict[str, Any]:
        return {
            "avg_r": 0.0, "median_r": 0.0, "r_stddev": 0.0,
            "best_r": 0.0, "worst_r": 0.0, "positive_r_pct": 0.0,
            "avg_hold_hours": 0.0, "stage_2_entry_rate": 0.0,
            "structure_respect_rate": 0.0, "regime_adaptation_speed": 0.0,
            "correlation_diversity": 0.0, "drawdown_recovery_time": 0.0,
            "avg_alignment_score": 0.0, "principle_coverage": 0.0,
            "total_trades": 0, "period_pnl_pct": 0.0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _calc_stage_2_rate(outcomes: List[TradeOutcome]) -> float:
        """Placeholder: fraction of entries at stage 2 breakout points."""
        # TODO: integrate with regime/stage detection
        return 0.0

    @staticmethod
    def _calc_regime_adaptation(outcomes: List[TradeOutcome]) -> float:
        """Measure how quickly strategy adapts to regime changes."""
        if len(outcomes) < 5:
            return 0.0
        regimes = [o.regime_at_entry for o in outcomes]
        changes = sum(1 for i in range(1, len(regimes)) if regimes[i] != regimes[i - 1])
        # Higher diversity in recent trades suggests adaptation
        return min(1.0, changes / max(1, len(outcomes) - 1))

    @staticmethod
    def _calc_diversity(outcomes: List[TradeOutcome]) -> float:
        """Measure symbol diversity in recent trades."""
        if not outcomes:
            return 0.0
        symbols = set(o.symbol for o in outcomes)
        return min(1.0, len(symbols) / max(1, len(outcomes) * 0.3))

    @staticmethod
    def _calc_recovery_time(outcomes: List[TradeOutcome]) -> float:
        """Estimate average drawdown recovery time in hours."""
        if len(outcomes) < 3:
            return 0.0
        # Simple: average duration of losing streak sequences
        streak_durations = []
        current_streak_hours = 0.0
        in_streak = False
        for o in outcomes:
            if o.r_multiple < 0:
                current_streak_hours += o.hold_duration_hours
                in_streak = True
            else:
                if in_streak:
                    streak_durations.append(current_streak_hours)
                    current_streak_hours = 0.0
                    in_streak = False
        if in_streak:
            streak_durations.append(current_streak_hours)
        return sum(streak_durations) / len(streak_durations) if streak_durations else 0.0

    @staticmethod
    def _calc_principle_coverage(outcomes: List[TradeOutcome]) -> float:
        """What fraction of Bible principles are being actively used."""
        if not outcomes:
            return 0.0
        all_cited = set()
        for o in outcomes:
            all_cited.update(o.cited_principles)
        # Rough estimate: assume ~15 total principles
        return min(1.0, len(all_cited) / 15.0)
