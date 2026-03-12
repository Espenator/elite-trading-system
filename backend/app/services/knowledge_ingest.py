"""KnowledgeIngestionService — user-facing API for feeding data into the system.

Users can feed:
  - YouTube video transcripts (URL or raw text)
  - News articles (URL or raw text)
  - Chart analysis / trade ideas (structured or free-text)
  - URLs to scrape and analyze
  - Arbitrary text notes / research

Each ingested item is:
  1. Parsed for symbols, direction, key concepts
  2. Stored in the knowledge store (SQLite)
  3. Published to MessageBus -> triggers a SwarmSpawner analysis

Usage:
    from app.services.knowledge_ingest import knowledge_ingest
    result = await knowledge_ingest.ingest_youtube("https://youtube.com/watch?v=...")
    result = await knowledge_ingest.ingest_text("AAPL looks bullish, breaking out of a cup and handle")
    result = await knowledge_ingest.ingest_url("https://example.com/article-about-nvda")
"""
import asyncio
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)

# Common ticker patterns (1-5 uppercase letters, optionally preceded by $)
_TICKER_RE = re.compile(r'(?<!\w)\$?([A-Z]{1,5})(?!\w)')
# Known non-ticker words to filter out
_NON_TICKERS = {
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER",
    "WAS", "ONE", "OUR", "OUT", "HAS", "HIS", "HOW", "MAN", "NEW", "NOW",
    "OLD", "SEE", "WAY", "WHO", "BOY", "DID", "ITS", "LET", "PUT", "SAY",
    "SHE", "TOO", "USE", "HIM", "HAD", "GET", "HIT", "RUN", "SET", "TOP",
    "WIN", "BIG", "MAY", "ALSO", "BACK", "BEEN", "CALL", "COME", "EACH",
    "FIND", "FIRST", "FROM", "GIVE", "GOOD", "HAVE", "HERE", "HIGH", "JUST",
    "KNOW", "LAST", "LONG", "LOOK", "MADE", "MAKE", "MANY", "MORE", "MOST",
    "MUCH", "MUST", "NAME", "NEXT", "ONLY", "OVER", "PART", "SAME", "SOME",
    "TAKE", "THAN", "THEM", "THEN", "THIS", "VERY", "WANT", "WELL", "WHAT",
    "WHEN", "WITH", "WILL", "WORK", "YEAR", "YOUR", "ABOUT", "AFTER", "COULD",
    "EVERY", "GREAT", "LARGE", "NEVER", "OTHER", "RIGHT", "SHALL", "STILL",
    "THEIR", "THERE", "THESE", "THINK", "THREE", "TODAY", "UNDER", "WATCH",
    "WATER", "WHERE", "WHICH", "WHILE", "WORLD", "WOULD", "ABOVE", "BEING",
    "BELOW", "GOING", "MIGHT", "SINCE", "UNTIL", "USING", "WOULD", "USD",
    "IMO", "LMAO", "FOMO", "ATH", "ATL", "ITM", "OTM", "EOD", "AH", "PM",
    "API", "ETF", "IPO", "CEO", "CFO", "GDP", "CPI", "FED", "SEC", "NFT",
}

# Directional keywords
_BULLISH_KW = {
    "bullish", "buy", "long", "calls", "breakout", "rally", "moon", "rip",
    "bull flag", "cup and handle", "golden cross", "double bottom",
    "ascending triangle", "accumulation", "demand zone", "support hold",
    "buy signal", "uptrend", "higher highs", "higher lows", "squeeze",
    "gamma ramp", "short squeeze", "dip buy", "oversold bounce",
}
_BEARISH_KW = {
    "bearish", "sell", "short", "puts", "breakdown", "crash", "dump",
    "bear flag", "head and shoulders", "death cross", "double top",
    "descending triangle", "distribution", "supply zone", "resistance",
    "sell signal", "downtrend", "lower highs", "lower lows",
    "overbought", "fade", "risk off",
}

# Concept extraction patterns
_CONCEPT_PATTERNS = [
    "cup and handle", "bull flag", "bear flag", "double bottom", "double top",
    "head and shoulders", "ascending triangle", "descending triangle",
    "golden cross", "death cross", "support", "resistance",
    "breakout", "breakdown", "squeeze", "gamma ramp", "short squeeze",
    "demand zone", "supply zone", "accumulation", "distribution",
    "divergence", "MACD crossover", "RSI oversold", "RSI overbought",
    "volume spike", "dark pool", "unusual options", "earnings",
    "FDA", "merger", "acquisition", "buyback", "dividend",
    "fibonacci", "gap fill", "VWAP", "moving average",
]


