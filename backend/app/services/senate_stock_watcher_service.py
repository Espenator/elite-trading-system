"""Senate Stock Watcher service — fallback for congressional trade data.

Wraps the senatestockwatcher.com JSON API (free, no key required).
This is a secondary source behind capitol_trades_service / Unusual Whales.

Used by: congressional_agent.py → _fetch_congressional_trades() (2nd fallback)
"""

import logging
import time
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

_CACHE: Dict[str, Any] = {}
_CACHE_TTL = 600


async def get_ticker_trades(symbol: str) -> List[Dict[str, Any]]:
    """Fetch Senate disclosure trades for a ticker from senatestockwatcher.com."""
    symbol = symbol.upper()
    cache_key = f"ssw_{symbol}"
    now = time.time()
    if cache_key in _CACHE and (now - _CACHE[cache_key].get("ts", 0)) < _CACHE_TTL:
        return _CACHE[cache_key]["data"]

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; EmbodierTrader/4.1)",
            "Accept": "application/json",
        }
        url = f"https://senatestockwatcher.com/api/trades/{symbol}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code != 200:
            logger.debug("Senate Stock Watcher returned %s for %s", resp.status_code, symbol)
            return []

        data = resp.json()
        trades = data if isinstance(data, list) else data.get("trades", [])

        # Normalize
        result = [
            {
                "member": t.get("senator", t.get("full_name", "")),
                "party": t.get("party", ""),
                "state": t.get("state", ""),
                "transaction_type": t.get("type", t.get("transaction_type", "")),
                "amount": t.get("amount", ""),
                "date": t.get("transaction_date", t.get("date", "")),
                "symbol": symbol,
                "source": "senate_stock_watcher",
            }
            for t in trades
        ]

        _CACHE[cache_key] = {"data": result, "ts": now}
        logger.debug("Senate Stock Watcher: %d trades for %s", len(result), symbol)
        return result

    except Exception as e:
        logger.debug("Senate Stock Watcher failed for %s: %s", symbol, e)
        return []
