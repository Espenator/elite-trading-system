"""
Market Data Agent — thin supervisor for ingestion adapters.

v3.0: Refactored into adapter-based architecture.  Each source is now a
``BaseSourceAdapter`` registered in the ``AdapterRegistry``.  This module
provides:

  * ``run_tick()`` — one legacy compatibility tick (delegates to adapters'
    ``poll_once()`` for sources that are still scheduled, and reports
    adapter health for streaming sources).
  * Adapter health summary for the activity log.

The heavy per-source fetch logic has moved into:
    ``app.services.ingestion.adapters.*``

The legacy ``run_tick()`` signature is preserved so that
``app.api.v1.agents.run_market_data_tick_if_running()`` keeps working
without any changes.

Fixes Issue #25 Task 5.
"""
import logging
import time
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
    Run one Market Data Agent tick.  Returns list of (message, level).

    v3.0: Delegates to ingestion adapters when available; falls back to
    legacy inline fetchers for backward compatibility.
    """
    entries: List[Tuple[str, str]] = []
    tracked_symbols: list = []

    # ── Try adapter-based path first ──────────────────────────────────
    try:
        from app.services.ingestion.registry import get_adapter_registry
        registry = get_adapter_registry()
        adapters = registry.all_adapters()
    except Exception:
        adapters = []

    # If adapters are running, report their health instead of duplicating fetches.
    adapter_names = {a.source_name for a in adapters if a._running}

    # --- Finviz Elite ---
    if run_finviz and "finviz" not in adapter_names:
        entries.extend(await _fetch_finviz_legacy())
    elif run_finviz and "finviz" in adapter_names:
        adapter = registry.get("finviz")
        h = adapter.health()
        entries.append((
            f"Finviz adapter: {h.get('state')} ({h.get('events_published', 0)} events)",
            "success" if h.get("state") == "healthy" else "info",
        ))

    # --- Alpaca connection check (lightweight, always inline) ---
    if run_alpaca:
        entries.extend(await _check_alpaca_connection())

    # --- Unusual Whales ---
    if run_unusual_whales and "unusual_whales" not in adapter_names:
        entries.extend(await _fetch_unusual_whales())
    elif run_unusual_whales and "unusual_whales" in adapter_names:
        adapter = registry.get("unusual_whales")
        h = adapter.health()
        entries.append((
            f"Unusual Whales adapter: {h.get('state')} ({h.get('events_published', 0)} events)",
            "success" if h.get("state") == "healthy" else "info",
        ))

    # --- FRED ---
    if run_fred and "fred" not in adapter_names:
        entries.extend(await _fetch_fred())
    elif run_fred and "fred" in adapter_names:
        adapter = registry.get("fred")
        h = adapter.health()
        entries.append((
            f"FRED adapter: {h.get('state')} ({h.get('events_published', 0)} events)",
            "success" if h.get("state") == "healthy" else "info",
        ))

    # --- SEC EDGAR ---
    if run_edgar and "sec_edgar" not in adapter_names:
        entries.extend(await _fetch_edgar())
    elif run_edgar and "sec_edgar" in adapter_names:
        adapter = registry.get("sec_edgar")
        h = adapter.health()
        entries.append((
            f"SEC EDGAR adapter: {h.get('state')} ({h.get('events_published', 0)} events)",
            "success" if h.get("state") == "healthy" else "info",
        ))

    # --- OpenClaw ---
    if run_openclaw and "openclaw" not in adapter_names:
        entries.extend(await _fetch_openclaw())
    elif run_openclaw and "openclaw" in adapter_names:
        adapter = registry.get("openclaw")
        h = adapter.health()
        entries.append((
            f"OpenClaw adapter: {h.get('state')} ({h.get('events_published', 0)} events)",
            "success" if h.get("state") == "healthy" else "info",
        ))

    # --- DuckDB Ingestion (legacy path — still needed for indicators + trade outcomes) ---
    if run_ingestion:
        entries.extend(await _run_ingestion(tracked_symbols))

    return entries


# ──────────────────────────────────────────────────────────────────────────
# Legacy inline fetchers (kept for backward compat when adapters aren't up)
# ──────────────────────────────────────────────────────────────────────────

async def _fetch_finviz_legacy() -> List[Tuple[str, str]]:
    """Legacy Finviz inline fetch."""
    try:
        from app.services.finviz_service import FinvizService
        from app.modules.symbol_universe import set_tracked_symbols_from_finviz

        svc = FinvizService()
        stocks = await svc.get_stock_list()
        count = len(stocks) if stocks else 0
        stored = set_tracked_symbols_from_finviz(stocks or [])
        return [(
            f"Finviz Elite: {count} symbols -> symbol_universe: {stored} tracked",
            "success",
        )]
    except Exception as e:
        logger.exception("Finviz tick failed")
        return [(f"Finviz: {str(e)[:80]}", "warning")]


async def _check_alpaca_connection() -> List[Tuple[str, str]]:
    """Alpaca clock / connectivity check."""
    try:
        from app.services.alpaca_service import alpaca_service

        url = f"{alpaca_service.base_url.rstrip('/')}/clock"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers=alpaca_service._get_headers())
        if r.status_code == 200:
            data = r.json()
            is_open = data.get("is_open", False)
            return [(f"Alpaca: connected, market_open={is_open}", "success")]
        return [(f"Alpaca: HTTP {r.status_code}", "warning")]
    except Exception as e:
        logger.exception("Alpaca tick failed")
        return [(f"Alpaca: {str(e)[:80]}", "warning")]


async def _run_ingestion(symbols: list) -> List[Tuple[str, str]]:
    """Persist collected data to DuckDB via data_ingestion service.

    Runs incremental ingestion (last 5 days) on each tick.
    For full backfill, use data_ingestion.ingest_all(symbols, days=252).
    """
    if not symbols:
        try:
            from app.modules.symbol_universe import get_tracked_symbols
            symbols = get_tracked_symbols()[:20]
        except Exception:
            pass

    if not symbols:
        return [("DuckDB ingestion: no symbols to ingest", "info")]

    try:
        from app.services.data_ingestion import data_ingestion

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
        from app.core.message_bus import get_message_bus

        try:
            from app.modules.symbol_universe import get_tracked_symbols
            symbols = get_tracked_symbols() or ["AAPL"]
        except Exception:
            symbols = ["AAPL"]

        svc = SecEdgarService()
        results = []
        for symbol in symbols[:5]:
            try:
                forms = await svc.get_recent_forms(symbol, limit=5)
                filing_data = {"symbol": symbol, "forms": forms}
                results.append(filing_data)

                try:
                    bus = get_message_bus()
                    if bus._running:
                        await bus.publish("perception.edgar", {
                            "type": "sec_filing",
                            "data": filing_data,
                            "source": "market_data_agent",
                            "timestamp": time.time(),
                        })
                except Exception:
                    pass
            except Exception:
                pass

        if results:
            summary = ", ".join(
                f"{r['symbol']}:{','.join(r['forms'][:2]) or 'none'}"
                for r in results
            )
            return [(f"SEC EDGAR ({len(results)} symbols): {summary[:80]}", "success")]
        return [("SEC EDGAR: no results", "info")]
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
            return [(
                "Unusual Whales: endpoint not found -- set UNUSUAL_WHALES_FLOW_PATH from api.unusualwhales.com/docs",
                "info",
            )]
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

        return [(
            f"OpenClaw: regime={regime_state}, {candidate_count} candidates, "
            f"top={top_ticker} ({top_score}), {whale_count} whale alerts, "
            f"scan={scan_date}",
            "success",
        )]
    except Exception as e:
        logger.exception("OpenClaw Bridge fetch failed")
        return [(f"OpenClaw: {str(e)[:80]}", "warning")]
