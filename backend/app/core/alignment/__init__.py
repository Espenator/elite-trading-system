"""Constitutive Alignment Module for Embodier Trader.

Implements the 'Soul Document' architecture for trading systems:
- Identity-based signal evaluation (not just metric thresholds)
- Hard-coded bright lines that cannot be overridden
- Metacognitive self-skepticism for ML models
- Trading Bible DNA as executable identity
- Outcome Constellation for drift detection
- Swarm Critique for multi-perspective review

Based on Anthropic's constitutive alignment patterns applied to
algorithmic trading (Goodhart-resistant design).
"""

# Types (Pattern 1: Signal Identity)
from app.core.alignment.types import (
    Severity,
    SignalIdentity,
    SignalProposal,
    TradeIntent,
    EnforcementDecision,
    MetacognitionReport,
    OutcomeConstellation as OutcomeConstellationType,
)

# Pattern 2: Bright-Line Enforcer
from app.core.alignment.bright_lines import BrightLineEnforcer

# Pattern 3: Model Metacognition
from app.core.alignment.metacognition import ModelMetacognition

# Pattern 4: Trading Bible DNA
from app.core.alignment.bible import TradingBibleChecker, TRADING_BIBLE

# Pattern 5: Outcome Constellation
from app.core.alignment.constellation import OutcomeConstellation

# Pattern 6: Swarm Critique
from app.core.alignment.critique import SwarmCritique

# Orchestrator
from app.core.alignment.engine import AlignmentEngine, AlignmentVerdict

__all__ = [
    # Types
    "Severity",
    "SignalIdentity",
    "SignalProposal",
    "TradeIntent",
    "EnforcementDecision",
    "MetacognitionReport",
    # Pattern implementations
    "BrightLineEnforcer",
    "ModelMetacognition",
    "TradingBibleChecker",
    "TRADING_BIBLE",
    "OutcomeConstellation",
    "SwarmCritique",
    # Engine
    "AlignmentEngine",
    "AlignmentVerdict",
]
