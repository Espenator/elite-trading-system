"""Unusual Whales adapter for scheduled options flow ingestion."""
import hashlib
from datetime import datetime
from typing import List, Optional, Any, Dict
from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent
from app.services.unusual_whales_service import UnusualWhalesService


class UnusualWhalesAdapter(BaseSourceAdapter):
    """Adapter for Unusual Whales options flow data.

    Fetches flow alerts, insider trades, congress trades, and dark pool data.
    """

    def __init__(self, **kwargs):
        super().__init__(adapter_id="unusual_whales", **kwargs)
        self.uw = UnusualWhalesService()

    async def fetch_events(self, since: Optional[datetime] = None) -> List[SourceEvent]:
        """Fetch latest options flow and trade data.

        Args:
            since: Optional timestamp for incremental fetching

        Returns:
            List of SourceEvent objects
        """
        events = []
        current_time = datetime.utcnow()

        # Fetch flow alerts
        try:
            self.logger.info("Fetching Unusual Whales flow alerts")
            flow_data = await self.uw.get_flow_alerts()
            events.extend(self._convert_flow_alerts(flow_data, current_time))
        except Exception as e:
            self.logger.error(f"Failed to fetch UW flow alerts: {e}")

        # Fetch congress trades
        try:
            self.logger.info("Fetching Unusual Whales congress trades")
            congress_data = await self.uw.get_congress_trades()
            events.extend(self._convert_congress_trades(congress_data, current_time))
        except Exception as e:
            self.logger.error(f"Failed to fetch UW congress trades: {e}")

        # Fetch insider trades
        try:
            self.logger.info("Fetching Unusual Whales insider trades")
            insider_data = await self.uw.get_insider_trades()
            events.extend(self._convert_insider_trades(insider_data, current_time))
        except Exception as e:
            self.logger.error(f"Failed to fetch UW insider trades: {e}")

        # Fetch dark pool data
        try:
            self.logger.info("Fetching Unusual Whales dark pool data")
            darkpool_data = await self.uw.get_darkpool_flow()
            events.extend(self._convert_darkpool_flow(darkpool_data, current_time))
        except Exception as e:
            self.logger.error(f"Failed to fetch UW dark pool data: {e}")

        return events

    def _convert_flow_alerts(self, data: Any, current_time: datetime) -> List[SourceEvent]:
        """Convert flow alerts to SourceEvent format."""
        events = []
        items = data if isinstance(data, list) else data.get("items", [])

        for alert in items:
            try:
                symbol = alert.get("ticker") or alert.get("symbol")
                if not symbol:
                    continue

                # Create unique event ID
                alert_time = alert.get("time") or alert.get("date") or current_time.isoformat()
                event_id = hashlib.sha256(
                    f"uw_flow_{symbol}_{alert_time}_{alert.get('premium', 0)}".encode()
                ).hexdigest()[:16]

                event = SourceEvent(
                    event_id=event_id,
                    source="unusual_whales",
                    event_type="options_flow",
                    event_time=current_time,
                    symbol=symbol,
                    data=alert,
                    metadata={"data_type": "flow_alert"}
                )
                events.append(event)
            except Exception as e:
                self.logger.error(f"Failed to convert flow alert: {e}")

        return events

    def _convert_congress_trades(self, data: Any, current_time: datetime) -> List[SourceEvent]:
        """Convert congress trades to SourceEvent format."""
        events = []
        items = data if isinstance(data, list) else data.get("items", [])

        for trade in items:
            try:
                symbol = trade.get("ticker") or trade.get("symbol")
                if not symbol:
                    continue

                event_id = hashlib.sha256(
                    f"uw_congress_{symbol}_{trade.get('filed_date', '')}_{trade.get('representative', '')}".encode()
                ).hexdigest()[:16]

                event = SourceEvent(
                    event_id=event_id,
                    source="unusual_whales",
                    event_type="congress_trade",
                    event_time=current_time,
                    symbol=symbol,
                    data=trade,
                    metadata={"data_type": "congress_trade"}
                )
                events.append(event)
            except Exception as e:
                self.logger.error(f"Failed to convert congress trade: {e}")

        return events

    def _convert_insider_trades(self, data: Any, current_time: datetime) -> List[SourceEvent]:
        """Convert insider trades to SourceEvent format."""
        events = []
        items = data if isinstance(data, list) else data.get("items", [])

        for trade in items:
            try:
                symbol = trade.get("ticker") or trade.get("symbol")
                if not symbol:
                    continue

                event_id = hashlib.sha256(
                    f"uw_insider_{symbol}_{trade.get('filed_date', '')}_{trade.get('insider', '')}".encode()
                ).hexdigest()[:16]

                event = SourceEvent(
                    event_id=event_id,
                    source="unusual_whales",
                    event_type="insider_trade",
                    event_time=current_time,
                    symbol=symbol,
                    data=trade,
                    metadata={"data_type": "insider_trade"}
                )
                events.append(event)
            except Exception as e:
                self.logger.error(f"Failed to convert insider trade: {e}")

        return events

    def _convert_darkpool_flow(self, data: Any, current_time: datetime) -> List[SourceEvent]:
        """Convert dark pool flow to SourceEvent format."""
        events = []
        items = data if isinstance(data, list) else data.get("items", [])

        for flow in items:
            try:
                symbol = flow.get("ticker") or flow.get("symbol")
                if not symbol:
                    continue

                event_id = hashlib.sha256(
                    f"uw_darkpool_{symbol}_{flow.get('date', '')}_{flow.get('volume', 0)}".encode()
                ).hexdigest()[:16]

                event = SourceEvent(
                    event_id=event_id,
                    source="unusual_whales",
                    event_type="darkpool_flow",
                    event_time=current_time,
                    symbol=symbol,
                    data=flow,
                    metadata={"data_type": "darkpool"}
                )
                events.append(event)
            except Exception as e:
                self.logger.error(f"Failed to convert darkpool flow: {e}")

        return events

    def get_topic(self) -> str:
        """Get MessageBus topic for Unusual Whales events."""
        return "perception.unusualwhales"
