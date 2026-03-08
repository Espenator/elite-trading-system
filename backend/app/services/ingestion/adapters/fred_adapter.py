"""FRED adapter — low-frequency poller with per-series checkpoint.

Fetches economic data series from the Federal Reserve (FRED API) and
publishes ``perception.macro`` events.  Checkpoints the latest observation
date per series so only new data is fetched after restart.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from app.services.ingestion.base import BaseSourceAdapter
from app.services.ingestion.models import SourceEvent, SourceKind

logger = logging.getLogger(__name__)

# Default FRED series IDs for macro features
DEFAULT_SERIES = {
    "vix_close": "VIXCLS",
    "dxy_close": "DTWEXBGS",
    "us10y_yield": "DGS10",
    "fed_funds_rate": "DFF",
}


class FredAdapter(BaseSourceAdapter):
    source_name = "fred"
    source_kind = SourceKind.LOW_FREQ
    poll_interval_seconds = 3600.0  # 1 hour

    def __init__(self, message_bus=None, series: Dict[str, str] | None = None):
        super().__init__(message_bus)
        self._series = series or dict(DEFAULT_SERIES)

    async def poll_once(self) -> None:
        from app.services.fred_service import FredService

        svc = FredService()
        series_checkpoints = self._checkpoint.get("series", {})

        for col_name, series_id in self._series.items():
            try:
                last_date = series_checkpoints.get(series_id, "")
                obs = await svc.get_observations(series_id, limit=10, sort_order="desc")

                new_obs = []
                for ob in obs:
                    d = ob.get("date", "")
                    v = ob.get("value", "")
                    if d and v and v != "." and d > last_date:
                        new_obs.append(ob)

                if not new_obs:
                    continue

                # Update checkpoint to latest date
                latest_date = max(ob["date"] for ob in new_obs)
                series_checkpoints[series_id] = latest_date

                event = SourceEvent(
                    source=self.source_name,
                    source_kind=self.source_kind,
                    topic="perception.macro",
                    entity_id=series_id,
                    payload={
                        "type": "fred_observations",
                        "series_id": series_id,
                        "column_name": col_name,
                        "observations": new_obs,
                        "source": "fred_adapter",
                        "timestamp": time.time(),
                    },
                    dedupe_key=f"fred-{series_id}-{latest_date}",
                )
                await self.publish_event(event)

            except Exception as exc:
                logger.warning("FRED series %s fetch failed: %s", series_id, exc)

        self._checkpoint["series"] = series_checkpoints
        self._checkpoint["last_poll_at"] = time.time()
