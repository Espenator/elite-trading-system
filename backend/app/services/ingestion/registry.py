"""Adapter registry — manages lifecycle of all ingestion adapters.

Provides a single point for ``main.py`` to start / stop / health-check
every adapter.  The ``market_data_agent`` tick loop delegates to this
registry instead of calling source services directly.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.ingestion.base import BaseSourceAdapter
from app.services.ingestion.health import IngestionHealth

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Central registry for ingestion adapters."""

    def __init__(self):
        self._adapters: Dict[str, BaseSourceAdapter] = {}
        self._health = IngestionHealth(registry=self)

    def register(self, adapter: BaseSourceAdapter) -> None:
        """Register an adapter by its source_name."""
        name = adapter.source_name
        if name in self._adapters:
            logger.warning("Adapter '%s' already registered — replacing", name)
        self._adapters[name] = adapter
        logger.info("Registered ingestion adapter: %s (%s)", name, adapter.source_kind.value)

    def get(self, name: str) -> Optional[BaseSourceAdapter]:
        return self._adapters.get(name)

    def all_adapters(self) -> List[BaseSourceAdapter]:
        return list(self._adapters.values())

    async def start_all(self) -> None:
        """Start every registered adapter."""
        for name, adapter in self._adapters.items():
            try:
                await adapter.start()
            except Exception as exc:
                logger.warning("Adapter '%s' failed to start: %s", name, exc)

    async def stop_all(self) -> None:
        """Stop every registered adapter (reverse order)."""
        for name in reversed(list(self._adapters.keys())):
            try:
                await self._adapters[name].stop()
            except Exception as exc:
                logger.debug("Adapter '%s' stop error: %s", name, exc)

    def health_summary(self) -> Dict[str, Any]:
        return self._health.summary()


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------
_registry: AdapterRegistry | None = None


def get_adapter_registry() -> AdapterRegistry:
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
    return _registry
