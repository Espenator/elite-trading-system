"""
Market Data Agent — one tick of data collection.
Scans: Finviz Elite, Alpaca, Unusual Whales. Pulls: FRED economic data, SEC EDGAR filings.
Run every 60s during market hours when agent is started (configurable via agent config).
"""

import logging
from typing import List, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

AGENT_NAME = "Market Data Agent"


async def run_tick(
    *,
    run_finviz: bool = True,
    run_alpaca: bool = True,
    run_fred: bool = True,
    run_edgar: bool = True,
    run_unusual_whales: bool = True,
) -> List[Tuple[str, str]]:
    """
    Run one Market Data Agent tick. Returns list of (message, level) for activity log.
    """
    entries: List[Tuple[str, str]] = []

    # --- Finviz Elite → symbol_universe (client link) ---
    if run_finviz:
        try:
            from app.services.finviz_service import FinvizService
            from app.modules.symbol_universe import set_tracked_symbols_from_finviz

            svc = FinvizService()
            stocks = await svc.get_stock_list()
            count = len(stocks) if stocks else 0
            # Push to symbol_universe so clients (ML, screeners, execution) get tracked symbols
            stored = set_tracked_symbols_from_finviz(stocks or [])
            entries.append(
                (
                    f"Finviz Elite: {count} symbols → symbol_universe: {stored} tracked",
                    "success",
                )
            )
        except Exception as e:
            logger.exception("Finviz tick failed")
            entries.append((f"Finviz: {str(e)[:80]}", "warning"))

    # --- Alpaca (market data / connection check) ---
    if run_alpaca:
        try:
            from app.services.alpaca_service import alpaca_service
            import httpx

            # Alpaca clock to verify connection and get market state
            url = f"{alpaca_service.base_url.rstrip('/')}/clock"
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    url,
                    headers=alpaca_service._get_headers(),
                )
            if r.status_code == 200:
                data = r.json()
                is_open = data.get("is_open", False)
                entries.append((f"Alpaca: connected, market_open={is_open}", "success"))
            else:
                entries.append((f"Alpaca: HTTP {r.status_code}", "warning"))
        except Exception as e:
            logger.exception("Alpaca tick failed")
            entries.append((f"Alpaca: {str(e)[:80]}", "warning"))

    # --- Unusual Whales (options flow) ---
    if run_unusual_whales:
        entries.extend(await _fetch_unusual_whales())

    # --- FRED economic data ---
    if run_fred:
        entries.extend(await _fetch_fred())

    # --- SEC EDGAR filings ---
    if run_edgar:
        entries.extend(await _fetch_edgar())

    return entries


async def _fetch_fred() -> List[Tuple[str, str]]:
    """Pull latest FRED series (e.g. CPI) via FredService."""
    try:
        from app.services.fred_service import FredService

        svc = FredService()
        result = await svc.get_latest_value("CPIAUCSL")
        if result:
            return [(f"FRED CPI (CPIAUCSL): {result['value']} ({result['date']})", "success")]
        return [("FRED: no recent observation", "info")]
    except ValueError as e:
        return [(f"FRED: {str(e)[:80]}", "info")]
    except Exception as e:
        logger.exception("FRED fetch failed")
        return [(f"FRED: {str(e)[:80]}", "warning")]


async def _fetch_edgar() -> List[Tuple[str, str]]:
    """Pull SEC EDGAR company filings via SecEdgarService."""
    try:
        from app.services.sec_edgar_service import SecEdgarService

        svc = SecEdgarService()
        forms = await svc.get_recent_forms("AAPL", limit=5)
        filings = ", ".join(forms) if forms else "none"
        return [(f"SEC EDGAR AAPL recent: {filings}", "success")]
    except Exception as e:
        logger.exception("SEC EDGAR fetch failed")
        msg = (str(e) or type(e).__name__ or "error")[:80]
        return [(f"SEC EDGAR: {msg}", "warning")]


async def _fetch_unusual_whales() -> List[Tuple[str, str]]:
    """Unusual Whales options flow via UnusualWhalesService."""
    try:
        from app.services.unusual_whales_service import UnusualWhalesService

        svc = UnusualWhalesService()
        data = await svc.get_flow_alerts()
        count = len(data) if isinstance(data, list) else (data.get("count") or data.get("total") or "ok")
        return [(f"Unusual Whales: {count} flow entries", "success")]
    except ValueError as e:
        return [(f"Unusual Whales: {str(e)[:80]}", "info")]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return [("Unusual Whales: invalid API key", "warning")]
        if e.response.status_code == 404:
            return [
                (
                    "Unusual Whales: endpoint not found — set UNUSUAL_WHALES_FLOW_PATH from api.unusualwhales.com/docs",
                    "info",
                )
            ]
        return [(f"Unusual Whales: HTTP {e.response.status_code}", "warning")]
    except httpx.ConnectError:
        return [("Unusual Whales: connection failed (check base URL)", "warning")]
    except Exception as e:
        logger.exception("Unusual Whales fetch failed")
        return [(f"Unusual Whales: {str(e)[:80]}", "warning")]
