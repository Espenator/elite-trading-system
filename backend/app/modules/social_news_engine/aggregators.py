"""
Aggregators: fetch or stub data from Stockgeist, News API, Discord, X (Twitter).
Each returns list of items with ticker and text (or score) for sentiment aggregation.
"""

import base64
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TWITTER_API_BASE = "https://api.twitter.com"
_x_oauth2_bearer_cache: Optional[str] = None
_x_oauth2_bearer_expires: float = 0
CACHE_TTL_SEC = 300  # 5 min


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_stockgeist(
    symbols: List[str], limit_per_symbol: int = 5
) -> List[Dict[str, Any]]:
    """Stockgeist: social sentiment API. Set STOCKGEIST_API_KEY and STOCKGEIST_BASE_URL in config to enable."""
    api_key = (settings.STOCKGEIST_API_KEY or "").strip()
    if not api_key:
        return []
    base = (settings.STOCKGEIST_BASE_URL or "https://api.stockgeist.ai").rstrip("/")
    out: List[Dict[str, Any]] = []
    with httpx.Client(timeout=15.0) as client:
        for symbol in (symbols or [])[:20]:
            if not symbol or not str(symbol).strip():
                continue
            sym = str(symbol).strip().upper()
            try:
                # Stockgeist API v2: token auth; try stock sentiment or message metrics endpoint
                r = client.get(
                    f"{base}/v2/stock/{sym}",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Accept": "application/json",
                    },
                )
                if r.status_code != 200:
                    logger.debug(
                        "Stockgeist %s: %s %s", sym, r.status_code, r.text[:150]
                    )
                    continue
                data = r.json() if r.content else {}
                # If API returns messages/text list, use them; else use summary or sentiment score as text
                messages = (
                    data.get("messages") or data.get("posts") or data.get("items") or []
                )
                if isinstance(messages, list):
                    for m in messages[:limit_per_symbol]:
                        text = m.get("text") or m.get("content") or m.get("body") or ""
                        if isinstance(m, dict) and text:
                            out.append(
                                {
                                    "source": "stockgeist",
                                    "ticker": sym,
                                    "text": str(text)[:2000],
                                    "timestamp": m.get("created_at")
                                    or m.get("timestamp")
                                    or _iso_now(),
                                }
                            )
                if not messages and data:
                    # No message list: use sentiment summary as one item so symbol gets a score
                    summary = (
                        data.get("sentiment_summary")
                        or data.get("summary")
                        or data.get("description")
                    )
                    score = data.get("sentiment_score") or data.get("score")
                    if summary or score is not None:
                        text = (
                            summary or f"Sentiment score {score}"
                            if score is not None
                            else "Stockgeist data"
                        )
                        out.append(
                            {
                                "source": "stockgeist",
                                "ticker": sym,
                                "text": str(text)[:2000],
                                "timestamp": data.get("timestamp") or _iso_now(),
                            }
                        )
            except Exception as e:
                logger.debug("Stockgeist %s error: %s", sym, e)
    return out


def fetch_news_api(
    symbols: List[str], limit_per_symbol: int = 5
) -> List[Dict[str, Any]]:
    """News API: headline/snippet fetch from newsapi.org. Set NEWS_API_KEY in config to enable."""
    api_key = (settings.NEWS_API_KEY or "").strip()
    if not api_key:
        return []
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=1)
    from_str = from_date.strftime("%Y-%m-%d")
    out: List[Dict[str, Any]] = []
    page_size = min(100, max(5, limit_per_symbol))
    with httpx.Client(timeout=15.0) as client:
        for symbol in (symbols or [])[:20]:
            if not symbol or not str(symbol).strip():
                continue
            sym = str(symbol).strip().upper()
            try:
                r = client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": sym,
                        "from": from_str,
                        "sortBy": "publishedAt",
                        "pageSize": page_size,
                        "language": "en",
                        "apiKey": api_key,
                    },
                )
                if r.status_code != 200:
                    logger.debug("News API %s: %s %s", sym, r.status_code, r.text[:150])
                    continue
                data = r.json()
                if data.get("status") != "ok":
                    continue
                for art in (data.get("articles") or [])[:limit_per_symbol]:
                    title = (art.get("title") or "").strip()
                    desc = (art.get("description") or "").strip()
                    content = (art.get("content") or "").strip()
                    text = title
                    if desc:
                        text = f"{text} {desc}" if text else desc
                    if content:
                        text = f"{text} {content[:500]}" if text else content[:500]
                    if not text:
                        continue
                    out.append(
                        {
                            "source": "news_api",
                            "ticker": sym,
                            "text": text[:2000],
                            "timestamp": art.get("publishedAt") or _iso_now(),
                        }
                    )
            except Exception as e:
                logger.debug("News API %s error: %s", sym, e)
    return out


