"""
Elite Trading System - FastAPI Backend
Version 7.0 - Glass House Edition
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import signals
import uvicorn

# Create FastAPI app
app = FastAPI(
    title="Elite Trading System API",
    version="7.0",
    description="Aurora Glass House Trading System - Real-time Signal API"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(signals.router)


@app.get("/")
async def root():
    """Root endpoint - API status"""
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
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "7.0",
        "system": "operational"
    }


@app.get("/api/status")
async def api_status():
    """Detailed API status"""
    return {
        "api": "online",
        "database": "connected",
        "version": "7.0",
        "features": [
            "Real-time signals",
            "Multi-tier tracking",
            "System health monitoring",
            "Glass House transparency"
        ]
    }


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

