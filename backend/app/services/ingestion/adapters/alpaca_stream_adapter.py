"""
Alpaca Stream Ingestion Adapter

Wraps AlpacaStreamService to provide real-time market data as ingestion events.
This is a streaming adapter that continuously publishes bars.
"""

from datetime import datetime
from typing import List, Optional
import hashlib
import logging

from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent
from app.core.config import settings

logger = logging.getLogger(__name__)


class AlpacaStreamAdapter(BaseSourceAdapter):
    """
    Adapter for Alpaca real-time market data stream

    Note: This is a special adapter that runs continuously (streaming)
    rather than polling on a schedule. It integrates with AlpacaStreamService.
    """

    def __init__(self, checkpoint_store, message_bus=None, alpaca_stream_service=None):
        super().__init__(checkpoint_store, message_bus)
        self.alpaca_stream_service = alpaca_stream_service
        self._bar_count = 0

    def get_source_name(self) -> str:
        return "alpaca_stream"

    def get_source_kind(self) -> str:
        return "stream"

    async def validate_credentials(self) -> bool:
        """Check if Alpaca API credentials are configured"""
        try:
            api_key = getattr(settings, "ALPACA_API_KEY", None)
            secret_key = getattr(settings, "ALPACA_SECRET_KEY", None)
            return bool(api_key and secret_key)
        except Exception as e:
            logger.error(f"Alpaca credential validation failed: {e}")
            return False

    async def fetch_incremental(
        self,
        last_cursor: Optional[str] = None,
        last_timestamp: Optional[datetime] = None
    ) -> List[SourceEvent]:
        """
        Not used for streaming adapter - bars are pushed via callbacks

        Streaming adapters use start() method instead to run continuously
        """
        return []

    async def start(self):
        """
        Start the streaming adapter

        For Alpaca, the AlpacaStreamService should already be running.
        This adapter acts as a bridge to track ingestion events.
        """
        await super().start()

        # If alpaca_stream_service is provided, we can hook into its bar events
        # For now, we just mark as running - actual streaming happens in AlpacaStreamService
        logger.info(f"[{self.get_source_name()}] Streaming adapter started")

        # The actual bar ingestion is handled by AlpacaStreamService which publishes
        # to 'market_data.bar' topic. We could subscribe to that topic and convert
        # to SourceEvents if needed, but for now we let it publish directly.

    async def on_bar_received(self, bar_data: dict):
        """
        Callback when a bar is received from Alpaca stream

        This can be called by AlpacaStreamService to track bars as SourceEvents
        """
        try:
            symbol = bar_data.get("symbol") or bar_data.get("S")
            timestamp_str = bar_data.get("timestamp") or bar_data.get("t")

            if not symbol:
                return

            try:
                occurred_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")) if timestamp_str else datetime.utcnow()
            except:
                occurred_at = datetime.utcnow()

            # Create dedupe key from symbol + timestamp
            dedupe_key = hashlib.sha256(
                f"{symbol}_{timestamp_str}".encode()
            ).hexdigest()[:16]

            event = SourceEvent(
                source=self.get_source_name(),
                source_kind=self.get_source_kind(),
                topic="market_data.bar",
                symbol=symbol,
                entity_id=f"bar_{symbol}_{timestamp_str}",
                occurred_at=occurred_at,
                dedupe_key=dedupe_key,
                payload_json=bar_data
            )

            # Publish to message bus if available
            if self.message_bus and event.topic:
                await self.message_bus.publish(event.topic, event.dict())

            self._bar_count += 1

            # Periodically save checkpoint (every 100 bars)
            if self._bar_count % 100 == 0:
                self.checkpoint_store.save_checkpoint(
                    adapter_name=self.get_source_name(),
                    source_key="stream",
                    last_timestamp=occurred_at,
                    status="success",
                    row_count=self._bar_count,
                    metadata={"total_bars": self._bar_count}
                )

        except Exception as e:
            logger.error(f"Alpaca bar processing failed: {e}", exc_info=True)
