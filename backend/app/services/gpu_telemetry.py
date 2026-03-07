"""GPU Telemetry Daemon — Real-time GPU/VRAM monitoring for intelligent routing.

Reads hardware stats from NVIDIA GPUs (via pynvml) and Ollama's /api/ps
endpoint to provide the LLM Dispatcher with live utilization data.

Broadcasts to MessageBus topic ``cluster.telemetry`` every N seconds so that
any subscriber (LLMDispatcher, NodeDiscovery, cluster API) can make
telemetry-aware decisions.

Graceful fallback: if pynvml is not installed or no NVIDIA GPU is present,
the daemon still runs — it just reports Ollama-only telemetry without
hardware VRAM/utilization numbers.

Part of #39 — E1.1
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GPUSnapshot:
    """Point-in-time GPU hardware stats for one device."""
    device_index: int = 0
    name: str = ""
    vram_total_mb: int = 0
    vram_used_mb: int = 0
    vram_free_mb: int = 0
    gpu_utilization_pct: float = 0.0
    temperature_c: int = 0
    timestamp: float = 0.0

    @property
    def vram_utilization_pct(self) -> float:
        if self.vram_total_mb == 0:
            return 0.0
        return round(self.vram_used_mb / self.vram_total_mb * 100, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_index": self.device_index,
            "name": self.name,
            "vram_total_mb": self.vram_total_mb,
            "vram_used_mb": self.vram_used_mb,
            "vram_free_mb": self.vram_free_mb,
            "vram_utilization_pct": self.vram_utilization_pct,
            "gpu_utilization_pct": self.gpu_utilization_pct,
            "temperature_c": self.temperature_c,
            "timestamp": self.timestamp,
        }


@dataclass
class OllamaProcessInfo:
    """A model currently loaded in Ollama VRAM."""
    model: str = ""
    size_mb: int = 0
    vram_mb: int = 0
    until: str = ""  # Ollama's expiry timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "size_mb": self.size_mb,
            "vram_mb": self.vram_mb,
            "until": self.until,
        }


@dataclass
class NodeTelemetry:
    """Combined telemetry snapshot for one node (GPU + Ollama)."""
    node_url: str = ""
    hostname: str = ""
    gpu: Optional[GPUSnapshot] = None
    loaded_models: List[OllamaProcessInfo] = field(default_factory=list)
    ollama_responsive: bool = False
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_url": self.node_url,
            "hostname": self.hostname,
            "gpu": self.gpu.to_dict() if self.gpu else None,
            "loaded_models": [m.to_dict() for m in self.loaded_models],
            "ollama_responsive": self.ollama_responsive,
            "timestamp": self.timestamp,
        }

    @property
    def model_names(self) -> List[str]:
        """Return names of all models currently loaded."""
        return [m.model for m in self.loaded_models]


# ---------------------------------------------------------------------------
# GPU reader (pynvml)
# ---------------------------------------------------------------------------

def _read_local_gpu() -> Optional[GPUSnapshot]:
    """Read local GPU stats via pynvml. Returns None if unavailable."""
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8")

        snapshot = GPUSnapshot(
            device_index=0,
            name=name,
            vram_total_mb=int(mem.total / (1024 * 1024)),
            vram_used_mb=int(mem.used / (1024 * 1024)),
            vram_free_mb=int(mem.free / (1024 * 1024)),
            gpu_utilization_pct=float(util.gpu),
            temperature_c=temp,
            timestamp=time.time(),
        )
        pynvml.nvmlShutdown()
        return snapshot
    except ImportError:
        logger.debug("pynvml not installed — GPU telemetry disabled (pip install pynvml)")
        return None
    except Exception as e:
        logger.debug("GPU read failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Ollama process reader
# ---------------------------------------------------------------------------

async def _read_ollama_processes(base_url: str) -> List[OllamaProcessInfo]:
    """Query Ollama /api/ps for currently loaded models."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base_url.rstrip('/')}/api/ps")
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.debug("Ollama /api/ps failed at %s: %s", base_url, e)
        return []

    models = []
    for entry in data.get("models", []):
        name = entry.get("name", entry.get("model", ""))
        size_bytes = entry.get("size", 0)
        vram_bytes = entry.get("size_vram", entry.get("vram", 0))
        until = entry.get("expires_at", entry.get("until", ""))
        models.append(OllamaProcessInfo(
            model=name,
            size_mb=int(size_bytes / (1024 * 1024)) if size_bytes else 0,
            vram_mb=int(vram_bytes / (1024 * 1024)) if vram_bytes else 0,
            until=str(until),
        ))
    return models


# ---------------------------------------------------------------------------
# Telemetry Daemon
# ---------------------------------------------------------------------------

