"""
Elite Trading System - Backend API Server
FastAPI REST API for dashboard communication
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import yaml
from pathlib import Path

from core.logger import get_logger
from core.event_bus import event_bus

logger = get_logger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Elite Trading System API",
    description="Backend API for algorithmic trading system",
    version="1.0.0"
)

# CORS middleware (allow Streamlit frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load config
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# =============================================================================
# DATA MODELS
# =============================================================================

class Signal(BaseModel):
    """Signal data model"""
    symbol: str
    direction: str  # LONG or SHORT
    score: float
    velez_score: Dict[str, float]
    explosive_signal: bool
    compression_days: int
    fresh_ignition: Dict[str, float]
    whale_data: Optional[Dict] = None
    entry_price: float
    stop_price: float
    target_price: float
    timestamp: str

class Position(BaseModel):
    """Position data model"""
    symbol: str
    direction: str
    entry_price: float
    current_price: float
    shares: int
    stop_loss: float
    target_1: float
    target_2: float
    unrealized_pnl: float
    r_multiple: float
    entry_time: str

class TradeApproval(BaseModel):
    """User approval for a trade"""
    symbol: str
    approved: bool
    notes: Optional[str] = None

class SettingsUpdate(BaseModel):
    """Settings update from dashboard"""
    section: str
    key: str
    value: Any

# =============================================================================
# GLOBAL STATE (In-memory for now, will move to database)
# =============================================================================

class SystemState:
    """Global system state"""
    def __init__(self):
        self.signals: List[Signal] = []
        self.positions: List[Position] = []
        self.pending_approvals: Dict[str, Signal] = {}
        self.is_scanning: bool = False
        self.last_scan_time: Optional[datetime] = None
        self.market_data: Dict = {}
        
state = SystemState()

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "system": "Elite Trading System",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/status")
async def get_status():
    """Get system status"""
    return {
        "is_scanning": state.is_scanning,
        "last_scan_time": state.last_scan_time.isoformat() if state.last_scan_time else None,
        "active_positions": len(state.positions),
        "pending_signals": len(state.pending_approvals),
        "config": {
            "trading_style": config['user_preferences']['trading_style'],
            "ai_trust_level": config['ai_control']['ai_trust_level'],
            "max_positions": config['account']['max_positions']
        }
    }

@app.get("/api/signals", response_model=List[Signal])
async def get_signals(direction: Optional[str] = None):
    """
    Get current signals
    
    Args:
        direction: Filter by LONG or SHORT (optional)
    """
    signals = state.signals
    
    if direction:
        signals = [s for s in signals if s.direction == direction.upper()]
    
    # Sort by score descending
    signals = sorted(signals, key=lambda x: x.score, reverse=True)
    
    return signals

@app.get("/api/positions", response_model=List[Position])
async def get_positions():
    """Get open positions"""
    return state.positions

@app.post("/api/approve_trade")
async def approve_trade(approval: TradeApproval, background_tasks: BackgroundTasks):
    """
    Approve or reject a trade
    
    Args:
        approval: Trade approval decision
    """
    symbol = approval.symbol
    
    if symbol not in state.pending_approvals:
        raise HTTPException(status_code=404, detail=f"Signal for {symbol} not found")
    
    signal = state.pending_approvals[symbol]
    
    if approval.approved:
        logger.info(f"Trade approved by user: {symbol}")
        
        # Publish event for execution
        event_bus.publish('trade_approved', {
            'signal': signal.dict(),
            'notes': approval.notes
        })
        
        # Remove from pending
        del state.pending_approvals[symbol]
        
        return {"status": "approved", "message": f"Trade {symbol} queued for execution"}
    else:
        logger.info(f"Trade rejected by user: {symbol}")
        del state.pending_approvals[symbol]
        return {"status": "rejected", "message": f"Trade {symbol} rejected"}

@app.post("/api/settings/update")
async def update_settings(update: SettingsUpdate):
    """
    Update system settings
    
    Args:
        update: Settings update (section, key, value)
    """
    try:
        # Update in-memory config
        if update.section in config:
            config[update.section][update.key] = update.value
            
            # Write back to file
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            logger.info(f"Settings updated: {update.section}.{update.key} = {update.value}")
            
            # Publish event
            event_bus.publish('settings_changed', {
                'section': update.section,
                'key': update.key,
                'value': update.value
            })
            
            return {"status": "success", "message": "Settings updated"}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid section: {update.section}")
            
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return config

@app.get("/api/market_data")
async def get_market_data():
    """Get current market data (VIX, SPY, QQQ, etc.)"""
    return state.market_data

@app.post("/api/scan/force")
async def force_scan(background_tasks: BackgroundTasks):
    """Force an immediate scan"""
    if state.is_scanning:
        raise HTTPException(status_code=409, detail="Scan already in progress")
    
    logger.info("Force scan requested by user")
    
    # Trigger scan in background
    background_tasks.add_task(run_scan)
    
    return {"status": "started", "message": "Scan initiated"}

@app.post("/api/system/pause")
async def pause_system():
    """Pause all scanning/trading"""
    config['schedule']['enabled'] = False
    logger.warning("System paused by user")
    return {"status": "paused"}

@app.post("/api/system/resume")
async def resume_system():
    """Resume scanning/trading"""
    config['schedule']['enabled'] = True
    logger.info("System resumed by user")
    return {"status": "resumed"}

# =============================================================================
# BACKGROUND TASKS
# =============================================================================

async def run_scan():
    """Run a full market scan"""
    state.is_scanning = True
    state.last_scan_time = datetime.now()
    
    try:
        # Import here to avoid circular imports
        from backend.scheduler import run_full_scan
        
        signals = await run_full_scan()
        
        # Update state
        state.signals = signals
        
        # Create pending approvals for top signals
        for signal in signals[:40]:  # Top 20 LONG + 20 SHORT
            state.pending_approvals[signal.symbol] = signal
        
        logger.info(f"Scan complete: {len(signals)} signals found")
        
    except Exception as e:
        logger.error(f"Error during scan: {e}")
    finally:
        state.is_scanning = False

# =============================================================================
# STARTUP/SHUTDOWN
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("=" * 70)
    logger.info("🚀 Elite Trading System Backend - STARTING")
    logger.info("=" * 70)
    logger.info(f"Config loaded: {config_path}")
    logger.info(f"Trading style: {config['user_preferences']['trading_style']}")
    logger.info(f"AI trust level: {config['ai_control']['ai_trust_level']}%")
    logger.info("=" * 70)
    
    # Subscribe to events
    event_bus.subscribe('new_signal', on_new_signal)
    event_bus.subscribe('position_opened', on_position_opened)
    event_bus.subscribe('position_closed', on_position_closed)
    
    logger.info("✅ Backend ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Backend shutting down...")
    event_bus.clear()

# =============================================================================
# EVENT HANDLERS
# =============================================================================

def on_new_signal(event):
    """Handle new signal event"""
    signal_data = event['data']
    logger.info(f"New signal: {signal_data['symbol']} (Score: {signal_data['score']})")
    
    # Add to signals list
    signal = Signal(**signal_data)
    state.signals.append(signal)
    state.pending_approvals[signal.symbol] = signal

def on_position_opened(event):
    """Handle position opened event"""
    position_data = event['data']
    logger.info(f"Position opened: {position_data['symbol']}")
    
    # Add to positions list
    position = Position(**position_data)
    state.positions.append(position)

def on_position_closed(event):
    """Handle position closed event"""
    position_data = event['data']
    symbol = position_data['symbol']
    logger.info(f"Position closed: {symbol}")
    
    # Remove from positions
    state.positions = [p for p in state.positions if p.symbol != symbol]

# =============================================================================
# RUN SERVER (if executed directly)
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

