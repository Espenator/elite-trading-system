"""Base adapter interface for all ingestion sources.

Every external data source — whether a live WebSocket stream, a periodic REST
poll, or a one-shot scrape — must implement ``BaseSourceAdapter`` so the
ingestion supervisor can manage its lifecycle uniformly.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.services.ingestion.models import SourceEvent, SourceKind

logger = logging.getLogger(__name__)


class BaseSourceAdapter(ABC):
    """Common contract for all ingestion adapters.

    Subclasses must implement:
        ``source_name``  — unique string identifying this source
        ``source_kind``  — how data is acquired (stream / incremental / snapshot / low_freq)
        ``poll_once()``  — fetch one batch of data and publish events (for polled sources)
        OR
        ``_run_stream()`` — long-running coroutine for streaming sources

    Optional overrides:
        ``backfill()``   — one-time historical fetch
        ``_on_start()``  — hook called after generic start logic
        ``_on_stop()``   — hook called before generic stop logic
    """

    # Subclasses set these
    source_name: str = "unknown"
    source_kind: SourceKind = SourceKind.SNAPSHOT

    # Default poll interval in seconds (only for polled adapters)
    poll_interval_seconds: float = 60.0

    # Backoff parameters
    _max_backoff: float = 300.0   # 5 minutes
    _base_backoff: float = 5.0
    _degraded_error_threshold: int = 5

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._start_time: Optional[float] = None
        self._sequence: int = 0

        # Observability counters
        self._events_published: int = 0
        self._errors: int = 0
        self._last_success_at: float = 0.0
        self._last_error_at: float = 0.0
        self._last_error_msg: str = ""
        self._reconnects: int = 0
        self._consecutive_errors: int = 0

        # Checkpoint state (loaded/saved by subclass or checkpoint store)
        self._checkpoint: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the adapter. Loads checkpoint, then enters poll/stream loop."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()

        await self.load_checkpoint()
        await self._on_start()

        if self.source_kind == SourceKind.STREAM:
            self._task = asyncio.create_task(self._stream_loop())
        else:
            self._task = asyncio.create_task(self._poll_loop())

        logger.info(
            "%s adapter started (kind=%s, interval=%.0fs)",
            self.source_name, self.source_kind.value, self.poll_interval_seconds,
        )

    async def stop(self) -> None:
        """Stop the adapter gracefully."""
        self._running = False
        await self._on_stop()

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        await self.save_checkpoint()
        logger.info("%s adapter stopped", self.source_name)

    # ------------------------------------------------------------------
    # Poll / stream loops
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Repeatedly call ``poll_once()`` with exponential backoff on errors."""
        backoff = 0.0
        while self._running:
            try:
                await self.poll_once()
                self._last_success_at = time.time()
                self._consecutive_errors = 0
                backoff = 0.0
                await self.save_checkpoint()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._errors += 1
                self._consecutive_errors += 1
                self._last_error_at = time.time()
                self._last_error_msg = str(exc)[:200]
                backoff = min(
                    self._base_backoff * (2 ** (self._consecutive_errors - 1)),
                    self._max_backoff,
                )
                logger.warning(
                    "%s poll error (backoff %.0fs): %s",
                    self.source_name, backoff, exc,
                )

            sleep = self.poll_interval_seconds + backoff
            try:
                await asyncio.sleep(sleep)
            except asyncio.CancelledError:
                break

    async def _stream_loop(self) -> None:
        """Reconnect loop around ``_run_stream()``."""
        backoff = 0.0
        while self._running:
            try:
                await self._run_stream()
                # Stream ended cleanly — reset backoff
                backoff = 0.0
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._errors += 1
                self._consecutive_errors += 1
                self._reconnects += 1
                self._last_error_at = time.time()
                self._last_error_msg = str(exc)[:200]
                backoff = min(
                    self._base_backoff * (2 ** (self._consecutive_errors - 1)),
                    self._max_backoff,
                )
                logger.warning(
                    "%s stream error, reconnect in %.0fs: %s",
                    self.source_name, backoff, exc,
                )

            if self._running:
                try:
                    await asyncio.sleep(backoff or 1.0)
                except asyncio.CancelledError:
                    break

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish_event(self, event: SourceEvent) -> None:
        """Publish a SourceEvent to the MessageBus."""
        if self._bus is None:
            logger.debug("%s: no message bus configured, skipping publish", self.source_name)
            return

        self._sequence += 1
        event.sequence = self._sequence

        try:
            await self._bus.publish(event.topic, event.to_dict())
            self._events_published += 1
        except Exception as exc:
            logger.warning("%s publish failed: %s", self.source_name, exc)
            self._errors += 1

    # ------------------------------------------------------------------
    # Health / observability
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Return per-source health snapshot."""
        now = time.time()
        uptime = now - self._start_time if self._start_time else 0
        last_success_age = now - self._last_success_at if self._last_success_at else None

        if not self._running:
            state = "stopped"
        elif self._consecutive_errors >= self._degraded_error_threshold:
            state = "degraded"
        elif self._last_success_at == 0.0 and uptime > self.poll_interval_seconds * 2:
            state = "offline"
        else:
            state = "healthy"

        return {
            "source": self.source_name,
            "kind": self.source_kind.value,
            "state": state,
            "running": self._running,
            "uptime_seconds": round(uptime, 1),
            "events_published": self._events_published,
            "errors": self._errors,
            "consecutive_errors": self._consecutive_errors,
            "reconnects": self._reconnects,
            "last_success_age_seconds": round(last_success_age, 1) if last_success_age else None,
            "last_error": self._last_error_msg or None,
            "events_per_minute": round(
                self._events_published / (uptime / 60), 2
            ) if uptime > 60 else 0,
            "checkpoint": self._checkpoint,
        }

    # ------------------------------------------------------------------
    # Checkpoint persistence
    # ------------------------------------------------------------------

    async def load_checkpoint(self) -> None:
        """Load durable checkpoint for this adapter (override for custom store)."""
        try:
            from app.services.ingestion.checkpoints import get_checkpoint_store
            store = get_checkpoint_store()
            self._checkpoint = store.load(self.source_name)
        except Exception as exc:
            logger.debug("%s checkpoint load failed: %s", self.source_name, exc)

    async def save_checkpoint(self) -> None:
        """Persist current checkpoint dict."""
        try:
            from app.services.ingestion.checkpoints import get_checkpoint_store
            store = get_checkpoint_store()
            store.save(self.source_name, self._checkpoint)
        except Exception as exc:
            logger.debug("%s checkpoint save failed: %s", self.source_name, exc)

    @property
    def is_running(self) -> bool:
        """Whether this adapter is currently running."""
        return self._running

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------

    async def _on_start(self) -> None:
        """Called after checkpoint load, before starting the poll/stream loop."""

    async def _on_stop(self) -> None:
        """Called before generic stop logic.  Override for cleanup."""

    # ------------------------------------------------------------------
    # Abstract / default methods for subclasses
    # ------------------------------------------------------------------

    async def poll_once(self) -> None:
        """Fetch one batch of data and publish events.

        Must be implemented by polled adapters (snapshot / incremental / low_freq).
        Streaming adapters implement ``_run_stream()`` instead.
        """
        raise NotImplementedError(f"{self.source_name}: poll_once not implemented")

    async def _run_stream(self) -> None:
        """Long-running coroutine for streaming adapters.

        Should block until the stream disconnects or is stopped.
        """
        raise NotImplementedError(f"{self.source_name}: _run_stream not implemented")

    async def backfill(self, **kwargs) -> Dict[str, Any]:
        """Optional one-time historical data fetch."""
        return {"status": "not_implemented"}
