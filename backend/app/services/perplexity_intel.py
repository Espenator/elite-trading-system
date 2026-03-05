"""Perplexity Intel Service — live market context via Perplexity Sonar.

Provides real-time market intelligence by querying Perplexity's Sonar model
for live web context about stocks, sectors, macro events, etc.

Results are cached for a configurable TTL to avoid redundant API calls.

Usage:
    from app.services.perplexity_intel import get_perplexity_intel
    svc = get_perplexity_intel()
    context = await svc.get_market_context("AAPL")
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PerplexityIntelService:
    """Live market intelligence via Perplexity Sonar API.

    Parameters
    ----------
    cache_ttl_seconds : int
        How long to cache results (default 300 = 5 minutes).
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        self.cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._request_count: int = 0
        self._cache_hits: int = 0

    async def get_market_context(
        self, symbol: str, extra_context: str = ""
    ) -> Dict[str, Any]:
        """Get live market context for a symbol.

        Returns cached result if available and fresh.
        """
        cache_key = f"market:{symbol}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            self._cache_hits += 1
            return cached

        prompt = (
            f"What are the latest market developments, news, and analyst sentiment "
            f"for {symbol}? Include any recent earnings, SEC filings, insider trades, "
            f"or macro events that could affect the stock price. "
            f"Be concise and factual."
        )
        if extra_context:
            prompt += f"\n\nAdditional context: {extra_context}"

        try:
            from app.core.llm_router import get_llm_router, ModelTier
            router = get_llm_router()
            response = await router.route(
                prompt=prompt,
                complexity="live_context",
                system_prompt=(
                    "You are a financial market analyst. Provide factual, "
                    "concise market intelligence. No investment advice."
                ),
                force_tier=ModelTier.PERPLEXITY,
                max_tokens=512,
            )

            result = {
                "symbol": symbol,
                "context": response.text,
                "model": response.model_name,
                "latency_ms": response.latency_ms,
                "cost_usd": response.cost_usd,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cached": False,
            }
            self._cache[cache_key] = {
                "data": result,
                "expires": time.time() + self.cache_ttl,
            }
            self._request_count += 1
            return result

        except Exception as e:
            logger.warning("Perplexity context fetch failed for %s: %s", symbol, e)
            return {
                "symbol": symbol,
                "context": "",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def get_sector_context(self, sector: str) -> Dict[str, Any]:
        """Get live context for a market sector."""
        cache_key = f"sector:{sector}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            self._cache_hits += 1
            return cached

        prompt = (
            f"What are the latest developments affecting the {sector} sector? "
            f"Include regulatory changes, earnings trends, and macro factors. "
            f"Be concise."
        )

        try:
            from app.core.llm_router import get_llm_router, ModelTier
            router = get_llm_router()
            response = await router.route(
                prompt=prompt,
                complexity="live_context",
                force_tier=ModelTier.PERPLEXITY,
                max_tokens=512,
            )

            result = {
                "sector": sector,
                "context": response.text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._cache[cache_key] = {
                "data": result,
                "expires": time.time() + self.cache_ttl,
            }
            self._request_count += 1
            return result

        except Exception as e:
            logger.warning("Sector context fetch failed for %s: %s", sector, e)
            return {"sector": sector, "context": "", "error": str(e)}

    def _get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        """Return cached data if fresh, else None."""
        entry = self._cache.get(key)
        if entry and time.time() < entry["expires"]:
            result = dict(entry["data"])
            result["cached"] = True
            return result
        return None

    def get_status(self) -> Dict[str, Any]:
        """Return service status."""
        return {
            "requests": self._request_count,
            "cache_hits": self._cache_hits,
            "cache_size": len(self._cache),
            "cache_ttl_seconds": self.cache_ttl,
        }


_instance: Optional[PerplexityIntelService] = None


def get_perplexity_intel() -> PerplexityIntelService:
    """Get or create the PerplexityIntelService singleton."""
    global _instance
    if _instance is None:
        _instance = PerplexityIntelService()
    return _instance
