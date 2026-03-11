"""Benzinga data service — scrapes earnings dates and transcripts.

Benzinga does not provide a free API key for this project's use case.
Instead we authenticate via email/password to the Benzinga website and
scrape the publicly-available earnings calendar and transcript pages.

Env vars:
    BENZINGA_EMAIL    – login email
    BENZINGA_PASSWORD – login password

If credentials are missing, functions return None gracefully so council
agents fall back to their secondary data sources.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_SESSION_COOKIE: Optional[str] = None


async def _get_session() -> Optional[httpx.Cookies]:
    """Authenticate with Benzinga and cache the session cookie."""
    global _SESSION_COOKIE

    email = getattr(settings, "BENZINGA_EMAIL", None) or ""
    password = getattr(settings, "BENZINGA_PASSWORD", None) or ""
    if not email or not password:
        logger.debug("Benzinga credentials not configured — skipping")
        return None

    if _SESSION_COOKIE is not None:
        return _SESSION_COOKIE

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.post(
                "https://www.benzinga.com/user/login",
                data={"email": email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code < 400:
                _SESSION_COOKIE = resp.cookies
                logger.info("Benzinga session authenticated")
                return _SESSION_COOKIE
            else:
                logger.warning("Benzinga login failed: %s", resp.status_code)
                return None
    except Exception as e:
        logger.warning("Benzinga login error: %s", e)
        return None


async def get_next_earnings_date(symbol: str) -> Optional[datetime]:
    """Get the next earnings date for a symbol from Benzinga calendar.

    Returns a timezone-aware datetime or None.
    """
    cookies = await _get_session()
    try:
        url = f"https://www.benzinga.com/stock/{symbol.upper()}/earnings"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, cookies=cookies)
        if resp.status_code != 200:
            return None

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
    """
    cookies = await _get_session()
    try:
        url = f"https://www.benzinga.com/quote/{symbol.upper()}/earnings-transcript"
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, cookies=cookies)
        if resp.status_code != 200:
            return None

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

        return {
            "symbol": symbol.upper(),
            "source": "benzinga",
            "text": clean[:50000],  # Cap at 50k chars
            "date": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.debug("Benzinga transcript fetch failed for %s: %s", symbol, e)
        return None


def invalidate_session():
    """Force re-authentication on next request."""
    global _SESSION_COOKIE
    _SESSION_COOKIE = None
