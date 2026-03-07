"""Comprehensive import test: validates every module in the backend can be imported without errors.

This catches:
- IndentationErrors
- Missing dependencies
- Circular imports
- Broken imports at the module level
"""
import importlib
import sys
import os
import pytest

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── All backend service modules ──────────────────────────────────────────────

SERVICE_MODULES = [
    "app.services.adaptive_router",
    "app.services.alpaca_key_pool",
    "app.services.alpaca_service",
    "app.services.alpaca_stream_manager",
    "app.services.alpaca_stream_service",
    "app.services.autonomous_scout",
    "app.services.backtest_engine",
    "app.services.brain_client",
    "app.services.claude_reasoning",
    "app.services.cognitive_telemetry",
    "app.services.correlation_radar",
    "app.services.council_evaluator",
    "app.services.data_ingestion",
    "app.services.database",
    "app.services.discord_swarm_bridge",
    "app.services.execution_simulator",
    "app.services.expected_move_service",
    "app.services.feature_service",
    "app.services.finviz_service",
    "app.services.fred_service",
    "app.services.geopolitical_radar",
    "app.services.gpu_telemetry",
    "app.services.hyper_swarm",
    "app.services.intelligence_cache",
    "app.services.intelligence_orchestrator",
    "app.services.kelly_position_sizer",
    "app.services.knowledge_ingest",
    "app.services.llm_dispatcher",
    "app.services.llm_router",
    "app.services.llm_schemas",
    "app.services.market_data_agent",
    "app.services.market_wide_sweep",
    "app.services.ml_scorer",
    "app.services.ml_training",
    "app.services.model_pinning",
    "app.services.news_aggregator",
    "app.services.node_discovery",
    "app.services.ollama_node_pool",
    "app.services.openclaw_bridge_service",
    "app.services.openclaw_db",
    "app.services.order_executor",
    "app.services.outcome_tracker",
    "app.services.pattern_library",
    "app.services.perplexity_intelligence",
    "app.services.position_manager",
    "app.services.sec_edgar_service",
    "app.services.settings_service",
    "app.services.signal_engine",
    "app.services.swarm_spawner",
    "app.services.trade_stats_service",
    "app.services.training_store",
    "app.services.turbo_scanner",
    "app.services.unified_profit_engine",
    "app.services.unusual_whales_service",
    "app.services.walk_forward_validator",
]

# ── LLM Client modules ──────────────────────────────────────────────────────

LLM_CLIENT_MODULES = [
    "app.services.llm_clients.claude_client",
    "app.services.llm_clients.ollama_client",
    "app.services.llm_clients.perplexity_client",
]

# ── All API route modules ────────────────────────────────────────────────────

ROUTE_MODULES = [
    "app.api.v1.agents",
    "app.api.v1.alerts",
    "app.api.v1.alignment",
    "app.api.v1.alpaca",
    "app.api.v1.backtest_routes",
    "app.api.v1.cluster",
    "app.api.v1.cns",
    "app.api.v1.cognitive",
    "app.api.v1.council",
    "app.api.v1.data_sources",
    "app.api.v1.features",
    "app.api.v1.flywheel",
    "app.api.v1.logs",
    "app.api.v1.market",
    "app.api.v1.ml_brain",
    "app.api.v1.openclaw",
    "app.api.v1.orders",
    "app.api.v1.patterns",
    "app.api.v1.performance",
    "app.api.v1.portfolio",
    "app.api.v1.quotes",
    "app.api.v1.risk",
    "app.api.v1.risk_shield_api",
    "app.api.v1.sentiment",
    "app.api.v1.settings_routes",
    "app.api.v1.signals",
    "app.api.v1.status",
    "app.api.v1.stocks",
    "app.api.v1.strategy",
    "app.api.v1.swarm",
    "app.api.v1.system",
    "app.api.v1.training",
    "app.api.v1.youtube_knowledge",
    "app.api.ingestion",
]

# ── Council agent modules ────────────────────────────────────────────────────

COUNCIL_AGENT_MODULES = [
    "app.council.agents.market_perception_agent",
    "app.council.agents.flow_perception_agent",
    "app.council.agents.regime_agent",
    "app.council.agents.social_perception_agent",
    "app.council.agents.news_catalyst_agent",
    "app.council.agents.youtube_knowledge_agent",
    "app.council.agents.hypothesis_agent",
    "app.council.agents.strategy_agent",
    "app.council.agents.risk_agent",
    "app.council.agents.execution_agent",
    "app.council.agents.critic_agent",
    "app.council.agents.rsi_agent",
    "app.council.agents.bbv_agent",
    "app.council.agents.ema_trend_agent",
    "app.council.agents.intermarket_agent",
    "app.council.agents.relative_strength_agent",
    "app.council.agents.cycle_timing_agent",
    "app.council.agents.gex_agent",
    "app.council.agents.insider_agent",
    "app.council.agents.earnings_tone_agent",
    "app.council.agents.finbert_sentiment_agent",
    "app.council.agents.supply_chain_agent",
    "app.council.agents.institutional_flow_agent",
    "app.council.agents.congressional_agent",
    "app.council.agents.dark_pool_agent",
    "app.council.agents.portfolio_optimizer_agent",
    "app.council.agents.layered_memory_agent",
    "app.council.agents.alt_data_agent",
    "app.council.agents.macro_regime_agent",
    "app.council.agents.red_team_agent",
    "app.council.agents.bull_debater",
    "app.council.agents.bear_debater",
]

