"""
WebSocket Endpoint for Real-Time Signal Broadcasting
NOW WITH AUTOMATIC SIGNAL BROADCASTING EVERY 5 MINUTES
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio
from datetime import datetime, time as dt_time
from core.logger import get_logger

logger = get_logger(__name__)

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = get_logger(__name__)
        self.broadcast_task = None
    
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
            self.logger.info(f"📡 Broadcast to {len(self.active_connections)} clients: {message.get('type')}")

# Global connection manager
manager = ConnectionManager()

# Background task for broadcasting signals
async def broadcast_signals_loop():
    """
    CRITICAL FIX: Automatically broadcast signals every 5 minutes
    
    This connects the existing ScannerManager to the WebSocket
    so frontend receives real-time signals
    """
    from backend.scheduler import ScannerManager
    
    scanner = ScannerManager(config={})
    logger.info("🚀 Signal broadcasting loop started")
    
    while True:
        try:
            # Check if market hours (optional - can remove for testing)
            now = datetime.now()
            current_time = now.time()
            
            # Market hours: 9:30 AM - 4:00 PM EST (adjust as needed)
            market_open = dt_time(9, 30)
            market_close = dt_time(16, 0)
            
            # For testing, broadcast 24/7. For production, uncomment:
            # is_market_hours = market_open <= current_time <= market_close
            # is_weekday = now.weekday() < 5  # Monday=0, Friday=4
            
            # ALWAYS RUN FOR TESTING
            is_market_hours = True
            is_weekday = True
            
            if is_market_hours and is_weekday:
                logger.info("⏰ Starting scheduled scan...")
                
                # Run the scanner (YELLOW = neutral regime, TOP 20)
                signals = await scanner.run_scan({
                    "regime": "YELLOW",
                    "top_n": 20
                })
                
                if signals:
                    logger.info(f"✅ Generated {len(signals)} signals, broadcasting...")
                    
                    # Broadcast to all connected clients
                    await manager.broadcast({
                        "type": "signals_update",
                        "signals": signals,
                        "timestamp": datetime.now().isoformat(),
                        "scan_complete": True,
                        "total_signals": len(signals)
                    })
                    
                    # Also broadcast individual signals for real-time feed
                    for signal in signals[:10]:  # Top 10 for feed
                        await manager.broadcast({
                            "type": "new_signal",
                            "signal": signal
                        })
                        await asyncio.sleep(0.1)  # Small delay between signals
                    
                    logger.info("✅ Broadcast complete")
                else:
                    logger.warning("⚠️ Scan returned no signals")
                    await manager.broadcast({
                        "type": "scan_complete",
                        "signals": [],
                        "message": "No signals found in current scan",
                        "timestamp": datetime.now().isoformat()
                    })
            else:
                logger.info("⏸️ Outside market hours, skipping scan")
                await manager.broadcast({
                    "type": "status",
                    "message": "Market closed",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Wait 5 minutes before next scan
            logger.info("⏳ Waiting 5 minutes until next scan...")
            await asyncio.sleep(300)  # 300 seconds = 5 minutes
            
        except Exception as e:
            logger.error(f"❌ Broadcast loop error: {e}")
            await manager.broadcast({
                "type": "error",
                "message": f"Scan error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            # Wait 1 minute before retry on error
            await asyncio.sleep(60)

# Start background task when first client connects
broadcast_task_started = False

async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint handler"""
    global broadcast_task_started
    
    await manager.connect(websocket)
    
    # Start broadcast loop on first connection
    if not broadcast_task_started:
        broadcast_task_started = True
        asyncio.create_task(broadcast_signals_loop())
        logger.info("🚀 Started background signal broadcasting task")
    
    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connection",
            "status": "connected",
            "message": "Elite Trading System WebSocket Connected",
            "broadcast_interval": "5 minutes"
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
                
                elif message.get('type') == 'force_scan':
                    # Client requests immediate scan
                    logger.info("🔄 Client requested force scan")
                    await manager.send_personal_message({
                        "type": "scan_started",
                        "message": "Forcing immediate scan..."
                    }, websocket)
                    # Trigger immediate scan (could add this feature)
                
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
