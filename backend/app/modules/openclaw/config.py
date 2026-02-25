"""config.py v6.0 - OpenClaw Apex Predator Swarm Configuration

Central configuration for the 24/7 multi-agent intelligence swarm.
Alpaca Markets API is the PRIMARY data publisher (real-time bars,
account data, order execution).  All agents read from / write to
the in-process Blackboard via Pub/Sub topics.

v6.0 additions:
- Elite Trading System Bridge (PC2 GPU training integration)
- 4-Agent Options Flow Pipeline (institutional sweep detection)
- Darwinian Swarm meta-layer (self-evolving agent architecture)
- Hunter-Killer Short Swarm (bear-side relative weakness)
- Swarm Daemon (OS-level agent spawner on port 8787)
- Tier 5 Clawbots (Apex Predator hierarchy agents)

Hierarchy:
  .env  ->  os.environ  ->  defaults below
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── project paths ────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"
for _d in (DATA_DIR, MODELS_DIR, LOGS_DIR):
    _d.mkdir(exist_ok=True)

# ============================================================
#  ALPACA MARKETS — PRIMARY DATA PUBLISHER
#  Real-time WebSocket bars, historical OHLCV, account/orders,
#  trade execution.  Every other data source is supplementary.
# ============================================================
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
ALPACA_DATA_URL = os.getenv("ALPACA_DATA_URL", "https://data.alpaca.markets")
ALPACA_STREAM_URL = os.getenv("ALPACA_STREAM_URL", "wss://stream.data.alpaca.markets/v2/iex")
ALPACA_FEED = os.getenv("ALPACA_FEED", "iex")  # iex (free) | sip (paid)
ALPACA_MAX_SYMBOLS = int(os.getenv("ALPACA_MAX_SYMBOLS", "50"))

# ============================================================
#  BLACKBOARD — PUB/SUB MESSAGE BROKER (in-process)
#  Agents publish to topics; subscribers react in real time.
#  No external Redis / Kafka needed.
# ============================================================
BLACKBOARD_PERSIST_PATH = str(DATA_DIR / "live_scores.json")
BLACKBOARD_PERSIST_INTERVAL = int(os.getenv("BLACKBOARD_PERSIST_INTERVAL", "60"))
BLACKBOARD_MAX_HISTORY = int(os.getenv("BLACKBOARD_MAX_HISTORY", "500"))

# Topic names (agents publish / subscribe to these)
TOPIC_ALPHA_SIGNALS = "alpha_signals"
TOPIC_ANALYSIS = "analysis"
TOPIC_SCORES = "scores"
TOPIC_EXECUTION = "execution"
TOPIC_RISK = "risk"
TOPIC_MEMORY = "memory"
TOPIC_HEARTBEAT = "heartbeat"
TOPIC_SCOUT = "scout_signals"
TOPIC_ORACLE = "oracle_intel"
TOPIC_LORA = "lora_updates"

# ============================================================
#  AGENT HEARTBEAT & HEALTH
#  Every agent pings heartbeat topic; streaming_engine monitors.
# ============================================================
AGENT_HEARTBEAT_INTERVAL = int(os.getenv("AGENT_HEARTBEAT_INTERVAL", "30"))
AGENT_HEARTBEAT_TIMEOUT = int(os.getenv("AGENT_HEARTBEAT_TIMEOUT", "90"))
AGENT_RESTART_MAX_RETRIES = int(os.getenv("AGENT_RESTART_MAX_RETRIES", "3"))

# ============================================================
#  REAL-TIME STREAMING ENGINE
#  streaming_engine.py = central nervous system (always on)
#  Subscribes to Alpaca WebSocket, drives the entire swarm.
# ============================================================
STREAMING_ENABLED = os.getenv("STREAMING_ENABLED", "true").lower() == "true"
STREAMING_BAR_TIMEFRAME = os.getenv("STREAMING_BAR_TIMEFRAME", "1Min")
STREAMING_RECONNECT_BASE = float(os.getenv("STREAMING_RECONNECT_BASE", "1.0"))
STREAMING_RECONNECT_MAX = float(os.getenv("STREAMING_RECONNECT_MAX", "60.0"))
SCORE_TRIGGER_THRESHOLD = int(os.getenv("SCORE_TRIGGER_THRESHOLD", "75"))
WATCHLIST_PATH = str(DATA_DIR / "daily_watchlist.json")
LIVE_SCORES_PATH = str(DATA_DIR / "live_scores.json")

# ============================================================
#  SUPPLEMENTARY DATA PUBLISHERS (Tier 1 - write to Blackboard)
# ============================================================

# -- Unusual Whales (options flow + OI) --
UNUSUALWHALES_API_KEY = os.getenv("UNUSUALWHALES_API_KEY")
UNUSUALWHALES_BASE_URL = "https://api.unusualwhales.com/api"
WHALE_MIN_PREMIUM = int(os.getenv("WHALE_MIN_PREMIUM", "100000"))
WHALE_MAX_DTE = int(os.getenv("WHALE_MAX_DTE", "60"))
WHALE_MIN_DTE = int(os.getenv("WHALE_MIN_DTE", "7"))

# -- Finviz Elite (PAS v8 Gate screener) --
FINVIZ_EXPORT_BASE_URL = "https://elite.finviz.com/export.ashx"
FINVIZ_API_KEY = os.getenv("FINVIZ_API_KEY", "")
SCAN_PRESET = os.getenv("SCAN_PRESET", "pas_v8_gate")
SCAN_MAX_RESULTS = int(os.getenv("SCAN_MAX_RESULTS", "50"))

# -- FOM Expected Moves --
FOM_CACHE_HOURS = int(os.getenv("FOM_CACHE_HOURS", "6"))
FOM_FALLBACK_ATR_MULTIPLIER = float(os.getenv("FOM_FALLBACK_ATR_MULTIPLIER", "1.0"))

# -- FRED (Federal Reserve Economic Data) --
FRED_API_KEY = os.getenv("FRED_API_KEY")

# ============================================================
#  COMMUNICATION CHANNELS
# ============================================================

# -- Slack --
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
OC_TRADE_DESK_CHANNEL = os.getenv("OC_TRADE_DESK_CHANNEL")
OC_SIGNALS_RAW_CHANNEL = os.getenv("OC_SIGNALS_RAW_CHANNEL")

# -- Discord --
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_UW_CHANNEL_ID = os.getenv("DISCORD_UW_CHANNEL_ID")
DISCORD_FOM_CHANNEL_ID = os.getenv("DISCORD_FOM_CHANNEL_ID")
DISCORD_EXPECTED_MOVES_CHANNEL_ID = os.getenv("DISCORD_EXPECTED_MOVES_CHANNEL_ID")
DISCORD_MAVERICK_CHANNEL_ID = os.getenv("DISCORD_MAVERICK_CHANNEL_ID")

# -- Database Logger (replaces Google Sheets) --
OPENCLAW_DB_PATH = os.getenv("OPENCLAW_DB_PATH", str(DATA_DIR / "openclaw_trades.db"))
# -- TradingView --
TRADINGVIEW_WEBHOOK_SECRET = os.getenv("TRADINGVIEW_WEBHOOK_SECRET", "")
TRADINGVIEW_WEBHOOK_URL = os.getenv("TRADINGVIEW_WEBHOOK_URL", "")

# ============================================================
#  REGIME DETECTION & MARKET STATE
# ============================================================
REGIME_GREEN_MIN = int(os.getenv("REGIME_GREEN_MIN", "18"))
REGIME_YELLOW_MIN = int(os.getenv("REGIME_YELLOW_MIN", "25"))
REGIME_GREEN_VIX = REGIME_GREEN_MIN
REGIME_YELLOW_VIX = REGIME_YELLOW_MIN
REGIME_RED_VIX = 999

REGIME_CONFIG = {
    "GREEN":        {"momentum": 0.70, "reversion": 0.30, "risk_pct": 2.0, "max_positions": 6},
    "YELLOW":       {"momentum": 0.40, "reversion": 0.60, "risk_pct": 1.5, "max_positions": 5},
    "RED":          {"momentum": 0.0,  "reversion": 0.0,  "risk_pct": 0.0, "max_positions": 0},
    "RED_RECOVERY": {"momentum": 0.0,  "reversion": 1.0,  "risk_pct": 1.0, "max_positions": 4},
}

REGIME_EXPOSURE = {"GREEN": 0.60, "YELLOW": 0.40, "RED": 0.20}

# Velez scoring thresholds
VELEZ_SLAM = 70
VELEZ_GO = 80
VELEZ_WATCH = 50

# ============================================================
#  CRASH DETECTION THRESHOLDS
# ============================================================
CRASH_NY_SPREAD = 0.4
CRASH_VIX_SINGLE_DAY = 25
CRASH_BREADTH_MIN = 0.25
CRASH_SPY_DROP = 0.02
CRASH_HY_SPREAD = 0.15
CRASH_VIX_SPIKE = 0.15

# ============================================================
#  RISK MANAGEMENT & POSITION SIZING
# ============================================================
DEFAULT_RISK_PCT = float(os.getenv("DEFAULT_RISK_PCT", "1.5"))
MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "2.0"))
MAX_PORTFOLIO_HEAT = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.06"))
CORRELATION_THRESHOLD = float(os.getenv("CORRELATION_THRESHOLD", "0.75"))
CIRCUIT_BREAKER_THRESHOLD = float(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "-0.03"))
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.05"))
MAX_DEPLOYED_PCT = float(os.getenv("MAX_DEPLOYED_PCT", "0.60"))
MAX_POSITIONS_PER_SECTOR = int(os.getenv("MAX_POSITIONS_PER_SECTOR", "3"))

# ============================================================
#  EXECUTION ENGINE
# ============================================================
MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "10"))
TRADE_CONFIRM_TIMEOUT = int(os.getenv("TRADE_CONFIRM_TIMEOUT", "300"))
EXECUTION_LOG_DIR = str(DATA_DIR)
AUTO_EXECUTE_ENABLED = os.getenv("AUTO_EXECUTE_ENABLED", "false").lower() == "true"

# ============================================================
#  LLM — HYBRID (Ollama local + Perplexity cloud)
#  Local = free / unlimited.  Perplexity = live web + deep research.
# ============================================================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "qwen3:14b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
LLM_PREFER_LOCAL = os.getenv("LLM_PREFER_LOCAL", "true").lower() == "true"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
PERPLEXITY_SEARCH_MODEL = os.getenv("PERPLEXITY_SEARCH_MODEL", "sonar-pro")
PERPLEXITY_REASON_MODEL = os.getenv("PERPLEXITY_REASON_MODEL", "sonar-reasoning-pro")
PERPLEXITY_DEEP_MODEL = os.getenv("PERPLEXITY_DEEP_MODEL", "sonar-deep-research")
PERPLEXITY_ENABLED = os.getenv("PERPLEXITY_ENABLED", "true").lower() == "true"

# ============================================================
#  ML ENSEMBLE (XGBoost + Bayesian weights)
# ============================================================
ML_ENSEMBLE_ENABLED = os.getenv("ML_ENSEMBLE_ENABLED", "true").lower() == "true"
ML_RETRAIN_SCHEDULE = os.getenv("ML_RETRAIN_SCHEDULE", "saturday_02:00")
MIN_TRAINING_SAMPLES = int(os.getenv("MIN_TRAINING_SAMPLES", "100"))
ML_MODELS_DIR = str(MODELS_DIR)

# ============================================================
#  MEMORY SYSTEM (SQLite + ChromaDB + causal graph)
# ============================================================
MEMORY_DB_PATH = str(DATA_DIR / "memory_v3.db")
MEMORY_CHROMA_DIR = str(DATA_DIR / "chroma_store")
MEMORY_ALPHA_DECAY_DAYS = int(os.getenv("MEMORY_ALPHA_DECAY_DAYS", "90"))
MEMORY_MAX_SIMILAR_RESULTS = int(os.getenv("MEMORY_MAX_SIMILAR_RESULTS", "10"))
MEMORY_FEEDBACK_ENABLED = os.getenv("MEMORY_FEEDBACK_ENABLED", "true").lower() == "true"

# -- NEW: Memory Consolidation Config --
MEMORY_CONSOLIDATION_INTERVAL_HOURS = int(os.getenv("MEMORY_CONSOLIDATION_INTERVAL_HOURS", "24"))
MEMORY_COMPACTION_AGE_DAYS = int(os.getenv("MEMORY_COMPACTION_AGE_DAYS", "90"))
MEMORY_MIN_TRADES_FOR_SEMANTIC = int(os.getenv("MEMORY_MIN_TRADES_FOR_SEMANTIC", "5"))

# -- NEW: Memory Recall Config --
MEMORY_PRELOAD_DAYS = int(os.getenv("MEMORY_PRELOAD_DAYS", "2"))
MEMORY_RECALL_MAX_TOKENS = int(os.getenv("MEMORY_RECALL_MAX_TOKENS", "4000"))

# ============================================================
#  DASHBOARD (Flask monitoring UI)
# ============================================================
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5001"))
DASHBOARD_REFRESH_SECONDS = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "30"))

# ============================================================
#  LOGGING
# ============================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "True").lower() in ("true", "1", "yes")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", str(LOGS_DIR / "openclaw.log"))

# ============================================================
#  FLASK WEBHOOK SERVER
# ============================================================
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

# ============================================================
#  AI BRIDGE (Perplexity Tasks <-> OpenClaw via Gist)
# ============================================================
GIST_TOKEN = os.getenv("GIST_TOKEN")
BRIDGE_GIST_ID = os.getenv("BRIDGE_GIST_ID")
AI_BRIDGE_ENABLED = os.getenv("AI_BRIDGE_ENABLED", "True").lower() in ("true", "1", "yes")

# ============================================================
#  EXTERNAL DATA APIs (sentiment, news, social)
# ============================================================
STOCKGEIST_API_URL = os.getenv("STOCKGEIST_API_URL", "https://api.stockgeist.ai")
STOCKGEIST_TOKEN = os.getenv("STOCKGEIST_TOKEN")
STOCKGEIST_AUTH = os.getenv("STOCKGEIST_AUTH")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

# ============================================================
#  WORLD INTEL (macro research pipeline)
# ============================================================
WORLD_INTEL_DIR = BASE_DIR / "world_intel"
WORLD_INTEL_CACHE_HOURS = int(os.getenv("WORLD_INTEL_CACHE_HOURS", "12"))

# ============================================================
#  ELITE TRADING SYSTEM BRIDGE (PC2 GPU Training)
#  Connects OpenClaw swarm to the Elite Trading System on PC2
#  for GPU-accelerated model training and inference.
# ============================================================
ELITE_API_URL = os.getenv("ELITE_API_URL", "http://PC2_IP:8001")
ELITE_API_PREFIX = "/api/v1"
GPU_DEVICE = os.getenv("GPU_DEVICE", "cuda:0")  # PC1 inference GPU
MODEL_ARTIFACTS_PATH = os.getenv("MODEL_ARTIFACTS_PATH", "models/artifacts")
ELITE_SYNC_INTERVAL = int(os.getenv("ELITE_SYNC_INTERVAL", "300"))  # seconds
ELITE_ENABLED = os.getenv("ELITE_ENABLED", "false").lower() == "true"
OPENCLAW_BRIDGE_TOKEN = os.getenv("OPENCLAW_BRIDGE_TOKEN", "")

# ============================================================
# SOVEREIGN GPU — LOCAL SCOUT MODELS & LORA FLYWHEEL
# Local GPU inference for fast pre-screening, nightly LoRA
# fine-tuning on trade outcomes, and Perplexity Oracle for
# pre-market macro intelligence.
# ============================================================
SCOUT_MODEL_NAME = os.getenv("SCOUT_MODEL_NAME", "mistral-7b-instruct")
SCOUT_MODEL_PATH = str(MODELS_DIR / os.getenv("SCOUT_MODEL_PATH", "scout_latest"))
SCOUT_GPU_DEVICE = os.getenv("SCOUT_GPU_DEVICE", "cuda:0")
SCOUT_MAX_TOKENS = int(os.getenv("SCOUT_MAX_TOKENS", "512"))
SCOUT_TEMPERATURE = float(os.getenv("SCOUT_TEMPERATURE", "0.3"))
SCOUT_BATCH_SIZE = int(os.getenv("SCOUT_BATCH_SIZE", "8"))
SCOUT_ENABLED = os.getenv("SCOUT_ENABLED", "true").lower() == "true"

# LoRA fine-tuning schedule (nightly retrain on trade outcomes)
LORA_ENABLED = os.getenv("LORA_ENABLED", "true").lower() == "true"
LORA_SCHEDULE_CRON = os.getenv("LORA_SCHEDULE_CRON", "0 2 * * *")  # 2 AM nightly
LORA_BASE_MODEL = os.getenv("LORA_BASE_MODEL", "mistral-7b-instruct")
LORA_RANK = int(os.getenv("LORA_RANK", "16"))
LORA_ALPHA = int(os.getenv("LORA_ALPHA", "32"))
LORA_EPOCHS = int(os.getenv("LORA_EPOCHS", "3"))
LORA_LR = float(os.getenv("LORA_LR", "2e-4"))
LORA_MIN_TRADES = int(os.getenv("LORA_MIN_TRADES", "50"))
LORA_OUTPUT_DIR = str(MODELS_DIR / "lora_adapters")
LORA_TRAINING_DATA = str(DATA_DIR / "trade_outcomes.jsonl")

# Perplexity Oracle (pre-market macro intelligence)
ORACLE_ENABLED = os.getenv("ORACLE_ENABLED", "true").lower() == "true"
ORACLE_SCHEDULE_CRON = os.getenv("ORACLE_SCHEDULE_CRON", "30 8 * * 1-5")  # 8:30 AM weekdays
ORACLE_TOPICS = os.getenv("ORACLE_TOPICS", "fed_policy,earnings,geopolitical,sector_rotation,volatility").split(",")
ORACLE_CACHE_TTL = int(os.getenv("ORACLE_CACHE_TTL", "3600"))  # seconds
ORACLE_MAX_QUERIES = int(os.getenv("ORACLE_MAX_QUERIES", "10"))

# ============================================================
#  OPTIONS FLOW PIPELINE (4-Agent Institutional Flow Chain)
#  Flow Monitor -> Contextualizer -> Sentiment -> Risk Auditor
#  Each agent enriches and filters institutional sweeps.
# ============================================================
FLOW_MIN_PREMIUM = int(os.getenv("FLOW_MIN_PREMIUM", "50000"))
FLOW_MIN_OI_RATIO = float(os.getenv("FLOW_MIN_OI_RATIO", "1.5"))
FLOW_SWEEP_ONLY = os.getenv("FLOW_SWEEP_ONLY", "true").lower() == "true"
FLOW_POLL_INTERVAL = int(os.getenv("FLOW_POLL_INTERVAL", "15"))  # seconds
FLOW_GEX_CACHE_TTL = int(os.getenv("FLOW_GEX_CACHE_TTL", "120"))  # seconds
FLOW_TIDE_CACHE_TTL = int(os.getenv("FLOW_TIDE_CACHE_TTL", "60"))  # seconds
FLOW_PIPELINE_HISTORY_SIZE = int(os.getenv("FLOW_PIPELINE_HISTORY_SIZE", "200"))
FLOW_PIPELINE_FILE = str(DATA_DIR / "flow_pipeline_history.json")

# ============================================================
#  DARWINIAN SWARM — META-LAYER (Self-Evolving Architecture)
#  Meta-agents that build, test, and cull trading agents based
#  on live fitness scores.  The swarm evolves autonomously.
# ============================================================
DARWIN_ENABLED = os.getenv("DARWIN_ENABLED", "false").lower() == "true"
DARWIN_CYCLE_MINUTES = int(os.getenv("DARWIN_CYCLE_MINUTES", "30"))
DARWIN_KILL_PERCENTILE = float(os.getenv("DARWIN_KILL_PERCENTILE", "0.10"))
DARWIN_PROMOTE_PERCENTILE = float(os.getenv("DARWIN_PROMOTE_PERCENTILE", "0.10"))
DARWIN_MIN_TRADES_FOR_EVAL = int(os.getenv("DARWIN_MIN_TRADES_FOR_EVAL", "5"))
DARWIN_GRACE_PERIOD_HOURS = int(os.getenv("DARWIN_GRACE_PERIOD_HOURS", "48"))
DARWIN_MAX_CAPITAL_ALLOC = float(os.getenv("DARWIN_MAX_CAPITAL_ALLOC", "7500"))
DARWIN_BASE_CAPITAL_ALLOC = float(os.getenv("DARWIN_BASE_CAPITAL_ALLOC", "5000"))
DARWIN_PROMOTE_MULTIPLIER = float(os.getenv("DARWIN_PROMOTE_MULTIPLIER", "1.25"))
# Fitness score weights (must sum to 1.0)
DARWIN_W_NET_PNL = float(os.getenv("DARWIN_W_NET_PNL", "0.30"))
DARWIN_W_SHARPE = float(os.getenv("DARWIN_W_SHARPE", "0.25"))
DARWIN_W_MAX_DD = float(os.getenv("DARWIN_W_MAX_DD", "0.25"))
DARWIN_W_WIN_RATE = float(os.getenv("DARWIN_W_WIN_RATE", "0.20"))
# Architect (code-generating meta-agent)
DARWIN_MIN_SHARPE_DEPLOY = float(os.getenv("DARWIN_MIN_SHARPE_DEPLOY", "1.5"))
DARWIN_PAPER_TEST_HOURS = int(os.getenv("DARWIN_PAPER_TEST_HOURS", "48"))

# ============================================================
#  HUNTER-KILLER SHORT SWARM (Bear-side agents)
#  Relative weakness detector -> short basket compiler.
#  Only active in YELLOW/RED regimes or when shorts are enabled.
# ============================================================
SHORT_SWARM_ENABLED = os.getenv("SHORT_SWARM_ENABLED", "true").lower() == "true"
SHORT_MAX_BASKET_SIZE = int(os.getenv("SHORT_MAX_BASKET_SIZE", "3"))
SHORT_STOP_ATR_MULTIPLE = float(os.getenv("SHORT_STOP_ATR_MULTIPLE", "1.5"))
SHORT_DEFAULT_STOP_PCT = float(os.getenv("SHORT_DEFAULT_STOP_PCT", "0.02"))
SHORT_MAX_BORROW_FEE_PCT = float(os.getenv("SHORT_MAX_BORROW_FEE_PCT", "25.0"))
SHORT_WEAKNESS_THRESHOLD = float(os.getenv("SHORT_WEAKNESS_THRESHOLD", "60.0"))
SHORT_MAX_CORRELATED_EXPOSURE = float(os.getenv("SHORT_MAX_CORRELATED_EXPOSURE", "15.0"))

# ============================================================
#  SWARM DAEMON (OS-Level Agent Spawner)
#  Listens for SPAWN/KILL/PROMOTE directives from meta-agents.
#  Physically creates/destroys agent processes on the host.
# ============================================================
SWARM_DAEMON_PORT = int(os.getenv("SWARM_DAEMON_PORT", "8787"))
SWARM_DAEMON_URL = os.getenv("SWARM_DAEMON_URL", "http://127.0.0.1:8787/bus")
SWARM_AGENTS_DIR = str(BASE_DIR / "swarm_agents")
SWARM_ARCHIVE_DIR = str(BASE_DIR / "swarm_archive")
SWARM_REGISTRY_PATH = str(DATA_DIR / "agent_registry.json")
MAX_ACTIVE_AGENTS = int(os.getenv("MAX_ACTIVE_AGENTS", "20"))
# Regime-to-strategy mapping for the Architect meta-agent
REGIME_STRATEGY_MAP = {
  "bull_trend": "momentum_breakout",
  "bear_trend": "short_momentum",
  "high_vol_chop": "mean_reversion",
  "low_vol_grind": "range_scalp",
  "crash": "volatility_fade",
  "recovery_bounce": "rebound_long",
}

# ============================================================
#  AGENT REGISTRY
#  Canonical list of every swarm agent for health monitoring.
#  streaming_engine.py uses this to verify heartbeats.
# ============================================================
AGENT_REGISTRY = {
    # Tier 1 - Data Publishers (write to Blackboard)
    "finviz_scanner":      {"module": "finviz_scanner",      "tier": 1, "topic": TOPIC_ALPHA_SIGNALS},
    "whale_flow":          {"module": "whale_flow",          "tier": 1, "topic": TOPIC_ALPHA_SIGNALS},
    "sector_rotation":     {"module": "sector_rotation",     "tier": 1, "topic": TOPIC_ALPHA_SIGNALS},
    "earnings_calendar":   {"module": "earnings_calendar",   "tier": 1, "topic": TOPIC_ALPHA_SIGNALS},
    "discord_listener":    {"module": "discord_listener",    "tier": 1, "topic": TOPIC_ALPHA_SIGNALS},
    "fom_expected_moves":  {"module": "fom_expected_moves",  "tier": 1, "topic": TOPIC_ALPHA_SIGNALS},
    # Tier 1 - Analysis Publishers (read data, write analysis)
    "technical_checker":   {"module": "technical_checker",   "tier": 1, "topic": TOPIC_ANALYSIS},
    "mtf_alignment":       {"module": "mtf_alignment",       "tier": 1, "topic": TOPIC_ANALYSIS},
    "amd_detector":        {"module": "amd_detector",        "tier": 1, "topic": TOPIC_ANALYSIS},
    "pullback_detector":   {"module": "pullback_detector",   "tier": 1, "topic": TOPIC_ANALYSIS},
    "rebound_detector":    {"module": "rebound_detector",    "tier": 1, "topic": TOPIC_ANALYSIS},
    "short_detector":      {"module": "short_detector",      "tier": 1, "topic": TOPIC_ANALYSIS},
    "macro_context":       {"module": "macro_context",       "tier": 1, "topic": TOPIC_ANALYSIS},
    # Tier 2 - Scoring Agents (read Blackboard, write scores)
    "composite_scorer":    {"module": "composite_scorer",    "tier": 2, "topic": TOPIC_SCORES},
    "ensemble_scorer":     {"module": "ensemble_scorer",     "tier": 2, "topic": TOPIC_SCORES},
    "dynamic_weights":     {"module": "dynamic_weights",     "tier": 2, "topic": TOPIC_SCORES},
    # Tier 3 - Execution (read scores, execute trades)
    "smart_entry":         {"module": "smart_entry",         "tier": 3, "topic": TOPIC_EXECUTION},
    "auto_executor":       {"module": "auto_executor",       "tier": 3, "topic": TOPIC_EXECUTION},
    "position_manager":    {"module": "position_manager",    "tier": 3, "topic": TOPIC_EXECUTION},
    # Tier 4 - Learning & Memory
    "memory":              {"module": "memory",              "tier": 4, "topic": TOPIC_MEMORY},
    "memory_v3":           {"module": "memory_v3",           "tier": 4, "topic": TOPIC_MEMORY},
    "performance_tracker": {"module": "performance_tracker", "tier": 4, "topic": TOPIC_MEMORY},
    # Tier 5 - Clawbots (Apex Predator hierarchy)
  "apex_orchestrator": {"module": "clawbots.agent_apex_orchestrator", "tier": 5, "topic": TOPIC_EXECUTION},
  "relative_weakness": {"module": "clawbots.agent_relative_weakness", "tier": 5, "topic": TOPIC_ANALYSIS},
  "short_basket_compiler": {"module": "clawbots.agent_short_basket_compiler", "tier": 5, "topic": TOPIC_EXECUTION},
  "risk_governor": {"module": "clawbots.risk_governor", "tier": 5, "topic": TOPIC_RISK},
}


# ============================================================
#  STARTUP VALIDATION
#  Warn (don't crash) when optional keys are missing so the
#  swarm can still run in degraded mode.
# ============================================================
_REQUIRED_KEYS = [
    ("ALPACA_API_KEY",  ALPACA_API_KEY,  "Alpaca trading/data will not work"),
    ("ALPACA_SECRET_KEY", ALPACA_SECRET_KEY, "Alpaca trading/data will not work"),
]
_OPTIONAL_KEYS = [
    ("SLACK_BOT_TOKEN",        SLACK_BOT_TOKEN,        "Slack alerts disabled"),
    ("UNUSUALWHALES_API_KEY",  UNUSUALWHALES_API_KEY,  "Whale flow agent disabled"),
    ("FINVIZ_API_KEY",         FINVIZ_API_KEY,         "Finviz scanner will use fallback"),
    ("FRED_API_KEY",           FRED_API_KEY,           "Macro context limited"),
    ("PERPLEXITY_API_KEY",     PERPLEXITY_API_KEY,     "Cloud LLM disabled, local-only"),
    ("DISCORD_BOT_TOKEN",      DISCORD_BOT_TOKEN,      "Discord listener disabled"),
    ("GIST_TOKEN",             GIST_TOKEN,             "AI Bridge disabled"),
    ("OPENCLAW_DB_PATH", OPENCLAW_DB_PATH, "Database trade logging uses default path"),
    ("ELITE_API_URL",           ELITE_API_URL,           "Elite Trading System bridge disabled"),
  ("STOCKGEIST_TOKEN",        STOCKGEIST_TOKEN,        "StockGeist sentiment disabled"),
  ("NEWS_API_KEY",            NEWS_API_KEY,            "News API disabled"),
  ("X_BEARER_TOKEN",          X_BEARER_TOKEN,          "X/Twitter sentiment disabled"),
]

_log = logging.getLogger("config")


def validate_config() -> list[str]:
    """Run at startup.  Returns list of warning strings."""
    warnings = []
    for name, val, msg in _REQUIRED_KEYS:
        if not val:
            _log.error("MISSING REQUIRED: %s - %s", name, msg)
            warnings.append(f"REQUIRED: {name} - {msg}")
    for name, val, msg in _OPTIONAL_KEYS:
        if not val:
            _log.warning("Missing optional: %s - %s", name, msg)
            warnings.append(f"optional: {name} - {msg}")
              # ── Bounds validation on critical numeric values ──
    _bounds = [
        ("MAX_DAILY_LOSS_PCT", MAX_DAILY_LOSS_PCT, 0, 10, "must be 0-10%"),
        ("DEFAULT_RISK_PCT", DEFAULT_RISK_PCT, 0, 5, "must be 0-5%"),
        ("MAX_PORTFOLIO_HEAT", MAX_PORTFOLIO_HEAT, 0, 0.5, "must be 0-50%"),
        ("MAX_POSITION_PCT", MAX_POSITION_PCT, 0, 0.25, "must be 0-25%"),
        ("MAX_DEPLOYED_PCT", MAX_DEPLOYED_PCT, 0, 1.0, "must be 0-100%"),
        ("CRASH_SPY_DROP", CRASH_SPY_DROP, 0, 0.2, "must be 0-20%"),
    ]
    for name, val, lo, hi, msg in _bounds:
        if not (lo <= val <= hi):
            _log.error("OUT OF RANGE: %s=%s  %s", name, val, msg)
            warnings.append(f"BOUNDS: {name}={val} {msg}")
    if ALPACA_API_KEY and ALPACA_SECRET_KEY:
        _log.info("Alpaca API configured (primary data publisher ready)")
    _log.info(
        "Config v6.0 loaded | %d agents registered | Alpaca feed=%s | regime=%s",
        len(AGENT_REGISTRY),
        ALPACA_FEED,
        "GREEN" if REGIME_GREEN_MIN else "unknown",
    )
    return warnings


def log_config_summary() -> None:
    """Log active features, API key presence, and regime settings at startup."""
    _log.info("=" * 60)
    _log.info("OpenClaw Config Summary v6.0")
    _log.info("=" * 60)
    # API keys (presence only, never values)
    _apis = {
        "Alpaca": bool(ALPACA_API_KEY),
        "Slack": bool(SLACK_BOT_TOKEN),
        "Discord": bool(DISCORD_BOT_TOKEN),
        "Perplexity": bool(PERPLEXITY_API_KEY),
        "UnusualWhales": bool(UNUSUALWHALES_API_KEY),
        "Finviz": bool(FINVIZ_API_KEY),
        "FRED": bool(FRED_API_KEY),
        "StockGeist": bool(STOCKGEIST_TOKEN),
        "NewsAPI": bool(NEWS_API_KEY),
    }
    for name, present in _apis.items():
        status = "ACTIVE" if present else "disabled"
        _log.info("  %-18s %s", name, status)
    # Regime settings
    _log.info("Regime: GREEN<=%s  YELLOW<=%s  Feed=%s",
              REGIME_GREEN_MIN, REGIME_YELLOW_MIN, ALPACA_FEED)
    # Risk limits
    _log.info("Risk: daily_loss=%.1f%%  risk_pct=%.1f%%  heat=%.1f%%",
              MAX_DAILY_LOSS_PCT, DEFAULT_RISK_PCT, MAX_PORTFOLIO_HEAT * 100)
    # Feature flags
    _log.info("Features: streaming=%s  auto_exec=%s  llm=%s  elite=%s  darwin=%s",
              STREAMING_ENABLED, AUTO_EXECUTE_ENABLED, LLM_ENABLED,
              ELITE_ENABLED, DARWIN_ENABLED)
    _log.info("Agents registered: %d", len(AGENT_REGISTRY))
    _log.info("=" * 60)
