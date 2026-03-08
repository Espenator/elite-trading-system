"""Snapshot diff helper for poll-based source adapters.

For sources that return a full snapshot (e.g. Finviz screener, OpenClaw
candidate list), this module compares the new snapshot to the previous one
and yields SourceEvent instances only for rows that were inserted, changed,
or removed — avoiding redundant downstream processing.

Usage::

    from app.services.ingestion.snapshot_diff import SnapshotDiffer

    differ = SnapshotDiffer(source="finviz", feed="screener", key_field="ticker")
    events = differ.diff(new_snapshot)
    for event in events:
        await bus.publish("source_event", event.to_bus_dict())
"""
import logging
from typing import Any, Dict, Iterator, List, Optional

from app.models.source_event import SourceEvent

logger = logging.getLogger(__name__)


def _stable_hash(row: Dict[str, Any]) -> str:
    """Return a compact hex hash of a dict's content for change detection."""
    import hashlib, json
    return hashlib.sha256(
        json.dumps(row, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


class SnapshotDiffer:
    """Stateful differ that tracks the last snapshot and emits delta events.

    Parameters
    ----------
    source:
        Adapter name (e.g. ``"finviz"``).
    feed:
        Sub-feed label (e.g. ``"screener"``).
    key_field:
        Name of the field in each row used as a stable entity key (e.g.
        ``"ticker"``, ``"symbol"``, ``"cik"``).
    emit_removals:
        When ``True``, entities that disappear from the snapshot are emitted
        as ``SourceEvent(is_deleted=True)``.
    """

    def __init__(
        self,
        source: str,
        feed: str,
        key_field: str = "symbol",
        emit_removals: bool = True,
    ) -> None:
        self.source = source
        self.feed = feed
        self.key_field = key_field
        self.emit_removals = emit_removals

        # key → content-hash of last-seen row
        self._prev_hashes: Dict[str, str] = {}
        # key → last-seen raw row
        self._prev_rows: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------

    def diff(
        self,
        new_rows: List[Dict[str, Any]],
        extra_symbols: Optional[List[str]] = None,
    ) -> List[SourceEvent]:
        """Compare *new_rows* to the internal previous snapshot.

        Returns a list of SourceEvent for:
        - **inserted** rows (key not seen before)
        - **changed** rows (key seen but content different)
        - **removed** rows (key missing from new snapshot, if emit_removals)

        The internal state is updated to *new_rows* after diffing.
        """
        new_by_key: Dict[str, Dict[str, Any]] = {}
        for row in new_rows:
            key = str(row.get(self.key_field, ""))
            if not key:
                continue
            new_by_key[key] = row

        events: List[SourceEvent] = []

        # Inserted + changed
        for key, row in new_by_key.items():
            new_hash = _stable_hash(row)
            if key not in self._prev_hashes or self._prev_hashes[key] != new_hash:
                symbols = extra_symbols or ([key] if self.key_field == "symbol" else [])
                event = SourceEvent.from_screener_row(
                    source=self.source,
                    symbol=key if self.key_field == "symbol" else "",
                    row=row,
                    feed=self.feed,
                )
                if symbols:
                    event.symbols = symbols
                events.append(event)

        # Removed
        if self.emit_removals:
            removed_keys = set(self._prev_hashes) - set(new_by_key)
            for key in removed_keys:
                prev_row = self._prev_rows.get(key, {})
                dedupe_key = SourceEvent.make_dedupe_key(
                    self.source, f"removed:{key}", prev_row
                )
                symbols = [key] if self.key_field == "symbol" else []
                event = SourceEvent(
                    dedupe_key=dedupe_key,
                    source=self.source,
                    feed=self.feed,
                    symbols=symbols,
                    payload=dict(prev_row),
                    is_deleted=True,
                )
                events.append(event)

        if events:
            inserted = sum(
                1 for e in events
                if not e.is_deleted
                and str(e.symbols[0] if e.symbols else e.payload.get(self.key_field, ""))
                not in self._prev_hashes
            )
            changed = sum(1 for e in events if not e.is_deleted) - inserted
            removed = sum(1 for e in events if e.is_deleted)
            logger.debug(
                "[%s/%s] diff — inserted=%d changed=%d removed=%d",
                self.source, self.feed, inserted, changed, removed,
            )

        # Commit new state
        self._prev_hashes = {k: _stable_hash(v) for k, v in new_by_key.items()}
        self._prev_rows = dict(new_by_key)

        return events

    def reset(self) -> None:
        """Clear internal state (forces full re-emit on next diff call)."""
        self._prev_hashes.clear()
        self._prev_rows.clear()

    @property
    def tracked_keys(self) -> List[str]:
        """Keys currently in the previous-snapshot cache."""
        return list(self._prev_hashes.keys())
