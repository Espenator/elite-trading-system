"""
WebSocket Endpoint for Real-Time Signal Broadcasting
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio
from core.logger import get_logger

logger = get_logger(__name__)

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = get_logger(__name__)
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"✅ WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove disconnected WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.logger.info(f"❌ WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                self.logger.error(f"Broadcast failed for connection: {e}")
                disconnected.append(connection)
        
        # Remove dead connections
        for conn in disconnected:
            self.disconnect(conn)
        
        if message.get('type') != 'heartbeat':  # Don't log heartbeats
            self.logger.info(f"📡 Broadcast to {len(self.active_connections)} clients")

# Global connection manager
manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint handler"""
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connection",
            "status": "connected",
            "message": "Elite Trading System WebSocket Connected"
        }, websocket)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get('type') == 'ping':
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": message.get('timestamp')
                    }, websocket)
                
                elif message.get('type') == 'subscribe':
                    # Client wants to subscribe to signals
                    await manager.send_personal_message({
                        "type": "subscribed",
                        "channel": message.get('channel', 'signals')
                    }, websocket)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON"
                }, websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    
    finally:
        manager.disconnect(websocket)

# Utility function for broadcasting signals
async def broadcast_signal(signal: dict):
    """Broadcast a trading signal to all connected clients"""
    await manager.broadcast({
        "type": "signal",
        "data": signal
    })

# Utility function for broadcasting scan status
async def broadcast_scan_status(status: dict):
    """Broadcast scan status to all connected clients"""
    await manager.broadcast({
        "type": "scan_status",
        "data": status
    })
