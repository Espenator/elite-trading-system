"""FastAPI application entry point.

Enhanced with:
- ML Flywheel Engine initialization (model registry + drift monitor)
- Event-driven MessageBus architecture for <1s signal latency
- Alpaca WebSocket streaming for real-time market data
- EventDrivenSignalEngine reacting to market_data.bar events
- CouncilGate: 35-agent council controls all trading decisions
- OrderExecutor receives council.verdict (not raw signals)
- Bayesian weight learning from trade outcomes
"""
import asyncio
import concurrent.futures
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path


# Load .env into os.environ BEFORE any other imports
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)

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
from app.core.process_lock import acquire_lock, release_lock
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
    brain,
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
    mobile_api,
    awareness,
    blackboard_routes,
    triage,
    webhooks,
    metrics_api,
    briefing,
    tradingview,
)
from app.api import ingestion
from app.api.v1 import ingestion_firehose

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


async def _supervised_loop(name: str, coro_factory, max_consecutive_failures: int = 3):
    """Supervisor wrapper for background loops (SF9 fix).

    On crash: log error, wait 5s, respawn. After max_consecutive_failures,
    stop retrying and alert.
    """
    consecutive_failures = 0
    while True:
        try:
            await coro_factory()
            consecutive_failures = 0  # Reset on clean exit (shouldn't normally happen)
            return
        except asyncio.CancelledError:
            log.info("Supervised loop '%s' cancelled", name)
            return
        except Exception:
            consecutive_failures += 1
            log.exception(
                "Background loop '%s' crashed (failure %d/%d) — restarting in 5s",
                name, consecutive_failures, max_consecutive_failures,
            )
            if consecutive_failures >= max_consecutive_failures:
                log.critical(
                    "Background loop '%s' failed %d times consecutively — giving up. "
                    "Check logs and restart the server.",
                    name, consecutive_failures,
                )
                # Try to alert via Slack
                try:
                    from app.services.slack_notification_service import get_slack_service
                    slack = get_slack_service()
                    await slack.send_alert(
                        f"CRITICAL: Background loop '{name}' crashed {consecutive_failures}x. Manual restart needed."
                    )
                except Exception:
                    pass
                return
            await asyncio.sleep(5)


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
                live_df = await asyncio.to_thread(_get_recent_features)
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
        conn = duckdb_store.get_thread_cursor()
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
_price_cache = None
_channels_orch = None
_ml_pub = None


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
    global _gpu_telemetry_daemon, _llm_dispatcher

    log.info("=" * 60)
    log.info("\U0001f680 Starting Event-Driven Pipeline (Council-Controlled)")
    log.info("=" * 60)

    # Feature flags — disable heavy LLM/swarm services when Ollama isn't running
    _llm_enabled = os.getenv("LLM_ENABLED", "true").lower() == "true"
    _council_enabled = os.getenv("COUNCIL_ENABLED", "true").lower() == "true"
    log.info("Feature flags: LLM_ENABLED=%s (raw=%r), COUNCIL_ENABLED=%s",
             _llm_enabled, os.getenv("LLM_ENABLED"), _council_enabled)

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

    # 1a. Redis startup health check (PC1: REDIS_URL required for cross-PC MessageBus)
    _redis_url = getattr(settings, "REDIS_URL", "") or os.getenv("REDIS_URL", "")
    if _redis_url:
        try:
            import redis.asyncio as aioredis
            _r = aioredis.from_url(_redis_url.strip(), socket_connect_timeout=3)
            await _r.ping()
            await _r.close()
            log.info("\u2705 Redis OK at %s", _redis_url.split("@")[-1] if "@" in _redis_url else _redis_url)
        except Exception as e:
            if os.getenv("REDIS_REQUIRED", "").lower() in ("1", "true", "yes"):
                log.critical("Redis required but unavailable: %s — set REDIS_REQUIRED=false to allow startup", e)
                raise
            log.warning("Redis unavailable (%s) — MessageBus running local-only. PC2 needs REDIS_URL=redis://192.168.1.105:6379", e)
    else:
        log.info("REDIS_URL not set — MessageBus local-only (set redis://localhost:6379 on PC1 for dual-PC)")

    # 1b. GPU Telemetry Daemon — broadcasts to cluster.telemetry
    from app.services.gpu_telemetry import GPUTelemetryDaemon
    _gpu_telemetry_daemon = GPUTelemetryDaemon(message_bus=_message_bus)
    asyncio.create_task(_gpu_telemetry_daemon.start())
    log.info("\u2705 GPUTelemetryDaemon started (interval=%.1fs)", settings.GPU_TELEMETRY_INTERVAL)

    # 1c. LLM Dispatcher — telemetry-aware workload routing
    from app.services.llm_dispatcher import LLMDispatcher, get_llm_dispatcher
    _llm_dispatcher = get_llm_dispatcher()
    log.info("\u2705 LLMDispatcher initialized (enabled=%s)", _llm_dispatcher._enabled)

    # 1d. Subscribe NodeDiscovery to cluster.telemetry events
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

    # 2b. StreamingDiscoveryEngine — E1: real-time anomaly detection from market bars
    if os.getenv("STREAMING_DISCOVERY_ENABLED", "true").lower() in ("1", "true", "yes"):
        from app.services.streaming_discovery import get_streaming_discovery_engine
        _streaming_discovery = get_streaming_discovery_engine()
        _streaming_discovery._bus = _message_bus
        await _streaming_discovery.start()
        log.info("\u2705 StreamingDiscoveryEngine started (5 detectors, 3-gate emit)")
    else:
        log.info("\u26A0\uFE0F StreamingDiscoveryEngine skipped (STREAMING_DISCOVERY_ENABLED=false)")

    # 2c. IdeaTriageService — E3: dedup, priority scoring, adaptive threshold
    from app.services.idea_triage import get_idea_triage_service
    _idea_triage = get_idea_triage_service()
    _idea_triage._bus = _message_bus
    await _idea_triage.start()
    log.info("\u2705 IdeaTriageService started (base_threshold=40, routes swarm.idea → triage.escalated)")

    # 2c2. DiscoverySignalBridge — triage.escalated → signal.generated so scout discoveries reach council
    from app.services.discovery_signal_bridge import get_discovery_signal_bridge
    _discovery_bridge = get_discovery_signal_bridge()
    _discovery_bridge._bus = _message_bus
    await _discovery_bridge.start()
    log.info("\u2705 DiscoverySignalBridge started (triage.escalated → signal.generated)")

    # 2d. ScoutRegistry — E2: 12 dedicated continuous scout agents.
    # Started here (adjacent to E1/E3) so all three discovery-pipeline stages
    # are live before any downstream consumers (SwarmSpawner, HyperSwarm) start.
    if os.getenv("SCOUTS_ENABLED", "true").lower() in ("1", "true", "yes"):
        from app.services.scouts.registry import get_scout_registry
        _scout_registry = get_scout_registry()
        await _scout_registry.start(message_bus=_message_bus)
        log.info("\u2705 ScoutRegistry started (%d scouts)", _scout_registry.scout_count)
    else:
        log.info("\u26A0\uFE0F ScoutRegistry skipped (SCOUTS_ENABLED=false)")

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
            gate_threshold=float(os.getenv("COUNCIL_GATE_THRESHOLD", "0.65")),
            max_concurrent=int(os.getenv("COUNCIL_MAX_CONCURRENT", "3")),
            cooldown_seconds=int(os.getenv("COUNCIL_COOLDOWN_SECS", "120")),
        )
        await _council_gate.start()
        log.info("\u2705 CouncilGate started (33-agent council controls trading)")
    else:
        log.info("\u26a0 CouncilGate DISABLED -- routing signals directly to OrderExecutor")
        # BUG FIX: When council is off, route signals directly as verdicts.
        # Without this, signal.generated has NO trading consumer and nothing executes.
        async def _signal_to_verdict_fallback(signal_data):
            """Bypass council — convert signal.generated directly to council.verdict format."""
            from app.core.score_semantics import coerce_signal_score_0_100, score_to_final_confidence_0_1
            raw_score = signal_data.get("score", 0)
            score_100 = coerce_signal_score_0_100(raw_score, context="signal_to_verdict_fallback")
            if score_100 < 65.0:  # Gate on minimum score (0-100 scale)
                return
            await _message_bus.publish("council.verdict", {
                "symbol": signal_data.get("symbol", ""),
                "final_direction": signal_data.get("label", "long"),
                "final_confidence": score_to_final_confidence_0_1(score_100, context="signal_to_verdict_fallback"),
                "execution_ready": True,
                "vetoed": False,
                "votes": [],
                "council_reasoning": "CouncilGate disabled — direct signal passthrough",
                "signal_data": signal_data,
                "price": signal_data.get("close", signal_data.get("price", 0)),
            })
        await _message_bus.subscribe("signal.generated", _signal_to_verdict_fallback)
        log.info("\u2705 Signal->Verdict fallback subscriber registered (CouncilGate bypass)")

    # 3.5 Paper/Live safety gate (US8 fix)
    # Validate Alpaca account type matches TRADING_MODE before enabling auto-execute
    auto_execute = os.getenv("AUTO_EXECUTE_TRADES", "false").lower() == "true"
    if auto_execute:
        try:
            from app.services.alpaca_service import alpaca_service
            safety = await alpaca_service.validate_account_safety()
            if not safety.get("valid"):
                log.critical(
                    "SAFETY: Account validation FAILED — forcing SHADOW mode. Warnings: %s",
                    safety.get("warnings", []),
                )
                auto_execute = False  # Force shadow mode on safety failure
            else:
                for w in safety.get("warnings", []):
                    log.warning("Account safety warning: %s", w)
        except Exception as e:
            log.warning("Account safety check failed (non-fatal): %s", e)

    # 4. OrderExecutor (subscribes to council.verdict)
    from app.services.order_executor import OrderExecutor
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
            # Channel "council": symbol, direction, confidence, council_decision_id for frontend (SwarmOverviewTab, etc.)
            await broadcast_ws("council", {
                "type": "council_verdict",
                "symbol": verdict_data.get("symbol"),
                "direction": verdict_data.get("final_direction"),
                "confidence": verdict_data.get("final_confidence"),
                "council_decision_id": verdict_data.get("council_decision_id"),
                "verdict": verdict_data,
            })
            # Channel "council_verdict" so frontend TradeExecution (WS_CHANNELS.council_verdict) receives updates
            await broadcast_ws("council_verdict", {"type": "council_verdict", "verdict": verdict_data})
        except Exception as e:
            log.debug("WS council broadcast failed: %s", e)

    await _message_bus.subscribe("council.verdict", _bridge_council_to_ws)
    log.info("\u2705 Council->WebSocket bridge active")

    # 6. Slack notification bridges (forward critical events to Slack)
    async def _bridge_council_to_slack(verdict_data):
        """Push every council BUY/SELL verdict to Slack (skip HOLD to reduce noise)."""
        try:
            from app.services.slack_notification_service import slack_service
            direction = verdict_data.get("direction", "hold").upper()
            if direction == "HOLD":
                return  # Only alert on actionable decisions
            symbol = verdict_data.get("symbol", "???")
            confidence = verdict_data.get("confidence", 0)
            if isinstance(confidence, (int, float)) and confidence < 1:
                confidence *= 100  # normalize 0-1 to 0-100
            await slack_service.send_council_verdict(symbol, direction, confidence)
        except Exception as e:
            log.debug("Slack council bridge failed: %s", e)

    await _message_bus.subscribe("council.verdict", _bridge_council_to_slack)

    async def _bridge_order_to_slack(order_data):
        """Push order submissions to Slack."""
        try:
            from app.services.slack_notification_service import slack_service
            symbol = order_data.get("symbol", "???")
            side = order_data.get("side", "unknown")
            qty = order_data.get("qty", 0)
            price = order_data.get("price") or order_data.get("limit_price") or 0
            await slack_service.send_trade_execution(symbol, side, qty, float(price))
        except Exception as e:
            log.debug("Slack order bridge failed: %s", e)

    await _message_bus.subscribe("order.submitted", _bridge_order_to_slack)

    async def _bridge_fill_to_slack(fill_data):
        """Push order fills to Slack #executions."""
        try:
            from app.services.slack_notification_service import slack_service
            symbol = fill_data.get("symbol", "???")
            side = fill_data.get("side", "unknown")
            qty = fill_data.get("filled_qty") or fill_data.get("qty", 0)
            price = fill_data.get("filled_avg_price") or fill_data.get("price", 0)
            from app.services.slack_notification_service import CH_EXECUTIONS
            await slack_service._post_message(
                CH_EXECUTIONS,
                f":moneybag: Filled: {side.upper()} {qty}x *{symbol}* @ ${float(price):.2f}",
            )
        except Exception as e:
            log.debug("Slack fill bridge failed: %s", e)

    await _message_bus.subscribe("order.filled", _bridge_fill_to_slack)

    async def _bridge_signal_to_slack(signal_data):
        """Push high-score signals to Slack (score >= 75 only to reduce noise)."""
        try:
            from app.services.slack_notification_service import slack_service
            score = signal_data.get("score", 0)
            if score < 75:
                return  # Only alert on strong signals
            symbol = signal_data.get("symbol", "???")
            direction = signal_data.get("direction", "LONG")
            kelly = signal_data.get("kelly_pct", 0)
            await slack_service.send_signal(symbol, direction, score, kelly)
        except Exception as e:
            log.debug("Slack signal bridge failed: %s", e)

    await _message_bus.subscribe("signal.generated", _bridge_signal_to_slack)

    async def _bridge_alert_to_slack(alert_data):
        """Push system alerts (circuit breakers, agent failures) to Slack."""
        try:
            from app.services.slack_notification_service import slack_service
            message = alert_data.get("message", str(alert_data))
            level = alert_data.get("severity", "INFO")
            await slack_service.send_alert(message, level=level)
        except Exception as e:
            log.debug("Slack alert bridge failed: %s", e)

    for alert_topic in [
        "alert.health", "alert.agent_failure",
        "alert.data_starvation", "alert.council_degraded",
        "alert.websocket_circuit_open",
    ]:
        await _message_bus.subscribe(alert_topic, _bridge_alert_to_slack)

    log.info("\u2705 Slack bridges active (council, orders, fills, signals, alerts)")

    # 5b. BUG FIX 5: Subscribe to market_data.bar to persist snapshot/stream data to DuckDB.
    # Without this, snapshots published by AlpacaStreamService flow through the event pipeline
    # but never reach the database — the data_ingestion.ingest_all path uses separate HTTP calls.
    # BUG FIX 11: Uses async_insert() instead of sync conn.execute() to avoid blocking the event loop.
    # PERF FIX: Batch writes every 5 seconds instead of per-bar to reduce DuckDB lock contention
    # and thread pool usage (~8 writes/sec → 1 batch write every 5s).
    _bar_write_buffer: list = []
    _bar_buffer_lock = asyncio.Lock()

    async def _persist_bar_to_duckdb(bar_data):
        """Buffer a market_data.bar event for batched DuckDB write."""
        symbol = bar_data.get("symbol")
        timestamp = bar_data.get("timestamp", "")
        if not symbol or not timestamp:
            return
        date_str = str(timestamp)[:10]
        row = (
            symbol,
            date_str,
            float(bar_data.get("open") or 0),
            float(bar_data.get("high") or 0),
            float(bar_data.get("low") or 0),
            float(bar_data.get("close") or 0),
            int(bar_data.get("volume") or 0),
            bar_data.get("source", "stream"),
        )
        async with _bar_buffer_lock:
            _bar_write_buffer.append(row)

    async def _flush_bar_buffer():
        """Flush buffered bars to DuckDB (interval from BAR_BUFFER_FLUSH_SEC)."""
        from app.data.duckdb_storage import duckdb_store
        from app.core.config import settings
        flush_sec = getattr(settings, "BAR_BUFFER_FLUSH_SEC", 5.0)
        while True:
            await asyncio.sleep(flush_sec)
            async with _bar_buffer_lock:
                if not _bar_write_buffer:
                    continue
                batch = list(_bar_write_buffer)
                _bar_write_buffer.clear()
            try:
                # Deduplicate by (symbol, date) — keep latest bar per symbol per day
                seen = {}
                for row in batch:
                    seen[(row[0], row[1])] = row
                deduped = list(seen.values())

                def _batch_insert():
                    conn = duckdb_store._get_conn()
                    with duckdb_store._lock:
                        for row in deduped:
                            conn.execute(
                                "INSERT OR REPLACE INTO daily_ohlcv "
                                "(symbol, date, open, high, low, close, volume, source) "
                                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                list(row),
                            )

                await asyncio.to_thread(_batch_insert)
                log.debug("Flushed %d bars to DuckDB (%d unique)", len(batch), len(deduped))
            except Exception as e:
                log.debug("DuckDB bar batch persist failed: %s", e)

    await _message_bus.subscribe("market_data.bar", _persist_bar_to_duckdb)
    asyncio.create_task(_flush_bar_buffer())
    try:
        from app.core.config import settings as _bar_settings
        _bar_flush_sec = getattr(_bar_settings, "BAR_BUFFER_FLUSH_SEC", 5.0)
    except Exception:
        _bar_flush_sec = 5.0
    log.info("\u2705 market_data.bar -> DuckDB batched persistence active (%.1fs flush)", _bar_flush_sec)

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

    # -- WS bridges for swarm/macro (register immediately, services start deferred) --
    async def _bridge_swarm_to_ws(result_data):
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("swarm", {"type": "swarm_result", "result": result_data})
        except Exception as e:
            log.debug("WS swarm broadcast failed: %s", e)

    await _message_bus.subscribe("swarm.result", _bridge_swarm_to_ws)

    async def _bridge_swarm_idea_to_ws(idea_data):
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("swarm", {"type": "swarm_idea", "idea": idea_data})
        except Exception as e:
            log.debug("WS swarm.idea broadcast failed: %s", e)

    await _message_bus.subscribe("swarm.idea", _bridge_swarm_idea_to_ws)

    async def _bridge_macro_to_ws(event_data):
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("risk", {"type": "macro_event", "event": event_data})
        except Exception as e:
            log.debug("WS macro broadcast failed: %s", e)

    await _message_bus.subscribe("scout.discovery", _bridge_macro_to_ws)
    log.info("\u2705 Swarm/Macro->WebSocket bridges registered")

    # -- Lightweight services (DuckDB-only, no LLM) -- start immediately --

    # 15. CorrelationRadar
    from app.services.correlation_radar import get_correlation_radar, KEY_PAIRS
    _corr_radar = get_correlation_radar()
    _corr_radar._bus = _message_bus
    await _corr_radar.start()
    log.info("\u2705 CorrelationRadar started (%d key pairs)", len(KEY_PAIRS))

    # 16. PatternLibrary
    from app.services.pattern_library import get_pattern_library
    _pattern_lib = get_pattern_library()
    _pattern_lib._bus = _message_bus
    await _pattern_lib.start()
    log.info("\u2705 PatternLibrary started (%d patterns)", len(_pattern_lib._patterns))

    # 17. ExpectedMoveService
    from app.services.expected_move_service import get_expected_move_service
    _em_service = get_expected_move_service()
    _em_service._bus = _message_bus
    await _em_service.start()
    log.info("\u2705 ExpectedMoveService started (%d symbols)", len(get_expected_move_service()._levels) or 18)

    # 9. KnowledgeIngestionService
    from app.services.knowledge_ingest import knowledge_ingest
    knowledge_ingest.set_message_bus(_message_bus)
    log.info("\u2705 KnowledgeIngestionService connected to MessageBus")

    # 18. OffHoursMonitor (gap detection, data freshness, session-aware quality)
    try:
        from app.services.off_hours_monitor import get_off_hours_monitor
        _off_hours = get_off_hours_monitor(message_bus=_message_bus)
        await _off_hours.start()
        log.info("\u2705 OffHoursMonitor started (session=%s)", _off_hours._detect_session())
    except Exception as e:
        log.warning("OffHoursMonitor failed to start: %s", e)

    # 19. DataSourceHealthAggregator (unified health + Slack alerts)
    try:
        from app.services.data_source_health_aggregator import get_health_aggregator
        _health_agg = get_health_aggregator(message_bus=_message_bus)
        await _health_agg.start()
        log.info("\u2705 DataSourceHealthAggregator started")
    except Exception as e:
        log.warning("DataSourceHealthAggregator failed to start: %s", e)

    # -- DEFERRED HEAVY SERVICES -----------------------------------------------
    # These services are LLM-heavy, do bulk HTTP fetches, or process thousands
    # of symbols. Starting them immediately saturates the asyncio event loop
    # and makes the HTTP server unresponsive for 30-60s after startup.
    # Solution: launch them in a background task after a delay so the API
    # server is fully ready to serve health checks and council evaluations.
    _deferred_startup_delay = int(os.getenv("DEFERRED_STARTUP_DELAY", "15"))

    async def _start_deferred_services():
        """Start heavy background services after the API server is ready."""
        await asyncio.sleep(_deferred_startup_delay)
        log.info("Starting deferred heavy services (after %ds delay)...", _deferred_startup_delay)

        # 8. SwarmSpawner
        if _llm_enabled:
            try:
                from app.services.swarm_spawner import get_swarm_spawner
                _swarm_spawner = get_swarm_spawner()
                _swarm_spawner._bus = _message_bus
                await _swarm_spawner.start()
                log.info("\u2705 SwarmSpawner started (%d workers)", _swarm_spawner.MAX_CONCURRENT_SWARMS)
            except Exception as e:
                log.warning("SwarmSpawner failed to start: %s", e)

        await asyncio.sleep(2)  # Yield to event loop between heavy services

        # 10. AutonomousScoutService
        if _llm_enabled:
            try:
                from app.services.autonomous_scout import get_scout_service
                _scout_service = get_scout_service()
                _scout_service._bus = _message_bus
                await _scout_service.start()
                log.info("\u2705 AutonomousScoutService started (%d scouts)", len(_scout_service._tasks))
            except Exception as e:
                log.warning("AutonomousScoutService failed to start: %s", e)

        # 11. DiscordSwarmBridge
        if _llm_enabled:
            try:
                from app.services.discord_swarm_bridge import get_discord_bridge
                _discord_bridge = get_discord_bridge()
                _discord_bridge._bus = _message_bus
                await _discord_bridge.start()
                log.info("\u2705 DiscordSwarmBridge started (%d channels)", len(_discord_bridge._channels))
            except Exception as e:
                log.warning("DiscordSwarmBridge failed to start: %s", e)

        # 20. Data swarm (24/7 collectors: Alpaca, UW, FinViz) — opt-in via DATA_SWARM_ENABLED=true
        if os.getenv("DATA_SWARM_ENABLED", "").lower() in ("1", "true", "yes"):
            try:
                from app.services.data_swarm import get_swarm_orchestrator
                _data_swarm = get_swarm_orchestrator()
                asyncio.create_task(_data_swarm.run())
                log.info("\u2705 Data swarm orchestrator started (session-aware collectors)")
            except Exception as e:
                log.warning("Data swarm orchestrator failed to start: %s", e)

        await asyncio.sleep(2)

        # 12. GeopoliticalRadar
        if _llm_enabled:
            try:
                from app.services.geopolitical_radar import get_geopolitical_radar
                _geo_radar = get_geopolitical_radar()
                _geo_radar._bus = _message_bus
                await _geo_radar.start()
                log.info("\u2705 GeopoliticalRadar started (alert_level=%s)", _geo_radar._alert_level)
            except Exception as e:
                log.warning("GeopoliticalRadar failed to start: %s", e)

        await asyncio.sleep(2)

        # 18. TurboScanner
        if os.getenv("TURBO_SCANNER_ENABLED", "true").lower() in ("1", "true", "yes"):
            try:
                from app.services.turbo_scanner import get_turbo_scanner
                _turbo_scanner = get_turbo_scanner()
                _turbo_scanner._bus = _message_bus
                await _turbo_scanner.start()
                log.info("\u2705 TurboScanner started (interval=%ds)", _turbo_scanner._scan_interval)
            except Exception as e:
                log.warning("TurboScanner failed to start: %s", e)

        await asyncio.sleep(2)

        # 19. HyperSwarm
        if _llm_enabled:
            try:
                from app.services.hyper_swarm import get_hyper_swarm
                _hyper_swarm = get_hyper_swarm()
                _hyper_swarm._bus = _message_bus
                await _hyper_swarm.start()
                log.info("\u2705 HyperSwarm started (%d workers, %d Ollama nodes)", len(_hyper_swarm._workers), len(_hyper_swarm._ollama_urls))
            except Exception as e:
                log.warning("HyperSwarm failed to start: %s", e)

        await asyncio.sleep(2)

        # 20. NewsAggregator
        if _llm_enabled:
            try:
                from app.services.news_aggregator import get_news_aggregator
                _news_agg = get_news_aggregator()
                _news_agg._bus = _message_bus
                await _news_agg.start()
                log.info("\u2705 NewsAggregator started (%d RSS feeds)", 9)
            except Exception as e:
                log.warning("NewsAggregator failed to start: %s", e)

        await asyncio.sleep(3)

        # 21. MarketWideSweep
        if os.getenv("MARKET_SWEEP_ENABLED", "true").lower() in ("1", "true", "yes"):
            try:
                from app.services.market_wide_sweep import get_market_sweep
                _market_sweep = get_market_sweep()
                _market_sweep._bus = _message_bus
                await _market_sweep.start()
                log.info("\u2705 MarketWideSweep started (universe=%d symbols)", len(_market_sweep._universe))
            except Exception as e:
                log.warning("MarketWideSweep failed to start: %s", e)

        await asyncio.sleep(3)

        # D1: Autonomous data backfill (startup + daily scheduler)
        if os.getenv("STARTUP_BACKFILL_ENABLED", "true").lower() in ("1", "true", "yes"):
            async def _run_backfill():
                try:
                    from app.services.data_ingestion import data_ingestion
                    log.info("Starting startup data backfill (252 days) in background...")
                    report = await data_ingestion.run_startup_backfill(days=252)
                    log.info(
                        "\u2705 Startup backfill complete: %d symbols, %.1fs",
                        report.get("symbol_count", 0),
                        report.get("elapsed_seconds", 0),
                    )
                    asyncio.create_task(
                        _supervised_loop("data_ingestion_scheduler", data_ingestion.scheduler_loop)
                    )
                    log.info("\u2705 DataIngestion scheduler started (daily 4:30AM + weekly Sunday)")
                except Exception as e:
                    log.warning("Data backfill/scheduler failed to start: %s", e)
            asyncio.create_task(_run_backfill())
        else:
            log.info("\u26a0\ufe0f Startup backfill skipped (STARTUP_BACKFILL_ENABLED=false)")

        await asyncio.sleep(2)

        # D5: Session Scanner (pre-market gaps + after-hours earnings)
        try:
            from app.services.session_scanner import get_session_scanner
            _session_scanner = get_session_scanner()
            await _session_scanner.start(message_bus=_message_bus)
            log.info(
                "\u2705 SessionScanner started (session=%s)",
                _session_scanner._detect_session(),
            )
        except Exception as e:
            log.warning("SessionScanner failed to start: %s", e)

        log.info("\u2705 All deferred heavy services started")

    asyncio.create_task(_start_deferred_services())

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

    # 24b. outcome.resolved subscribers — single path: OutcomeTracker already updates
    #      WeightLearner + SelfAwareness streaks before publishing. No duplicate updates
    #      (dopamine loop fix: one source of truth, no double-counting).
    async def _on_outcome_resolved(outcome_data):
        """OutcomeTracker is the single path for weight/streak updates. Subscriber reserved for other side effects."""
        pass

    await _message_bus.subscribe("outcome.resolved", _on_outcome_resolved)
    log.info("\u2705 outcome.resolved subscriber active (weights/streaks updated by OutcomeTracker only)")

    # 24c. PriceCacheService — caches last price per symbol from market_data.bar/quote
    global _price_cache, _channels_orch, _ml_pub
    from app.services.price_cache_service import PriceCacheService
    _price_cache = PriceCacheService(message_bus=_message_bus)
    await _price_cache.start()
    log.info("\u2705 PriceCacheService started")

    # 24d. ChannelsOrchestrator — firehose data ingestion agents
    if os.getenv("CHANNELS_FIREHOSE_ENABLED", "true").lower() in ("1", "true", "yes"):
        from app.services.channels.orchestrator import ChannelsOrchestrator
        _channels_orch = ChannelsOrchestrator(message_bus=_message_bus)
        await _channels_orch.start()
        log.info("\u2705 ChannelsOrchestrator started (%d agents)", len(_channels_orch._agents))
    else:
        log.info("\u26A0\uFE0F ChannelsOrchestrator skipped (CHANNELS_FIREHOSE_ENABLED=false)")

    # 24e. MLSignalPublisher — publishes ML scores to signal.generated
    try:
        from app.services.ml_signal_publisher import get_ml_signal_publisher
        _ml_pub = get_ml_signal_publisher(_message_bus)
        _ml_pub._bus = _message_bus
        await _ml_pub.start()
        log.info("\u2705 MLSignalPublisher started")
    except Exception as e:
        log.warning("MLSignalPublisher start failed: %s", e)

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

    # Phase C (I1): Activate SelfAwareness Bayesian tracking at startup
    try:
        from app.council.self_awareness import get_self_awareness
        _self_awareness = get_self_awareness()
        log.info(
            "\u2705 SelfAwareness initialized (agents tracked: %d)",
            len(_self_awareness.weights._weights),
        )
    except Exception as e:
        log.warning("\u26A0\uFE0F SelfAwareness init failed: %s", e)

    # Phase C (I1): Wire SelfAwareness weights as additional signal to WeightLearner
    try:
        from app.council.weight_learner import get_weight_learner
        _wl = get_weight_learner()
        _sa_weights = _self_awareness.weights.get_all_weights()
        if _sa_weights:
            log.info(
                "\u2705 SelfAwareness → WeightLearner bridge active (%d agent weights)",
                len(_sa_weights),
            )
    except Exception as e:
        log.debug("SelfAwareness → WeightLearner bridge skipped: %s", e)

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
    global _price_cache, _channels_orch, _ml_pub
    log.info("Shutting down event-driven pipeline...")

    if _ml_pub:
        try:
            await _ml_pub.stop()
        except Exception:
            pass
    if _channels_orch:
        try:
            await _channels_orch.stop()
        except Exception:
            pass
    if _price_cache:
        try:
            await _price_cache.stop()
        except Exception:
            pass

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
    # Stop E2 publishers (scouts) before E3 processor (triage) so in-flight
    # swarm.idea events aren't dispatched to an already-stopped triage service.
    try:
        from app.services.scouts.registry import get_scout_registry
        await get_scout_registry().stop()
    except Exception:
        pass
    # Stop E1 publisher before E3 processor for the same reason.
    try:
        from app.services.streaming_discovery import get_streaming_discovery_engine
        await get_streaming_discovery_engine().stop()
    except Exception:
        pass
    try:
        from app.services.discovery_signal_bridge import get_discovery_signal_bridge
        await get_discovery_signal_bridge().stop()
    except Exception:
        pass
    try:
        from app.services.idea_triage import get_idea_triage_service
        await get_idea_triage_service().stop()
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


