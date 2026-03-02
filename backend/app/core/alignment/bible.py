# backend/app/core/alignment/bible.py
"""
Pattern 4: Trading Bible as DNA

Encodes trading philosophy as structured, queryable data
that every decision must reference. Not prose -- code.

Every trade must trace back to a Bible principle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PrincipleCategory(str, Enum):
    RISK = "risk"
    ENTRY = "entry"
    EXIT = "exit"
    POSITION_SIZING = "position_sizing"
    PSYCHOLOGY = "psychology"
    REGIME = "regime"


@dataclass
class TradingPrinciple:
    """A single principle from the Trading Bible."""
    id: str
    category: PrincipleCategory
    statement: str
    rationale: str
    hard_constraint: bool = False  # If True, violation = automatic block
    related_principles: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# THE TRADING BIBLE -- Constitutional trading philosophy
# ---------------------------------------------------------------------------
# These are NOT suggestions. They are the DNA of how we trade.
# Every trade decision must be traceable to one or more principles.
# ---------------------------------------------------------------------------

TRADING_BIBLE: Dict[str, TradingPrinciple] = {}


def _register(p: TradingPrinciple) -> None:
    TRADING_BIBLE[p.id] = p


# --- RISK PRINCIPLES ---
_register(TradingPrinciple(
    id="RISK-001",
    category=PrincipleCategory.RISK,
    statement="Preserve capital above all else.",
    rationale="You cannot trade if you have no capital. Survival is the first objective.",
    hard_constraint=True,
))
_register(TradingPrinciple(
    id="RISK-002",
    category=PrincipleCategory.RISK,
    statement="Never risk more than 2% of portfolio on a single trade.",
    rationale="No single trade should threaten overall portfolio health.",
    hard_constraint=True,
))
_register(TradingPrinciple(
    id="RISK-003",
    category=PrincipleCategory.RISK,
    statement="Cut losses quickly. Let winners run.",
    rationale="Asymmetric payoff is the foundation of profitable trading.",
    hard_constraint=False,
))
_register(TradingPrinciple(
    id="RISK-004",
    category=PrincipleCategory.RISK,
    statement="Reduce exposure during drawdowns, never increase it.",
    rationale="Drawdowns impair judgment. Smaller size preserves optionality.",
    hard_constraint=True,
))

# --- ENTRY PRINCIPLES ---
_register(TradingPrinciple(
    id="ENTRY-001",
    category=PrincipleCategory.ENTRY,
    statement="Every entry must have a thesis and invalidation condition.",
    rationale="Without a thesis, you are gambling. Without invalidation, you cannot be wrong.",
    hard_constraint=True,
))
_register(TradingPrinciple(
    id="ENTRY-002",
    category=PrincipleCategory.ENTRY,
    statement="Prefer entries with structural support (levels, patterns, volume).",
    rationale="Structure-based entries have higher probability and clearer invalidation.",
    hard_constraint=False,
))
_register(TradingPrinciple(
    id="ENTRY-003",
    category=PrincipleCategory.ENTRY,
    statement="Do not chase. Wait for the setup or miss it.",
    rationale="FOMO entries have the worst risk/reward profiles.",
    hard_constraint=False,
    related_principles=["PSYCHOLOGY-001"],
))

# --- EXIT PRINCIPLES ---
_register(TradingPrinciple(
    id="EXIT-001",
    category=PrincipleCategory.EXIT,
    statement="Define exit before entry. No trade without a stop.",
    rationale="Pre-defined exits remove emotional decision-making at the worst time.",
    hard_constraint=True,
))
_register(TradingPrinciple(
    id="EXIT-002",
    category=PrincipleCategory.EXIT,
    statement="Take partial profits at structure. Trail the rest.",
    rationale="Partial profits lock in gains while allowing for larger moves.",
    hard_constraint=False,
))

# --- POSITION SIZING ---
_register(TradingPrinciple(
    id="SIZE-001",
    category=PrincipleCategory.POSITION_SIZING,
    statement="Size positions based on risk, not conviction.",
    rationale="Conviction is subjective and prone to bias. Risk is measurable.",
    hard_constraint=True,
))
_register(TradingPrinciple(
    id="SIZE-002",
    category=PrincipleCategory.POSITION_SIZING,
    statement="Scale in, not all-at-once.",
    rationale="Scaling reduces timing risk and allows for better average entry.",
    hard_constraint=False,
))

# --- PSYCHOLOGY ---
_register(TradingPrinciple(
    id="PSYCHOLOGY-001",
    category=PrincipleCategory.PSYCHOLOGY,
    statement="Never trade to recover losses.",
    rationale="Revenge trading compounds losses. Take a break after significant drawdown.",
    hard_constraint=True,
    related_principles=["RISK-004"],
))
_register(TradingPrinciple(
    id="PSYCHOLOGY-002",
    category=PrincipleCategory.PSYCHOLOGY,
    statement="Overconfidence after wins is as dangerous as fear after losses.",
    rationale="Mean reversion applies to trader psychology too.",
    hard_constraint=False,
))

# --- REGIME ---
_register(TradingPrinciple(
    id="REGIME-001",
    category=PrincipleCategory.REGIME,
    statement="Adapt strategy to market regime. Do not force a strategy onto the wrong regime.",
    rationale="Trend strategies fail in ranges. Mean-reversion fails in trends.",
    hard_constraint=False,
))
_register(TradingPrinciple(
    id="REGIME-002",
    category=PrincipleCategory.REGIME,
    statement="When uncertain about regime, reduce size and widen stops.",
    rationale="Uncertainty demands caution, not aggression.",
    hard_constraint=False,
    related_principles=["RISK-004"],
))


# ---------------------------------------------------------------------------
# Bible Checker
# ---------------------------------------------------------------------------

@dataclass
class BibleCheckResult:
    """Result of checking a trade against the Trading Bible."""
    aligned: bool
    matched_principles: List[str] = field(default_factory=list)
    violated_principles: List[str] = field(default_factory=list)
    hard_violations: List[str] = field(default_factory=list)
    recommendation: str = ""


class TradingBibleChecker:
    """
    Checks trade decisions against the Trading Bible.

    Every trade must be traceable to at least one principle.
    Hard-constraint violations are automatic blocks.
    """

    def check_trade(
        self,
        cited_principles: List[str],
        has_thesis: bool = False,
        has_stop_loss: bool = False,
        has_invalidation: bool = False,
        is_during_drawdown: bool = False,
        is_increasing_size: bool = False,
        is_revenge_trade: bool = False,
    ) -> BibleCheckResult:
        """Check a proposed trade against Bible principles."""
        matched: List[str] = []
        violated: List[str] = []
        hard_violated: List[str] = []

        # Verify cited principles exist
        for pid in cited_principles:
            if pid in TRADING_BIBLE:
                matched.append(pid)
            else:
                logger.warning("Unknown principle cited: %s", pid)

        # Check hard constraints
        if not has_thesis:
            violated.append("ENTRY-001")
            hard_violated.append("ENTRY-001")

        if not has_stop_loss:
            violated.append("EXIT-001")
            hard_violated.append("EXIT-001")

        if not has_invalidation:
            violated.append("ENTRY-001")
            if "ENTRY-001" not in hard_violated:
                hard_violated.append("ENTRY-001")

        if is_during_drawdown and is_increasing_size:
            violated.append("RISK-004")
            hard_violated.append("RISK-004")

        if is_revenge_trade:
            violated.append("PSYCHOLOGY-001")
            hard_violated.append("PSYCHOLOGY-001")

        # Must cite at least one principle
        if not matched:
            violated.append("NO_PRINCIPLE_CITED")

        aligned = len(hard_violated) == 0 and len(matched) > 0

        return BibleCheckResult(
            aligned=aligned,
            matched_principles=matched,
            violated_principles=violated,
            hard_violations=hard_violated,
            recommendation=self._recommend(aligned, hard_violated, violated),
        )

    def get_principles_by_category(
        self, category: PrincipleCategory
    ) -> List[TradingPrinciple]:
        """Get all principles in a category."""
        return [
            p for p in TRADING_BIBLE.values()
            if p.category == category
        ]

    def get_hard_constraints(self) -> List[TradingPrinciple]:
        """Get all hard-constraint principles."""
        return [p for p in TRADING_BIBLE.values() if p.hard_constraint]

    @staticmethod
    def _recommend(
        aligned: bool,
        hard_violated: List[str],
        violated: List[str],
    ) -> str:
        if aligned:
            return "Trade aligns with Trading Bible principles."
        parts = ["Trade violates Trading Bible:"]
        for hv in hard_violated:
            p = TRADING_BIBLE.get(hv)
            stmt = p.statement if p else hv
            parts.append(f"  HARD VIOLATION: [{hv}] {stmt}")
        for v in violated:
            if v not in hard_violated and v != "NO_PRINCIPLE_CITED":
                p = TRADING_BIBLE.get(v)
                stmt = p.statement if p else v
                parts.append(f"  violation: [{v}] {stmt}")
        if "NO_PRINCIPLE_CITED" in violated:
            parts.append("  No Bible principle cited for this trade.")
        return "\n".join(parts)
