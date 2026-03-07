"""OllamaNodePool — Shared Ollama node pool with health checks.

Extracted from HyperSwarm to be reusable by all services that need
local LLM inference (HyperSwarm, BrainClient, AutonomousScout, etc.).

Features:
    - Load nodes from SCANNER_OLLAMA_URLS env var (comma-separated)
    - Per-node asyncio.Semaphore for concurrency limiting
    - Round-robin get_next_node() with health-aware skip
    - Periodic health check via GET {url}/api/tags
    - Unhealthy nodes re-checked every 60s
    - Thread-safe singleton via get_ollama_pool()

Part of #39 — E0.3
"""
import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_OLLAMA_URLS = ["http://localhost:11434"]
DEFAULT_MAX_CONCURRENT = 10
HEALTH_CHECK_INTERVAL = 60  # seconds
UNHEALTHY_THRESHOLD = 3     # consecutive failures before marking unhealthy


@dataclass
class OllamaNodeStats:
    """Per-node health and performance stats."""
    url: str
    healthy: bool = True
    consecutive_failures: int = 0
    total_successes: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    last_success_time: float = 0.0
    last_error_time: float = 0.0
    last_health_check: float = 0.0
    models_available: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "healthy": self.healthy,
            "consecutive_failures": self.consecutive_failures,
            "total_successes": self.total_successes,
            "total_errors": self.total_errors,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "models_available": self.models_available,
        }


class OllamaNodePool:
    """Shared pool of Ollama nodes with health checking and load balancing."""

    def __init__(self, max_concurrent_per_node: int = DEFAULT_MAX_CONCURRENT):
        self._max_concurrent = max_concurrent_per_node
        self._nodes: Dict[str, OllamaNodeStats] = {}
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._node_index: int = 0
        self._health_task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._load_nodes()

    def _load_nodes(self) -> None:
        """Load Ollama node URLs from environment."""
        env_urls = os.getenv("SCANNER_OLLAMA_URLS", "")
        if env_urls:
            urls = [u.strip().rstrip("/") for u in env_urls.split(",") if u.strip()]
        else:
            urls = list(DEFAULT_OLLAMA_URLS)

        for url in urls:
            self._nodes[url] = OllamaNodeStats(url=url)
            self._semaphores[url] = asyncio.Semaphore(self._max_concurrent)

        logger.info(
            "OllamaNodePool loaded %d node(s): %s",
            len(self._nodes), ", ".join(urls),
        )

    def add_node(self, url: str) -> None:
        """Dynamically add a node to the pool (e.g., from NodeDiscovery)."""
        url = url.rstrip("/")
        if url not in self._nodes:
            self._nodes[url] = OllamaNodeStats(url=url)
            self._semaphores[url] = asyncio.Semaphore(self._max_concurrent)
            logger.info("OllamaNodePool: added node %s", url)

    def remove_node(self, url: str) -> None:
        """Remove a node from the pool."""
        url = url.rstrip("/")
        self._nodes.pop(url, None)
        self._semaphores.pop(url, None)
        logger.info("OllamaNodePool: removed node %s", url)

    @property
    def urls(self) -> List[str]:
        """Return all node URLs."""
        return list(self._nodes.keys())

    @property
    def healthy_urls(self) -> List[str]:
        """Return only healthy node URLs."""
        return [url for url, stats in self._nodes.items() if stats.healthy]

    def get_next_node(self) -> Optional[str]:
        """Round-robin selection with health-aware skip.

        Returns the next healthy node URL, or None if all nodes are down.
        """
        healthy = self.healthy_urls
        if not healthy:
            # All nodes unhealthy — try the least-recently-failed one
            if self._nodes:
                return min(
                    self._nodes.values(),
                    key=lambda n: n.last_error_time,
                ).url
            return None

        url = healthy[self._node_index % len(healthy)]
        self._node_index += 1
        return url

    def get_semaphore(self, url: str) -> Optional[asyncio.Semaphore]:
        """Get the concurrency semaphore for a node."""
        return self._semaphores.get(url.rstrip("/"))

    def report_success(self, url: str, latency_ms: float = 0.0) -> None:
        """Report a successful request to a node."""
        url = url.rstrip("/")
        stats = self._nodes.get(url)
        if stats:
            stats.consecutive_failures = 0
            stats.healthy = True
            stats.total_successes += 1
            stats.last_success_time = time.time()
            # Running average latency
            n = stats.total_successes
            stats.avg_latency_ms = (
                (stats.avg_latency_ms * (n - 1) + latency_ms) / n
            )

    def report_error(self, url: str) -> None:
        """Report a failed request to a node."""
        url = url.rstrip("/")
        stats = self._nodes.get(url)
        if stats:
            stats.consecutive_failures += 1
            stats.total_errors += 1
            stats.last_error_time = time.time()
            if stats.consecutive_failures >= UNHEALTHY_THRESHOLD:
                stats.healthy = False
                logger.warning(
                    "OllamaNodePool: node %s marked unhealthy (%d consecutive failures)",
                    url, stats.consecutive_failures,
                )

    async def start_health_checks(self) -> None:
        """Start the background health check loop."""
        if self._running:
            return
        self._running = True
        self._health_task = asyncio.create_task(self._health_check_loop())
        logger.info("OllamaNodePool: health check loop started")

    async def stop_health_checks(self) -> None:
        """Stop the background health check loop."""
        self._running = False
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

    async def _health_check_loop(self) -> None:
        """Periodically ping each node to check health."""
        while self._running:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                await self._check_all_nodes()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("OllamaNodePool: health check error")

    async def _check_all_nodes(self) -> None:
        """Ping all nodes (healthy and unhealthy) for health status."""
        import httpx

        for url, stats in self._nodes.items():
            try:
                t0 = time.monotonic()
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(f"{url}/api/tags")
                    r.raise_for_status()
                latency = (time.monotonic() - t0) * 1000

                data = r.json()
                models = [
                    m.get("name", "")
                    for m in data.get("models", [])
                ]
                stats.models_available = models
                stats.last_health_check = time.time()

                was_unhealthy = not stats.healthy
                stats.healthy = True
                stats.consecutive_failures = 0
                stats.last_success_time = time.time()

                if was_unhealthy:
                    logger.info(
                        "OllamaNodePool: node %s recovered (%.0fms, %d models)",
                        url, latency, len(models),
                    )

            except Exception as e:
                stats.consecutive_failures += 1
                stats.last_error_time = time.time()
                stats.last_health_check = time.time()
                if stats.consecutive_failures >= UNHEALTHY_THRESHOLD:
                    stats.healthy = False
                logger.debug(
                    "OllamaNodePool: health check failed for %s: %s",
                    url, e,
                )

    def get_status(self) -> Dict[str, Any]:
        """Return pool status for monitoring."""
        return {
            "total_nodes": len(self._nodes),
            "healthy_nodes": len(self.healthy_urls),
            "max_concurrent_per_node": self._max_concurrent,
            "nodes": {url: stats.to_dict() for url, stats in self._nodes.items()},
        }


# ── Module-level singleton ────────────────────────────────────────────────
_ollama_pool: Optional[OllamaNodePool] = None


def get_ollama_pool() -> OllamaNodePool:
    """Get or create the singleton OllamaNodePool."""
    global _ollama_pool
    if _ollama_pool is None:
        _ollama_pool = OllamaNodePool()
    return _ollama_pool
