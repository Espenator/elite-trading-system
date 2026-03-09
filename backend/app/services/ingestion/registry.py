"""
Adapter Registry

Central registry for managing all ingestion adapters.
Provides unified interface for starting, stopping, and monitoring adapters.
"""

import logging
from typing import Dict, List, Optional, Any

from app.services.ingestion.base import BaseSourceAdapter
from app.services.ingestion.adapters import (
    FinvizAdapter,
    FREDAdapter,
    UnusualWhalesAdapter,
    SECEdgarAdapter,
    OpenClawAdapter,
    AlpacaStreamAdapter
)
from app.data.checkpoint_store import CheckpointStore

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """
    Registry for all data source adapters

    Manages lifecycle (start/stop), health checks, and coordination
    of all ingestion adapters.
    """

    def __init__(self, checkpoint_store: CheckpointStore, message_bus=None):
        """
        Initialize adapter registry

        Args:
            checkpoint_store: Checkpoint store for tracking progress
            message_bus: Message bus for publishing events
        """
        self.checkpoint_store = checkpoint_store
        self.message_bus = message_bus
        self._adapters: Dict[str, BaseSourceAdapter] = {}
        self._initialized = False

    def initialize_adapters(self, alpaca_stream_service=None):
        """
        Initialize all adapters

        Args:
            alpaca_stream_service: Optional AlpacaStreamService instance
        """
        if self._initialized:
            logger.warning("Adapters already initialized")
            return

        # Create all adapter instances
        self._adapters = {
            "finviz": FinvizAdapter(self.checkpoint_store, self.message_bus),
            "fred": FREDAdapter(self.checkpoint_store, self.message_bus),
            "unusual_whales": UnusualWhalesAdapter(self.checkpoint_store, self.message_bus),
            "sec_edgar": SECEdgarAdapter(self.checkpoint_store, self.message_bus),
            "openclaw": OpenClawAdapter(self.checkpoint_store, self.message_bus),
            "alpaca_stream": AlpacaStreamAdapter(
                self.checkpoint_store,
                self.message_bus,
                alpaca_stream_service
            ),
        }

        self._initialized = True
        logger.info(f"Initialized {len(self._adapters)} adapters")

    def get_adapter(self, adapter_name: str) -> Optional[BaseSourceAdapter]:
        """Get adapter by name"""
        return self._adapters.get(adapter_name)

    def get_all_adapters(self) -> Dict[str, BaseSourceAdapter]:
        """Get all registered adapters"""
        return self._adapters.copy()

    async def start_all(self):
        """Start all adapters"""
        logger.info("Starting all adapters...")
        for name, adapter in self._adapters.items():
            try:
                await adapter.start()
                logger.info(f"Started adapter: {name}")
            except Exception as e:
                logger.error(f"Failed to start adapter {name}: {e}", exc_info=True)

    async def stop_all(self):
        """Stop all adapters"""
        logger.info("Stopping all adapters...")
        for name, adapter in self._adapters.items():
            try:
                await adapter.stop()
                logger.info(f"Stopped adapter: {name}")
            except Exception as e:
                logger.error(f"Failed to stop adapter {name}: {e}", exc_info=True)

    async def start_adapter(self, adapter_name: str):
        """Start a specific adapter"""
        adapter = self.get_adapter(adapter_name)
        if not adapter:
            raise ValueError(f"Adapter not found: {adapter_name}")

        await adapter.start()
        logger.info(f"Started adapter: {adapter_name}")

    async def stop_adapter(self, adapter_name: str):
        """Stop a specific adapter"""
        adapter = self.get_adapter(adapter_name)
        if not adapter:
            raise ValueError(f"Adapter not found: {adapter_name}")

        await adapter.stop()
        logger.info(f"Stopped adapter: {adapter_name}")

    async def run_adapter(self, adapter_name: str) -> Dict[str, Any]:
        """
        Run ingestion for a specific adapter once

        Args:
            adapter_name: Name of adapter to run

        Returns:
            Ingestion result dictionary
        """
        adapter = self.get_adapter(adapter_name)
        if not adapter:
            raise ValueError(f"Adapter not found: {adapter_name}")

        logger.info(f"Running ingestion for: {adapter_name}")
        result = await adapter.ingest()
        return result

    async def health_check_all(self) -> List[Dict[str, Any]]:
        """
        Get health status for all adapters

        Returns:
            List of health check results
        """
        health_checks = []

        for name, adapter in self._adapters.items():
            try:
                health = await adapter.health_check()
                health_checks.append(health)
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                health_checks.append({
                    "adapter_name": name,
                    "status": "error",
                    "error": str(e)
                })

        return health_checks

    async def health_check(self, adapter_name: str) -> Dict[str, Any]:
        """Get health status for a specific adapter"""
        adapter = self.get_adapter(adapter_name)
        if not adapter:
            raise ValueError(f"Adapter not found: {adapter_name}")

        return await adapter.health_check()

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get overall registry statistics"""
        running_count = sum(1 for a in self._adapters.values() if a.is_running())

        return {
            "total_adapters": len(self._adapters),
            "running_adapters": running_count,
            "stopped_adapters": len(self._adapters) - running_count,
            "adapter_names": list(self._adapters.keys()),
            "checkpoints": self.checkpoint_store.get_all_checkpoints()
        }
