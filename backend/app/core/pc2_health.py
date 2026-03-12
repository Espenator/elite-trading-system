"""PC2 (ProfitTrader) LAN health check and Redis dependency verification.

Checks that PC2 gRPC brain_service (:50051) and Redis (:6379) are reachable
before enabling cross-PC features. Called during lifespan startup.

Architecture:
  PC1 ESPENMAIN (192.168.1.105) — FastAPI, DuckDB, trade execution
  PC2 ProfitTrader (192.168.1.116) — GPU training, ML inference, brain_service
"""
import asyncio
import logging
import os
import socket

log = logging.getLogger(__name__)

# PC2 defaults — override via .env
PC2_HOST = os.getenv("PC2_HOST", "192.168.1.116")
PC2_GRPC_PORT = int(os.getenv("PC2_GRPC_PORT", "50051"))
REDIS_HOST = os.getenv("REDIS_HOST", "192.168.1.105")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


def _check_tcp(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except (socket.error, OSError):
        return False


async def check_pc2_health() -> dict:
    """Check PC2 gRPC brain_service reachability.

    Returns dict with status and whether brain-dependent council stages
    should be enabled.
    """
    grpc_ok = await asyncio.to_thread(_check_tcp, PC2_HOST, PC2_GRPC_PORT)

    if grpc_ok:
        log.info("✅ PC2 gRPC brain_service reachable at %s:%d", PC2_HOST, PC2_GRPC_PORT)
    else:
        log.warning(
            "⚠️ PC2 gRPC brain_service UNREACHABLE at %s:%d — "
            "brain-dependent council stages will run in degraded mode",
            PC2_HOST, PC2_GRPC_PORT,
        )

    return {
        "pc2_host": PC2_HOST,
        "grpc_reachable": grpc_ok,
        "grpc_port": PC2_GRPC_PORT,
        "brain_enabled": grpc_ok,
    }


async def check_redis_health() -> dict:
    """Check Redis connectivity for cross-PC MessageBus bridge.

    Redis is REQUIRED for PC1↔PC2 event routing. If unreachable,
    cross-PC features are disabled but the system continues operating
    in single-PC mode.
    """
    redis_url = os.getenv("REDIS_URL", "").strip()

    # If REDIS_URL is empty/unset, Redis is explicitly disabled
    if not redis_url:
        log.info("ℹ️ REDIS_URL not set — running in single-PC mode (no cross-PC MessageBus)")
        return {
            "configured": False,
            "reachable": False,
            "mode": "single_pc",
            "detail": "REDIS_URL not configured",
        }

    # Parse host/port from redis URL (redis://host:port or just host:port)
    try:
        if "://" in redis_url:
            # redis://host:port/db or redis://host:port
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            r_host = parsed.hostname or REDIS_HOST
            r_port = parsed.port or REDIS_PORT
        else:
            parts = redis_url.split(":")
            r_host = parts[0]
            r_port = int(parts[1]) if len(parts) > 1 else REDIS_PORT
    except Exception:
        r_host = REDIS_HOST
        r_port = REDIS_PORT

    tcp_ok = await asyncio.to_thread(_check_tcp, r_host, r_port)

    if tcp_ok:
        # Verify actual Redis protocol (PING/PONG)
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(redis_url, socket_timeout=3)
            pong = await client.ping()
            await client.aclose()
            redis_ok = pong is True
        except Exception as e:
            log.warning("Redis TCP open but PING failed: %s", e)
            redis_ok = False
    else:
        redis_ok = False

    if redis_ok:
        log.info("✅ Redis reachable at %s:%d — cross-PC MessageBus ENABLED", r_host, r_port)
    else:
        log.warning(
            "⚠️ Redis UNREACHABLE at %s:%d — cross-PC features DISABLED. "
            "PC2 brain_service discoveries will NOT reach PC1 OrderExecutor. "
            "Start Redis or set REDIS_URL= to suppress this warning.",
            r_host, r_port,
        )

    return {
        "configured": True,
        "reachable": redis_ok,
        "host": r_host,
        "port": r_port,
        "mode": "dual_pc" if redis_ok else "single_pc_degraded",
    }


async def run_infrastructure_checks() -> dict:
    """Run all infrastructure health checks at startup.

    Called from main.py lifespan before enabling services that depend
    on PC2 or Redis.
    """
    log.info("=" * 60)
    log.info("🔍 Infrastructure Health Check")
    log.info("=" * 60)

    pc2 = await check_pc2_health()
    redis = await check_redis_health()

    summary = {
        "pc2": pc2,
        "redis": redis,
        "dual_pc_operational": pc2["grpc_reachable"] and redis.get("reachable", False),
    }

    if summary["dual_pc_operational"]:
        log.info("✅ Dual-PC mode OPERATIONAL — PC2 brain + Redis bridge active")
    else:
        reasons = []
        if not pc2["grpc_reachable"]:
            reasons.append("PC2 gRPC unreachable")
        if not redis.get("reachable", False):
            reasons.append("Redis unreachable" if redis.get("configured") else "Redis not configured")
        log.warning("⚠️ Single-PC mode — %s", ", ".join(reasons))

    log.info("=" * 60)
    return summary