def get_discord_channel_ids() -> List[str]:
    """Parse DISCORD_CHANNEL_IDS from config (comma-separated)."""
    raw = (settings.DISCORD_CHANNEL_IDS or "").strip()
    if not raw:
        return []
    return [c.strip() for c in raw.split(",") if c.strip()]


def _discord_parse_mentioned_symbols(content: str, symbols: List[str]) -> List[str]:
    """Return list of symbols mentioned in content ($SYMBOL or word-boundary SYMBOL)."""
    if not content or not symbols:
        return []
    text = content.upper()
    seen = set()
    sym_set = {str(s).strip().upper() for s in symbols if s}
    for sym in sym_set:
        if not sym or len(sym) < 2:
            continue
        if (
            f"${sym}" in text
            or f" ${sym} " in text
            or text.startswith(sym + " ")
            or text.endswith(" " + sym)
        ):
            seen.add(sym)
        # Word boundary: SYMBOL surrounded by non-alphanumeric
        if re.search(r"(?<![A-Z0-9])" + re.escape(sym) + r"(?![A-Z0-9])", text):
            seen.add(sym)
    return list(seen)


def fetch_discord(
    symbols: List[str], limit_per_symbol: int = 5
) -> List[Dict[str, Any]]:
    """Discord: fetch messages from monitored channels via REST API. Requires DISCORD_BOT_TOKEN and DISCORD_CHANNEL_IDS."""
    token = (settings.DISCORD_BOT_TOKEN or "").strip()
    if not token:
        return []
    channel_ids = get_discord_channel_ids()
    if not channel_ids:
        return []
    symbol_set = [str(s).strip().upper() for s in (symbols or []) if str(s).strip()]
    out: List[Dict[str, Any]] = []
    limit = min(100, max(10, limit_per_symbol * 2))
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=15.0) as client:
        for channel_id in channel_ids[:25]:
            try:
                r = client.get(
                    f"{settings.DISCORD_API_BASE.rstrip('/')}/channels/{channel_id}/messages",
                    params={"limit": limit},
                    headers=headers,
                )
                if r.status_code == 401:
                    logger.warning("Discord: invalid bot token (401)")
                    break
                if r.status_code == 403:
                    logger.debug("Discord channel %s: forbidden (403)", channel_id)
                    continue
                if r.status_code == 404:
                    continue
                if r.status_code != 200:
                    logger.debug(
                        "Discord channel %s: %s %s",
                        channel_id,
                        r.status_code,
                        r.text[:100],
                    )
                    continue
                messages = r.json() if r.content else []
                if not isinstance(messages, list):
                    continue
                for msg in messages:
                    content = (msg.get("content") or "").strip()
                    if not content:
                        continue
                    timestamp = msg.get("timestamp") or _iso_now()
                    mentioned = _discord_parse_mentioned_symbols(content, symbol_set)
                    for sym in mentioned[:5]:
                        out.append(
                            {
                                "source": "discord",
                                "ticker": sym,
                                "text": content[:2000],
                                "timestamp": timestamp,
                            }
                        )
            except Exception as e:
                logger.debug("Discord channel %s error: %s", channel_id, e)
    return out


def _x_credentials_configured() -> bool:
    """True if Bearer Token is set or OAuth 2.0 Client ID + Secret for app-only token."""
    return bool(
        (settings.TWITTER_BEARER_TOKEN or "").strip()
        or (
            (settings.X_OAUTH2_CLIENT_ID or "").strip()
            and (settings.X_OAUTH2_CLIENT_SECRET or "").strip()
        )
    )


