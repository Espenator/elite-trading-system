"""SecEdgarAdapter — polls SEC EDGAR for recent company filings.

Schedule: every 30 minutes.

For each tracked symbol, fetches the most recent filings via
:class:`~app.services.sec_edgar_service.SecEdgarService` and emits a
:class:`~app.models.source_event.SourceEvent` for each new filing (form type
+ accession number) not yet seen.

CheckpointStore key: ``sec_edgar.last_accession.<TICKER>`` — most recent
                     accession number seen per symbol.
Topic: ``ingestion.filing``
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.source_event import SourceEvent
from app.services.ingestion.base import BaseSourceAdapter

logger = logging.getLogger(__name__)

# Default set of form types to track (8-K = material events, 10-K/10-Q = financials)
DEFAULT_FORM_TYPES = {"8-K", "10-K", "10-Q", "SC 13G", "SC 13G/A"}

_CHECKPOINT_PREFIX = "sec_edgar.seen_accessions"


class SecEdgarAdapter(BaseSourceAdapter):
    """Polls SEC EDGAR filings for a watchlist of ticker symbols.

    Args:
        symbols:     List of tickers to monitor (default: S&P 500 mega-caps).
        form_types:  Set of SEC form types to emit events for.
        limit:       Max filings to fetch per symbol per poll.
    """

    name = "sec_edgar"
    source_kind = "poll"
    # SEC rate-limit: 10 requests/second; be conservative
    backoff_base = 2.0
    backoff_max = 120.0

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        form_types: Optional[set] = None,
        limit: int = 10,
    ) -> None:
        super().__init__()
        self._symbols = symbols or [
            "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "BRK.B",
        ]
        self._form_types = form_types or DEFAULT_FORM_TYPES
        self._limit = limit
        # CIK cache (ticker -> CIK string) — populated lazily
        self._cik_cache: Dict[str, Optional[str]] = {}

    async def fetch(self) -> List[SourceEvent]:
        from app.services.sec_edgar_service import SecEdgarService

        svc = SecEdgarService()

        # Build CIK map once per fetch cycle (cache avoids repeated API calls)
        if not self._cik_cache:
            try:
                tickers_data = await svc.get_company_tickers()
                for sym in self._symbols:
                    self._cik_cache[sym] = svc.find_cik_by_ticker(tickers_data, sym)
            except Exception as exc:  # noqa: BLE001
                logger.warning("SecEdgarAdapter: could not fetch CIK map: %s", exc)
                return []

        events: List[SourceEvent] = []
        seq = 0

        for ticker in self._symbols:
            cik = self._cik_cache.get(ticker)
            if not cik:
                continue

            try:
                submissions = await svc.get_submissions(cik)
            except Exception as exc:  # noqa: BLE001
                logger.debug("SecEdgarAdapter: %s submissions failed: %s", ticker, exc)
                continue

            recent: Dict[str, Any] = submissions.get("recent", {})
            forms: List[str] = recent.get("form", [])
            accessions: List[str] = recent.get("accessionNumber", [])
            filed_dates: List[str] = recent.get("filingDate", [])

            seen_key = f"{_CHECKPOINT_PREFIX}.{ticker}"
            seen_accessions: List[str] = self.checkpoint.get(seen_key) or []
            seen_set = set(seen_accessions)
            new_seen: List[str] = []

            for form, acc, filed in zip(forms, accessions, filed_dates):
                if form not in self._form_types:
                    continue
                if acc in seen_set:
                    continue

                events.append(
                    SourceEvent(
                        source=self.name,
                        source_kind=self.source_kind,
                        topic="ingestion.filing",
                        payload={
                            "ticker": ticker,
                            "cik": cik,
                            "form_type": form,
                            "accession_number": acc,
                            "filing_date": filed,
                        },
                        symbol=ticker,
                        occurred_at=datetime.fromisoformat(filed) if filed else None,
                        sequence=seq,
                    )
                )
                new_seen.append(acc)
                seen_set.add(acc)
                seq += 1

                if len(new_seen) >= self._limit:
                    break

            if new_seen:
                # Keep only the most recent 200 accessions to bound memory
                combined = (seen_accessions + new_seen)[-200:]
                self.checkpoint.set(seen_key, combined)

        logger.info(
            "SecEdgarAdapter: %d new filing events for %d symbols",
            len(events), len(self._symbols),
        )
        return events

    async def close(self) -> None:
        self._cik_cache.clear()  # Release cached CIK map
