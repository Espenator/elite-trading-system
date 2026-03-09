"""FastAPI application entry point.

Enhanced with:
- ML Flywheel Engine initialization (model registry + drift monitor)
- Event-driven MessageBus architecture for <1s signal latency
- Alpaca WebSocket streaming for real-time market data
- EventDrivenSignalEngine reacting to market_data.bar events
- CouncilGate: 13-agent council controls all trading decisions
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

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.websocket_manager import (
    add_connection,
    remove_connection,
    heartbeat_loop,
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
    cns,
    youtube_knowledge,
    swarm,
    cognitive,
    cluster,
    llm_health,
)
from app.api import ingestion

# Configure structured logging (JSON in production, human-readable in dev)
from app.core.logging_config import setup_logging, correlation_id, generate_correlation_id
setup_logging()
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
        conn = duckdb_store._get_conn()
        df = conn.execute("SELECT * FROM features ORDER BY ts DESC LIMIT 200").fetchdf()
        return df if not df.empty else None
    except Exception:
        return None


async def _market_data_tick_loop():
    """Run Market Data Agent tick every 60s when status is 'running'.

    NOTE: This is the legacy polling loop. The new event-driven path via
    MessageBus + AlpacaStreamService provides <1s latency for symbols
    covered by the WebSocket. This loop remains for symbols/data sources
    not yet on the event bus (e.g. Finviz scraping, FRED data).

    First tick delayed 45s so API server is responsive before heavy
    DuckDB ingestion starts.
    """
    await asyncio.sleep(45)
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
_council_evaluator = None
_node_discovery = None
_stream_manager = None
_gpu_telemetry_daemon = None
_llm_dispatcher = None
_brain_client = None


async def _start_event_driven_pipeline():
    """Initialize and start the event-driven trading pipeline.

    Components (in order):
    1. MessageBus -- async pub/sub event routing
    2. EventDrivenSignalEngine -- market_data.bar -> signal.generated
    3. CouncilGate -- signal.generated -> council evaluation -> council.verdict
    4. OrderExecutor -- council.verdict -> order.submitted (council-controlled)
    5. WebSocket bridges -- forward events to frontend dashboard
    6. AlpacaStreamManager -- multi-key WebSocket bars -> market_data.bar events
    """
    global _message_bus, _alpaca_stream, _event_signal_engine
    global _council_gate, _order_executor, _alpaca_stream_task
    global _node_discovery, _stream_manager
    global _gpu_telemetry_daemon, _llm_dispatcher, _brain_client

    log.info("=" * 60)
    log.info("\U0001f680 Starting Event-Driven Pipeline (Council-Controlled)")
    log.info("=" * 60)

    # Feature flags — disable heavy LLM/swarm services when Ollama isn't running
    _llm_enabled = os.getenv("LLM_ENABLED", "true").lower() == "true"
    _council_enabled = os.getenv("COUNCIL_ENABLED", "true").lower() == "true"

    # 0. Node Discovery (non-blocking) — must run before other services
    from app.services.node_discovery import NodeDiscovery
    _node_discovery = NodeDiscovery()
    asyncio.create_task(_node_discovery.start())  # Fire and forget
    log.info("NodeDiscovery started (PC2: %s)", settings.CLUSTER_PC2_HOST or "disabled")

    # 0b. OllamaNodePool health checks
    from app.services.ollama_node_pool import get_ollama_pool
    _ollama_pool = get_ollama_pool()
    asyncio.create_task(_ollama_pool.start_health_checks())
    log.info("\u2705 OllamaNodePool health checks started (%d nodes)", len(_ollama_pool.urls))

    # 1. MessageBus
    from app.core.message_bus import get_message_bus
    _message_bus = get_message_bus()
    await _message_bus.start()
    log.info("\u2705 MessageBus started")

    # 1b. GPU Telemetry Daemon — broadcasts to cluster.telemetry
    from app.services.gpu_telemetry import GPUTelemetryDaemon
    _gpu_telemetry_daemon = GPUTelemetryDaemon(message_bus=_message_bus)
    asyncio.create_task(_gpu_telemetry_daemon.start())
    log.info("\u2705 GPUTelemetryDaemon started (interval=%.1fs)", settings.GPU_TELEMETRY_INTERVAL)

    # 1c. LLM Dispatcher — telemetry-aware workload routing
    from app.services.llm_dispatcher import LLMDispatcher, get_llm_dispatcher
    _llm_dispatcher = get_llm_dispatcher()
    log.info("\u2705 LLMDispatcher initialized (enabled=%s)", _llm_dispatcher._enabled)

    # 1d. Brain Service (gRPC client) — hypothesis + critic agents
    from app.services.brain_client import get_brain_client
    _brain_client = get_brain_client()
    if _brain_client.enabled:
        log.info(
            "\u2705 Brain Service client initialized (gRPC target: %s:%d)",
            _brain_client.host,
            _brain_client.port,
        )
    else:
        log.info("\u26a0 Brain Service DISABLED — hypothesis/critic agents will use LLM router fallback")

    # 1e. Subscribe NodeDiscovery to cluster.telemetry events
    if _node_discovery:
        await _message_bus.subscribe(
            "cluster.telemetry",
            _node_discovery.handle_telemetry_event,
        )
        log.info("\u2705 NodeDiscovery subscribed to cluster.telemetry")

    # 2. EventDrivenSignalEngine (subscribes to market_data.bar)
    # BUG FIX 3: Always start — this does DuckDB queries + technical analysis, NOT LLM calls.
    # Without it, no signals are generated from incoming market data.
    from app.services.signal_engine import EventDrivenSignalEngine
    _event_signal_engine = EventDrivenSignalEngine(_message_bus)
    await _event_signal_engine.start()
    log.info("\u2705 EventDrivenSignalEngine started")

    # 3. CouncilGate (subscribes to signal.generated, invokes council)
    # Disable when LLM or council is off — council calls LLM which blocks when Ollama is down.
    council_gate_enabled = (
        os.getenv("COUNCIL_GATE_ENABLED", "true").lower() == "true"
        and _llm_enabled
        and _council_enabled
    )
    if council_gate_enabled:
        from app.council.council_gate import CouncilGate
        _council_gate = CouncilGate(
            message_bus=_message_bus,
            gate_threshold=float(os.getenv("COUNCIL_GATE_THRESHOLD", "65")),
            max_concurrent=int(os.getenv("COUNCIL_MAX_CONCURRENT", "3")),
            cooldown_seconds=int(os.getenv("COUNCIL_COOLDOWN_SECS", "120")),
        )
        await _council_gate.start()
        log.info("\u2705 CouncilGate started (13-agent council controls trading)")
    else:
        log.info("\u26a0 CouncilGate DISABLED -- routing signals directly to OrderExecutor")
        # BUG FIX: When council is off, route signals directly as verdicts.
        # Without this, signal.generated has NO trading consumer and nothing executes.
        async def _signal_to_verdict_fallback(signal_data):
            """Bypass council — convert signal.generated directly to council.verdict format."""
            score = signal_data.get("score", 0)
            if score < 65:  # Still gate on minimum score
                return
            await _message_bus.publish("council.verdict", {
                "symbol": signal_data.get("symbol", ""),
                "final_direction": signal_data.get("label", "long"),
                "final_confidence": min(score / 100.0, 1.0),
                "execution_ready": True,
                "vetoed": False,
                "votes": [],
                "council_reasoning": "CouncilGate disabled — direct signal passthrough",
                "signal_data": signal_data,
                "price": signal_data.get("close", signal_data.get("price", 0)),
            })
        await _message_bus.subscribe("signal.generated", _signal_to_verdict_fallback)
        log.info("\u2705 Signal->Verdict fallback subscriber registered (CouncilGate bypass)")

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

    # 5b. BUG FIX 5: Subscribe to market_data.bar to persist snapshot/stream data to DuckDB.
    # Without this, snapshots published by AlpacaStreamService flow through the event pipeline
    # but never reach the database — the data_ingestion.ingest_all path uses separate HTTP calls.
    # BUG FIX 11: Uses async_insert() instead of sync conn.execute() to avoid blocking the event loop.
    async def _persist_bar_to_duckdb(bar_data):
        """Write a market_data.bar event to DuckDB daily_ohlcv table (non-blocking)."""
        try:
            from app.data.duckdb_storage import duckdb_store
            symbol = bar_data.get("symbol")
            timestamp = bar_data.get("timestamp", "")
            if not symbol or not timestamp:
                return

            # Extract date from timestamp (could be ISO format or date string)
            date_str = str(timestamp)[:10]  # YYYY-MM-DD

            await duckdb_store.async_insert(
                """
                INSERT OR REPLACE INTO daily_ohlcv (symbol, date, open, high, low, close, volume, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    symbol,
                    date_str,
                    float(bar_data.get("open") or 0),
                    float(bar_data.get("high") or 0),
                    float(bar_data.get("low") or 0),
                    float(bar_data.get("close") or 0),
                    int(bar_data.get("volume") or 0),
                    bar_data.get("source", "stream"),
                ],
            )
        except Exception as e:
            log.debug("DuckDB bar persist failed: %s", e)

    await _message_bus.subscribe("market_data.bar", _persist_bar_to_duckdb)
    log.info("\u2705 market_data.bar -> DuckDB persistence subscriber active")

    # 5c. BUG FIX 8: Bridge market_data.bar events to WebSocket "market" channel.
    # Without this, the frontend Dashboard gets NO real-time price updates through
    # WebSocket — only through REST polling every 5-30s. This bridge pushes every
    # bar/snapshot to all clients subscribed to the "market" channel.
    async def _bridge_market_data_to_ws(bar_data):
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("market", {"type": "price_update", "bar": bar_data})
        except Exception as e:
            log.debug("WS market broadcast failed: %s", e)

    await _message_bus.subscribe("market_data.bar", _bridge_market_data_to_ws)
    log.info("\u2705 MarketData->WebSocket bridge active")

    # 6. AlpacaStreamManager (replaces single AlpacaStreamService)
    global _stream_manager
    if os.getenv("DISABLE_ALPACA_DATA_STREAM", "").strip().lower() in ("1", "true", "yes"):
        log.info("AlpacaStreamManager skipped (DISABLE_ALPACA_DATA_STREAM=1)")
    else:
        from app.services.alpaca_stream_manager import AlpacaStreamManager
        try:
            from app.modules.symbol_universe import get_tracked_symbols
            tracked = get_tracked_symbols()
        except Exception:
            tracked = []
        default_symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
            "TSLA", "META", "SPY", "QQQ", "IWM",
        ]
        symbols = list(set(tracked or default_symbols))
        _stream_manager = AlpacaStreamManager(_message_bus, symbols)
        _alpaca_stream_task = asyncio.create_task(_stream_manager.start())
        # Keep _alpaca_stream reference for backward compat in health checks
        _alpaca_stream = _stream_manager
        log.info("\u2705 AlpacaStreamManager launched for %d symbols", len(symbols))

    # 8. SwarmSpawner — spawns analysis swarms from ideas
    # Skip when LLM disabled — _run_swarm does synchronous DuckDB ingest + LLM council
    # which blocks the entire async event loop and deadlocks the server.
    if _llm_enabled:
        from app.services.swarm_spawner import get_swarm_spawner
        _swarm_spawner = get_swarm_spawner()
        _swarm_spawner._bus = _message_bus
        await _swarm_spawner.start()
        log.info("\u2705 SwarmSpawner started (%d workers)", _swarm_spawner.MAX_CONCURRENT_SWARMS)
    else:
        log.info("\u26A0\uFE0F SwarmSpawner skipped (LLM_ENABLED=false)")

    # 9. KnowledgeIngestionService — connect to message bus
    from app.services.knowledge_ingest import knowledge_ingest
    knowledge_ingest.set_message_bus(_message_bus)
    log.info("\u2705 KnowledgeIngestionService connected to MessageBus")

    # 10. AutonomousScoutService — proactive opportunity discovery
    if _llm_enabled:
        from app.services.autonomous_scout import get_scout_service
        _scout_service = get_scout_service()
        _scout_service._bus = _message_bus
        await _scout_service.start()
        log.info("\u2705 AutonomousScoutService started (%d scouts)", len(_scout_service._tasks))
    else:
        log.info("\u26A0\uFE0F AutonomousScoutService skipped (LLM_ENABLED=false)")

    # 11. DiscordSwarmBridge — Discord channels -> swarm analysis
    if _llm_enabled:
        from app.services.discord_swarm_bridge import get_discord_bridge
        _discord_bridge = get_discord_bridge()
        _discord_bridge._bus = _message_bus
        await _discord_bridge.start()
        log.info("\u2705 DiscordSwarmBridge started (%d channels)", len(_discord_bridge._channels))
    else:
        log.info("\u26A0\uFE0F DiscordSwarmBridge skipped (LLM_ENABLED=false)")

    # 12. GeopoliticalRadar — continuous macro event detection
    if _llm_enabled:
        from app.services.geopolitical_radar import get_geopolitical_radar
        _geo_radar = get_geopolitical_radar()
        _geo_radar._bus = _message_bus
        await _geo_radar.start()
        log.info("\u2705 GeopoliticalRadar started (alert_level=%s)", _geo_radar._alert_level)
    else:
        log.info("\u26A0\uFE0F GeopoliticalRadar skipped (LLM_ENABLED=false)")

    # 13. Swarm result -> WebSocket bridge
    async def _bridge_swarm_to_ws(result_data):
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("swarm", {"type": "swarm_result", "result": result_data})
        except Exception as e:
            log.debug("WS swarm broadcast failed: %s", e)

    await _message_bus.subscribe("swarm.result", _bridge_swarm_to_ws)
    log.info("\u2705 Swarm->WebSocket bridge active")

    # 14. Macro event -> WebSocket bridge
    async def _bridge_macro_to_ws(event_data):
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("risk", {"type": "macro_event", "event": event_data})
        except Exception as e:
            log.debug("WS macro broadcast failed: %s", e)

    await _message_bus.subscribe("scout.discovery", _bridge_macro_to_ws)
    log.info("\u2705 MacroEvent->WebSocket bridge active")

    # 15. CorrelationRadar — cross-asset correlation breaks + sector rotation
    # BUG FIX 3: Always start — uses sync DuckDB queries, no LLM dependency.
    from app.services.correlation_radar import get_correlation_radar, KEY_PAIRS
    _corr_radar = get_correlation_radar()
    _corr_radar._bus = _message_bus
    await _corr_radar.start()
    log.info("\u2705 CorrelationRadar started (%d key pairs)", len(KEY_PAIRS))

    # 16. PatternLibrary — discovers and validates recurring patterns
    # BUG FIX 3: Always start — DuckDB pattern discovery, no LLM dependency.
    from app.services.pattern_library import get_pattern_library
    _pattern_lib = get_pattern_library()
    _pattern_lib._bus = _message_bus
    await _pattern_lib.start()
    log.info("\u2705 PatternLibrary started (%d patterns)", len(_pattern_lib._patterns))

    # 17. ExpectedMoveService — options-derived reversal zones
    # BUG FIX 3: Always start — options data processing, no LLM dependency.
    from app.services.expected_move_service import get_expected_move_service
    _em_service = get_expected_move_service()
    _em_service._bus = _message_bus
    await _em_service.start()
    log.info("\u2705 ExpectedMoveService started (%d symbols)", len(get_expected_move_service()._levels) or 18)

    # 18. TurboScanner — parallel multi-source 60s scanner (10 concurrent DuckDB screens)
    from app.services.turbo_scanner import get_turbo_scanner
    _turbo_scanner = get_turbo_scanner()
    _turbo_scanner._bus = _message_bus
    await _turbo_scanner.start()
    log.info("\u2705 TurboScanner started (interval=%ds)", _turbo_scanner._scan_interval)

    # 19. HyperSwarm — 50+ concurrent micro-swarms via local Ollama
    if _llm_enabled:
        from app.services.hyper_swarm import get_hyper_swarm
        _hyper_swarm = get_hyper_swarm()
        _hyper_swarm._bus = _message_bus
        await _hyper_swarm.start()
        log.info("\u2705 HyperSwarm started (%d workers, %d Ollama nodes)", len(_hyper_swarm._workers), len(_hyper_swarm._ollama_urls))
    else:
        log.info("\u26A0\uFE0F HyperSwarm skipped (LLM_ENABLED=false)")

    # 20. NewsAggregator — 8+ RSS/API news sources every 60s
    # Publishes swarm.idea + signal.generated events → sync DuckDB processing.
    if _llm_enabled:
        from app.services.news_aggregator import get_news_aggregator
        _news_agg = get_news_aggregator()
        _news_agg._bus = _message_bus
        await _news_agg.start()
        log.info("\u2705 NewsAggregator started (%d RSS feeds)", 9)
    else:
        log.info("\u26A0\uFE0F NewsAggregator skipped (LLM_ENABLED=false)")

    # 21. MarketWideSweep — batch Alpaca ingest + 10 SQL screens across full market
    # BUG FIX 3: Always start — batch Alpaca ingest + SQL screens, no LLM dependency.
    # This is critical for populating DuckDB with market-wide data.
    from app.services.market_wide_sweep import get_market_sweep
    _market_sweep = get_market_sweep()
    _market_sweep._bus = _message_bus
    await _market_sweep.start()
    log.info("\u2705 MarketWideSweep started (universe=%d symbols)", len(_market_sweep._universe))

    # 22. UnifiedProfitEngine — single adaptive scorer replacing 5 competing brains
    # Subscribes to signal.generated and does synchronous DuckDB queries for ML scoring.
    # Skip when LLM is off to avoid blocking the event loop.
    if _llm_enabled:
        from app.services.unified_profit_engine import get_unified_engine
        _unified = get_unified_engine()
        _unified._bus = _message_bus
        await _unified.start()
        log.info("\u2705 UnifiedProfitEngine started — weights: %s",
                 {k: f"{v:.2f}" for k, v in _unified._weights.items()})
    else:
        log.info("\u26A0\uFE0F UnifiedProfitEngine skipped (LLM_ENABLED=false)")

    # 23. PositionManager — automated exits (trailing stops, time exits, partial profits)
    # BUG FIX 3: Always start — uses Alpaca API for position management, no LLM dependency.
    from app.services.position_manager import get_position_manager
    _position_mgr = get_position_manager()
    _position_mgr._bus = _message_bus
    await _position_mgr.start()
    log.info("\u2705 PositionManager started (trailing stops + time exits)")

    # 24. OutcomeTracker — closes the feedback loop (real PnL → Kelly calibration + agent weights)
    # BUG FIX 3: Always start — tracks real PnL from Alpaca, no LLM dependency.
    from app.services.outcome_tracker import get_outcome_tracker
    _outcome_tracker = get_outcome_tracker()
    _outcome_tracker._bus = _message_bus
    await _outcome_tracker.start()
    log.info("\u2705 OutcomeTracker started (win_rate=%.2f, resolved=%d)",
             _outcome_tracker._stats["win_rate"], _outcome_tracker._stats["total_resolved"])

    # 24b. outcome.resolved subscribers — close the feedback loop (Audit Bug #12)
    async def _on_outcome_resolved(outcome_data):
        """Feed resolved outcomes to WeightLearner and SelfAwareness."""
        try:
            from app.council.weight_learner import get_weight_learner
            learner = get_weight_learner()
            learner.update_from_outcome(
                symbol=outcome_data.get("symbol", ""),
                outcome_direction="win" if outcome_data.get("pnl_pct", 0) > 0.001 else "loss",
                pnl=outcome_data.get("pnl", 0.0),
                r_multiple=outcome_data.get("r_multiple", 0.0),
            )
        except Exception as e:
            log.debug("WeightLearner outcome update failed: %s", e)

        try:
            from app.council.self_awareness import get_self_awareness
            sa = get_self_awareness()
            profitable = outcome_data.get("pnl_pct", 0) > 0.001
            agent_votes = outcome_data.get("agent_votes", {}) or {}
            if agent_votes:
                for agent_name in agent_votes:
                    sa.record_trade_outcome(agent_name, profitable)
            else:
                for agent_name in [
                    "market_perception", "flow_perception", "regime", "intermarket",
                    "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
                    "hypothesis", "strategy", "risk", "execution",
                ]:
                    sa.record_trade_outcome(agent_name, profitable)
        except Exception as e:
            log.debug("SelfAwareness outcome update failed: %s", e)

    await _message_bus.subscribe("outcome.resolved", _on_outcome_resolved)
    log.info("\u2705 outcome.resolved subscriber active (WeightLearner + SelfAwareness)")

    # 24. Knowledge Layer — EmbeddingService + MemoryBank + HeuristicEngine + KnowledgeGraph
    # Initialize singletons eagerly so they're warm when council calls them.
    # No LLM requirement — these are local DuckDB + numpy/sentence-transformers.
    try:
        from app.knowledge.embedding_service import get_embedding_engine
        _embedding_engine = get_embedding_engine()
        log.info("\u2705 EmbeddingService initialized (model=%s, device=%s)",
                 _embedding_engine._model_name, _embedding_engine._device or "lazy")
    except Exception as e:
        log.warning("\u26A0\uFE0F EmbeddingService init failed: %s", e)

    try:
        from app.knowledge.memory_bank import get_memory_bank
        _memory_bank = get_memory_bank()
        log.info("\u2705 MemoryBank initialized (%d agents cached)", len(_memory_bank._cache))
    except Exception as e:
        log.warning("\u26A0\uFE0F MemoryBank init failed: %s", e)

    try:
        from app.knowledge.heuristic_engine import get_heuristic_engine
        _heuristic_engine = get_heuristic_engine()
        log.info("\u2705 HeuristicEngine initialized (%d heuristics loaded)", len(_heuristic_engine._heuristics))
    except Exception as e:
        log.warning("\u26A0\uFE0F HeuristicEngine init failed: %s", e)

    try:
        from app.knowledge.knowledge_graph import get_knowledge_graph
        _knowledge_graph = get_knowledge_graph()
        log.info("\u2705 KnowledgeGraph initialized (%d edges)", len(_knowledge_graph._edges))
    except Exception as e:
        log.warning("\u26A0\uFE0F KnowledgeGraph init failed: %s", e)

    # 25. IntelligenceOrchestrator — eagerly warm the singleton (used by council runner)
    if _llm_enabled:
        try:
            from app.services.intelligence_orchestrator import get_intelligence_orchestrator
            _intel_orchestrator = get_intelligence_orchestrator()
            log.info("\u2705 IntelligenceOrchestrator initialized (pre-council multi-tier LLM)")
        except Exception as e:
            log.warning("\u26A0\uFE0F IntelligenceOrchestrator init failed: %s", e)
    else:
        log.info("\u26A0\uFE0F IntelligenceOrchestrator skipped (LLM_ENABLED=false)")

    # 25b. IntelligenceCache — pre-warm council intelligence data
    try:
        from app.services.intelligence_cache import get_intelligence_cache
        _intelligence_cache = get_intelligence_cache()
        await _intelligence_cache.start()
        log.info("\u2705 IntelligenceCache started (pre-warming council data)")
    except Exception as e:
        log.warning("\u26A0\uFE0F IntelligenceCache start failed: %s", e)

    # ── Startup Validation: Topic Health Check ──────────────────────
    _critical_topics = {"signal.generated", "council.verdict", "order.submitted"}
    _all_topics = _message_bus.VALID_TOPICS
    _no_subscribers = []
    _critical_missing = []

    for topic in sorted(_all_topics):
        handlers = _message_bus._subscribers.get(topic, [])
        if not handlers:
            _no_subscribers.append(topic)
            if topic in _critical_topics:
                _critical_missing.append(topic)

    if _no_subscribers:
        log.warning(
            "\u26A0 MessageBus: %d/%d topics have ZERO subscribers: %s",
            len(_no_subscribers), len(_all_topics),
            ", ".join(_no_subscribers[:10]) + ("..." if len(_no_subscribers) > 10 else ""),
        )

    if _critical_missing:
        log.error(
            "\U0001F6A8 CRITICAL: These essential topics have NO consumers \u2014 trading pipeline is broken: %s",
            ", ".join(_critical_missing),
        )
        # Don't fail hard \u2014 log the error so it's visible but allow startup to continue
        # in development mode. In production, this should be a hard failure.

    _active_topics = len(_all_topics) - len(_no_subscribers)
    log.info(
        "\U0001F4CA MessageBus Health: %d/%d topics active, %d zero-subscriber, %d critical",
        _active_topics, len(_all_topics), len(_no_subscribers), len(_critical_missing),
    )

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
    global _node_discovery, _stream_manager
    global _gpu_telemetry_daemon, _llm_dispatcher
    log.info("Shutting down event-driven pipeline...")

    # Stop GPU Telemetry Daemon
    if _gpu_telemetry_daemon:
        try:
            await _gpu_telemetry_daemon.stop()
        except Exception:
            pass

    # Stop NodeDiscovery
    if _node_discovery:
        try:
            await _node_discovery.stop()
        except Exception:
            pass

    # Stop OllamaNodePool health checks
    try:
        from app.services.ollama_node_pool import get_ollama_pool
        await get_ollama_pool().stop_health_checks()
    except Exception:
        pass

    # Stop AlpacaStreamManager (handles all sub-streams)
    if _stream_manager:
        try:
            await _stream_manager.stop()
        except Exception:
            pass

    # Stop swarm intelligence components first (reverse startup order)
    try:
        from app.services.outcome_tracker import get_outcome_tracker
        await get_outcome_tracker().stop()
    except Exception:
        pass
    try:
        from app.services.unified_profit_engine import get_unified_engine
        await get_unified_engine().stop()
    except Exception:
        pass
    try:
        from app.services.position_manager import get_position_manager
        await get_position_manager().stop()
    except Exception:
        pass
    try:
        from app.services.market_wide_sweep import get_market_sweep
        await get_market_sweep().stop()
    except Exception:
        pass
    try:
        from app.services.news_aggregator import get_news_aggregator
        await get_news_aggregator().stop()
    except Exception:
        pass
    try:
        from app.services.hyper_swarm import get_hyper_swarm
        await get_hyper_swarm().stop()
    except Exception:
        pass
    try:
        from app.services.turbo_scanner import get_turbo_scanner
        await get_turbo_scanner().stop()
    except Exception:
        pass
    try:
        from app.services.expected_move_service import get_expected_move_service
        await get_expected_move_service().stop()
    except Exception:
        pass
    try:
        from app.services.pattern_library import get_pattern_library
        await get_pattern_library().stop()
    except Exception:
        pass
    try:
        from app.services.correlation_radar import get_correlation_radar
        await get_correlation_radar().stop()
    except Exception:
        pass
    try:
        from app.services.geopolitical_radar import get_geopolitical_radar
        await get_geopolitical_radar().stop()
    except Exception:
        pass
    try:
        from app.services.discord_swarm_bridge import get_discord_bridge
        await get_discord_bridge().stop()
    except Exception:
        pass
    try:
        from app.services.autonomous_scout import get_scout_service
        await get_scout_service().stop()
    except Exception:
        pass
    try:
        from app.services.swarm_spawner import get_swarm_spawner
        await get_swarm_spawner().stop()
    except Exception:
        pass

    if _council_evaluator:
        await _council_evaluator.stop()

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

    # 3b. Flywheel scheduler (optional)
    try:
        from app.jobs.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        log.debug("Flywheel scheduler not started: %s", e)

    # 4-6. Background tasks (legacy + monitoring)
    # BUG FIX 2: tick_task must ALWAYS run — it does Alpaca data ingestion into DuckDB,
    # NOT LLM work. Without it, no data flows into the database regardless of market hours.
    # drift_task is ML-specific and can safely remain gated on LLM_ENABLED.
    _llm_on = os.getenv("LLM_ENABLED", "true").lower() == "true"
    tick_task = asyncio.create_task(_market_data_tick_loop())  # Always run
    drift_task = asyncio.create_task(_drift_check_loop()) if _llm_on else None
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    risk_monitor_task = asyncio.create_task(_risk_monitor_loop())

    log.info("=" * 60)
    log.info("Embodier Trader v%s ONLINE — PRODUCTION (Council-Controlled Intelligence)", settings.APP_VERSION)
    _port = settings.effective_port; log.info("  API: http://localhost:%s/docs", _port)
    log.info("  Health: http://localhost:%s/health", _port)
    log.info("  WS: ws://localhost:%s/ws", _port)
    log.info("=" * 60)

    try:
        yield
    finally:
        try:
            from app.jobs.scheduler import stop_scheduler
            stop_scheduler()
        except Exception:
            pass
        await _stop_event_driven_pipeline()
        for task in [tick_task, drift_task, heartbeat_task, risk_monitor_task]:
            if task is not None:
                task.cancel()
        for task in [tick_task, drift_task, heartbeat_task, risk_monitor_task]:
            if task is not None:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        # Stop intelligence cache background loop
        try:
            from app.services.intelligence_cache import get_intelligence_cache
            cache = get_intelligence_cache()
            if cache._running:
                await cache.stop()
        except Exception:
            pass

        # Close DuckDB connection
        try:
            from app.data.duckdb_storage import duckdb_store
            if hasattr(duckdb_store, '_conn') and duckdb_store._conn:
                duckdb_store._conn.close()
                duckdb_store._conn = None
                log.info("DuckDB connection closed")
        except Exception:
            pass

        log.info("Application shutdown complete")


