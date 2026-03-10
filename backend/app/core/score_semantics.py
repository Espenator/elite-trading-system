import logging
from typing import Any, Tuple

logger = logging.getLogger(__name__)


def coerce_signal_score_0_100(score: Any, *, context: str = "") -> float:
    """
    Canonicalize signal scores to the system invariant:
      - signal.generated.score is a float in [0, 100]

    Defensive behavior:
      - If score looks normalized (0..1), scale to 0..100 and warn.
      - Clamp out-of-range values with a warning.
    """
    try:
        s = float(score)
    except Exception:
        s = 0.0

    if 0.0 < s <= 1.0:
        logger.warning(
            "%sscore looks normalized (%.4f in 0..1); scaling to 0..100",
            (context + ": ") if context else "",
            s,
        )
        s *= 100.0

    if s < 0.0 or s > 100.0:
        logger.warning(
            "%sscore out of range (%.3f); clamping to 0..100",
            (context + ": ") if context else "",
            s,
        )

    return max(0.0, min(100.0, s))


def coerce_gate_threshold_0_100(threshold: Any, *, context: str = "") -> float:
    """
    Canonicalize gate thresholds to 0..100 scale.
    """
    try:
        t = float(threshold)
    except Exception:
        t = 65.0

    if 0.0 < t <= 1.0:
        logger.warning(
            "%sthreshold looks normalized (%.4f in 0..1); scaling to 0..100",
            (context + ": ") if context else "",
            t,
        )
        t *= 100.0

    return t


def score_to_final_confidence_0_1(score_0_100: Any, *, context: str = "") -> float:
    """
    Map a canonical 0..100 signal score into council.verdict.final_confidence (0..1).
    """
    s = coerce_signal_score_0_100(score_0_100, context=context)
    return max(0.0, min(1.0, s / 100.0))

