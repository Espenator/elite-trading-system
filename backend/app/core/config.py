"""
Elite Trading System - Application Configuration
All fields match EXACTLY what services reference via settings.FIELD_NAME
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    APP_NAME: str = "Elite Trading System"
    PROJECT_NAME: str = "Elite Trading System"
    APP_VERSION: str = "3.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    TRADING_MODE: str = "paper"
    SCAN_INTERVAL_MINUTES: int = 5

    # ── API Authentication ────────────────────────────────
    API_AUTH_TOKEN: str = ""  # Set to enable Bearer token auth on state-changing endpoints

    # ── Server ──────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8501"

    # ── Alpaca Markets ──────────────────────────────────────
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"
    ALPACA_DATA_URL: str = "https://data.alpaca.markets"

    @property
    def APCA_API_KEY_ID(self) -> str:
        return self.ALPACA_API_KEY

    @property
    def APCA_API_SECRET_KEY(self) -> str:
        return self.ALPACA_SECRET_KEY

    # ── FinViz ──────────────────────────────────────────────
    FINVIZ_API_KEY: str = ""
    FINVIZ_BASE_URL: str = "https://elite.finviz.com"
    FINVIZ_QUOTE_TIMEFRAME: str = "d"
    FINVIZ_SCREENER_FILTERS: str = "sh_avgvol_o500,sh_price_u500"
    FINVIZ_SCREENER_FILTER_TYPE: str = "all"
    FINVIZ_SCREENER_VERSION: str = "2"

    # ── FRED ────────────────────────────────────────────────
    FRED_API_KEY: str = ""
    FRED_BASE_URL: str = "https://api.stlouisfed.org/fred"

    # ── SEC Edgar ───────────────────────────────────────────
    SEC_EDGAR_USER_AGENT: str = ""

    # ── Unusual Whales ──────────────────────────────────────
    UNUSUAL_WHALES_API_KEY: str = ""
    UNUSUAL_WHALES_BASE_URL: str = "https://api.unusualwhales.com/api"

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
    DISCORD_CHANNEL_IDS: str = ""
    DISCORD_API_BASE: str = "https://discord.com/api/v10"

    # ── X / Twitter ─────────────────────────────────────────
    X_OAUTH: str = ""

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
    OPENCLAW_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ── Brain Service (PC2) ───────────────────────────────
    BRAIN_ENABLED: bool = False
    BRAIN_HOST: str = "localhost"
    BRAIN_PORT: int = 50051
    OLLAMA_MODEL: str = "llama3.2"

    # ── Multi-LLM Intelligence Layer ─────────────────────
    PERPLEXITY_API_KEY: str = ""
    PERPLEXITY_BASE_URL: str = "https://api.perplexity.ai"
    PERPLEXITY_MODEL: str = "sonar-pro"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    LLM_ROUTER_ENABLED: bool = True
    LLM_COST_TRACKING: bool = True

    # ── Council ────────────────────────────────────────────
    COUNCIL_ENABLED: bool = True

    # ── Execution Realism ──────────────────────────────────
    SLIPPAGE_BPS: float = 5.0
    PARTIAL_FILL_ENABLED: bool = True
    FILL_SEED: int = 0  # 0 = random

    # ── Scheduler ──────────────────────────────────────────
    SCHEDULER_ENABLED: bool = False

    # ── Risk Guardrails (additional) ───────────────────────
    MAX_SINGLE_POSITION: float = 0.02

    # ── ML Engine ───────────────────────────────────────────
    ML_MODEL_DIR: str = "data/models"
    ML_RETRAIN_INTERVAL_HOURS: int = 168


settings = Settings()

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
        raise ValueError(
            f"Live trading mode requires these env vars: {', '.join(_missing)}. "
            "Set them in .env or switch TRADING_MODE=paper."
        )
