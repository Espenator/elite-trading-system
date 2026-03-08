"""AdapterRegistry — manages the lifecycle of all source adapters.

Usage::

    from app.services.ingestion.registry import adapter_registry

    await adapter_registry.start_all()   # called at FastAPI startup
    health = adapter_registry.get_health()
    await adapter_registry.stop_all()    # called at FastAPI shutdown
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.ingestion.base import BaseSourceAdapter

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Central registry for all :class:`~app.services.ingestion.base.BaseSourceAdapter` instances.

    Adapters are registered via :meth:`register` (called at startup) and
    then managed through :meth:`start_all` / :meth:`stop_all`.

    The registry does **not** drive the polling schedule itself — that is
    delegated to APScheduler (``app/jobs/scheduler.py``).  The registry
    simply maintains references and aggregates health data.
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, BaseSourceAdapter] = {}
        self._started: bool = False

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, adapter: BaseSourceAdapter) -> None:
        """Add an adapter to the registry.

        Raises ``ValueError`` if an adapter with the same ``name`` is
        already registered.
        """
        if adapter.name in self._adapters:
            raise ValueError(
                f"Adapter '{adapter.name}' is already registered. "
                "Use a unique name for each adapter."
            )
        self._adapters[adapter.name] = adapter
        logger.debug("AdapterRegistry: registered '%s'", adapter.name)

    def get(self, name: str) -> Optional[BaseSourceAdapter]:
        """Return adapter by name, or ``None`` if not found."""
        return self._adapters.get(name)

    def all(self) -> List[BaseSourceAdapter]:
        """Return all registered adapters."""
        return list(self._adapters.values())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start_all(self) -> None:
        """Mark all adapters as started.

        The registry itself doesn't schedule polling; callers should start
        the APScheduler jobs separately.  This method is a hook point for
        any per-adapter initialisation (e.g. opening WebSocket connections
        for streaming adapters).
        """
        self._started = True
        logger.info(
            "AdapterRegistry: %d adapter(s) registered and ready: %s",
            len(self._adapters),
            list(self._adapters.keys()),
        )

    async def stop_all(self) -> None:
        """Gracefully close all adapters in registration order."""
        errors: List[str] = []
        for name, adapter in list(self._adapters.items()):
            try:
                await adapter.close()
                logger.info("AdapterRegistry: '%s' closed", name)
            except Exception as exc:  # noqa: BLE001
                msg = f"'{name}' close failed: {exc}"
                logger.warning("AdapterRegistry: %s", msg)
                errors.append(msg)
        self._started = False
        if errors:
            logger.warning("AdapterRegistry stop_all had %d error(s)", len(errors))

    # ------------------------------------------------------------------
    # Health aggregation
    # ------------------------------------------------------------------

    def get_health(self) -> Dict[str, Any]:
        """Aggregate health metrics from all registered adapters.

        Returns a dict with::

            {
                "started": bool,
                "adapter_count": int,
                "adapters": {name: adapter.health(), ...},
                "degraded": [name, ...],  # adapters with status == "degraded"
            }
        """
        adapters_health: Dict[str, Any] = {}
        degraded: List[str] = []
        for name, adapter in self._adapters.items():
            h = adapter.health()
            adapters_health[name] = h
            if h.get("status") == "degraded":
                degraded.append(name)

        return {
            "started": self._started,
            "adapter_count": len(self._adapters),
            "adapters": adapters_health,
            "degraded": degraded,
        }


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------
adapter_registry = AdapterRegistry()
