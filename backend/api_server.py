"""
Embodier Trader — Lightweight API-Only Server for PC2.

This is the SPLIT architecture: instead of loading the entire monolith
(35 agents, 12 services, DuckDB, Alpaca streams), this server ONLY
serves the FastAPI HTTP/WebSocket endpoints and proxies data from:
  - PC1's backend via Redis Streams (real-time events)
  - Local GPU worker via Redis queues (feature engineering, scoring)
  - Local brain_service via gRPC (LLM inference)

Starts in <2 seconds. Never blocks the event loop.
"""
import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Windows ProactorEventLoop fix
if sys.platform == "win32":
    from asyncio.proactor_events import _ProactorBasePipeTransport
    _orig = _ProactorBasePipeTransport._call_connection_lost
    def _silent(self, exc):
        try:
            _orig(self, exc)
        except (ConnectionResetError, OSError):
            pass
    _ProactorBasePipeTransport._call_connection_lost = _silent

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json

log = logging.getLogger("api_server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

# Redis connection for event mesh
_redis = None
_ws_connections: set = set()
_subscriptions: dict = {}  # channel -> set of websockets


async def get_redis():
    """Get or create Redis connection."""
    global _redis
    if _redis is None:
        import redis.asyncio as aioredis
        host = os.getenv("REDIS_HOST", "192.168.1.105")
        _redis = aioredis.Redis(host=host, port=6379, decode_responses=True)
    return _redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Minimal startup — no heavy services, just Redis mesh connection."""
    log.info("=" * 60)
    log.info("Embodier API Server (PC2 Lightweight) starting...")
    log.info("=" * 60)

    # Connect to Redis
    try:
        r = await get_redis()
        await r.ping()
        log.info("Redis mesh connected at %s:6379", os.getenv("REDIS_HOST", "192.168.1.105"))
    except Exception as e:
        log.warning("Redis not available: %s (will retry)", e)

    # Start Redis subscriber for real-time data from PC1
    sub_task = asyncio.create_task(_redis_subscriber())
    # Start heartbeat for WebSocket clients
    hb_task = asyncio.create_task(_ws_heartbeat())
    # Start GPU worker health check
    gpu_task = asyncio.create_task(_gpu_health_loop())

    log.info("Embodier API Server ONLINE — lightweight mode (no engine)")
    log.info("  GPU Worker: redis queue 'gpu:tasks'")
    log.info("  Brain gRPC: localhost:50051")
    log.info("  Event Mesh: Redis Streams from PC1")

    yield

    sub_task.cancel()
    hb_task.cancel()
    gpu_task.cancel()
    if _redis:
        await _redis.close()
    log.info("API Server shutdown complete")


app = FastAPI(title="Embodier Trader PC2", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Endpoint ──────────────────────────────────────────────
@app.get("/health")
@app.get("/api/v1/health")
async def health():
    """Lightweight health check — never blocks."""
    gpu_ok = _gpu_status.get("available", False)
    brain_ok = await _check_brain()
    redis_ok = False
    try:
        r = await get_redis()
        redis_ok = await r.ping()
    except Exception:
        pass

    status = "healthy" if (redis_ok and brain_ok) else "degraded"
    return {
        "status": status,
        "mode": "pc2-lightweight",
        "components": {
            "redis_mesh": {"status": "healthy" if redis_ok else "unhealthy"},
            "brain_grpc": {"status": "healthy" if brain_ok else "unhealthy"},
            "gpu_worker": {
                "status": "healthy" if gpu_ok else "unhealthy",
                "gpu": _gpu_status.get("gpu_name", "unknown"),
                "vram_gb": _gpu_status.get("vram_gb", 0),
                "model": _gpu_status.get("model", "none"),
            },
        },
    }


# ── Dashboard Data (proxied from PC1 via Redis) ─────────────────
_cached_data = {}  # topic -> latest data from Redis

@app.get("/api/v1/dashboard")
async def dashboard():
    """Return cached dashboard data from PC1's Redis stream."""
    return _cached_data.get("dashboard", {"signals": [], "positions": [], "regime": "unknown"})


@app.get("/api/v1/signals")
async def signals():
    return _cached_data.get("signals", [])


@app.get("/api/v1/positions")
async def positions():
    return _cached_data.get("positions", [])


@app.get("/api/v1/regime")
async def regime():
    return _cached_data.get("regime", {"regime": "unknown", "probability": 0})


# ── GPU Feature Engineering Endpoint ─────────────────────────────
@app.post("/api/v1/gpu/features")
async def compute_features(request: Request):
    """Submit feature computation to GPU worker via Redis queue."""
    body = await request.json()
    r = await get_redis()

    task_id = f"feat_{int(asyncio.get_event_loop().time() * 1000)}"
    await r.xadd("gpu:tasks", {
        "task_id": task_id,
        "type": "features",
        "payload": json.dumps(body),
    })

    # Wait for result (with timeout)
    for _ in range(50):  # 5 seconds max
        result = await r.get(f"gpu:result:{task_id}")
        if result:
            await r.delete(f"gpu:result:{task_id}")
            return json.loads(result)
        await asyncio.sleep(0.1)

    return {"error": "GPU worker timeout", "task_id": task_id}


@app.post("/api/v1/gpu/score")
async def batch_score(request: Request):
    """Submit batch scoring to GPU worker."""
    body = await request.json()
    r = await get_redis()

    task_id = f"score_{int(asyncio.get_event_loop().time() * 1000)}"
    await r.xadd("gpu:tasks", {
        "task_id": task_id,
        "type": "score",
        "payload": json.dumps(body),
    })

    for _ in range(100):  # 10 seconds max
        result = await r.get(f"gpu:result:{task_id}")
        if result:
            await r.delete(f"gpu:result:{task_id}")
            return json.loads(result)
        await asyncio.sleep(0.1)

    return {"error": "GPU worker timeout", "task_id": task_id}


# ── Brain/LLM Proxy ─────────────────────────────────────────────
@app.post("/api/v1/brain/infer")
async def brain_infer(request: Request):
    """Proxy inference to local brain gRPC service."""
    body = await request.json()
    try:
        import grpc
        from brain_service import brain_pb2, brain_pb2_grpc

        channel = grpc.aio.insecure_channel("localhost:50051")
        stub = brain_pb2_grpc.BrainServiceStub(channel)
        response = await stub.InferCandidateContext(
            brain_pb2.InferRequest(
                symbol=body.get("symbol", ""),
                context=json.dumps(body.get("context", {})),
            )
        )
        await channel.close()
        return {"result": response.text, "model": response.model}
    except Exception as e:
        return {"error": str(e)}


# ── WebSocket ────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_connections.add(ws)
    log.info("WS client connected (%d total)", len(_ws_connections))
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "subscribe":
                ch = msg.get("channel", "all")
                _subscriptions.setdefault(ch, set()).add(ws)
            elif msg.get("type") == "pong":
                pass  # heartbeat response
    except WebSocketDisconnect:
        pass
    finally:
        _ws_connections.discard(ws)
        for subs in _subscriptions.values():
            subs.discard(ws)
        log.info("WS client disconnected (%d remaining)", len(_ws_connections))


# ── Background Tasks ─────────────────────────────────────────────
_gpu_status = {}


async def _check_brain() -> bool:
    """TCP check on brain gRPC port."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        await asyncio.to_thread(s.connect, ("localhost", 50051))
        s.close()
        return True
    except Exception:
        return False


async def _gpu_health_loop():
    """Periodically check GPU worker status."""
    global _gpu_status
    while True:
        try:
            r = await get_redis()
            status = await r.get("gpu:status")
            if status:
                _gpu_status = json.loads(status)
            else:
                _gpu_status = {"available": False}
        except Exception:
            _gpu_status = {"available": False}
        await asyncio.sleep(10)


async def _redis_subscriber():
    """Subscribe to Redis Streams from PC1 and cache + broadcast."""
    streams = {
        "embodier:signals": "0",
        "embodier:positions": "0",
        "embodier:regime": "0",
        "embodier:dashboard": "0",
        "embodier:health": "0",
    }
    while True:
        try:
            r = await get_redis()
            while True:
                results = await r.xread(streams, count=10, block=2000)
                for stream_name, messages in results:
                    for msg_id, data in messages:
                        streams[stream_name] = msg_id
                        topic = stream_name.replace("embodier:", "")
                        if "payload" in data:
                            parsed = json.loads(data["payload"])
                            _cached_data[topic] = parsed
                            # Broadcast to WebSocket clients
                            await _broadcast(topic, parsed)
        except Exception as e:
            log.warning("Redis subscriber error: %s, retrying in 5s", e)
            await asyncio.sleep(5)


async def _broadcast(channel: str, data: dict):
    """Broadcast to subscribed WebSocket clients."""
    msg = json.dumps({"channel": channel, "data": data})
    targets = list(_subscriptions.get(channel, set())) or list(_ws_connections)
    dead = []
    for ws in targets:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_connections.discard(ws)
        for subs in _subscriptions.values():
            subs.discard(ws)


async def _ws_heartbeat():
    """Send ping to all WebSocket clients every 30s."""
    while True:
        await asyncio.sleep(30)
        msg = json.dumps({"type": "ping", "ts": asyncio.get_event_loop().time()})
        for ws in list(_ws_connections):
            try:
                await ws.send_text(msg)
            except Exception:
                _ws_connections.discard(ws)


# ── Import existing API routes if available ──────────────────────
# Try to mount existing route modules for compatibility
try:
    from app.api.v1 import health as health_routes
    # Already have /health above, skip duplicate
except ImportError:
    pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", access_log=False)
