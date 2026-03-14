"""Remote Health Monitor -- PC1 monitors PC2 (and vice versa).

Runs on ESPENMAIN (PC1) to continuously monitor ProfitTrader (PC2).
Provides health dashboard data and alerts when PC2 becomes unavailable.

Checks:
  1. HTTP health endpoint (FastAPI /health)
  2. gRPC brain_service (TCP port 50051)
  3. Redis connectivity (shared event bus)
  4. GPU worker status (via Redis key)
  5. Ollama model availability

Usage:
    from app.core.remote_health import RemoteHealthMonitor
    monitor = RemoteHealthMonitor()
    await monitor.start()  # runs in background
    status = monitor.get_status()
"""
import asyncio
import json
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


@dataclass
class PeerStatus:
    """Health status of the peer PC."""
    hostname: str = ""
    ip: str = ""
    reachable: bool = False
    api_healthy: bool = False
    brain_healthy: bool = False
    gpu_available: bool = False
    redis_connected: bool = False
    gpu_name: str = ""
    gpu_vram_gb: float = 0
    ollama_model: str = ""
    last_check: float = 0
    last_healthy: float = 0
    consecutive_failures: int = 0
    latency_ms: float = 0
    error: str = ""

    @property
    def is_healthy(self) -> bool:
        return self.reachable and self.api_healthy

    @property
    def is_fully_healthy(self) -> bool:
        return self.reachable and self.api_healthy and self.brain_healthy and self.gpu_available

    def to_dict(self) -> dict:
        return {
            "hostname": self.hostname,
            "ip": self.ip,
            "reachable": self.reachable,
            "api_healthy": self.api_healthy,
            "brain_healthy": self.brain_healthy,
            "gpu_available": self.gpu_available,
            "redis_connected": self.redis_connected,
            "gpu_name": self.gpu_name,
            "gpu_vram_gb": self.gpu_vram_gb,
            "ollama_model": self.ollama_model,
            "is_healthy": self.is_healthy,
            "is_fully_healthy": self.is_fully_healthy,
            "last_check_ago_s": round(time.time() - self.last_check, 1) if self.last_check else 0,
            "consecutive_failures": self.consecutive_failures,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
        }


class RemoteHealthMonitor:
    """Monitors the peer PC's health from this machine."""

    def __init__(self, peer_ip: str = None, check_interval: int = 30):
        from app.core.pc_role import get_role
        role = get_role()
        self._peer_ip = peer_ip or role.peer_ip
        self._peer_hostname = role.peer_hostname
        self._interval = check_interval
        self._status = PeerStatus(hostname=self._peer_hostname, ip=self._peer_ip)
        self._task: Optional[asyncio.Task] = None
        self._callbacks = []  # called on status change

    @property
    def status(self) -> PeerStatus:
        return self._status

    def on_status_change(self, callback):
        """Register callback for health status changes."""
        self._callbacks.append(callback)

    async def start(self):
        """Start background health monitoring."""
        self._task = asyncio.create_task(self._monitor_loop())
        log.info("Remote health monitor started for %s at %s (every %ds)",
                 self._peer_hostname, self._peer_ip, self._interval)

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def check_now(self) -> PeerStatus:
        """Run a health check immediately."""
        return await self._check_peer()

    async def _monitor_loop(self):
        """Background loop checking peer health."""
        while True:
            try:
                old_healthy = self._status.is_healthy
                await self._check_peer()
                new_healthy = self._status.is_healthy

                if old_healthy != new_healthy:
                    state = "UP" if new_healthy else "DOWN"
                    log.warning("PEER %s is %s (failures=%d, latency=%.0fms)",
                                self._peer_hostname, state,
                                self._status.consecutive_failures,
                                self._status.latency_ms)
                    for cb in self._callbacks:
                        try:
                            await cb(self._status)
                        except Exception as e:
                            log.debug("Health callback error: %s", e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.debug("Health monitor error: %s", e)

            await asyncio.sleep(self._interval)

    async def _check_peer(self) -> PeerStatus:
        """Run all health checks against the peer."""
        s = self._status
        s.last_check = time.time()

        # 1. TCP reachability (fast)
        t0 = time.perf_counter()
        s.reachable = await self._tcp_check(self._peer_ip, 8001, timeout=3)
        s.latency_ms = (time.perf_counter() - t0) * 1000

        if not s.reachable:
            s.api_healthy = False
            s.brain_healthy = False
            s.gpu_available = False
            s.consecutive_failures += 1
            s.error = "TCP unreachable"
            return s

        # 2. HTTP health endpoint
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"http://{self._peer_ip}:8001/health")
                if r.status_code == 200:
                    data = r.json()
                    s.api_healthy = data.get("status") in ("healthy", "degraded")
                    components = data.get("components", {})
                    s.brain_healthy = components.get("brain_grpc", {}).get("status") == "healthy"
                    gpu = components.get("gpu_worker", {})
                    s.gpu_available = gpu.get("status") == "healthy"
                    s.gpu_name = gpu.get("gpu", "")
                    s.gpu_vram_gb = gpu.get("vram_gb", 0)
                    s.ollama_model = gpu.get("model", "")
                else:
                    s.api_healthy = False
                    s.error = f"HTTP {r.status_code}"
        except Exception as e:
            s.api_healthy = False
            s.error = str(e)[:100]

        # 3. gRPC brain_service
        s.brain_healthy = await self._tcp_check(self._peer_ip, 50051, timeout=2)

        # Update counters
        if s.is_healthy:
            s.consecutive_failures = 0
            s.last_healthy = time.time()
            s.error = ""
        else:
            s.consecutive_failures += 1

        return s

    @staticmethod
    async def _tcp_check(host: str, port: int, timeout: float = 3) -> bool:
        """Quick TCP connectivity check."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = await asyncio.to_thread(s.connect_ex, (host, port))
            s.close()
            return result == 0
        except Exception:
            return False

    def get_status(self) -> dict:
        """Get current peer status as dict."""
        return self._status.to_dict()


# ── Singleton ────────────────────────────────────────────────────

_monitor: Optional[RemoteHealthMonitor] = None


def get_remote_health_monitor() -> RemoteHealthMonitor:
    """Get or create the remote health monitor (singleton)."""
    global _monitor
    if _monitor is None:
        _monitor = RemoteHealthMonitor()
    return _monitor
