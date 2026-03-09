"""
FRED (Federal Reserve Economic Data) Ingestion Adapter

Wraps FredService to provide incremental economic data ingestion.
"""

from datetime import datetime
from typing import List, Optional
import hashlib
import logging

from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent
from app.services.fred_service import FredService
from app.core.config import settings

logger = logging.getLogger(__name__)


# Key economic indicators to track
FRED_SERIES = [
    "CPIAUCSL",      # Consumer Price Index
    "UNRATE",        # Unemployment Rate
    "GDP",           # Gross Domestic Product
    "DFF",           # Federal Funds Rate
    "DGS10",         # 10-Year Treasury Rate
    "DGS2",          # 2-Year Treasury Rate
    "VIXCLS",        # VIX Volatility Index
    "DEXUSEU",       # USD/EUR Exchange Rate
    "DTWEXBGS",      # Trade Weighted USD Index
    "PAYEMS",        # Non-Farm Payrolls
]


class FREDAdapter(BaseSourceAdapter):
    """Adapter for FRED economic data"""

    def __init__(self, checkpoint_store, message_bus=None):
        super().__init__(checkpoint_store, message_bus)
        self.fred_service = FredService()

    def get_source_name(self) -> str:
        return "fred"

    def get_source_kind(self) -> str:
        return "economic"

    async def validate_credentials(self) -> bool:
        """Check if FRED API key is configured"""
        try:
            api_key = getattr(settings, "FRED_API_KEY", None)
            return bool(api_key and api_key.strip())
        except Exception as e:
            logger.error(f"FRED credential validation failed: {e}")
            return False

    async def fetch_incremental(
        self,
        last_cursor: Optional[str] = None,
        last_timestamp: Optional[datetime] = None
    ) -> List[SourceEvent]:
        """
        Fetch latest economic data from FRED

        FRED provides dated observations - we track last_timestamp to avoid duplicates
        """
        events = []

        try:
            # Fetch latest observation for each series
            for series_id in FRED_SERIES:
                try:
                    observations = await self.fred_service.get_observations(
                        series_id=series_id,
                        limit=5,  # Get last 5 to handle revisions
                        sort_order="desc"
                    )

                    for obs in observations:
                        obs_date = obs.get("date")
                        obs_value = obs.get("value")

                        if not obs_date or obs_value == ".":
                            continue

                        # Skip if we've already ingested this observation
                        obs_datetime = datetime.fromisoformat(obs_date)
                        if last_timestamp and obs_datetime <= last_timestamp:
                            continue

                        # Create dedupe key from series + date
                        dedupe_key = hashlib.sha256(
                            f"{series_id}_{obs_date}".encode()
                        ).hexdigest()[:16]

                        event = SourceEvent(
                            source=self.get_source_name(),
                            source_kind=self.get_source_kind(),
                            topic="fred.economic",
                            symbol=None,  # Economic data is not symbol-specific
                            entity_id=series_id,
                            occurred_at=obs_datetime,
                            dedupe_key=dedupe_key,
                            payload_json={
                                "series_id": series_id,
                                "date": obs_date,
                                "value": obs_value,
                                "realtime_start": obs.get("realtime_start"),
                                "realtime_end": obs.get("realtime_end")
                            }
                        )
                        events.append(event)

                except Exception as e:
                    logger.warning(f"FRED series {series_id} fetch failed: {e}")
                    continue

            logger.info(f"FRED: Fetched {len(events)} observations across {len(FRED_SERIES)} series")

        except Exception as e:
            logger.error(f"FRED fetch failed: {e}", exc_info=True)
            raise

        return events
