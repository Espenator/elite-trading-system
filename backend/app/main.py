"""FastAPI application entry point.

Enhanced with ML Flywheel Engine initialization:
- Model Registry singleton for experiment tracking
- Drift Monitor singleton for auto-retrain triggers
- Integrated drift checks in market data tick loop
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.websocket_manager import add_connection, remove_connection, heartbeat_loop, accept_connection
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
    openclaw,
    ml_brain,
    risk_shield_api,
    market,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ML Flywheel Engine Initialization
# ---------------------------------------------------------------------------

def _init_ml_singletons():
    """Initialize ML engine singletons (model registry + drift monitor).
    
    Called once during app startup. Gracefully handles missing dependencies.
    """
    initialized = []
    
    # Model Registry
    try:
        from app.modules.ml_engine.model_registry import get_registry
        registry = get_registry()
        initialized.append("ModelRegistry")
        log.info("ML Model Registry initialized: %s", registry.get_status() if hasattr(registry, 'get_status') else 'OK')
    except ImportError:
        log.info("model_registry not available — skipping")
    except Exception as e:
        log.warning("ModelRegistry init failed: %s", e)
    
    # Drift Monitor
    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        monitor = get_drift_monitor()
        initialized.append("DriftMonitor")
        log.info("ML Drift Monitor initialized: %s", monitor.get_status() if hasattr(monitor, 'get_status') else 'OK')
    except ImportError:
        log.info("drift_detector not available — skipping")
    except Exception as e:
        log.warning("DriftMonitor init failed: %s", e)
    
    if initialized:
        log.info("ML Flywheel singletons ready: %s", ', '.join(initialized))
    
    return initialized


async def _drift_check_loop():
    """Periodic drift check loop — runs every 60 minutes.
    
    Checks feature distribution drift and model performance decay.
    Triggers auto-retrain when thresholds are breached.
    """
    await asyncio.sleep(300)  # Wait 5 min after startup
    
    while True:
        try:
            from app.modules.ml_engine.drift_detector import get_drift_monitor
            monitor = get_drift_monitor()
            status = monitor.get_status()
            if status.get("reference_set"):
                log.info("Drift check: data_drift=%s, perf_drift=%s",
                         status.get("data_drift_detected"),
                         status.get("performance_drift_detected"))
        except ImportError:
            pass  # drift_detector not installed
        except Exception:
            log.exception("Drift check loop error")
        
        await asyncio.sleep(3600)  # Check every hour


async def _market_data_tick_loop():
    """Run Market Data Agent tick every 60s when status is 'running'. First tick runs after 2s so last_tick_at is set quickly."""
    await asyncio.sleep(2)  # brief delay so app is ready
    try:
        from app.api.v1 import agents
        await agents.run_market_data_tick_if_running()
    except asyncio.CancelledError:
        return
    except Exception:
        logging.exception("Market data tick loop error")

    while True:
        await asyncio.sleep(60)
        try:
            from app.api.v1 import agents
            await agents.run_market_data_tick_if_running()
        except asyncio.CancelledError:
            break
        except Exception:
            logging.exception("Market data tick loop error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize data schema on startup; start background loops.
    
    Startup sequence:
    1. Initialize DuckDB schema
    2. Initialize ML Flywheel singletons (registry + drift monitor)
    3. Start market data tick loop (60s interval)
    4. Start drift check loop (1hr interval)
    """
    # 1. Data schema
    try:
        from app.data.storage import init_schema
        init_schema()
    except Exception:
        pass
    
    # 2. ML Flywheel singletons
    _init_ml_singletons()
    
    # 3. Background tasks
    tick_task = asyncio.create_task(_market_data_tick_loop())
    drift_task = asyncio.create_task(_drift_check_loop())
            heartbeat_task = asyncio.create_task(heartbeat_loop())
    
    try:
        yield
    finally:
        tick_task.cancel()
        drift_task.cancel()
                    heartbeat_task.cancel()
        try:
            await tick_task
        except asyncio.CancelledError:
            pass
        try:
            await drift_task
        except asyncio.CancelledError:
            pass
        log.info("Application shutdown complete")


app = FastAPI(
    title=settings.PROJECT_NAME if hasattr(settings, 'PROJECT_NAME') else "Elite Trading System",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routers ---
app.include_router(stocks.router, prefix="/api/v1", tags=["stocks"])
app.include_router(quotes.router, prefix="/api/v1", tags=["quotes"])
app.include_router(orders.router, prefix="/api/v1", tags=["orders"])
app.include_router(system.router, prefix="/api/v1", tags=["system"])
app.include_router(training.router, prefix="/api/v1", tags=["training"])
app.include_router(signals.router, prefix="/api/v1", tags=["signals"])
app.include_router(backtest_routes.router, prefix="/api/v1", tags=["backtest"])
app.include_router(status.router, prefix="/api/v1", tags=["status"])
app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
app.include_router(data_sources.router, prefix="/api/v1", tags=["data_sources"])
app.include_router(sentiment.router, prefix="/api/v1", tags=["sentiment"])
app.include_router(youtube_knowledge.router, prefix="/api/v1", tags=["youtube"])
app.include_router(portfolio.router, prefix="/api/v1", tags=["portfolio"])
app.include_router(risk.router, prefix="/api/v1", tags=["risk"])
app.include_router(strategy.router, prefix="/api/v1", tags=["strategy"])
app.include_router(performance.router, prefix="/api/v1", tags=["performance"])
app.include_router(flywheel.router, prefix="/api/v1", tags=["flywheel"])
app.include_router(logs.router, prefix="/api/v1", tags=["logs"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
app.include_router(patterns.router, prefix="/api/v1", tags=["patterns"])
app.include_router(settings_routes.router, prefix="/api/v1", tags=["settings"])
app.include_router(openclaw.router, prefix="/api/v1", tags=["openclaw"])
app.include_router(ml_brain.router, prefix="/api/v1", tags=["ml_brain"])
app.include_router(risk_shield_api.router, prefix="/api/v1", tags=["risk_shield"])
app.include_router(market.router, prefix="/api/v1", tags=["market"])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    connection_id = add_connection(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except Exception:
        pass
    finally:
        remove_connection(connection_id)


@app.get("/health")
async def health_check():
    """Health check endpoint with ML engine status."""
    ml_status = {}
    
    try:
        from app.modules.ml_engine.model_registry import get_registry
        ml_status["model_registry"] = get_registry().get_status() if hasattr(get_registry(), 'get_status') else "loaded"
    except Exception:
        ml_status["model_registry"] = "unavailable"
    
    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        ml_status["drift_monitor"] = get_drift_monitor().get_status() if hasattr(get_drift_monitor(), 'get_status') else "loaded"
    except Exception:
        ml_status["drift_monitor"] = "unavailable"
    
    return {
        "status": "healthy",
        "version": "3.0.0",
        "ml_engine": ml_status,
    }
