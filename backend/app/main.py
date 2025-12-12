# app/main.py - Elite Trading System v2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api.v1.items import router as items_router
from app.api.v1.stocks import router as stocks_router
from app.api.v1.websocket import router as websocket_router, manager
from app.api.v1.chart import router as chart_router
from app.db.session import init_db
from app.services.live_data_service import live_data_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Elite Trading System API...")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down...")
    live_data_service.shutdown()
    logger.info("Cleanup complete")


app = FastAPI(
    title="Elite Trading System API",
    description="API for fetching and managing stock data with live signal feed",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API routers
app.include_router(items_router, prefix="/api/v1/items", tags=["items"])
app.include_router(stocks_router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(chart_router, prefix="/api/chart", tags=["chart"])

# Include WebSocket router at API level
app.include_router(websocket_router, prefix="/api/v1", tags=["websocket"])


# Root-level WebSocket endpoint (for frontend compatibility)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Root-level WebSocket endpoint for live signal feed.
    
    Streams real-time trading signals generated from yfinance market data.
    
    Signal Format:
    {
        "type": "signals_update",
        "signals": [
            {
                "symbol": "AAPL",
                "signal_type": "momentum",
                "tier": "T1",
                "score": 85.5,
                "price": 178.50,
                "change_pct": 2.5,
                "volume_ratio": 2.3,
                "catalyst": "Strong momentum +2.5% with 2.3x vol",
                "rsi": 65.2,
                "momentum": 3.1,
                "timestamp": "2024-12-12T10:30:00"
            }
        ],
        "timestamp": "2024-12-12T10:30:00"
    }
    """
    await manager.connect(websocket)
    
    try:
        while True:
            message = await websocket.receive_text()
            await manager.handle_client_message(websocket, message)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/")
def root():
    return {
        "message": "Elite Trading System API",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "stocks": "/api/v1/stocks",
            "scrape": "/api/v1/stocks/scrape",
            "chart": "/api/chart/data/{symbol}",
            "websocket": "/ws (WebSocket for live signals)",
        },
        "features": [
            "Real-time signal feed via WebSocket",
            "Live market data from yfinance",
            "Multi-factor signal scoring (momentum, volume, RSI, VWAP)",
            "Tiered signal classification (T1/T2/T3)"
        ]
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "websocket_connections": len(manager.active_connections),
        "scanner_running": manager._is_running
    }
