"""
Unusual sentiment spike detection: compare current score to recent history (mean ± threshold * std).
"""

import logging
from typing import List, Tuple, Optional

from app.services.database import db_service
from app.modules.social_news_engine.config import SENTIMENT_HISTORY_LEN, SPIKE_THRESHOLD

logger = logging.getLogger(__name__)

CONFIG_KEY = "social_news_sentiment_history"


def _get_history() -> dict:
    return db_service.get_config(CONFIG_KEY) or {}


def _set_history(data: dict) -> None:
    db_service.set_config(CONFIG_KEY, data)


def append_score(ticker: str, score: int) -> None:
    """Append one score (0–100) for ticker; keep last SENTIMENT_HISTORY_LEN."""
    data = _get_history()
    key = ticker.upper()
    arr = list(data.get(key) or [])
    arr.append(score)
    data[key] = arr[-SENTIMENT_HISTORY_LEN:]
    _set_history(data)


def check_spike(ticker: str, current_score: int) -> Optional[str]:
    """
    If current_score is unusually high or low vs recent history, return direction message.
    Otherwise return None. Uses SPIKE_THRESHOLD (e.g. 1.5) standard deviations.
    """
    data = _get_history()
    arr = data.get(ticker.upper()) or []
    if len(arr) < 5:
        return None
    mean = sum(arr) / len(arr)
    variance = sum((x - mean) ** 2 for x in arr) / len(arr)
    std = variance**0.5 if variance > 0 else 0
    if std < 1:
        return None
    z = (current_score - mean) / std
    if z >= SPIKE_THRESHOLD:
        return "unusual bullish spike"
    if z <= -SPIKE_THRESHOLD:
        return "unusual bearish spike"
    return None
