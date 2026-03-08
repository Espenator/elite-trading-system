"""SEC Edgar adapter for scheduled filings ingestion."""
import hashlib
from datetime import datetime
from typing import List, Optional
from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent
from app.services.sec_edgar_service import SecEdgarService


class SecEdgarAdapter(BaseSourceAdapter):
    """Adapter for SEC EDGAR filings data.

    Fetches recent company filings (8-K, 10-Q, 10-K, etc.).
    """

    def __init__(self, **kwargs):
        super().__init__(adapter_id="sec_edgar", **kwargs)
        self.edgar = SecEdgarService()
        # Track which form types to monitor
        self.form_types = ["8-K", "10-Q", "10-K", "S-1", "13F-HR"]

    async def fetch_events(self, since: Optional[datetime] = None) -> List[SourceEvent]:
        """Fetch recent SEC filings.

        Args:
            since: Optional timestamp for incremental fetching

        Returns:
            List of SourceEvent objects
        """
        events = []
        current_time = datetime.utcnow()

        try:
            self.logger.info("Fetching SEC Edgar recent filings")

            # Get recent filings for each form type
            for form_type in self.form_types:
                try:
                    filings = await self.edgar.get_recent_forms(form_type=form_type, limit=20)

                    for filing in filings:
                        symbol = filing.get("ticker") or filing.get("symbol")

                        # Create unique event ID
                        accession_number = filing.get("accessionNumber", "")
                        event_id = hashlib.sha256(
                            f"edgar_{form_type}_{accession_number}".encode()
                        ).hexdigest()[:16]

                        filing_date = filing.get("filingDate") or filing.get("filing_date")
                        event_time = datetime.fromisoformat(filing_date) if filing_date else current_time

                        event = SourceEvent(
                            event_id=event_id,
                            source="sec_edgar",
                            event_type=f"filing_{form_type.lower()}",
                            event_time=event_time,
                            symbol=symbol,
                            data=filing,
                            metadata={"form_type": form_type}
                        )
                        events.append(event)

                except Exception as e:
                    self.logger.error(f"Failed to fetch {form_type} filings: {e}")

        except Exception as e:
            self.logger.error(f"Failed to fetch SEC Edgar filings: {e}")

        return events

    def get_topic(self) -> str:
        """Get MessageBus topic for SEC Edgar events."""
        return "perception.edgar"
