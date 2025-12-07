"""
Elite Trading System - FastAPI Backend
Version 7.0 - Glass House Edition
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import signals
import uvicorn

app = FastAPI(
    title="Elite Trading System API",
    version="7.0",
    description="Aurora Glass House Trading System - Real-time Signal API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signals.router)

@app.get("/")
async def root():
    return {
        "name": "Elite Trading System API",
        "version": "7.0",
        "status": "operational",
        "description": "Aurora Glass House Trading System",
        "endpoints": {
            "docs": "/docs",
            "signals": "/api/signals",
            "health": "/api/signals/health/system"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Import new route modules
from routes import market, trading

# Include new routers
app.include_router(market.router)
app.include_router(trading.router)

# WebSocket endpoint for real-time price updates
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            import yfinance as yf
            btc = yf.Ticker("BTC-USD")
            eth = yf.Ticker("ETH-USD")
            
            btc_data = btc.history(period="1d")
            eth_data = eth.history(period="1d")
            
            if not btc_data.empty and not eth_data.empty:
                btc_price = float(btc_data['Close'].iloc[-1])
                eth_price = float(eth_data['Close'].iloc[-1])
                
                btc_change = ((btc_price - float(btc_data['Open'].iloc[0])) / float(btc_data['Open'].iloc[0])) * 100
                eth_change = ((eth_price - float(eth_data['Open'].iloc[0])) / float(eth_data['Open'].iloc[0])) * 100
                
                await websocket.send_json({
                    "type": "price_update",
                    "data": {
                        "BTC": {"symbol": "BTC", "price": round(btc_price, 2), "change_percent_24h": round(btc_change, 2)},
                        "ETH": {"symbol": "ETH", "price": round(eth_price, 2), "change_percent_24h": round(eth_change, 2)}
                    },
                    "timestamp": datetime.now().isoformat()
                })
            
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Import WebSocket manager
from websocket_manager import ws_manager
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates
    Frontend connects at: ws://localhost:8000/ws
    """
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Send periodic updates every 3 seconds
            import sqlite3
            import os
            import json
            
            # Get latest signals from database
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "trading.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get signal counts by tier
            cursor.execute("SELECT tier, COUNT(*) FROM signals GROUP BY tier")
            tier_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get latest 10 signals
            cursor.execute("SELECT ticker, tier, current_price, percent_change, global_confidence FROM signals ORDER BY timestamp DESC LIMIT 10")
            recent_signals = []
            for row in cursor.fetchall():
                recent_signals.append({
                    "ticker": row[0],
                    "tier": row[1],
                    "currentPrice": row[2],
                    "percentChange": row[3],
                    "globalConfidence": row[4]
                })
            
            conn.close()
            
            # Send update to client
            update = {
                "type": "system_update",
                "data": {
                    "tierCounts": tier_counts,
                    "recentSignals": recent_signals,
                    "timestamp": datetime.now().isoformat(),
                    "status": "operational"
                }
            }
            
            await websocket.send_json(update)
            await asyncio.sleep(3)
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        print("Client disconnected normally")
    except Exception as e:
        print(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

# CORS configuration for frontend
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
