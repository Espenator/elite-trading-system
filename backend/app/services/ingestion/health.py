"""Ingestion health aggregator.

Collects ``health()`` snapshots from all registered adapters and exposes
a unified view for the existing ``/health`` and ``/readyz`` endpoints.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List


class IngestionHealth:
    """Aggregates per-adapter health into a single report."""

    def __init__(self, registry=None):
        self._registry = registry

    def summary(self) -> Dict[str, Any]:
        """Return aggregated health for all adapters."""
        if self._registry is None:
            return {"status": "no_registry"}

        adapters: List[Dict[str, Any]] = []
        degraded = []
        offline = []
        total_events = 0
        total_errors = 0

        for adapter in self._registry.all_adapters():
            h = adapter.health()
            adapters.append(h)
            total_events += h.get("events_published", 0)
            total_errors += h.get("errors", 0)
            state = h.get("state", "unknown")
            if state == "degraded":
                degraded.append(h["source"])
            elif state == "offline":
                offline.append(h["source"])

        overall = "healthy"
        if offline:
            overall = "degraded"
        if len(offline) == len(adapters) and adapters:
            overall = "offline"

        return {
            "status": overall,
            "adapter_count": len(adapters),
            "total_events_published": total_events,
            "total_errors": total_errors,
            "degraded_sources": degraded,
            "offline_sources": offline,
            "adapters": adapters,
            "checked_at": time.time(),
        }
