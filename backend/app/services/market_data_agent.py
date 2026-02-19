"""
Market Data Agent — one tick of data collection.
Scans: Finviz Elite, Alpaca, Unusual Whales. Pulls: FRED economic data, SEC EDGAR filings.
Run every 60s during market hours when agent is started (configurable via agent config).
"""

import logging
from typing import List, Tuple
from datetime import datetime, timezone

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

    # --- Unusual Whales (stub until integration) ---
    if run_unusual_whales:
        entries.append(("Unusual Whales: stub (integration pending)", "info"))

    # --- FRED economic data (stub until integration) ---
    if run_fred:
        entries.append(("FRED: stub (integration pending)", "info"))

    # --- SEC EDGAR filings (stub until integration) ---
    if run_edgar:
        entries.append(("SEC EDGAR: stub (integration pending)", "info"))

    return entries
