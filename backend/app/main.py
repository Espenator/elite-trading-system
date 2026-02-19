"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.websocket_manager import add_connection, remove_connection
from app.core.config import settings
from app.api.v1 import (
    stocks,
    quotes,
    orders,
    system,
    training,
    signals,
    backtest_routes,
    status,
    agents,
    data_sources,
    sentiment,
    youtube_knowledge,
    portfolio,
    risk,
    strategy,
    performance,
    flywheel,
    logs,
    alerts,
    patterns,
    settings_routes,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize data schema on startup."""
    try:
        from app.data.storage import init_schema

        init_schema()
    except Exception:
        pass
    yield


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Elite Trading System Backend API - Finviz, Alpaca, ML Signals & Backtest",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    stocks.router, prefix=f"{settings.API_V1_PREFIX}/stocks", tags=["stocks"]
)

app.include_router(
    quotes.router, prefix=f"{settings.API_V1_PREFIX}/quotes", tags=["quotes"]
)

app.include_router(
    orders.router, prefix=f"{settings.API_V1_PREFIX}/orders", tags=["orders"]
)

app.include_router(
    system.router, prefix=f"{settings.API_V1_PREFIX}/system", tags=["system"]
)

app.include_router(
    training.router, prefix=f"{settings.API_V1_PREFIX}/training", tags=["training"]
)
app.include_router(
    signals.router, prefix=f"{settings.API_V1_PREFIX}/signals", tags=["signals"]
)
app.include_router(
    backtest_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/backtest",
    tags=["backtest"],
)
app.include_router(
    status.router, prefix=f"{settings.API_V1_PREFIX}/status", tags=["status"]
)
app.include_router(
    agents.router, prefix=f"{settings.API_V1_PREFIX}/agents", tags=["agents"]
)
app.include_router(
    data_sources.router,
    prefix=f"{settings.API_V1_PREFIX}/data-sources",
    tags=["data-sources"],
)
app.include_router(
    sentiment.router,
    prefix=f"{settings.API_V1_PREFIX}/sentiment",
    tags=["sentiment"],
)
app.include_router(
    youtube_knowledge.router,
    prefix=f"{settings.API_V1_PREFIX}/youtube-knowledge",
    tags=["youtube-knowledge"],
)
app.include_router(
    portfolio.router,
    prefix=f"{settings.API_V1_PREFIX}/portfolio",
    tags=["portfolio"],
)
app.include_router(
    risk.router,
    prefix=f"{settings.API_V1_PREFIX}/risk",
    tags=["risk"],
)
app.include_router(
    strategy.router,
    prefix=f"{settings.API_V1_PREFIX}/strategy",
    tags=["strategy"],
)
app.include_router(
    performance.router,
    prefix=f"{settings.API_V1_PREFIX}/performance",
    tags=["performance"],
)
app.include_router(
    flywheel.router,
    prefix=f"{settings.API_V1_PREFIX}/flywheel",
    tags=["flywheel"],
)
app.include_router(
    logs.router,
    prefix=f"{settings.API_V1_PREFIX}/logs",
    tags=["logs"],
)
app.include_router(
    alerts.router,
    prefix=f"{settings.API_V1_PREFIX}/alerts",
    tags=["alerts"],
)
app.include_router(
    patterns.router,
    prefix=f"{settings.API_V1_PREFIX}/patterns",
    tags=["patterns"],
)
app.include_router(
    settings_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/settings",
    tags=["settings"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Elite Trading System API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket at /ws for real-time updates.
    Frontend subscribes to channels (agents, datasources, etc.).
    Use app.websocket_manager.broadcast_ws(channel, data) from route handlers to push updates.
    """
    await websocket.accept()
    add_connection(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
    except Exception:
        pass
    finally:
        remove_connection(websocket)
