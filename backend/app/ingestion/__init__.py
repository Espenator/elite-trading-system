"""Shared ingestion foundation for all data sources.

This package provides a locked, coherent foundation for ingesting data from
external sources into the trading system. All source adapters should inherit
from BaseSourceAdapter and emit SourceEvent objects.

Components:
- SourceEvent: Standardized event structure
- BaseSourceAdapter: Base class for all source adapters
- CheckpointStore: Event persistence and deduplication
- EventSink: MessageBus integration (re-exported from core)
- Health/metrics primitives: Standardized health checking

Architecture:
    External API → Concrete Adapter (BaseSourceAdapter) → SourceEvent
    → EventSink (MessageBus) → CheckpointStore (DuckDB)
"""

from app.ingestion.event import SourceEvent
from app.ingestion.adapter import BaseSourceAdapter
from app.ingestion.checkpoint import CheckpointStore
from app.ingestion.health import HealthStatus, HealthMetrics

__all__ = [
    "SourceEvent",
    "BaseSourceAdapter",
    "CheckpointStore",
    "HealthStatus",
    "HealthMetrics",
]
