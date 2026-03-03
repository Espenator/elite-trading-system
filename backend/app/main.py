"""FastAPI application entry point.

Enhanced with:
- ML Flywheel Engine initialization (model registry + drift monitor)
- Event-driven MessageBus architecture for <1s signal latency
- Alpaca WebSocket streaming for real-time market data
- EventDrivenSignalEngine reacting to market_data.bar events
- OrderExecutor auto-executing trades from signal.generated events
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.websocket_manager import (
    add_connection, remove_connection, heartbeat_loop, accept_connection,
    handle_pong, subscribe, unsubscribe, broadcast_ws,
)
import json
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
    alpaca,
    alignment,
    features as features_routes,
    council,
)
from app.api import ingestion

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
        log.info("ML Model Registry initialized: %s",
                 registry.get_status() if hasattr(registry, 'get_status') else 'OK')
    except ImportError:
        log.info("model_registry not available -- skipping")
    except Exception as e:
        log.warning("ModelRegistry init failed: %s", e)

    # Drift Monitor
    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        monitor = get_drift_monitor()
        initialized.append("DriftMonitor")
        log.info("ML Drift Monitor initialized: %s",
                 monitor.get_status() if hasattr(monitor, 'get_status') else 'OK')
    except ImportError:
        log.info("drift_detector not available -- skipping")
    except Exception as e:
        log.warning("DriftMonitor init failed: %s", e)

    if initialized:
        log.info("ML Flywheel singletons ready: %s", ', '.join(initialized))

    return initialized


async def _drift_check_loop():
    """Periodic drift check loop -- runs every 60 minutes.

    Pulls recent features from DuckDB, gets accuracy from outcome_resolver,
    and calls check_drift_and_retrain to close the ML flywheel loop.
    """
    await asyncio.sleep(300)  # Wait 5 min after startup

    while True:
        try:
            from app.modules.ml_engine.drift_detector import (
                get_drift_monitor,
                check_drift_and_retrain,
            )
            from app.modules.ml_engine.outcome_resolver import get_flywheel_metrics

            monitor = get_drift_monitor()
            drift_status = monitor.get_status()

            if drift_status.get("reference_set"):
                # Pull live features from DuckDB
                live_df = _get_recent_features()
                # Get current accuracy from outcome_resolver
                metrics = get_flywheel_metrics()
                accuracy = metrics.get("accuracy_30d")

                if live_df is not None and not live_df.empty:
                    result = await check_drift_and_retrain(
                        monitor=monitor,
                        live_df=live_df,
                        current_accuracy=accuracy,
                    )
                    log.info(
                        "Drift check: data_drift=%s, perf_drift=%s, retrain=%s",
                        result.data_drift_detected,
                        result.performance_drift_detected,
                        result.needs_retrain,
                    )
                else:
                    log.debug("Drift check skipped — no recent feature data")
        except ImportError:
            pass  # drift_detector not installed
        except Exception:
            log.exception("Drift check loop error")

        await asyncio.sleep(3600)  # Check every hour


def _get_recent_features():
    """Pull recent feature rows from DuckDB for drift detection."""
    try:
        import pandas as pd
        from app.services.database import db_service
        db = db_service._get_duckdb()
        if db is None:
            return None
        df = db.execute(
            "SELECT * FROM features ORDER BY timestamp DESC LIMIT 200"
        ).fetchdf()
        return df if not df.empty else None
    except Exception:
        return None


async def _market_data_tick_loop():
    """Run Market Data Agent tick every 60s when status is 'running'.

    NOTE: This is the legacy polling loop. The new event-driven path via
    MessageBus + AlpacaStreamService provides <1s latency for symbols
    covered by the WebSocket. This loop remains for symbols/data sources
    not yet on the event bus (e.g. Finviz scraping, FRED data).
    """
    await asyncio.sleep(2)  # brief delay so app is ready
    try:
        from app.api.v1 import agents as _agents_mod
        await _agents_mod.run_market_data_tick_if_running()
    except asyncio.CancelledError:
        return
    except Exception:
        logging.exception("Market data tick loop error")

    while True:
        await asyncio.sleep(60)
        try:
            from app.api.v1 import agents as _agents_mod
            await _agents_mod.run_market_data_tick_if_running()
        except asyncio.CancelledError:
            break
        except Exception:
            logging.exception("Market data tick loop error")


async def _risk_monitor_loop():
    """Risk monitoring background task - polls every 30s."""
    await asyncio.sleep(10)  # Wait for app to stabilize
    while True:
        try:
            from app.api.v1.risk import risk_score, drawdown_check_status as drawdown_check
            from app.websocket_manager import broadcast_ws

            risk_data = await risk_score()
            await broadcast_ws("risk", {"type": "risk_update", "data": risk_data})

            dd_data = await drawdown_check()
            if dd_data.get("drawdown_breached") or not dd_data.get("trading_allowed", True):
                await broadcast_ws("risk", {"type": "drawdown_alert", "data": dd_data})

            await asyncio.sleep(30)
        except Exception as e:
            log.warning("Risk monitor error: %s", e)
            await asyncio.sleep(60)


# ---------------------------------------------------------------------------
# Event-Driven Architecture: MessageBus + Stream + Signal + OrderExecutor
# ---------------------------------------------------------------------------
_message_bus = None
_alpaca_stream = None
_event_signal_engine = None
_order_executor = None


async def _start_event_driven_pipeline():
    """Initialize and start the event-driven trading pipeline.

    Components:
    1. MessageBus — async pub/sub event routing
    2. AlpacaStreamService — WebSocket bars -> market_data.bar events
    3. EventDrivenSignalEngine — market_data.bar -> signal.generated events
    4. OrderExecutor — signal.generated -> order.submitted events
    5. WebSocket bridges — forward events to frontend dashboard
    """
    global _message_bus, _alpaca_stream, _event_signal_engine, _order_executor

    log.info("=" * 60)
    log.info("\U0001f680 Starting Event-Driven Pipeline")
    log.info("=" * 60)

    # 1. MessageBus
    from app.core.message_bus import get_message_bus
    _message_bus = get_message_bus()
    await _message_bus.start()
    log.info("\u2705 MessageBus started")

    # 2. EventDrivenSignalEngine (subscribes to market_data.bar)
    from app.services.signal_engine import EventDrivenSignalEngine
    _event_signal_engine = EventDrivenSignalEngine(_message_bus)
    await _event_signal_engine.start()
    log.info("\u2705 EventDrivenSignalEngine started")

    # 3. OrderExecutor (subscribes to signal.generated)
    from app.services.order_executor import OrderExecutor
    import os

    auto_execute = os.getenv("AUTO_EXECUTE_TRADES", "false").lower() == "true"
    _order_executor = OrderExecutor(
        message_bus=_message_bus,
        auto_execute=auto_execute,
        min_score=float(os.getenv("ORDER_MIN_SCORE", "75")),
        max_daily_trades=int(os.getenv("ORDER_MAX_DAILY", "10")),
        cooldown_seconds=int(os.getenv("ORDER_COOLDOWN_SECS", "300")),
        max_portfolio_heat=float(os.getenv("ORDER_MAX_HEAT", "0.25")),
        max_single_position=float(os.getenv("ORDER_MAX_POSITION", "0.10")),
        use_bracket_orders=os.getenv("ORDER_USE_BRACKETS", "true").lower() == "true",
    )
    await _order_executor.start()
    log.info("\u2705 OrderExecutor started (%s mode)", "AUTO" if auto_execute else "SHADOW")

    # 4. Signal-to-WebSocket bridge (forward signals to frontend)
    async def _bridge_signal_to_ws(signal_data):
        """Forward signal.generated events to frontend via WebSocket."""
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("signal", {
                "type": "new_signal",
                "signal": signal_data,
            })
        except Exception as e:
            log.debug("WS broadcast failed: %s", e)

    await _message_bus.subscribe("signal.generated", _bridge_signal_to_ws)
    log.info("\u2705 Signal->WebSocket bridge active")

    # 5. Order-to-WebSocket bridge (forward order events to frontend)
    async def _bridge_order_to_ws(order_data):
        """Forward order events to frontend via WebSocket."""
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("order", {
                "type": "order_update",
                "order": order_data,
            })
        except Exception as e:
            log.debug("WS order broadcast failed: %s", e)

    await _message_bus.subscribe("order.submitted", _bridge_order_to_ws)
    await _message_bus.subscribe("order.filled", _bridge_order_to_ws)
    await _message_bus.subscribe("order.cancelled", _bridge_order_to_ws)
    log.info("\u2705 Order->WebSocket bridges active")

    # 7. Council verdict-to-WebSocket bridge (forward council decisions to frontend)
    async def _bridge_council_to_ws(verdict_data):
        """Forward council.verdict events to frontend via WebSocket."""
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("council", {
                "type": "council_verdict",
                "verdict": verdict_data,
            })
        except Exception as e:
            log.debug("WS council broadcast failed: %s", e)

    await _message_bus.subscribe("council.verdict", _bridge_council_to_ws)
    log.info("\u2705 Council->WebSocket bridge active")

    # 6. AlpacaStreamService (publishes market_data.bar events)
    from app.services.alpaca_stream_service import AlpacaStreamService

    try:
        from app.modules.symbol_universe import get_tracked_symbols
        tracked = get_tracked_symbols()
    except Exception:
        tracked = []

    default_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "SPY", "QQQ", "IWM"]
    symbols = list(set(tracked or default_symbols))

    _alpaca_stream = AlpacaStreamService(_message_bus, symbols)
    asyncio.create_task(_alpaca_stream.start())
    log.info("\u2705 AlpacaStreamService launched for %d symbols", len(symbols))

    log.info("=" * 60)
    log.info("\u2705 Event-Driven Pipeline ONLINE")
    log.info("   Stream -> MessageBus -> SignalEngine -> OrderExecutor -> Alpaca")
    log.info("   Mode: %s | Latency: <1s end-to-end", "AUTO-EXECUTE" if auto_execute else "SHADOW")
    log.info("=" * 60)


async def _stop_event_driven_pipeline():
    """Graceful shutdown of event-driven components (reverse order)."""
    global _message_bus, _alpaca_stream, _event_signal_engine, _order_executor

    log.info("Shutting down event-driven pipeline...")

    if _alpaca_stream:
        await _alpaca_stream.stop()

    if _order_executor:
        await _order_executor.stop()

    if _event_signal_engine:
        await _event_signal_engine.stop()

    if _message_bus:
        await _message_bus.stop()

    log.info("Event-driven pipeline shutdown complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize data schema on startup; start background loops.

    Startup sequence:
    1. Initialize DuckDB schema
    2. Initialize ML Flywheel singletons (registry + drift monitor)
    3. Start event-driven pipeline (MessageBus + Stream + Signal + OrderExecutor)
    4. Start legacy market data tick loop (for Finviz/FRED polling)
    5. Start drift check loop (1hr interval)
    6. Start risk monitor loop (30s interval)
    """
    # 1. Data schema
    try:
        from app.data.storage import init_schema
        init_schema()
        log.info("SQLite schema initialized")
    except Exception as e:
        log.warning("SQLite schema init skipped: %s", e)

    # 1b. DuckDB schema
    try:
        from app.data.duckdb_storage import duckdb_store
        health = duckdb_store.health_check()
        log.info("DuckDB ready: %d tables, %d rows",
                 health.get("total_tables", 0), health.get("total_rows", 0))
    except Exception as e:
        log.warning("DuckDB init skipped: %s", e)

    # 2. ML Flywheel singletons
    try:
        _init_ml_singletons()
    except Exception as e:
        log.warning("ML singletons init failed: %s", e)

    # 3. Event-driven pipeline (new)
    try:
        await _start_event_driven_pipeline()
    except Exception:
        log.exception("Event-driven pipeline failed to start -- falling back to polling only")

    # 3b. Flywheel scheduler (optional)
    try:
        from app.jobs.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        log.debug("Flywheel scheduler not started: %s", e)

    # 4-6. Background tasks (legacy + monitoring)
    tick_task = asyncio.create_task(_market_data_tick_loop())
    drift_task = asyncio.create_task(_drift_check_loop())
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    risk_monitor_task = asyncio.create_task(_risk_monitor_loop())

    log.info("="*60)
    log.info("Elite Trading System v3.1.0 ONLINE")
    log.info("  API: http://localhost:8000/docs")
    log.info("  Health: http://localhost:8000/health")
    log.info("  WS: ws://localhost:8000/ws")
    log.info("="*60)

    try:
        yield
    finally:
        # Shutdown flywheel scheduler
        try:
            from app.jobs.scheduler import stop_scheduler
            stop_scheduler()
        except Exception:
            pass

        # Shutdown event-driven pipeline
        await _stop_event_driven_pipeline()

        # Cancel legacy tasks
        tick_task.cancel()
        drift_task.cancel()
        heartbeat_task.cancel()
        risk_monitor_task.cancel()
        for task in [tick_task, drift_task, heartbeat_task, risk_monitor_task]:
            try:
                await task
            except asyncio.CancelledError:
                pass
        log.info("Application shutdown complete")


