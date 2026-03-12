"""
Embodier Trader - Application Configuration
All fields match EXACTLY what services reference via settings.FIELD_NAME
"""
import logging
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_log = logging.getLogger(__name__)

# Resolve .env relative to backend/ root (parent of app/core/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
    )

    # ── App ─────────────────────────────────────────────────
    APP_NAME: str = "Embodier Trader"
    PROJECT_NAME: str = "Embodier Trader"
    APP_VERSION: str = "4.1.0-dev"  # Single source of truth for version
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"
    TRADING_MODE: str = "paper"
    SCAN_INTERVAL_MINUTES: int = 5

    # ── API Authentication ────────────────────────────────
    API_AUTH_TOKEN: str = ""  # Set to enable Bearer token auth on state-changing endpoints

    # ── Server ──────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = Field(default=8000, alias="PORT")
    BACKEND_PORT: Optional[int] = None
    FRONTEND_PORT: int = 3000
    UVICORN_WORKERS: int = 4  # PC1: match P-cores (only used when DEBUG=False)
    # CORS: Set CORS_ORIGINS env var to add production/custom origins.
    # Localhost origins are always included (Electron app connects via localhost).
    CORS_ORIGINS: str = ""

    @property
    def effective_cors_origins(self) -> list[str]:
        """Return CORS origins as a list.

        Always includes localhost origins because the Electron desktop app
        loads from file:// and makes API calls to http://localhost:8000 /
        http://127.0.0.1:8000.  Browsers send a ``null`` Origin header for
        file:// pages, so we include ``"null"`` as well.

        In production, set CORS_ORIGINS to add any additional allowed
        origins (e.g. a hosted dashboard domain).  A warning is logged if
        CORS_ORIGINS is empty in production so operators are aware only
        localhost and null origins are permitted.
        """
        # Localhost / Electron defaults — always present
        localhost_origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:3002",
            "http://localhost:8501",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3002",
            "http://127.0.0.1:8501",
            "null",  # Electron file:// protocol sends Origin: null
        ]

        custom_origins = [
            o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()
        ] if self.CORS_ORIGINS else []

        if self.ENVIRONMENT == "production" and not custom_origins:
            _log.warning(
                "CORS_ORIGINS is empty in production. Only localhost and "
                "null (Electron file://) origins are allowed. Set "
                "CORS_ORIGINS to add external domains."
            )

        # Deduplicate while preserving order
        seen: set[str] = set()
        origins: list[str] = []
        for origin in custom_origins + localhost_origins:
            if origin not in seen:
                seen.add(origin)
                origins.append(origin)
        return origins

    @property
    def effective_port(self) -> int:
        """Return the port the backend should listen on."""
        return self.BACKEND_PORT if self.BACKEND_PORT is not None else self.PORT

    # ── Alpaca Markets ──────────────────────────────────────
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URL: str = "https://api.alpaca.markets"
    ALPACA_DATA_URL: str = "https://data.alpaca.markets"
    ALPACA_FEED: str = "iex"  # sip (real-time) | iex (free delayed)

    @property
    def APCA_API_KEY_ID(self) -> str:
        return self.ALPACA_API_KEY

    @property
    def APCA_API_SECRET_KEY(self) -> str:
        return self.ALPACA_SECRET_KEY

    # ── Multi-Key Alpaca Pool ─────────────────────────────
    ALPACA_KEY_1: str = ""
    ALPACA_SECRET_1: str = ""
    ALPACA_KEY_2: str = ""
    ALPACA_SECRET_2: str = ""
    ALPACA_KEY_3: str = ""
    ALPACA_SECRET_3: str = ""

    # ── FinViz ──────────────────────────────────────────────
    FINVIZ_API_KEY: str = ""
    FINVIZ_BASE_URL: str = "https://elite.finviz.com"
    FINVIZ_QUOTE_TIMEFRAME: str = "d"
    FINVIZ_SCREENER_FILTERS: str = "cap_midover,sh_avgvol_o500,sh_price_o10"
    FINVIZ_SCREENER_FILTER_TYPE: str = "4"
    FINVIZ_SCREENER_VERSION: str = "111"

    # ── FRED ────────────────────────────────────────────────
    FRED_API_KEY: str = ""
    FRED_BASE_URL: str = "https://api.stlouisfed.org/fred"

    # ── SEC Edgar ───────────────────────────────────────────
    SEC_EDGAR_USER_AGENT: str = ""

    # ── Unusual Whales ──────────────────────────────────────
    # Accepts both UNUSUAL_WHALES_API_KEY and UNUSUALWHALES_API_KEY from env
    UNUSUAL_WHALES_API_KEY: str = ""
    UNUSUAL_WHALES_BASE_URL: str = "https://api.unusualwhales.com/api"
    UNUSUALWHALES_API_KEY: str = ""  # OpenClaw compat alias

    # ── StockGeist (Sentiment) ──────────────────────────────
    STOCKGEIST_API_KEY: str = ""
    STOCKGEIST_BASE_URL: str = "https://api.stockgeist.ai"

    # ── News API ────────────────────────────────────────────
    NEWS_API_KEY: str = ""

    # ── YouTube Knowledge Agent ─────────────────────────────
    YOUTUBE_API_KEY: str = ""
    YOUTUBE_SEARCH_QUERY: str = "stock trading signals analysis"

    # ── Discord ─────────────────────────────────────────────
    DISCORD_BOT_TOKEN: str = ""
    DISCORD_USER_TOKEN: str = ""  # Self-bot token for channel reading
    DISCORD_CHANNEL_IDS: str = ""
    DISCORD_API_BASE: str = "https://discord.com/api/v10"
    DISCORD_UW_CHANNEL_ID: str = ""  # Unusual Whales channel
    DISCORD_UW_LIVE_CHANNEL_ID: str = ""  # UW Live channel
    DISCORD_FOM_CHANNEL_ID: str = ""  # FOM channel
    DISCORD_FOM_ZONES_CHANNEL_ID: str = ""  # FOM Zones channel
    DISCORD_FOM_IVOL_CHANNEL_ID: str = ""  # FOM IVOL channel
    DISCORD_EXPECTED_MOVES_CHANNEL_ID: str = ""  # Expected Moves channel
    DISCORD_MAVERICK_CHANNEL_ID: str = ""  # Maverick channel

    # ── X / Twitter ─────────────────────────────────────────
    X_API_KEY: str = ""  # Consumer key
    X_API_KEY_SECRET: str = ""  # Consumer secret
    X_OAUTH: str = ""
    X_OAUTH2_CLIENT_ID: str = ""
    X_OAUTH2_CLIENT_SECRET: str = ""
    X_BEARER_TOKEN: str = ""

    # ── Reddit ──────────────────────────────────────────────
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""

    # ── Slack ───────────────────────────────────────────────
    SLACK_BOT_TOKEN: str = ""
    SLACK_APP_TOKEN: str = ""
    SLACK_SIGNING_SECRET: str = ""
    SLACK_WEBHOOK_URL: str = ""
    OC_TRADE_DESK_CHANNEL: str = ""
    OC_SIGNALS_RAW_CHANNEL: str = ""
    SLACK_WEBHOOK_UW: str = ""
    SLACK_WEBHOOK_FOM: str = ""
    SLACK_WEBHOOK_MAV: str = ""
    SLACK_WEBHOOK_CHANNEL: str = ""

    # ── Benzinga ───────────────────────────────────────────
    BENZINGA_API_KEY: str = ""

    # ── Kelly Criterion Position Sizing ─────────────────────
    KELLY_DEFAULT_WIN_RATE: float = 0.55
    KELLY_DEFAULT_AVG_WIN: float = 1.5
    KELLY_DEFAULT_AVG_LOSS: float = 1.0
    KELLY_MAX_ALLOCATION: float = 0.25
    KELLY_USE_HALF: bool = True

    # ── Risk Management ─────────────────────────────────────
    MAX_PORTFOLIO_HEAT: float = 0.06
    MAX_SECTOR_CONCENTRATION: float = 0.30
    MIN_RISK_SCORE: float = 3.0
    VOLATILITY_BASELINE: float = 0.15

    # ── Database ────────────────────────────────────────────
    DATABASE_URL: str = "duckdb:///data/elite_trading.duckdb"

    # ── Efficiency / performance (EFFICIENCY-AND-HARDWARE-DESIGN.md) ──
    ASYNCIO_THREAD_POOL_WORKERS: int = 64  # Default executor for DuckDB/blocking work
    FEATURE_AGGREGATOR_WORKERS: int = 4    # Parallel DuckDB fetches per feature build (6–8 on i9)
    BAR_BUFFER_FLUSH_SEC: float = 5.0      # Seconds between DuckDB bar batch writes

    # ── Google Sheets ───────────────────────────────────────
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = ""
    GOOGLE_SHEETS_SPREADSHEET_ID: str = ""

    # ── Telegram Alerts ─────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ── Email / Resend ──────────────────────────────────────
    EMAIL_SENDER: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_RECIPIENT: str = ""
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "alerts@elite-trading.dev"
    RESEND_ALERT_TO_EMAIL: str = ""

    # ── OpenClaw (Multi-Agent) ──────────────────────────────
    OPENCLAW_ENABLED: bool = True
    OPENCLAW_BRIDGE_TOKEN: str = ""  # Auth token for OpenClaw bridge
    GIST_TOKEN: str = ""  # GitHub Gist token for AI bridge
    BRIDGE_GIST_ID: str = ""  # Gist ID for bridge sync
    OLLAMA_BASE_URL: str = "http://localhost:11434"  # Backward compat; prefer OLLAMA_URL for PC1 fallback

    # ── Cluster / PC Role ───────────────────────────────────
    # PC_ROLE controls which Alpaca keys this machine uses for WebSocket/REST:
    #   "primary"   — PC1 (ESPENMAIN): Key 1 (trading), serves frontend/API
    #   "secondary" — PC2 (ProfitTrader): Key 2 (discovery scanning), runs brain_service
    # If unset, defaults to "primary" (single-PC mode).
    PC_ROLE: str = "primary"

    # ── Canonical LLM contract ─────────────────────────────
    # PC2: Brain Service (gRPC) — primary trading intelligence entrypoint
    BRAIN_SERVICE_URL: str = ""  # e.g. localhost:50051; empty = derive from BRAIN_HOST:BRAIN_PORT
    BRAIN_ENABLED: bool = True
    BRAIN_HOST: str = "localhost"
    BRAIN_PORT: int = 50051
    # PC1 fallback: local Ollama when Brain Service unreachable (Electron: process/health only; no trading logic)
    OLLAMA_URL: str = ""  # Empty = use OLLAMA_BASE_URL (e.g. http://localhost:11434)
    OLLAMA_MODEL: str = "mistral:7b"

    # ── Multi-LLM Intelligence Layer ─────────────────────
    PERPLEXITY_API_KEY: str = ""
    PERPLEXITY_BASE_URL: str = "https://api.perplexity.ai"
    PERPLEXITY_MODEL: str = "sonar-pro"
    PERPLEXITY_ENABLED: bool = True
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    LOCAL_LLM_MODEL: str = "qwen2.5:14b"
    LLM_ENABLED: bool = True
    LLM_PREFER_LOCAL: bool = True
    LLM_ROUTER_ENABLED: bool = True
    LLM_COST_TRACKING: bool = True

    # ── Dual-PC Ollama Configuration ──────────────────────
    OLLAMA_PC2_URL: str = "http://localhost:11434"  # PC-2 endpoint (set to PC-2 IP for dual-PC)
    OLLAMA_SMALL_MODEL: str = "mistral:7b"          # PC-1: fast, <200ms, ~4GB VRAM
    OLLAMA_LARGE_MODEL: str = "qwen2.5:32b"           # PC-2: complex, ~20GB VRAM

    # ── Cluster / Multi-PC ────────────────────────────────
    CLUSTER_PC2_HOST: str = ""  # Empty = single-PC mode
    CLUSTER_HEALTH_INTERVAL: int = 60  # Seconds between health checks

    # ── Redis (Cross-PC MessageBus Bridge) ────────────────
    # Set to enable real-time pub/sub between PC1 and PC2.
    # Leave empty for local-only MessageBus (single-PC mode).
    REDIS_URL: str = ""  # e.g., redis://192.168.1.105:6379/0
    SCANNER_OLLAMA_URLS: str = "http://localhost:11434,http://192.168.1.116:11434"

    # ── GPU Telemetry ─────────────────────────────────────
    GPU_TELEMETRY_ENABLED: bool = True
    GPU_TELEMETRY_INTERVAL: float = 3.0  # Seconds between telemetry broadcasts
    GPU_VRAM_HEADROOM_MB: int = 512  # Reserve this much VRAM as buffer

    # ── Model Pinning (Asymmetric Routing) ────────────────
    # PC1 (Master / Rapid Responder): fast tactical models
    MODEL_PIN_PC1: str = "mistral:7b"  # Comma-separated models pinned to PC1
    # PC2 (Heavy Compute): deep thinking models
    MODEL_PIN_PC2: str = "qwen2.5:14b,qwen2.5:32b,deepseek-r1:8b"  # Comma-separated models pinned to PC2
    # Task → node affinity (task:node pairs, comma-separated)
    # Tasks: regime_classification,signal_scoring,risk_check → pc1
    # Tasks: trade_thesis,strategy_critic,deep_postmortem → pc2
    MODEL_PIN_TASK_AFFINITY: str = "regime_classification:pc1,signal_scoring:pc1,risk_check:pc1,quick_hypothesis:pc1,feature_summary:pc1,trade_thesis:pc2,strategy_critic:pc2,deep_postmortem:pc2,strategy_evolution:pc2,overnight_analysis:pc2"

    # ── LLM Dispatcher ────────────────────────────────────
    LLM_DISPATCHER_ENABLED: bool = True
    LLM_DISPATCHER_HEARTBEAT_TIMEOUT: int = 3  # Missed heartbeats before marking OFFLINE
    LLM_DISPATCHER_FALLBACK_MODEL: str = "mistral:7b"  # Downgrade to this when PC2 dies
    LLM_DISPATCHER_GPU_UTIL_THRESHOLD: float = 85.0  # Route away if GPU util > this %

    # ── Adaptive Router Settings ──────────────────────────
    ADAPTIVE_ROUTING_ENABLED: bool = True
    ROUTING_ACCURACY_THRESHOLD: float = 0.45   # escalate if accuracy below this
    ROUTING_MIN_CALLS: int = 10                # min calls before adaptive kicks in
    ROUTING_MONTHLY_BUDGET_USD: float = 100.0  # cloud API monthly budget cap
    ROUTING_TIMEOUT_BRAINSTEM: float = 10.0
    ROUTING_TIMEOUT_CORTEX: float = 15.0
    ROUTING_TIMEOUT_DEEP: float = 30.0

    # ── Debate Engine Settings ────────────────────────────
    DEBATE_ENABLED: bool = True
    DEBATE_MAX_ROUNDS: int = 3
    DEBATE_CONFIDENCE_SPREAD_THRESHOLD: float = 0.7

    # ── Knowledge System Settings ─────────────────────────
    KNOWLEDGE_SYSTEM_ENABLED: bool = True
    KNOWLEDGE_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    KNOWLEDGE_HEURISTIC_MIN_SAMPLE: int = 25
    KNOWLEDGE_HEURISTIC_MIN_WIN_RATE: float = 0.55

    # ── Council ────────────────────────────────────────────
    COUNCIL_ENABLED: bool = True

    # ── Execution Realism ──────────────────────────────────
    SLIPPAGE_BPS: float = 5.0
    PARTIAL_FILL_ENABLED: bool = True
    FILL_SEED: int = 0  # 0 = random

    # ── Scheduler ──────────────────────────────────────────
    SCHEDULER_ENABLED: bool = True

    # ── Risk Guardrails (additional) ───────────────────────
    MAX_SINGLE_POSITION: float = 0.02
    MAX_DAILY_LOSS_PCT: float = 2.0
    DEFAULT_RISK_PCT: float = 1.5
    CIRCUIT_BREAKER_THRESHOLD: float = -0.03
    ATR_STOP_MULTIPLIER: float = 2.0
    MAX_DAILY_DRAWDOWN_PCT: float = 5.0
    AUTO_PAUSE_TRADING: bool = True
    TRAILING_STOP_PCT: float = 0.03
    MAX_POSITION_PCT: float = 0.10
    SIGNAL_BUY_THRESHOLD: float = 0.60
    SIGNAL_STRONG_BUY_THRESHOLD: float = 0.75
    SIGNAL_MIN_EDGE: float = 0.05
    SIGNAL_MIN_VOLUME_SCORE: float = 0.5
    AUTO_EXECUTE_TRADES: bool = False
    AUTO_EXECUTE_ENABLED: bool = True
    MAX_DAILY_TRADES: int = 10

    # ── StockGeist Aliases (OpenClaw compat) ───────────────
    STOCKGEIST_TOKEN: str = ""  # alias for STOCKGEIST_API_KEY
    STOCKGEIST_AUTH: str = ""  # alternate auth header

    # ── Streaming / Signals ────────────────────────────────
    STREAMING_ENABLED: bool = True
    STREAMING_BAR_TIMEFRAME: str = "1Min"
    SCORE_TRIGGER_THRESHOLD: int = 75

    # ── Encryption ─────────────────────────────────────────
    FERNET_KEY: str = ""  # Fernet symmetric key for encrypting stored secrets

    # ── API Auth Token ──────────────────────────────────────
    # (moved up for clarity but kept here as well for reference)

    # ── TradingView ────────────────────────────────────────
    TRADINGVIEW_WEBHOOK_SECRET: str = ""
    TRADINGVIEW_WEBHOOK_URL: str = ""

    # ── WebSocket ──────────────────────────────────────────
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 100

    # ── ML Engine ───────────────────────────────────────────
    ML_MODEL_DIR: str = "data/models"
    ML_RETRAIN_INTERVAL_HOURS: int = 168
    ML_ENSEMBLE_ENABLED: bool = True

    # ── Outcome / Learning integrity ────────────────────────
    # Shadow timeout policy: "timeout_censored" (do not count toward win/loss/Kelly/weights)
    # or "mark_to_market" (resolve at last known price; requires reliable price source)
    OUTCOME_TIMEOUT_POLICY: str = "mark_to_market"

    # ── Degraded mode (real-time truth for operator) ─────────
    # When True, OrderExecutor may AUTO-execute even if brain reports degraded (use with caution).
    DEGRADED_MODE_OVERRIDE: bool = False

    # ── Profit-brain alignment / pipeline enforcement ────────
    # Enforce typed event contracts and reject malformed pipeline payloads.
    ENFORCE_CANONICAL_PIPELINE: bool = True
    # Block any execution path that does not carry an approved ExecutionDecision (council + sizing + risk).
    BLOCK_EXECUTION_WITHOUT_COUNCIL: bool = True
    # Durable idempotent outcome resolution; explicit unresolved/timeout statuses.
    STRICT_OUTCOME_INTEGRITY: bool = True
    # Learner accepts only valid/attributable outcomes; drop low-quality with audit.
    STRICT_LEARNER_INPUTS: bool = True
    # Startup fails (or hard-degraded) if critical pipeline topics lack required subscribers.
    FAIL_ON_CRITICAL_SUBSCRIBER_MISSING: bool = False
    # Portfolio-level hard limits (exposure, concentration, daily loss, drawdown).
    ENABLE_PORTFOLIO_RISK_GOVERNOR: bool = True
    # Pre-trade slippage/liquidity viability gate (deny when expected cost > edge).
    ENABLE_EXECUTION_VIABILITY_GATE: bool = True
    # Outbox/inbox + idempotency for critical stage transitions.
    ENABLE_EXACTLY_ONCE_CRITICAL_EVENTS: bool = False
    # Stamp verdict/execution/outcome with strategy/model/config version.
    ENABLE_STRATEGY_VERSION_PINNING: bool = False
    # Global kill switch: block new entries; optional flatten mode.
    ENABLE_KILL_SWITCH: bool = True


