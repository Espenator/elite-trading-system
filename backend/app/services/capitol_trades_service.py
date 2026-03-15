"""Capitol Trades service — congressional trading data.

Capitol Trades (capitoltrades.com) does not offer a public API.
Instead, we source congressional trade disclosures from the
Unusual Whales API (/congress/trading endpoint), which aggregates
the same STOCK Act disclosure data.

If Unusual Whales is unavailable, falls back to scraping the free
capitoltrades.com public table.

Used by: congressional_agent.py → _fetch_congressional_trades()
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE: Dict[str, Any] = {}
_CACHE_TTL = 600  # 10 minutes


async def get_trades_by_ticker(symbol: str) -> List[Dict[str, Any]]:
    """Get congressional trades for a specific ticker.

    Tries Unusual Whales API first, then falls back to scraping capitoltrades.com.
    """
    symbol = symbol.upper()

    # Check cache
    cache_key = f"congress_{symbol}"
    now = time.time()
    if cache_key in _CACHE and (now - _CACHE[cache_key].get("ts", 0)) < _CACHE_TTL:
        return _CACHE[cache_key]["data"]

    # Try Unusual Whales congress endpoint (primary source)
    trades = await _fetch_from_unusual_whales(symbol)
    if trades:
        _CACHE[cache_key] = {"data": trades, "ts": now}
        # C8: Publish congressional trades to MessageBus
        try:
            from app.core.message_bus import get_message_bus
            bus = get_message_bus()
            if bus._running:
                await bus.publish("perception.congressional", {
                    "type": "congressional_trades",
                    "symbol": symbol,
                    "trades": trades,
                    "source": "capitol_trades_service",
                    "timestamp": time.time(),
                })
                # Firehose v5: individual congress.trade events
                for t in trades:
                    await bus.publish("congress.trade", {
                        "symbol": symbol,
                        "politician": t.get("member", ""),
                        "transaction_type": t.get("transaction_type", ""),
                        "amount_range": t.get("amount", ""),
                        "disclosure_delay_days": None,
                        "source": "capitol_trades",
                    })
        except Exception:
            pass
        return trades

    # Fallback: scrape capitoltrades.com
    trades = await _scrape_capitol_trades(symbol)
    if trades:
        _CACHE[cache_key] = {"data": trades, "ts": now}
        # C8: Publish congressional trades to MessageBus (scrape fallback)
        try:
            from app.core.message_bus import get_message_bus
            bus = get_message_bus()
            if bus._running:
                await bus.publish("perception.congressional", {
                    "type": "congressional_trades",
                    "symbol": symbol,
                    "trades": trades,
                    "source": "capitol_trades_service",
                    "timestamp": time.time(),
                })
                for t in trades:
                    await bus.publish("congress.trade", {
                        "symbol": symbol,
                        "politician": t.get("member", ""),
                        "transaction_type": t.get("transaction_type", ""),
                        "amount_range": t.get("amount", ""),
                        "disclosure_delay_days": None,
                        "source": "capitol_trades",
                    })
        except Exception:
            pass
    return trades


async def _fetch_from_unusual_whales(symbol: str) -> List[Dict[str, Any]]:
    """Fetch congressional trades from Unusual Whales API."""
    api_key = (getattr(settings, "UNUSUAL_WHALES_API_KEY", None) or "").strip()
    if not api_key:
        return []

    base_url = (
        getattr(settings, "UNUSUAL_WHALES_BASE_URL", None)
        or "https://api.unusualwhales.com/api"
    ).rstrip("/")

    try:
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{base_url}/congress/trading",
                params={"symbol": symbol},
                headers=headers,
            )
        if resp.status_code != 200:
            logger.debug("UW congress endpoint returned %s", resp.status_code)
            return []

        data = resp.json()
        trades = data if isinstance(data, list) else data.get("data", data.get("trades", []))

        # Normalize to standard format expected by congressional_agent
        return [
            {
                "member": t.get("representative", t.get("politician", "")),
                "party": t.get("party", ""),
                "state": t.get("state", ""),
                "transaction_type": t.get("type", t.get("transaction_type", "")),
                "amount": t.get("amount", t.get("range", "")),
                "date": t.get("transaction_date", t.get("disclosure_date", "")),
                "symbol": symbol,
                "committee": t.get("committee", ""),
                "source": "unusual_whales",
            }
            for t in trades
        ]
    except Exception as e:
        logger.debug("UW congress fetch failed for %s: %s", symbol, e)
        return []


async def _scrape_capitol_trades(symbol: str) -> List[Dict[str, Any]]:
    """Scrape capitoltrades.com free public table as fallback."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        url = f"https://www.capitoltrades.com/trades?ticker={symbol}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code != 200:
            return []

        text = resp.text
        trades: List[Dict[str, Any]] = []

        # Capitol Trades renders a table with trade rows
        # Each row has: politician, party, trade type, date, amount, ticker
        rows = re.findall(
            r'<tr[^>]*>(.*?)</tr>',
            text, re.DOTALL,
        )

        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) < 4:
                continue

            # Strip HTML from cell contents
            clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]

            # Try to identify trade fields from cell content
            trade: Dict[str, Any] = {"symbol": symbol, "source": "capitol_trades"}
            for cell in clean:
                if cell.lower() in ("purchase", "sale", "buy", "sell", "exchange"):
                    trade["transaction_type"] = cell
                elif re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', cell):
                    trade["date"] = cell
                elif "$" in cell or re.match(r'\d+[,\d]*-', cell):
                    trade["amount"] = cell
                elif len(cell) > 3 and not cell.isdigit():
                    if "member" not in trade:
                        trade["member"] = cell

            if trade.get("transaction_type") or trade.get("member"):
                trades.append(trade)

        logger.debug("Scraped %d trades from capitoltrades.com for %s", len(trades), symbol)
        return trades

    except Exception as e:
        logger.debug("Capitol Trades scrape failed for %s: %s", symbol, e)
        return []


def clear_cache():
    """Clear the trade cache."""
    _CACHE.clear()
