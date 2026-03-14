"""Persistent gRPC channel singleton for brain_service on PC2.

Provides a shared, keepalive-enabled gRPC channel that is reused
across all brain_client calls, eliminating per-call channel creation
overhead (~50-100ms saved per call).

Usage:
    from app.core.brain_channel import get_brain_channel, close_brain_channel
    channel = await get_brain_channel()
    # ... use channel ...
    await close_brain_channel()  # on app shutdown
"""
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

_channel = None
_channel_lock = asyncio.Lock()


async def get_brain_channel():
    """Return singleton persistent gRPC channel. Creates on first call."""
    global _channel
    async with _channel_lock:
        if _channel is None:
            try:
                import grpc.aio
            except ImportError:
                logger.warning("[brain_channel] grpc not installed")
                return None

            host = os.getenv("BRAIN_HOST", "localhost")
            port = int(os.getenv("BRAIN_PORT", "50051"))
            options = [
                ("grpc.keepalive_time_ms", 30_000),
                ("grpc.keepalive_timeout_ms", 10_000),
                ("grpc.keepalive_permit_without_calls", True),
                ("grpc.http2.max_pings_without_data", 0),
                ("grpc.connect_timeout_ms", 5000),
            ]
            _channel = grpc.aio.insecure_channel(
                f"{host}:{port}", options=options
            )
            logger.info(
                "[brain_channel] Persistent gRPC channel opened to %s:%d",
                host, port,
            )
    return _channel


async def close_brain_channel():
    """Close the persistent gRPC channel (call on app shutdown)."""
    global _channel
    if _channel is not None:
        try:
            await _channel.close()
        except Exception as e:
            logger.debug("[brain_channel] close error: %s", e)
        _channel = None
        logger.info("[brain_channel] gRPC channel closed")


async def check_brain_channel_health() -> bool:
    """Returns True if channel is in READY or IDLE state."""
    try:
        import grpc
        ch = await get_brain_channel()
        if ch is None:
            return False
        state = ch.get_state(try_to_connect=True)
        return state in (
            grpc.ChannelConnectivity.READY,
            grpc.ChannelConnectivity.IDLE,
        )
    except Exception as e:
        logger.error("[brain_channel] health check failed: %s", e)
        return False
