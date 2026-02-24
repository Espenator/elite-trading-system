"""YouTube Knowledge Agent config: intervals, limits, extraction keywords."""

from pathlib import Path

MAX_VIDEOS_PER_TICK = 2
KNOWLEDGE_MAX_ENTRIES = 500
TRANSCRIPT_LANGUAGES = ["en"]

IDEA_KEYWORDS = [
    "long", "short", "bullish", "bearish", "breakout", "break down",
    "support", "resistance", "target", "stop loss", "take profit",
    "entry", "exit", "swing trade", "day trade", "position", "setup",
    "buy the dip", "sell the rip", "reversal", "continuation",
    "overbought", "oversold", "momentum", "trend", "consolidation",
]

CONCEPT_KEYWORDS = [
    "rsi", "macd", "moving average", "ma ", "ema", "sma",
    "bull flag", "bear flag", "head and shoulders", "double top", "double bottom",
    "fibonacci", "retracement", "vwap", "volume profile", "support level",
    "resistance level", "trendline", "channel", "wedge", "triangle",
    "gap", "gap fill", "iv", "implied volatility", "options flow",
    "put/call", "open interest", "earnings", "catalyst",
]

def _norm(s):
    return (s or "").lower().strip()

IDEA_KEYWORDS_NORM = [_norm(k) for k in IDEA_KEYWORDS]
CONCEPT_KEYWORDS_NORM = [_norm(k) for k in CONCEPT_KEYWORDS]

_AGENT_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = _AGENT_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
