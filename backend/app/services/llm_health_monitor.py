"""
LLM Health Monitor — tracks provider rate limits, quota exhaustion, and health.

Broadcasts real-time alerts via WebSocket when:
    - A provider hits a rate limit (429)
    - A provider returns auth failure (401) — key revoked/expired/billing
    - A provider is overloaded (529)
    - All tiers are exhausted (total fallback failure)
    - A provider recovers after being degraded

UI endpoint: GET /api/v1/llm/health
WebSocket channel: "llm_health"

Events:
    llm.rate_limited      — 429 hit, includes retry-after
    llm.auth_failure      — 401/403, key invalid or billing exhausted
    llm.overloaded        — 529, provider capacity issue
    llm.quota_warning     — approaching rate limit (< 20% remaining)
    llm.all_exhausted     — every tier failed, system degraded
    llm.provider_recovered — circuit breaker closed, provider back online
    llm.provider_degraded  — circuit breaker opened, provider offline

Usage:
    from app.services.llm_health_monitor import llm_health_monitor
    llm_health_monitor.record_rate_limit("anthropic", retry_after=60)
    llm_health_monitor.record_auth_failure("anthropic", "Invalid authentication credentials")
    status = llm_health_monitor.get_status()
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    RATE_LIMITED = "rate_limited"
    AUTH_FAILURE = "auth_failure"
    OVERLOADED = "overloaded"
    DEGRADED = "degraded"       # circuit breaker open
    OFFLINE = "offline"         # multiple consecutive failures
    UNKNOWN = "unknown"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RateLimitEvent:
    provider: str
    timestamp: float
    http_status: int
    error_type: str           # "rate_limit", "auth_failure", "overloaded", "timeout", "error"
    message: str
    retry_after: Optional[float] = None
    remaining: Optional[int] = None   # from X-RateLimit-Remaining header
    limit: Optional[int] = None       # from X-RateLimit-Limit header
    reset_at: Optional[float] = None  # epoch seconds

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "timestamp": self.timestamp,
            "iso_time": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
            "http_status": self.http_status,
            "error_type": self.error_type,
            "message": self.message,
            "retry_after": self.retry_after,
            "remaining": self.remaining,
            "limit": self.limit,
            "reset_at": self.reset_at,
        }


@dataclass
class ProviderHealth:
    name: str
    display_name: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    total_calls: int = 0
    total_failures: int = 0
    total_rate_limits: int = 0
    rate_limit_events: deque = field(default_factory=lambda: deque(maxlen=50))
    # Rate limit header tracking
    remaining_requests: Optional[int] = None
    request_limit: Optional[int] = None
    limit_reset_at: Optional[float] = None
    # Circuit breaker state
    circuit_open: bool = False
    circuit_opened_at: Optional[float] = None
    # Auth state
    auth_valid: bool = True
    auth_error: Optional[str] = None

    def to_dict(self) -> dict:
        now = time.time()
        return {
            "name": self.name,
            "display_name": self.display_name,
            "status": self.status.value,
            "last_success": self.last_success,
            "last_success_ago_s": round(now - self.last_success, 1) if self.last_success else None,
            "last_failure": self.last_failure,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_rate_limits": self.total_rate_limits,
            "remaining_requests": self.remaining_requests,
            "request_limit": self.request_limit,
            "limit_reset_at": self.limit_reset_at,
            "circuit_open": self.circuit_open,
            "auth_valid": self.auth_valid,
            "auth_error": self.auth_error,
            "recent_events": [e.to_dict() for e in list(self.rate_limit_events)[-10:]],
            "health_pct": self._health_pct(),
        }

    def _health_pct(self) -> int:
        """0-100 health score."""
        if not self.auth_valid:
            return 0
        if self.circuit_open:
            return 10
        if self.status == ProviderStatus.RATE_LIMITED:
            return 30
        if self.status == ProviderStatus.OVERLOADED:
            return 20
        if self.total_calls == 0:
            return 100
        fail_rate = self.total_failures / max(self.total_calls, 1)
        return max(0, int(100 * (1 - fail_rate * 3)))


class LLMHealthMonitor:
    """Singleton health monitor for all LLM providers."""

    def __init__(self):
        self._providers: Dict[str, ProviderHealth] = {
            "ollama": ProviderHealth(name="ollama", display_name="Ollama (Local)"),
            "perplexity": ProviderHealth(name="perplexity", display_name="Perplexity Sonar Pro"),
            "anthropic": ProviderHealth(name="anthropic", display_name="Anthropic Claude"),
        }
        self._all_exhausted_count = 0
        self._last_broadcast: Dict[str, float] = {}  # throttle broadcasts
        self._broadcast_cooldown = 30  # seconds between same-type broadcasts

    # ── Record events ────────────────────────────────────────────────────────

    def record_success(self, provider: str) -> None:
        """Record a successful API call."""
        p = self._get_or_create(provider)
        p.total_calls += 1
        p.last_success = time.time()
        p.consecutive_failures = 0
        was_degraded = p.status != ProviderStatus.HEALTHY
        p.status = ProviderStatus.HEALTHY
        if was_degraded:
            self._fire_event("llm.provider_recovered", Severity.INFO, {
                "provider": provider,
                "display_name": p.display_name,
                "message": f"{p.display_name} is back online",
            })

    def record_failure(self, provider: str, error: str, http_status: int = 0) -> None:
        """Record a generic failure (not rate limit specific)."""
        p = self._get_or_create(provider)
        p.total_calls += 1
        p.total_failures += 1
        p.last_failure = time.time()
        p.last_error = error
        p.consecutive_failures += 1
        if p.consecutive_failures >= 3 and p.status != ProviderStatus.DEGRADED:
            p.status = ProviderStatus.DEGRADED
            self._fire_event("llm.provider_degraded", Severity.WARNING, {
                "provider": provider,
                "display_name": p.display_name,
                "consecutive_failures": p.consecutive_failures,
                "last_error": error,
                "message": f"{p.display_name} degraded after {p.consecutive_failures} consecutive failures",
            })

    def record_rate_limit(
        self,
        provider: str,
        http_status: int = 429,
        message: str = "",
        retry_after: Optional[float] = None,
        remaining: Optional[int] = None,
        limit: Optional[int] = None,
        reset_at: Optional[float] = None,
    ) -> None:
        """Record a rate limit event (429). This is the big one."""
        p = self._get_or_create(provider)
        p.total_calls += 1
        p.total_failures += 1
        p.total_rate_limits += 1
        p.last_failure = time.time()
        p.last_error = message or f"Rate limited (HTTP {http_status})"
        p.consecutive_failures += 1
        p.status = ProviderStatus.RATE_LIMITED
        if remaining is not None:
            p.remaining_requests = remaining
        if limit is not None:
            p.request_limit = limit
        if reset_at is not None:
            p.limit_reset_at = reset_at

        event = RateLimitEvent(
            provider=provider,
            timestamp=time.time(),
            http_status=http_status,
            error_type="rate_limit",
            message=message or f"Rate limited (HTTP {http_status})",
            retry_after=retry_after,
            remaining=remaining,
            limit=limit,
            reset_at=reset_at,
        )
        p.rate_limit_events.append(event)

        self._fire_event("llm.rate_limited", Severity.WARNING, {
            "provider": provider,
            "display_name": p.display_name,
            "http_status": http_status,
            "retry_after": retry_after,
            "remaining": remaining,
            "limit": limit,
            "message": f"{p.display_name} rate limited{f' — retry in {retry_after}s' if retry_after else ''}",
            "event": event.to_dict(),
        })

    def record_auth_failure(self, provider: str, message: str = "", http_status: int = 401) -> None:
        """Record authentication failure — key invalid, expired, or billing exhausted."""
        p = self._get_or_create(provider)
        p.total_calls += 1
        p.total_failures += 1
        p.last_failure = time.time()
        p.last_error = message
        p.auth_valid = False
        p.auth_error = message
        p.status = ProviderStatus.AUTH_FAILURE

        event = RateLimitEvent(
            provider=provider,
            timestamp=time.time(),
            http_status=http_status,
            error_type="auth_failure",
            message=message,
        )
        p.rate_limit_events.append(event)

        self._fire_event("llm.auth_failure", Severity.CRITICAL, {
            "provider": provider,
            "display_name": p.display_name,
            "http_status": http_status,
            "message": f"{p.display_name} authentication failed — {message}",
            "action_required": "Check API key in Settings → Data Sources, or check billing on provider dashboard",
            "event": event.to_dict(),
        })

    def record_overloaded(self, provider: str, message: str = "", http_status: int = 529) -> None:
        """Record provider overloaded (529 or 503)."""
        p = self._get_or_create(provider)
        p.total_calls += 1
        p.total_failures += 1
        p.last_failure = time.time()
        p.last_error = message
        p.status = ProviderStatus.OVERLOADED

        event = RateLimitEvent(
            provider=provider,
            timestamp=time.time(),
            http_status=http_status,
            error_type="overloaded",
            message=message,
        )
        p.rate_limit_events.append(event)

        self._fire_event("llm.overloaded", Severity.WARNING, {
            "provider": provider,
            "display_name": p.display_name,
            "message": f"{p.display_name} is overloaded — falling back to alternate provider",
            "event": event.to_dict(),
        })

    def record_quota_warning(self, provider: str, remaining: int, limit: int) -> None:
        """Record when a provider is approaching its rate limit (< 20% remaining)."""
        p = self._get_or_create(provider)
        p.remaining_requests = remaining
        p.request_limit = limit
        pct = (remaining / max(limit, 1)) * 100

        if pct < 20:
            self._fire_event("llm.quota_warning", Severity.WARNING, {
                "provider": provider,
                "display_name": p.display_name,
                "remaining": remaining,
                "limit": limit,
                "usage_pct": round(100 - pct, 1),
                "message": f"{p.display_name} at {round(100-pct)}% quota usage ({remaining}/{limit} requests remaining)",
            })

    def record_all_tiers_exhausted(self, task: str) -> None:
        """Record when all fallback tiers have failed for a task."""
        self._all_exhausted_count += 1
        self._fire_event("llm.all_exhausted", Severity.CRITICAL, {
            "task": task,
            "total_exhaustion_count": self._all_exhausted_count,
            "provider_statuses": {
                name: p.status.value for name, p in self._providers.items()
            },
            "message": f"All LLM providers failed for task '{task}' — system operating in degraded mode",
            "action_required": "Check LLM provider status in Settings or restart Ollama locally",
        })

    def record_circuit_breaker_opened(self, provider: str) -> None:
        """Record circuit breaker opening."""
        p = self._get_or_create(provider)
        p.circuit_open = True
        p.circuit_opened_at = time.time()
        if p.status not in (ProviderStatus.AUTH_FAILURE,):
            p.status = ProviderStatus.DEGRADED

        self._fire_event("llm.provider_degraded", Severity.WARNING, {
            "provider": provider,
            "display_name": p.display_name,
            "reason": "circuit_breaker",
            "consecutive_failures": p.consecutive_failures,
            "message": f"{p.display_name} circuit breaker opened — too many failures, skipping for 5 min",
        })

    def record_circuit_breaker_closed(self, provider: str) -> None:
        """Record circuit breaker closing (half-open probe succeeded)."""
        p = self._get_or_create(provider)
        p.circuit_open = False
        p.circuit_opened_at = None

    def update_rate_limit_headers(
        self,
        provider: str,
        remaining: Optional[int] = None,
        limit: Optional[int] = None,
        reset_at: Optional[float] = None,
    ) -> None:
        """Update rate limit tracking from response headers (called on success too)."""
        p = self._get_or_create(provider)
        if remaining is not None:
            p.remaining_requests = remaining
            if limit is not None:
                p.request_limit = limit
                # Check if approaching limit
                self.record_quota_warning(provider, remaining, limit)
        if reset_at is not None:
            p.limit_reset_at = reset_at

    # ── Query ────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Full health status for all providers — feeds the UI."""
        providers = {}
        for name, p in self._providers.items():
            providers[name] = p.to_dict()

        # Overall system health
        healthy_count = sum(1 for p in self._providers.values() if p.status == ProviderStatus.HEALTHY)
        total = len(self._providers)
        system_health = "healthy" if healthy_count == total else \
                        "degraded" if healthy_count > 0 else "critical"

        return {
            "system_health": system_health,
            "healthy_providers": healthy_count,
            "total_providers": total,
            "all_exhausted_count": self._all_exhausted_count,
            "providers": providers,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_provider_status(self, provider: str) -> Optional[Dict]:
        p = self._providers.get(provider)
        return p.to_dict() if p else None

    def is_provider_healthy(self, provider: str) -> bool:
        p = self._providers.get(provider)
        return p is not None and p.status == ProviderStatus.HEALTHY

    def get_degraded_providers(self) -> List[str]:
        return [
            name for name, p in self._providers.items()
            if p.status != ProviderStatus.HEALTHY
        ]

    # ── Internal ─────────────────────────────────────────────────────────────

    def _get_or_create(self, provider: str) -> ProviderHealth:
        if provider not in self._providers:
            self._providers[provider] = ProviderHealth(
                name=provider, display_name=provider.title()
            )
        return self._providers[provider]

    def _fire_event(self, event_type: str, severity: Severity, data: Dict[str, Any]) -> None:
        """Broadcast event via WebSocket and log it."""
        # Throttle: don't spam same event type within cooldown
        key = f"{event_type}:{data.get('provider', '')}"
        now = time.time()
        if key in self._last_broadcast and (now - self._last_broadcast[key]) < self._broadcast_cooldown:
            logger.debug("Throttled broadcast: %s", key)
            return
        self._last_broadcast[key] = now

        level = {
            Severity.INFO: logger.info,
            Severity.WARNING: logger.warning,
            Severity.CRITICAL: logger.error,
        }.get(severity, logger.info)
        level("LLM Health [%s] %s: %s", severity.value, event_type, data.get("message", ""))

        # Broadcast via WebSocket (non-blocking)
        payload = {
            "type": event_type,
            "severity": severity.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        try:
            from app.websocket_manager import broadcast_ws
            asyncio.get_event_loop().create_task(
                broadcast_ws("llm_health", payload)
            )
        except RuntimeError:
            # No event loop (startup or testing)
            logger.debug("No event loop for WebSocket broadcast")
        except Exception as e:
            logger.debug("WebSocket broadcast failed: %s", e)


# ── Singleton ────────────────────────────────────────────────────────────────

_instance: Optional[LLMHealthMonitor] = None


def get_llm_health_monitor() -> LLMHealthMonitor:
    global _instance
    if _instance is None:
        _instance = LLMHealthMonitor()
    return _instance


# Convenience alias
llm_health_monitor = get_llm_health_monitor()
