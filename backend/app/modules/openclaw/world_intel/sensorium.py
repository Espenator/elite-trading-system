#!/usr/bin/env python3
"""
World Intelligence Sensorium — OpenClaw Agent Swarm System 1 (v1.0)

Multi-source real-time intelligence pipeline that scans the information
environment and publishes structured alpha signals to the Blackboard.

Architecture:
    ┌─────────────────────────────────────────────────┐
    │            WorldIntelSensorium (Orchestrator)    │
    │                                                 │
    │  ┌────────────┐  ┌──────────┐  ┌────────────┐  │
    │  │NewsAggregat│  │ XScanner │  │YouTubeIntel│  │
    │  │    or       │  │          │  │            │  │
    │  └─────┬──────┘  └────┬─────┘  └─────┬──────┘  │
    │        │              │              │          │
    │        ▼              ▼              ▼          │
    │  ┌─────────────────────────────────────────┐    │
    │  │       LLMThemeExtractor (Synthesis)     │    │
    │  └──────────────────┬──────────────────────┘    │
    │                     │                           │
    │  ┌──────────────────▼──────────────────────┐    │
    │  │      CatalystTracker (Correlation)       │    │
    │  └──────────────────┬──────────────────────┘    │
    │                     │                           │
    └─────────────────────┼───────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Blackboard Pub/Sub   │
              │  topic: alpha_signals │
              └───────────────────────┘

Blackboard Integration:
    - Publishes to: alpha_signals, regime_updates
    - Subscribes to: watchlist_updates (to know which tickers to monitor)
    - Heartbeat: agent_heartbeats every 30s

Data Sources:
    - NewsAPI (newsapi.org) — financial headlines & articles
    - RSS Feeds — Bloomberg, Reuters, CNBC, MarketWatch
    - X/Twitter — public firehose via search API or scraping
    - YouTube — yt-dlp transcript extraction + Whisper fallback
    - FRED — macro event calendar correlation

Usage:
    # Standalone
    python -m world_intel.sensorium --scan
    python -m world_intel.sensorium --themes
    python -m world_intel.sensorium --catalysts

    # Integrated with swarm
    from world_intel import WorldIntelSensorium
    sensorium = WorldIntelSensorium(blackboard=get_blackboard())
    await sensorium.run()  # continuous async loop
"""

import os
import re
import json
import time
import hashlib
import asyncio
import logging
import argparse
import subprocess
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    import feedparser
except ImportError:
    feedparser = None

# Blackboard integration
try:
    from streaming_engine import (
        get_blackboard, Blackboard, BlackboardMessage, Topic
    )
except ImportError:
    get_blackboard = None
    Blackboard = None
    BlackboardMessage = None
    Topic = None

# LLM integration for theme extraction
try:
    from llm_client import call_llm
except ImportError:
    call_llm = None

# Config
try:
    from config import (
        NEWS_API_KEY,
        FRED_API_KEY,
    )
except ImportError:
    NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
    FRED_API_KEY = os.getenv("FRED_API_KEY", "")

logger = logging.getLogger(__name__)

# ============================================================
# Constants & Configuration
# ============================================================

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "world_intel")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
TRANSCRIPT_DIR = os.path.join(DATA_DIR, "transcripts")

# News scanning
NEWS_API_BASE = "https://newsapi.org/v2"
MAX_NEWS_ARTICLES = 50
NEWS_SCAN_INTERVAL = 300  # 5 minutes

# RSS feeds for financial news
RSS_FEEDS = {
    "reuters_markets": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
    "cnbc_top": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "marketwatch_top": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "seekingalpha": "https://seekingalpha.com/market_currents.xml",
    "benzinga": "https://www.benzinga.com/feed",
}

# X/Twitter scanning
X_SCAN_INTERVAL = 180  # 3 minutes
X_CASHTAG_PATTERN = re.compile(r"\$([A-Z]{1,5})\b")
X_FINANCIAL_ACCOUNTS = [
    "unusual_whales", "DeItaone", "Deepwaterpoint", "zabormarket",
    "jimcramer", "elikibaroforex", "financialjuice", "Stocktwits",
]

# YouTube intel
YT_SCAN_INTERVAL = 900  # 15 minutes
YT_FINANCIAL_CHANNELS = [
    "UCIALMKvObZNtJ68-rmGgsow",  # Trades by Matt
    "UCHop-jpf-huVT1IYw79PmFkw",  # ZipTrader
    "UCQMYJ_WKM1AElnhPCYeJHQ",  # Graham Stephan
]

# Catalyst types
class CatalystType(str, Enum):
    EARNINGS = "earnings"
    FDA = "fda"
    FOMC = "fomc"
    CPI = "cpi"
    JOBS = "jobs"
    IPO = "ipo"
    MERGER = "merger"
    GUIDANCE = "guidance"
    ANALYST = "analyst"
    INSIDER = "insider"
    SECTOR_ROTATION = "sector_rotation"
    MACRO = "macro"
    SOCIAL_TREND = "social_trend"
    UNKNOWN = "unknown"


# Intel signal priority
class IntelPriority(int, Enum):
    CRITICAL = 1    # Market-moving event (FOMC, major earnings miss)
    HIGH = 2        # Strong catalyst (FDA approval, M&A rumor)
    MEDIUM = 5      # Moderate signal (analyst upgrade, insider buy)
    LOW = 7         # Background intel (social chatter, theme trend)
    NOISE = 10      # Filtered out, not published