class GPUTelemetryDaemon:
    """Background service that collects and broadcasts GPU telemetry.

    - Reads local GPU stats via pynvml (if available)
    - Queries local Ollama /api/ps for loaded models
    - Publishes ``NodeTelemetry`` to MessageBus ``cluster.telemetry``
    - Maintains a telemetry cache accessible to other services
    """

    def __init__(self, message_bus=None):
        self._message_bus = message_bus
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._interval: float = 3.0
        self._local_url: str = "http://localhost:11434"
        self._hostname: str = ""

        # Telemetry cache (latest snapshot per node URL)
        self._cache: Dict[str, NodeTelemetry] = {}

        self._load_config()

    def _load_config(self) -> None:
        try:
            from app.core.config import settings
            self._interval = settings.GPU_TELEMETRY_INTERVAL
            self._local_url = settings.OLLAMA_BASE_URL.rstrip("/")
        except Exception:
            import os
            self._interval = float(os.getenv("GPU_TELEMETRY_INTERVAL", "3.0"))
            self._local_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

        import socket
        self._hostname = socket.gethostname()

    async def start(self) -> None:
        """Start the telemetry collection loop."""
        try:
            from app.core.config import settings
            if not settings.GPU_TELEMETRY_ENABLED:
                logger.info("GPUTelemetryDaemon: disabled via GPU_TELEMETRY_ENABLED=false")
                return
        except Exception:
            pass

        self._running = True
        self._task = asyncio.create_task(self._collect_loop())
        logger.info(
            "GPUTelemetryDaemon started (interval=%.1fs, ollama=%s)",
            self._interval, self._local_url,
        )

    async def stop(self) -> None:
        """Stop the telemetry collection loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _collect_loop(self) -> None:
        """Main collection loop — reads GPU + Ollama, broadcasts to MessageBus."""
        while self._running:
            try:
                telemetry = await self._collect_local()
                self._cache[telemetry.node_url] = telemetry

                # Broadcast to MessageBus
                if self._message_bus:
                    await self._message_bus.publish(
                        "cluster.telemetry",
                        telemetry.to_dict(),
                    )

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("GPUTelemetryDaemon: collection error")

            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break

    async def _collect_local(self) -> NodeTelemetry:
        """Collect telemetry for the local node."""
        gpu = _read_local_gpu()
        loaded_models = await _read_ollama_processes(self._local_url)

        return NodeTelemetry(
            node_url=self._local_url,
            hostname=self._hostname,
            gpu=gpu,
            loaded_models=loaded_models,
            ollama_responsive=True if loaded_models is not None else False,
            timestamp=time.time(),
        )

    def update_remote_telemetry(self, telemetry_dict: Dict[str, Any]) -> None:
        """Ingest telemetry from a remote node (received via MessageBus).

        Called by NodeDiscovery when it receives cluster.telemetry events
        from PC2's telemetry daemon.
        """
        node_url = telemetry_dict.get("node_url", "")
        if not node_url:
            return

        gpu_data = telemetry_dict.get("gpu")
        gpu = None
        if gpu_data:
            gpu = GPUSnapshot(
                device_index=gpu_data.get("device_index", 0),
                name=gpu_data.get("name", ""),
                vram_total_mb=gpu_data.get("vram_total_mb", 0),
                vram_used_mb=gpu_data.get("vram_used_mb", 0),
                vram_free_mb=gpu_data.get("vram_free_mb", 0),
                gpu_utilization_pct=gpu_data.get("gpu_utilization_pct", 0.0),
                temperature_c=gpu_data.get("temperature_c", 0),
                timestamp=gpu_data.get("timestamp", time.time()),
            )

        loaded_models = []
        for m in telemetry_dict.get("loaded_models", []):
            loaded_models.append(OllamaProcessInfo(
                model=m.get("model", ""),
                size_mb=m.get("size_mb", 0),
                vram_mb=m.get("vram_mb", 0),
                until=m.get("until", ""),
            ))

        self._cache[node_url] = NodeTelemetry(
            node_url=node_url,
            hostname=telemetry_dict.get("hostname", ""),
            gpu=gpu,
            loaded_models=loaded_models,
            ollama_responsive=telemetry_dict.get("ollama_responsive", False),
            timestamp=telemetry_dict.get("timestamp", time.time()),
        )

    def get_node_telemetry(self, node_url: str) -> Optional[NodeTelemetry]:
        """Get the latest telemetry for a specific node."""
        return self._cache.get(node_url.rstrip("/"))

    def get_all_telemetry(self) -> Dict[str, NodeTelemetry]:
        """Get telemetry for all known nodes."""
        return dict(self._cache)

    def get_status(self) -> Dict[str, Any]:
        """Return daemon status for monitoring."""
        return {
            "enabled": self._running,
            "interval": self._interval,
            "nodes_tracked": len(self._cache),
            "nodes": {
                url: t.to_dict() for url, t in self._cache.items()
            },
        }


# ── Module-level singleton ────────────────────────────────────────────────
_gpu_telemetry: Optional[GPUTelemetryDaemon] = None


def get_gpu_telemetry() -> GPUTelemetryDaemon:
    """Get or create the singleton GPUTelemetryDaemon."""
    global _gpu_telemetry
    if _gpu_telemetry is None:
        _gpu_telemetry = GPUTelemetryDaemon()
    return _gpu_telemetry