# Readiness state: set during lifespan so /readyz and /api/v1/status/ready can return 200 only when ready.
# Launcher should poll: GET /readyz or GET /api/v1/status/ready until 200 before starting frontend.
READINESS_DUCKDB_KEY = "duckdb_ready"
READINESS_MESSAGEBUS_KEY = "message_bus_ready"
DUCKDB_INIT_ATTEMPTS = 3
DUCKDB_INIT_DELAY_SEC = 2.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize data schema on startup; start background loops.

    6-phase lifespan: (0) thread pool, (0b) infra checks, (1) DB schema + DuckDB with retry,
    (1b) ingestion, (2) ML singletons, (3) event pipeline. If a critical phase fails,
    we log clearly and fail fast (or retry for DuckDB) so the app does not yield in a broken state.
    """
    app.state.duckdb_ready = False
    app.state.message_bus_ready = False
    _lock_acquired = False

    # Process guard: block duplicate backend instances before DuckDB init.
    if not acquire_lock():
        os._exit(3)
    _lock_acquired = True

    # Phase 0: Thread pool for concurrent DuckDB/blocking work (tunable via ASYNCIO_THREAD_POOL_WORKERS)
    from app.core.config import settings
    _pool_size = getattr(settings, "ASYNCIO_THREAD_POOL_WORKERS", 64)
    loop = asyncio.get_running_loop()
    loop.set_default_executor(concurrent.futures.ThreadPoolExecutor(max_workers=_pool_size))
    log.info("Thread pool set to %d workers for async DuckDB operations", _pool_size)

    # Phase 0b: Infrastructure health checks (PC2 + Redis) — non-fatal
    _infra_status = {}
    try:
        from app.core.pc2_health import run_infrastructure_checks
        _infra_status = await run_infrastructure_checks()
        app.state.infra_status = _infra_status
    except Exception as e:
        log.warning("Infrastructure health checks failed: %s", e)
        app.state.infra_status = {"dual_pc_operational": False}

    # Phase 1a: SQLite schema (non-fatal)
    try:
        from app.data.storage import init_schema
        init_schema()
        log.info("SQLite schema initialized")
    except Exception as e:
        log.warning("SQLite schema init skipped: %s", e)

    # Phase 1b: DuckDB schema with retry (3 attempts, 2s apart) — fail fast if still locked/unavailable
    from app.data.duckdb_storage import duckdb_store
    _duckdb_ok = False
    _last_duckdb_error = None
    for attempt in range(1, DUCKDB_INIT_ATTEMPTS + 1):
        try:
            duckdb_store.init_schema()
            health = duckdb_store.health_check()
            _duckdb_ok = True
            log.info(
                "DuckDB ready: %d tables, %d rows (attempt %d/%d)",
                health.get("total_tables", 0),
                health.get("total_rows", 0),
                attempt,
                DUCKDB_INIT_ATTEMPTS,
            )
            break
        except Exception as e:
            _last_duckdb_error = e
            err_msg = str(e).lower()
            is_lock = (
                "already open" in err_msg
                or "file is already open" in err_msg
                or "being used by another process" in err_msg
                or "locked" in err_msg
                or "cannot open" in err_msg
            )
            log.warning(
                "DuckDB init attempt %d/%d failed: %s",
                attempt, DUCKDB_INIT_ATTEMPTS, e,
            )
            if attempt < DUCKDB_INIT_ATTEMPTS:
                log.info("Retrying DuckDB init in %.1fs...", DUCKDB_INIT_DELAY_SEC)
                await asyncio.sleep(DUCKDB_INIT_DELAY_SEC)
            else:
                if is_lock:
                    log.critical(
                        "DuckDB init failed after %d attempts (file locked by another process). "
                        "Only one backend instance per data directory. Exiting.",
                        DUCKDB_INIT_ATTEMPTS,
                    )
                    os._exit(2)  # EXIT_DUPLICATE_INSTANCE
                raise RuntimeError(
                    f"DuckDB init failed after {DUCKDB_INIT_ATTEMPTS} attempts: {_last_duckdb_error}"
                ) from _last_duckdb_error
    if _duckdb_ok:
        app.state.duckdb_ready = True

    # 1b. Ingestion framework (incremental adapters)
    try:
        from app.data.checkpoint_store import CheckpointStore
        from app.services.ingestion.registry import AdapterRegistry
        from app.services.ingestion.scheduler import IngestionScheduler
        from app.core.message_bus import get_message_bus

        checkpoint_store = CheckpointStore()
        message_bus = get_message_bus()
        adapter_registry = AdapterRegistry(checkpoint_store, message_bus)
        adapter_registry.initialize_adapters()

        ingestion_scheduler = IngestionScheduler(adapter_registry)
        ingestion_scheduler.schedule_all_adapters()
        ingestion_scheduler.start()

        log.info("Ingestion framework initialized: %d adapters scheduled",
                len(adapter_registry.get_all_adapters()))
    except Exception as e:
        log.warning("Ingestion framework init failed: %s", e)

    # 2. ML Flywheel singletons
    try:
        _init_ml_singletons()
    except Exception as e:
        log.warning("ML singletons init failed: %s", e)

    # Phase 3: Event-driven pipeline (council-controlled) — fail fast so app is not left broken
    try:
        await _start_event_driven_pipeline()
        app.state.message_bus_ready = True
    except Exception:
        log.exception(
            "Event-driven pipeline failed to start — backend cannot serve traffic. Failing fast."
        )
        raise

    # 3b. Flywheel scheduler (optional)
    try:
        from app.jobs.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        log.debug("Flywheel scheduler not started: %s", e)

    # 3c. Auto-backfill if DuckDB has 0 indicator/feature rows (first-run bootstrap)
    _auto_backfill_enabled = os.getenv("AUTO_BACKFILL", "true").lower() in ("1", "true", "yes")
    if not _auto_backfill_enabled:
        log.info("\u26A0\uFE0F Auto-backfill skipped (AUTO_BACKFILL=false)")
    if _auto_backfill_enabled:
        try:
            from app.data.duckdb_storage import duckdb_store
            _health = duckdb_store.health_check()
            _ohlcv_rows = 0
            _indicator_rows = 0
            for t in (_health.get("tables") or []):
                if t.get("name") == "daily_ohlcv":
                    _ohlcv_rows += t.get("rows", 0)
                if t.get("name") in ("daily_indicators", "daily_features"):
                    _indicator_rows += t.get("rows", 0)
            if _ohlcv_rows == 0 or _indicator_rows == 0:
                log.info(
                    "DuckDB data starvation detected (ohlcv=%d, indicators=%d) — scheduling auto-backfill",
                    _ohlcv_rows, _indicator_rows,
                )

                async def _auto_backfill():
                    await asyncio.sleep(30)  # Let API server start first
                    try:
                        from app.services.data_ingestion import data_ingestion
                        from app.modules.symbol_universe import get_tracked_symbols
                        symbols = get_tracked_symbols()[:20] or [
                            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
                            "TSLA", "META", "SPY", "QQQ", "IWM",
                        ]
                        log.info("Auto-backfill starting for %d symbols (30 days)...", len(symbols))
                        report = await data_ingestion.ingest_all(symbols, days=30)
                        ohlcv = report.get("ohlcv", {}).get("total_rows", 0)
                        indicators = report.get("indicators", 0)
                        log.info("Auto-backfill complete: %d OHLCV, %d indicators", ohlcv, indicators)
                        # Verify DuckDB has data now — re-check health
                        post_health = duckdb_store.health_check()
                        for t in (post_health.get("tables") or []):
                            if t.get("name") == "daily_ohlcv":
                                log.info("Post-backfill daily_ohlcv: %d rows", t.get("rows", 0))
                    except Exception as e:
                        log.warning("Auto-backfill failed (non-fatal): %s", e)

                asyncio.create_task(_auto_backfill())
            else:
                log.info("DuckDB data OK: %d OHLCV rows, %d indicator rows — skipping backfill", _ohlcv_rows, _indicator_rows)
        except Exception:
            pass

    # 4-6. Background tasks (legacy + monitoring)
    # BUG FIX 2: tick_task must ALWAYS run — it does Alpaca data ingestion into DuckDB,
    # NOT LLM work. Without it, no data flows into the database regardless of market hours.
    # drift_task is ML-specific and can safely remain gated on LLM_ENABLED.
    _llm_on = os.getenv("LLM_ENABLED", "true").lower() == "true"
    _bg_loops = os.getenv("BACKGROUND_LOOPS", "true").lower() in ("1", "true", "yes")
    # Wrap background loops in supervisor for crash recovery (SF9 fix)
    tick_task = asyncio.create_task(
        _supervised_loop("market_data_tick", _market_data_tick_loop)
    ) if _bg_loops else None
    drift_task = asyncio.create_task(
        _supervised_loop("drift_check", _drift_check_loop)
    ) if (_llm_on and _bg_loops) else None
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    risk_monitor_task = asyncio.create_task(
        _supervised_loop("risk_monitor", _risk_monitor_loop)
    ) if _bg_loops else None
    if not _bg_loops:
        log.info("\u26A0\uFE0F Background loops disabled (BACKGROUND_LOOPS=false)")

    # Phase 4: Regime Publisher — broadcasts current regime every 60s
    _regime_pub_task = None
    if _bg_loops:
        try:
            from app.council.regime_publisher import get_regime_publisher
            _regime_pub = get_regime_publisher()
            await _regime_pub.start()
            log.info("RegimePublisher started (60s interval)")
        except Exception as e:
            log.debug("RegimePublisher not started: %s", e)

    # Event loop watchdog — logs every 5s to detect freezes
    # 30. Wire critical PUBLISH_ONLY subscribers (Audit Item 2)
    # These events were published into the void — now they have handlers.
    async def _on_hitl_approval_needed(data):
        """Log HITL requests, broadcast to frontend for approval dialog, and alert dashboard."""
        log.warning(
            "🛑 HITL APPROVAL NEEDED: %s %s confidence=%.1f — awaiting human decision",
            data.get("symbol", "?"), data.get("direction", "?"),
            data.get("confidence", 0),
        )
        # Broadcast to frontend so approval dialog can be shown (prevents trades hanging)
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("agents", {
                "type": "hitl_approval_needed",
                "symbol": data.get("symbol"),
                "direction": data.get("direction"),
                "confidence": data.get("confidence"),
                "data": data,
            })
        except Exception as e:
            log.debug("HITL WebSocket broadcast failed: %s", e)
        # Forward to alert.health for dashboard visibility
        try:
            await _message_bus.publish("alert.health", {
                "level": "warning",
                "source": "hitl",
                "message": f"Trade approval needed: {data.get('symbol', '?')} {data.get('direction', '?')}",
                "data": data,
            })
        except Exception:
            pass

    async def _on_position_closed(data):
        """Track closed positions, feed feedback_loop for weight learning, and log."""
        symbol = data.get("symbol", "?")
        pnl = data.get("pnl", 0)
        pnl_pct = data.get("pnl_pct", 0) or (pnl / (data.get("entry_price", 1) * data.get("qty", 1)) if data.get("entry_price") and data.get("qty") else 0)
        reason = data.get("reason") or data.get("close_reason", "?")
        log.info(
            "📊 Position CLOSED: %s pnl=%.2f (%.2f%%) reason=%s",
            symbol, pnl, pnl_pct * 100, reason,
        )
        # CRITICAL: Feed feedback_loop so weight_learner learns from this trade
        try:
            from app.council.feedback_loop import record_outcome
            trade_id = data.get("council_decision_id") or data.get("order_id") or ""
            outcome = "win" if pnl > 0 else "loss" if pnl < 0 else "scratch"
            entry = data.get("entry_price") or 1.0
            r_multiple = (pnl / (entry * data.get("qty", 1))) if entry and data.get("qty") else 0.0
            record_outcome(trade_id=trade_id, symbol=symbol, outcome=outcome, r_multiple=r_multiple)
        except Exception as e:
            log.debug("Feedback loop record_outcome failed: %s", e)

    async def _on_position_partial_exit(data):
        """Log partial exits for position tracking."""
        log.info(
            "📉 Partial EXIT: %s qty_closed=%s remaining=%s",
            data.get("symbol", "?"), data.get("qty_closed", "?"),
            data.get("qty_remaining", "?"),
        )

    async def _on_symbol_prep_ready(data):
        """Symbol preparation complete — ready for signal generation."""
        log.info(
            "✅ Symbol PREP READY: %s (features=%d)",
            data.get("symbol", "?"), len(data.get("features", {})),
        )

    await _message_bus.subscribe("hitl.approval_needed", _on_hitl_approval_needed)
    await _message_bus.subscribe("position.closed", _on_position_closed)
    await _message_bus.subscribe("position.partial_exit", _on_position_partial_exit)
    await _message_bus.subscribe("symbol.prep.ready", _on_symbol_prep_ready)
    log.info("✅ 4 critical PUBLISH_ONLY subscribers wired (hitl, position.closed/partial, symbol.prep.ready)")

    # 31. Sensory store — wire orphan perception/macro/signal topics so council agents can read them
    from app.core.sensory_store import update as sensory_update
    _SENSORY_TOPICS = (
        "perception.finviz.screener",
        "perception.macro",
        "perception.edgar",
        "perception.gex",
        "perception.insider",
        "perception.squeezemetrics",
        "perception.earnings",
        "perception.congressional",
        "macro.fred",
        "perception.flow.uw_analysis",
        "signal.external",
        "knowledge.ingested",
    )
    for _topic in _SENSORY_TOPICS:
        async def _handler(payload, t=_topic):
            try:
                sensory_update(t, payload)
            except Exception as e:
                log.debug("Sensory store update failed for %s: %s", t, e)
        await _message_bus.subscribe(_topic, _handler)

    # alert.health → homeostasis + dashboard WebSocket
    async def _on_alert_health(data):
        try:
            sensory_update("alert.health", data)
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("health", {"type": "alert", "data": data})
        except Exception as e:
            log.debug("Alert health handler failed: %s", e)
    await _message_bus.subscribe("alert.health", _on_alert_health)

    # position.partial_exit → sensory store (portfolio_optimizer_agent can read from blackboard)
    async def _on_position_partial_exit_sensory(data):
        try:
            sensory_update("position.partial_exit", data)
        except Exception:
            pass
    await _message_bus.subscribe("position.partial_exit", _on_position_partial_exit_sensory)

    log.info("✅ Sensory store + alert.health subscribers wired (%d perception/macro/signal topics)", len(_SENSORY_TOPICS) + 2)

    _heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "30"))

    async def _event_loop_watchdog():
        import time as _time
        _tick = 0
        while True:
            _tick += 1
            if _tick <= 3 or _tick % 12 == 0:  # Log first 3 then every ~6 min
                log.info("🫀 EventLoop heartbeat #%d (alive at T+%ds)", _tick, _tick * _heartbeat_interval)
            await asyncio.sleep(_heartbeat_interval)

    asyncio.create_task(_event_loop_watchdog())

    # Start HealthMonitor background task
    try:
        from app.services.health_monitor import health_monitor as _health_monitor
        await _health_monitor.start()
        log.info("✅ HealthMonitor started (auto-debug + self-healing)")
    except Exception as e:
        log.warning("HealthMonitor failed to start: %s", e)

    log.info("=" * 60)
    log.info("Embodier Trader v%s ONLINE — PRODUCTION (Council-Controlled Intelligence)", settings.APP_VERSION)
    _port = settings.effective_port; log.info("  API: http://localhost:%s/docs", _port)
    log.info("  Health: http://localhost:%s/health", _port)
    log.info("  Deep Health: http://localhost:%s/health/deep", _port)
    log.info("  WS: ws://localhost:%s/ws", _port)
    log.info("=" * 60)

    try:
        yield
    finally:
        # Stop HealthMonitor
        try:
            from app.services.health_monitor import health_monitor as _hm
            await _hm.stop()
        except Exception:
            pass
        # Stop ingestion framework
        try:
            if 'ingestion_scheduler' in locals():
                ingestion_scheduler.stop()
                log.info("Ingestion scheduler stopped")
        except Exception as e:
            log.warning("Error stopping ingestion scheduler: %s", e)

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
        # Stop regime publisher
        try:
            from app.council.regime_publisher import get_regime_publisher
            _rp = get_regime_publisher()
            await _rp.stop()
        except Exception:
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
            duckdb_store.close()
        except Exception:
            pass

        if _lock_acquired:
            release_lock()

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
    allow_origins=settings.effective_cors_origins,
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
app.include_router(mobile_api.router, prefix="/api/v1/mobile", tags=["mobile"])
app.include_router(ingestion_firehose.router)
app.include_router(brain.router, prefix="/api/v1/brain", tags=["brain"])
app.include_router(awareness.router, prefix="/api/v1", tags=["awareness"])
app.include_router(blackboard_routes.router, prefix="/api/v1/blackboard", tags=["blackboard"])
app.include_router(triage.router, prefix="/api/v1/triage", tags=["triage"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(briefing.router, prefix="/api/v1/briefing", tags=["briefing"])
app.include_router(tradingview.router, prefix="/api/v1/tradingview", tags=["tradingview"])
app.include_router(metrics_api.router, tags=["metrics"])

# Unified health monitoring endpoint (required for Startup Health page and 7-phase check)
from app.api.v1 import health as health_api
app.include_router(health_api.router, tags=["health"])


@app.get("/api/v1/ws/registry", tags=["websocket"])
async def ws_registry():
    """WebSocket channel registry: channel names, message schema, subscriber counts."""
    from app.websocket_manager import get_channel_info
    info = get_channel_info()
    live = info.get("channels", {}) or {}
    # Expose all valid channel names so clients know what can be subscribed to
    all_channel_names = sorted(set(_VALID_WS_CHANNELS) | set(live.keys()))
    subscriber_counts = {ch: live.get(ch, 0) for ch in all_channel_names}
    return {
        "total_connections": info.get("total_connections", 0),
        "channels": all_channel_names,
        "subscriber_counts": subscriber_counts,
        "message_schema": {
            "channel": "string (e.g. signal, council, risk, market, order, swarm)",
            "type": "string (e.g. update, new_signal, verdict)",
            "data": "object (payload)",
            "ts": "number (Unix timestamp)",
        },
        "schema_examples": [
            {"channel": "signal", "type": "new_signal", "data": {"symbol": "AAPL", "score": 80}, "ts": 1234567890.0},
            {"channel": "council", "type": "verdict", "data": {"symbol": "AAPL", "direction": "buy"}, "ts": 1234567890.0},
        ],
    }


@app.get("/api/v1/consensus", tags=["agents"])
async def consensus_alias():
    """Same as GET /api/v1/agents/consensus."""
    from app.api.v1.agents import get_consensus
    return await get_consensus()


# --- Valid WebSocket channels (server-side only publishing) ---
# Must match WS_ALLOWED_CHANNELS in websocket_manager.py and frontend WS_CHANNELS (config/api.js)
_VALID_WS_CHANNELS = frozenset({
    "signal", "signals", "order", "council", "council_verdict",
    "risk", "swarm", "kelly", "market", "macro", "blackboard",
    "alerts", "performance", "agents", "data_sources", "datasources",
    "trades", "logs", "sentiment", "alignment", "homeostasis", "circuit_breaker",
    "health", "market_data", "outcomes", "system", "briefing",
})

# --- WebSocket rate limiting (Audit Task 15) ---
_WS_MSG_RATE: dict = {}  # websocket -> list of timestamps
_WS_MSG_RATE_LAST_PRUNE: float = 0.0  # last prune epoch
_WS_MAX_MSGS_PER_MIN = 120
_WS_MAX_CONNECTIONS = 50


def _prune_ws_rate_dict() -> None:
    """Safety-net pruning for _WS_MSG_RATE — removes stale entries.

    Runs at most once per 60 seconds. Catches leaked WebSocket entries
    whose finally block didn't execute (e.g., process crash, TCP RST).
    """
    import time as _t
    global _WS_MSG_RATE_LAST_PRUNE
    now = _t.time()
    if now - _WS_MSG_RATE_LAST_PRUNE < 60:
        return
    _WS_MSG_RATE_LAST_PRUNE = now
    # Remove entries with no recent activity (>120s)
    stale = [ws for ws, ts_list in _WS_MSG_RATE.items()
             if not ts_list or (now - max(ts_list)) > 120]
    for ws in stale:
        _WS_MSG_RATE.pop(ws, None)
    if stale:
        log.debug("WS rate-limit pruned %d stale entries", len(stale))


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

    # Enforce auth token on WebSocket connect (production security)
    token = websocket.query_params.get("token", "")
    expected = (settings.API_AUTH_TOKEN or "").strip()
    if expected and (not token or token != expected):
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept()
    add_connection(websocket)
    _WS_MSG_RATE[websocket] = []
    try:
        while True:
            raw = await websocket.receive_text()

            # Rate limiting (Task 15): max 120 msgs/min per connection
            _prune_ws_rate_dict()  # safety-net prune for leaked entries
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


@app.get("/")
async def root():
    """Root path — redirects to docs and confirms API is up."""
    return {
        "app": "Embodier Trader",
        "version": getattr(settings, "APP_VERSION", "5.0.0"),
        "docs": "/docs",
        "health": "/health",
        "healthz": "/healthz",
    }


@app.get("/healthz")
async def liveness():
    """Liveness probe — confirms the process is alive and can serve HTTP.

    Kubernetes uses this to decide whether to restart the container.
    Must be fast (<50ms) with zero external dependencies.
    """
    return {"status": "alive"}


@app.get("/readyz")
async def readiness(request: Request):
    """Readiness probe — confirms the app can serve real traffic.

    Returns 200 only when DuckDB and MessageBus are ready (set during lifespan).
    Launcher should poll this URL (or GET /api/v1/status/ready) before starting the frontend.

    Kubernetes uses this to decide whether to route traffic to this pod.
    Returns 503 if any critical dependency is down.
    """
    checks = {}
    ready = True

    # Lifespan-set flags take precedence (backend ready only after full 6-phase startup)
    duckdb_ready = getattr(request.app.state, READINESS_DUCKDB_KEY, False)
    message_bus_ready = getattr(request.app.state, READINESS_MESSAGEBUS_KEY, False)
    if not duckdb_ready or not message_bus_ready:
        checks["duckdb"] = "ok" if duckdb_ready else "not_ready"
        checks["message_bus"] = "ok" if message_bus_ready else "not_ready"
        ready = False
    else:
        # Confirm with live checks
        try:
            from app.data.duckdb_storage import duckdb_store
            health = duckdb_store.health_check()
            checks["duckdb"] = "ok" if health.get("total_tables", 0) > 0 else "degraded"
            if checks["duckdb"] != "ok":
                ready = False
        except Exception:
            checks["duckdb"] = "unavailable"
            ready = False
        checks["message_bus"] = "ok" if _message_bus else "not_started"
        if not _message_bus:
            ready = False

    # Alpaca API keys configured (required for trading)
    from app.services.alpaca_service import alpaca_service
    checks["alpaca_configured"] = "ok" if alpaca_service._is_configured() else "not_configured"

    # Per-service health (Audit Task 8)
    try:
        from app.core.service_registry import get_health_summary
        svc_health = get_health_summary()
        checks["services"] = svc_health
        if svc_health.get("failed", 0) > 0:
            checks["intelligence_degraded"] = True
    except Exception:
        checks["services"] = "registry_unavailable"

    # Ollama LLM availability (v5.0.0 audit)
    try:
        import httpx
        ollama_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                checks["ollama"] = {"status": "ok", "models_loaded": len(models)}
            else:
                checks["ollama"] = {"status": "degraded", "http_code": resp.status_code}
    except Exception:
        checks["ollama"] = {"status": "unavailable"}

    # Redis connectivity (v5.0.0 audit)
    redis_url = getattr(settings, "REDIS_URL", "").strip()
    if redis_url:
        try:
            import socket
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 6379
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((host, port))
            sock.sendall(b"PING\r\n")
            data = sock.recv(64)
            sock.close()
            checks["redis"] = "ok" if b"PONG" in data else "degraded"
        except Exception:
            checks["redis"] = "unavailable"
            redis_required = getattr(settings, "REDIS_REQUIRED", False)
            if redis_required:
                ready = False
    else:
        checks["redis"] = "not_configured"

    # Brain Service / PC2 gRPC (v5.0.0 audit)
    try:
        brain_host = getattr(settings, "BRAIN_HOST", "localhost")
        brain_port = int(getattr(settings, "BRAIN_PORT", 50051))
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((brain_host, brain_port))
        sock.close()
        checks["brain_service"] = "ok" if result == 0 else "unavailable"
    except Exception:
        checks["brain_service"] = "unavailable"

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


@app.get("/health/deep")
async def deep_health_check():
    """Deep health check — all components with auto-debug diagnostics.

    Runs full health checks on every component (DB, Alpaca, Brain, Ollama,
    MessageBus, Council, Signal Engine, Frontend). Used by the Service
    Supervisor for auto-restart decisions.
    """
    try:
        from app.services.health_monitor import health_monitor
        await health_monitor._run_all_checks()
        return health_monitor.get_full_report()
    except Exception as exc:
        log.exception("Deep health check failed")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(exc)},
        )
