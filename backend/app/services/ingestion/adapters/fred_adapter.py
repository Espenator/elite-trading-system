"""FredAdapter — polls FRED macro series and emits SourceEvents.

Schedule: every 15 minutes.

Fetches the FRED series listed in :data:`FRED_SERIES` using the existing
:class:`~app.services.fred_service.FredService`.  Only observations newer
than the last checkpoint are emitted.

CheckpointStore key: ``fred.last_date`` — most-recent observation date seen
Topic: ``ingestion.macro``
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.source_event import SourceEvent
from app.services.ingestion.base import BaseSourceAdapter

logger = logging.getLogger(__name__)

# FRED series to poll — same set used by data_ingestion.py
FRED_SERIES: Dict[str, str] = {
    "vix_close":       "VIXCLS",
    "dxy_close":       "DTWEXBGS",
    "us10y_yield":     "DGS10",
    "fed_funds_rate":  "DFF",
}

_CHECKPOINT_KEY = "fred.last_date"


class FredAdapter(BaseSourceAdapter):
    """Polls FRED macro series.

    Emits one ``SourceEvent`` per observation that is *newer* than the last
    checkpointed date.  On first run (no checkpoint) fetches the last 30
    observations per series.

    Args:
        series: Mapping of ``column_name -> FRED_series_id`` to fetch.
                Defaults to :data:`FRED_SERIES`.
        lookback: Number of historical observations to fetch on a cold start.
    """

    name = "fred"
    source_kind = "poll"

    def __init__(
        self,
        series: Optional[Dict[str, str]] = None,
        lookback: int = 30,
    ) -> None:
        super().__init__()
        self._series = series or FRED_SERIES
        self._lookback = lookback

    async def fetch(self) -> List[SourceEvent]:
        from app.services.fred_service import FredService

        svc = FredService()
        last_date: Optional[str] = self.checkpoint.get(_CHECKPOINT_KEY)

        events: List[SourceEvent] = []
        newest_date: Optional[str] = last_date
        seq = 0

        for col_name, series_id in self._series.items():
            try:
                obs_list = await svc.get_observations(
                    series_id, limit=self._lookback, sort_order="asc"
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("FredAdapter: series %s failed: %s", series_id, exc)
                continue

            for obs in obs_list:
                obs_date: str = obs.get("date", "")
                obs_value = obs.get("value")
                if not obs_date or obs_value in (None, ".", ""):
                    continue
                # Skip observations we've already seen
                if last_date and obs_date <= last_date:
                    continue

                events.append(
                    SourceEvent(
                        source=self.name,
                        source_kind=self.source_kind,
                        topic="ingestion.macro",
                        payload={
                            "series_id": series_id,
                            "column": col_name,
                            "date": obs_date,
                            "value": float(obs_value),
                        },
                        entity_id=series_id,
                        occurred_at=datetime.fromisoformat(obs_date)
                        if obs_date
                        else None,
                        sequence=seq,
                    )
                )
                seq += 1

                if newest_date is None or obs_date > newest_date:
                    newest_date = obs_date

        # Advance checkpoint
        if newest_date and newest_date != last_date:
            self.checkpoint.set(_CHECKPOINT_KEY, newest_date)

        logger.info(
            "FredAdapter: %d new observations (last_date: %s → %s)",
            len(events), last_date, newest_date,
        )
        return events

    async def close(self) -> None:
        pass  # Stateless HTTP poller — nothing to close
