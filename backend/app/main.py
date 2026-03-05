"""FastAPI application entry point.

Enhanced with:
- ML Flywheel Engine initialization (model registry + drift monitor)
- Event-driven MessageBus architecture for <1s signal latency
- Alpaca WebSocket streaming for real-time market data
- EventDrivenSignalEngine reacting to market_data.bar events
- CouncilGate: 14-agent council controls all trading decisions
- OrderExecutor receives council.verdict (not raw signals)
- Bayesian weight learning from trade outcomes
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Load .env into os.environ BEFORE any other imports
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=False)

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.websocket_manager import (
    add_connection,
    remove_connection,
    heartbeat_loop,
    accept_connection,
    handle_pong,
    subscribe,
    unsubscribe,
    broadcast_ws,
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
    youtube_knowledge,
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
    """Initialize ML engine singletons (model registry + drift monitor)."""
    initialized = []
    try:
        from app.modules.ml_engine.model_registry import get_registry
        registry = get_registry()
        initialized.append("ModelRegistry")
        log.info(
            "ML Model Registry initialized: %s",
            registry.get_status() if hasattr(registry, "get_status") else "OK",
        )
    except ImportError:
        log.info("model_registry not available -- skipping")
    except Exception as e:
        log.warning("ModelRegistry init failed: %s", e)

    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        monitor = get_drift_monitor()
        initialized.append("DriftMonitor")
        log.info(
            "ML Drift Monitor initialized: %s",
            monitor.get_status() if hasattr(monitor, "get_status") else "OK",
        )
    except ImportError:
        log.info("drift_detector not available -- skipping")
    except Exception as e:
        log.warning("DriftMonitor init failed: %s", e)

    if initialized:
        log.info("ML Flywheel singletons ready: %s", ", ".join(initialized))
    return initialized


async def _drift_check_loop():
    """Periodic drift check loop -- runs every 60 minutes."""
    await asyncio.sleep(300)
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
                live_df = _get_recent_features()
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
                    log.debug("Drift check skipped -- no recent feature data")
        except ImportError:
            pass
        except Exception:
            log.exception("Drift check loop error")
        await asyncio.sleep(3600)


def _get_recent_features():
    """Pull recent feature rows from DuckDB for drift detection."""
    try:
        from app.data.duckdb_storage import duckdb_store
        df = duckdb_store.query("SELECT * FROM features ORDER BY ts DESC LIMIT 200").fetchdf()
        return df if not df.empty else None
    except Exception as e:
        log.debug("Recent features unavailable: %s", e)
        return None


async def _market_data_tick_loop():
    """Run Market Data Agent tick every 60s when status is 'running'.

    NOTE: This is the legacy polling loop. The new event-driven path via
    MessageBus + AlpacaStreamService provides <1s latency for symbols
    covered by the WebSocket. This loop remains for symbols/data sources
    not yet on the event bus (e.g. Finviz scraping, FRED data).
    """
    await asyncio.sleep(2)
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
    await asyncio.sleep(10)
    while True:
        try:
            from app.api.v1.risk import (
                risk_score,
                drawdown_check_status as drawdown_check,
            )
            from app.websocket_manager import broadcast_ws

            risk_data = await risk_score()
            await broadcast_ws("risk", {"type": "risk_update", "data": risk_data})
            dd_data = await drawdown_check()
            if dd_data.get("drawdown_breached") or not dd_data.get(
                "trading_allowed", True
            ):
                await broadcast_ws("risk", {"type": "drawdown_alert", "data": dd_data})
            await asyncio.sleep(30)
        except Exception as e:
            log.warning("Risk monitor error: %s", e)
            await asyncio.sleep(60)


# ---------------------------------------------------------------------------
# Event-Driven Architecture: MessageBus + Stream + Signal + Council + Order
# ---------------------------------------------------------------------------
_message_bus = None
_alpaca_stream = None
_alpaca_stream_task = None
_event_signal_engine = None
_council_gate = None
_order_executor = None


async def _start_event_driven_pipeline():
    """Initialize and start the event-driven trading pipeline.

    Components (in order):
    1. MessageBus -- async pub/sub event routing
    2. EventDrivenSignalEngine -- market_data.bar -> signal.generated
    3. CouncilGate -- signal.generated -> council evaluation -> council.verdict
    4. OrderExecutor -- council.verdict -> order.submitted (council-controlled)
    5. WebSocket bridges -- forward events to frontend dashboard
    6. AlpacaStreamService -- WebSocket bars -> market_data.bar events
    """
    global _message_bus, _alpaca_stream, _event_signal_engine
    global _council_gate, _order_executor, _alpaca_stream_task

    log.info("=" * 60)
    log.info("\U0001f680 Starting Event-Driven Pipeline (Council-Controlled)")
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

    # 3. CouncilGate (subscribes to signal.generated, invokes council)
    council_gate_enabled = os.getenv("COUNCIL_GATE_ENABLED", "true").lower() == "true"
    if council_gate_enabled:
        from app.council.council_gate import CouncilGate
        _council_gate = CouncilGate(
            message_bus=_message_bus,
            gate_threshold=float(os.getenv("COUNCIL_GATE_THRESHOLD", "65")),
            max_concurrent=int(os.getenv("COUNCIL_MAX_CONCURRENT", "3")),
            cooldown_seconds=int(os.getenv("COUNCIL_COOLDOWN_SECS", "120")),
        )
        await _council_gate.start()
        log.info("\u2705 CouncilGate started (council controls trading)")
    else:
        log.info("\u26a0 CouncilGate DISABLED -- signals go directly to OrderExecutor")

    # 4. OrderExecutor (subscribes to council.verdict)
    from app.services.order_executor import OrderExecutor
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
    log.info(
        "\u2705 OrderExecutor started (%s mode, council-controlled)",
        "AUTO" if auto_execute else "SHADOW",
    )

    # 5. WebSocket bridges (forward events to frontend)
    async def _bridge_signal_to_ws(signal_data):
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("signal", {"type": "new_signal", "signal": signal_data})
        except Exception as e:
            log.debug("WS broadcast failed: %s", e)

    await _message_bus.subscribe("signal.generated", _bridge_signal_to_ws)
    log.info("\u2705 Signal->WebSocket bridge active")

    async def _bridge_order_to_ws(order_data):
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("order", {"type": "order_update", "order": order_data})
        except Exception as e:
            log.debug("WS order broadcast failed: %s", e)

    await _message_bus.subscribe("order.submitted", _bridge_order_to_ws)
    await _message_bus.subscribe("order.filled", _bridge_order_to_ws)
    await _message_bus.subscribe("order.cancelled", _bridge_order_to_ws)
    log.info("\u2705 Order->WebSocket bridges active")

    async def _bridge_council_to_ws(verdict_data):
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("council", {"type": "council_verdict", "verdict": verdict_data})
        except Exception as e:
            log.debug("WS council broadcast failed: %s", e)

    await _message_bus.subscribe("council.verdict", _bridge_council_to_ws)
    log.info("\u2705 Council->WebSocket bridge active")

    # 6. AlpacaStreamService (publishes market_data.bar events)
    if os.getenv("DISABLE_ALPACA_DATA_STREAM", "").strip().lower() in ("1", "true", "yes"):
        log.info("AlpacaStreamService skipped (DISABLE_ALPACA_DATA_STREAM=1)")
    else:
        from app.services.alpaca_stream_service import AlpacaStreamService
        try:
            from app.modules.symbol_universe import get_tracked_symbols
            tracked = get_tracked_symbols()
        except Exception as e:
            log.debug("Symbol universe unavailable, using defaults: %s", e)
            tracked = []
        default_symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
            "TSLA", "META", "SPY", "QQQ", "IWM",
        ]
        symbols = list(set(tracked or default_symbols))
        _alpaca_stream = AlpacaStreamService(_message_bus, symbols)
        _alpaca_stream_task = asyncio.create_task(_alpaca_stream.start())
        log.info("\u2705 AlpacaStreamService launched for %d symbols", len(symbols))

    log.info("=" * 60)
    log.info("\u2705 Event-Driven Pipeline ONLINE (Council-Controlled)")
    log.info("  Stream -> SignalEngine -> CouncilGate -> Council -> OrderExecutor")
    log.info(
        "  Mode: %s | Council: %s | Latency: <1s end-to-end",
        "AUTO-EXECUTE" if auto_execute else "SHADOW",
        "ENABLED" if council_gate_enabled else "DISABLED",
    )
    log.info("=" * 60)


async def _stop_event_driven_pipeline():
    """Graceful shutdown of event-driven components (reverse order)."""
    global _message_bus, _alpaca_stream, _alpaca_stream_task
    global _event_signal_engine, _council_gate, _order_executor
    log.info("Shutting down event-driven pipeline...")

    if _alpaca_stream:
        await _alpaca_stream.stop()
    if _alpaca_stream_task and not _alpaca_stream_task.done():
        _alpaca_stream_task.cancel()
        try:
            await asyncio.wait_for(_alpaca_stream_task, timeout=3.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    if _order_executor:
        await _order_executor.stop()
    if _council_gate:
        await _council_gate.stop()
    if _event_signal_engine:
        await _event_signal_engine.stop()
    if _message_bus:
        await _message_bus.stop()

    await asyncio.sleep(0.25)
    log.info("Event-driven pipeline shutdown complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize data schema on startup; start background loops."""
    # 1. Data schema
    try:
        from app.data.storage import init_schema
        init_schema()
        log.info("SQLite schema initialized")
    except Exception as e:
        log.warning("SQLite schema init skipped: %s", e)

    try:
        from app.data.duckdb_storage import duckdb_store
        health = duckdb_store.health_check()
        log.info(
            "DuckDB ready: %d tables, %d rows",
            health.get("total_tables", 0),
            health.get("total_rows", 0),
        )
    except Exception as e:
        log.warning("DuckDB init skipped: %s", e)

    # 1b. Memory schemas (episodic, semantic, prediction)
    try:
        from app.data.memory_schemas import init_memory_schemas
        init_memory_schemas()
        log.info("Memory schemas initialized (episodic, semantic, prediction)")
    except Exception as e:
        log.debug("Memory schemas init skipped: %s", e)

    # 2. ML Flywheel singletons
    try:
        _init_ml_singletons()
    except Exception as e:
        log.warning("ML singletons init failed: %s", e)

    # 3. Event-driven pipeline (council-controlled)
    try:
        await _start_event_driven_pipeline()
    except Exception:
        log.exception(
            "Event-driven pipeline failed to start -- falling back to polling only"
        )

    # 4. Flywheel scheduler (optional)
    try:
        from app.jobs.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        log.debug("Flywheel scheduler not started: %s", e)

    # 5. trade.resolved → WeightLearner bridge
    try:
        from app.council.weight_learner import get_weight_learner
        from app.core.message_bus import get_message_bus

        _wl_bus = get_message_bus()

        async def _bridge_trade_resolved(resolved_data):
            try:
                learner = get_weight_learner()
                learner.update_from_outcome(
                    symbol=resolved_data.get("symbol", ""),
                    outcome_direction=resolved_data.get("outcome", ""),
                    pnl=resolved_data.get("pnl", 0.0),
                    r_multiple=resolved_data.get("r_multiple", 0.0),
                )
            except Exception as e:
                log.debug("WeightLearner update failed: %s", e)

        await _wl_bus.subscribe("trade.resolved", _bridge_trade_resolved)
        log.info("\u2705 trade.resolved -> WeightLearner bridge active")
    except Exception as e:
        log.debug("WeightLearner bridge not started: %s", e)

    # 5b. HemisphereBridge (PC-1 ↔ PC-2 communication)
    _hemisphere_bridge = None
    try:
        brain_enabled = os.getenv("BRAIN_ENABLED", "false").lower() == "true"
        if brain_enabled:
            from app.core.hemisphere_bridge import get_hemisphere_bridge
            _hemisphere_bridge = get_hemisphere_bridge()
            await _hemisphere_bridge.start()
            log.info("\u2705 HemisphereBridge started (PC-1 ↔ PC-2)")
        else:
            log.info("HemisphereBridge skipped (BRAIN_ENABLED=false)")
    except Exception as e:
        log.debug("HemisphereBridge not started: %s", e)

    # 6. Background tasks (legacy + monitoring)
    tick_task = asyncio.create_task(_market_data_tick_loop())
    drift_task = asyncio.create_task(_drift_check_loop())
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    risk_monitor_task = asyncio.create_task(_risk_monitor_loop())

    log.info("=" * 60)
    log.info("Embodier Trader v4.0.0 ONLINE (Cognitive-1000 Brain)")
    log.info("  API: http://localhost:8000/docs")
    log.info("  Health: http://localhost:8000/health")
    log.info("  WS: ws://localhost:8000/ws")
    log.info("=" * 60)

    try:
        yield
    finally:
        try:
            from app.jobs.scheduler import stop_scheduler
            stop_scheduler()
        except Exception as e:
            log.debug("Scheduler stop failed: %s", e)
        if _hemisphere_bridge:
            try:
                await _hemisphere_bridge.stop()
            except Exception as e:
                log.debug("HemisphereBridge stop failed: %s", e)
        await _stop_event_driven_pipeline()
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
    title=(
        settings.PROJECT_NAME
        if hasattr(settings, "PROJECT_NAME")
        else "Embodier Trader"
    ),
    version="4.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routers ---
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(quotes.router, prefix="/api/v1/quotes", tags=["quotes"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(training.router, prefix="/api/v1/training", tags=["training"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["signals"])
app.include_router(backtest_routes.router, prefix="/api/v1/backtest", tags=["backtest"])
app.include_router(status.router, prefix="/api/v1/status", tags=["status"])
app.include_router(data_sources.router, prefix="/api/v1/data-sources", tags=["data_sources"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["risk"])
app.include_router(strategy.router, prefix="/api/v1/strategy", tags=["strategy"])
app.include_router(performance.router, prefix="/api/v1/performance", tags=["performance"])
app.include_router(flywheel.router, prefix="/api/v1/flywheel", tags=["flywheel"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(patterns.router, prefix="/api/v1/patterns", tags=["patterns"])
app.include_router(openclaw.router, prefix="/api/v1/openclaw", tags=["openclaw"])
app.include_router(ml_brain.router, prefix="/api/v1/ml-brain", tags=["ml_brain"])
app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(sentiment.router, prefix="/api/v1/sentiment", tags=["sentiment"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(settings_routes.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(alpaca.router, prefix="/api/v1/alpaca", tags=["alpaca"])
app.include_router(alignment.router, prefix="/api/v1/alignment", tags=["alignment"])
app.include_router(risk_shield_api.router, prefix="/api/v1/risk-shield", tags=["risk_shield"])
app.include_router(features_routes.router, prefix="/api/v1/features", tags=["features"])
app.include_router(council.router, prefix="/api/v1/council", tags=["council"])
app.include_router(youtube_knowledge.router, prefix="/api/v1/youtube-knowledge", tags=["youtube_knowledge"])
app.include_router(ingestion.router, tags=["ingestion"])


@app.get("/api/v1/consensus", tags=["agents"])
async def consensus_alias():
    """Same as GET /api/v1/agents/consensus."""
    from app.api.v1.agents import get_consensus
    return await get_consensus()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
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
                await broadcast_ws(msg["channel"], msg.get("data", {}))
    except Exception as e:
        log.debug("WebSocket connection error: %s", e)
    finally:
        remove_connection(websocket)


@app.get("/health")
async def health_check():
    """Health check with ML + event pipeline + council + DuckDB status."""
    ml_status = {}
    try:
        from app.modules.ml_engine.model_registry import get_registry
        ml_status["model_registry"] = (
            get_registry().get_status()
            if hasattr(get_registry(), "get_status")
            else "loaded"
        )
    except Exception:
        ml_status["model_registry"] = "unavailable"

    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        ml_status["drift_monitor"] = (
            get_drift_monitor().get_status()
            if hasattr(get_drift_monitor(), "get_status")
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
    if _council_gate:
        event_pipeline["council_gate"] = _council_gate.get_status()
    if _order_executor:
        event_pipeline["order_executor"] = _order_executor.get_status()

    # Agent weights
    agent_weights = {}
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        agent_weights = {
            "weights": learner.get_weights(),
            "update_count": learner.update_count,
        }
    except Exception:
        agent_weights = {"status": "unavailable"}

    # DuckDB status
    duckdb_status = {}
    try:
        from app.data.duckdb_storage import duckdb_store
        duckdb_status = duckdb_store.health_check()
    except Exception:
        duckdb_status = {"status": "unavailable"}

    # LLM Router status
    llm_router_status = {}
    try:
        from app.core.llm_router import get_llm_router
        llm_router_status = get_llm_router().get_status()
    except Exception:
        llm_router_status = {"status": "unavailable"}

    # Hemisphere Bridge status
    hemisphere_status = {}
    try:
        from app.core.hemisphere_bridge import get_hemisphere_bridge
        hemisphere_status = get_hemisphere_bridge().get_status()
    except Exception:
        hemisphere_status = {"status": "unavailable"}

    # Prediction Tracker status
    prediction_status = {}
    try:
        from app.council.prediction_tracker import get_prediction_tracker
        prediction_status = get_prediction_tracker().get_status()
    except Exception:
        prediction_status = {"status": "unavailable"}

    return {
        "status": "healthy",
        "version": "4.0.0",
        "brand": "Embodier Trader",
        "architecture": "cognitive-1000",
        "ml_engine": ml_status,
        "event_pipeline": event_pipeline,
        "agent_weights": agent_weights,
        "duckdb": duckdb_status,
        "llm_router": llm_router_status,
        "hemisphere_bridge": hemisphere_status,
        "prediction_tracker": prediction_status,
    }