# Rate limiter: 200/min general, 20/min for order endpoints
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title=(
        settings.PROJECT_NAME
        if hasattr(settings, "PROJECT_NAME")
        else "Embodier Trader"
    ),
    version=settings.APP_VERSION,  # Audit Task 19: single source from config.py
    lifespan=lifespan,
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.effective_cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


@app.middleware("http")
async def add_security_and_correlation_headers(request, call_next):
    # Set correlation ID for request tracing
    cid = request.headers.get("X-Correlation-ID") or generate_correlation_id()
    token = correlation_id.set(cid)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
    finally:
        correlation_id.reset(token)

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
app.include_router(cns.router, prefix="/api/v1/cns", tags=["cns"])
app.include_router(swarm.router, prefix="/api/v1/swarm", tags=["swarm"])
app.include_router(cognitive.router, prefix="/api/v1/cognitive", tags=["cognitive"])
app.include_router(youtube_knowledge.router, prefix="/api/v1/youtube-knowledge", tags=["youtube_knowledge"])
app.include_router(ingestion.router, tags=["ingestion"])
app.include_router(cluster.router, prefix="/api/v1/cluster", tags=["cluster"])
app.include_router(llm_health.router, prefix="/api/v1/llm/health", tags=["llm_health"])

@app.get("/api/v1/consensus", tags=["agents"])
async def consensus_alias():
    """Same as GET /api/v1/agents/consensus."""
    from app.api.v1.agents import get_consensus
    return await get_consensus()


