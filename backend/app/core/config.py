"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Elite Trading System API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8001
    HOST: str = "0.0.0.0"
    
    # Finviz API
    FINVIZ_API_KEY: str = ""
    FINVIZ_BASE_URL: str = "https://elite.finviz.com"
    
    # Screener filters (comma-separated, e.g., "cap_midover,sh_avgvol_o500,sh_price_o10")
    FINVIZ_SCREENER_FILTERS: str = "cap_midover,sh_avgvol_o500,sh_price_o10"
    FINVIZ_SCREENER_VERSION: str = "111"
    FINVIZ_SCREENER_FILTER_TYPE: str = "4"
    
    # Quote/Chart settings
    FINVIZ_QUOTE_TIMEFRAME: str = "d"  # d=daily, w=weekly, m=monthly, etc.
    
    # Alpaca Markets API — paper by default; set TRADING_MODE=live for real money
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets/v2"
    TRADING_MODE: str = "paper"  # "paper" | "live" — only use "live" when explicitly ready
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()

