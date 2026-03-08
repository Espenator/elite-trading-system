"""BaseScout — abstract contract for all 12 dedicated discovery scouts.

Every scout in the continuous-discovery architecture inherits from this class.
It provides a production-grade lifecycle (start → run-loop → stop), automatic
restart-on-error with exponential back-off, heartbeat publishing, per-scan
timeout enforcement, and a clean hook interface that each concrete scout
fills in.

Lifecycle
---------
::

    registry.start_all(bus)
        └── scout.start(bus) ─────────────────────────────────── spawns asyncio.Task
                └── _run_loop()
                        ├── setup()          ← override for one-time init
                        └── loop:
                                ├── _emit_heartbeat()
                                ├── scan()   ← override — returns List[DiscoveryPayload]
                                ├── _publish_discoveries(payloads)
                                └── sleep(scan_interval)

    registry.stop_all()
        └── scout.stop()
                └── teardown()   ← override for cleanup

Error handling
--------------
* Per-scan timeout: ``timeout`` seconds (default 30 s).  Exceeded scan is
  cancelled and counted as an error.
* Exponential back-off on consecutive errors: ``min(base_backoff * 2^errors, max_backoff)``.
* Circuit breaker: after ``max_consecutive_errors`` the scout enters ``error``
  state and backs off at ``max_backoff``; it auto-recovers on next successful scan.
* All exceptions are caught so a misbehaving scout never crashes the process.

Dual-mode hook (E6)
-------------------
Subclasses may optionally implement :meth:`analyst_evaluate` for future
dual-mode analyst/scout behaviour.  The base class defines the signature but
does not call it — the orchestrator will invoke it in analyst mode.
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from app.services.scouts.schemas import DiscoveryPayload, ScoutHealth

if TYPE_CHECKING:
    from app.core.message_bus import MessageBus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults — overridable per scout
# ---------------------------------------------------------------------------
DEFAULT_SCAN_INTERVAL: float = 60.0        # seconds between scans
DEFAULT_TIMEOUT: float = 30.0              # per-scan timeout
DEFAULT_HEARTBEAT_INTERVAL: float = 30.0   # heartbeat publish cadence
DEFAULT_MAX_CONSECUTIVE_ERRORS: int = 5    # circuit-breaker threshold
DEFAULT_BASE_BACKOFF: float = 5.0          # initial back-off on error (seconds)
DEFAULT_MAX_BACKOFF: float = 300.0         # cap back-off at 5 minutes


class BaseScout(ABC):
    """Abstract base class for all continuous-discovery scout agents.

    Subclasses **must** implement :meth:`scan`.
    Subclasses **should** override :attr:`scout_id`, :attr:`source`,
    :attr:`source_type`, :attr:`scan_interval`, and :attr:`timeout`.
    """

    # ----- Identity (override in subclass) ------------------------------------
    scout_id: str = "base_scout"
    source: str = "Base"
    source_type: str = "unknown"

    # ----- Timing (override to tune cadence) ----------------------------------
    scan_interval: float = DEFAULT_SCAN_INTERVAL
    timeout: float = DEFAULT_TIMEOUT
    heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL

    # ----- Resilience (override to tune circuit-breaker) ---------------------
    max_consecutive_errors: int = DEFAULT_MAX_CONSECUTIVE_ERRORS
    base_backoff: float = DEFAULT_BASE_BACKOFF
    max_backoff: float = DEFAULT_MAX_BACKOFF

    def __init__(self) -> None:
        self._bus: Optional["MessageBus"] = None
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._started_at: Optional[float] = None

        # Health counters
        self._total_scans: int = 0
        self._total_discoveries: int = 0
        self._consecutive_errors: int = 0
        self._last_scan_at: Optional[str] = None
        self._last_discovery_at: Optional[str] = None
        self._last_error: str = ""
        self._last_scan_latency_ms: float = 0.0
        self._last_heartbeat_at: float = 0.0

    # =========================================================================
    # Abstract interface — subclasses implement these
    # =========================================================================

    @abstractmethod
    async def scan(self) -> List[DiscoveryPayload]:
        """Execute one discovery scan and return any findings.

        This method is called every ``scan_interval`` seconds inside a
        timeout guard.  It **must not** catch :class:`asyncio.CancelledError`
        so that timeout enforcement works correctly.

        Returns
        -------
        List[DiscoveryPayload]
            Zero or more discoveries.  An empty list is perfectly valid.
        """

    async def setup(self) -> None:
        """One-time initialisation called before the scan loop starts.

        Override to pre-load caches, validate API keys, warm connections, etc.
        Default is a no-op.
        """

    async def teardown(self) -> None:
        """Cleanup called once after the scan loop stops.

        Override to close connections, flush caches, etc.
        Default is a no-op.
        """

    # E6 hook — dual-mode analyst/scout (not called by base; reserved for orchestrator)
    async def analyst_evaluate(
        self,
        symbol: str,
        timeframe: str,
        features: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[Any]:
        """Analyst-mode evaluation hook for future dual-mode behaviour (E6).

        Returns ``None`` by default.  Subclasses that support dual-mode
        should return an :class:`~app.council.schemas.AgentVote`.
        """
        return None

    # =========================================================================
    # Lifecycle — do not override
    # =========================================================================

    async def start(self, bus: "MessageBus") -> None:
        """Attach to the message bus and start the background scan task."""
        if self._running:
            logger.debug("[%s] already running — ignoring start()", self.scout_id)
            return
        self._bus = bus
        self._running = True
        self._started_at = time.monotonic()
        self._task = asyncio.create_task(
            self._run_loop(), name=f"scout:{self.scout_id}"
        )
        logger.info("[%s] started (interval=%.0fs, timeout=%.0fs)",
                    self.scout_id, self.scan_interval, self.timeout)

    async def stop(self) -> None:
        """Gracefully stop the scout and wait for the task to finish."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        self._task = None
        try:
            await self.teardown()
        except Exception as exc:
            logger.warning("[%s] teardown error: %s", self.scout_id, exc)
        logger.info("[%s] stopped", self.scout_id)

    def get_health(self) -> ScoutHealth:
        """Return current health snapshot."""
        uptime = (
            time.monotonic() - self._started_at if self._started_at else 0.0
        )
        status = (
            "stopped" if not self._running
            else "error" if self._consecutive_errors >= self.max_consecutive_errors
            else "running"
        )
        return ScoutHealth(
            scout_id=self.scout_id,
            status=status,
            last_scan_at=self._last_scan_at,
            last_discovery_at=self._last_discovery_at,
            consecutive_errors=self._consecutive_errors,
            total_discoveries=self._total_discoveries,
            total_scans=self._total_scans,
            scan_latency_ms=self._last_scan_latency_ms,
            error_message=self._last_error,
            uptime_seconds=uptime,
        )

    # =========================================================================
    # Internal loop — not part of the public API
    # =========================================================================

    async def _run_loop(self) -> None:
        """Main background loop: setup → heartbeat → scan → sleep → repeat."""
        try:
            await self.setup()
        except Exception as exc:
            logger.error("[%s] setup() failed: %s", self.scout_id, exc)
            # Keep running — setup failure is not fatal

        while self._running:
            # --- heartbeat ---------------------------------------------------
            now = time.monotonic()
            if now - self._last_heartbeat_at >= self.heartbeat_interval:
                await self._emit_heartbeat()
                self._last_heartbeat_at = now

            # --- scan with timeout -------------------------------------------
            t0 = time.monotonic()
            payloads: List[DiscoveryPayload] = []
            try:
                payloads = await asyncio.wait_for(
                    self.scan(), timeout=self.timeout
                )
                elapsed_ms = (time.monotonic() - t0) * 1000
                self._last_scan_latency_ms = elapsed_ms
                self._total_scans += 1
                self._consecutive_errors = 0
                from datetime import datetime, timezone
                self._last_scan_at = datetime.now(timezone.utc).isoformat()
                logger.debug(
                    "[%s] scan complete: %d discoveries in %.0fms",
                    self.scout_id, len(payloads), elapsed_ms,
                )
            except asyncio.TimeoutError:
                self._consecutive_errors += 1
                self._last_error = f"scan timed out after {self.timeout:.0f}s"
                logger.warning("[%s] scan timed out", self.scout_id)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._consecutive_errors += 1
                self._last_error = str(exc)
                logger.error("[%s] scan error: %s", self.scout_id, exc)

            # --- publish discoveries ------------------------------------------
            if payloads:
                await self._publish_discoveries(payloads)

            # --- back-off / sleep --------------------------------------------
            backoff = self._compute_backoff()
            sleep_s = backoff if self._consecutive_errors > 0 else self.scan_interval
            try:
                await asyncio.sleep(sleep_s)
            except asyncio.CancelledError:
                break

    def _compute_backoff(self) -> float:
        """Exponential back-off capped at ``max_backoff``."""
        if self._consecutive_errors == 0:
            return self.scan_interval
        delay = self.base_backoff * (2 ** (self._consecutive_errors - 1))
        return min(delay, self.max_backoff)

    async def _emit_heartbeat(self) -> None:
        """Publish a ScoutHealth snapshot to ``scout.heartbeat``."""
        if not self._bus:
            return
        try:
            health = self.get_health()
            await self._bus.publish("scout.heartbeat", health.to_dict())
        except Exception as exc:
            logger.debug("[%s] heartbeat publish error: %s", self.scout_id, exc)

    async def _publish_discoveries(self, payloads: List[DiscoveryPayload]) -> None:
        """Publish each discovery payload to ``swarm.idea``."""
        if not self._bus:
            return
        from datetime import datetime, timezone
        for payload in payloads:
            try:
                await self._bus.publish("swarm.idea", payload.to_dict())
                self._total_discoveries += 1
                self._last_discovery_at = datetime.now(timezone.utc).isoformat()
                logger.info(
                    "[%s] discovery → %s | %s | score=%d | %s",
                    self.scout_id, payload.symbol, payload.direction,
                    payload.score, payload.reasoning[:60],
                )
            except Exception as exc:
                logger.warning("[%s] failed to publish discovery: %s", self.scout_id, exc)
