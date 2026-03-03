"""
Market Data Agent — one tick of data collection.
Scans: Finviz Elite, Alpaca, Unusual Whales, OpenClaw Bridge.
Pulls: FRED economic data, SEC EDGAR filings.

v2.0: Now persists all data to DuckDB via data_ingestion service.
Run every 60s during market hours when agent is started.

Fixes Issue #25 Task 5.
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
    run_openclaw: bool = True,
    run_ingestion: bool = True,
) -> List[Tuple[str, str]]:
    """
    Run one Market Data Agent tick. Returns list of (message, level) for activity log.

    v2.0: Added run_ingestion flag. When True, persists all fetched data
    to DuckDB via data_ingestion service after collection.
    """
    entries: List[Tuple[str, str]] = []

    tracked_symbols: list = []

    # --- Finviz Elite -> symbol_universe (client link) ---
    if run_finviz:
        try:
            from app.services.finviz_service import FinvizService
            from app.modules.symbol_universe import set_tracked_symbols_from_finviz

            svc = FinvizService()
            stocks = await svc.get_stock_list()
            count = len(stocks) if stocks else 0
            stored = set_tracked_symbols_from_finviz(stocks or [])
            tracked_symbols = list(stocks or []) if isinstance(stocks, list) else []
            # Extract just ticker strings if stocks are dicts
            if tracked_symbols and isinstance(tracked_symbols[0], dict):
                tracked_symbols = [
                    s.get("ticker") or s.get("symbol") or s.get("Ticker", "")
                    for s in tracked_symbols
                ]
                tracked_symbols = [t for t in tracked_symbols if t]
            entries.append(
                (
                    f"Finviz Elite: {count} symbols -> symbol_universe: {stored} tracked",
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

    # --- OpenClaw Bridge (regime, candidates, whale flow from Gist) ---
    if run_openclaw:
        entries.extend(await _fetch_openclaw())

    # --- DuckDB Ingestion (persist everything collected above) ---
    if run_ingestion:
        entries.extend(await _run_ingestion(tracked_symbols))

    return entries


async def _run_ingestion(symbols: list) -> List[Tuple[str, str]]:
    """Persist collected data to DuckDB via data_ingestion service.

    Runs incremental ingestion (last 5 days) on each tick.
    For full backfill, use data_ingestion.ingest_all(symbols, days=252).
    """
    if not symbols:
        # Fallback: use tracked symbols from symbol_universe
        try:
            from app.modules.symbol_universe import get_tracked_symbols
            symbols = get_tracked_symbols()[:20]
        except Exception:
            pass

    if not symbols:
        return [("DuckDB ingestion: no symbols to ingest", "info")]

    try:
        from app.services.data_ingestion import data_ingestion

        # Incremental: last 5 days of bars + indicators + flow + macro
        report = await data_ingestion.ingest_all(symbols[:20], days=5)

        ohlcv_total = report.get("ohlcv", {}).get("total_rows", 0)
        indicator_count = report.get("indicators", 0)
        flow_count = report.get("options_flow", 0)
        macro_count = report.get("macro", 0)
        trade_count = report.get("trade_outcomes", 0)

        health = report.get("duckdb_health", {})

        msg = (
            f"DuckDB ingestion: {ohlcv_total} OHLCV, {indicator_count} indicators, "
            f"{flow_count} flow, {macro_count} macro, {trade_count} trades"
        )

        if health:
            msg += f" | tables={health.get('total_tables', '?')}, rows={health.get('total_rows', '?')}"

        return [(msg, "success")]

    except Exception as e:
        logger.exception("DuckDB ingestion failed")
        return [(f"DuckDB ingestion: {str(e)[:80]}", "warning")]


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
                    "Unusual Whales: endpoint not found -- set UNUSUAL_WHALES_FLOW_PATH from api.unusualwhales.com/docs",
                    "info",
                )
            ]
        return [(f"Unusual Whales: HTTP {e.response.status_code}", "warning")]
    except httpx.ConnectError:
        return [("Unusual Whales: connection failed (check base URL)", "warning")]
    except Exception as e:
        logger.exception("Unusual Whales fetch failed")
        return [(f"Unusual Whales: {str(e)[:80]}", "warning")]


async def _fetch_openclaw() -> List[Tuple[str, str]]:
    """OpenClaw Bridge: fetch regime, candidates, and whale flow from Gist."""
    try:
        from app.services.openclaw_bridge_service import openclaw_bridge

        health = await openclaw_bridge.get_health()
        if not health.get("connected"):
            if not health.get("gist_id_configured"):
                return [("OpenClaw: OPENCLAW_GIST_ID not set (skip)", "info")]
            return [("OpenClaw: Gist fetch failed", "warning")]

        regime = await openclaw_bridge.get_regime()
        candidates = await openclaw_bridge.get_top_candidates(n=5)
        whale_flow = await openclaw_bridge.get_whale_flow()

        regime_state = regime.get("state", "UNKNOWN")
        candidate_count = len(candidates)
        whale_count = len(whale_flow)
        scan_date = regime.get("scan_date", "?")

        top_ticker = candidates[0].get("ticker", "?") if candidates else "none"
        top_score = candidates[0].get("composite_score", 0) if candidates else 0

        entries = [
            (
                f"OpenClaw: regime={regime_state}, {candidate_count} candidates, "
                f"top={top_ticker} ({top_score}), {whale_count} whale alerts, "
                f"scan={scan_date}",
                "success",
            )
        ]
        return entries
    except Exception as e:
        logger.exception("OpenClaw Bridge fetch failed")
        return [(f"OpenClaw: {str(e)[:80]}", "warning")]
