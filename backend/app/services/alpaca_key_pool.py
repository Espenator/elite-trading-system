"""AlpacaKeyPool — Manage multiple Alpaca API keys with role assignment.

Each Alpaca account allows exactly 1 WebSocket connection per endpoint.
Multiple keys = multiple WebSocket streams = 1000+ symbols in real-time.

Roles:
    trading      — Portfolio symbols only (from Alpaca positions API)
    discovery_a  — Top 500 high-priority symbols
    discovery_b  — Next 500 symbols (rotating universe)

Backward compatible: if no ALPACA_KEY_1/2/3 are set, falls back to the
single ALPACA_API_KEY / ALPACA_SECRET_KEY pair with role 'trading'.

Part of #39 — E0.1
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AlpacaKeyConfig:
    """A single Alpaca API key with its role and health metrics."""
    api_key: str
    secret_key: str
    role: str  # trading, discovery_a, discovery_b
    rate_limit_hits: int = 0
    consecutive_errors: int = 0
    total_successes: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    last_error_time: float = 0.0
    last_success_time: float = 0.0

    @property
    def is_healthy(self) -> bool:
        """Key is healthy if fewer than 5 consecutive errors."""
        return self.consecutive_errors < 5

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "api_key_suffix": self.api_key[-4:] if len(self.api_key) >= 4 else "****",
            "is_healthy": self.is_healthy,
            "rate_limit_hits": self.rate_limit_hits,
            "consecutive_errors": self.consecutive_errors,
            "total_successes": self.total_successes,
            "total_errors": self.total_errors,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
        }


_ROLE_ORDER = ["trading", "discovery_a", "discovery_b"]


class AlpacaKeyPool:
    """Pool of Alpaca API keys with role assignment and health tracking."""

    def __init__(self):
        self._keys: Dict[str, AlpacaKeyConfig] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """Load keys from settings, falling back to single-key mode."""
        try:
            from app.core.config import settings
            pairs = [
                (settings.ALPACA_KEY_1, settings.ALPACA_SECRET_1, "trading"),
                (settings.ALPACA_KEY_2, settings.ALPACA_SECRET_2, "discovery_a"),
                (settings.ALPACA_KEY_3, settings.ALPACA_SECRET_3, "discovery_b"),
            ]
            for api_key, secret_key, role in pairs:
                if api_key and secret_key:
                    self._keys[role] = AlpacaKeyConfig(
                        api_key=api_key,
                        secret_key=secret_key,
                        role=role,
                    )

            # Fallback: single-key mode using ALPACA_API_KEY
            if not self._keys:
                api_key = settings.ALPACA_API_KEY
                secret_key = settings.ALPACA_SECRET_KEY
                if api_key and secret_key:
                    self._keys["trading"] = AlpacaKeyConfig(
                        api_key=api_key,
                        secret_key=secret_key,
                        role="trading",
                    )

        except Exception as e:
            logger.warning("AlpacaKeyPool: failed to load from settings: %s", e)
            # Last resort: try os.environ directly
            import os
            api_key = os.getenv("ALPACA_API_KEY", "")
            secret_key = os.getenv("ALPACA_SECRET_KEY", "")
            if api_key and secret_key:
                self._keys["trading"] = AlpacaKeyConfig(
                    api_key=api_key,
                    secret_key=secret_key,
                    role="trading",
                )

        if self._keys:
            logger.info(
                "AlpacaKeyPool loaded %d key(s): %s",
                len(self._keys),
                ", ".join(sorted(self._keys.keys())),
            )
        else:
            logger.warning("AlpacaKeyPool: no Alpaca API keys configured")

    def get_key(self, role: str) -> Optional[AlpacaKeyConfig]:
        """Get the key for a given role. Returns None if not configured."""
        return self._keys.get(role)

    def get_all_keys(self) -> List[AlpacaKeyConfig]:
        """Get all configured keys, ordered by role priority."""
        return [
            self._keys[r]
            for r in _ROLE_ORDER
            if r in self._keys
        ]

    def get_healthy_keys(self) -> List[AlpacaKeyConfig]:
        """Get all healthy (non-errored) keys."""
        return [k for k in self.get_all_keys() if k.is_healthy]

    def report_error(self, role: str) -> None:
        """Report an error for a key role."""
        key = self._keys.get(role)
        if key:
            key.consecutive_errors += 1
            key.total_errors += 1
            key.last_error_time = time.time()
            if key.consecutive_errors >= 5:
                logger.warning(
                    "AlpacaKeyPool: key '%s' marked unhealthy (%d consecutive errors)",
                    role, key.consecutive_errors,
                )

    def report_success(self, role: str, latency_ms: float = 0.0) -> None:
        """Report a successful operation for a key role."""
        key = self._keys.get(role)
        if key:
            key.consecutive_errors = 0
            key.total_successes += 1
            key.last_success_time = time.time()
            # Running average latency
            n = key.total_successes
            key.avg_latency_ms = (
                (key.avg_latency_ms * (n - 1) + latency_ms) / n
            )

    def report_rate_limit(self, role: str) -> None:
        """Report a rate limit hit for a key role."""
        key = self._keys.get(role)
        if key:
            key.rate_limit_hits += 1
            logger.warning(
                "AlpacaKeyPool: rate limit hit on '%s' (total: %d)",
                role, key.rate_limit_hits,
            )

    @property
    def is_multi_key(self) -> bool:
        """True if more than one key is configured."""
        return len(self._keys) > 1

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def get_status(self) -> Dict:
        """Return pool status for health checks."""
        return {
            "key_count": len(self._keys),
            "is_multi_key": self.is_multi_key,
            "keys": {role: key.to_dict() for role, key in self._keys.items()},
        }


# ── Module-level singleton ────────────────────────────────────────────────
_key_pool: Optional[AlpacaKeyPool] = None


def get_alpaca_key_pool() -> AlpacaKeyPool:
    """Get or create the singleton AlpacaKeyPool."""
    global _key_pool
    if _key_pool is None:
        _key_pool = AlpacaKeyPool()
    return _key_pool
