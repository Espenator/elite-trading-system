"""Ingestion layer for data source adapters.

This module provides a unified interface for ingesting data from
various external sources (Finviz, FRED, Unusual Whales, SEC Edgar, OpenClaw).

Key components:
- BaseSourceAdapter: Base class for all adapters
- SourceEvent: Unified event model
- CheckpointStore: State persistence for incremental ingestion
- AdapterRegistry: Central registry for all adapters
"""

from app.services.ingestion.base import BaseSourceAdapter, AdapterHealth
from app.services.ingestion.adapter_registry import (
    AdapterRegistry,
    get_adapter_registry,
    initialize_adapters
)

__all__ = [
    "BaseSourceAdapter",
    "AdapterHealth",
    "AdapterRegistry",
    "get_adapter_registry",
    "initialize_adapters",
]
