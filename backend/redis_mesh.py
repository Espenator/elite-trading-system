"""
Embodier Trader — Redis Streams Event Mesh.

Bridges events between PC1 (ESPENMAIN) and PC2 (ProfitTrader) via Redis Streams.
Replaces the in-process MessageBus for cross-machine communication.

Architecture:
  PC1 runs this as PUBLISHER: reads from local MessageBus → writes to Redis Streams
  PC2 runs this as SUBSCRIBER: reads from Redis Streams → feeds local API/GPU worker

Streams:
  embodier:signals    — trade signals from SignalEngine
  embodier:positions  — position updates from PositionManager
  embodier:regime     — market regime from RegimePublisher
  embodier:dashboard  — aggregated dashboard state
  embodier:health     — system health snapshots
  embodier:gpu:tasks  — GPU work queue (PC2 consumes)
  embodier:gpu:results — GPU results (PC2 publishes)

Usage:
  # On PC1 (publisher mode):
  python redis_mesh.py --mode publish

  # On PC2 (subscriber mode):
  python redis_mesh.py --mode subscribe

  # Test connectivity:
  python redis_mesh.py --mode test
"""
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

log = logging.getLogger("redis_mesh")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [MESH] %(message)s")

REDIS_HOST = os.getenv("REDIS_HOST", "192.168.1.105")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PC_ROLE = os.getenv("PC_ROLE", "secondary")  # primary = PC1, secondary = PC2

# Topics to bridge
BRIDGED_TOPICS = {
    "signal.generated": "embodier:signals",
    "council.verdict": "embodier:signals",
    "order.submitted": "embodier:positions",
    "order.filled": "embodier:positions",
    "position.closed": "embodier:positions",
    "position.partial_exit": "embodier:positions",
    "regime.current": "embodier:regime",
    "perception.regime.openclaw": "embodier:regime",
    "system.heartbeat": "embodier:health",
    "alert.health": "embodier:health",
}

# Max stream length (auto-trim old entries)
MAX_STREAM_LEN = 1000


async def get_redis():
    """Create async Redis connection."""
    import redis.asyncio as aioredis
    return aioredis.Redis(
        host=REDIS_HOST, port=REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=5,
    )


# ── Publisher Mode (runs on PC1) ─────────────────────────────────
async def publish_loop():
    """Read from local MessageBus and publish to Redis Streams.

    This should be started as a background task on PC1's backend.
    """
    r = await get_redis()
    await r.ping()
    log.info("Publisher connected to Redis at %s:%d", REDIS_HOST, REDIS_PORT)

    try:
        # Import PC1's MessageBus
        from app.core.message_bus import MessageBus
        bus = MessageBus()

        published = 0

        async def _on_event(topic: str, data):
            nonlocal published
            stream = BRIDGED_TOPICS.get(topic)
            if not stream:
                return
            try:
                payload = json.dumps(data) if not isinstance(data, str) else data
                await r.xadd(
                    stream,
                    {"topic": topic, "payload": payload, "ts": str(time.time())},
                    maxlen=MAX_STREAM_LEN,
                )
                published += 1
                if published % 100 == 0:
                    log.info("Published %d events to Redis", published)
            except Exception as e:
                log.warning("Publish error: %s", e)

        # Subscribe to all bridged topics
        for topic in BRIDGED_TOPICS:
            bus.subscribe(topic, lambda data, t=topic: asyncio.create_task(_on_event(t, data)))
            log.info("Subscribed to %s -> %s", topic, BRIDGED_TOPICS[topic])

        log.info("Publisher active — bridging %d topics", len(BRIDGED_TOPICS))

        # Keep alive + publish dashboard snapshots
        while True:
            await asyncio.sleep(5)
            # Publish aggregated dashboard snapshot
            try:
                dashboard = await _build_dashboard_snapshot()
                await r.xadd(
                    "embodier:dashboard",
                    {"payload": json.dumps(dashboard), "ts": str(time.time())},
                    maxlen=MAX_STREAM_LEN,
                )
            except Exception as e:
                log.debug("Dashboard snapshot error: %s", e)

    finally:
        await r.close()


async def _build_dashboard_snapshot() -> dict:
    """Build a dashboard snapshot from local state (PC1 only)."""
    snapshot = {
        "ts": time.time(),
        "signals": [],
        "positions": [],
        "regime": "unknown",
    }
    try:
        from app.services.database import trade_db
        positions = trade_db.get_open_positions()
        snapshot["positions"] = [
            {"symbol": p.symbol, "side": p.side, "qty": p.qty,
             "entry_price": p.entry_price, "pnl": getattr(p, "unrealized_pnl", 0)}
            for p in (positions or [])
        ]
    except Exception:
        pass
    return snapshot


# ── Subscriber Mode (runs on PC2) ───────────────────────────────
async def subscribe_loop():
    """Read from Redis Streams and process events locally on PC2."""
    r = await get_redis()
    await r.ping()
    log.info("Subscriber connected to Redis at %s:%d", REDIS_HOST, REDIS_PORT)

    streams = {
        "embodier:signals": "0",
        "embodier:positions": "0",
        "embodier:regime": "0",
        "embodier:dashboard": "0",
        "embodier:health": "0",
    }

    received = 0
    while True:
        try:
            results = await r.xread(streams, count=20, block=2000)
            for stream_name, messages in results:
                for msg_id, data in messages:
                    streams[stream_name] = msg_id
                    received += 1

                    topic = data.get("topic", stream_name)
                    payload = data.get("payload", "{}")

                    if received % 50 == 0:
                        log.info("Received %d events (latest: %s)", received, topic)

                    # TODO: Forward to local API server's WebSocket clients
                    # For now, just cache in Redis for the API server to read

        except Exception as e:
            log.warning("Subscriber error: %s, retrying in 3s", e)
            await asyncio.sleep(3)


# ── Test Mode ────────────────────────────────────────────────────
async def test_connectivity():
    """Test Redis connectivity and stream status."""
    r = await get_redis()

    log.info("Testing Redis at %s:%d...", REDIS_HOST, REDIS_PORT)
    pong = await r.ping()
    log.info("PING: %s", "OK" if pong else "FAILED")

    # Check stream lengths
    for stream in ["embodier:signals", "embodier:positions", "embodier:regime",
                   "embodier:dashboard", "embodier:health", "gpu:tasks"]:
        try:
            length = await r.xlen(stream)
            log.info("Stream %-25s: %d entries", stream, length)
        except Exception:
            log.info("Stream %-25s: (not created yet)", stream)

    # Check GPU worker status
    gpu_status = await r.get("gpu:status")
    if gpu_status:
        status = json.loads(gpu_status)
        log.info("GPU Worker: %s (VRAM: %s GB)", status.get("gpu_name"), status.get("vram_gb"))
    else:
        log.info("GPU Worker: not registered")

    # Publish a test event
    await r.xadd("embodier:health", {
        "topic": "mesh.test",
        "payload": json.dumps({"test": True, "from": PC_ROLE, "ts": time.time()}),
        "ts": str(time.time()),
    }, maxlen=100)
    log.info("Test event published to embodier:health")

    await r.close()
    log.info("Connectivity test PASSED")


# ── Entry Point ──────────────────────────────────────────────────
async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--mode"
    if mode in ("--mode", "-m"):
        mode = sys.argv[2] if len(sys.argv) > 2 else "test"

    if mode == "publish":
        await publish_loop()
    elif mode == "subscribe":
        await subscribe_loop()
    elif mode == "test":
        await test_connectivity()
    else:
        log.error("Usage: python redis_mesh.py --mode [publish|subscribe|test]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
