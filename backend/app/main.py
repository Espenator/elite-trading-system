"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import stocks, quotes, orders, system, training, signals, backtest_routes, status, openclaw

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
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
    stocks.router,
    prefix=f"{settings.API_V1_PREFIX}/stocks",
    tags=["stocks"]
)
app.include_router(
    quotes.router,
    prefix=f"{settings.API_V1_PREFIX}/quotes",
    tags=["quotes"]
)
app.include_router(
    orders.router,
    prefix=f"{settings.API_V1_PREFIX}/orders",
    tags=["orders"]
)
app.include_router(
    system.router,
    prefix=f"{settings.API_V1_PREFIX}/system",
    tags=["system"]
)
app.include_router(
    training.router,
    prefix=f"{settings.API_V1_PREFIX}/training",
    tags=["training"]
)
app.include_router(
    signals.router,
    prefix=f"{settings.API_V1_PREFIX}/signals",
    tags=["signals"]
)
app.include_router(
    backtest_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/backtest",
    tags=["backtest"]
)
app.include_router(
    status.router,
    prefix=f"{settings.API_V1_PREFIX}/status",
    tags=["status"]
)
app.include_router(
    openclaw.router,
    prefix=f"{settings.API_V1_PREFIX}/openclaw",
    tags=["openclaw"]
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Elite Trading System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
