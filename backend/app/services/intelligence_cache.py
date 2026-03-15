"""Intelligence Cache — pre-fetch intelligence on a background loop.

Solves the latency problem: instead of blocking the council pipeline for 3-8s
waiting for Perplexity/Claude, intelligence is continuously pre-fetched and
cached. Council agents read from the warm cache instead.

Architecture:
    - Background asyncio task polls intelligence every REFRESH_INTERVAL seconds
    - Results cached per-symbol with configurable TTL
    - Council reads from cache (0ms) instead of blocking on Perplexity (3000ms)
    - Stale data is clearly marked so agents can adjust confidence

Usage:
    from app.services.intelligence_cache import get_intelligence_cache
    cache = get_intelligence_cache()
    await cache.start()  # Begin background pre-fetching
    intel = cache.get("AAPL")  # Instant read from cache
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings

logger = logging.getLogger(__name__)

# Default timings
DEFAULT_REFRESH_INTERVAL = 60.0  # Refresh intelligence every 60s
DEFAULT_TTL = 120.0  # Cache entries valid for 120s
MAX_STALE_AGE = 300.0  # After 5 min, mark as stale (agents should lower confidence)
MARKET_REFRESH_INTERVAL = 300.0  # Market-wide intel refreshed every 5 min
WEEKEND_REFRESH_INTERVAL = 300.0  # Weekend: 5 min between refreshes (conserve resources)
WEEKEND_MARKET_REFRESH_INTERVAL = 900.0  # Weekend: 15 min for market-wide intel
MAX_SYMBOL_CACHE_SIZE = 200  # Prevent unbounded cache growth

# Latency budgets (hard limits)
LATENCY_BUDGET_MS = {
    "brainstem": 500,
    "cortex": 3000,
    "deep_cortex": 10000,
    "total_pre_council": 5000,  # Max time intelligence gather can take
}


class CacheEntry:
    """A single cached intelligence result."""

    def __init__(self, data: Dict[str, Any], ttl: float = DEFAULT_TTL):
        self.data = data
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def is_expired(self) -> bool:
        return self.age_seconds > self.ttl

    @property
    def is_stale(self) -> bool:
        return self.age_seconds > MAX_STALE_AGE

    @property
    def freshness(self) -> str:
        age = self.age_seconds
        if age < self.ttl:
            return "fresh"
        elif age < MAX_STALE_AGE:
            return "aging"
        return "stale"

    def read(self) -> Dict[str, Any]:
        self.access_count += 1
        return {
            **self.data,
            "_cache_age_seconds": round(self.age_seconds, 1),
            "_cache_freshness": self.freshness,
            "_cache_access_count": self.access_count,
        }


class IntelligenceCache:
    """Background pre-fetch cache for multi-tier intelligence."""

    def __init__(self):
        self._symbol_cache: Dict[str, CacheEntry] = {}
        self._market_cache: Dict[str, CacheEntry] = {}
        self._watchlist: Set[str] = set()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._refresh_interval = DEFAULT_REFRESH_INTERVAL
        self._stats = {
            "cache_hits": 0, "cache_misses": 0, "refreshes": 0,
            "errors": 0, "avg_refresh_ms": 0.0,
        }

    def set_watchlist(self, symbols: List[str]):
        """Set the symbols to continuously pre-fetch intelligence for."""
        self._watchlist = set(s.upper() for s in symbols)
        logger.info("Intelligence cache watchlist: %s", self._watchlist)

    def add_symbol(self, symbol: str):
        """Add a symbol to the pre-fetch watchlist."""
        self._watchlist.add(symbol.upper())

    def remove_symbol(self, symbol: str):
        """Remove a symbol from the watchlist."""
        self._watchlist.discard(symbol.upper())
        self._symbol_cache.pop(symbol.upper(), None)

    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached intelligence for a symbol. Returns None if no cache."""
        key = symbol.upper()
        entry = self._symbol_cache.get(key)
        if entry is None:
            self._stats["cache_misses"] += 1
            return None
        self._stats["cache_hits"] += 1
        return entry.read()

    def get_market(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached market-wide intelligence (fear_greed, macro, sectors)."""
        entry = self._market_cache.get(key)
        if entry is None:
            return None
        return entry.read()

    async def start(self):
        """Start the background pre-fetch loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._refresh_loop())
        logger.info("Intelligence cache started (interval=%.0fs)", self._refresh_interval)

    async def stop(self):
        """Stop the background pre-fetch loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Intelligence cache stopped")

    async def force_refresh(self, symbol: str = None):
        """Force an immediate refresh for a symbol or all watchlist."""
        if symbol:
            await self._refresh_symbol(symbol.upper())
        else:
            await self._refresh_all()

    def _get_intervals(self) -> tuple:
        """Return (refresh_interval, market_interval) based on session."""
        try:
            from app.services.session_manager import get_current_session, WEEKEND, OVERNIGHT
            session = get_current_session()
            if session == WEEKEND:
                return WEEKEND_REFRESH_INTERVAL, WEEKEND_MARKET_REFRESH_INTERVAL
            if session == OVERNIGHT:
                return DEFAULT_REFRESH_INTERVAL * 2, MARKET_REFRESH_INTERVAL * 2
        except Exception:
            pass
        return self._refresh_interval, MARKET_REFRESH_INTERVAL

    async def _refresh_loop(self):
        """Background loop: refresh intelligence on interval."""
        market_last_refresh = 0.0
        while self._running:
            try:
                t0 = time.time()
                refresh_interval, market_interval = self._get_intervals()

                # Refresh per-symbol intelligence
                await self._refresh_all()

                # Refresh market-wide intelligence less frequently
                if time.time() - market_last_refresh > market_interval:
                    await self._refresh_market()
                    market_last_refresh = time.time()

                elapsed = (time.time() - t0) * 1000
                self._stats["refreshes"] += 1
                # Running average
                self._stats["avg_refresh_ms"] = (
                    self._stats["avg_refresh_ms"] * 0.9 + elapsed * 0.1
                )

                # Sleep for remaining interval
                sleep_time = max(1.0, refresh_interval - elapsed / 1000)
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Intelligence cache refresh error: %s", e)
                self._stats["errors"] += 1
                await asyncio.sleep(10)

    async def _refresh_all(self):
        """Refresh intelligence for all watchlist symbols in parallel."""
        if not self._watchlist:
            return

        tasks = [self._refresh_symbol(s) for s in self._watchlist]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _refresh_symbol(self, symbol: str):
        """Refresh intelligence for a single symbol with latency budget."""
        try:
            from app.services.perplexity_intelligence import get_perplexity_intel

            if not settings.PERPLEXITY_API_KEY:
                return

            intel = get_perplexity_intel()
            t0 = time.time()

            # Run news + institutional in parallel with latency budget
            budget = LATENCY_BUDGET_MS["cortex"] / 1000
            try:
                news, institutional = await asyncio.wait_for(
                    asyncio.gather(
                        intel.scan_breaking_news(symbol),
                        intel.get_institutional_flow(symbol),
                        return_exceptions=True,
                    ),
                    timeout=budget,
                )
            except asyncio.TimeoutError:
                logger.debug("Intelligence refresh for %s hit latency budget", symbol)
                news = {"error": "timeout"}
                institutional = {"error": "timeout"}

            # Social sentiment (sync, fast)
            social_data = {}
            try:
                from app.modules.social_news_engine.aggregators import aggregate_all
                from app.modules.social_news_engine.sentiment import score_text, score_to_0_100
                from app.modules.social_news_engine.config import DEFAULT_SOURCES
                social_items = aggregate_all([symbol], DEFAULT_SOURCES)
                if social_items:
                    texts = [it.get("text", "") for it in social_items if it.get("text")]
                    raw = score_text(" ".join(texts), use_vader=True) if texts else 0.0
                    score = score_to_0_100(raw)
                    social_data = {"score": score, "item_count": len(social_items)}
            except Exception:
                pass

            package = {
                "symbol": symbol,
                "cortex_news": news if not isinstance(news, Exception) else {"error": str(news)},
                "cortex_institutional": institutional if not isinstance(institutional, Exception) else {"error": str(institutional)},
                "social_sentiment": social_data,
                "refreshed_at": time.time(),
                "latency_ms": (time.time() - t0) * 1000,
            }

            self._symbol_cache[symbol] = CacheEntry(package)
            # Evict oldest entries if cache exceeds limit
            if len(self._symbol_cache) > MAX_SYMBOL_CACHE_SIZE:
                oldest_key = min(self._symbol_cache, key=lambda k: self._symbol_cache[k].created_at)
                if oldest_key not in self._watchlist:
                    self._symbol_cache.pop(oldest_key, None)

        except Exception as e:
            logger.debug("Symbol intelligence refresh failed for %s: %s", symbol, e)
            self._stats["errors"] += 1

    async def _refresh_market(self):
        """Refresh market-wide intelligence (fear/greed, macro)."""
        try:
            from app.services.perplexity_intelligence import get_perplexity_intel

            if not settings.PERPLEXITY_API_KEY:
                return

            intel = get_perplexity_intel()
            budget = LATENCY_BUDGET_MS["cortex"] / 1000

            try:
                fg, macro = await asyncio.wait_for(
                    asyncio.gather(
                        intel.get_fear_greed_context(),
                        intel.scan_fed_macro(),
                        return_exceptions=True,
                    ),
                    timeout=budget,
                )
            except asyncio.TimeoutError:
                fg = {"error": "timeout"}
                macro = {"error": "timeout"}

            if not isinstance(fg, Exception):
                self._market_cache["fear_greed"] = CacheEntry(fg, ttl=MARKET_REFRESH_INTERVAL)
            if not isinstance(macro, Exception):
                self._market_cache["macro"] = CacheEntry(macro, ttl=MARKET_REFRESH_INTERVAL)

        except Exception as e:
            logger.debug("Market intelligence refresh failed: %s", e)

    def get_status(self) -> Dict[str, Any]:
        """Status for dashboard/health checks."""
        symbol_entries = {}
        for sym, entry in self._symbol_cache.items():
            symbol_entries[sym] = {
                "freshness": entry.freshness,
                "age_seconds": round(entry.age_seconds, 1),
                "access_count": entry.access_count,
            }
        return {
            "running": self._running,
            "watchlist": list(self._watchlist),
            "cached_symbols": symbol_entries,
            "market_cache_keys": list(self._market_cache.keys()),
            "stats": self._stats.copy(),
            "latency_budgets": LATENCY_BUDGET_MS,
        }


# Singleton
_cache: Optional[IntelligenceCache] = None


def get_intelligence_cache() -> IntelligenceCache:
    global _cache
    if _cache is None:
        _cache = IntelligenceCache()
    return _cache
