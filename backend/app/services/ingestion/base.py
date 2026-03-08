"""BaseSourceAdapter — abstract base for all ingestion source adapters.

Provides out-of-the-box:

* **Health metrics** — ``success_count``, ``error_count``,
  ``consecutive_failures``, ``last_success_ts``, ``last_error``.
* **Reconnect / backoff helper** — ``run_fetch()`` wraps the subclass
  ``fetch()`` in an exponential-backoff retry loop with full jitter.
* **Checkpoint integration hook** — subclasses call
  ``self.checkpoint.set(…)`` / ``self.checkpoint.get(…)`` via the
  pre-wired ``self.checkpoint`` attribute.

Subclass contract::

    class MyAdapter(BaseSourceAdapter):
        name = "my_adapter"
        source_kind = "poll"

        async def fetch(self) -> List[SourceEvent]:
            ...

        async def close(self) -> None:
            ...

Scheduler calls ``await adapter.run_fetch()`` which transparently handles
retries, records metrics, and returns the event list (or ``[]`` on total
failure so the caller never raises).
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.models.source_event import SourceEvent

logger = logging.getLogger(__name__)


class BaseSourceAdapter(ABC):
    """Abstract base class for all ingestion source adapters.

    Class-level attributes to override in subclasses
    ------------------------------------------------
    name          Unique adapter identifier used in checkpoints and health keys.
    source_kind   Transport type: ``"stream"`` | ``"poll"`` | ``"push"``.
    backoff_base  Initial retry sleep in seconds (default 1.0).
    backoff_max   Maximum retry sleep in seconds (default 60.0).
    backoff_factor  Multiplier applied per successive failure (default 2.0).
    max_retries   Number of retry attempts per ``run_fetch()`` call (default 3).
    """

    name: str = "base"
    source_kind: str = "poll"

    # Reconnect / backoff parameters
    backoff_base: float = 1.0
    backoff_max: float = 60.0
    backoff_factor: float = 2.0
    max_retries: int = 3

    def __init__(self) -> None:
        self._success_count: int = 0
        self._error_count: int = 0
        self._last_success_ts: Optional[float] = None
        self._last_error: Optional[str] = None
        self._last_error_ts: Optional[float] = None
        self._consecutive_failures: int = 0
        self._started_at: float = time.monotonic()

        # Lazily imported to avoid circular imports; available via property
        self._checkpoint: Any = None

    # ------------------------------------------------------------------
    # Checkpoint integration
    # ------------------------------------------------------------------

    @property
    def checkpoint(self):
        """Return the global CheckpointStore singleton."""
        if self._checkpoint is None:
            from app.data.checkpoint_store import checkpoint_store
            self._checkpoint = checkpoint_store
        return self._checkpoint

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def fetch(self) -> List[SourceEvent]:
        """Fetch events from the source.

        Must be implemented by every concrete adapter.  Should raise on
        unrecoverable errors; ``run_fetch()`` will retry transient ones.
        """

    @abstractmethod
    async def close(self) -> None:
        """Release any held resources (connections, file handles, etc.).

        Called once during graceful shutdown.  Should be idempotent.
        """

    # ------------------------------------------------------------------
    # Retry / backoff wrapper
    # ------------------------------------------------------------------

    async def run_fetch(self) -> List[SourceEvent]:
        """Invoke ``fetch()`` with exponential-backoff retry.

        * Tries up to ``max_retries + 1`` times.
        * Sleeps ``_backoff_delay(attempt)`` between attempts (full jitter).
        * Records success/failure metrics on each attempt.
        * Always returns a list — never raises — so callers are safe.

        Returns:
            List of :class:`~app.models.source_event.SourceEvent` objects,
            or ``[]`` if all attempts failed.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                events = await self.fetch()
                self._record_success()
                return events
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._record_error(str(exc))
                if attempt < self.max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        "%s fetch attempt %d/%d failed: %s — retrying in %.1fs",
                        self.name,
                        attempt + 1,
                        self.max_retries,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)

        logger.error(
            "%s: all %d fetch attempts failed. Last error: %s",
            self.name,
            self.max_retries,
            last_exc,
        )
        return []

    def _backoff_delay(self, attempt: int) -> float:
        """Compute exponential backoff with **full jitter**.

        Formula: ``sleep = random(0, min(backoff_max, backoff_base * factor^attempt))``
        Jitter prevents thundering-herd when multiple adapters restart simultaneously.
        """
        cap = min(self.backoff_max, self.backoff_base * (self.backoff_factor ** attempt))
        return random.uniform(0.0, cap)  # noqa: S311 — not cryptographic

    # ------------------------------------------------------------------
    # Metric recording
    # ------------------------------------------------------------------

    def _record_success(self) -> None:
        self._success_count += 1
        self._last_success_ts = time.time()
        self._consecutive_failures = 0

    def _record_error(self, error: str) -> None:
        self._error_count += 1
        self._last_error = error
        self._last_error_ts = time.time()
        self._consecutive_failures += 1

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Return a health-metrics dict for dashboard / API consumption.

        Keys
        ----
        name                 Adapter name.
        source_kind          Transport type.
        up_seconds           Seconds since adapter was constructed.
        success_count        Total successful fetches.
        error_count          Total failed fetch attempts.
        success_rate         success / (success + error), in [0, 1].
        consecutive_failures Number of consecutive failures without a success.
        last_success_age_s   Seconds since last successful fetch (None if never).
        last_error           Last error message string (None if no errors).
        status               ``"healthy"`` | ``"starting"`` | ``"degraded"``.
        """
        up_seconds = time.monotonic() - self._started_at
        total = self._success_count + self._error_count
        success_rate = self._success_count / total if total > 0 else 0.0

        last_success_age: Optional[float] = None
        if self._last_success_ts is not None:
            last_success_age = round(time.time() - self._last_success_ts, 1)

        return {
            "name": self.name,
            "source_kind": self.source_kind,
            "up_seconds": round(up_seconds),
            "success_count": self._success_count,
            "error_count": self._error_count,
            "success_rate": round(success_rate, 3),
            "consecutive_failures": self._consecutive_failures,
            "last_success_age_s": last_success_age,
            "last_error": self._last_error,
            "status": self._status_label(),
        }

    def _status_label(self) -> str:
        if self._consecutive_failures >= self.max_retries:
            return "degraded"
        if self._last_success_ts is None:
            return "starting"
        return "healthy"

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__} name={self.name!r} status={self._status_label()!r}>"
