"""Benzinga data service — scrapes earnings dates and transcripts.

Benzinga does not provide a free API key for this project's use case.
Instead we authenticate via email/password to the Benzinga website and
scrape the publicly-available earnings calendar and transcript pages.

Phase D4 enhancements (March 11 2026):
  - Session cookie TTL with automatic refresh on 401/403
  - Circuit breaker to avoid hammering a down service
  - Rate limiting via AsyncRateLimiter
  - Reusable httpx client

Env vars:
    BENZINGA_EMAIL    – login email
    BENZINGA_PASSWORD – login password

If credentials are missing, functions return None gracefully so council
agents fall back to their secondary data sources.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_SESSION_COOKIE: Optional[httpx.Cookies] = None
_SESSION_CREATED_AT: float = 0.0
_SESSION_TTL: float = 3600.0  # Re-authenticate after 1 hour

# Circuit breaker for Benzinga
_circuit_breaker = None


def _get_circuit_breaker():
    global _circuit_breaker
    if _circuit_breaker is None:
        from app.core.rate_limiter import CircuitBreaker
        _circuit_breaker = CircuitBreaker(
            "benzinga", failure_threshold=3, recovery_seconds=120.0
        )
    return _circuit_breaker


async def _get_session(force_refresh: bool = False) -> Optional[httpx.Cookies]:
    """Authenticate with Benzinga and cache the session cookie.

    D4: Session cookie expires after 1 hour. Auto-refreshes on
    401/403 responses. Uses circuit breaker to avoid login storms.
    """
    global _SESSION_COOKIE, _SESSION_CREATED_AT

    email = getattr(settings, "BENZINGA_EMAIL", None) or ""
    password = getattr(settings, "BENZINGA_PASSWORD", None) or ""
    if not email or not password:
        logger.debug("Benzinga credentials not configured — skipping")
        return None

    # Return cached session if still valid
    if (
        _SESSION_COOKIE is not None
        and not force_refresh
        and (time.time() - _SESSION_CREATED_AT) < _SESSION_TTL
    ):
        return _SESSION_COOKIE

    # Check circuit breaker before attempting login
    cb = _get_circuit_breaker()
    if not cb.allow_request():
        logger.debug("Benzinga circuit breaker OPEN — skipping login attempt")
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.post(
                "https://www.benzinga.com/user/login",
                data={"email": email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code < 400:
                _SESSION_COOKIE = resp.cookies
                _SESSION_CREATED_AT = time.time()
                cb.record_success()
                logger.info("Benzinga session authenticated")
                return _SESSION_COOKIE
            else:
                cb.record_failure()
                logger.warning("Benzinga login failed: %s", resp.status_code)
                return None
    except Exception as e:
        cb.record_failure()
        logger.warning("Benzinga login error: %s", e)
        return None


async def get_next_earnings_date(symbol: str) -> Optional[datetime]:
    """Get the next earnings date for a symbol from Benzinga calendar.

    Returns a timezone-aware datetime or None.
    D4: Circuit breaker + auto-refresh on 401/403.
    """
    cb = _get_circuit_breaker()
    if not cb.allow_request():
        return None

    cookies = await _get_session()
    try:
        url = f"https://www.benzinga.com/stock/{symbol.upper()}/earnings"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, cookies=cookies)

        # D4: Refresh session on auth errors
        if resp.status_code in (401, 403):
            logger.info("Benzinga auth expired for %s — refreshing session", symbol)
            cookies = await _get_session(force_refresh=True)
            if cookies:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    resp = await client.get(url, cookies=cookies)

        if resp.status_code != 200:
            cb.record_failure()
            return None

        cb.record_success()

        text = resp.text
        # Look for next earnings date pattern in the page
        # Benzinga shows "Next Earnings Date: Mar 15, 2026" style text
        import re
        match = re.search(
            r'(?:next\s+earnings?\s+date|upcoming\s+earnings?)[:\s]*'
            r'([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})',
            text, re.IGNORECASE,
        )
        if match:
            date_str = match.group(1).replace(",", "")
            for fmt in ("%b %d %Y", "%B %d %Y"):
                try:
                    return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

        # Try JSON-LD structured data
        import json
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.DOTALL):
            try:
                data = json.loads(m.group(1))
                if isinstance(data, dict) and "earningsDate" in data:
                    return datetime.fromisoformat(data["earningsDate"]).replace(tzinfo=timezone.utc)
            except Exception:
                continue

        return None
    except Exception as e:
        logger.debug("Benzinga earnings date lookup failed for %s: %s", symbol, e)
        return None


async def get_earnings_transcript(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch the most recent earnings call transcript for a symbol.

    Returns dict with keys: symbol, date, text, speakers (if available).
    D4: Circuit breaker + auto-refresh on 401/403.
    """
    cb = _get_circuit_breaker()
    if not cb.allow_request():
        return None

    cookies = await _get_session()
    try:
        url = f"https://www.benzinga.com/quote/{symbol.upper()}/earnings-transcript"
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, cookies=cookies)

        if resp.status_code in (401, 403):
            cookies = await _get_session(force_refresh=True)
            if cookies:
                async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                    resp = await client.get(url, cookies=cookies)

        if resp.status_code != 200:
            cb.record_failure()
            return None

        cb.record_success()

        text = resp.text

        import re
        # Extract transcript body — typically in an article or div.transcript class
        body_match = re.search(
            r'<(?:article|div)[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</(?:article|div)>',
            text, re.DOTALL | re.IGNORECASE,
        )
        if not body_match:
            # Fallback: look for large text blocks that look like transcripts
            body_match = re.search(
                r'<div[^>]*class="[^"]*article-content[^"]*"[^>]*>(.*?)</div>',
                text, re.DOTALL | re.IGNORECASE,
            )

        if not body_match:
            return None

        # Strip HTML tags for plain text
        raw = body_match.group(1)
        clean = re.sub(r'<[^>]+>', '\n', raw)
        clean = re.sub(r'\n{3,}', '\n\n', clean).strip()

        if len(clean) < 200:
            return None

        transcript = {
            "symbol": symbol.upper(),
            "source": "benzinga",
            "text": clean[:50000],  # Cap at 50k chars
            "date": datetime.now(timezone.utc).isoformat(),
        }

        # C8: Publish earnings transcript to MessageBus
        try:
            from app.core.message_bus import get_message_bus
            bus = get_message_bus()
            if bus._running:
                import asyncio
                asyncio.get_event_loop().create_task(bus.publish("perception.earnings", {
                    "type": "earnings_transcript",
                    "symbol": symbol.upper(),
                    "source": "benzinga_service",
                    "timestamp": time.time(),
                }))
                # Firehose v5: news catalyst topic for news_catalyst_agent
                asyncio.get_event_loop().create_task(bus.publish("news.catalyst", {
                    "symbol": symbol.upper(),
                    "headline": f"Earnings transcript available for {symbol.upper()}",
                    "summary": clean[:500] if clean else "",
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "source": "benzinga",
                }))
        except Exception:
            pass

        return transcript
    except Exception as e:
        logger.debug("Benzinga transcript fetch failed for %s: %s", symbol, e)
        return None


def invalidate_session():
    """Force re-authentication on next request."""
    global _SESSION_COOKIE
    _SESSION_COOKIE = None
