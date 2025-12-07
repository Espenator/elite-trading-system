"""
Elite Trading System - FastAPI Backend
Version 7.0 - Glass House Edition - PRODUCTION READY
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
import sqlite3
import json
import os
from typing import List

# Import routes
from routes import signals, market, trading, ml_config

# Import WebSocket manager
from websocket_manager import ws_manager

# Initialize FastAPI app
app = FastAPI(
    title="Elite Trading System API",
    version="7.0",
    description="Aurora Glass House Trading System - Real-time Signal API"
)

# CORS Configuration (SINGLE INSTANCE ONLY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:5173",
        "http://localhost:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(signals.router)
app.include_router(market.router)
app.include_router(trading.router)
app.include_router(ml_config.router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "Elite Trading System API",
        "version": "7.0",
        "status": "operational",
        "description": "Aurora Glass House Trading System",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "signals": "/api/signals",
            "market": "/api/market/indices",
            "charts": "/api/market/charts/{symbol}",
            "trades": "/api/trades",
            "portfolio": "/api/portfolio",
            "health": "/api/signals/health/system",
            "websocket": "ws://localhost:8000/ws"
        }
    }


# Health check endpoint
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time signal updates
    Frontend connects at: ws://localhost:8000/ws
    """
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Get database path
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "trading.db")
            
            if not os.path.exists(db_path):
                await asyncio.sleep(3)
                continue
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get signal counts by tier
                cursor.execute("SELECT tier, COUNT(*) FROM signals GROUP BY tier")
                tier_counts = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Get latest 10 signals
                cursor.execute("""
                    SELECT ticker, tier, current_price, percent_change, global_confidence 
                    FROM signals 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """)
                recent_signals = []
                for row in cursor.fetchall():
                    recent_signals.append({
                        "ticker": row[0],
                        "tier": row[1],
                        "currentPrice": row[2] or 0.0,
                        "percentChange": row[3] or 0.0,
                        "globalConfidence": row[4] or 50
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
                
            except sqlite3.Error as e:
                print(f"Database error in WebSocket: {e}")
            except Exception as e:
                print(f"Error preparing WebSocket update: {e}")
            
            await asyncio.sleep(3)
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        print("Client disconnected normally")
    except Exception as e:
        print(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


# Startup event
@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("🚀 Elite Trading System Backend Started")
    print("=" * 60)
    print(f"✅ API Documentation: http://localhost:8000/docs")
    print(f"✅ WebSocket Endpoint: ws://localhost:8000/ws")
    print(f"✅ Signals API: http://localhost:8000/api/signals")
    print(f"✅ Market API: http://localhost:8000/api/market/indices")
    print(f"✅ Trading API: http://localhost:8000/api/trades")
    print(f"✅ ML Config API: http://localhost:8000/api/ml/config")
    print("=" * 60)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    print("\n🛑 Elite Trading System Backend Shutting Down...")


# Run server (only when executed directly)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