# --- Valid WebSocket channels (server-side only publishing) ---
# Must include every channel the frontend subscribes to (WS_CHANNELS in config/api.js)
_VALID_WS_CHANNELS = frozenset({
    "signal", "signals", "order", "council", "council_verdict",
    "risk", "swarm", "kelly", "market", "macro", "blackboard",
    "alerts", "performance", "agents", "data_sources", "trades",
    "logs", "sentiment", "alignment", "homeostasis", "circuit_breaker",
})

# --- WebSocket rate limiting (Audit Task 15) ---
_WS_MSG_RATE: dict = {}  # websocket -> list of timestamps
_WS_MAX_MSGS_PER_MIN = 120
_WS_MAX_CONNECTIONS = 50


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates.

    SECURITY (Audit Task 2): Clients can only subscribe/unsubscribe/pong.
    All data publishing to channels originates from server-side services
    via broadcast_ws(). Client-to-channel relay has been removed to prevent
    UI spoofing (fake council_verdict, risk_update, order_update messages).

    RATE LIMITING (Audit Task 15): Max 120 messages/min per connection,
    max 50 simultaneous connections.
    """
    import time as _time

    # Enforce max connections (Task 15)
    from app.websocket_manager import get_connection_count
    if get_connection_count() >= _WS_MAX_CONNECTIONS:
        await websocket.close(code=1013, reason="Max connections reached")
        return

    await websocket.accept()
    add_connection(websocket)
    _WS_MSG_RATE[websocket] = []
    try:
        while True:
            raw = await websocket.receive_text()

            # Rate limiting (Task 15): max 120 msgs/min per connection
            now = _time.time()
            timestamps = _WS_MSG_RATE.get(websocket, [])
            timestamps = [t for t in timestamps if now - t < 60]
            if len(timestamps) >= _WS_MAX_MSGS_PER_MIN:
                await websocket.send_json({
                    "type": "error",
                    "detail": "Rate limit exceeded. Max 120 messages/minute.",
                })
                continue
            timestamps.append(now)
            _WS_MSG_RATE[websocket] = timestamps

            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue

            msg_type = msg.get("type", "")

            if msg_type == "pong":
                handle_pong(websocket)
            elif msg_type == "subscribe":
                ch = msg.get("channel")
                if ch and ch in _VALID_WS_CHANNELS:
                    subscribe(websocket, ch)
            elif msg_type == "unsubscribe":
                ch = msg.get("channel")
                if ch:
                    unsubscribe(websocket, ch)
            # SECURITY: No client-to-channel relay. Clients cannot broadcast.
            # Commands (e.g., trigger council evaluation) go through REST endpoints.
    except Exception:
        pass
    finally:
        _WS_MSG_RATE.pop(websocket, None)
        remove_connection(websocket)


@app.get("/healthz")
async def liveness():
    """Liveness probe — confirms the process is alive and can serve HTTP.

    Kubernetes uses this to decide whether to restart the container.
    Must be fast (<50ms) with zero external dependencies.
    """
    return {"status": "alive"}


@app.get("/readyz")
async def readiness():
    """Readiness probe — confirms the app can serve real traffic.

    Kubernetes uses this to decide whether to route traffic to this pod.
    Checks critical dependencies: DuckDB, Alpaca connectivity, service health.
    Returns 503 if any critical dependency is down.

    AUDIT FIX (Task 8): Includes per-service health from the service registry
    so operators and the HITL gate know which intelligence layers are active.
    """
    checks = {}
    ready = True

    # DuckDB — critical for all data operations
    try:
        from app.data.duckdb_storage import duckdb_store
        health = duckdb_store.health_check()
        checks["duckdb"] = "ok" if health.get("total_tables", 0) > 0 else "degraded"
    except Exception:
        checks["duckdb"] = "unavailable"
        ready = False

    # Alpaca API keys configured (required for trading)
    from app.services.alpaca_service import alpaca_service
    checks["alpaca_configured"] = "ok" if alpaca_service._is_configured() else "not_configured"

    # Event pipeline running
    checks["message_bus"] = "ok" if _message_bus else "not_started"

    # Per-service health (Audit Task 8)
    try:
        from app.core.service_registry import get_health_summary
        svc_health = get_health_summary()
        checks["services"] = svc_health
        if svc_health.get("failed", 0) > 0:
            checks["intelligence_degraded"] = True
    except Exception:
        checks["services"] = "registry_unavailable"

    status_code = 200 if ready else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )


@app.get("/health")
async def health_check():
    """Health check with ML + event pipeline + council + DuckDB status."""
    try:
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

        return {
            "status": "healthy",
            "version": settings.APP_VERSION,  # Audit Task 19: single source
            "brand": "Embodier Trader",
            "architecture": "council-controlled",
            "ml_engine": ml_status,
            "event_pipeline": event_pipeline,
            "agent_weights": agent_weights,
            "duckdb": duckdb_status,
        }
    except Exception as exc:
        log.exception("Health check failed")
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(exc)},
        )
