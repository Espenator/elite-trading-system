"""
SEC EDGAR Ingestion Adapter

Wraps SecEdgarService to provide incremental filings ingestion.
"""

from datetime import datetime
from typing import List, Optional
import hashlib
import logging

from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent
from app.services.sec_edgar_service import SecEdgarService

logger = logging.getLogger(__name__)


class SECEdgarAdapter(BaseSourceAdapter):
    """Adapter for SEC EDGAR filings data"""

    def __init__(self, checkpoint_store, message_bus=None):
        super().__init__(checkpoint_store, message_bus)
        self.sec_service = SecEdgarService()

    def get_source_name(self) -> str:
        return "sec_edgar"

    def get_source_kind(self) -> str:
        return "filings"

    async def validate_credentials(self) -> bool:
        """SEC EDGAR doesn't require API key, just User-Agent"""
        try:
            return bool(self.sec_service.user_agent)
        except Exception as e:
            logger.error(f"SEC EDGAR credential validation failed: {e}")
            return False

    async def fetch_incremental(
        self,
        last_cursor: Optional[str] = None,
        last_timestamp: Optional[datetime] = None
    ) -> List[SourceEvent]:
        """
        Fetch recent SEC filings

        For now, we just fetch the company tickers list periodically.
        In future, we can track specific companies' filings.
        """
        events = []

        try:
            # Fetch company tickers
            tickers_data = await self.sec_service.get_company_tickers()

            # Convert to events (this is a snapshot, not truly incremental)
            # In production, you'd track specific filings for specific companies
            for idx, company_info in tickers_data.items():
                if not isinstance(company_info, dict):
                    continue

                ticker = company_info.get("ticker")
                cik = company_info.get("cik_str")
                title = company_info.get("title")

                if not ticker:
                    continue

                # Create dedupe key from CIK
                dedupe_key = f"sec_{cik}"

                event = SourceEvent(
                    source=self.get_source_name(),
                    source_kind=self.get_source_kind(),
                    topic="sec_edgar.company",
                    symbol=ticker,
                    entity_id=str(cik),
                    occurred_at=datetime.utcnow(),
                    dedupe_key=dedupe_key,
                    payload_json={
                        "ticker": ticker,
                        "cik": cik,
                        "title": title
                    }
                )
                events.append(event)

            logger.info(f"SEC EDGAR: Fetched {len(events)} companies")

        except Exception as e:
            logger.error(f"SEC EDGAR fetch failed: {e}", exc_info=True)
            raise

        return events
