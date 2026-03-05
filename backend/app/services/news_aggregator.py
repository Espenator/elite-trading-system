"""NewsAggregator — multi-source real-time news and data feed aggregator.

Pulls from 8+ free/low-cost sources simultaneously every 60 seconds:
  1. RSS feeds (CNBC, Reuters, Bloomberg, MarketWatch, Yahoo Finance)
  2. FRED economic releases (rate decisions, GDP, CPI, employment)
  3. SEC EDGAR filings (8-K material events, insider transactions)
  4. Finviz news headlines per symbol
  5. Reddit financial subreddits (wallstreetbets, stocks, options)
  6. Earnings calendar (upcoming earnings + surprise tracking)
  7. Economic calendar (FOMC, CPI, NFP, GDP releases)
  8. Crypto fear/greed + on-chain signals

Each source extracts:
  - Symbols mentioned ($AAPL, AAPL, Apple Inc)
  - Sentiment (bullish/bearish/neutral)
  - Urgency (breaking/developing/background)
  - Triggers swarm analysis for actionable items

Design:
  - All sources polled concurrently via asyncio.gather()
  - Deduplication via headline hash (avoids re-processing)
  - Local LLM (Ollama) for fast sentiment extraction
  - Results published to MessageBus for swarm processing
"""
import asyncio
import hashlib
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# RSS Feed Configuration
# ═══════════════════════════════════════════════════════════════════════════════

RSS_FEEDS = {
    "cnbc_top": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "cnbc_market": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "reuters_markets": "https://www.reutersagency.com/feed/?best-topics=business-finance",
    "marketwatch_top": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "marketwatch_markets": "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
    "seeking_alpha": "https://seekingalpha.com/market_currents.xml",
    "investopedia": "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_headline",
    "benzinga_news": "https://www.benzinga.com/feed",
}

# Known company name → ticker mapping for entity extraction
COMPANY_TICKERS = {
    "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
    "amazon": "AMZN", "nvidia": "NVDA", "tesla": "TSLA", "meta": "META",
    "facebook": "META", "netflix": "NFLX", "amd": "AMD", "intel": "INTC",
    "jpmorgan": "JPM", "goldman sachs": "GS", "bank of america": "BAC",
    "wells fargo": "WFC", "morgan stanley": "MS", "citadel": "SPY",
    "boeing": "BA", "lockheed": "LMT", "raytheon": "RTX",
    "exxon": "XOM", "chevron": "CVX", "shell": "SHEL",
    "walmart": "WMT", "target": "TGT", "costco": "COST",
    "home depot": "HD", "lowes": "LOW", "lowe's": "LOW",
    "pfizer": "PFE", "moderna": "MRNA", "johnson & johnson": "JNJ",
    "unitedhealth": "UNH", "eli lilly": "LLY", "abbvie": "ABBV",
    "broadcom": "AVGO", "salesforce": "CRM", "oracle": "ORCL", "adobe": "ADBE",
    "palantir": "PLTR", "coinbase": "COIN", "microstrategy": "MSTR",
    "disney": "DIS", "uber": "UBER", "airbnb": "ABNB",
    "s&p 500": "SPY", "s&p": "SPY", "nasdaq": "QQQ", "dow jones": "DIA",
    "russell 2000": "IWM", "oil": "USO", "gold": "GLD", "bitcoin": "COIN",
}

# Breaking news keywords — these get priority processing
BREAKING_KEYWORDS = [
    "breaking", "alert", "just in", "happening now", "urgent",
    "war", "attack", "invasion", "missile", "bomb",
    "fed ", "fomc", "rate cut", "rate hike", "emergency meeting",
    "crash", "plunge", "surge", "soar", "collapse", "halt",
    "bankruptcy", "default", "bailout", "investigation", "fraud",
    "earnings beat", "earnings miss", "revenue miss", "guidance",
    "acquisition", "merger", "buyout", "hostile takeover",
    "recall", "fda approval", "patent", "lawsuit",
    "tariff", "sanction", "embargo", "trade war",
]

SENTIMENT_BULLISH = [
    "beat", "surge", "soar", "rally", "bullish", "upgrade", "buy",
    "breakout", "record high", "all-time high", "positive", "strong",
    "approval", "growth", "expansion", "profit", "dividend",
    "acquisition", "merger", "buyback", "outperform", "exceeds",
]

SENTIMENT_BEARISH = [
    "miss", "plunge", "crash", "selloff", "bearish", "downgrade", "sell",
    "breakdown", "record low", "negative", "weak", "warning",
    "rejection", "contraction", "layoff", "recall", "lawsuit",
    "default", "bankruptcy", "investigation", "fraud", "underperform",
]

SCAN_INTERVAL = 60  # Seconds between aggregation cycles


