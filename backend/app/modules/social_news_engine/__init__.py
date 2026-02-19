"""
Social / News Engine — Stockgeist, News API, Discord, X (Twitter).
NLP sentiment per ticker; unusual sentiment spike detection.
"""

import logging
from collections import defaultdict
from typing import List, Tuple

from app.modules.symbol_universe import get_tracked_symbols
from app.modules.social_news_engine.config import (
    DEFAULT_SOURCES,
    MAX_SYMBOLS,
    SPIKE_THRESHOLD,
)
from app.modules.social_news_engine.aggregators import aggregate_all
from app.modules.social_news_engine.sentiment import score_text, score_to_0_100
from app.modules.social_news_engine.spike import append_score, check_spike

logger = logging.getLogger(__name__)

AGENT_NAME = "Sentiment Agent"


def get_status() -> dict:
    """Return engine status (running, last_run, error)."""
    from app.services.database import db_service

    stored = db_service.get_config("social_news_engine_status") or {}
    return {
        "status": stored.get("status", "stopped"),
        "last_run": stored.get("last_run"),
        "error": stored.get("error"),
    }


def run_tick(
    *,
    sources: List[str] = None,
    max_symbols: int = MAX_SYMBOLS,
    use_vader: bool = True,
) -> List[Tuple[str, str]]:
    """
    Run one Sentiment Agent tick: aggregate from sources, NLP score per ticker, spike detection.
    Returns list of (message, level) for activity log.
    """
    sources = sources or DEFAULT_SOURCES
    entries: List[Tuple[str, str]] = []

    symbols = get_tracked_symbols()
    if not symbols:
        entries.append(
            ("No symbols from Symbol Universe — run Market Data Agent first", "warning")
        )
        return entries

    sample = symbols[:max_symbols]
    items = aggregate_all(sample, sources)
    if not items:
        entries.append(
            (
                "No items from aggregators (set API keys for News/Stockgeist/Discord/X)",
                "info",
            )
        )
        return entries

    # Group by ticker and concatenate text for scoring
    by_ticker: dict = defaultdict(list)
    for it in items:
        t = (it.get("ticker") or "").upper().strip()
        if not t:
            continue
        text = it.get("text") or ""
        if text:
            by_ticker[t].append(text)

    scored = []
    for ticker, texts in by_ticker.items():
        combined = " ".join(texts)
        raw = score_text(combined, use_vader=use_vader)
        score = score_to_0_100(raw)
        append_score(ticker, score)
        spike_msg = check_spike(ticker, score)
        scored.append((ticker, score, spike_msg))

    if not scored:
        entries.append(("No tickers with text to score", "info"))
        return entries

    scored.sort(key=lambda x: -x[1])
    top = scored[0]
    entries.append(
        (
            f"Aggregated sentiment for {top[0]}: {top[1]} (Stockgeist + News + X)",
            "success",
        )
    )
    spikes = [s for s in scored if s[2]]
    if spikes:
        for ticker, score, msg in spikes[:3]:
            entries.append(
                (
                    f"Unusual sentiment spike on {ticker}: {msg} (score {score})",
                    "warning",
                )
            )
    entries.append(
        (
            f"NLP sentiment: {len(scored)} tickers from {len(items)} items ({', '.join(sources)})",
            "info",
        )
    )
    return entries
