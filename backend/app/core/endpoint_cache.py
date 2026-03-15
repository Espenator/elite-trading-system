"""Lightweight in-memory TTL cache for API endpoints.

Prevents signal flicker (42→0→42) and reduces CPU load by caching
endpoint results for one scan interval. No Redis dependency.

Usage:
    from app.core.endpoint_cache import get_cached, set_cache, get_default_ttl

    cached = get_cached("signals:2026-03-15")
    if cached is not None:
        return cached
    result = await _compute_result()
    set_cache("signals:2026-03-15", result)
    return result
"""
import time
from typing import Any, Dict, Optional, Tuple

# key -> (timestamp, data)
_cache: Dict[str, Tuple[float, Any]] = {}


def get_default_ttl() -> float:
    """Return TTL in seconds matching the current scan interval."""
    try:
        from app.services.data_swarm.session_clock import get_scan_interval
        return float(get_scan_interval())
    except Exception:
        return 30.0


def get_cached(key: str, ttl: Optional[float] = None) -> Optional[Any]:
    """Return cached result if still fresh, else None."""
    entry = _cache.get(key)
    if entry is None:
        return None
    cached_at, data = entry
    effective_ttl = ttl if ttl is not None else get_default_ttl()
    if time.time() - cached_at > effective_ttl:
        return None
    return data


def set_cache(key: str, data: Any) -> None:
    """Store result in cache with current timestamp."""
    _cache[key] = (time.time(), data)


def invalidate(key: str) -> None:
    """Remove a specific cache entry."""
    _cache.pop(key, None)


def clear_all() -> None:
    """Clear entire cache (useful for tests)."""
    _cache.clear()