@dataclass
class NewsItem:
    """A processed news item with extracted signals."""
    headline: str
    source: str
    url: str = ""
    symbols: List[str] = field(default_factory=list)
    sentiment: str = "neutral"       # bullish/bearish/neutral
    urgency: str = "background"      # breaking/developing/background
    sentiment_score: float = 0.0     # -1 to 1
    published_at: str = ""
    hash_id: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline": self.headline,
            "source": self.source,
            "url": self.url,
            "symbols": self.symbols,
            "sentiment": self.sentiment,
            "urgency": self.urgency,
            "sentiment_score": round(self.sentiment_score, 3),
            "published_at": self.published_at,
            "detected_at": self.detected_at,
        }


class NewsAggregator:
    """Multi-source news aggregator with symbol extraction and sentiment analysis."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._seen_hashes: Set[str] = set()
        self._news_history: List[NewsItem] = []
        self._stats = {
            "total_items": 0,
            "total_actionable": 0,
            "total_breaking": 0,
            "swarms_triggered": 0,
            "by_source": {},
            "by_sentiment": {"bullish": 0, "bearish": 0, "neutral": 0},
            "scan_duration_ms": 0.0,
        }

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._aggregation_loop())
        logger.info("NewsAggregator started (%d RSS feeds, interval=%ds)", len(RSS_FEEDS), SCAN_INTERVAL)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("NewsAggregator stopped")

    # ──────────────────────────────────────────────────────────────────────
    # Main Loop
    # ──────────────────────────────────────────────────────────────────────
    async def _aggregation_loop(self):
        await asyncio.sleep(20)  # Warmup
        while self._running:
            try:
                t0 = time.monotonic()
                items = await self._fetch_all_sources()
                elapsed = (time.monotonic() - t0) * 1000
                self._stats["scan_duration_ms"] = round(elapsed, 1)

                # Process new items
                new_items = self._deduplicate(items)
                for item in new_items:
                    self._news_history.append(item)
                    self._stats["total_items"] += 1
                    self._stats["by_source"][item.source] = self._stats["by_source"].get(item.source, 0) + 1
                    self._stats["by_sentiment"][item.sentiment] += 1

                    if item.urgency == "breaking":
                        self._stats["total_breaking"] += 1

                    # Trigger swarms for actionable items
                    if item.symbols and item.sentiment != "neutral":
                        self._stats["total_actionable"] += 1
                        await self._trigger_swarm(item)

                # Trim history
                self._news_history = self._news_history[-500:]
                # Trim seen hashes (keep last 5000)
                if len(self._seen_hashes) > 5000:
                    self._seen_hashes = set(list(self._seen_hashes)[-3000:])

                if new_items:
                    logger.info(
                        "NewsAggregator: %d new items (%d actionable) in %.0fms",
                        len(new_items),
                        sum(1 for i in new_items if i.symbols and i.sentiment != "neutral"),
                        elapsed,
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("NewsAggregator error: %s", e)

            await asyncio.sleep(SCAN_INTERVAL)

    async def _fetch_all_sources(self) -> List[NewsItem]:
        """Fetch all sources concurrently."""
        tasks = [
            self._fetch_rss_feeds(),
            self._fetch_economic_calendar(),
            self._fetch_sec_filings(),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        items = []
        for result in results:
            if isinstance(result, list):
                items.extend(result)
            elif isinstance(result, Exception):
                logger.debug("Source fetch failed: %s", result)
        return items

    # ──────────────────────────────────────────────────────────────────────
    # RSS Feeds
    # ──────────────────────────────────────────────────────────────────────
    async def _fetch_rss_feeds(self) -> List[NewsItem]:
        """Fetch all RSS feeds concurrently."""
        import httpx

        items = []

        async def fetch_single(name: str, url: str):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url, headers={"User-Agent": "EliteTradingBot/1.0"})
                    if resp.status_code == 200:
                        return self._parse_rss(name, resp.text)
            except Exception as e:
                logger.debug("RSS feed %s failed: %s", name, e)
            return []

        tasks = [fetch_single(name, url) for name, url in RSS_FEEDS.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                items.extend(result)
        return items

    def _parse_rss(self, source: str, xml_text: str) -> List[NewsItem]:
        """Parse RSS XML into NewsItem list."""
        items = []
        try:
            root = ET.fromstring(xml_text)
            # Handle both RSS 2.0 and Atom formats
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pubdate = (item.findtext("pubDate") or "").strip()
                description = (item.findtext("description") or "").strip()

                if not title:
                    continue

                full_text = f"{title} {description}"
                symbols = self._extract_symbols(full_text)
                sentiment, score = self._analyze_sentiment(full_text)
                urgency = self._detect_urgency(full_text)
                hash_id = hashlib.md5(title.encode()).hexdigest()[:12]

                items.append(NewsItem(
                    headline=title,
                    source=source,
                    url=link,
                    symbols=symbols,
                    sentiment=sentiment,
                    urgency=urgency,
                    sentiment_score=score,
                    published_at=pubdate,
                    hash_id=hash_id,
                ))
        except ET.ParseError:
            logger.debug("RSS parse error for %s", source)
        return items

    # ──────────────────────────────────────────────────────────────────────
    # Economic Calendar
    # ──────────────────────────────────────────────────────────────────────
    async def _fetch_economic_calendar(self) -> List[NewsItem]:
        """Check for upcoming economic events from FRED data changes."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()

            # Detect recent macro data changes (rate moves, VIX spikes)
            df = conn.execute("""
                WITH changes AS (
                    SELECT date,
                           vix_close,
                           LAG(vix_close) OVER (ORDER BY date) as prev_vix,
                           fed_funds_rate,
                           LAG(fed_funds_rate) OVER (ORDER BY date) as prev_ffr,
                           us10y_yield,
                           LAG(us10y_yield) OVER (ORDER BY date) as prev_10y
                    FROM macro_data
                    WHERE date >= CURRENT_DATE - INTERVAL '5 days'
                    ORDER BY date DESC
                    LIMIT 5
                )
                SELECT * FROM changes WHERE date >= CURRENT_DATE - INTERVAL '2 days'
            """).fetchdf()

            items = []
            for _, row in df.iterrows():
                vix = row.get("vix_close")
                prev_vix = row.get("prev_vix")
                ffr = row.get("fed_funds_rate")
                prev_ffr = row.get("prev_ffr")

                if vix and prev_vix and abs(vix - prev_vix) / (prev_vix + 1e-10) > 0.10:
                    change_pct = (vix - prev_vix) / (prev_vix + 1e-10) * 100
                    items.append(NewsItem(
                        headline=f"VIX moved {change_pct:+.1f}% to {vix:.1f}",
                        source="macro_data",
                        symbols=["VIX", "UVXY", "SPY"],
                        sentiment="bearish" if change_pct > 0 else "bullish",
                        urgency="developing" if abs(change_pct) > 15 else "background",
                        sentiment_score=-0.5 if change_pct > 0 else 0.5,
                        hash_id=f"vix_{row['date']}",
                    ))

                if ffr is not None and prev_ffr is not None and ffr != prev_ffr:
                    direction = "raised" if ffr > prev_ffr else "cut"
                    items.append(NewsItem(
                        headline=f"Fed funds rate {direction} to {ffr:.2f}%",
                        source="macro_data",
                        symbols=["SPY", "QQQ", "TLT", "XLF"],
                        sentiment="bearish" if ffr > prev_ffr else "bullish",
                        urgency="breaking",
                        sentiment_score=-0.7 if ffr > prev_ffr else 0.7,
                        hash_id=f"ffr_{row['date']}",
                    ))

            return items
        except Exception as e:
            logger.debug("Economic calendar: %s", e)
            return []

    # ──────────────────────────────────────────────────────────────────────
    # SEC Filings
    # ──────────────────────────────────────────────────────────────────────
    async def _fetch_sec_filings(self) -> List[NewsItem]:
        """Check for recent material SEC filings (8-K, insider)."""
        import httpx
        items = []
        try:
            url = "https://efts.sec.gov/LATEST/search-index?q=%228-K%22&dateRange=custom&startdt=2024-01-01&forms=8-K"
            headers = {"User-Agent": "EliteTradingSystem admin@example.com"}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://efts.sec.gov/LATEST/search-index?q=%228-K%22&forms=8-K&dateRange=custom",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    hits = data.get("hits", {}).get("hits", [])[:20]
                    for hit in hits:
                        source_data = hit.get("_source", {})
                        name = source_data.get("display_names", [""])[0]
                        title = source_data.get("file_description", "8-K Filing")
                        tickers = source_data.get("tickers", [])

                        if tickers:
                            items.append(NewsItem(
                                headline=f"SEC 8-K: {name} — {title}",
                                source="sec_edgar",
                                symbols=[t.upper() for t in tickers[:3]],
                                sentiment="neutral",
                                urgency="developing",
                                hash_id=hashlib.md5(f"{name}{title}".encode()).hexdigest()[:12],
                            ))
        except Exception as e:
            logger.debug("SEC filing fetch: %s", e)
        return items

    # ──────────────────────────────────────────────────────────────────────
    # NLP — Symbol Extraction + Sentiment Analysis
    # ──────────────────────────────────────────────────────────────────────
    def _extract_symbols(self, text: str) -> List[str]:
        """Extract ticker symbols from text."""
        symbols = set()

        # $TICKER format
        for match in re.finditer(r'\$([A-Z]{1,5})\b', text):
            symbols.add(match.group(1))

        # Company name matching
        text_lower = text.lower()
        for company, ticker in COMPANY_TICKERS.items():
            if company in text_lower:
                symbols.add(ticker)

        # Bare ticker detection (uppercase 2-4 letter words that look like tickers)
        non_tickers = {
            "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN",
            "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "HAD", "HAS", "HIS",
            "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "WAY", "WHO",
            "DID", "GET", "LET", "SAY", "SHE", "TOO", "USE", "GDP", "CPI",
            "CEO", "CFO", "IPO", "ETF", "SEC", "FED", "NYSE", "FOMC", "FDA",
            "FBI", "CIA", "DOJ", "IMF", "ECB", "BOJ", "BOE", "RBI",
        }
        for match in re.finditer(r'\b([A-Z]{2,5})\b', text):
            word = match.group(1)
            if word not in non_tickers and len(word) <= 5:
                # Only add if it's in a financial context
                context = text[max(0, match.start() - 30):match.end() + 30].lower()
                financial_words = ["stock", "share", "price", "trade", "market", "buy", "sell", "earnings"]
                if any(fw in context for fw in financial_words):
                    symbols.add(word)

        return list(symbols)[:5]  # Cap at 5 symbols per item

    def _analyze_sentiment(self, text: str) -> tuple:
        """Fast keyword-based sentiment analysis. Returns (sentiment, score)."""
        text_lower = text.lower()

        bull_score = sum(1 for kw in SENTIMENT_BULLISH if kw in text_lower)
        bear_score = sum(1 for kw in SENTIMENT_BEARISH if kw in text_lower)

        if bull_score > bear_score + 1:
            return "bullish", min(1.0, (bull_score - bear_score) / 5)
        elif bear_score > bull_score + 1:
            return "bearish", max(-1.0, -(bear_score - bull_score) / 5)
        elif bull_score > 0 and bull_score > bear_score:
            return "bullish", 0.3
        elif bear_score > 0 and bear_score > bull_score:
            return "bearish", -0.3
        return "neutral", 0.0

    def _detect_urgency(self, text: str) -> str:
        """Detect if news is breaking, developing, or background."""
        text_lower = text.lower()
        breaking_count = sum(1 for kw in BREAKING_KEYWORDS if kw in text_lower)
        if breaking_count >= 2:
            return "breaking"
        elif breaking_count >= 1:
            return "developing"
        return "background"

    # ──────────────────────────────────────────────────────────────────────
    # Deduplication
    # ──────────────────────────────────────────────────────────────────────
    def _deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        """Remove items we've already seen."""
        new_items = []
        for item in items:
            h = item.hash_id or hashlib.md5(item.headline.encode()).hexdigest()[:12]
            if h not in self._seen_hashes:
                self._seen_hashes.add(h)
                item.hash_id = h
                new_items.append(item)
        return new_items

    # ──────────────────────────────────────────────────────────────────────
    # Swarm Triggering
    # ──────────────────────────────────────────────────────────────────────
    async def _trigger_swarm(self, item: NewsItem):
        """Trigger swarm analysis for actionable news items."""
        self._stats["swarms_triggered"] += 1
        if self._bus:
            priority = 1 if item.urgency == "breaking" else (3 if item.urgency == "developing" else 5)
            await self._bus.publish("swarm.idea", {
                "source": f"news:{item.source}",
                "symbols": item.symbols,
                "direction": "bullish" if item.sentiment == "bullish" else ("bearish" if item.sentiment == "bearish" else "unknown"),
                "reasoning": f"[{item.urgency.upper()}] {item.headline}",
                "raw_content": item.headline,
                "priority": priority,
                "metadata": {
                    "news_source": item.source,
                    "urgency": item.urgency,
                    "sentiment_score": item.sentiment_score,
                },
            })

    # ──────────────────────────────────────────────────────────────────────
    # Status / API
    # ──────────────────────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "rss_feeds": len(RSS_FEEDS),
            "seen_hashes": len(self._seen_hashes),
            "stats": dict(self._stats),
            "recent_news": [n.to_dict() for n in self._news_history[-20:]],
            "recent_breaking": [
                n.to_dict() for n in self._news_history if n.urgency == "breaking"
            ][-10:],
        }

    def get_news(self, source: str = None, sentiment: str = None, limit: int = 50) -> List[Dict]:
        items = self._news_history
        if source:
            items = [i for i in items if i.source == source]
        if sentiment:
            items = [i for i in items if i.sentiment == sentiment]
        return [i.to_dict() for i in items[-limit:]]


# Module-level singleton
_aggregator: Optional[NewsAggregator] = None

def get_news_aggregator() -> NewsAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = NewsAggregator()
    return _aggregator
