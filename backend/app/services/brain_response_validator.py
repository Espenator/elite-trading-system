"""Strict parser/validator for Brain Service structured responses.

Ensures hypothesis and critic responses from the LLM never leak malformed
data into execution. Invalid or missing fields are normalized to safe defaults.
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VALID_DIRECTIONS = frozenset({"buy", "sell", "hold"})
CONFIDENCE_MIN, CONFIDENCE_MAX = 0.0, 1.0


@dataclass
class ValidatedHypothesis:
    """Validated hypothesis output safe for council use."""

    direction: str  # "buy" | "sell" | "hold"
    confidence: float  # 0.0–1.0
    reasoning: str
    supporting_signals: List[str]
    invalidation_notes: List[str]
    risk_flags: List[str]
    summary: str
    reasoning_bullets: List[str]
    is_fallback: bool  # True if LLM was not used or response was invalid


def validate_hypothesis_response(raw: Dict[str, Any]) -> ValidatedHypothesis:
    """Parse and validate brain infer response. Never raises; returns safe struct.

    - direction: coerced to buy/sell/hold; invalid → hold
    - confidence: clamped to [0, 1]; invalid → 0.2 (safe low)
    - reasoning/summary: string, max 2000 chars
    - supporting_signals, invalidation_notes, risk_flags, reasoning_bullets: lists of strings
    - If raw is clearly from fallback (risk_flags contain llm_unavailable, timeout, etc.),
      is_fallback=True and confidence is capped at 0.2.
    """
    fallback_tags = {"llm_unavailable", "brain_disabled", "timeout", "unreachable", "circuit_breaker_open", "grpc_not_connected", "unparseable_response", "internal_error"}
    risk_flags = _str_list(raw.get("risk_flags"), "risk_flags")[:20]
    is_fallback = bool(fallback_tags & set(risk_flags) or raw.get("error") or raw.get("degraded_mode"))

    direction = _direction(raw.get("direction"), "direction")
    confidence = _confidence(raw.get("confidence"), "confidence")
    if is_fallback:
        confidence = min(confidence, 0.2)

    reasoning = _str_val(raw.get("reasoning") or raw.get("summary"), "reasoning", max_len=2000)
    summary = _str_val(raw.get("summary") or reasoning, "summary", max_len=500)
    supporting_signals = _str_list(raw.get("supporting_signals"), "supporting_signals")[:10]
    invalidation_notes = _str_list(raw.get("invalidation_notes"), "invalidation_notes")[:10]
    reasoning_bullets = _str_list(raw.get("reasoning_bullets"), "reasoning_bullets")[:10]

    return ValidatedHypothesis(
        direction=direction,
        confidence=confidence,
        reasoning=reasoning,
        supporting_signals=supporting_signals,
        invalidation_notes=invalidation_notes,
        risk_flags=risk_flags,
        summary=summary,
        reasoning_bullets=reasoning_bullets,
        is_fallback=is_fallback,
    )


def _direction(value: Any, field: str) -> str:
    if value is None:
        return "hold"
    s = str(value).strip().lower()
    return s if s in VALID_DIRECTIONS else "hold"


def _confidence(value: Any, field: str) -> float:
    if value is None:
        return 0.2
    try:
        f = float(value)
        return max(CONFIDENCE_MIN, min(CONFIDENCE_MAX, f))
    except (TypeError, ValueError):
        return 0.2


def _str_val(value: Any, field: str, max_len: int = 5000) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return s[:max_len] if len(s) > max_len else s


def _str_list(value: Any, field: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        return []
    return [str(x).strip() for x in value if x is not None and str(x).strip()]


@dataclass
class ValidatedCritic:
    """Validated critic/postmortem output."""

    analysis: str
    lessons: List[str]
    performance_score: float  # 0.0–1.0
    key_takeaways: List[str]
    is_fallback: bool


def validate_critic_response(raw: Dict[str, Any]) -> ValidatedCritic:
    """Parse and validate brain critic response. Never raises; returns safe struct."""
    is_fallback = bool(raw.get("error")) or (raw.get("performance_score", 0) == 0 and not raw.get("analysis"))

    analysis = _str_val(raw.get("analysis"), "analysis", max_len=2000)
    lessons = _str_list(raw.get("lessons"), "lessons")[:10]
    key_takeaways = _str_list(raw.get("key_takeaways"), "key_takeaways")[:10]
    performance_score = _confidence(raw.get("performance_score"), "performance_score")

    return ValidatedCritic(
        analysis=analysis,
        lessons=lessons,
        performance_score=performance_score,
        key_takeaways=key_takeaways,
        is_fallback=is_fallback,
    )
