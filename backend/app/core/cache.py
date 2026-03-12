"""Optional Redis cache layer with in-memory fallback.

Use for: feature aggregator results (TTL 60s), market data snapshots (TTL 30s),
council votes for same-symbol within cooldown window.
When REDIS_URL is unset or Redis is unavailable, falls back to in-memory dict (no cache).
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_redis_client = None
_redis_available = False
_memory_fallback: dict = {}  # key -> (expiry_ts, value)
_fallback_lock = asyncio.Lock()


def _make_key(prefix: str, *parts: Any) -> str:
    """Build a cache key from prefix and parts."""
    raw = ":".join(str(p) for p in parts)
    if len(raw) > 200:
        raw = hashlib.sha256(raw.encode()).hexdigest()
    return f"{prefix}:{raw}"


async def _get_redis():
    """Lazy init Redis client; returns None if unavailable."""
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client if _redis_available else None
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return None
    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(url, socket_connect_timeout=2, decode_responses=True)
        await _redis_client.ping()
        _redis_available = True
        logger.info("Redis cache connected")
        return _redis_client
    except Exception as e:
        logger.debug("Redis cache unavailable (%s), using no-cache fallback", e)
        _redis_available = False
        return None


async def get(prefix: str, *key_parts: Any) -> Optional[Any]:
    """Get value from cache. Returns None if miss or cache disabled."""
    key = _make_key(prefix, *key_parts)
    client = await _get_redis()
    if client:
        try:
            raw = await asyncio.wait_for(client.get(key), timeout=1.0)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            return None
    # In-memory fallback (per-process, TTL respected)
    async with _fallback_lock:
        entry = _memory_fallback.get(key)
        if entry is None:
            return None
        expiry, val = entry
        if time.time() > expiry:
            _memory_fallback.pop(key, None)
            return None
        return val
    return None


async def set(prefix: str, ttl_seconds: int, value: Any, *key_parts: Any) -> bool:
    """Set value in cache with TTL. Returns True if stored."""
    key = _make_key(prefix, *key_parts)
    client = await _get_redis()
    if client:
        try:
            raw = json.dumps(value, default=str)
            await asyncio.wait_for(client.setex(key, ttl_seconds, raw), timeout=1.0)
            return True
        except Exception:
            return False
    # In-memory fallback
    async with _fallback_lock:
        _memory_fallback[key] = (time.time() + ttl_seconds, value)
    return True


async def delete(prefix: str, *key_parts: Any) -> bool:
    """Delete key from cache."""
    key = _make_key(prefix, *key_parts)
    client = await _get_redis()
    if client:
        try:
            await asyncio.wait_for(client.delete(key), timeout=1.0)
            return True
        except Exception:
            return False
    async with _fallback_lock:
        _memory_fallback.pop(key, None)
    return True


def is_available() -> bool:
    """Return True if Redis is connected (best-effort)."""
    return _redis_available
