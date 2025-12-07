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
