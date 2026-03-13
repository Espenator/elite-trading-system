"""Per-source rate limiting for data swarm API quotas.

- Alpaca REST: 200 requests/min
- Unusual Whales: token bucket (configurable)
- FinViz Elite: 1 request/second max, conservative
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Limits: requests per minute (RPM) or per second (RPS)
ALPACA_REST_RPM = 200
UW_RPM = 120  # Conservative; adjust per plan
FINVIZ_RPS = 1.0


class RateLimiter:
    """Async rate limiter per source. Uses sliding window + semaphore."""

    def __init__(
        self,
        name: str,
        requests_per_minute: Optional[float] = None,
        requests_per_second: Optional[float] = None,
    ) -> None:
        self.name = name
        self._rpm = requests_per_minute
        self._rps = requests_per_second
        self._lock = asyncio.Lock()
        self._timestamps: list[float] = []
        self._warn_at_ratio = 0.8  # Log warning at 80% usage

    async def acquire(self) -> None:
        """Wait until a request is allowed, then record it."""
        async with self._lock:
            now = time.monotonic()
            self._prune(now)
            if self._rps is not None:
                # 1 request per 1/rps seconds
                if self._timestamps:
                    elapsed = now - self._timestamps[-1]
                    wait = (1.0 / self._rps) - elapsed
                    if wait > 0:
                        await asyncio.sleep(wait)
            elif self._rpm is not None:
                # Sliding window: max rpm in the last 60 seconds
                if len(self._timestamps) >= self._rpm:
                    wait_until = self._timestamps[0] + 60.0
                    wait = wait_until - time.monotonic()
                    if wait > 0:
                        await asyncio.sleep(wait)
                    self._prune(time.monotonic())
            self._timestamps.append(time.monotonic())

    def _prune(self, now: float) -> None:
        """Drop timestamps older than 60 seconds."""
        cutoff = now - 60.0
        self._timestamps = [t for t in self._timestamps if t > cutoff]

    def usage_ratio(self) -> float:
        """Current usage vs limit (0.0–1.0+). Best-effort for logging."""
        if self._rpm is not None and self._rpm > 0:
            return len(self._timestamps) / self._rpm
        if self._rps is not None and self._rps > 0:
            return len(self._timestamps) / (self._rps * 60)
        return 0.0


_registry: Dict[str, RateLimiter] = {}
_registry_lock = asyncio.Lock()


def _make_limiter(source: str) -> RateLimiter:
    if source == "alpaca_rest":
        return RateLimiter(source, requests_per_minute=ALPACA_REST_RPM)
    if source.startswith("uw_"):
        return RateLimiter(source, requests_per_minute=UW_RPM)
    if source.startswith("finviz_"):
        return RateLimiter(source, requests_per_second=FINVIZ_RPS)
    return RateLimiter(source, requests_per_minute=60)


async def get_rate_limiter(source: str) -> RateLimiter:
    """Get or create the rate limiter for a given source."""
    global _registry
    async with _registry_lock:
        if source not in _registry:
            _registry[source] = _make_limiter(source)
        return _registry[source]


def get_rate_limiter_sync(source: str) -> RateLimiter:
    """Sync get (for tests or non-async contexts). Creates with default limits."""
    global _registry
    if source not in _registry:
        _registry[source] = _make_limiter(source)
    return _registry[source]
