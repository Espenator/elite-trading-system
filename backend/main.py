"""
Elite Trading System - Main FastAPI Application
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

# Import routers
from backend.api.routes import signals, trading, market, config
from backend.api.websocket_endpoint import websocket_endpoint, manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("?? Elite Trading System Starting...")
    print("? FastAPI server initialized")
    print("? WebSocket manager ready")
    yield
    # Shutdown
    print("?? Elite Trading System shutting down...")

app = FastAPI(
    title="Elite Trading System API",
    description="AI-Powered Trading Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(signals.router, prefix="/api", tags=["signals"])
app.include_router(trading.router, prefix="/api", tags=["trading"])
app.include_router(market.router, prefix="/api", tags=["market"])
app.include_router(config.router, prefix="/api", tags=["config"])

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket)

# Health check
@app.get("/api/health")
async def health_check():
    return {
        "status": "active",
        "latency": 12,
        "connections": len(manager.active_connections)
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Elite Trading System API",
        "version": "1.0.0",
        "status": "operational"
    }

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