class KnowledgeIngestionService:
    """Handles ingestion of user-provided knowledge into the trading system."""

    def __init__(self):
        self._bus = None
        self._stats = {
            "total_ingested": 0,
            "by_type": {},
        }

    def set_message_bus(self, bus):
        self._bus = bus

    # ------------------------------------------------------------------
    # YouTube transcript ingestion
    # ------------------------------------------------------------------
    async def ingest_youtube(
        self,
        url: str = "",
        transcript: str = "",
        title: str = "",
        channel: str = "",
    ) -> Dict[str, Any]:
        """Ingest a YouTube video transcript.

        Args:
            url: YouTube video URL (will extract video ID)
            transcript: Raw transcript text (if already extracted)
            title: Video title
            channel: YouTube channel name
        """
        video_id = self._extract_youtube_id(url) if url else ""
        text = transcript or ""

        # If URL provided but no transcript, try to fetch via YouTube API
        if url and not text:
            text = await self._fetch_youtube_transcript(video_id)

        if not text:
            return {"error": "No transcript provided and couldn't fetch from URL", "hint": "Paste the transcript text directly"}

        # Parse the transcript
        symbols = self._extract_symbols(text)
        direction = self._detect_direction(text)
        concepts = self._extract_concepts(text)
        ideas = self._extract_ideas(text)

        # Store in knowledge base
        entry = {
            "id": str(uuid.uuid4())[:12],
            "type": "youtube",
            "url": url,
            "video_id": video_id,
            "title": title,
            "channel": channel,
            "symbols": symbols,
            "direction": direction,
            "concepts": concepts,
            "ideas": ideas,
            "raw_text": text[:5000],  # Cap stored text
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._store_knowledge(entry)
        self._update_youtube_knowledge_store(entry)

        # Trigger swarm analysis for extracted symbols
        if symbols:
            await self._trigger_swarm(
                source="youtube",
                symbols=symbols[:5],
                direction=direction,
                reasoning=f"YouTube [{channel}]: {title or 'untitled'}. Concepts: {', '.join(concepts[:5])}",
                raw_content=text[:2000],
            )

        self._stats["total_ingested"] += 1
        self._stats["by_type"]["youtube"] = self._stats["by_type"].get("youtube", 0) + 1

        return {
            "status": "ingested",
            "id": entry["id"],
            "type": "youtube",
            "symbols_found": symbols,
            "direction": direction,
            "concepts": concepts,
            "ideas": ideas[:5],
            "swarm_triggered": bool(symbols),
        }

    # ------------------------------------------------------------------
    # News / article ingestion
    # ------------------------------------------------------------------
    async def ingest_news(
        self,
        url: str = "",
        text: str = "",
        title: str = "",
        source_name: str = "",
    ) -> Dict[str, Any]:
        """Ingest a news article."""
        content = text or ""

        # If URL provided, try to fetch content
        if url and not content:
            content = await self._fetch_url_content(url)

        if not content:
            return {"error": "No content provided and couldn't fetch from URL"}

        symbols = self._extract_symbols(content)
        direction = self._detect_direction(content)
        concepts = self._extract_concepts(content)

        entry = {
            "id": str(uuid.uuid4())[:12],
            "type": "news",
            "url": url,
            "title": title,
            "source_name": source_name,
            "symbols": symbols,
            "direction": direction,
            "concepts": concepts,
            "raw_text": content[:5000],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._store_knowledge(entry)

        if symbols:
            await self._trigger_swarm(
                source="news",
                symbols=symbols[:5],
                direction=direction,
                reasoning=f"News [{source_name}]: {title or url}",
                raw_content=content[:2000],
            )

        self._stats["total_ingested"] += 1
        self._stats["by_type"]["news"] = self._stats["by_type"].get("news", 0) + 1

        return {
            "status": "ingested",
            "id": entry["id"],
            "type": "news",
            "symbols_found": symbols,
            "direction": direction,
            "concepts": concepts,
            "swarm_triggered": bool(symbols),
        }

    # ------------------------------------------------------------------
    # Free-text / trade idea ingestion
    # ------------------------------------------------------------------
    async def ingest_text(
        self,
        text: str,
        idea_type: str = "trade_idea",
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Ingest free-text: trade ideas, chart analysis, research notes.

        Args:
            text: The content to ingest
            idea_type: "trade_idea", "chart_analysis", "research", "note"
            symbols: Override symbol detection (optional)
        """
        if not text.strip():
            return {"error": "Empty text"}

        detected_symbols = symbols or self._extract_symbols(text)
        direction = self._detect_direction(text)
        concepts = self._extract_concepts(text)
        ideas = self._extract_ideas(text)

        entry = {
            "id": str(uuid.uuid4())[:12],
            "type": idea_type,
            "symbols": detected_symbols,
            "direction": direction,
            "concepts": concepts,
            "ideas": ideas,
            "raw_text": text[:5000],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._store_knowledge(entry)

        if detected_symbols:
            await self._trigger_swarm(
                source="user",
                symbols=detected_symbols[:5],
                direction=direction,
                reasoning=f"User {idea_type}: {text[:200]}",
                raw_content=text[:2000],
            )

        self._stats["total_ingested"] += 1
        self._stats["by_type"][idea_type] = self._stats["by_type"].get(idea_type, 0) + 1

        return {
            "status": "ingested",
            "id": entry["id"],
            "type": idea_type,
            "symbols_found": detected_symbols,
            "direction": direction,
            "concepts": concepts,
            "ideas": ideas[:5],
            "swarm_triggered": bool(detected_symbols),
        }

    # ------------------------------------------------------------------
    # URL scraping + ingestion
    # ------------------------------------------------------------------
    async def ingest_url(self, url: str, hint: str = "") -> Dict[str, Any]:
        """Scrape a URL and ingest the content.

        Args:
            url: URL to fetch and analyze
            hint: Optional hint about what to look for (e.g., "NVDA analysis")
        """
        content = await self._fetch_url_content(url)
        if not content:
            return {"error": f"Couldn't fetch content from {url}"}

        if hint:
            content = f"Context: {hint}\n\n{content}"

        # Determine type from URL
        if "youtube.com" in url or "youtu.be" in url:
            return await self.ingest_youtube(url=url, transcript=content)

        return await self.ingest_news(url=url, text=content, source_name=self._domain_from_url(url))

    # ------------------------------------------------------------------
    # Batch ingestion — multiple symbols to analyze
    # ------------------------------------------------------------------
    async def ingest_symbols(
        self,
        symbols: List[str],
        reason: str = "User requested analysis",
    ) -> Dict[str, Any]:
        """Queue multiple symbols for swarm analysis.

        This is the simplest way to say "analyze these tickers for me."
        """
        cleaned = [s.upper().strip() for s in symbols if s.strip()]
        if not cleaned:
            return {"error": "No valid symbols provided"}

        triggered = []
        for sym in cleaned[:20]:  # Cap at 20
            await self._trigger_swarm(
                source="user",
                symbols=[sym],
                direction="unknown",
                reasoning=reason,
            )
            triggered.append(sym)

        self._stats["total_ingested"] += len(triggered)
        self._stats["by_type"]["symbol_scan"] = self._stats["by_type"].get("symbol_scan", 0) + len(triggered)

        return {
            "status": "queued",
            "symbols_queued": triggered,
            "swarms_triggered": len(triggered),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _extract_symbols(self, text: str) -> List[str]:
        """Extract stock ticker symbols from text."""
        matches = _TICKER_RE.findall(text)
        # Filter non-tickers and deduplicate preserving order
        seen = set()
        symbols = []
        for m in matches:
            upper = m.upper()
            if upper not in _NON_TICKERS and upper not in seen and len(upper) >= 2:
                seen.add(upper)
                symbols.append(upper)
        return symbols[:20]

    def _detect_direction(self, text: str) -> str:
        """Detect overall directional bias from text."""
        lower = text.lower()
        bull_score = sum(1 for kw in _BULLISH_KW if kw in lower)
        bear_score = sum(1 for kw in _BEARISH_KW if kw in lower)
        if bull_score > bear_score + 1:
            return "bullish"
        elif bear_score > bull_score + 1:
            return "bearish"
        elif bull_score > bear_score:
            return "lean_bullish"
        elif bear_score > bull_score:
            return "lean_bearish"
        return "neutral"

    def _extract_concepts(self, text: str) -> List[str]:
        """Extract trading concepts/patterns from text."""
        lower = text.lower()
        found = []
        for pattern in _CONCEPT_PATTERNS:
            if pattern.lower() in lower:
                found.append(pattern)
        return found

    def _extract_ideas(self, text: str) -> List[str]:
        """Extract actionable trading ideas as sentence fragments."""
        ideas = []
        # Look for sentences with actionable language
        sentences = re.split(r'[.!?\n]', text)
        action_words = {"buy", "sell", "long", "short", "entry", "target", "stop", "watch", "alert"}
        for sentence in sentences:
            s = sentence.strip()
            if len(s) > 15 and any(w in s.lower() for w in action_words):
                ideas.append(s[:200])
        return ideas[:10]

    def _extract_youtube_id(self, url: str) -> str:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'(?:embed/)([a-zA-Z0-9_-]{11})',
        ]
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        return ""

    async def _fetch_youtube_transcript(self, video_id: str) -> str:
        """Try to fetch a YouTube transcript via the YouTube Data API or transcript lib."""
        if not video_id:
            return ""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join(item["text"] for item in transcript_list)
        except ImportError:
            logger.debug("youtube_transcript_api not installed — user must paste transcript")
        except Exception as e:
            logger.debug("YouTube transcript fetch failed: %s", e)
        return ""

    @staticmethod
    def _is_safe_url(url: str) -> bool:
        """Validate URL to prevent SSRF — block private/internal networks."""
        import ipaddress
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
        except Exception:
            return False

        # Only allow http/https schemes
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Block obvious internal hostnames
        blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "metadata.google.internal"}
        if hostname.lower() in blocked_hosts:
            return False

        # Resolve hostname and block private IP ranges
        try:
            import socket
            resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for family, _type, _proto, _canon, sockaddr in resolved:
                ip = ipaddress.ip_address(sockaddr[0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False
        except (socket.gaierror, ValueError):
            return False

        return True

    async def _fetch_url_content(self, url: str) -> str:
        """Fetch and extract text content from a URL (with SSRF protection)."""
        if not self._is_safe_url(url):
            logger.warning("URL blocked by SSRF filter: %s", url)
            return ""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=15),
                    allow_redirects=False,
                ) as resp:
                    if resp.status != 200:
                        return ""
                    html = await resp.text()
                    return self._html_to_text(html)
        except Exception as e:
            logger.debug("URL fetch failed for %s: %s", url, e)
            return ""

    def _html_to_text(self, html: str) -> str:
        """Basic HTML to text conversion."""
        # Remove script and style tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Decode HTML entities
        import html as html_mod
        text = html_mod.unescape(text)
        return text[:10000]

    def _domain_from_url(self, url: str) -> str:
        """Extract domain from URL."""
        m = re.search(r'https?://(?:www\.)?([^/]+)', url)
        return m.group(1) if m else "unknown"

    def _store_knowledge(self, entry: Dict[str, Any]):
        """Persist knowledge entry to SQLite."""
        try:
            from app.services.database import db_service
            # Append to knowledge_feed list
            feed = db_service.get_config("knowledge_feed") or []
            if not isinstance(feed, list):
                feed = []
            feed.append(entry)
            # Keep last 500 entries
            if len(feed) > 500:
                feed = feed[-500:]
            db_service.set_config("knowledge_feed", feed)
        except Exception as e:
            logger.warning("Failed to store knowledge entry: %s", e)

    def _update_youtube_knowledge_store(self, entry: Dict[str, Any]):
        """Also update the YouTube knowledge store read by youtube_knowledge_agent."""
        try:
            from app.services.database import db_service
            yt_store = db_service.get_config("youtube_knowledge") or []
            if not isinstance(yt_store, list):
                yt_store = []
            yt_store.append({
                "symbols": entry.get("symbols", []),
                "ideas": entry.get("ideas", []),
                "concepts": entry.get("concepts", []),
                "title": entry.get("title", ""),
                "channel": entry.get("channel", ""),
                "timestamp": entry.get("timestamp", ""),
            })
            # Keep last 100 YouTube entries
            if len(yt_store) > 100:
                yt_store = yt_store[-100:]
            db_service.set_config("youtube_knowledge", yt_store)
        except Exception as e:
            logger.warning("Failed to update YouTube knowledge store: %s", e)

    async def _trigger_swarm(
        self,
        source: str,
        symbols: List[str],
        direction: str,
        reasoning: str,
        raw_content: str = "",
    ):
        """Trigger a swarm analysis via MessageBus."""
        if not self._bus:
            # Try to get global bus
            try:
                from app.core.message_bus import get_message_bus
                self._bus = get_message_bus()
            except Exception:
                pass

        if self._bus:
            await self._bus.publish("swarm.idea", {
                "source": source,
                "symbols": symbols,
                "direction": direction,
                "reasoning": reasoning,
                "raw_content": raw_content,
            })
        else:
            # Direct spawner call as fallback
            try:
                from app.services.swarm_spawner import get_swarm_spawner, SwarmIdea
                spawner = get_swarm_spawner()
                await spawner.spawn_analysis(SwarmIdea(
                    source=source,
                    symbols=symbols,
                    direction=direction,
                    reasoning=reasoning,
                    raw_content=raw_content,
                ))
            except Exception as e:
                logger.warning("Failed to trigger swarm: %s", e)

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    def get_knowledge_feed(self, limit: int = 50, type_filter: str = None) -> List[Dict[str, Any]]:
        """Retrieve recent knowledge entries."""
        try:
            from app.services.database import db_service
            feed = db_service.get_config("knowledge_feed") or []
            if type_filter:
                feed = [e for e in feed if e.get("type") == type_filter]
            return feed[-limit:]
        except Exception:
            return []


# Module-level singleton
knowledge_ingest = KnowledgeIngestionService()
