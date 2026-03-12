"""Per-service async rate limiter (D2).

Provides two primitives:
  1. AsyncRateLimiter — token-bucket limiter per service key
  2. CircuitBreaker   — open/half-open/closed with configurable thresholds

Usage:
    from app.core.rate_limiter import get_rate_limiter, CircuitBreaker

    limiter = get_rate_limiter("alpaca")
    async with limiter:
        resp = await client.get(...)

    cb = CircuitBreaker("benzinga", failure_threshold=5, recovery_seconds=60)
    if cb.allow_request():
        try:
            result = await do_thing()
            cb.record_success()
        except Exception:
            cb.record_failure()

Alpaca Algo Trader Plus ($99/mo) limits:
  - REST: 10,000 requests/minute
  - WebSocket: unlimited symbol subscriptions
  - 1 WebSocket connection per account per endpoint
"""

import asyncio
import logging
import time
from typing import Dict

logger = logging.getLogger(__name__)


class AsyncRateLimiter:
    """Token-bucket rate limiter using asyncio.Semaphore + refill task.

    Parameters
    ----------
    name : str
        Service identifier (for logging).
    max_per_minute : int
        Maximum requests per 60-second window.
    max_concurrent : int
        Maximum concurrent in-flight requests (Semaphore cap).
    """

    def __init__(self, name: str, max_per_minute: int = 200, max_concurrent: int = 10):
        self.name = name
        self.max_per_minute = max_per_minute
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tokens = max_per_minute
        self._max_tokens = max_per_minute
        self._lock = asyncio.Lock()
        self._last_refill = time.monotonic()
        self._total_requests = 0
        self._total_waits = 0

    async def acquire(self) -> None:
        """Wait until both concurrency slot and rate token are available."""
        await self._semaphore.acquire()
        async with self._lock:
            self._refill()
            while self._tokens <= 0:
                self._total_waits += 1
                # Release lock, wait, re-acquire
                wait_time = 60.0 / self._max_tokens
                self._lock.release()
                await asyncio.sleep(wait_time)
                await self._lock.acquire()
                self._refill()
            self._tokens -= 1
            self._total_requests += 1

    def release(self) -> None:
        """Release concurrency slot."""
        self._semaphore.release()

    def _refill(self) -> None:
        """Add tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * (self._max_tokens / 60.0)
        if new_tokens >= 1:
            self._tokens = min(self._max_tokens, self._tokens + int(new_tokens))
            self._last_refill = now

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *exc):
        self.release()

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "max_per_minute": self.max_per_minute,
            "max_concurrent": self.max_concurrent,
            "tokens_available": self._tokens,
            "total_requests": self._total_requests,
            "total_waits": self._total_waits,
        }


class CircuitBreaker:
    """Three-state circuit breaker: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.

    Parameters
    ----------
    name : str
        Service identifier.
    failure_threshold : int
        Consecutive failures before opening the circuit.
    recovery_seconds : float
        Seconds to wait in OPEN state before transitioning to HALF_OPEN.
    half_open_max : int
        Max test requests in HALF_OPEN before fully closing.
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_seconds: float = 60.0,
        half_open_max: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.half_open_max = half_open_max

        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_attempts = 0
        self._last_failure_time = 0.0
        self._total_opens = 0
        self._total_rejects = 0

    @property
    def state(self) -> str:
        # Auto-transition from OPEN -> HALF_OPEN after recovery time
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_seconds:
                self._state = self.HALF_OPEN
                self._half_open_attempts = 0
                logger.info("CircuitBreaker[%s]: OPEN -> HALF_OPEN (recovery elapsed)", self.name)
        return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        s = self.state  # Triggers auto-transition
        if s == self.CLOSED:
            return True
        if s == self.HALF_OPEN:
            if self._half_open_attempts < self.half_open_max:
                self._half_open_attempts += 1
                return True
            return False
        # OPEN
        self._total_rejects += 1
        return False

    def record_success(self) -> None:
        """Record a successful request."""
        self._success_count += 1
        if self._state == self.HALF_OPEN:
            # Enough successes in half-open → close
            self._state = self.CLOSED
            self._failure_count = 0
            logger.info("CircuitBreaker[%s]: HALF_OPEN -> CLOSED (success)", self.name)
        elif self._state == self.CLOSED:
            self._failure_count = 0  # Reset consecutive failures

    def record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == self.HALF_OPEN:
            # Any failure in half-open → back to open
            self._state = self.OPEN
            self._total_opens += 1
            logger.warning("CircuitBreaker[%s]: HALF_OPEN -> OPEN (failure in test)", self.name)
        elif self._state == self.CLOSED and self._failure_count >= self.failure_threshold:
            self._state = self.OPEN
            self._total_opens += 1
            logger.warning(
                "CircuitBreaker[%s]: CLOSED -> OPEN (hit %d failures)",
                self.name, self._failure_count,
            )

    def reset(self) -> None:
        """Force reset to CLOSED."""
        self._state = self.CLOSED
        self._failure_count = 0
        self._half_open_attempts = 0

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_opens": self._total_opens,
            "total_rejects": self._total_rejects,
            "recovery_seconds": self.recovery_seconds,
        }


