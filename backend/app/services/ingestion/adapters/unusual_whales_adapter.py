"""Unusual Whales adapter — incremental poller with timestamp checkpoint.

Wraps ``UnusualWhalesService`` and emits ``perception.unusualwhales``
events.  Stores the timestamp of the most recent alert seen so that
subsequent polls only publish new data.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from app.services.ingestion.base import BaseSourceAdapter
from app.services.ingestion.models import SourceEvent, SourceKind

logger = logging.getLogger(__name__)


class UnusualWhalesAdapter(BaseSourceAdapter):
    source_name = "unusual_whales"
    source_kind = SourceKind.INCREMENTAL
    poll_interval_seconds = 60.0

    async def poll_once(self) -> None:
        from app.services.unusual_whales_service import UnusualWhalesService

        svc = UnusualWhalesService()
        data = await svc.get_flow_alerts()

        alerts = data if isinstance(data, list) else data.get("data", data.get("items", []))
        if not alerts:
            return

        last_ts = self._checkpoint.get("last_timestamp", "")
        new_alerts = []

        for alert in alerts:
            ts = alert.get("traded_at") or alert.get("date") or alert.get("timestamp") or ""
            if ts > last_ts:
                new_alerts.append(alert)

        if not new_alerts:
            return

        # Update checkpoint to latest timestamp
        latest_ts = max(
            a.get("traded_at") or a.get("date") or a.get("timestamp") or ""
            for a in new_alerts
        )
        self._checkpoint["last_timestamp"] = latest_ts
        self._checkpoint["last_poll_at"] = time.time()
        self._checkpoint["alert_count"] = len(new_alerts)

        event = SourceEvent(
            source=self.source_name,
            source_kind=self.source_kind,
            topic="perception.unusualwhales",
            payload={
                "type": "flow_alerts",
                "alerts": new_alerts,
                "count": len(new_alerts),
                "source": "unusual_whales_adapter",
                "timestamp": time.time(),
            },
            dedupe_key=f"uw-{latest_ts}",
        )
        await self.publish_event(event)
