"""FRED adapter for scheduled economic data ingestion."""
import hashlib
from datetime import datetime
from typing import List, Optional
from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent
from app.services.fred_service import FredService


# Key economic indicators to track
FRED_SERIES = {
    "VIXCLS": "VIX",  # Volatility Index
    "DGS10": "US10Y",  # 10-Year Treasury Yield
    "DEXUSEU": "DXY",  # Dollar Index (vs Euro)
    "DFF": "FedFunds",  # Federal Funds Rate
    "UNRATE": "Unemployment",  # Unemployment Rate
    "CPIAUCSL": "CPI",  # Consumer Price Index
}


class FredAdapter(BaseSourceAdapter):
    """Adapter for FRED economic data ingestion.

    Fetches latest observations for key economic indicators.
    """

    def __init__(self, **kwargs):
        super().__init__(adapter_id="fred", **kwargs)
        self.fred = FredService()

    async def fetch_events(self, since: Optional[datetime] = None) -> List[SourceEvent]:
        """Fetch latest economic indicators from FRED.

        Args:
            since: Not used for FRED (always fetches latest value)

        Returns:
            List of SourceEvent objects, one per indicator
        """
        events = []
        current_time = datetime.utcnow()

        for series_id, series_name in FRED_SERIES.items():
            try:
                self.logger.debug(f"Fetching FRED series: {series_id} ({series_name})")
                latest = await self.fred.get_latest_value(series_id)

                if latest:
                    # Create unique event ID
                    event_id = hashlib.sha256(
                        f"fred_{series_id}_{latest['date']}".encode()
                    ).hexdigest()[:16]

                    event = SourceEvent(
                        event_id=event_id,
                        source="fred",
                        event_type="economic_indicator",
                        event_time=datetime.fromisoformat(latest["date"]) if latest.get("date") else current_time,
                        symbol=None,  # Economic data not symbol-specific
                        data={
                            "series_id": series_id,
                            "series_name": series_name,
                            "value": latest["value"],
                            "date": latest["date"]
                        },
                        metadata={"indicator": series_name}
                    )
                    events.append(event)

            except Exception as e:
                self.logger.error(f"Failed to fetch FRED series {series_id}: {e}")

        return events

    def get_topic(self) -> str:
        """Get MessageBus topic for FRED events."""
        return "perception.macro"
