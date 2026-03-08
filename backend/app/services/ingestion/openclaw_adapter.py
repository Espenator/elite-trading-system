"""OpenClaw adapter for scheduled signal ingestion."""
import hashlib
from datetime import datetime
from typing import List, Optional
from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent
from app.services.openclaw_bridge_service import OpenClawBridgeService


class OpenClawAdapter(BaseSourceAdapter):
    """Adapter for OpenClaw signal data.

    Fetches regime, top candidates, and whale flow signals.
    """

    def __init__(self, **kwargs):
        super().__init__(adapter_id="openclaw", **kwargs)
        self.openclaw = OpenClawBridgeService()

    async def fetch_events(self, since: Optional[datetime] = None) -> List[SourceEvent]:
        """Fetch latest signals from OpenClaw.

        Args:
            since: Optional timestamp for incremental fetching

        Returns:
            List of SourceEvent objects
        """
        events = []
        current_time = datetime.utcnow()

        # Fetch regime signal
        try:
            self.logger.info("Fetching OpenClaw regime signal")
            regime = await self.openclaw.get_regime()

            if regime:
                event_id = hashlib.sha256(
                    f"openclaw_regime_{current_time.date()}_{regime.get('regime', '')}".encode()
                ).hexdigest()[:16]

                event = SourceEvent(
                    event_id=event_id,
                    source="openclaw",
                    event_type="regime",
                    event_time=current_time,
                    symbol=None,
                    data=regime,
                    metadata={"signal_type": "regime"}
                )
                events.append(event)

        except Exception as e:
            self.logger.error(f"Failed to fetch OpenClaw regime: {e}")

        # Fetch top candidates
        try:
            self.logger.info("Fetching OpenClaw top candidates")
            candidates = await self.openclaw.get_top_candidates()

            for candidate in candidates:
                symbol = candidate.get("symbol") or candidate.get("ticker")
                if not symbol:
                    continue

                event_id = hashlib.sha256(
                    f"openclaw_candidate_{symbol}_{current_time.isoformat()}".encode()
                ).hexdigest()[:16]

                event = SourceEvent(
                    event_id=event_id,
                    source="openclaw",
                    event_type="candidate",
                    event_time=current_time,
                    symbol=symbol,
                    data=candidate,
                    metadata={"signal_type": "candidate"}
                )
                events.append(event)

        except Exception as e:
            self.logger.error(f"Failed to fetch OpenClaw candidates: {e}")

        # Fetch whale flow
        try:
            self.logger.info("Fetching OpenClaw whale flow")
            whale_flow = await self.openclaw.get_whale_flow()

            for flow in whale_flow:
                symbol = flow.get("symbol") or flow.get("ticker")
                if not symbol:
                    continue

                event_id = hashlib.sha256(
                    f"openclaw_whale_{symbol}_{current_time.isoformat()}_{flow.get('flow_id', '')}".encode()
                ).hexdigest()[:16]

                event = SourceEvent(
                    event_id=event_id,
                    source="openclaw",
                    event_type="whale_flow",
                    event_time=current_time,
                    symbol=symbol,
                    data=flow,
                    metadata={"signal_type": "whale_flow"}
                )
                events.append(event)

        except Exception as e:
            self.logger.error(f"Failed to fetch OpenClaw whale flow: {e}")

        return events

    def get_topic(self) -> str:
        """Get MessageBus topic for OpenClaw events."""
        return "perception.regime.openclaw"