# ---------------------------------------------------------------------------
# Global registry of rate limiters (one per service key)
# ---------------------------------------------------------------------------
_limiters: Dict[str, AsyncRateLimiter] = {}

# Default rate limits per service
# Alpaca Algo Trader Plus plan: 10,000 req/min REST, unlimited WS subs.
# Previous default of 200/min was for Basic plan — wasting 98% of paid capacity.
# We use 8,000/min as headroom (80% of 10K) to avoid 429s at burst edges.
_DEFAULT_LIMITS = {
    "alpaca": {"max_per_minute": 8000, "max_concurrent": 50},
    "alpaca_data": {"max_per_minute": 8000, "max_concurrent": 50},
    "fred": {"max_per_minute": 120, "max_concurrent": 5},
    "edgar": {"max_per_minute": 10, "max_concurrent": 2},
    "unusual_whales": {"max_per_minute": 30, "max_concurrent": 3},
    "benzinga": {"max_per_minute": 20, "max_concurrent": 3},
    "squeezemetrics": {"max_per_minute": 10, "max_concurrent": 2},
    "finviz": {"max_per_minute": 30, "max_concurrent": 3},
    "newsapi": {"max_per_minute": 60, "max_concurrent": 5},
}


def get_rate_limiter(service: str, **overrides) -> AsyncRateLimiter:
    """Get or create a rate limiter for a service.

    Uses defaults from _DEFAULT_LIMITS, can be overridden with kwargs.
    """
    if service not in _limiters:
        defaults = _DEFAULT_LIMITS.get(service, {"max_per_minute": 60, "max_concurrent": 5})
        defaults.update(overrides)
        _limiters[service] = AsyncRateLimiter(name=service, **defaults)
    return _limiters[service]


def get_all_limiter_statuses() -> list:
    """Return status of all registered rate limiters."""
    return [limiter.get_status() for limiter in _limiters.values()]


# ---------------------------------------------------------------------------
# Global registry of circuit breakers (D4)
# ---------------------------------------------------------------------------
_breakers: Dict[str, CircuitBreaker] = {}

# Default circuit breaker settings per scraper service
_DEFAULT_BREAKER_SETTINGS = {
    "benzinga": {"failure_threshold": 5, "recovery_seconds": 120.0, "half_open_max": 2},
    "squeezemetrics": {"failure_threshold": 3, "recovery_seconds": 300.0, "half_open_max": 1},
    "capitol_trades": {"failure_threshold": 5, "recovery_seconds": 180.0, "half_open_max": 2},
    "finviz": {"failure_threshold": 5, "recovery_seconds": 60.0, "half_open_max": 2},
    "newsapi": {"failure_threshold": 5, "recovery_seconds": 60.0, "half_open_max": 2},
    "edgar": {"failure_threshold": 3, "recovery_seconds": 120.0, "half_open_max": 1},
}


def get_circuit_breaker(service: str, **overrides) -> CircuitBreaker:
    """Get or create a circuit breaker for a service.

    Uses defaults from _DEFAULT_BREAKER_SETTINGS, can be overridden with kwargs.
    """
    if service not in _breakers:
        defaults = _DEFAULT_BREAKER_SETTINGS.get(
            service,
            {"failure_threshold": 5, "recovery_seconds": 60.0, "half_open_max": 2},
        )
        defaults.update(overrides)
        _breakers[service] = CircuitBreaker(name=service, **defaults)
    return _breakers[service]


def get_all_circuit_breaker_statuses() -> list:
    """Return status of all registered circuit breakers."""
    return [cb.get_status() for cb in _breakers.values()]
