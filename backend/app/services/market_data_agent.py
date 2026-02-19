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

# SEC requires a descriptive User-Agent (company name + contact)
SEC_USER_AGENT = "EliteTradingSystem/1.0 (Market Data Agent; contact@example.com)"


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
    """Pull latest FRED series (e.g. CPI). Requires FRED_API_KEY in .env."""
    if not getattr(settings, "FRED_API_KEY", None) or not settings.FRED_API_KEY.strip():
        return [
            ("FRED: set FRED_API_KEY in .env (free at fred.stlouisfed.org)", "info")
        ]
    try:
        # CPI All Urban Consumers (CPIAUCSL) — one observation
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": "CPIAUCSL",
            "api_key": settings.FRED_API_KEY.strip(),
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, params=params)
        if r.status_code != 200:
            return [(f"FRED: HTTP {r.status_code}", "warning")]
        data = r.json()
        obs = (data.get("observations") or [])[:1]
        if obs and obs[0].get("value") != ".":
            val = obs[0].get("value")
            date = obs[0].get("date", "")
            return [(f"FRED CPI (CPIAUCSL): {val} ({date})", "success")]
        return [("FRED: no recent observation", "info")]
    except Exception as e:
        logger.exception("FRED fetch failed")
        return [(f"FRED: {str(e)[:80]}", "warning")]


async def _fetch_edgar() -> List[Tuple[str, str]]:
    """Pull SEC EDGAR company filings (recent 8-K / 10-K for a sample ticker). No API key; User-Agent required."""
    try:
        # Company tickers mapping (ticker -> CIK)
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers={"User-Agent": SEC_USER_AGENT},
            )
        if r.status_code != 200:
            return [(f"SEC EDGAR: HTTP {r.status_code}", "warning")]
        tickers_data = r.json()
        # Find AAPL CIK (example)
        cik_str = None
        for _, info in tickers_data.items():
            if isinstance(info, dict) and info.get("ticker") == "AAPL":
                cik_str = str(info.get("cik_str", "")).zfill(10)
                break
        if not cik_str:
            return [("SEC EDGAR: ticker lookup ok, no sample", "info")]
        # Recent submissions for company
        async with httpx.AsyncClient(timeout=15.0) as client:
            r2 = await client.get(
                f"https://data.sec.gov/submissions/CIK{cik_str}.json",
                headers={"User-Agent": SEC_USER_AGENT},
            )
        if r2.status_code != 200:
            return [(f"SEC EDGAR submissions: HTTP {r2.status_code}", "warning")]
        sub = r2.json()
        recent = (sub.get("recent", {}) or {}).get("form", [])[:5]
        filings = ", ".join(recent) if recent else "none"
        return [(f"SEC EDGAR AAPL recent: {filings}", "success")]
    except Exception as e:
        logger.exception("SEC EDGAR fetch failed")
        return [(f"SEC EDGAR: {str(e)[:80]}", "warning")]


async def _fetch_unusual_whales() -> List[Tuple[str, str]]:
    """Unusual Whales options flow. Requires UNUSUAL_WHALES_API_KEY (and optional base URL)."""
    api_key = getattr(settings, "UNUSUAL_WHALES_API_KEY", None) or ""
    base_url = (getattr(settings, "UNUSUAL_WHALES_BASE_URL", None) or "").rstrip("/")
    if not api_key or not api_key.strip():
        return [
            (
                "Unusual Whales: set UNUSUAL_WHALES_API_KEY in .env for options flow",
                "info",
            )
        ]
    try:
        # Common pattern: auth via header or query; adjust if your provider differs
        url = (
            f"{base_url}/api/flow"
            if base_url
            else "https://api.unusualwhales.com/api/flow"
        )
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Accept": "application/json",
                },
            )
        if r.status_code == 200:
            data = r.json() if r.content else {}
            count = (
                len(data)
                if isinstance(data, list)
                else (data.get("count") or data.get("total") or "ok")
            )
            return [(f"Unusual Whales: {count} flow entries", "success")]
        if r.status_code == 401:
            return [("Unusual Whales: invalid API key", "warning")]
        return [(f"Unusual Whales: HTTP {r.status_code}", "warning")]
    except httpx.ConnectError:
        return [("Unusual Whales: connection failed (check base URL)", "warning")]
    except Exception as e:
        logger.exception("Unusual Whales fetch failed")
        return [(f"Unusual Whales: {str(e)[:80]}", "warning")]