settings = Settings()

# Unify Unusual Whales env var names (UNUSUAL_WHALES_API_KEY <-> UNUSUALWHALES_API_KEY)
if settings.UNUSUALWHALES_API_KEY and not settings.UNUSUAL_WHALES_API_KEY:
    settings.UNUSUAL_WHALES_API_KEY = settings.UNUSUALWHALES_API_KEY
elif settings.UNUSUAL_WHALES_API_KEY and not settings.UNUSUALWHALES_API_KEY:
    settings.UNUSUALWHALES_API_KEY = settings.UNUSUAL_WHALES_API_KEY

# Unify StockGeist aliases (STOCKGEIST_API_KEY <-> STOCKGEIST_TOKEN <-> STOCKGEIST_AUTH)
_sg = settings.STOCKGEIST_API_KEY or settings.STOCKGEIST_TOKEN or settings.STOCKGEIST_AUTH
if _sg:
    if not settings.STOCKGEIST_API_KEY:
        settings.STOCKGEIST_API_KEY = _sg
    if not settings.STOCKGEIST_TOKEN:
        settings.STOCKGEIST_TOKEN = _sg
    if not settings.STOCKGEIST_AUTH:
        settings.STOCKGEIST_AUTH = _sg

# Production safety: validate critical keys when in live trading mode
if settings.TRADING_MODE.lower() == "live":
    _missing = []
    if not settings.ALPACA_API_KEY:
        _missing.append("ALPACA_API_KEY")
    if not settings.ALPACA_SECRET_KEY:
        _missing.append("ALPACA_SECRET_KEY")
    if not settings.API_AUTH_TOKEN:
        _missing.append("API_AUTH_TOKEN")
    if _missing:
        raise RuntimeError(
            f"LIVE trading mode requires: {', '.join(_missing)}. "
            f"Set these environment variables and restart, or use TRADING_MODE=paper."
        )