app = FastAPI(
    title=settings.PROJECT_NAME if hasattr(settings, 'PROJECT_NAME') else "Elite Trading System",
    version="3.1.0",
    lifespan=lifespan,
)

# CORS - restricted to local dev origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routers ---
# Each router gets its own sub-path prefix matching frontend API_CONFIG.endpoints.
# Route decorators use relative paths (e.g. @router.get(""), @router.get("/history")).
app.include_router(stocks.router,          prefix="/api/v1/stocks",       tags=["stocks"])
app.include_router(quotes.router,          prefix="/api/v1/quotes",       tags=["quotes"])
app.include_router(orders.router,          prefix="/api/v1/orders",       tags=["orders"])
app.include_router(system.router,          prefix="/api/v1/system",       tags=["system"])
app.include_router(training.router,        prefix="/api/v1/training",     tags=["training"])
app.include_router(signals.router,         prefix="/api/v1/signals",      tags=["signals"])
app.include_router(backtest_routes.router, prefix="/api/v1/backtest",     tags=["backtest"])
app.include_router(status.router,          prefix="/api/v1/status",       tags=["status"])
app.include_router(data_sources.router,    prefix="/api/v1/data-sources", tags=["data_sources"])
app.include_router(portfolio.router,       prefix="/api/v1/portfolio",    tags=["portfolio"])
app.include_router(risk.router,            prefix="/api/v1/risk",         tags=["risk"])
app.include_router(strategy.router,        prefix="/api/v1/strategy",     tags=["strategy"])
app.include_router(performance.router,     prefix="/api/v1/performance",  tags=["performance"])
app.include_router(flywheel.router,        prefix="/api/v1/flywheel",     tags=["flywheel"])
app.include_router(logs.router,            prefix="/api/v1/logs",         tags=["logs"])
app.include_router(patterns.router,        prefix="/api/v1/patterns",     tags=["patterns"])
app.include_router(openclaw.router,        prefix="/api/v1/openclaw",     tags=["openclaw"])
app.include_router(ml_brain.router,        prefix="/api/v1/ml-brain",     tags=["ml_brain"])
app.include_router(market.router,          prefix="/api/v1/market",       tags=["market"])
app.include_router(agents.router,          prefix="/api/v1/agents",       tags=["agents"])
app.include_router(sentiment.router,       prefix="/api/v1/sentiment",    tags=["sentiment"])
app.include_router(alerts.router,          prefix="/api/v1/alerts",       tags=["alerts"])
app.include_router(settings_routes.router, prefix="/api/v1/settings",     tags=["settings"])
app.include_router(alpaca.router,          prefix="/api/v1/alpaca",       tags=["alpaca"])
app.include_router(alignment.router,       prefix="/api/v1/alignment",    tags=["alignment"])
app.include_router(risk_shield_api.router, prefix="/api/v1/risk-shield",  tags=["risk_shield"])

