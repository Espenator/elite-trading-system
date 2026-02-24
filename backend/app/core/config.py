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

    # -----------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------
    APP_NAME: str = "Elite Trading System API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8001
    HOST: str = "0.0.0.0"

    # -----------------------------------------------------------------------
    # Finviz API
    # -----------------------------------------------------------------------
    FINVIZ_API_KEY: str = ""
    FINVIZ_BASE_URL: str = "https://elite.finviz.com"

    # Screener filters (comma-separated, e.g., "cap_midover,sh_avgvol_o500,sh_price_o10")
    FINVIZ_SCREENER_FILTERS: str = "cap_midover,sh_avgvol_o500,sh_price_o10"
    FINVIZ_SCREENER_VERSION: str = "111"
    FINVIZ_SCREENER_FILTER_TYPE: str = "4"

    # Quote/Chart settings
    FINVIZ_QUOTE_TIMEFRAME: str = "d"  # d=daily, w=weekly, m=monthly, etc.

    # -----------------------------------------------------------------------
    # Alpaca Markets API - paper by default; set TRADING_MODE=live for real money
    # -----------------------------------------------------------------------
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URI: str = "https://paper-api.alpaca.markets/v2"
    TRADING_MODE: str = "paper"  # "paper" | "live" - only use "live" when explicitly ready

    # -----------------------------------------------------------------------
    # OpenClaw Bridge (PC1 -> PC2)
    # -----------------------------------------------------------------------
    OPENCLAW_BRIDGE_TOKEN: str = ""  # Shared secret for X-OpenClaw-Token header
    OPENCLAW_API_URL: str = ""  # URL of OpenClaw API on PC1 (e.g., http://192.168.x.x:5000)

    # -----------------------------------------------------------------------
    # GPU / CUDA  (APEX Phase 2)
    # -----------------------------------------------------------------------
    GPU_DEVICE: str = "auto"  # "auto" | "cuda:0" | "cuda:1" | "cpu"
    TORCH_MIXED_PRECISION: bool = True  # Enable AMP (FP16) when CUDA available
    XGBOOST_GPU_ID: int = 0  # GPU device ordinal for XGBoost gpu_hist

    # -----------------------------------------------------------------------
    # Training schedule & artefacts  (APEX Phase 2)
    # -----------------------------------------------------------------------
    TRAINING_SCHEDULE: str = "0 2 * * 6"  # cron: every Saturday at 02:00 UTC
    MODEL_ARTIFACTS_PATH: str = "models/artifacts"  # directory for checkpoints & metadata

    # -----------------------------------------------------------------------
    # DuckDB
    # -----------------------------------------------------------------------
    DUCKDB_PATH: str = "elite_trading.duckdb"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
