"""
OpenClaw Ingestion Adapter

Wraps OpenClawBridgeService to provide incremental regime/whale flow ingestion.
"""

from datetime import datetime
from typing import List, Optional
import hashlib
import logging

from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent
from app.services.openclaw_bridge_service import (
    get_latest_signals,
    get_realtime_stats
)

logger = logging.getLogger(__name__)


class OpenClawAdapter(BaseSourceAdapter):
    """Adapter for OpenClaw regime and whale flow signals"""

    def get_source_name(self) -> str:
        return "openclaw"

    def get_source_kind(self) -> str:
        return "regime_flow"

    async def validate_credentials(self) -> bool:
        """OpenClaw bridge doesn't require traditional credentials"""
        try:
            # Check if we can get stats (indicates bridge is working)
            stats = get_realtime_stats()
            return stats is not None
        except Exception as e:
            logger.error(f"OpenClaw validation failed: {e}")
            return False

    async def fetch_incremental(
        self,
        last_cursor: Optional[str] = None,
        last_timestamp: Optional[datetime] = None
    ) -> List[SourceEvent]:
        """
        Fetch latest OpenClaw signals from real-time buffer

        OpenClaw maintains its own ring buffer - we extract new signals
        """
        events = []

        try:
            # Get latest signals from OpenClaw bridge
            signals = get_latest_signals(limit=100)

            for signal in signals:
                signal_id = signal.get("signal_id") or signal.get("id")
                if not signal_id:
                    # Generate ID from signal data
                    signal_str = str(signal)
                    signal_id = hashlib.sha256(signal_str.encode()).hexdigest()[:16]

                symbol = signal.get("symbol") or signal.get("ticker")
                timestamp_str = signal.get("timestamp") or signal.get("created_at")

                try:
                    occurred_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")) if timestamp_str else datetime.utcnow()
                except:
                    occurred_at = datetime.utcnow()

                # Skip if we've already processed this signal
                if last_timestamp and occurred_at <= last_timestamp:
                    continue

                dedupe_key = f"openclaw_{signal_id}"

                # Determine topic based on signal type
                signal_type = signal.get("type", "unknown")
                if "regime" in signal_type.lower():
                    topic = "openclaw.regime"
                elif "whale" in signal_type.lower():
                    topic = "openclaw.whale_flow"
                else:
                    topic = "openclaw.signal"

                event = SourceEvent(
                    source=self.get_source_name(),
                    source_kind=self.get_source_kind(),
                    topic=topic,
                    symbol=symbol,
                    entity_id=signal_id,
                    occurred_at=occurred_at,
                    dedupe_key=dedupe_key,
                    payload_json=signal
                )
                events.append(event)

            logger.info(f"OpenClaw: Fetched {len(events)} signals")

        except Exception as e:
            logger.error(f"OpenClaw fetch failed: {e}", exc_info=True)
            raise

        return events
