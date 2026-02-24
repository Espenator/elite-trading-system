"""
WebSocket connection manager for broadcasting to all connected clients.
Import broadcast_ws(channel, data) from here to push updates.
"""

import asyncio
from fastapi import WebSocket
from typing import Set

# Set of all connected WebSocket clients
_ws_connections: Set[WebSocket] = set()


def add_connection(websocket: WebSocket):
    """Add a WebSocket connection to the set."""
    _ws_connections.add(websocket)


def remove_connection(websocket: WebSocket):
    """Remove a WebSocket connection from the set."""
    _ws_connections.discard(websocket)


async def broadcast_ws(channel: str, data: dict | list):
    """
    Send JSON message to all connected WebSocket clients.
    Call from route handlers when data changes (e.g. agent status, data source health).
    
    Example:
        await broadcast_ws("agents", {"type": "status_changed", "agent_id": 1})
    """
    msg = {"channel": channel, "data": data}
    dead = set()
    for ws in _ws_connections:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _ws_connections.discard(ws)
