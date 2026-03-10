"""
WebSocket connection manager for broadcasting to all connected clients.
Enhanced with: token auth, channel subscriptions, heartbeat, reconnection.
Import broadcast_ws(channel, data) from here to push updates.

Topic validation: subscribe/unsubscribe validate against WS_ALLOWED_CHANNELS
so unknown topics are rejected with structured error; connection/topic metrics emitted.
"""
import asyncio
import logging
import time
from typing import Any, Set, Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect, Query

logger = logging.getLogger(__name__)

# Channels allowed for WS subscription (subset of MessageBus or UI channels)
WS_ALLOWED_CHANNELS: Set[str] = {
    # Core trading channels
    "order", "risk", "kelly", "signals", "council", "health",
    "market_data", "alerts", "outcomes", "system",
    # Frontend dashboard channels (must match frontend WS_CHANNELS in config/api.js)
    "agents", "data_sources", "datasources", "trades", "logs",
    "sentiment", "alignment", "council_verdict",
    "homeostasis", "circuit_breaker", "swarm", "macro", "market",
}

# --- Connection Registry ---
_ws_connections: Set[WebSocket] = set()
_channel_subscriptions: Dict[str, Set[WebSocket]] = {}  # channel -> set of ws
_last_heartbeat: Dict[WebSocket, float] = {}  # ws -> last ping time

HEARTBEAT_INTERVAL = 30  # seconds
HEARTBEAT_TIMEOUT = 60  # seconds before disconnect

# --- Auth Token (simple shared secret for now, JWT upgrade in Phase 1) ---
_WS_AUTH_TOKEN: Optional[str] = None


def set_ws_auth_token(token: str):
    """Set the WebSocket auth token from config on startup."""
    global _WS_AUTH_TOKEN
    _WS_AUTH_TOKEN = token


def verify_ws_token(token: Optional[str]) -> bool:
    """Verify WebSocket connection token."""
    if _WS_AUTH_TOKEN is None:
        # Allow in development, block in production
        import os
        return os.getenv("TRADING_MODE", "live") != "live"
    return token == _WS_AUTH_TOKEN


async def accept_connection(websocket: WebSocket, token: Optional[str] = None) -> bool:
    """Accept WebSocket with optional token verification."""
    if not verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        logger.warning("WebSocket connection rejected: invalid token")
        return False
    await websocket.accept()
    _ws_connections.add(websocket)
    _last_heartbeat[websocket] = time.time()
    logger.info(f"WebSocket connected. Total: {len(_ws_connections)}")
    return True


def add_connection(websocket: WebSocket):
    """Add a WebSocket connection to the set."""
    _ws_connections.add(websocket)
    _last_heartbeat[websocket] = time.time()


def remove_connection(websocket: WebSocket):
    """Remove a WebSocket connection from the set."""
    _ws_connections.discard(websocket)
    _last_heartbeat.pop(websocket, None)
    # Remove from all channel subscriptions
    for subs in _channel_subscriptions.values():
        subs.discard(websocket)
    logger.info(f"WebSocket disconnected. Total: {len(_ws_connections)}")


def validate_channel(channel: str) -> tuple[bool, Optional[str]]:
    """Validate channel against allowed registry. Returns (valid, error_message)."""
    if not channel or not isinstance(channel, str):
        return False, "channel_required"
    if channel.strip() != channel:
        return False, "channel_invalid"
    if channel not in WS_ALLOWED_CHANNELS:
        return False, f"unknown_channel:{channel}"
    return True, None


def subscribe(websocket: WebSocket, channel: str) -> Dict[str, Any]:
    """Subscribe a client to a specific data channel. Validates against registry.
    Returns dict with success=True/False and optional error/reason for structured response.
    """
    try:
        from app.core.metrics import counter_inc
        counter_inc("ws_subscribe_attempt_total", {"channel": channel or "empty"})
    except Exception:
        pass
    valid, err = validate_channel(channel)
    if not valid:
        try:
            from app.core.metrics import counter_inc
            counter_inc("ws_subscribe_rejected_total", {"reason": err or "invalid"})
        except Exception:
            pass
        return {"success": False, "error": err, "channel": channel}
    if channel not in _channel_subscriptions:
        _channel_subscriptions[channel] = set()
    _channel_subscriptions[channel].add(websocket)
    return {"success": True, "channel": channel}