app.include_router(features_routes.router, prefix="/api/v1/features", tags=["features"])
app.include_router(council.router, prefix="/api/v1/council", tags=["council"])

# Data ingestion endpoints (backfill + DuckDB health)
app.include_router(ingestion.router, tags=["ingestion"])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates.

    Handles client messages:
      {"type": "pong"}              - heartbeat response
      {"type": "subscribe", "channel": "..."}   - subscribe to a data channel
      {"type": "unsubscribe", "channel": "..."} - unsubscribe
      {"channel": "...", "data": ...}           - client emit (forwarded)
    """
    await websocket.accept()
    add_connection(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue

            msg_type = msg.get("type", "")

            if msg_type == "pong":
                handle_pong(websocket)
            elif msg_type == "subscribe":
                ch = msg.get("channel")
                if ch:
                    subscribe(websocket, ch)
            elif msg_type == "unsubscribe":
                ch = msg.get("channel")
                if ch:
                    unsubscribe(websocket, ch)
            elif msg.get("channel"):
                # Client-emitted message -- rebroadcast to channel subscribers
                await broadcast_ws(msg["channel"], msg.get("data", {}))
    except Exception:
        pass
    finally:
        remove_connection(websocket)


@app.get("/health")
async def health_check():
    """Health check endpoint with ML engine + event pipeline + DuckDB status."""
    ml_status = {}

    try:
        from app.modules.ml_engine.model_registry import get_registry
        ml_status["model_registry"] = (
            get_registry().get_status()
            if hasattr(get_registry(), 'get_status')
            else "loaded"
        )
    except Exception:
        ml_status["model_registry"] = "unavailable"

    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        ml_status["drift_monitor"] = (
            get_drift_monitor().get_status()
            if hasattr(get_drift_monitor(), 'get_status')
            else "loaded"
        )
    except Exception:
        ml_status["drift_monitor"] = "unavailable"

    # Event pipeline status
    event_pipeline = {}
    if _message_bus:
        event_pipeline["message_bus"] = _message_bus.get_metrics()
    if _alpaca_stream:
        event_pipeline["alpaca_stream"] = _alpaca_stream.get_status()
    if _event_signal_engine:
        event_pipeline["signal_engine"] = _event_signal_engine.get_status()
    if _order_executor:
        event_pipeline["order_executor"] = _order_executor.get_status()

    # DuckDB status
    duckdb_status = {}
    try:
        from app.data.duckdb_storage import duckdb_store
        duckdb_status = duckdb_store.health_check()
    except Exception:
        duckdb_status = {"status": "unavailable"}

    return {
        "status": "healthy",
        "version": "3.1.0",
        "ml_engine": ml_status,
        "event_pipeline": event_pipeline,
        "duckdb": duckdb_status,
    }
