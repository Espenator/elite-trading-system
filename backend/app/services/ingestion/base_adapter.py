"""BaseSourceAdapter — abstract base class for all source adapters.

Concrete adapters (FinvizAdapter, FREDAdapter, EDGARAdapter, …) inherit
from this class and implement ``_run()``.  The base class provides:

- Lifecycle (``start`` / ``stop``)
- Health reporting (``health``)
- Checkpoint load / save (delegated to ``CheckpointStore``)
- Event publishing (via ``MessageBus``)
- Structured logging with per-adapter context
- Per-source metrics counters

Usage::

    class FinvizAdapter(BaseSourceAdapter):
        SOURCE = "finviz"
        FEED   = "screener"

        async def _run(self) -> None:
            while self._running:
                rows = await fetch_screener()
                for event in self._differ.diff(rows):
                    await self.publish_event(event)
                await self.save_checkpoint("screener", {"ts": utcnow()})
                await asyncio.sleep(60)
"""
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.data.checkpoint_store import checkpoint_store as _default_checkpoint_store
from app.models.source_event import SourceEvent

logger = logging.getLogger(__name__)

_BUS_TOPIC = "source_event"


class BaseSourceAdapter(ABC):
    """Abstract base for firehose source adapters.

    Subclasses **must** set class-level ``SOURCE`` (and optionally ``FEED``)
    and implement ``_run()``.
    """

    SOURCE: str = ""   # e.g. "finviz"
    FEED: str = ""     # e.g. "screener"

    def __init__(
        self,
        message_bus=None,
        checkpoint_store=None,
    ) -> None:
        if not self.SOURCE:
            raise ValueError(f"{type(self).__name__} must define SOURCE")

        self._bus = message_bus
        self._cp_store = checkpoint_store or _default_checkpoint_store

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._start_time: Optional[float] = None

        # Metrics
        self._events_published: int = 0
        self._tick_count: int = 0
        self._error_count: int = 0
        self._last_tick_ts: Optional[float] = None

        self._log = logging.getLogger(
            f"{__name__}.{type(self).__name__}"
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the adapter in a background asyncio task."""
        if self._running:
            self._log.warning("[%s] already running", self.SOURCE)
            return
        self._running = True
        self._start_time = time.monotonic()
        self._task = asyncio.create_task(
            self._safe_run(), name=f"adapter:{self.SOURCE}"
        )
        self._log.info("[%s] started", self.SOURCE)

    async def stop(self) -> None:
        """Signal the adapter to stop and wait for the task to finish."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        self._log.info(
            "[%s] stopped — events=%d ticks=%d errors=%d",
            self.SOURCE,
            self._events_published,
            self._tick_count,
            self._error_count,
        )

    async def _safe_run(self) -> None:
        """Wrapper that catches top-level exceptions and logs them."""
        try:
            await self._run()
        except asyncio.CancelledError:
            pass
        except Exception:
            self._log.exception("[%s] unhandled error in _run()", self.SOURCE)
        finally:
            self._running = False

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def _run(self) -> None:
        """Main adapter loop.  Must honour ``self._running``."""

    # ------------------------------------------------------------------
    # Checkpoint helpers (thin wrappers around CheckpointStore)
    # ------------------------------------------------------------------

    async def load_checkpoint(self, scope: str) -> Optional[Dict[str, Any]]:
        """Load a checkpoint for this source + scope."""
        return await self._cp_store.load(self.SOURCE, scope)

    async def save_checkpoint(self, scope: str, data: Dict[str, Any]) -> None:
        """Persist a checkpoint for this source + scope."""
        await self._cp_store.save(self.SOURCE, scope, data)

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    async def publish_event(self, event: SourceEvent) -> None:
        """Publish a SourceEvent to the MessageBus ``source_event`` topic."""
        if self._bus is None:
            self._log.debug("[%s] no bus configured — event dropped", self.SOURCE)
            return
        try:
            await self._bus.publish(_BUS_TOPIC, event.to_bus_dict())
            self._events_published += 1
            self._last_tick_ts = time.monotonic()
        except Exception:
            self._error_count += 1
            self._log.exception("[%s] failed to publish event", self.SOURCE)

    def _record_tick(self) -> None:
        """Increment tick counter and update last-tick timestamp."""
        self._tick_count += 1
        self._last_tick_ts = time.monotonic()

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Return a health/status dict for monitoring endpoints."""
        uptime: Optional[float] = None
        if self._start_time is not None:
            uptime = round(time.monotonic() - self._start_time, 1)

        last_tick_age: Optional[float] = None
        if self._last_tick_ts is not None:
            last_tick_age = round(time.monotonic() - self._last_tick_ts, 1)

        return {
            "source": self.SOURCE,
            "feed": self.FEED,
            "running": self._running,
            "uptime_seconds": uptime,
            "events_published": self._events_published,
            "tick_count": self._tick_count,
            "error_count": self._error_count,
            "last_tick_seconds_ago": last_tick_age,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
