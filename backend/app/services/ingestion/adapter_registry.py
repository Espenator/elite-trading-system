"""Adapter registry for managing all ingestion adapters."""
import logging
from typing import Dict, List, Optional
from app.services.ingestion.base import BaseSourceAdapter, AdapterHealth
from app.data.checkpoint_store import CheckpointStore

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Registry for managing all data source adapters.

    Provides centralized access to adapters, health monitoring,
    and batch operations.
    """

    def __init__(self, checkpoint_store: Optional[CheckpointStore] = None):
        self.checkpoint_store = checkpoint_store or CheckpointStore()
        self._adapters: Dict[str, BaseSourceAdapter] = {}

    def register(self, adapter: BaseSourceAdapter):
        """Register an adapter.

        Args:
            adapter: Adapter instance to register
        """
        self._adapters[adapter.adapter_id] = adapter
        logger.info(f"Registered adapter: {adapter.adapter_id}")

    def get(self, adapter_id: str) -> Optional[BaseSourceAdapter]:
        """Get an adapter by ID.

        Args:
            adapter_id: Unique identifier for the adapter

        Returns:
            Adapter instance or None if not found
        """
        return self._adapters.get(adapter_id)

    def get_all(self) -> List[BaseSourceAdapter]:
        """Get all registered adapters.

        Returns:
            List of all adapter instances
        """
        return list(self._adapters.values())

    def get_adapter_ids(self) -> List[str]:
        """Get list of all adapter IDs.

        Returns:
            List of adapter IDs
        """
        return list(self._adapters.keys())

    async def run_adapter(self, adapter_id: str) -> int:
        """Run a specific adapter.

        Args:
            adapter_id: ID of the adapter to run

        Returns:
            Number of events ingested

        Raises:
            ValueError: If adapter not found
        """
        adapter = self.get(adapter_id)
        if not adapter:
            raise ValueError(f"Adapter not found: {adapter_id}")

        return await adapter.run()

    async def run_all(self) -> Dict[str, int]:
        """Run all registered adapters.

        Returns:
            Dictionary mapping adapter_id to events_count
        """
        results = {}
        for adapter_id, adapter in self._adapters.items():
            try:
                count = await adapter.run()
                results[adapter_id] = count
            except Exception as e:
                logger.error(f"Failed to run adapter {adapter_id}: {e}")
                results[adapter_id] = -1

        return results

    def get_health(self, adapter_id: Optional[str] = None) -> Dict[str, AdapterHealth]:
        """Get health status for adapters.

        Args:
            adapter_id: Optional ID to get health for specific adapter

        Returns:
            Dictionary mapping adapter_id to AdapterHealth
        """
        if adapter_id:
            adapter = self.get(adapter_id)
            if adapter:
                return {adapter_id: adapter.get_health()}
            return {}

        # Get health for all adapters
        return {
            adapter_id: adapter.get_health()
            for adapter_id, adapter in self._adapters.items()
        }

    def get_health_summary(self) -> Dict[str, any]:
        """Get summary of all adapter health.

        Returns:
            Dictionary with health summary statistics
        """
        all_health = self.get_health()
        healthy_count = sum(1 for h in all_health.values() if h.is_healthy)
        total_count = len(all_health)
        total_events = sum(h.events_ingested for h in all_health.values())

        return {
            "total_adapters": total_count,
            "healthy_adapters": healthy_count,
            "unhealthy_adapters": total_count - healthy_count,
            "total_events_ingested": total_events,
            "adapters": {
                adapter_id: health.to_dict()
                for adapter_id, health in all_health.items()
            }
        }

    def reset_checkpoint(self, adapter_id: str):
        """Reset checkpoint for an adapter.

        Args:
            adapter_id: ID of the adapter to reset

        Raises:
            ValueError: If adapter not found
        """
        adapter = self.get(adapter_id)
        if not adapter:
            raise ValueError(f"Adapter not found: {adapter_id}")

        adapter.reset_checkpoint()
        logger.info(f"Reset checkpoint for adapter: {adapter_id}")


# Global adapter registry instance
_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """Get the global adapter registry instance.

    Returns:
        Global AdapterRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
    return _registry


def initialize_adapters():
    """Initialize and register all adapters.

    This should be called during application startup.
    """
    from app.services.ingestion.finviz_adapter import FinvizAdapter
    from app.services.ingestion.fred_adapter import FredAdapter
    from app.services.ingestion.unusual_whales_adapter import UnusualWhalesAdapter
    from app.services.ingestion.sec_edgar_adapter import SecEdgarAdapter
    from app.services.ingestion.openclaw_adapter import OpenClawAdapter

    registry = get_adapter_registry()

    # Register all adapters
    registry.register(FinvizAdapter())
    registry.register(FredAdapter())
    registry.register(UnusualWhalesAdapter())
    registry.register(SecEdgarAdapter())
    registry.register(OpenClawAdapter())

    logger.info(f"Initialized {len(registry.get_adapter_ids())} adapters")

    return registry
