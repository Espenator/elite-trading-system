"""SqueezeMetrics scraper — fetches DIX and GEX from squeezemetrics.com.

SqueezeMetrics publishes the Dark Index (DIX) and Gamma Exposure Index (GEX)
on their free public dashboard. There is no API — we scrape the public page.

DIX = Dark pool buying indicator (higher = more dark pool buying = bullish)
GEX = Gamma Exposure (positive = dealer hedging dampens moves, negative = amplifies)

Phase D4 enhancements (March 11 2026):
  - Circuit breaker to avoid hammering a down service
  - Staleness detection: warn if cached data is >24h old
  - Rate limiting via AsyncRateLimiter

Used by: dark_pool_agent.py → _fetch_dix_data()
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE: Dict[str, Any] = {}
_CACHE_TTL = 900  # 15 minutes — data updates once daily anyway
_STALENESS_THRESHOLD = 86400  # 24 hours — warn if data is older than this

# Circuit breaker
_circuit_breaker = None


def _get_circuit_breaker():
    global _circuit_breaker
    if _circuit_breaker is None:
        from app.core.rate_limiter import CircuitBreaker
        _circuit_breaker = CircuitBreaker(
            "squeezemetrics", failure_threshold=3, recovery_seconds=300.0
        )
    return _circuit_breaker


async def get_dix_gex() -> Optional[Dict[str, Any]]:
    """Scrape current DIX and GEX values from squeezemetrics.com.

    Returns:
        Dict with keys: dix, gex, date, source, stale (bool)
        None if scraping fails.

    D4: Circuit breaker + staleness detection.
    """
    now = time.time()

    # Return cached data if fresh
    if _CACHE.get("data") and (now - _CACHE.get("ts", 0)) < _CACHE_TTL:
        result = _CACHE["data"].copy()
        # Staleness check: warn if underlying data date is >24h old
        result["stale"] = (now - _CACHE.get("ts", 0)) > _STALENESS_THRESHOLD
        return result

    enabled = getattr(settings, "SQUEEZEMETRICS_ENABLED", "true")
    if str(enabled).lower() not in ("true", "1", "yes"):
        return None

    # D4: Circuit breaker check
    cb = _get_circuit_breaker()
    if not cb.allow_request():
        # Return stale cache if available when circuit is open
        if _CACHE.get("data"):
            result = _CACHE["data"].copy()
            result["stale"] = True
            result["circuit_open"] = True
            return result
        return None

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get("https://squeezemetrics.com/monitor/dix", headers=headers)

        if resp.status_code != 200:
            cb.record_failure()
            logger.warning("SqueezeMetrics returned %s", resp.status_code)
            # Return stale cache on error
            if _CACHE.get("data"):
                result = _CACHE["data"].copy()
                result["stale"] = True
                return result
            return None

        cb.record_success()
        text = resp.text

        # SqueezeMetrics embeds the data in JavaScript variables or a chart config
        # Look for DIX value — typically shown as a decimal like 0.45
        dix_match = re.search(
            r'(?:DIX|dix)["\s:=]*?(\d+\.\d{2,4})',
            text, re.IGNORECASE,
        )
        gex_match = re.search(
            r'(?:GEX|gex)["\s:=]*?(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)',
            text, re.IGNORECASE,
        )

        # Also try extracting from embedded JSON/chart data
        if not dix_match:
            # Look for chart data arrays — last value is most recent
            dix_array = re.search(r'(?:dix|DIX).*?\[([\d.,\s]+)\]', text, re.DOTALL)
            if dix_array:
                values = [float(v.strip()) for v in dix_array.group(1).split(",") if v.strip()]
                if values:
                    dix_val = values[-1]
                    dix_match = True  # flag that we found it

        if not gex_match:
            gex_array = re.search(r'(?:gex|GEX).*?\[([0-9eE+\-.,\s]+)\]', text, re.DOTALL)
            if gex_array:
                values = [float(v.strip()) for v in gex_array.group(1).split(",") if v.strip()]
                if values:
                    gex_val = values[-1]
                    gex_match = True

        # Build result
        result = {"source": "squeezemetrics", "date": None}

        if isinstance(dix_match, bool):
            result["dix"] = dix_val
        elif dix_match:
            result["dix"] = float(dix_match.group(1))
        else:
            result["dix"] = None

        if isinstance(gex_match, bool):
            result["gex"] = gex_val
        elif gex_match:
            result["gex"] = float(gex_match.group(1))
        else:
            result["gex"] = None

        # Extract date if available
        date_match = re.search(
            r'(?:date|as\s+of|updated)[:\s]*(\d{4}-\d{2}-\d{2})',
            text, re.IGNORECASE,
        )
        if date_match:
            result["date"] = date_match.group(1)

        if result["dix"] is not None or result["gex"] is not None:
            _CACHE["data"] = result
            _CACHE["ts"] = now
            logger.info("SqueezeMetrics DIX=%.4f GEX=%s", result.get("dix", 0), result.get("gex"))

            # C8: Publish DIX/GEX to MessageBus
            try:
                from app.core.message_bus import get_message_bus
                bus = get_message_bus()
                if bus._running:
                    import asyncio
                    asyncio.get_event_loop().create_task(bus.publish("perception.squeezemetrics", {
                        "type": "dix_gex",
                        "data": result,
                        "source": "squeezemetrics_service",
                        "timestamp": time.time(),
                    }))
                    # Firehose v5: dedicated dark pool topic for dark_pool_agent + gex_agent
                    asyncio.get_event_loop().create_task(bus.publish("market.dark_pool", {
                        "dix": result.get("dix"),
                        "gex": result.get("gex"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "squeezemetrics",
                    }))
            except Exception:
                pass

            return result

        logger.warning("SqueezeMetrics: could not parse DIX/GEX from page")
        return None

    except Exception as e:
        cb.record_failure()
        logger.warning("SqueezeMetrics scrape failed: %s", e)
        # Return stale cache on exception
        if _CACHE.get("data"):
            result = _CACHE["data"].copy()
            result["stale"] = True
            return result
        return None


def clear_cache():
    """Force refresh on next call."""
    _CACHE.clear()
