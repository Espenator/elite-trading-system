"""Application configuration using pydantic-settings."""

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

    # Finviz API
    FINVIZ_API_KEY: str = "4475cd42-70ea-4fa7-9630-0d9cd30d9620"
    FINVIZ_BASE_URL: str = "https://elite.finviz.com"

    # Screener filters (comma-separated, e.g., "cap_midover,sh_avgvol_o500,sh_price_o10")
    FINVIZ_SCREENER_FILTERS: str = "cap_midover,sh_avgvol_o500,sh_price_o10"
    FINVIZ_SCREENER_VERSION: str = "111"
    FINVIZ_SCREENER_FILTER_TYPE: str = "4"

    # Quote/Chart settings
    FINVIZ_QUOTE_TIMEFRAME: str = "d"  # d=daily, w=weekly, m=monthly, etc.

    # Alpaca Markets API — paper by default; set TRADING_MODE=live for real money
    ALPACA_API_KEY: str = "PKA72MJTJGEH66R3WVAMMTCKVT"
    ALPACA_SECRET_KEY: str = "2Tfr9sYKD6qDuZVaxdJ9HRSJYQBsRSDVUxTUtyqazEXP"
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets/v2"
    TRADING_MODE: str = (
        "paper"  # "paper" | "live" — only use "live" when explicitly ready
    )

    # FRED (Federal Reserve Economic Data) — free key at https://fred.stlouisfed.org/docs/api/api_key.html
    FRED_API_KEY: str = "efc9fe2858156b124be8b1d8fd212194"

    # Unusual Whales (options flow) — optional; set base URL and key if you have access
    UNUSUAL_WHALES_API_KEY: str = "d1cb154c-7988-41c6-ac00-09379ae7395c"
    UNUSUAL_WHALES_BASE_URL: str = "https://api.unusualwhales.com"
    UNUSUAL_WHALES_FLOW_PATH: str = (
        ""  # Default /api/option-trades/flow-alerts; override if needed
    )

    # SEC EDGAR — no key; User-Agent required (set in code)

    # Sentiment Agent / Social News Engine — optional; leave empty to use mock data
    NEWS_API_KEY: str = "9cb9b9e539434885bfd023ce5c60d90b"
    STOCKGEIST_API_KEY: str = "vbtig3q2xPB0EJyLerT5yx7ZgDh8agEG"
    STOCKGEIST_BASE_URL: str = "https://api.stockgeist.ai"
    DISCORD_BOT_TOKEN: str = (
        "MTE1Mzc1ODM2OTg1NzkzMzM4Mg.Gtkvds.ZO4Wfy3SnZSWpeDmVnMWr42O0YlyUmmecevy7E"
    )
    DISCORD_API_BASE: str = "https://discord.com/api/v10"
    # Discord channel IDs to monitor (comma-separated). Names: UW Free/Live Options Flow, FOM Trade Ideas, FOM Daily Expected Moves, FOM Zones, FOM Daily IVOL Alerts, Maverick Live Market Trading
    DISCORD_CHANNEL_IDS: str = (
        "1186354600622694400,1187484002844680354,850211054549860352,1097299537758003201,998705356882595840,1430213250645102602,1051968098506379265"
    )
    # X (Twitter) API — OAuth 2.0 client credentials for app-only read (client ID + secret)
    X_API_KEY: str = "xqJifauJmwyqJGmC1EV2fx3fF"
    X_API_KEY_SECRET: str = "kGuRa9RvBS98bT1AReIh0r8poq81XPLfID3Thi98ssYSFyngAT"
    X_OAUTH2_CLIENT_ID: str = "X3hzWHh1YkVocGZ1YUMzTVBzcnM6MTpjaQ"
    X_OAUTH2_CLIENT_SECRET: str = "8W6omW9jlhwHwipTO5f1FicHec_aWH--wwYXvQZcrVaK9-eByS"

    # YouTube Knowledge Agent — only YOUTUBE_API_KEY required; search discovers videos if no channels/IDs set
    YOUTUBE_API_KEY: str = "AIzaSyCn1B6rIYvhyoXsomXl4ZcyQIV7VbTbEkk"
    YOUTUBE_SEARCH_QUERY: str = (
        "stock market trading technical analysis"  # Used when only API key is set
    )

    # Resend — transactional email for risk/alert notifications
    RESEND_API_KEY: str = (
        "re_UFqqo1oe_DfMEofzkEgAyPM9uXmQH1CVA"  # Set in .env (e.g. re_xxx); required to send emails
    )
    RESEND_FROM_EMAIL: str = "Espen@embodier.ai"  # Must be a verified domain in Resend
    RESEND_ALERT_TO_EMAIL: str = (
        "Espen@embodier.ai"  # Default recipient for test and risk alerts (e.g. you@company.com)
    )

    # OpenClaw Bridge — reads scan data from GitHub Gist produced by OpenClaw api_data_bridge.py
    OPENCLAW_GIST_ID: str = (
        "725e68ffca84638fa267db8361f4c14f"  # GitHub Gist ID where OpenClaw pushes scan JSON
    )
    OPENCLAW_GIST_TOKEN: str = (
        "ghp_ppv6dafG7dmrcgkFhaBlkhxoHKgKkg2U5lI4"  # GitHub personal access token with gist scope (optional for public gists)
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