# ── Council core modules ─────────────────────────────────────────────────────

COUNCIL_CORE_MODULES = [
    "app.council.arbiter",
    "app.council.blackboard",
    "app.council.council_gate",
    "app.council.data_quality",
    "app.council.feedback_loop",
    "app.council.hitl_gate",
    "app.council.homeostasis",
    "app.council.overfitting_guard",
    "app.council.runner",
    "app.council.schemas",
    "app.council.self_awareness",
    "app.council.shadow_tracker",
    "app.council.task_spawner",
    "app.council.weight_learner",
    "app.council.agent_config",
]

# ── Knowledge modules ────────────────────────────────────────────────────────

KNOWLEDGE_MODULES = [
    "app.knowledge.embedding_service",
    "app.knowledge.heuristic_engine",
    "app.knowledge.knowledge_graph",
    "app.knowledge.memory_bank",
]

# ── ML/Data modules ──────────────────────────────────────────────────────────

ML_DATA_MODULES = [
    "app.data.duckdb_storage",
    "app.data.feature_store",
    "app.data.features",
    "app.data.labels",
    "app.data.storage",
    "app.modules.ml_engine.config",
    "app.modules.ml_engine.drift_detector",
    "app.modules.ml_engine.feature_pipeline",
    "app.modules.ml_engine.model_registry",
    "app.modules.ml_engine.multi_window_evaluator",
    "app.modules.ml_engine.outcome_resolver",
    "app.modules.ml_engine.risk_adjusted_objective",
    "app.modules.ml_engine.trainer",
    "app.modules.ml_engine.xgboost_trainer",
]

# ── Core modules ─────────────────────────────────────────────────────────────

CORE_MODULES = [
    "app.core.config",
    "app.core.logging_config",
    "app.core.message_bus",
    "app.core.security",
    "app.core.service_registry",
    "app.core.alignment.bible",
    "app.core.alignment.bright_lines",
    "app.core.alignment.constellation",
    "app.core.alignment.critique",
    "app.core.alignment.engine",
    "app.core.alignment.metacognition",
    "app.core.alignment.types",
    "app.websocket_manager",
]

# ── Combine all ──────────────────────────────────────────────────────────────

ALL_MODULES = (
    SERVICE_MODULES
    + LLM_CLIENT_MODULES
    + ROUTE_MODULES
    + COUNCIL_AGENT_MODULES
    + COUNCIL_CORE_MODULES
    + KNOWLEDGE_MODULES
    + ML_DATA_MODULES
    + CORE_MODULES
)


@pytest.mark.parametrize("module_path", ALL_MODULES)
def test_import_module(module_path):
    """Verify each module can be imported without errors."""
    try:
        mod = importlib.import_module(module_path)
        assert mod is not None
    except ImportError as e:
        # Allow optional dependencies to be missing (torch, sentence_transformers, etc.)
        optional = [
            "torch", "sentence_transformers", "transformers",
            "grpc", "grpcio",
        ]
        if any(opt in str(e) for opt in optional):
            pytest.skip(f"Optional dependency missing: {e}")
        raise


# ── Verify all route modules have a router attribute ─────────────────────────

@pytest.mark.parametrize("module_path", ROUTE_MODULES)
def test_route_module_has_router(module_path):
    """Every route module must export a 'router' APIRouter."""
    try:
        mod = importlib.import_module(module_path)
    except ImportError:
        pytest.skip("Module not importable")
        return
    assert hasattr(mod, "router"), f"{module_path} missing 'router' attribute"


# ── Verify all council agents have the required interface ────────────────────

@pytest.mark.parametrize("module_path", COUNCIL_AGENT_MODULES)
def test_council_agent_has_vote_function(module_path):
    """Every council agent must expose an async vote() or analyze() function."""
    try:
        mod = importlib.import_module(module_path)
    except ImportError:
        pytest.skip("Module not importable")
        return
    has_interface = (
        hasattr(mod, "evaluate")
        or hasattr(mod, "vote")
        or hasattr(mod, "analyze")
        or hasattr(mod, "run")
        or hasattr(mod, "evaluate_debate")  # bull_debater / bear_debater
    )
    assert has_interface, f"{module_path} missing evaluate()/vote()/analyze()/run()/debate() function"