def unsubscribe(websocket: WebSocket, channel: str):
    """Unsubscribe a client from a channel. Validates channel; no-op if unknown."""
    valid, _ = validate_channel(channel)
    if valid and channel in _channel_subscriptions:
        _channel_subscriptions[channel].discard(websocket)


async def broadcast_ws(channel: str, data: dict | list, type: Optional[str] = None):
    """
    Send JSON message to all connected WebSocket clients.
    Canonical payload: {channel, type, data, ts}. If type is omitted, use data.get("type", "update").
    If channel has subscribers, send only to them. Otherwise broadcast to all.
    """
    ts = time.time()
    if isinstance(data, dict) and type is None:
        type = data.get("type", "update")
    else:
        type = type or "update"
    msg = {"channel": channel, "type": type, "data": data, "ts": ts}
    
    # Use channel subscribers if any, otherwise broadcast to all
    targets = _channel_subscriptions.get(channel, _ws_connections)
    if not targets:
        targets = _ws_connections
    
    dead = set()
    for ws in targets:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.add(ws)
    for ws in dead:
        remove_connection(ws)


async def send_to(websocket: WebSocket, data: dict):
    """Send data to a specific WebSocket client."""
    try:
        await websocket.send_json(data)
    except Exception:
        remove_connection(websocket)


async def heartbeat_loop():
    """Background task: send pings and clean up dead connections."""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        now = time.time()
        dead = set()
        for ws in list(_ws_connections):
            last = _last_heartbeat.get(ws, 0)
            if now - last > HEARTBEAT_TIMEOUT:
                dead.add(ws)
                continue
            try:
                await ws.send_json({"type": "ping", "ts": now})
            except Exception:
                dead.add(ws)
        for ws in dead:
            remove_connection(ws)
            try:
                await ws.close()
            except Exception:
                pass
        if dead:
            logger.info(f"Heartbeat cleaned {len(dead)} dead connections")


def handle_pong(websocket: WebSocket):
    """Update heartbeat timestamp when client sends pong."""
    _last_heartbeat[websocket] = time.time()


def get_connection_count() -> int:
    """Return current WebSocket connection count."""
    return len(_ws_connections)


def get_channel_info() -> dict:
    """Return channel subscription counts for monitoring."""
    return {
        "total_connections": len(_ws_connections),
        "channels": {ch: len(subs) for ch, subs in _channel_subscriptions.items()}
    }


# --- Risk & Drawdown Broadcast Helpers ---

async def broadcast_risk_update(risk_data: dict):
    """Broadcast risk score update to all subscribed clients."""
    await broadcast_ws("risk", {
        "type": "risk_score_update",
        "risk_score": risk_data.get("risk_score", 100),
        "grade": risk_data.get("grade", "A"),
        "warnings": risk_data.get("warnings", []),
        "trading_recommended": risk_data.get("trading_recommended", True),
        "ts": time.time(),
    })


async def broadcast_drawdown_alert(dd_data: dict):
    """Broadcast drawdown breach alert to all clients."""
    await broadcast_ws("risk", {
        "type": "drawdown_alert",
        "trading_allowed": dd_data.get("trading_allowed", True),
        "daily_pnl": dd_data.get("daily_pnl", 0),
        "daily_pnl_pct": dd_data.get("daily_pnl_pct", 0),
        "drawdown_breached": dd_data.get("drawdown_breached", False),
        "severity": "critical" if dd_data.get("drawdown_breached") else "info",
        "ts": time.time(),
    })


async def broadcast_kelly_update(kelly_data: dict):
    """Broadcast Kelly position sizing update."""
    await broadcast_ws("kelly", {
        "type": "kelly_update",
        **kelly_data,
        "ts": time.time(),
    })