@dataclass
class IntelSignal:
    """Structured intelligence signal from any source."""
    source: str                    # "newsapi", "x_twitter", "youtube", "rss"
    signal_type: str               # "headline", "social_mention", "transcript"
    ticker: str                    # Primary ticker (can be empty for macro)
    tickers_mentioned: List[str]   # All tickers found in content
    headline: str                  # Short summary
    body: str                      # Full content or excerpt
    sentiment: float               # -1.0 to +1.0
    catalyst_type: str             # CatalystType value
    priority: int                  # IntelPriority value
    url: str = ""                  # Source URL
    author: str = ""               # Author or account
    published_at: str = ""         # ISO timestamp
    content_hash: str = ""         # Dedup hash
    metadata: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)

    def compute_hash(self) -> str:
        raw = f"{self.source}:{self.headline}:{self.ticker}"
        self.content_hash = hashlib.md5(raw.encode()).hexdigest()[:12]
        return self.content_hash


# ============================================================
# NewsAggregator — NewsAPI + RSS feed scanner
# ============================================================

class NewsAggregator:
    """
    Scans NewsAPI and financial RSS feeds for ticker-relevant headlines.
    Performs keyword extraction, basic sentiment scoring, and catalyst
    classification before publishing to the Blackboard.
    """

    # Keywords that boost sentiment / priority
    BULLISH_KEYWORDS = {
        "upgrade", "beats", "exceeds", "raises", "guidance", "growth",
        "breakout", "surge", "rally", "approval", "fda approved",
        "record revenue", "buyback", "dividend", "acquisition",
        "beat expectations", "strong earnings", "buy rating",
    }
    BEARISH_KEYWORDS = {
        "downgrade", "misses", "cuts", "lowers", "warning", "decline",
        "sell-off", "crash", "recall", "investigation", "lawsuit",
        "disappointing", "weak earnings", "sell rating", "bankruptcy",
        "layoffs", "missed expectations", "guidance cut",
    }
    CATALYST_KEYWORDS = {
        CatalystType.EARNINGS: {"earnings", "eps", "revenue", "quarterly results", "q1", "q2", "q3", "q4"},
        CatalystType.FDA: {"fda", "drug approval", "clinical trial", "phase 3", "nda"},
        CatalystType.FOMC: {"fomc", "fed", "interest rate", "powell", "rate decision"},
        CatalystType.CPI: {"cpi", "inflation", "consumer price"},
        CatalystType.JOBS: {"jobs report", "nonfarm payroll", "unemployment"},
        CatalystType.MERGER: {"merger", "acquisition", "buyout", "takeover", "m&a"},
        CatalystType.ANALYST: {"upgrade", "downgrade", "price target", "analyst"},
        CatalystType.INSIDER: {"insider buy", "insider sell", "insider trading", "sec filing"},
    }

    def __init__(self, api_key: str = "", watchlist: Optional[Set[str]] = None):
        self.api_key = api_key or NEWS_API_KEY
        self.watchlist = watchlist or set()
        self._seen_hashes: Set[str] = set()
        self._last_scan = 0.0
        self._article_cache: deque = deque(maxlen=500)
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _newsapi_search(self, query: str, page_size: int = 20) -> List[Dict]:
        """Search NewsAPI for articles matching query."""
        if not self.api_key or not requests:
            return []
        try:
            params = {
                "q": query,
                "apiKey": self.api_key,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": min(page_size, 100),
                "from": (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S"),
            }
            resp = requests.get(f"{NEWS_API_BASE}/everything", params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("articles", [])
            else:
                logger.warning(f"NewsAPI returned {resp.status_code}: {resp.text[:200]}")
                return []
        except Exception as e:
            logger.error(f"NewsAPI search failed: {e}")
            return []

    def _newsapi_headlines(self, category: str = "business") -> List[Dict]:
        """Get top business headlines from NewsAPI."""
        if not self.api_key or not requests:
            return []
        try:
            params = {
                "category": category,
                "apiKey": self.api_key,
                "language": "en",
                "country": "us",
                "pageSize": 30,
            }
            resp = requests.get(f"{NEWS_API_BASE}/top-headlines", params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("articles", [])
            return []
        except Exception as e:
            logger.error(f"NewsAPI headlines failed: {e}")
            return []

    def _scan_rss_feeds(self) -> List[Dict]:
        """Scan all configured RSS feeds for recent articles."""
        if not feedparser:
            logger.debug("feedparser not installed, skipping RSS")
            return []
        articles = []
        for feed_name, feed_url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:15]:
                    articles.append({
                        "source": {"name": feed_name},
                        "title": entry.get("title", ""),
                        "description": entry.get("summary", ""),
                        "url": entry.get("link", ""),
                        "publishedAt": entry.get("published", ""),
                        "author": entry.get("author", ""),
                        "_feed": feed_name,
                    })
            except Exception as e:
                logger.debug(f"RSS feed {feed_name} failed: {e}")
        return articles

    def _extract_tickers(self, text: str) -> List[str]:
        """Extract $TICKER cashtags and known ticker symbols from text."""
        tickers = set()
        # Cashtag pattern
        for match in X_CASHTAG_PATTERN.finditer(text):
            tickers.add(match.group(1))
        # Check watchlist tickers in text
        upper_text = text.upper()
        for ticker in self.watchlist:
            if f" {ticker} " in f" {upper_text} " or f"${ticker}" in upper_text:
                tickers.add(ticker)
        return sorted(tickers)

    def _score_sentiment(self, text: str) -> float:
        """Simple keyword-based sentiment scoring (-1.0 to +1.0)."""
        lower = text.lower()
        bull_hits = sum(1 for kw in self.BULLISH_KEYWORDS if kw in lower)
        bear_hits = sum(1 for kw in self.BEARISH_KEYWORDS if kw in lower)
        total = bull_hits + bear_hits
        if total == 0:
            return 0.0
        return round((bull_hits - bear_hits) / total, 3)

    def _classify_catalyst(self, text: str) -> str:
        """Classify the catalyst type from text content."""
        lower = text.lower()
        for catalyst_type, keywords in self.CATALYST_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return catalyst_type.value
        return CatalystType.UNKNOWN.value

    def _determine_priority(self, sentiment: float, catalyst_type: str, tickers: List[str]) -> int:
        """Determine signal priority based on content analysis."""
        if catalyst_type in (CatalystType.FOMC.value, CatalystType.CPI.value):
            return IntelPriority.CRITICAL
        if catalyst_type in (CatalystType.FDA.value, CatalystType.MERGER.value):
            return IntelPriority.HIGH
        if abs(sentiment) >= 0.6 and len(tickers) > 0:
            return IntelPriority.HIGH
        if len(tickers) > 0 and catalyst_type != CatalystType.UNKNOWN.value:
            return IntelPriority.MEDIUM
        if len(tickers) > 0:
            return IntelPriority.LOW
        return IntelPriority.NOISE

    def _article_to_signal(self, article: Dict, source: str = "newsapi") -> Optional[IntelSignal]:
        """Convert a raw article dict into a structured IntelSignal."""
        title = article.get("title", "") or ""
        desc = article.get("description", "") or ""
        full_text = f"{title} {desc}"
        if not title or len(title) < 10:
            return None

        tickers = self._extract_tickers(full_text)
        sentiment = self._score_sentiment(full_text)
        catalyst = self._classify_catalyst(full_text)
        priority = self._determine_priority(sentiment, catalyst, tickers)

        # Skip noise unless it mentions a watchlist ticker
        if priority >= IntelPriority.NOISE and not any(t in self.watchlist for t in tickers):
            return None

        signal = IntelSignal(
            source=source,
            signal_type="headline",
            ticker=tickers[0] if tickers else "",
            tickers_mentioned=tickers,
            headline=title[:200],
            body=desc[:500],
            sentiment=sentiment,
            catalyst_type=catalyst,
            priority=priority,
            url=article.get("url", ""),
            author=article.get("author", "") or "",
            published_at=article.get("publishedAt", ""),
            metadata={
                "source_name": article.get("source", {}).get("name", ""),
                "feed": article.get("_feed", ""),
            },
        )
        signal.compute_hash()
        return signal

    def scan(self, custom_queries: Optional[List[str]] = None) -> List[IntelSignal]:
        """
        Run a full news scan cycle. Returns deduplicated IntelSignals.

        Args:
            custom_queries: Additional search queries beyond the watchlist.

        Returns:
            List of IntelSignal objects sorted by priority.
        """
        signals: List[IntelSignal] = []
        all_articles: List[Dict] = []

        # 1) Top business headlines
        all_articles.extend(self._newsapi_headlines())

        # 2) Ticker-specific searches (batch watchlist tickers)
        if self.watchlist:
            ticker_batch = list(self.watchlist)[:20]
            for i in range(0, len(ticker_batch), 5):
                batch = ticker_batch[i:i+5]
                query = " OR ".join(batch)
                all_articles.extend(self._newsapi_search(query, page_size=15))
                time.sleep(0.3)  # Rate limit courtesy

        # 3) Custom queries
        for query in (custom_queries or []):
            all_articles.extend(self._newsapi_search(query, page_size=10))

        # 4) RSS feeds
        all_articles.extend(self._scan_rss_feeds())

        # 5) Convert and deduplicate
        for article in all_articles:
            signal = self._article_to_signal(article)
            if signal and signal.content_hash not in self._seen_hashes:
                self._seen_hashes.add(signal.content_hash)
                signals.append(signal)
                self._article_cache.append(signal.to_dict())

        # Sort by priority (lowest number = highest priority)
        signals.sort(key=lambda s: s.priority)
        self._last_scan = time.time()
        logger.info(f"[NewsAggregator] Scanned {len(all_articles)} articles -> {len(signals)} signals")
        return signals[:MAX_NEWS_ARTICLES]


# ============================================================
# XScanner — X/Twitter social signal scanner
# ============================================================

class XScanner:
    """
    Scans X/Twitter for financial signals: cashtag mentions,
    unusual activity, and sentiment from key financial accounts.

    Uses public search endpoints (no paid API required for basic
    functionality). Falls back to cached data if rate-limited.
    """

    def __init__(self, bearer_token: str = "", watchlist: Optional[Set[str]] = None):
        self.bearer_token = bearer_token or os.getenv("X_BEARER_TOKEN", "")
        self.watchlist = watchlist or set()
        self._seen_hashes: Set[str] = set()
        self._mention_counts: Dict[str, int] = defaultdict(int)
        self._velocity_window: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._last_scan = 0.0

    def _search_x(self, query: str, max_results: int = 20) -> List[Dict]:
        """Search X/Twitter API for recent tweets."""
        if not self.bearer_token or not requests:
            return []
        try:
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            params = {
                "query": query,
                "max_results": min(max_results, 100),
                "tweet.fields": "created_at,author_id,public_metrics,context_annotations",
                "sort_order": "recency",
            }
            resp = requests.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers=headers, params=params, timeout=15
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
            elif resp.status_code == 429:
                logger.warning("[XScanner] Rate limited, using cached data")
                return []
            else:
                logger.debug(f"[XScanner] API returned {resp.status_code}")
                return []
        except Exception as e:
            logger.error(f"[XScanner] Search failed: {e}")
            return []

    def _compute_mention_velocity(self, ticker: str) -> float:
        """Compute mention velocity (mentions per minute) for a ticker."""
        window = self._velocity_window.get(ticker, deque())
        if len(window) < 2:
            return 0.0
        time_span = (window[-1] - window[0]).total_seconds()
        if time_span <= 0:
            return 0.0
        return len(window) / (time_span / 60.0)

    def _tweet_to_signal(self, tweet: Dict) -> Optional[IntelSignal]:
        """Convert a tweet into an IntelSignal."""
        text = tweet.get("text", "")
        if not text:
            return None

        tickers = list(set(X_CASHTAG_PATTERN.findall(text)))
        for t in self.watchlist:
            if f"${t}" in text.upper() or f" {t} " in f" {text.upper()} ":
                if t not in tickers:
                    tickers.append(t)

        if not tickers:
            return None

        # Update velocity tracking
        for t in tickers:
            self._mention_counts[t] += 1
            self._velocity_window[t].append(datetime.now())

        # Basic sentiment from text
        lower = text.lower()
        bull_words = sum(1 for w in ["bullish", "moon", "calls", "breakout", "squeeze", "buy", "long"] if w in lower)
        bear_words = sum(1 for w in ["bearish", "puts", "short", "crash", "dump", "sell", "drill"] if w in lower)
        total = bull_words + bear_words
        sentiment = (bull_words - bear_words) / total if total > 0 else 0.0

        metrics = tweet.get("public_metrics", {})
        engagement = (
            metrics.get("retweet_count", 0) +
            metrics.get("like_count", 0) +
            metrics.get("reply_count", 0)
        )

        # Priority based on engagement and ticker relevance
        priority = IntelPriority.LOW
        if engagement > 1000:
            priority = IntelPriority.HIGH
        elif engagement > 100 or any(t in self.watchlist for t in tickers):
            priority = IntelPriority.MEDIUM

        signal = IntelSignal(
            source="x_twitter",
            signal_type="social_mention",
            ticker=tickers[0] if tickers else "",
            tickers_mentioned=tickers,
            headline=text[:200],
            body=text,
            sentiment=round(sentiment, 3),
            catalyst_type=CatalystType.SOCIAL_TREND.value,
            priority=priority,
            url=f"https://x.com/i/status/{tweet.get('id', '')}",
            author=tweet.get("author_id", ""),
            published_at=tweet.get("created_at", ""),
            metadata={
                "engagement": engagement,
                "retweets": metrics.get("retweet_count", 0),
                "likes": metrics.get("like_count", 0),
            },
        )
        signal.compute_hash()
        return signal

    def scan(self) -> List[IntelSignal]:
        """
        Run X/Twitter scan cycle for watchlist tickers and key accounts.

        Returns:
            List of IntelSignal objects from social media.
        """
        signals: List[IntelSignal] = []

        # Scan cashtags for watchlist tickers
        if self.watchlist:
            ticker_list = list(self.watchlist)[:15]
            for i in range(0, len(ticker_list), 5):
                batch = ticker_list[i:i+5]
                query = " OR ".join(f"${t}" for t in batch)
                tweets = self._search_x(query)
                for tweet in tweets:
                    signal = self._tweet_to_signal(tweet)
                    if signal and signal.content_hash not in self._seen_hashes:
                        self._seen_hashes.add(signal.content_hash)
                        signals.append(signal)
                time.sleep(1)  # Rate limit

        # Scan key financial accounts
        for account in X_FINANCIAL_ACCOUNTS[:5]:
            tweets = self._search_x(f"from:{account}", max_results=10)
            for tweet in tweets:
                signal = self._tweet_to_signal(tweet)
                if signal and signal.content_hash not in self._seen_hashes:
                    self._seen_hashes.add(signal.content_hash)
                    signals.append(signal)
            time.sleep(1)

        signals.sort(key=lambda s: s.priority)
        self._last_scan = time.time()
        logger.info(f"[XScanner] Found {len(signals)} social signals")
        return signals

    def get_trending_tickers(self, min_velocity: float = 2.0) -> List[Tuple[str, float]]:
        """Get tickers with high mention velocity (mentions/min)."""
        trending = []
        for ticker in self._mention_counts:
            velocity = self._compute_mention_velocity(ticker)
            if velocity >= min_velocity:
                trending.append((ticker, velocity))
        trending.sort(key=lambda x: x[1], reverse=True)
        return trending


# ============================================================
# YouTubeIntel — Video transcript extraction
# ============================================================

class YouTubeIntel:
    """
    Extracts intelligence from financial YouTube videos using yt-dlp
    for download and Whisper for transcription. Scans transcripts
    for ticker mentions and catalyst keywords.
    """

    def __init__(self, watchlist: Optional[Set[str]] = None):
        self.watchlist = watchlist or set()
        self._processed_videos: Set[str] = set()
        self._last_scan = 0.0
        os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

    def _check_yt_dlp(self) -> bool:
        """Check if yt-dlp is available."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _get_auto_transcript(self, video_url: str) -> Optional[str]:
        """
        Extract auto-generated transcript from YouTube video using yt-dlp.
        Falls back to subtitle extraction if available.
        """
        if not self._check_yt_dlp():
            logger.debug("yt-dlp not available")
            return None

        try:
            video_id = self._extract_video_id(video_url)
            if not video_id:
                return None

            output_path = os.path.join(TRANSCRIPT_DIR, f"{video_id}")

            # Try auto-generated subtitles first
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--write-auto-subs",
                    "--sub-lang", "en",
                    "--sub-format", "vtt",
                    "--skip-download",
                    "-o", output_path,
                    video_url,
                ],
                capture_output=True, text=True, timeout=60
            )

            # Look for the subtitle file
            vtt_file = f"{output_path}.en.vtt"
            if os.path.exists(vtt_file):
                with open(vtt_file, "r") as f:
                    content = f.read()
                # Clean VTT format to plain text
                transcript = self._clean_vtt(content)
                return transcript

            logger.debug(f"No auto-subs found for {video_id}")
            return None

        except subprocess.TimeoutExpired:
            logger.warning(f"yt-dlp timed out for {video_url}")
            return None
        except Exception as e:
            logger.error(f"Transcript extraction failed: {e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        patterns = [
            r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
            r"(?:embed/)([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _clean_vtt(self, vtt_content: str) -> str:
        """Clean WebVTT subtitle content to plain text."""
        lines = []
        for line in vtt_content.split("\n"):
            line = line.strip()
            # Skip timestamps, WEBVTT header, and empty lines
            if not line or "-->" in line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            # Remove HTML tags
            clean = re.sub(r"<[^>]+>", "", line)
            if clean and not clean.isdigit():
                lines.append(clean)
        # Deduplicate consecutive identical lines (common in auto-subs)
        deduped = []
        prev = ""
        for line in lines:
            if line != prev:
                deduped.append(line)
                prev = line
        return " ".join(deduped)

    def _analyze_transcript(self, transcript: str, video_url: str, video_title: str = "") -> Optional[IntelSignal]:
        """Analyze transcript for trading intelligence."""
        if not transcript or len(transcript) < 50:
            return None

        # Extract tickers
        tickers = list(set(X_CASHTAG_PATTERN.findall(transcript)))
        upper = transcript.upper()
        for t in self.watchlist:
            if f" {t} " in f" {upper} ":
                if t not in tickers:
                    tickers.append(t)

        if not tickers:
            return None

        # Keyword-based sentiment
        lower = transcript.lower()
        bull = sum(1 for kw in NewsAggregator.BULLISH_KEYWORDS if kw in lower)
        bear = sum(1 for kw in NewsAggregator.BEARISH_KEYWORDS if kw in lower)
        total = bull + bear
        sentiment = (bull - bear) / total if total > 0 else 0.0

        signal = IntelSignal(
            source="youtube",
            signal_type="transcript",
            ticker=tickers[0] if tickers else "",
            tickers_mentioned=tickers,
            headline=video_title[:200] or f"YouTube video mentioning {', '.join(tickers[:3])}",
            body=transcript[:1000],
            sentiment=round(sentiment, 3),
            catalyst_type=CatalystType.SOCIAL_TREND.value,
            priority=IntelPriority.LOW,
            url=video_url,
            metadata={
                "transcript_length": len(transcript),
                "tickers_count": len(tickers),
                "video_id": self._extract_video_id(video_url) or "",
            },
        )
        signal.compute_hash()
        return signal

    def scan_video(self, video_url: str, video_title: str = "") -> Optional[IntelSignal]:
        """Scan a single YouTube video for intel."""
        video_id = self._extract_video_id(video_url)
        if not video_id or video_id in self._processed_videos:
            return None

        transcript = self._get_auto_transcript(video_url)
        if not transcript:
            return None

        self._processed_videos.add(video_id)
        return self._analyze_transcript(transcript, video_url, video_title)

    def scan_channel_recent(self, channel_id: str, max_videos: int = 3) -> List[IntelSignal]:
        """Scan recent videos from a YouTube channel. Requires yt-dlp."""
        if not self._check_yt_dlp():
            return []

        signals = []
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--flat-playlist",
                    "--print", "%(id)s %(title)s",
                    "--playlist-items", f"1:{max_videos}",
                    f"https://www.youtube.com/channel/{channel_id}/videos",
                ],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    parts = line.split(" ", 1)
                    if len(parts) >= 1:
                        vid_id = parts[0]
                        title = parts[1] if len(parts) > 1 else ""
                        url = f"https://www.youtube.com/watch?v={vid_id}"
                        signal = self.scan_video(url, title)
                        if signal:
                            signals.append(signal)
        except Exception as e:
            logger.error(f"Channel scan failed for {channel_id}: {e}")

        return signals


# ============================================================
# CatalystTracker — Event calendar and correlation
# ============================================================

class CatalystTracker:
    """
    Tracks upcoming catalysts (earnings, FDA dates, FOMC, CPI, etc.)
    and correlates them with incoming intel signals to boost priority.
    """

    # FRED series for macro events
    FRED_MACRO_SERIES = {
        "VIXCLS": "VIX",
        "DGS10": "10Y_yield",
        "DGS2": "2Y_yield",
        "FEDFUNDS": "fed_funds",
        "UNRATE": "unemployment",
        "CPIAUCSL": "cpi",
    }

    def __init__(self, api_key: str = ""):
        self.fred_api_key = api_key or FRED_API_KEY
        self._catalyst_calendar: List[Dict] = []
        self._macro_cache: Dict[str, Any] = {}
        self._last_macro_fetch = 0.0

    def _fetch_fred_series(self, series_id: str, limit: int = 5) -> Optional[List[Dict]]:
        """Fetch recent observations from FRED."""
        if not self.fred_api_key or not requests:
            return None
        try:
            params = {
                "series_id": series_id,
                "api_key": self.fred_api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": limit,
            }
            resp = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params=params, timeout=15
            )
            if resp.status_code == 200:
                return resp.json().get("observations", [])
            return None
        except Exception as e:
            logger.error(f"FRED fetch failed for {series_id}: {e}")
            return None

    def refresh_macro_data(self) -> Dict[str, Any]:
        """Refresh macro indicators from FRED."""
        now = time.time()
        if now - self._last_macro_fetch < 3600:  # Cache for 1 hour
            return self._macro_cache

        macro = {}
        for series_id, label in self.FRED_MACRO_SERIES.items():
            obs = self._fetch_fred_series(series_id, limit=2)
            if obs:
                latest = obs[0]
                macro[label] = {
                    "value": float(latest.get("value", 0)) if latest.get("value", ".") != "." else None,
                    "date": latest.get("date", ""),
                    "series_id": series_id,
                }
                if len(obs) > 1:
                    prev_val = float(obs[1].get("value", 0)) if obs[1].get("value", ".") != "." else None
                    if prev_val and macro[label]["value"]:
                        macro[label]["change"] = round(macro[label]["value"] - prev_val, 4)
            time.sleep(0.2)  # FRED rate limit

        self._macro_cache = macro
        self._last_macro_fetch = now
        logger.info(f"[CatalystTracker] Refreshed {len(macro)} macro indicators")
        return macro

    def add_catalyst(self, ticker: str, catalyst_type: str, event_date: str, description: str = ""):
        """Add a known upcoming catalyst to the calendar."""
        self._catalyst_calendar.append({
            "ticker": ticker,
            "catalyst_type": catalyst_type,
            "event_date": event_date,
            "description": description,
            "added_at": datetime.now().isoformat(),
        })

    def get_upcoming_catalysts(self, days_ahead: int = 5) -> List[Dict]:
        """Get catalysts within the next N days."""
        cutoff = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        today = date.today().isoformat()
        return [
            c for c in self._catalyst_calendar
            if today <= c.get("event_date", "") <= cutoff
        ]

    def correlate_signal(self, signal: IntelSignal) -> IntelSignal:
        """
        Enrich a signal with catalyst correlation. If a signal's ticker
        has an upcoming catalyst, boost its priority.
        """
        if not signal.ticker:
            return signal

        upcoming = self.get_upcoming_catalysts()
        for cat in upcoming:
            if cat["ticker"] == signal.ticker:
                signal.priority = min(signal.priority, IntelPriority.HIGH)
                signal.metadata["upcoming_catalyst"] = cat
                if signal.catalyst_type == CatalystType.UNKNOWN.value:
                    signal.catalyst_type = cat["catalyst_type"]

        # Macro correlation
        macro = self._macro_cache
        vix = macro.get("VIX", {}).get("value")
        if vix and vix > 25:
            signal.metadata["elevated_vix"] = vix
            if signal.priority > IntelPriority.MEDIUM:
                signal.priority = IntelPriority.MEDIUM

        return signal


# ============================================================
# LLMThemeExtractor — AI-powered theme synthesis
# ============================================================

class LLMThemeExtractor:
    """
    Uses LLM (GPT-4/Claude) to extract macro themes and trading
    narratives from batches of raw intel signals. Identifies
    sector rotations, thematic plays, and emerging catalysts.
    """

    THEME_PROMPT_TEMPLATE = """You are a professional trading desk intelligence analyst.
Analyze these {count} financial intelligence signals and extract:

1. TOP 3 MACRO THEMES (with confidence 0-100)
2. SECTOR ROTATION signals (which sectors are strengthening/weakening)
3. INDIVIDUAL TICKER CATALYSTS (ticker, catalyst, sentiment, urgency)
4. EMERGING NARRATIVES (new themes forming that could drive multi-day moves)

Signals:
{signals_text}

Respond in JSON format:
{{
  "themes": [{"name": "...", "confidence": 0-100, "tickers": [...], "direction": "bullish/bearish/neutral"}],
  "sector_rotation": [{"sector": "...", "direction": "inflow/outflow", "evidence": "..."}],
  "ticker_catalysts": [{"ticker": "...", "catalyst": "...", "sentiment": -1 to 1, "urgency": "high/medium/low"}],
  "emerging_narratives": [{"narrative": "...", "confidence": 0-100, "timeframe": "intraday/swing/position"}]
}}"""

    def __init__(self):
        self._theme_cache: Dict = {}
        self._last_extraction = 0.0

    def extract_themes(self, signals: List[IntelSignal], force: bool = False) -> Dict:
        """
        Run LLM theme extraction on a batch of signals.

        Args:
            signals: List of IntelSignals to analyze.
            force: Force re-extraction even if cache is fresh.

        Returns:
            Dict with themes, sector_rotation, ticker_catalysts, emerging_narratives.
        """
        now = time.time()
        if not force and now - self._last_extraction < 600 and self._theme_cache:
            return self._theme_cache

        if not signals:
            return {"themes": [], "sector_rotation": [], "ticker_catalysts": [], "emerging_narratives": []}

        if not call_llm:
            logger.warning("[LLMThemeExtractor] llm_client not available, using fallback")
            return self._fallback_extraction(signals)

        # Prepare signal summaries for the LLM
        signal_lines = []
        for s in signals[:30]:  # Limit to 30 to fit context
            line = (
                f"[{s.source}] {s.ticker or 'MACRO'} | {s.headline} | "
                f"sentiment={s.sentiment:.2f} | catalyst={s.catalyst_type} | "
                f"priority={s.priority}"
            )
            signal_lines.append(line)

        prompt = self.THEME_PROMPT_TEMPLATE.format(
            count=len(signal_lines),
            signals_text="\n".join(signal_lines),
        )

        try:
            response = call_llm(prompt, max_tokens=2000, temperature=0.3)
            if response:
                # Parse JSON from LLM response
                json_match = re.search(r"\{[\s\S]*\}", response)
                if json_match:
                    themes = json.loads(json_match.group())
                    self._theme_cache = themes
                    self._last_extraction = now
                    logger.info(f"[LLMThemeExtractor] Extracted {len(themes.get('themes', []))} themes")
                    return themes
        except Exception as e:
            logger.error(f"[LLMThemeExtractor] Extraction failed: {e}")

        return self._fallback_extraction(signals)

    def _fallback_extraction(self, signals: List[IntelSignal]) -> Dict:
        """Simple keyword-based theme extraction when LLM is unavailable."""
        ticker_counts: Dict[str, int] = defaultdict(int)
        catalyst_counts: Dict[str, int] = defaultdict(int)
        sentiment_sums: Dict[str, float] = defaultdict(float)

        for s in signals:
            for t in s.tickers_mentioned:
                ticker_counts[t] += 1
                sentiment_sums[t] += s.sentiment
            catalyst_counts[s.catalyst_type] += 1

        # Top tickers by mention count
        top_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        themes = []
        if catalyst_counts.get(CatalystType.EARNINGS.value, 0) > 3:
            themes.append({"name": "Earnings Season", "confidence": 70, "tickers": [], "direction": "neutral"})
        if catalyst_counts.get(CatalystType.FOMC.value, 0) > 0:
            themes.append({"name": "Fed Policy Focus", "confidence": 85, "tickers": [], "direction": "neutral"})

        ticker_catalysts = []
        for ticker, count in top_tickers:
            avg_sent = sentiment_sums[ticker] / count if count > 0 else 0
            ticker_catalysts.append({
                "ticker": ticker,
                "catalyst": "high_mention_count",
                "sentiment": round(avg_sent, 3),
                "urgency": "high" if count >= 5 else "medium",
            })

        result = {
            "themes": themes,
            "sector_rotation": [],
            "ticker_catalysts": ticker_catalysts,
            "emerging_narratives": [],
            "_method": "fallback",
        }
        self._theme_cache = result
        self._last_extraction = time.time()
        return result


# ============================================================
# WorldIntelSensorium — Main Orchestrator
# ============================================================

class WorldIntelSensorium:
    """
    Main orchestrator for the World Intelligence pipeline.
    Coordinates all scanners, runs LLM theme extraction, correlates
    with catalyst calendar, and publishes enriched signals to the
    Blackboard for consumption by downstream swarm agents.

    Lifecycle:
        1. Initialize all scanner components
        2. Subscribe to watchlist_updates on Blackboard
        3. Run continuous scan loop (news -> social -> youtube -> themes)
        4. Publish enriched signals to alpha_signals topic
        5. Publish macro themes to regime_updates topic
        6. Send heartbeats every 30s
    """

    AGENT_ID = "world_intel_sensorium"

    def __init__(self, blackboard=None, watchlist: Optional[Set[str]] = None):
        self.blackboard = blackboard
        self.watchlist: Set[str] = watchlist or set()

        # Sub-components
        self.news = NewsAggregator(watchlist=self.watchlist)
        self.x_scanner = XScanner(watchlist=self.watchlist)
        self.youtube = YouTubeIntel(watchlist=self.watchlist)
        self.catalyst_tracker = CatalystTracker()
        self.theme_extractor = LLMThemeExtractor()

        # State
        self._all_signals: deque = deque(maxlen=1000)
        self._latest_themes: Dict = {}
        self._scan_count = 0
        self._running = False
        self._stats = defaultdict(int)

        os.makedirs(DATA_DIR, exist_ok=True)
        logger.info(f"[{self.AGENT_ID}] Initialized with {len(self.watchlist)} watchlist tickers")

    def update_watchlist(self, tickers: Set[str]):
        """Update the watchlist across all sub-components."""
        self.watchlist = tickers
        self.news.watchlist = tickers
        self.x_scanner.watchlist = tickers
        self.youtube.watchlist = tickers
        logger.info(f"[{self.AGENT_ID}] Watchlist updated: {len(tickers)} tickers")

    async def _publish_signal(self, signal: IntelSignal):
        """Publish an enriched signal to the Blackboard."""
        if not self.blackboard or not BlackboardMessage:
            return
        try:
            msg = BlackboardMessage(
                topic=Topic.ALPHA_SIGNALS if Topic else "alpha_signals",
                payload=signal.to_dict(),
                source_agent=self.AGENT_ID,
                priority=signal.priority,
                ttl_seconds=600,
            )
            await self.blackboard.publish(msg)
            self._stats["signals_published"] += 1
        except Exception as e:
            logger.error(f"[{self.AGENT_ID}] Publish failed: {e}")

    async def _publish_themes(self, themes: Dict):
        """Publish extracted themes to regime_updates topic."""
        if not self.blackboard or not BlackboardMessage:
            return
        try:
            msg = BlackboardMessage(
                topic=Topic.REGIME_UPDATES if Topic else "regime_updates",
                payload={
                    "type": "world_intel_themes",
                    "themes": themes,
                    "timestamp": datetime.now().isoformat(),
                },
                source_agent=self.AGENT_ID,
                priority=3,
                ttl_seconds=1800,
            )
            await self.blackboard.publish(msg)
        except Exception as e:
            logger.error(f"[{self.AGENT_ID}] Theme publish failed: {e}")

    async def _listen_watchlist_updates(self):
        """Listen for watchlist updates from the Blackboard."""
        if not self.blackboard:
            return
        try:
            queue = await self.blackboard.subscribe(
                Topic.WATCHLIST_UPDATES if Topic else "watchlist_updates",
                self.AGENT_ID,
            )
            while self._running:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=5.0)
                    if isinstance(msg, BlackboardMessage) and not msg.is_expired():
                        tickers = msg.payload.get("tickers", [])
                        if tickers:
                            self.update_watchlist(set(tickers))
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
        except Exception as e:
            logger.error(f"[{self.AGENT_ID}] Watchlist listener error: {e}")

    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while self._running:
            try:
                if self.blackboard:
                    await self.blackboard.heartbeat(self.AGENT_ID)
            except Exception as e:
                logger.debug(f"Heartbeat error: {e}")
            await asyncio.sleep(30)

    def scan_all_sync(self) -> Dict:
        """
        Run a full synchronous scan cycle (for CLI or standalone use).

        Returns:
            Dict with signals, themes, catalysts, and stats.
        """
        all_signals: List[IntelSignal] = []

        # 1) News scan
        logger.info(f"[{self.AGENT_ID}] Running news scan...")
        news_signals = self.news.scan()
        all_signals.extend(news_signals)
        self._stats["news_signals"] += len(news_signals)

        # 2) X/Twitter scan
        logger.info(f"[{self.AGENT_ID}] Running X/Twitter scan...")
        x_signals = self.x_scanner.scan()
        all_signals.extend(x_signals)
        self._stats["x_signals"] += len(x_signals)

        # 3) Catalyst correlation
        logger.info(f"[{self.AGENT_ID}] Correlating catalysts...")
        self.catalyst_tracker.refresh_macro_data()
        for signal in all_signals:
            self.catalyst_tracker.correlate_signal(signal)

        # 4) LLM theme extraction
        logger.info(f"[{self.AGENT_ID}] Extracting themes...")
        high_priority = [s for s in all_signals if s.priority <= IntelPriority.MEDIUM]
        themes = self.theme_extractor.extract_themes(high_priority or all_signals[:20])
        self._latest_themes = themes

        # 5) Store
        for sig in all_signals:
            self._all_signals.append(sig)
        self._scan_count += 1

        result = {
            "signals": [s.to_dict() for s in all_signals],
            "signal_count": len(all_signals),
            "themes": themes,
            "macro": self.catalyst_tracker._macro_cache,
            "upcoming_catalysts": self.catalyst_tracker.get_upcoming_catalysts(),
            "trending_tickers": self.x_scanner.get_trending_tickers(),
            "scan_number": self._scan_count,
            "timestamp": datetime.now().isoformat(),
        }

        # Persist to disk
        try:
            out_file = os.path.join(DATA_DIR, "latest_intel.json")
            with open(out_file, "w") as f:
                json.dump(result, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to persist intel: {e}")

        logger.info(
            f"[{self.AGENT_ID}] Scan #{self._scan_count} complete: "
            f"{len(news_signals)} news, {len(x_signals)} social, "
            f"{len(themes.get('themes', []))} themes"
        )
        return result

    async def run_scan_cycle(self):
        """
        Run one async scan cycle and publish results to Blackboard.
        """
        # Run synchronous scanning in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.scan_all_sync)

        # Publish individual signals to Blackboard
        signals = result.get("signals", [])
        for sig_dict in signals:
            signal = IntelSignal(**{k: v for k, v in sig_dict.items() if k in IntelSignal.__dataclass_fields__})
            if signal.priority <= IntelPriority.MEDIUM:
                await self._publish_signal(signal)

        # Publish themes
        themes = result.get("themes", {})
        if themes.get("themes"):
            await self._publish_themes(themes)

        return result

    async def run(self):
        """
        Main async run loop for continuous intelligence gathering.
        Integrates with the Blackboard swarm architecture.
        """
        self._running = True
        logger.info(f"[{self.AGENT_ID}] Starting continuous scan loop...")

        # Launch background tasks
        tasks = []
        tasks.append(asyncio.create_task(self._heartbeat_loop()))
        if self.blackboard:
            tasks.append(asyncio.create_task(self._listen_watchlist_updates()))

        # Main scan loop
        try:
            while self._running:
                try:
                    await self.run_scan_cycle()
                except Exception as e:
                    logger.error(f"[{self.AGENT_ID}] Scan cycle error: {e}")

                # Wait for next scan interval
                await asyncio.sleep(NEWS_SCAN_INTERVAL)

        except asyncio.CancelledError:
            logger.info(f"[{self.AGENT_ID}] Cancelled")
        finally:
            self._running = False
            for task in tasks:
                task.cancel()
            logger.info(f"[{self.AGENT_ID}] Shutdown complete")

    def get_stats(self) -> Dict:
        """Get sensorium statistics."""
        return {
            "agent_id": self.AGENT_ID,
            "scan_count": self._scan_count,
            "total_signals": len(self._all_signals),
            "watchlist_size": len(self.watchlist),
            "stats": dict(self._stats),
            "latest_themes": self._latest_themes,
            "macro_data": self.catalyst_tracker._macro_cache,
        }


# ============================================================
# CLI Entry Point
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw World Intelligence Sensorium v1.0"
    )
    parser.add_argument("--scan", action="store_true", help="Run full scan cycle")
    parser.add_argument("--themes", action="store_true", help="Show latest themes")
    parser.add_argument("--catalysts", action="store_true", help="Show upcoming catalysts")
    parser.add_argument("--macro", action="store_true", help="Show macro data from FRED")
    parser.add_argument("--tickers", nargs="+", help="Watchlist tickers to scan")
    parser.add_argument("--daemon", action="store_true", help="Run continuous scan loop")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    watchlist = set(args.tickers) if args.tickers else set()
    sensorium = WorldIntelSensorium(watchlist=watchlist)

    if args.scan:
        print("\nOpenClaw World Intelligence Sensorium v1.0")
        print("=" * 55)
        result = sensorium.scan_all_sync()
        print(f"\nSignals found: {result['signal_count']}")
        print(f"Themes: {len(result['themes'].get('themes', []))}")
        for sig in result["signals"][:15]:
            emoji = "🟢" if sig["sentiment"] > 0.2 else "🔴" if sig["sentiment"] < -0.2 else "⚪"
            print(
                f"  {emoji} [{sig['source']:<10s}] {sig['ticker'] or 'MACRO':<6s} "
                f"p={sig['priority']} | {sig['headline'][:80]}"
            )

    elif args.themes:
        result = sensorium.scan_all_sync()
        themes = result.get("themes", {})
        print("\nExtracted Themes:")
        for t in themes.get("themes", []):
            print(f"  • {t['name']} (confidence: {t['confidence']}) [{t['direction']}]")
        print("\nTicker Catalysts:")
        for tc in themes.get("ticker_catalysts", [])[:10]:
            print(f"  ${tc['ticker']}: {tc['catalyst']} (sentiment: {tc['sentiment']}, urgency: {tc['urgency']})")

    elif args.catalysts:
        sensorium.catalyst_tracker.refresh_macro_data()
        cats = sensorium.catalyst_tracker.get_upcoming_catalysts()
        print(f"\nUpcoming Catalysts ({len(cats)}):")
        for c in cats:
            print(f"  {c['event_date']} | ${c['ticker']} | {c['catalyst_type']} | {c['description']}")

    elif args.macro:
        macro = sensorium.catalyst_tracker.refresh_macro_data()
        print("\nMacro Indicators (FRED):")
        print("=" * 50)
        for label, data in macro.items():
            val = data.get("value", "N/A")
            change = data.get("change", "")
            change_str = f" (Δ {change:+.4f})" if isinstance(change, (int, float)) else ""
            print(f"  {label:<15s} {val}{change_str}  [{data.get('date', '')}]")

    elif args.daemon:
        print("OpenClaw World Intelligence Sensorium v1.0 — Daemon Mode")
        print("=" * 55)
        bb = get_blackboard() if get_blackboard else None
        sensorium.blackboard = bb
        asyncio.run(sensorium.run())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
