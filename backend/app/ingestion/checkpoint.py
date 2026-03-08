"""CheckpointStore - Event persistence and deduplication."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from app.ingestion.event import SourceEvent

logger = logging.getLogger(__name__)


class CheckpointStore:
    """In-memory checkpoint store for event deduplication.

    Maintains a time-window cache of seen event IDs to prevent duplicate
    processing. Events expire after the configured TTL.

    For persistent checkpointing, events are also written to DuckDB via
    the existing duckdb_storage infrastructure.

    Attributes:
        ttl_seconds: Time-to-live for checkpoint entries
        max_entries: Maximum number of entries to cache
    """

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 10_000):
        """Initialize the checkpoint store.

        Args:
            ttl_seconds: How long to remember event IDs (default: 5 minutes)
            max_entries: Maximum cache size (auto-prune when exceeded)
        """
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._seen: Dict[str, datetime] = {}
        self._stats: Dict[str, int] = defaultdict(int)

    def has_seen(self, event: SourceEvent) -> bool:
        """Check if an event has been seen recently.

        Args:
            event: The event to check

        Returns:
            True if the event was seen within the TTL window
        """
        self._prune_expired()
        return event.event_id in self._seen

    def mark_seen(self, event: SourceEvent) -> None:
        """Mark an event as seen.

        Args:
            event: The event to mark as seen
        """
        from datetime import timezone
        self._seen[event.event_id] = datetime.now(timezone.utc)
        self._stats["total_marked"] += 1
        self._prune_if_needed()

    def get_stats(self) -> Dict[str, int]:
        """Get checkpoint store statistics.

        Returns:
            Dictionary with cache stats (size, hits, misses, etc.)
        """
        self._prune_expired()
        return {
            "cache_size": len(self._seen),
            "max_entries": self.max_entries,
            "ttl_seconds": self.ttl_seconds,
            **self._stats,
        }

    def clear(self) -> None:
        """Clear all checkpoints (for testing)."""
        self._seen.clear()
        self._stats.clear()
        self._stats["cache_cleared"] = 1

    def _prune_expired(self) -> None:
        """Remove expired entries from the cache."""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.ttl_seconds)
        expired = [
            event_id
            for event_id, timestamp in self._seen.items()
            if timestamp < cutoff
        ]
        for event_id in expired:
            del self._seen[event_id]
        if expired:
            self._stats["entries_expired"] += len(expired)

    def _prune_if_needed(self) -> None:
        """Prune oldest entries if cache exceeds max size."""
        if len(self._seen) <= self.max_entries:
            return

        # Remove oldest 10% of entries
        items = sorted(self._seen.items(), key=lambda x: x[1])
        to_remove = len(items) - int(self.max_entries * 0.9)
        for event_id, _ in items[:to_remove]:
            del self._seen[event_id]
        self._stats["entries_pruned"] += to_remove


# Global instance
checkpoint_store = CheckpointStore()
