"""
NLP sentiment scoring: map text to score 0–100 (neutral 50).
Uses simple lexicon + optional VADER if available.
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Minimal finance-oriented sentiment words (expand as needed)
POSITIVE = {
    "bull",
    "bullish",
    "buy",
    "rally",
    "surge",
    "gain",
    "growth",
    "beat",
    "strong",
    "upgrade",
    "outperform",
    "breakout",
    "moon",
    "long",
    "call",
    "soar",
    "jump",
    "recovery",
    "profit",
    "earnings beat",
    "raised",
    "target raised",
    "up",
}
NEGATIVE = {
    "bear",
    "bearish",
    "sell",
    "crash",
    "drop",
    "loss",
    "weak",
    "miss",
    "downgrade",
    "underperform",
    "breakdown",
    "short",
    "put",
    "plunge",
    "fall",
    "recession",
    "cut",
    "target cut",
    "down",
    "warning",
    "concern",
    "risk",
    "fear",
}


def _tokenize(text: str) -> List[str]:
    if not text or not isinstance(text, str):
        return []
    t = re.sub(r"[^\w\s]", " ", text.lower())
    return t.split()


def score_text_simple(text: str) -> float:
    """
    Return sentiment score in [-1, 1] from word counts (neutral 0).
    Scale to 0–100 in caller: 50 + 50 * score.
    """
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    pos = sum(1 for w in tokens if w in POSITIVE)
    neg = sum(1 for w in tokens if w in NEGATIVE)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def score_text_vader(text: str) -> float:
    """Use VADER if available; return score in [-1, 1]. Otherwise return 0."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        analyzer = SentimentIntensityAnalyzer()
        compound = analyzer.polarity_scores(text or "")["compound"]
        return compound
    except ImportError:
        return 0.0
    except Exception:
        return 0.0


def score_text(text: str, use_vader: bool = True) -> float:
    """
    Combined: try VADER first if use_vader, else use simple lexicon.
    Returns value in [-1, 1].
    """
    if use_vader:
        v = score_text_vader(text)
        if v != 0.0:
            return v
    return score_text_simple(text)


def score_to_0_100(raw: float) -> int:
    """Map [-1, 1] to [0, 100] with 50 neutral."""
    x = max(-1.0, min(1.0, raw))
    return int(50 + 50 * x)
