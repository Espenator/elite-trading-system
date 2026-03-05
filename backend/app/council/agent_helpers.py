"""Council Agent Helpers — shared utilities for all council agents.

Reduces boilerplate across the 14 agents by providing:
- Safe feature extraction with type coercion
- Standard scoring → direction/confidence mapping
- Consistent float parsing from feature dicts
"""

from typing import Any, Dict, Optional, Tuple


def get_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the inner features dict (handles both nested and flat formats)."""
    return features.get("features", features)


def safe_float(
    features: Dict[str, Any],
    key: str,
    default: float = 0.0,
    *,
    fallback_keys: Optional[Tuple[str, ...]] = None,
) -> float:
    """Safely extract a float from features dict.

    Args:
        features: Feature dict to extract from.
        key: Primary key to look up.
        default: Default value if key missing or None.
        fallback_keys: Additional keys to try if primary key is missing.

    Returns:
        Float value, or default if extraction fails.
    """
    val = features.get(key)
    if val is None and fallback_keys:
        for fk in fallback_keys:
            val = features.get(fk)
            if val is not None:
                break
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def score_to_vote(
    score: int,
    *,
    strong_threshold: int = 3,
    weak_threshold: int = 1,
    base_confidence: float = 0.3,
    strong_confidence_boost: float = 0.07,
    weak_confidence_boost: float = 0.05,
    max_confidence: float = 0.85,
) -> Tuple[str, float]:
    """Convert a numerical score to (direction, confidence).

    Positive scores → buy, negative → sell, near zero → hold.

    Args:
        score: Integer score (positive = bullish, negative = bearish).
        strong_threshold: Score magnitude for strong conviction.
        weak_threshold: Score magnitude for weak conviction.
        base_confidence: Starting confidence level.
        strong_confidence_boost: Per-point confidence boost for strong signals.
        weak_confidence_boost: Per-point confidence boost for weak signals.
        max_confidence: Maximum allowed confidence.

    Returns:
        Tuple of (direction, confidence).
    """
    abs_score = abs(score)

    if abs_score >= strong_threshold:
        direction = "buy" if score > 0 else "sell"
        confidence = min(max_confidence, 0.4 + abs_score * strong_confidence_boost)
    elif abs_score >= weak_threshold:
        direction = "buy" if score > 0 else "sell"
        confidence = base_confidence + abs_score * weak_confidence_boost
    else:
        direction = "hold"
        confidence = base_confidence

    return direction, round(min(max_confidence, confidence), 2)
