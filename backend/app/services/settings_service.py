"""Settings service — DuckDB-backed, migration-safe, real validation.

Manages all settings for the Embodier Trader across 18 categories:
trading, risk, dataSources, notifications, ml, agents, system, etc.
Persisted in DuckDB settings table with auto-creation.

When API keys are updated via the Settings UI, changes propagate to:
  1. DuckDB (persisted settings)
  2. Runtime `settings` object (app.core.config.settings)
  3. The backend/.env file (so next restart also picks them up)
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings, _ENV_FILE
from app.services.database import db_service


DEFAULTS: Dict[str, Dict[str, Any]] = {
    "trading": {
        "tradingMode": "live",
        "defaultOrderType": "market",
        "maxPositionSize": 10000,
        "maxDailyTrades": 20,
        "autoExecute": True,
        "confirmBeforeOrder": True,
        "marketOpen": "09:30",
        "marketClose": "16:00",
        "preMarketEnabled": False,
        "afterHoursEnabled": False,
        "entryMethod": "signal",
    },
    "risk": {
        "maxPortfolioRisk": 0.06,
        "maxPositionRisk": 0.02,
        "stopLossDefault": 0.03,
        "takeProfitDefault": 0.06,
        "kellyFractionMultiplier": 0.5,
        "maxDrawdownLimit": 0.10,
        "riskPerTrade": 0.01,
        "atrStopMultiplier": 2.0,
        "circuitBreakerEnabled": True,
        "maxPositions": 15,
        "positionSizePct": 2.0,
        "maxDailyLossPct": 5.0,
    },
    "kelly": {
        "kellyMaxAllocation": 0.10,
        "kellyDefaultWinRate": 0.55,
        "kellyUseHalf": True,
        "kellyDefaultAvgWin": 0.035,
        "kellyDefaultAvgLoss": 0.015,
        "maxPortfolioHeat": 0.25,
        "maxSectorConcentration": 0.25,
    },
    "dataSources": {
        # Alpaca Markets
        "alpacaApiKey": "",
        "alpacaSecretKey": "",
        "alpacaBaseUrl": "paper",
        "alpacaFeed": "iex",
        # Market Data
        "unusualWhalesApiKey": "",
        "finvizApiKey": "",
        "fredApiKey": "",
        "newsApiKey": "",
        "benzingaApiKey": "",
        "stockgeistApiKey": "",
        "youtubeApiKey": "",
        "secEdgarUserAgent": "Embodier.ai espen@embodier.ai",
        # Social / Communication
        "xApiKey": "",
        "xApiKeySecret": "",
        "xOAuth2ClientId": "",
        "xOAuth2ClientSecret": "",
        "xBearerToken": "",
        "redditClientId": "",
        "redditClientSecret": "",
        # Discord
        "discordBotToken": "",
        "discordUserToken": "",
        "discordUwChannelId": "",
        "discordUwLiveChannelId": "",
        "discordFomChannelId": "",
        "discordFomZonesChannelId": "",
        "discordFomIvolChannelId": "",
        "discordExpectedMovesChannelId": "",
        "discordMaverickChannelId": "",
        # Slack
        "slackBotToken": "",
        "slackAppToken": "",
        "slackWebhookUrl": "",
        # Email / Resend
        "resendApiKey": "",
        "resendFromEmail": "alerts@embodier.ai",
        "resendAlertToEmail": "espen@embodier.ai",
        # LLM (Cloud)
        "perplexityApiKey": "",
        "anthropicApiKey": "",
        # OpenClaw Bridge
        "openclawBridgeToken": "",
        # Auth / Encryption
        "apiAuthToken": "",
        "fernetKey": "",
        # Misc
        "refreshIntervalSeconds": 300,
    },
    "notifications": {
        "discordWebhookUrl": "",
        "slackWebhookUrl": "",
        "slackWebhookUw": "",
        "slackWebhookFom": "",
        "slackWebhookMav": "",
        "slackWebhookChannel": "",
        "telegramBotToken": "",
        "telegramChatId": "",
        "tradeAlerts": True,
        "riskAlerts": True,
        "dailySummary": True,
        "agentStatusAlerts": False,
        "signalAlerts": True,
    },
    "ml": {
        "modelType": "xgboost",
        "retrainFrequency": "weekly",
        "confidenceThreshold": 0.65,
        "featureSet": ["price", "volume", "rsi", "macd", "vwap", "rvol"],
        "walkForwardWindow": 60,
        "driftDetectionEnabled": True,
        "driftThreshold": 0.15,
        "minCompositeScore": 60,
        "minMLConfidence": 40,
    },
    "agents": {
        "openclawEnabled": True,
        "maxConcurrentAgents": 4,
        "agentTimeout": 30,
        "autoRestart": True,
        "scannerInterval": 300,
        "marketDataAgent": True,
        "riskAgent": True,
        "signalEngine": True,
        "patternAI": True,
        "youtubeAgent": True,
        "driftMonitor": True,
        "flywheelEngine": True,
        "openclawBridge": True,
    },
    "openclaw": {
        "openclawWsUrl": "",
        "openclawApiKey": "",
        "openclawReconnectInterval": 5,
        "openclawEnabled": True,
    },
    "ollama": {
        "ollamaHostUrl": "http://localhost:11434",
        "ollamaDefaultModel": "llama3.2",
        "ollamaContextLength": 4096,
        "ollamaGpuDevice": "auto",
        "ollamaCudaEnabled": True,
        "duckdbPath": "elite_trading.duckdb",
        "activeModels": ["llama3.2", "mistral", "deepseek-r1"],
    },
    "tradingview": {
        "webhookKey": "",
        "alertFormat": "json",
        "chartTheme": "dark",
    },
    "finvizScreener": {
        "finvizFilters": "cap_midover,sh_avgvol_o500,sh_price_o10",
        "finvizVersion": "111",
        "finvizFilterType": "4",
        "finvizQuoteTimeframe": "d",
        "scanInterval": 300,
    },
    "council": {
        # Market Perception Agent
        "return_1d_threshold": 0.005,
        "return_5d_threshold": 0.01,
        "return_20d_threshold": 0.03,
        "volume_surge_threshold": 1.5,
        "near_high_threshold": -0.02,
        "near_low_threshold": 0.02,
        # Flow Perception Agent
        "pcr_bullish_threshold": 0.7,
        "pcr_mild_bearish_threshold": 1.0,
        "pcr_bearish_threshold": 1.3,
        # Strategy Agent
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "adx_trending_threshold": 25,
        "strategy_buy_pass_rate": 0.6,
        "strategy_sell_pass_rate": 0.3,
        # Risk Agent
        "max_portfolio_heat": 0.06,
        "max_single_position": 0.02,
        "risk_score_veto_threshold": 30,
        "volatility_elevated_threshold": 0.30,
        "volatility_extreme_threshold": 0.50,
        # Execution Agent
        "min_volume_threshold": 50000,
        # Hypothesis Agent
        "llm_buy_confidence_threshold": 0.6,
        "llm_sell_confidence_threshold": 0.4,
        # Critic Agent
        "critic_excellent_r": 2.0,
        "critic_good_r": 1.0,
        "critic_small_loss_r": -1.0,
        # Agent weights
        "weight_market_perception": 1.0,
        "weight_flow_perception": 0.8,
        "weight_regime": 1.2,
        "weight_hypothesis": 0.9,
        "weight_strategy": 1.1,
        "weight_risk": 1.5,
        "weight_execution": 1.3,
        "weight_critic": 0.5,
    },
    "strategy": {
        "defaultOrderType": "market",
        "entryMethod": "signal",
        "autoExecuteTrades": False,
        "backtestStartDate": "2024-01-01",
        "backtestEndDate": "2025-12-31",
        "walkForwardWindows": 6,
        "minSharpeRatio": 1.5,
        "minWinRate": 55,
    },
    "logging": {
        "logLevel": "INFO",
        "logRetentionDays": 30,
        "auditRetentionDays": 90,
        "tradeAuditLog": True,
        "performanceMetricsLog": True,
        "agentDecisionLog": True,
        "apiRequestLog": False,
    },
    "system": {
        "theme": "dark",
        "timezone": "America/New_York",
        "databaseUrl": "postgresql://localhost/elite_trading",
        "redisUrl": "redis://localhost:6379",
        "appPort": 8000,
        "workerThreads": 4,
        "debugMode": False,
        "paperTradingMode": True,
        "maintenanceMode": False,
    },
    "user": {
        "displayName": "",
        "email": "",
        "timezone": "America/New_York",
        "currency": "USD",
        "twoFactorEnabled": False,
        "sessionTimeoutMinutes": 30,
    },
    "machine": {
        # Identity
        "machineId": "",  # ESPENMAIN | ProfitTrader | custom
        "machineName": "",  # Friendly display name
        "machineRole": "auto",  # "pc1" | "pc2" | "standalone" | "auto"
        "isPrimaryNode": None,  # bool | None (auto-detect)
        # Auto-detection
        "autoDetectHostname": True,
        "hostnameOverride": "",  # Force specific hostname match
        # GPU
        "gpuEnabled": True,
        "gpuDeviceIndex": 0,
        "gpuRole": "mixed",  # "inference" | "training" | "mixed"
        "gpuVramHeadroom": 512,  # MB reserved as buffer
    },
    "deployment": {
        # Mode
        "deploymentMode": "auto",  # "single_pc" | "dual_pc" | "auto"
        "distributedModeEnabled": False,  # Explicit toggle
        # Peer Configuration
        "peerMachineHost": "",  # IP or hostname of peer (e.g., "192.168.1.116")
        "peerMachineRole": "",  # "pc1" | "pc2" | ""
        "peerRequiredForStartup": False,
        "peerRequiredForExecution": False,
        # Fallback
        "allowSinglePcFallback": True,
        "fallbackModeActive": False,  # Runtime state (read-only)
        "peerOnline": False,  # Runtime state (read-only)
        # Service Affinity
        "serviceAffinityMode": "auto",  # "auto" | "manual"
        "runTrainingServices": "auto",  # "yes" | "no" | "auto"
        "runInferenceServices": "auto",
        "runExecutionServices": "auto",
        "runIntelligenceServices": "auto",
    },
    "device": {
        # DEPRECATED - use machine.* and deployment.* instead
        "deviceName": "",  # deprecated - use machine.machineName
        "deviceRole": "full",  # deprecated - use machine.machineRole
        "backendPort": 8000,
        "brainHost": "localhost",  # deprecated - use deployment.peerMachineHost
        "brainPort": 50051,
        "peerDevices": [],  # deprecated
        "tradingMode": "live",  # deprecated - use trading.tradingMode
    },
    "appearance": {
        "theme": "dark",
        "density": "compact",
        "chartTimeframe": "5m",
        "showPnlHeader": True,
        "animations": True,
        "soundAlerts": False,
    },
    "alignment": {
        "enabled": True,
        "mode": "strict",
        "checkBrightLines": True,
        "checkBible": True,
        "checkMetacognition": True,
        "checkCritique": True,
        "maxPositionPct": 5,
        "maxHeatPct": 20,
        "maxDrawdownPct": 10,
        "dailyTradeCap": 15,
        "rapidFireWindowSec": 60,
        "critiqueThreshold": 70,
    },
}


def _get_stored_settings() -> Dict[str, Any]:
    """Get all stored settings from SQLite via db_service."""
    stored = db_service.get_config("app_settings")
    if not stored or not isinstance(stored, dict):
        return {}
    return stored


def _save_settings(settings: Dict[str, Any]) -> None:
    """Save full settings dict to SQLite via db_service."""
    db_service.set_config("app_settings", settings)


def get_all_settings() -> Dict[str, Any]:
    """Return all settings across every category, merged with defaults."""
    stored = _get_stored_settings()
    merged = {}
    for cat, defaults in DEFAULTS.items():
        merged[cat] = {**defaults, **(stored.get(cat, {}))}
    return merged


def get_settings_by_category(category: str) -> Dict[str, Any]:
    """Get settings for a single category."""
    if category not in DEFAULTS:
        raise ValueError(f"Unknown settings category: {category}")
    stored = _get_stored_settings()
    return {**DEFAULTS[category], **(stored.get(category, {}))}


def update_all_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Update settings across multiple categories at once."""
    current = _get_stored_settings()
    for category, data in settings.items():
        if category not in DEFAULTS:
            continue
        if category not in current:
            current[category] = {}
        current[category] = {**DEFAULTS[category], **current[category], **data}
        # Propagate API key changes to .env + runtime
        _propagate_env_changes(category, data)
    _save_settings(current)
    return get_all_settings()


