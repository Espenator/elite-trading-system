"""Application configuration using pydantic-settings.

APEX Phase 2 additions:
- GPU_DEVICE, TORCH_MIXED_PRECISION  (PyTorch / LSTM trainer)
- XGBOOST_GPU_ID                     (XGBoost trainer)
- TRAINING_SCHEDULE                  (cron expression for scheduled retraining)
- MODEL_ARTIFACTS_PATH               (where trained models are saved)
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Embodier.ai Trading Intelligence"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8001
    HOST: str = "0.0.0.0"

    # Finviz API  -- set in .env
    FINVIZ_API_KEY: str = ""
    FINVIZ_BASE_URL: str = "https://elite.finviz.com"

    # Screener filters (comma-separated, e.g., "cap_midover,sh_avgvol_o500,sh_price_o10")
    FINVIZ_SCREENER_FILTERS: str = "cap_midover,sh_avgvol_o500,sh_price_o10"
    FINVIZ_SCREENER_VERSION: str = "111"
    FINVIZ_SCREENER_FILTER_TYPE: str = "4"

    # Quote/Chart settings
    FINVIZ_QUOTE_TIMEFRAME: str = "d"  # d=daily, w=weekly, m=monthly, etc.

    # -----------------------------------------------------------------------
    # OpenClaw Bridge (PC1 -> PC2)
    # -----------------------------------------------------------------------
    OPENCLAW_BRIDGE_TOKEN: str = ""  # Shared secret for X-OpenClaw-Token header
    OPENCLAW_BRIDGE_SECRET: str = ""  # HMAC-SHA256 secret for bridge signature verification
    OPENCLAW_API_URL: str = (
        ""  # URL of OpenClaw API on PC1 (e.g., http://192.168.x.x:5000)
    )

    # -----------------------------------------------------------------------
    # GPU / CUDA (APEX Phase 2)
    # -----------------------------------------------------------------------
    GPU_DEVICE: str = "auto"  # "auto" | "cuda:0" | "cuda:1" | "cpu"
    TORCH_MIXED_PRECISION: bool = True  # Enable AMP (FP16) when CUDA available
    XGBOOST_GPU_ID: int = 0  # GPU device ordinal for XGBoost gpu_hist

    # -----------------------------------------------------------------------
    # Training schedule & artefacts (APEX Phase 2)
    # -----------------------------------------------------------------------
    TRAINING_SCHEDULE: str = "0 2 * * 6"  # cron: every Saturday at 02:00 UTC
    MODEL_ARTIFACTS_PATH: str = (
        "models/artifacts"  # directory for checkpoints & metadata
    )

    # -----------------------------------------------------------------------
    # DuckDB
    # -----------------------------------------------------------------------
    DUCKDB_PATH: str = "elite_trading.duckdb"

    # Alpaca Markets API -- set in .env; paper by default
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets/v2"
    TRADING_MODE: str = (
        "paper"  # "paper" | "live" -- only use "live" when explicitly ready
    )

    # FRED (Federal Reserve Economic Data) -- set in .env
    FRED_API_KEY: str = ""

    # Unusual Whales (options flow) -- set in .env
    UNUSUAL_WHALES_API_KEY: str = ""
    UNUSUAL_WHALES_BASE_URL: str = "https://api.unusualwhales.com"
    UNUSUAL_WHALES_FLOW_PATH: str = (
        ""  # Default /api/option-trades/flow-alerts; override if needed
    )

    # SEC EDGAR -- no key; User-Agent required (set in code)

    # Sentiment Agent / Social News Engine -- set in .env; returns empty list if not configured
    NEWS_API_KEY: str = ""
    STOCKGEIST_API_KEY: str = ""
    STOCKGEIST_BASE_URL: str = "https://api.stockgeist.ai"
    DISCORD_BOT_TOKEN: str = ""
    DISCORD_API_BASE: str = "https://discord.com/api/v10"
    # Discord channel IDs to monitor (comma-separated)
    DISCORD_CHANNEL_IDS: str = ""

    # X (Twitter) API -- OAuth 2.0 client credentials; set in .env
    X_API_KEY: str = ""
    X_API_KEY_SECRET: str = ""
    X_OAUTH2_CLIENT_ID: str = ""
    X_OAUTH2_CLIENT_SECRET: str = ""

    # YouTube Knowledge Agent -- set in .env
    YOUTUBE_API_KEY: str = ""
    YOUTUBE_SEARCH_QUERY: str = (
        "stock market trading technical analysis"  # Used when only API key is set
    )

    # Resend -- transactional email for risk/alert notifications; set in .env
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""  # Must be a verified domain in Resend
    RESEND_ALERT_TO_EMAIL: str = (
        ""  # Default recipient for test and risk alerts
    )

    # OpenClaw Bridge -- reads scan data from GitHub Gist; set in .env
    OPENCLAW_GIST_ID: str = ""
    OPENCLAW_GIST_TOKEN: str = (
        ""  # GitHub personal access token with gist scope (optional for public gists)
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
