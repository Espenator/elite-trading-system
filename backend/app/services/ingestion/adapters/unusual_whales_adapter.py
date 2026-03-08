"""
Unusual Whales Ingestion Adapter

Wraps UnusualWhalesService to provide incremental options flow ingestion.
"""

from datetime import datetime
from typing import List, Optional
import hashlib
import logging

from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent
from app.services.unusual_whales_service import UnusualWhalesService
from app.core.config import settings

logger = logging.getLogger(__name__)


class UnusualWhalesAdapter(BaseSourceAdapter):
    """Adapter for Unusual Whales options flow data"""

    def __init__(self, checkpoint_store, message_bus=None):
        super().__init__(checkpoint_store, message_bus)
        self.uw_service = UnusualWhalesService()

    def get_source_name(self) -> str:
        return "unusual_whales"

    def get_source_kind(self) -> str:
        return "options_flow"

    async def validate_credentials(self) -> bool:
        """Check if Unusual Whales API key is configured"""
        try:
            api_key = getattr(settings, "UNUSUAL_WHALES_API_KEY", None)
            return bool(api_key and api_key.strip())
        except Exception as e:
            logger.error(f"Unusual Whales credential validation failed: {e}")
            return False

    async def fetch_incremental(
        self,
        last_cursor: Optional[str] = None,
        last_timestamp: Optional[datetime] = None
    ) -> List[SourceEvent]:
        """
        Fetch latest options flow data from Unusual Whales

        Combines flow alerts, congress trades, insider trades, and dark pool data
        """
        events = []

        try:
            # Fetch flow alerts
            flow_data = await self.uw_service.get_flow_alerts()
            flow_list = flow_data if isinstance(flow_data, list) else flow_data.get("data", [])

            for alert in flow_list:
                symbol = alert.get("ticker") or alert.get("symbol")
                if not symbol:
                    continue

                # Create dedupe key from alert ID or data hash
                alert_id = alert.get("id") or alert.get("alert_id")
                if alert_id:
                    dedupe_key = f"flow_{alert_id}"
                else:
                    # Hash the alert data for deduplication
                    alert_str = f"{symbol}_{alert.get('time', '')}_{alert.get('premium', '')}"
                    dedupe_key = hashlib.sha256(alert_str.encode()).hexdigest()[:16]

                occurred_at_str = alert.get("time") or alert.get("timestamp")
                try:
                    occurred_at = datetime.fromisoformat(occurred_at_str.replace("Z", "+00:00")) if occurred_at_str else datetime.utcnow()
                except:
                    occurred_at = datetime.utcnow()

                # Skip if we've already ingested this
                if last_timestamp and occurred_at <= last_timestamp:
                    continue

                event = SourceEvent(
                    source=self.get_source_name(),
                    source_kind=self.get_source_kind(),
                    topic="unusual_whales.flow",
                    symbol=symbol,
                    entity_id=dedupe_key,
                    occurred_at=occurred_at,
                    dedupe_key=dedupe_key,
                    payload_json={"type": "flow_alert", "data": alert}
                )
                events.append(event)

            # Fetch congress trades
            try:
                congress_data = await self.uw_service.get_congress_trades()
                congress_list = congress_data if isinstance(congress_data, list) else congress_data.get("data", [])

                for trade in congress_list:
                    symbol = trade.get("ticker") or trade.get("symbol")
                    if not symbol:
                        continue

                    trade_id = trade.get("id") or hashlib.sha256(
                        str(trade).encode()
                    ).hexdigest()[:16]

                    event = SourceEvent(
                        source=self.get_source_name(),
                        source_kind=self.get_source_kind(),
                        topic="unusual_whales.congress",
                        symbol=symbol,
                        entity_id=f"congress_{trade_id}",
                        occurred_at=datetime.utcnow(),
                        dedupe_key=f"congress_{trade_id}",
                        payload_json={"type": "congress_trade", "data": trade}
                    )
                    events.append(event)
            except Exception as e:
                logger.warning(f"Congress trades fetch failed: {e}")

            # Fetch insider trades
            try:
                insider_data = await self.uw_service.get_insider_trades()
                insider_list = insider_data if isinstance(insider_data, list) else insider_data.get("data", [])

                for trade in insider_list:
                    symbol = trade.get("ticker") or trade.get("symbol")
                    if not symbol:
                        continue

                    trade_id = trade.get("id") or hashlib.sha256(
                        str(trade).encode()
                    ).hexdigest()[:16]

                    event = SourceEvent(
                        source=self.get_source_name(),
                        source_kind=self.get_source_kind(),
                        topic="unusual_whales.insider",
                        symbol=symbol,
                        entity_id=f"insider_{trade_id}",
                        occurred_at=datetime.utcnow(),
                        dedupe_key=f"insider_{trade_id}",
                        payload_json={"type": "insider_trade", "data": trade}
                    )
                    events.append(event)
            except Exception as e:
                logger.warning(f"Insider trades fetch failed: {e}")

            # Fetch dark pool data
            try:
                darkpool_data = await self.uw_service.get_darkpool_flow()
                darkpool_list = darkpool_data if isinstance(darkpool_data, list) else darkpool_data.get("data", [])

                for dp in darkpool_list:
                    symbol = dp.get("ticker") or dp.get("symbol")
                    if not symbol:
                        continue

                    dp_id = dp.get("id") or hashlib.sha256(
                        str(dp).encode()
                    ).hexdigest()[:16]

                    event = SourceEvent(
                        source=self.get_source_name(),
                        source_kind=self.get_source_kind(),
                        topic="unusual_whales.darkpool",
                        symbol=symbol,
                        entity_id=f"darkpool_{dp_id}",
                        occurred_at=datetime.utcnow(),
                        dedupe_key=f"darkpool_{dp_id}",
                        payload_json={"type": "darkpool", "data": dp}
                    )
                    events.append(event)
            except Exception as e:
                logger.warning(f"Dark pool fetch failed: {e}")

            logger.info(f"Unusual Whales: Fetched {len(events)} events")

        except Exception as e:
            logger.error(f"Unusual Whales fetch failed: {e}", exc_info=True)
            raise

        return events
