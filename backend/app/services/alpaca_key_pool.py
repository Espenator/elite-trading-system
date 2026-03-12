"""AlpacaKeyPool — Manage multiple Alpaca API keys with role assignment.

Each Alpaca account allows exactly 1 WebSocket connection per endpoint.
Multiple keys = multiple WebSocket streams = 1000+ symbols in real-time.

Two-PC Architecture (prevents WebSocket conflicts):
    PC1 (PC_ROLE=primary):   Key 1 only → trading role (portfolio WS + REST)
    PC2 (PC_ROLE=secondary): Key 2 only → discovery role (discovery WS + REST)

    Each PC opens WebSocket on ITS OWN key only. No conflicts because
    Alpaca allows 1 WS per account per endpoint — each PC uses a different account.

Single-PC fallback: if only ALPACA_API_KEY is set, uses it with role 'trading'.

Part of #39 — E0.1
"""
import logging
import os
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


_ROLE_ORDER = ["trading", "discovery", "discovery_rest", "discovery_a", "discovery_b"]


class AlpacaKeyPool:
    """Pool of Alpaca API keys with role assignment and health tracking."""

    def __init__(self):
        self._keys: Dict[str, AlpacaKeyConfig] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """Load keys from settings, filtered by PC_ROLE to prevent WS conflicts.

        Two-PC key assignment:
            PC_ROLE=primary   → loads Key 1 as 'trading' (portfolio WS + orders)
            PC_ROLE=secondary → loads Key 2 as 'discovery' (discovery WS + scanning)

        This ensures each PC only opens WebSocket on its OWN Alpaca account,
        avoiding the 1-WS-per-account-per-endpoint limit conflict.
        """
        pc_role = os.getenv("PC_ROLE", "primary").lower()
        self._pc_role = pc_role

        try:
            from app.core.config import settings
            pc_role = getattr(settings, "PC_ROLE", pc_role).lower()
            self._pc_role = pc_role

            if pc_role == "secondary":
                # PC2: only load Key 2 for discovery scanning
                if settings.ALPACA_KEY_2 and settings.ALPACA_SECRET_2:
                    self._keys["discovery"] = AlpacaKeyConfig(
                        api_key=settings.ALPACA_KEY_2,
                        secret_key=settings.ALPACA_SECRET_2,
                        role="discovery",
                    )
                elif settings.ALPACA_API_KEY and settings.ALPACA_SECRET_KEY:
                    # Fallback: use default key as discovery
                    self._keys["discovery"] = AlpacaKeyConfig(
                        api_key=settings.ALPACA_API_KEY,
                        secret_key=settings.ALPACA_SECRET_KEY,
                        role="discovery",
                    )
                logger.info(
                    "AlpacaKeyPool: PC2 (secondary) mode — discovery key only"
                )
            else:
                # PC1 (primary): load Key 1 for trading
                if settings.ALPACA_KEY_1 and settings.ALPACA_SECRET_1:
                    self._keys["trading"] = AlpacaKeyConfig(
                        api_key=settings.ALPACA_KEY_1,
                        secret_key=settings.ALPACA_SECRET_1,
                        role="trading",
                    )
                elif settings.ALPACA_API_KEY and settings.ALPACA_SECRET_KEY:
                    # Fallback: single-key mode
                    self._keys["trading"] = AlpacaKeyConfig(
                        api_key=settings.ALPACA_API_KEY,
                        secret_key=settings.ALPACA_SECRET_KEY,
                        role="trading",
                    )

                # PC1 can also load Key 2 for REST-only discovery calls
                # (no WebSocket — that's PC2's job)
                if settings.ALPACA_KEY_2 and settings.ALPACA_SECRET_2:
                    self._keys["discovery_rest"] = AlpacaKeyConfig(
                        api_key=settings.ALPACA_KEY_2,
                        secret_key=settings.ALPACA_SECRET_2,
                        role="discovery_rest",
                    )

                logger.info(
                    "AlpacaKeyPool: PC1 (primary) mode — trading key%s",
                    " + discovery REST key" if "discovery_rest" in self._keys else "",
                )

        except Exception as e:
            logger.warning("AlpacaKeyPool: failed to load from settings: %s", e)
            api_key = os.getenv("ALPACA_API_KEY", "")
            secret_key = os.getenv("ALPACA_SECRET_KEY", "")
            if api_key and secret_key:
                role = "discovery" if pc_role == "secondary" else "trading"
                self._keys[role] = AlpacaKeyConfig(
                    api_key=api_key,
                    secret_key=secret_key,
                    role=role,
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
    def pc_role(self) -> str:
        """Return this machine's PC role (primary or secondary)."""
        return getattr(self, "_pc_role", "primary")

    @property
    def is_multi_key(self) -> bool:
        """True if more than one key is configured."""
        return len(self._keys) > 1

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def get_ws_key(self) -> Optional[AlpacaKeyConfig]:
        """Get the key this PC should use for WebSocket connections.

        PC1 (primary)   → trading key (portfolio symbols)
        PC2 (secondary) → discovery key (discovery universe)

        Only ONE key per PC opens a WebSocket — prevents account conflicts.
        """
        if self.pc_role == "secondary":
            return self._keys.get("discovery")
        return self._keys.get("trading")

    def get_status(self) -> Dict:
        """Return pool status for health checks."""
        return {
            "pc_role": self.pc_role,
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
