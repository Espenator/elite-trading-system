"""Constitutive Alignment Module for Embodier Trader.

Implements the 'Soul Document' architecture for trading systems:
- Identity-based signal evaluation (not just metric thresholds)
- Hard-coded bright lines that cannot be overridden
- Metacognitive self-skepticism for ML models
- Trading Bible DNA as executable identity

Based on Anthropic's constitutive alignment patterns applied to
algorithmic trading (Goodhart-resistant design).
"""
from app.core.alignment.types import (
    SignalIdentity,
    SignalProposal,
    TradeIntent,
    EnforcementDecision,
    MetacognitionReport,
    OutcomeConstellation,
)
from app.core.alignment.bright_lines import BrightLineEnforcer
from app.core.alignment.metacognition import ModelMetacognition
from app.core.alignment.constitution import TradingConstitution

__all__ = [
    "SignalIdentity",
    "SignalProposal",
    "TradeIntent",
    "EnforcementDecision",
    "MetacognitionReport",
    "OutcomeConstellation",
    "BrightLineEnforcer",
    "ModelMetacognition",
    "TradingConstitution",
]
