from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import sys
import os
from pathlib import Path
from datetime import datetime

from core.logger import setup_logger
from core.event_bus import EventBus
from backend.scheduler import ScannerManager

# Initialize logger
logger = setup_logger()
event_bus = EventBus()

# Create FastAPI app
app = FastAPI(
    title="Elite Trading System API",
    description="Backend API for algorithmic trading system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load config
config_path = Path(__file__).parent.parent / "config.yaml"
import yaml
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# Initialize scanner manager
scanner_manager = ScannerManager(config=config)

# In-memory storage
signals_db = []
positions_db = []

# Pydantic models
class Signal(BaseModel):
    symbol: str
    direction: str
    score: float
    entry_price: float
    timestamp: str

class TradeApproval(BaseModel):
    signal_id: str
    approved: bool

class SettingsUpdate(BaseModel):
    key: str
    value: Any

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 70)
    logger.info("🚀 Elite Trading System Backend - STARTING")
    logger.info("=" * 70)
    logger.info(f"📊 Trading style: {config.get('trading', {}).get('style', 'unknown')}")
    logger.info(f"🎯 Risk level: {config.get('trading', {}).get('risk_level', 'unknown')}")
    logger.info(f"💰 Account value: {config.get('trading', {}).get('initial_capital', 0)}")
    logger.info("=" * 70)
    logger.info("✅ Backend ready")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Backend shutting down...")

@app.get("/")
async def root():
    return {"message": "Elite Trading System API", "status": "online"}

@app.get("/api/status")
async def get_status():
    return {"status": "running", "version": "1.0.0"}

# ⭐ FIXED: Added /scan endpoint (without /api prefix) for frontend compatibility
@app.post("/scan")
async def trigger_scan(payload: Dict[str, Any]):
    """Main scan endpoint called by frontend"""
    try:
        start_time = datetime.now()
        logger.info(f"🔍 Scan request received: {payload}")
        
        # Extract parameters
        regime = payload.get("regime", "YELLOW")
        min_bible_score = payload.get("min_bible_score", 40)
        top_n = payload.get("top_n", 20)
        custom_weights = payload.get("custom_weights", None)
        
        # Run the scan
        results = await scanner_manager.run_scan({
            "regime": regime,
            "min_bible_score": min_bible_score,
            "top_n": top_n,
            "custom_weights": custom_weights
        })
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Build response matching frontend expectations
        response = {
            "final_signals": results,
            "regime": regime,
            "finviz_count": len(results) * 5,  # Mock data
            "bible_passed": len(results) * 3,  # Mock data
            "structure_passed": len(results) * 2,  # Mock data
            "composite_scored": len(results),
            "scan_duration_seconds": duration
        }
        
        logger.info(f"✅ Scan complete: {len(results)} signals in {duration:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"❌ Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Keep the /api/scan endpoint for backward compatibility
@app.post("/api/scan")
async def api_trigger_scan(params: Dict[str, Any]):
    """Alternative endpoint with /api prefix"""
    return await trigger_scan(params)

@app.get("/api/signals")
async def get_signals():
    return {"signals": signals_db}

@app.get("/api/positions")
async def get_positions():
    return {"positions": positions_db}

@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    try:
        config[settings.key] = settings.value
        return {"success": True, "message": f"Updated {settings.key}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

