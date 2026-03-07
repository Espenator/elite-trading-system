"""NodeDiscovery — Auto-discovery + telemetry-aware cluster management.

Discovers PC2 capabilities (Ollama, Brain gRPC) and registers them
with the appropriate pools. Fire-and-forget — NEVER blocks startup.

E0.5 features:
    - Read CLUSTER_PC2_HOST from config (empty = single-PC mode)
    - Ping PC2 health endpoints on startup
    - If PC2 Ollama responds: add URL to OllamaNodePool
    - If PC2 brain responds: update brain_client to use PC2 host
    - Background re-check every CLUSTER_HEALTH_INTERVAL seconds
    - get_cluster_status() for /api/v1/cluster/status endpoint

E1.6 additions:
    - Subscribe to cluster.telemetry MessageBus topic
    - Feed telemetry into GPUTelemetryDaemon + LLMDispatcher
    - Register new nodes with ModelPinningRegistry + LLMDispatcher
    - mDNS-style network scan for auto-discovering Ollama instances
    - Collect PC2 telemetry via HTTP (when PC2 runs a telemetry daemon)

Part of #39 — E0.5 + E1.6
"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class NodeDiscovery:
    """Discover and register PC2 capabilities."""

    def __init__(self):
        self._pc2_host: str = ""
        self._health_interval: int = 60
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

        # Discovery state
        self._pc2_ollama_available: bool = False
        self._pc2_brain_available: bool = False
        self._pc2_ollama_models: list = []
        self._last_check_time: float = 0.0
        self._check_count: int = 0

        self._load_config()

    def _load_config(self) -> None:
        """Load cluster config from settings."""
        try:
            from app.core.config import settings
            self._pc2_host = (settings.CLUSTER_PC2_HOST or "").strip()
            self._health_interval = settings.CLUSTER_HEALTH_INTERVAL
        except Exception:
            import os
            self._pc2_host = os.getenv("CLUSTER_PC2_HOST", "").strip()
            self._health_interval = int(os.getenv("CLUSTER_HEALTH_INTERVAL", "60"))

    @property
    def is_cluster_mode(self) -> bool:
        """True if PC2 host is configured."""
        return bool(self._pc2_host)

    async def start(self) -> None:
        """Start discovery (non-blocking background task)."""
        if not self.is_cluster_mode:
            logger.info("NodeDiscovery: single-PC mode (CLUSTER_PC2_HOST not set)")
            return

        self._running = True
        logger.info("NodeDiscovery: discovering PC2 at %s", self._pc2_host)

        # Initial discovery
        await self._discover()

        # Start background health check loop
        self._task = asyncio.create_task(self._health_loop())

    async def stop(self) -> None:
        """Stop discovery background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _health_loop(self) -> None:
        """Periodic re-discovery for late joiners or recovery."""
        while self._running:
            try:
                await asyncio.sleep(self._health_interval)
                await self._discover()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("NodeDiscovery: health loop error")

    async def _discover(self) -> None:
        """Ping PC2 endpoints and register capabilities."""
        import httpx

        self._check_count += 1
        self._last_check_time = time.time()

        # 1. Check PC2 Ollama
        ollama_url = f"http://{self._pc2_host}:11434"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{ollama_url}/api/tags")
                r.raise_for_status()
                data = r.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                self._pc2_ollama_models = models

                was_available = self._pc2_ollama_available
                self._pc2_ollama_available = True

                # Register with OllamaNodePool
                try:
                    from app.services.ollama_node_pool import get_ollama_pool
                    pool = get_ollama_pool()
                    pool.add_node(ollama_url)
                except Exception as e:
                    logger.debug("NodeDiscovery: failed to add to OllamaNodePool: %s", e)

                if not was_available:
                    logger.info(
                        "NodeDiscovery: PC2 Ollama ONLINE at %s (%d models: %s)",
                        ollama_url, len(models), ", ".join(models[:5]),
                    )

        except Exception as e:
            if self._pc2_ollama_available:
                logger.warning("NodeDiscovery: PC2 Ollama went OFFLINE: %s", e)
            self._pc2_ollama_available = False

        # 2. Check PC2 Brain Service (gRPC health)
        brain_target = f"{self._pc2_host}:50051"
        try:
            # Simple TCP connect check for gRPC (faster than full gRPC health)
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._pc2_host, 50051),
                timeout=3.0,
            )
            writer.close()
            await writer.wait_closed()

            was_available = self._pc2_brain_available
            self._pc2_brain_available = True

            # Update brain_client host
            try:
                from app.services.brain_client import get_brain_client
                brain = get_brain_client()
                if brain.host != self._pc2_host:
                    brain.host = self._pc2_host
                    brain.enabled = True
                    # Force reconnect by clearing existing channel
                    if brain._channel:
                        try:
                            await brain._channel.close()
                        except Exception:
                            pass
                        brain._channel = None
                        brain._stub = None
                    logger.info(
                        "NodeDiscovery: brain_client updated to PC2 host %s",
                        self._pc2_host,
                    )
            except Exception as e:
                logger.debug("NodeDiscovery: failed to update brain_client: %s", e)

            if not was_available:
                logger.info(
                    "NodeDiscovery: PC2 Brain Service ONLINE at %s",
                    brain_target,
                )

        except Exception as e:
            if self._pc2_brain_available:
                logger.warning("NodeDiscovery: PC2 Brain Service went OFFLINE: %s", e)
            self._pc2_brain_available = False

        # 3. Register with dispatcher + collect telemetry (E1.6)
        await self._register_with_dispatcher()
        await self._collect_pc2_telemetry()

    # -- Telemetry integration (E1.6) -----------------------------------------

    async def handle_telemetry_event(self, data: Dict[str, Any]) -> None:
        """MessageBus callback for cluster.telemetry events.

        Feeds incoming telemetry into GPUTelemetryDaemon (for caching)
        and LLMDispatcher (for routing decisions).
        """
        try:
            from app.services.gpu_telemetry import get_gpu_telemetry
            get_gpu_telemetry().update_remote_telemetry(data)
        except Exception as e:
            logger.debug("Failed to update GPU telemetry cache: %s", e)

        try:
            from app.services.llm_dispatcher import get_llm_dispatcher
            get_llm_dispatcher().ingest_telemetry(data)
        except Exception as e:
            logger.debug("Failed to update LLM dispatcher: %s", e)

    async def _collect_pc2_telemetry(self) -> None:
        """Actively fetch telemetry from PC2 if it's running a telemetry daemon.

        This supplements MessageBus-based telemetry for cases where PC2
        is not yet publishing to the bus (e.g., during startup).
        """
        if not self._pc2_ollama_available:
            return

        import httpx

        ollama_url = f"http://{self._pc2_host}:11434"
        try:
            # Fetch Ollama /api/ps for loaded models
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{ollama_url}/api/ps")
                r.raise_for_status()
                ps_data = r.json()

            # Build synthetic telemetry event
            loaded_models = []
            for entry in ps_data.get("models", []):
                loaded_models.append({
                    "model": entry.get("name", entry.get("model", "")),
                    "size_mb": int(entry.get("size", 0) / (1024 * 1024)),
                    "vram_mb": int(entry.get("size_vram", 0) / (1024 * 1024)),
                    "until": str(entry.get("expires_at", "")),
                })

            telemetry = {
                "node_url": ollama_url,
                "hostname": self._pc2_host,
                "gpu": None,  # No pynvml access on remote — use heartbeat data
                "loaded_models": loaded_models,
                "ollama_responsive": True,
                "timestamp": time.time(),
            }

            await self.handle_telemetry_event(telemetry)

        except Exception as e:
            logger.debug("Failed to collect PC2 telemetry: %s", e)

    async def _register_with_dispatcher(self) -> None:
        """Register discovered nodes with LLMDispatcher and ModelPinning."""
        if not self._pc2_ollama_available:
            return

        ollama_url = f"http://{self._pc2_host}:11434"

        try:
            from app.services.llm_dispatcher import get_llm_dispatcher
            get_llm_dispatcher().register_node(ollama_url)
        except Exception as e:
            logger.debug("Failed to register node with dispatcher: %s", e)

        try:
            from app.services.model_pinning import get_model_pinning, NodeRole
            registry = get_model_pinning()
            registry.update_node_url(NodeRole.PC2, ollama_url)
        except Exception as e:
            logger.debug("Failed to update model pinning registry: %s", e)

    def get_cluster_status(self) -> Dict[str, Any]:
        """Return cluster health for /api/v1/cluster/status."""
        status: Dict[str, Any] = {
            "cluster_mode": self.is_cluster_mode,
            "pc2_host": self._pc2_host or None,
            "check_count": self._check_count,
            "last_check_age_seconds": (
                round(time.time() - self._last_check_time, 1)
                if self._last_check_time else None
            ),
        }

        if self.is_cluster_mode:
            status["pc2"] = {
                "ollama": {
                    "available": self._pc2_ollama_available,
                    "url": f"http://{self._pc2_host}:11434",
                    "models": self._pc2_ollama_models,
                },
                "brain_service": {
                    "available": self._pc2_brain_available,
                    "target": f"{self._pc2_host}:50051",
                },
            }

        # Include OllamaNodePool status if available
        try:
            from app.services.ollama_node_pool import get_ollama_pool
            status["ollama_pool"] = get_ollama_pool().get_status()
        except Exception:
            pass

        # Include AlpacaKeyPool status if available
        try:
            from app.services.alpaca_key_pool import get_alpaca_key_pool
            status["alpaca_key_pool"] = get_alpaca_key_pool().get_status()
        except Exception:
            pass

        # Include GPU telemetry if available
        try:
            from app.services.gpu_telemetry import get_gpu_telemetry
            status["gpu_telemetry"] = get_gpu_telemetry().get_status()
        except Exception:
            pass

        # Include LLM dispatcher status if available
        try:
            from app.services.llm_dispatcher import get_llm_dispatcher
            status["llm_dispatcher"] = get_llm_dispatcher().get_status()
        except Exception:
            pass

        # Include model pinning status if available
        try:
            from app.services.model_pinning import get_model_pinning
            status["model_pinning"] = get_model_pinning().get_status()
        except Exception:
            pass

        return status


# ── Module-level singleton ────────────────────────────────────────────────
_node_discovery: Optional[NodeDiscovery] = None


def get_node_discovery() -> NodeDiscovery:
    """Get or create the singleton NodeDiscovery."""
    global _node_discovery
    if _node_discovery is None:
        _node_discovery = NodeDiscovery()
    return _node_discovery
