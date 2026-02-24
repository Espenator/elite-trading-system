"""Social / News Engine config: sources, spike threshold, optional API keys from env."""

from typing import List

# Sources to aggregate (match Agent 4 config)
DEFAULT_SOURCES: List[str] = ["stockgeist", "news_api", "discord", "twitter"]
# Standard deviations above mean to flag as "unusual sentiment spike"
SPIKE_THRESHOLD = 1.5
# Max symbols to score per tick (limit API calls and latency)
MAX_SYMBOLS = 50
# History length per ticker for spike detection (number of past scores to keep)
SENTIMENT_HISTORY_LEN = 20