def _get_twitter_bearer_token() -> Optional[str]:
    """Return Bearer token: from TWITTER_BEARER_TOKEN or via OAuth 2.0 client credentials."""
    bearer = (settings.TWITTER_BEARER_TOKEN or "").strip()
    if bearer:
        return bearer
    client_id = (settings.X_OAUTH2_CLIENT_ID or "").strip()
    client_secret = (settings.X_OAUTH2_CLIENT_SECRET or "").strip()
    if not client_id or not client_secret:
        return None
    global _x_oauth2_bearer_cache, _x_oauth2_bearer_expires
    if _x_oauth2_bearer_cache and time.time() < _x_oauth2_bearer_expires:
        return _x_oauth2_bearer_cache
    try:
        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                f"{TWITTER_API_BASE}/2/oauth2/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {creds}",
                },
                data={"grant_type": "client_credentials"},
            )
        if r.status_code != 200:
            logger.warning(
                "Twitter OAuth2 token failed: %s %s", r.status_code, r.text[:200]
            )
            return None
        data = r.json()
        _x_oauth2_bearer_cache = data.get("access_token")
        _x_oauth2_bearer_expires = time.time() + CACHE_TTL_SEC
        return _x_oauth2_bearer_cache
    except Exception as e:
        logger.warning("Twitter OAuth2 token error: %s", e)
        return None


def fetch_twitter_x(
    symbols: List[str], limit_per_symbol: int = 5
) -> List[Dict[str, Any]]:
    """X (Twitter): search recent tweets by ticker via API v2. Uses Bearer Token or OAuth 2.0 client credentials."""
    if not _x_credentials_configured():
        return []
    bearer = _get_twitter_bearer_token()
    if not bearer:
        return []
    out: List[Dict[str, Any]] = []
    max_results = min(100, max(10, limit_per_symbol))
    with httpx.Client(timeout=15.0) as client:
        for symbol in (symbols or [])[:15]:
            if not symbol or not str(symbol).strip():
                continue
            sym = str(symbol).strip().upper()
            # Cashtag or keyword; exclude retweets for cleaner sentiment
            query = f"${sym} OR {sym} -is:retweet lang:en"
            try:
                r = client.get(
                    f"{TWITTER_API_BASE}/2/tweets/search/recent",
                    params={
                        "query": query,
                        "max_results": max_results,
                        "tweet.fields": "created_at,text",
                    },
                    headers={
                        "Authorization": f"Bearer {bearer}",
                        "Content-Type": "application/json",
                    },
                )
                if r.status_code != 200:
                    logger.debug(
                        "Twitter search %s: %s %s", sym, r.status_code, r.text[:150]
                    )
                    continue
                data = r.json()
                for tweet in data.get("data") or []:
                    text = (tweet.get("text") or "").strip()
                    if not text:
                        continue
                    created = tweet.get("created_at") or _iso_now()
                    out.append(
                        {
                            "source": "twitter",
                            "ticker": sym,
                            "text": text,
                            "timestamp": created,
                        }
                    )
            except Exception as e:
                logger.debug("Twitter search %s error: %s", sym, e)
    return out


def aggregate_all(
    symbols: List[str],
    sources: List[str],
) -> List[Dict[str, Any]]:
    """
    Run all requested source aggregators; return combined list of {source, ticker, text}.
    If no API keys, returns mock items so sentiment pipeline still runs (for demo).
    """
    out: List[Dict[str, Any]] = []
    source_fns = {
        "stockgeist": fetch_stockgeist,
        "news_api": fetch_news_api,
        "discord": fetch_discord,
        "twitter": fetch_twitter_x,
    }
    for name in sources:
        fn = source_fns.get(name)
        if not fn:
            continue
        try:
            items = fn(symbols[:20], limit_per_symbol=3)
            out.extend(items)
        except Exception as e:
            logger.debug("Aggregator %s failed: %s", name, e)

    # If no real data, add minimal mock so we still produce one aggregate score for first symbol
    if not out and symbols:
        for s in symbols[:5]:
            out.append(
                {
                    "source": "mock",
                    "ticker": s,
                    "text": "Market update. Neutral tone.",
                    "timestamp": _iso_now(),
                }
            )
    return out
