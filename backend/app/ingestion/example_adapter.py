"""Example concrete adapter demonstrating the ingestion foundation.

This is a reference implementation showing how to build a source adapter
using the BaseSourceAdapter foundation.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.ingestion.adapter import BaseSourceAdapter
from app.ingestion.event import SourceEvent


class ExampleMarketDataAdapter(BaseSourceAdapter):
    """Example adapter for demonstration and testing purposes.

    This shows the minimal implementation required to create a working
    source adapter. Real adapters (Alpaca, Unusual Whales) follow the
    same pattern but with actual API calls.
    """

    def __init__(self, api_key: str = None, **kwargs):
        """Initialize with optional API key."""
        super().__init__(**kwargs)
        self.api_key = api_key
        self._fetch_count = 0

    @property
    def source_name(self) -> str:
        """Unique identifier for this source."""
        return "example_market_data"

    @property
    def event_type(self) -> str:
        """Default event type for this source."""
        return "market_data.bar"

    async def fetch_data(self) -> Dict[str, Any]:
        """Fetch simulated market data.

        In a real adapter, this would make an HTTP request to an external API.
        """
        # Simulate API latency
        await asyncio.sleep(0.01)

        self._fetch_count += 1

        # Simulate API response
        return {
            "bars": [
                {
                    "symbol": "AAPL",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "open": 175.00,
                    "high": 176.50,
                    "low": 174.80,
                    "close": 176.20,
                    "volume": 1000000,
                },
                {
                    "symbol": "MSFT",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "open": 410.00,
                    "high": 412.00,
                    "low": 409.50,
                    "close": 411.75,
                    "volume": 500000,
                },
            ]
        }

    def transform_to_events(self, raw_data: Any) -> List[SourceEvent]:
        """Transform API response into SourceEvent objects."""
        events = []
        for bar in raw_data.get("bars", []):
            event = SourceEvent(
                event_type=self.event_type,
                source=self.source_name,
                data={
                    "symbol": bar["symbol"],
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                    "volume": bar["volume"],
                },
                timestamp=datetime.fromisoformat(bar["timestamp"]),
                metadata={
                    "session": "market_hours",
                    "data_quality": "realtime",
                },
            )
            events.append(event)
        return events

    def validate_config(self) -> bool:
        """Validate adapter configuration."""
        # In a real adapter, you'd check for required API keys, etc.
        return True
