"""Settings service — DuckDB-backed, migration-safe, real validation.

Manages all settings for the Elite Trading System across 7 categories:
trading, risk, dataSources, notifications, ml, agents, system.
Persisted in DuckDB settings table with auto-creation.
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from app.services.database import db_service


DEFAULTS: Dict[str, Dict[str, Any]] = {
    "trading": {
        "tradingMode": "paper",
        "defaultOrderType": "market",
        "maxPositionSize": 10000,
        "maxDailyTrades": 20,
        "autoExecute": False,
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
        "alpacaApiKey": "",
        "alpacaSecretKey": "",
        "alpacaBaseUrl": "paper",
        "unusualWhalesApiKey": "",
        "finvizApiKey": "",
        "fredApiKey": "",
        "newsApiKey": "",
        "stockgeistApiKey": "",
        "refreshIntervalSeconds": 300,
    },
    "notifications": {
        "discordWebhookUrl": "",
        "slackWebhookUrl": "",
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
    _save_settings(current)
    return get_all_settings()


def update_settings_by_category(category: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update settings for a single category."""
    if category not in DEFAULTS:
        raise ValueError(f"Unknown settings category: {category}")
    current = _get_stored_settings()
    if category not in current:
        current[category] = {}
    current[category] = {**DEFAULTS[category], **current[category], **data}
    _save_settings(current)
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
                "https://api.unusualwhales.com/api/market/overview",
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

    return {"valid": False, "provider": provider, "message": f"Unknown provider: {provider}"}


def test_connection(source: str) -> Dict[str, Any]:
    """Test connectivity to a data source using stored keys."""
    settings = get_settings_by_category("dataSources")

    if source == "alpaca":
        return validate_api_key("alpaca", settings["alpacaApiKey"], settings["alpacaSecretKey"])
    elif source == "unusual_whales":
        return validate_api_key("unusual_whales", settings["unusualWhalesApiKey"])
    elif source == "finviz":
        return validate_api_key("finviz", settings["finvizApiKey"])
    elif source == "fred":
        return validate_api_key("fred", settings["fredApiKey"])
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


# ── Aliases for settings_routes.py compatibility ─────────────────────
# Routes import update_category_settings; service uses update_settings_by_category
update_category_settings = update_settings_by_category

# CATEGORIES dict keyed by name for validation in routes
CATEGORIES: dict = {k: list(v.keys()) for k, v in DEFAULTS.items()}

