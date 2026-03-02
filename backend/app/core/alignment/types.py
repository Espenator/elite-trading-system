"""Constitutive Alignment Type Definitions.

These dataclasses replace single-number composite scores with
multi-dimensional identity objects. The ML flywheel cannot game
an identity -- only a metric.

Used by: signal_engine.py, kelly_position_sizer.py, alpaca_service.py,
         openclaw_bridge_service.py, ml_training.py
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

Side = Literal["BUY", "SELL"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


# ---------------------------------------------------------------------------
# Pattern 1: Signal Identity (replaces single composite_score float)
# ---------------------------------------------------------------------------
@dataclass
class SignalIdentity:
    """Constitutive signal -- IS the setup, not a score ABOUT the setup.

    Each facet describes a dimension of the signal's character.
    Downstream systems reason about identity coherence, not threshold
    comparisons on a single number.
    """
    ticker: str
    timeframe: str  # e.g. "15m", "1h", "1D"

    # Constitutive facets (identity, not score)
    compression_profile: Dict[str, Any] = field(default_factory=dict)
    ignition_profile: Dict[str, Any] = field(default_factory=dict)
    structure_profile: Dict[str, Any] = field(default_factory=dict)
    flow_profile: Dict[str, Any] = field(default_factory=dict)
    regime_context: Dict[str, Any] = field(default_factory=dict)

    # Explainability
    narrative: str = ""
    tags: List[str] = field(default_factory=list)

    # Legacy compatibility: keep composite_score as DIAGNOSTIC ONLY
    composite_score: float = 50.0  # NOT a training target


@dataclass
class SignalProposal:
    """A proposal to take a trade, derived from a SignalIdentity.

    Confidence and expected_r are advisory -- they inform but do not
    determine execution. The BrightLineEnforcer has final say.
    """
    identity: SignalIdentity
    side: Side
    confidence: float  # 0.0-1.0, advisory only
    expected_r: float  # advisory only
    reasons: List[str] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pattern 2: Trade Intent + Enforcement (BrightLineEnforcer types)
# ---------------------------------------------------------------------------
@dataclass
class TradeIntent:
    """A sized trade proposal ready for enforcement gate."""
    proposal: SignalProposal
    size_pct: float  # Kelly-suggested size as fraction of equity
    stop: Dict[str, Any] = field(default_factory=dict)
    take_profit: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnforcementDecision:
    """Output of BrightLineEnforcer.validate_intent().

    If allowed=False, the trade MUST NOT execute. No reasoning
    around this -- if the system tries to override, there is a bug.
    """
    allowed: bool
    final_size_pct: float
    veto_reason: Optional[str] = None
    resize_reason: Optional[str] = None
    flags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pattern 3: Metacognition Report
# ---------------------------------------------------------------------------
@dataclass
class MetacognitionReport:
    """Output of ModelMetacognition checks.

    If the model is reasoning toward bright-line violations,
    the reasoning is wrong -- not the limits.
    """
    severity: Severity
    flags: List[str] = field(default_factory=list)
    confidence_adjustment: float = 0.0  # negative = reduce confidence
    action: str = "PROCEED"  # PROCEED / REDUCE_CONFIDENCE / BLOCK / CONSERVATIVE_ONLY
    recommendation: str = ""


# ---------------------------------------------------------------------------
# Pattern 5: Outcome Constellation (diagnostic, NEVER a training target)
# ---------------------------------------------------------------------------
@dataclass
class OutcomeConstellation:
    """Multi-metric diagnostic view of trading outcomes.

    CRITICAL: This is NEVER collapsed into a single target that
    agents or ML models optimize against. It exists for human
    review and drift detection only.
    """
    r_multiple_distribution: List[float] = field(default_factory=list)
    stage_2_entry_rate: float = 0.0  # Are we entering early?
    structure_respect_rate: float = 0.0  # Are stops structural?
    regime_adaptation_speed: float = 0.0  # How fast do we adjust?
    correlation_diversity: float = 0.0  # Are we diversified?
    drawdown_recovery_time: float = 0.0  # How resilient are we?

    def purpose_alignment_diagnostic(self) -> Dict[str, Any]:
        """NOT a training target. A diagnostic.
        If this diverges from expectations, investigate -- don't optimize."""
        return {
            "avg_r": sum(self.r_multiple_distribution) / max(1, len(self.r_multiple_distribution)),
            "entry_timing": self.stage_2_entry_rate,
            "discipline": self.structure_respect_rate,
            "adaptability": self.regime_adaptation_speed,
            "diversification": self.correlation_diversity,
            "resilience": self.drawdown_recovery_time,
        }
