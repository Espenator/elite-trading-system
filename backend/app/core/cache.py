"""Optional Redis cache layer with graceful fallback.

When REDIS_URL is set and Redis is available: get/set/delete work as expected.
When Redis is unavailable or not configured: get returns None, set/delete are no-op.
System must work without Redis (no dependency on Redis for core flow).
"""
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_redis_client: Any = None
_redis_available: bool = False


def _get_redis():
    """Lazy init Redis connection. Returns None if unavailable."""
    global _redis_client, _redis_available
    if _redis_client is not None or _redis_available is False and _redis_client is None:
        if _redis_client is not None:
            return _redis_client
        url = os.getenv("REDIS_URL", "").strip()
        if not url:
            return None
        try:
            import redis.asyncio as aioredis
            _redis_client = aioredis.from_url(url, socket_connect_timeout=2, decode_responses=True)
            _redis_available = True
            return _redis_client
        except Exception as e:
            logger.debug("Redis not available (%s) — cache disabled", e)
            _redis_available = False
            _redis_client = None
            return None
    return _redis_client


async def cache_get(key: str) -> Optional[str]:
    """Get value by key. Returns None if not found or Redis unavailable."""
    client = _get_redis()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception as e:
        logger.debug("Cache get failed for %s: %s", key[:50], e)
        return None


async def cache_set(key: str, value: str, ttl_sec: int = 60) -> bool:
    """Set value with TTL. Returns True if stored, False if Redis unavailable."""
    client = _get_redis()
    if client is None:
        return False
    try:
        await client.set(key, value, ex=ttl_sec)
        return True
    except Exception as e:
        logger.debug("Cache set failed for %s: %s", key[:50], e)
        return False


async def cache_delete(key: str) -> bool:
    """Delete key. Returns True if deleted, False if Redis unavailable."""
    client = _get_redis()
    if client is None:
        return False
    try:
        await client.delete(key)
        return True
    except Exception as e:
        logger.debug("Cache delete failed for %s: %s", key[:50], e)
        return False


def is_redis_available() -> bool:
    """Return True if Redis was successfully connected."""
    return _redis_available and _redis_client is not None


# ---------------------------------------------------------------------------
# Convenience: JSON get/set for feature dicts and verdicts
# ---------------------------------------------------------------------------

async def cache_get_json(key: str) -> Optional[dict]:
    """Get and JSON-decode value. Returns None if miss or error."""
    raw = await cache_get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


async def cache_set_json(key: str, value: dict, ttl_sec: int = 60) -> bool:
    """JSON-encode and set value."""
    try:
        return await cache_set(key, json.dumps(value, default=str), ttl_sec=ttl_sec)
    except Exception:
        return False