def update_settings_by_category(category: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update settings for a single category.

    For dataSources and notifications, also writes changed API keys
    back to the .env file and updates the runtime settings object.
    """
    if category not in DEFAULTS:
        raise ValueError(f"Unknown settings category: {category}")
    current = _get_stored_settings()
    if category not in current:
        current[category] = {}
    current[category] = {**DEFAULTS[category], **current[category], **data}
    _save_settings(current)
    # Propagate API key changes to .env + runtime
    _propagate_env_changes(category, data)
    return current[category]


def reset_settings(category: str) -> Dict[str, Any]:
    """Reset a category back to factory defaults."""
    if category not in DEFAULTS:
        raise ValueError(f"Unknown settings category: {category}")
    current = _get_stored_settings()
    current[category] = DEFAULTS[category].copy()
    _save_settings(current)
    return DEFAULTS[category]


def validate_api_key(provider: str, api_key: str, secret_key: str = "") -> Dict[str, Any]:
    """Validate API key by testing actual connection to provider."""
    if provider == "alpaca":
        try:
            import httpx
            trading_mode = getattr(settings, "TRADING_MODE", "live").lower()
            if trading_mode == "live":
                base_url = "https://api.alpaca.markets/v2"
            else:
                base_url = "https://paper-api.alpaca.markets/v2"
            resp = httpx.get(
                f"{base_url}/account",
                headers={
                    "APCA-API-KEY-ID": api_key,
                    "APCA-API-SECRET-KEY": secret_key,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                account = resp.json()
                return {
                    "valid": True,
                    "provider": provider,
                    "message": f"Connected - Account {account.get('account_number', 'OK')}",
                    "details": {"status": account.get("status"), "equity": str(account.get("equity", ""))},
                }
            return {"valid": False, "provider": provider, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "provider": provider, "message": str(e)}

    elif provider == "unusual_whales":
        try:
            import httpx
            resp = httpx.get(
                "https://api.unusualwhales.com/api/darkpool/recent",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return {"valid": True, "provider": provider, "message": "Connected to Unusual Whales"}
            return {"valid": False, "provider": provider, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "provider": provider, "message": str(e)}

    elif provider == "finviz":
        try:
            import httpx
            resp = httpx.get(
                f"https://elite.finviz.com/export.ashx?v=111&auth={api_key}",
                timeout=10,
            )
            if resp.status_code == 200:
                return {"valid": True, "provider": provider, "message": "FinViz Elite connected"}
            return {"valid": False, "provider": provider, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "provider": provider, "message": str(e)}

    elif provider == "fred":
        try:
            import httpx
            resp = httpx.get(
                f"https://api.stlouisfed.org/fred/series?series_id=GDP&api_key={api_key}&file_type=json",
                timeout=10,
            )
            if resp.status_code == 200:
                return {"valid": True, "provider": provider, "message": "FRED API connected"}
            return {"valid": False, "provider": provider, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "provider": provider, "message": str(e)}

    elif provider == "news_api":
        try:
            import httpx
            resp = httpx.get(
                f"https://newsapi.org/v2/top-headlines?country=us&pageSize=1&apiKey={api_key}",
                timeout=10,
            )
            if resp.status_code == 200:
                return {"valid": True, "provider": provider, "message": "News API connected"}
            return {"valid": False, "provider": provider, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "provider": provider, "message": str(e)}

    elif provider == "discord":
        try:
            import httpx
            resp = httpx.get(
                "https://discord.com/api/v10/users/@me",
                headers={"Authorization": f"Bot {api_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                user = resp.json()
                return {"valid": True, "provider": provider, "message": f"Discord bot: {user.get('username', 'OK')}"}
            return {"valid": False, "provider": provider, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "provider": provider, "message": str(e)}

    elif provider == "youtube":
        try:
            import httpx
            resp = httpx.get(
                f"https://www.googleapis.com/youtube/v3/search?part=snippet&q=stock+market&maxResults=1&key={api_key}",
                timeout=10,
            )
            if resp.status_code == 200:
                return {"valid": True, "provider": provider, "message": "YouTube API connected"}
            return {"valid": False, "provider": provider, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "provider": provider, "message": str(e)}

    elif provider == "stockgeist":
        try:
            import httpx
            resp = httpx.get(
                "https://api.stockgeist.ai/v1/health",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return {"valid": True, "provider": provider, "message": "StockGeist connected"}
            return {"valid": False, "provider": provider, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "provider": provider, "message": str(e)}

    elif provider == "resend":
        try:
            import httpx
            resp = httpx.get(
                "https://api.resend.com/domains",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return {"valid": True, "provider": provider, "message": "Resend API connected"}
            return {"valid": False, "provider": provider, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "provider": provider, "message": str(e)}

    elif provider == "perplexity":
        try:
            import httpx
            resp = httpx.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "sonar", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
                timeout=15,
            )
            if resp.status_code == 200:
                return {"valid": True, "provider": provider, "message": "Perplexity API connected"}
            return {"valid": False, "provider": provider, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "provider": provider, "message": str(e)}

    elif provider == "anthropic":
        try:
            import httpx
            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 5, "messages": [{"role": "user", "content": "ping"}]},
                timeout=15,
            )
            if resp.status_code == 200:
                return {"valid": True, "provider": provider, "message": "Anthropic API connected"}
            return {"valid": False, "provider": provider, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "provider": provider, "message": str(e)}

    return {"valid": False, "provider": provider, "message": f"Unknown provider: {provider}"}


def test_connection(source: str) -> Dict[str, Any]:
    """Test connectivity to a data source using stored keys."""
    ds_settings = get_settings_by_category("dataSources")

    if source == "alpaca":
        return validate_api_key("alpaca", ds_settings.get("alpacaApiKey", ""), ds_settings.get("alpacaSecretKey", ""))
    elif source == "unusual_whales":
        return validate_api_key("unusual_whales", ds_settings.get("unusualWhalesApiKey", ""))
    elif source == "finviz":
        return validate_api_key("finviz", ds_settings.get("finvizApiKey", ""))
    elif source == "fred":
        return validate_api_key("fred", ds_settings.get("fredApiKey", ""))
    elif source == "news_api":
        return validate_api_key("news_api", ds_settings.get("newsApiKey", ""))
    elif source == "discord":
        return validate_api_key("discord", ds_settings.get("discordBotToken", ""))
    elif source == "youtube":
        return validate_api_key("youtube", ds_settings.get("youtubeApiKey", ""))
    elif source == "stockgeist":
        return validate_api_key("stockgeist", ds_settings.get("stockgeistApiKey", ""))
    elif source == "resend":
        return validate_api_key("resend", ds_settings.get("resendApiKey", ""))
    elif source == "perplexity":
        return validate_api_key("perplexity", ds_settings.get("perplexityApiKey", ""))
    elif source == "anthropic":
        return validate_api_key("anthropic", ds_settings.get("anthropicApiKey", ""))
    elif source == "ollama":
        try:
            import httpx
            ollama_settings = get_settings_by_category("ollama")
            resp = httpx.get(f"{ollama_settings['ollamaHostUrl']}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return {"valid": True, "source": source, "message": f"Ollama connected - {len(models)} models"}
            return {"valid": False, "source": source, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "source": source, "message": str(e)}

    return {"valid": False, "source": source, "message": f"Unknown source: {source}"}


def export_settings() -> Dict[str, Any]:
    """Export all settings as JSON."""
    settings = get_all_settings()
    settings["_exported_at"] = datetime.utcnow().isoformat()
    settings["_version"] = "1.0"
    return settings


def import_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    """Import settings from JSON payload."""
    cleaned = {k: v for k, v in data.items() if k in DEFAULTS}
    return update_all_settings(cleaned)


# ====================================================================
#  ENV WRITEBACK — propagate Settings UI changes to .env + runtime
# ====================================================================

# Map camelCase dataSources key -> UPPER_SNAKE .env key
_DS_TO_ENV: Dict[str, str] = {
    "alpacaApiKey": "ALPACA_API_KEY",
    "alpacaSecretKey": "ALPACA_SECRET_KEY",
    "alpacaBaseUrl": "ALPACA_BASE_URL",
    "alpacaFeed": "ALPACA_FEED",
    "unusualWhalesApiKey": "UNUSUAL_WHALES_API_KEY",
    "finvizApiKey": "FINVIZ_API_KEY",
    "fredApiKey": "FRED_API_KEY",
    "newsApiKey": "NEWS_API_KEY",
    "benzingaApiKey": "BENZINGA_API_KEY",
    "stockgeistApiKey": "STOCKGEIST_API_KEY",
    "youtubeApiKey": "YOUTUBE_API_KEY",
    "secEdgarUserAgent": "SEC_EDGAR_USER_AGENT",
    "xApiKey": "X_API_KEY",
    "xApiKeySecret": "X_API_KEY_SECRET",
    "xOAuth2ClientId": "X_OAUTH2_CLIENT_ID",
    "xOAuth2ClientSecret": "X_OAUTH2_CLIENT_SECRET",
    "xBearerToken": "X_BEARER_TOKEN",
    "redditClientId": "REDDIT_CLIENT_ID",
    "redditClientSecret": "REDDIT_CLIENT_SECRET",
    "discordBotToken": "DISCORD_BOT_TOKEN",
    "discordUserToken": "DISCORD_USER_TOKEN",
    "discordUwChannelId": "DISCORD_UW_CHANNEL_ID",
    "discordUwLiveChannelId": "DISCORD_UW_LIVE_CHANNEL_ID",
    "discordFomChannelId": "DISCORD_FOM_CHANNEL_ID",
    "discordFomZonesChannelId": "DISCORD_FOM_ZONES_CHANNEL_ID",
    "discordFomIvolChannelId": "DISCORD_FOM_IVOL_CHANNEL_ID",
    "discordExpectedMovesChannelId": "DISCORD_EXPECTED_MOVES_CHANNEL_ID",
    "discordMaverickChannelId": "DISCORD_MAVERICK_CHANNEL_ID",
    "slackBotToken": "SLACK_BOT_TOKEN",
    "slackAppToken": "SLACK_APP_TOKEN",
    "slackWebhookUrl": "SLACK_WEBHOOK_URL",
    "resendApiKey": "RESEND_API_KEY",
    "resendFromEmail": "RESEND_FROM_EMAIL",
    "resendAlertToEmail": "RESEND_ALERT_TO_EMAIL",
    "perplexityApiKey": "PERPLEXITY_API_KEY",
    "anthropicApiKey": "ANTHROPIC_API_KEY",
    "openclawBridgeToken": "OPENCLAW_BRIDGE_TOKEN",
    "apiAuthToken": "API_AUTH_TOKEN",
    "fernetKey": "FERNET_KEY",
}

# Notifications keys that map to .env
_NOTIF_TO_ENV: Dict[str, str] = {
    "telegramBotToken": "TELEGRAM_BOT_TOKEN",
    "telegramChatId": "TELEGRAM_CHAT_ID",
    "slackWebhookUrl": "SLACK_WEBHOOK_URL",
    "slackWebhookUw": "SLACK_WEBHOOK_UW",
    "slackWebhookFom": "SLACK_WEBHOOK_FOM",
    "slackWebhookMav": "SLACK_WEBHOOK_MAV",
    "slackWebhookChannel": "SLACK_WEBHOOK_CHANNEL",
}


def _write_env_key(env_key: str, value: str) -> None:
    """Update a single key in the backend/.env file.

    If the key already exists, its value is replaced in-place.
    If the key doesn't exist, it's appended at the end.
    Also updates os.environ so the change is visible to OpenClaw's config.py.
    """
    env_path = Path(_ENV_FILE)
    if not env_path.exists():
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    pattern = re.compile(rf"^{re.escape(env_key)}\s*=")
    replaced = False
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"{env_key}={value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{env_key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Also push into os.environ for OpenClaw config.py reads
    os.environ[env_key] = str(value)


def _sync_runtime_settings(env_key: str, value: Any) -> None:
    """Push the new value into the live `settings` object (pydantic-settings).

    Uses object.__setattr__ to bypass Pydantic frozen-model guards.
    """
    attr_name = env_key  # Settings fields use UPPER_SNAKE matching env key
    if hasattr(settings, attr_name):
        try:
            object.__setattr__(settings, attr_name, value)
        except Exception:
            pass  # Best-effort; restart will pick up from .env


def _propagate_env_changes(category: str, data: Dict[str, Any]) -> None:
    """After a category update, write changed API keys to .env and runtime."""
    mapping: Dict[str, str] = {}
    if category == "dataSources":
        mapping = _DS_TO_ENV
    elif category == "notifications":
        mapping = _NOTIF_TO_ENV
    else:
        return  # Only dataSources and notifications carry API keys

    for camel_key, env_key in mapping.items():
        if camel_key in data:
            val = str(data[camel_key])
            _write_env_key(env_key, val)
            _sync_runtime_settings(env_key, val)

    # Special: Unusual Whales alias sync
    if category == "dataSources" and "unusualWhalesApiKey" in data:
        _write_env_key("UNUSUALWHALES_API_KEY", str(data["unusualWhalesApiKey"]))
    # Special: StockGeist alias sync
    if category == "dataSources" and "stockgeistApiKey" in data:
        _write_env_key("STOCKGEIST_TOKEN", str(data["stockgeistApiKey"]))
        _write_env_key("STOCKGEIST_AUTH", str(data["stockgeistApiKey"]))


# ── Aliases for settings_routes.py compatibility ─────────────────────
update_category_settings = update_settings_by_category

# CATEGORIES dict keyed by name for validation in routes
CATEGORIES: dict = {k: list(v.keys()) for k, v in DEFAULTS.items()}

