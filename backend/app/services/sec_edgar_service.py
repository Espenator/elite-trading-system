"""SEC EDGAR API service for company filings and ticker/CIK lookup. No API key; User-Agent required."""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# SEC requires a descriptive User-Agent (company name + contact)
DEFAULT_USER_AGENT = "EliteTradingSystem/1.0 (Market Data Agent; contact@example.com)"


class SecEdgarService:
    """Service for SEC EDGAR company tickers and submissions (filings)."""

    def __init__(self, user_agent: Optional[str] = None):
        self.sec_gov_url = "https://www.sec.gov"
        self.data_sec_gov_url = "https://data.sec.gov"
        self.user_agent = (user_agent or DEFAULT_USER_AGENT).strip()
        if not self.user_agent:
            raise ValueError("SEC EDGAR requires a non-empty User-Agent.")

    def _headers(self) -> Dict[str, str]:
        return {"User-Agent": self.user_agent}

    async def get_company_tickers(self) -> Dict[str, Any]:
        """
        Fetch the SEC company tickers JSON (ticker -> cik_str, title, etc.).
        Returns dict keyed by index (0, 1, ...) with values { ticker, cik_str, title }.
        """
        url = f"{self.sec_gov_url}/files/company_tickers.json"
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def find_cik_by_ticker(
        self, tickers_data: Dict[str, Any], ticker: str
    ) -> Optional[str]:
        """
        From get_company_tickers() result, find CIK (zero-padded 10 chars) for a ticker.
        """
        ticker_upper = (ticker or "").strip().upper()
        if not ticker_upper:
            return None
        for _, info in tickers_data.items():
            if (
                isinstance(info, dict)
                and (info.get("ticker") or "").strip().upper() == ticker_upper
            ):
                cik = info.get("cik_str")
                if cik is not None:
                    return str(cik).zfill(10)
        return None

    async def get_submissions(self, cik: str) -> Dict[str, Any]:
        """
        Fetch company submissions for a CIK (10-digit string).
        Returns dict with 'recent' (forms, dates, etc.) and other metadata.
        """
        cik_padded = str(cik).zfill(10)
        url = f"{self.data_sec_gov_url}/submissions/CIK{cik_padded}.json"
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json()

    async def get_recent_forms(self, ticker: str, limit: int = 10) -> List[str]:
        """
        Get list of recent form types (e.g. 8-K, 10-K) for a ticker.
        Returns list of form type strings, most recent first.
        """
        tickers_data = await self.get_company_tickers()
        cik = self.find_cik_by_ticker(tickers_data, ticker)
        if not cik:
            return []
        sub = await self.get_submissions(cik)
        recent = (sub.get("recent") or {}).get("form", [])[:limit]
        return recent if isinstance(recent, list) else []
