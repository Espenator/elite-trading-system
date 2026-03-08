"""Finviz adapter for scheduled ingestion."""
import hashlib
from datetime import datetime
from typing import List, Optional
from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent
from app.services.finviz_service import FinvizService, FINVIZ_PRESETS


class FinvizAdapter(BaseSourceAdapter):
    """Adapter for Finviz screener data ingestion.

    Runs all Finviz presets (breakout, momentum, swing_pullback, pas_gate)
    and converts results to SourceEvent format.
    """

    def __init__(self, **kwargs):
        super().__init__(adapter_id="finviz", **kwargs)
        self.finviz = FinvizService()

    async def fetch_events(self, since: Optional[datetime] = None) -> List[SourceEvent]:
        """Fetch screener results from all Finviz presets.

        Args:
            since: Not used for Finviz (always fetches current state)

        Returns:
            List of SourceEvent objects, one per stock per preset
        """
        events = []
        current_time = datetime.utcnow()

        # Run all presets
        for preset_name in FINVIZ_PRESETS.keys():
            try:
                self.logger.info(f"Running Finviz preset: {preset_name}")
                stocks = await self.finviz.get_intraday_screen(preset=preset_name)

                for stock in stocks:
                    # Create unique event ID based on symbol + preset + date
                    symbol = stock.get("Ticker") or stock.get("ticker", "")
                    event_id = hashlib.sha256(
                        f"finviz_{preset_name}_{symbol}_{current_time.date()}".encode()
                    ).hexdigest()[:16]

                    event = SourceEvent(
                        event_id=event_id,
                        source="finviz",
                        event_type=f"screener_{preset_name}",
                        event_time=current_time,
                        symbol=symbol,
                        data=stock,
                        metadata={"preset": preset_name}
                    )
                    events.append(event)

            except Exception as e:
                self.logger.error(f"Failed to fetch Finviz preset {preset_name}: {e}")

        return events

    def get_topic(self) -> str:
        """Get MessageBus topic for Finviz events."""
        return "perception.finviz.screener"
