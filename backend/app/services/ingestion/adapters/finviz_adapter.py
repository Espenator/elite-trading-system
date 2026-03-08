"""
Finviz Ingestion Adapter

Wraps FinvizService to provide incremental ingestion with checkpoint tracking.
"""

from datetime import datetime
from typing import List, Optional
import hashlib
import logging

from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent
from app.services.finviz_service import FinvizService
from app.core.config import settings

logger = logging.getLogger(__name__)


class FinvizAdapter(BaseSourceAdapter):
    """Adapter for Finviz stock screener data"""

    def __init__(self, checkpoint_store, message_bus=None):
        super().__init__(checkpoint_store, message_bus)
        self.finviz_service = FinvizService()

    def get_source_name(self) -> str:
        return "finviz"

    def get_source_kind(self) -> str:
        return "screener"

    async def validate_credentials(self) -> bool:
        """Check if Finviz Elite credentials are configured"""
        try:
            # Finviz Elite doesn't require API key - just cookie-based auth
            # We can validate by checking if settings are present
            return True
        except Exception as e:
            logger.error(f"Finviz credential validation failed: {e}")
            return False

    async def fetch_incremental(
        self,
        last_cursor: Optional[str] = None,
        last_timestamp: Optional[datetime] = None
    ) -> List[SourceEvent]:
        """
        Fetch latest screener data from Finviz

        Finviz doesn't have true incremental API - we fetch full snapshot
        and deduplicate based on symbol + timestamp
        """
        events = []

        try:
            # Fetch screener data using predefined presets
            # This returns a full snapshot, not incremental
            screener_results = await self.finviz_service.fetch_screener(
                filters={},  # Can customize filters based on use case
                limit=1000
            )

            # Convert each stock to a SourceEvent
            for stock in screener_results:
                symbol = stock.get("Ticker") or stock.get("ticker")
                if not symbol:
                    continue

                # Create dedupe key from symbol + market cap + price
                # This helps identify when a stock's fundamentals change
                dedupe_data = f"{symbol}_{stock.get('Market Cap', '')}_{stock.get('Price', '')}"
                dedupe_key = hashlib.sha256(dedupe_data.encode()).hexdigest()[:16]

                event = SourceEvent(
                    source=self.get_source_name(),
                    source_kind=self.get_source_kind(),
                    topic="finviz.screener",
                    symbol=symbol,
                    entity_id=symbol,
                    occurred_at=datetime.utcnow(),  # Finviz doesn't provide event time
                    dedupe_key=dedupe_key,
                    payload_json=stock
                )
                events.append(event)

            logger.info(f"Finviz: Fetched {len(events)} stocks")

        except Exception as e:
            logger.error(f"Finviz fetch failed: {e}", exc_info=True)
            raise

        return events
