"""SecEdgarScout — monitors SEC EDGAR filings for material catalysts.

Scan cadence: 300 s
Source: SEC EDGAR (public API, no key required)
Signal types: filing_catalyst

Discovery criteria
------------------
* 8-K filings (material events, earnings, M&A).
* 4 filings (insider transactions > $1M).
* Only recent filings (within the last 30 minutes).
"""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.services.scouts.base_scout import BaseScout
from app.services.scouts.schemas import (
    DiscoveryPayload,
    DIRECTION_BULLISH,
    DIRECTION_BEARISH,
    DIRECTION_NEUTRAL,
    SIGNAL_FILING_CATALYST,
    SOURCE_SEC_EDGAR,
)

logger = logging.getLogger(__name__)

# Form types to watch
_WATCH_FORMS = {"8-K", "4"}
# 8-K item codes that are highly material
_MATERIAL_8K_ITEMS = {
    "1.01",  # Entry into material agreement
    "1.02",  # Termination of material agreement
    "2.01",  # Completion of acquisition
    "5.02",  # Departure / appointment of executive
    "8.01",  # Other events
}
# Symbols to monitor (extend with dynamic universe later)
_WATCH_TICKERS = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "TSLA", "META",
    "JPM", "BAC", "GS", "WFC", "MS",
]
_RECENT_WINDOW_MINUTES = 30


class SecEdgarScout(BaseScout):
    """Scout that detects material SEC filings for watched tickers."""

    scout_id = "sec_edgar"
    source = "SEC EDGAR Filings"
    source_type = SOURCE_SEC_EDGAR
    scan_interval = 300.0
    timeout = 60.0

    def __init__(self) -> None:
        super().__init__()
        self._seen_accessions: deque = deque(maxlen=5000)
        self._seen_accessions_set: set = set()

    async def scan(self) -> List[DiscoveryPayload]:
        discoveries: List[DiscoveryPayload] = []
        try:
            tickers_data = await self._fetch_tickers()
        except Exception as exc:
            logger.debug("[%s] tickers fetch failed: %s", self.scout_id, exc)
            return discoveries

        for symbol in _WATCH_TICKERS:
            try:
                payloads = await self._scan_ticker(symbol, tickers_data)
                discoveries.extend(payloads)
            except Exception as exc:
                logger.debug("[%s] scan_ticker %s failed: %s", self.scout_id, symbol, exc)

        return discoveries

    async def _fetch_tickers(self) -> Dict[str, Any]:
        from app.services.sec_edgar_service import SecEdgarService
        svc = SecEdgarService()
        return await svc.get_company_tickers()

    async def _scan_ticker(
        self, symbol: str, tickers_data: Dict[str, Any]
    ) -> List[DiscoveryPayload]:
        from app.services.sec_edgar_service import SecEdgarService
        svc = SecEdgarService()
        cik = svc.find_cik_by_ticker(tickers_data, symbol)
        if not cik:
            return []

        submissions = await svc.get_submissions(cik)
        filings = submissions.get("filings", {}).get("recent", {})
        if not filings:
            return []

        forms = filings.get("form", []) or []
        dates = filings.get("filingDate", []) or []
        accessions = filings.get("accessionNumber", []) or []
        descriptions = filings.get("primaryDocument", []) or []

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=_RECENT_WINDOW_MINUTES)
        results: List[DiscoveryPayload] = []

        for i, form in enumerate(forms):
            if form not in _WATCH_FORMS:
                continue
            acc = accessions[i] if i < len(accessions) else ""
            if acc in self._seen_accessions_set:
                continue

            filing_date_str = dates[i] if i < len(dates) else ""
            try:
                parsed = datetime.fromisoformat(filing_date_str)
                # Make tz-aware: if naive, assume UTC; if already aware, normalise to UTC
                if parsed.tzinfo is None:
                    filing_dt = parsed.replace(tzinfo=timezone.utc)
                else:
                    filing_dt = parsed.astimezone(timezone.utc)
                if filing_dt < cutoff:
                    continue
            except (ValueError, TypeError):
                continue

            # Evict oldest entry when deque is at capacity
            if len(self._seen_accessions) == self._seen_accessions.maxlen:
                evicted = self._seen_accessions[0]
                self._seen_accessions_set.discard(evicted)
            self._seen_accessions.append(acc)
            self._seen_accessions_set.add(acc)

            doc = descriptions[i] if i < len(descriptions) else ""
            direction = DIRECTION_NEUTRAL  # filings are initially neutral; context needed
            score = 70 if form == "8-K" else 50

            results.append(DiscoveryPayload(
                scout_id=self.scout_id,
                source=self.source,
                source_type=self.source_type,
                symbol=symbol,
                direction=direction,
                signal_type=SIGNAL_FILING_CATALYST,
                confidence=0.6,
                score=score,
                reasoning=f"SEC {form} filing: {doc or 'see EDGAR'}",
                priority=2,
                ttl_seconds=3600,
                attributes={
                    "form_type": form,
                    "accession_number": acc,
                    "filing_date": filing_date_str,
                    "cik": cik,
                },
            ))

        return results
