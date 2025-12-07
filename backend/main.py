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
