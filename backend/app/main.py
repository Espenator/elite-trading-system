"""FastAPI application entry point."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import stocks, quotes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Elite Trading System Backend API - Finviz Integration",
    version="1.0.0",
    debug=settings.DEBUG
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

