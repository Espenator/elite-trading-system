"""Exponential-backoff reconnect helper for WebSocket / live adapters.

Usage::

    from app.services.ingestion.reconnect import ReconnectPolicy

    policy = ReconnectPolicy(name="alpaca_ws")
    while True:
        try:
            await connect_and_stream()
            policy.on_success()
        except Exception as exc:
            delay = policy.on_failure(exc)
            if delay is None:
                raise          # max attempts reached
            await asyncio.sleep(delay)
"""
import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ReconnectPolicy:
    """Stateful exponential-backoff with jitter for connection retry loops.

    Parameters
    ----------
    name:
        Human-readable label for log messages.
    initial_delay:
        First backoff interval in seconds.
    max_delay:
        Cap on the computed backoff.
    multiplier:
        Factor applied to the delay after each failure.
    jitter:
        Max jitter added to each delay (uniform random in [0, jitter]).
    max_attempts:
        Hard cap; ``on_failure`` returns ``None`` when exceeded.
        0 = unlimited.
    """

    name: str = "adapter"
    initial_delay: float = 2.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: float = 5.0
    max_attempts: int = 0  # 0 = unlimited

    # ── Runtime state (not constructor args) ──────────────────────────────
    _attempt: int = field(default=0, init=False, repr=False)
    _current_delay: float = field(default=0.0, init=False, repr=False)
    _last_success_ts: Optional[float] = field(default=None, init=False, repr=False)
    _last_failure_ts: Optional[float] = field(default=None, init=False, repr=False)
    _consecutive_failures: int = field(default=0, init=False, repr=False)
    _total_reconnects: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._current_delay = self.initial_delay

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def on_success(self) -> None:
        """Reset backoff state after a successful connection/operation."""
        self._attempt = 0
        self._current_delay = self.initial_delay
        self._consecutive_failures = 0
        self._last_success_ts = time.monotonic()
        logger.debug("[%s] Connection succeeded — backoff reset", self.name)

    def on_failure(self, exc: Optional[Exception] = None) -> Optional[float]:
        """Record a failure and return the computed sleep duration.

        Returns ``None`` when ``max_attempts > 0`` and the attempt count
        has been exhausted, signalling the caller to give up.
        """
        self._attempt += 1
        self._consecutive_failures += 1
        self._total_reconnects += 1
        self._last_failure_ts = time.monotonic()

        if self.max_attempts > 0 and self._attempt > self.max_attempts:
            logger.error(
                "[%s] Max reconnect attempts (%d) exceeded — giving up",
                self.name, self.max_attempts,
            )
            return None

        delay = min(self._current_delay, self.max_delay)
        jitter = random.uniform(0.0, self.jitter)
        total = delay + jitter

        logger.warning(
            "[%s] Failure #%d (consecutive=%d): %s — reconnecting in %.1fs",
            self.name,
            self._attempt,
            self._consecutive_failures,
            exc or "unknown error",
            total,
        )

        # Advance for next call
        self._current_delay = min(self._current_delay * self.multiplier, self.max_delay)
        return total

    # ------------------------------------------------------------------
    # Convenience: managed reconnect loop
    # ------------------------------------------------------------------

    async def run_with_retry(self, coro_factory) -> None:
        """Run ``coro_factory()`` in a loop, applying backoff on failures.

        The loop exits only when ``max_attempts`` is exhausted or the task
        is cancelled.

        Parameters
        ----------
        coro_factory:
            A callable (no args) that returns an awaitable representing one
            attempt.  It must raise on failure.
        """
        while True:
            try:
                await coro_factory()
                self.on_success()
            except asyncio.CancelledError:
                logger.info("[%s] Reconnect loop cancelled", self.name)
                raise
            except Exception as exc:
                delay = self.on_failure(exc)
                if delay is None:
                    raise
                await asyncio.sleep(delay)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Return a dict suitable for health checks / metrics."""
        uptime_since_success: Optional[float] = None
        if self._last_success_ts is not None:
            uptime_since_success = round(time.monotonic() - self._last_success_ts, 1)
        return {
            "name": self.name,
            "attempt": self._attempt,
            "consecutive_failures": self._consecutive_failures,
            "total_reconnects": self._total_reconnects,
            "current_delay": round(self._current_delay, 2),
            "last_success_seconds_ago": uptime_since_success,
            "last_failure_ts": self._last_failure_ts,
        }
