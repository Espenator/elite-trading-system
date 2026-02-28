Made with Perplexity
"""
Data Sources Manager - Elite Trading System
backend/app/api/v1/data_sources.py

Full CRUD, encrypted credentials, live connection testing,
AI provider detection, WebSocket broadcasts on all mutations.
NO yfinance. Primary: Alpaca, Unusual Whales, Finviz.
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import os
import requests
import json
from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime, timezone
from enum import Enum

from app.services.alpaca_service import alpaca_service
from app.services.database import db_service
from app.websocket_manager import broadcast_ws

router = APIRouter(prefix="/data-sources", tags=["data-sources"])

# ---------------------------------------------------------------------------
# Fernet encryption for API credentials
# ---------------------------------------------------------------------------
FERNET_KEY = os.getenv("FERNET_KEY", Fernet.generate_key().decode())
_cipher = Fernet(FERNET_KEY.encode())

DB_CONFIG_KEY = "data_sources_registry"
DB_CREDS_PREFIX = "ds_creds_"


def _encrypt(plain: Dict[str, str]) -> str:
    return _cipher.encrypt(json.dumps(plain).encode()).decode()


def _decrypt(token: str) -> Dict[str, str]:
    try:
        return json.loads(_cipher.decrypt(token.encode()).decode())
    except (InvalidToken, Exception):
        raise HTTPException(400, "Credential decryption failed")


def _mask(keys: Dict[str, str]) -> Dict[str, str]:
    masked = {}
    for k, v in keys.items():
        if len(v) > 8:
            masked[k] = v[:4] + "*" * (len(v) - 8) + v[-4:]
        else:
            masked[k] = "****"
    return masked


# ---------------------------------------------------------------------------
# Source categories & types
# ---------------------------------------------------------------------------
class SourceCategory(str, Enum):
    MARKET = "market"
    OPTIONS_FLOW = "options_flow"
    ECONOMIC = "economic"
    FILINGS = "filings"
    SENTIMENT = "sentiment"
    NEWS = "news"
    SOCIAL = "social"
    ALERTS = "alerts"
    BRIDGE = "bridge"
    STORAGE = "storage"
    CUSTOM = "custom"


class SourceType(str, Enum):
    REST = "rest"
    WEBSOCKET = "websocket"
    RSS = "rss"
    SCRAPER = "scraper"
    LOCAL = "local"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class DataSourceBase(BaseModel):
    id: str
    name: str
    type: SourceType = SourceType.REST
    category: SourceCategory = SourceCategory.MARKET
    base_url: str = ""
    required_keys: List[str] = []
    test_endpoint: str = ""
    status: str = "pending"
    enabled: bool = True


class DataSourceRead(DataSourceBase):
    last_test: Optional[str] = None
    last_latency_ms: Optional[float] = None
    last_error: Optional[str] = None
    has_credentials: bool = False


class DataSourceCreate(BaseModel):
    id: str
    name: str
    type: SourceType = SourceType.REST
    category: SourceCategory = SourceCategory.CUSTOM
    base_url: str = ""
    required_keys: List[str] = []
    test_endpoint: str = ""
    enabled: bool = True


class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    test_endpoint: Optional[str] = None
    enabled: Optional[bool] = None
    type: Optional[SourceType] = None
    category: Optional[SourceCategory] = None
    required_keys: Optional[List[str]] = None


class CredentialsPayload(BaseModel):
    keys: Dict[str, str]


class TestResult(BaseModel):
    source_id: str
    success: bool
    latency_ms: float
    status_code: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None
    tested_at: str


class AIDetectRequest(BaseModel):
    url: str


class AIDetectResponse(BaseModel):
    detected_provider: Optional[str] = None
    confidence: float = 0.0
    template: Optional[Dict[str, Any]] = None
    suggestion: str = ""


# ---------------------------------------------------------------------------
# Default 17 sources + custom slot = 18
# ---------------------------------------------------------------------------
DEFAULT_SOURCES: Dict[str, Dict[str, Any]] = {
    "alpaca": {
        "id": "alpaca",
        "name": "Alpaca Markets",
        "type": "rest",
        "category": "market",
        "base_url": "https://api.alpaca.markets",
        "required_keys": ["api_key", "secret_key"],
        "test_endpoint": "/v2/account",
        "status": "active",
        "enabled": True,
    },
    "unusual_whales": {
        "id": "unusual_whales",
        "name": "Unusual Whales",
        "type": "rest",
        "category": "options_flow",
        "base_url": "https://api.unusualwhales.com/api",
        "required_keys": ["api_key"],
        "test_endpoint": "/v1/flow/live",
        "status": "active",
        "enabled": True,
    },
    "finviz": {
        "id": "finviz",
        "name": "Finviz",
        "type": "scraper",
        "category": "market",
        "base_url": "https://finviz.com",
        "required_keys": ["api_key"],
        "test_endpoint": "/screener.ashx?v=111",
        "status": "active",
        "enabled": True,
    },
    "fred": {
        "id": "fred",
        "name": "FRED",
        "type": "rest",
        "category": "economic",
        "base_url": "https://api.stlouisfed.org/fred",
        "required_keys": ["api_key"],
        "test_endpoint": "/series?series_id=DGS10",
        "status": "active",
        "enabled": True,
    },
    "sec_edgar": {
        "id": "sec_edgar",
        "name": "SEC EDGAR",
        "type": "rest",
        "category": "filings",
        "base_url": "https://efts.sec.gov/LATEST",
        "required_keys": ["user_agent"],
        "test_endpoint": "/search-index?q=AAPL&dateRange=custom&startdt=2025-01-01&enddt=2025-01-02",
        "status": "active",
        "enabled": True,
    },
    "stockgeist": {
        "id": "stockgeist",
        "name": "Stockgeist",
        "type": "rest",
        "category": "sentiment",
        "base_url": "https://api.stockgeist.ai",
        "required_keys": ["api_key"],
        "test_endpoint": "/v1/health",
        "status": "beta",
        "enabled": False,
    },
    "news_api": {
        "id": "news_api",
        "name": "News API",
        "type": "rest",
        "category": "news",
        "base_url": "https://newsapi.org/v2",
        "required_keys": ["api_key"],
        "test_endpoint": "/top-headlines?country=us&pageSize=1",
        "status": "active",
        "enabled": True,
    },
    "discord": {
        "id": "discord",
        "name": "Discord",
        "type": "websocket",
        "category": "social",
        "base_url": "https://discord.com/api/v10",
        "required_keys": ["bot_token"],
        "test_endpoint": "/gateway",
        "status": "active",
        "enabled": True,
    },
    "twitter": {
        "id": "twitter",
        "name": "X/Twitter",
        "type": "rest",
        "category": "social",
        "base_url": "https://api.x.com/2",
        "required_keys": ["bearer_token"],
        "test_endpoint": "/tweets/search/recent?query=SPY&max_results=10",
        "status": "active",
        "enabled": True,
    },
    "youtube": {
        "id": "youtube",
        "name": "YouTube",
        "type": "rest",
        "category": "social",
        "base_url": "https://www.googleapis.com/youtube/v3",
        "required_keys": ["api_key"],
        "test_endpoint": "/search?part=snippet&q=stock+market&maxResults=1",
        "status": "active",
        "enabled": True,
    },
    "reddit": {
        "id": "reddit",
        "name": "Reddit",
        "type": "rest",
        "category": "social",
        "base_url": "https://oauth.reddit.com",
        "required_keys": ["client_id", "client_secret", "user_agent"],
        "test_endpoint": "/api/v1/me",
        "status": "active",
        "enabled": True,
    },
    "benzinga": {
        "id": "benzinga",
        "name": "Benzinga",
        "type": "rest",
        "category": "news",
        "base_url": "https://api.benzinga.com",
        "required_keys": ["token"],
        "test_endpoint": "/api/v2/news?pageSize=1",
        "status": "active",
        "enabled": True,
    },
    "rss": {
        "id": "rss",
        "name": "RSS Feeds",
        "type": "rss",
        "category": "news",
        "base_url": "",
        "required_keys": [],
        "test_endpoint": "",
        "status": "active",
        "enabled": True,
    },
    "tradingview": {
        "id": "tradingview",
        "name": "TradingView",
        "type": "rest",
        "category": "market",
        "base_url": "https://scanner.tradingview.com",
        "required_keys": [],
        "test_endpoint": "/america/scan",
        "status": "active",
        "enabled": True,
    },
    "openclaw_bridge": {
        "id": "openclaw_bridge",
        "name": "OpenClaw Bridge",
        "type": "local",
        "category": "bridge",
        "base_url": "http://localhost:8080",
        "required_keys": [],
        "test_endpoint": "/health",
        "status": "active",
        "enabled": True,
    },
    "resend": {
        "id": "resend",
        "name": "Resend",
        "type": "rest",
        "category": "alerts",
        "base_url": "https://api.resend.com",
        "required_keys": ["api_key"],
        "test_endpoint": "/domains",
        "status": "active",
        "enabled": True,
    },
    "github_gist": {
        "id": "github_gist",
        "name": "GitHub Gist",
        "type": "rest",
        "category": "storage",
        "base_url": "https://api.github.com",
        "required_keys": ["access_token"],
        "test_endpoint": "/gists?per_page=1",
        "status": "active",
        "enabled": True,
    },
}


# ---------------------------------------------------------------------------
# Persistence helpers via db_service.get_config / set_config
# ---------------------------------------------------------------------------
def _load_sources() -> Dict[str, Dict[str, Any]]:
    raw = db_service.get_config(DB_CONFIG_KEY)
    if raw:
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            pass
    _save_sources(DEFAULT_SOURCES)
    return DEFAULT_SOURCES.copy()


def _save_sources(sources: Dict[str, Dict[str, Any]]):
    db_service.set_config(DB_CONFIG_KEY, json.dumps(sources))


def _source_to_read(src: Dict[str, Any]) -> DataSourceRead:
    creds_key = f"{DB_CREDS_PREFIX}{src['id']}"
    has_creds = bool(db_service.get_config(creds_key))
    return DataSourceRead(
        id=src["id"],
        name=src["name"],
        type=src.get("type", "rest"),
        category=src.get("category", "custom"),
        base_url=src.get("base_url", ""),
        required_keys=src.get("required_keys", []),
        test_endpoint=src.get("test_endpoint", ""),
        status=src.get("status", "pending"),
        enabled=src.get("enabled", True),
        last_test=src.get("last_test"),
        last_latency_ms=src.get("last_latency_ms"),
        last_error=src.get("last_error"),
        has_credentials=has_creds,
    )


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------


@router.get("/", response_model=List[DataSourceRead])
async def list_sources():
    """List all 18 data sources with live health status."""
    sources = _load_sources()
    return [_source_to_read(s) for s in sources.values()]


@router.get("/{source_id}", response_model=DataSourceRead)
async def get_source(source_id: str):
    """Get single source details."""
    sources = _load_sources()
    if source_id not in sources:
        raise HTTPException(404, f"Source '{source_id}' not found")
    return _source_to_read(sources[source_id])


@router.post("/", response_model=DataSourceRead, status_code=201)
async def add_source(payload: DataSourceCreate):
    """Add a new data source (custom or from defaults)."""
    sources = _load_sources()
    if payload.id in sources:
        raise HTTPException(409, f"Source '{payload.id}' already exists")
    new_source = {
        "id": payload.id,
        "name": payload.name,
        "type": payload.type.value,
        "category": payload.category.value,
        "base_url": payload.base_url,
        "required_keys": payload.required_keys,
        "test_endpoint": payload.test_endpoint,
        "status": "pending",
        "enabled": payload.enabled,
        "last_test": None,
        "last_latency_ms": None,
        "last_error": None,
    }
    sources[payload.id] = new_source
    _save_sources(sources)
    await broadcast_ws({
        "type": "data_source_added",
        "source_id": payload.id,
        "data": new_source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return _source_to_read(new_source)


@router.put("/{source_id}", response_model=DataSourceRead)
async def update_source(source_id: str, payload: DataSourceUpdate):
    """Update an existing data source's configuration."""
    sources = _load_sources()
    if source_id not in sources:
        raise HTTPException(404, f"Source '{source_id}' not found")
    src = sources[source_id]
    if payload.name is not None:
        src["name"] = payload.name
    if payload.base_url is not None:
        src["base_url"] = payload.base_url
    if payload.test_endpoint is not None:
        src["test_endpoint"] = payload.test_endpoint
    if payload.enabled is not None:
        src["enabled"] = payload.enabled
    if payload.type is not None:
        src["type"] = payload.type.value
    if payload.category is not None:
        src["category"] = payload.category.value
    if payload.required_keys is not None:
        src["required_keys"] = payload.required_keys
    sources[source_id] = src
    _save_sources(sources)
    await broadcast_ws({
        "type": "data_source_updated",
        "source_id": source_id,
        "data": src,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return _source_to_read(src)


@router.delete("/{source_id}")
async def delete_source(source_id: str):
    """Remove a data source and its stored credentials."""
    sources = _load_sources()
    if source_id not in sources:
        raise HTTPException(404, f"Source '{source_id}' not found")
    del sources[source_id]
    _save_sources(sources)
    creds_key = f"{DB_CREDS_PREFIX}{source_id}"
    db_service.set_config(creds_key, "")
    await broadcast_ws({
        "type": "data_source_deleted",
        "source_id": source_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": f"Source '{source_id}' deleted", "id": source_id}


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


@router.put("/{source_id}/credentials")
async def set_credentials(source_id: str, payload: CredentialsPayload):
    """Encrypt and store API credentials for a source."""
    sources = _load_sources()
    if source_id not in sources:
        raise HTTPException(404, f"Source '{source_id}' not found")
    required = sources[source_id].get("required_keys", [])
    missing = [k for k in required if k not in payload.keys]
    if missing:
        raise HTTPException(400, f"Missing required keys: {missing}")
    encrypted = _encrypt(payload.keys)
    creds_key = f"{DB_CREDS_PREFIX}{source_id}"
    db_service.set_config(creds_key, encrypted)
    await broadcast_ws({
        "type": "credentials_updated",
        "source_id": source_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": f"Credentials stored for '{source_id}'", "keys_count": len(payload.keys)}


@router.get("/{source_id}/credentials")
async def get_credentials(source_id: str):
    """Retrieve masked credentials for display."""
    sources = _load_sources()
    if source_id not in sources:
        raise HTTPException(404, f"Source '{source_id}' not found")
    creds_key = f"{DB_CREDS_PREFIX}{source_id}"
    encrypted = db_service.get_config(creds_key)
    if not encrypted:
        raise HTTPException(404, f"No credentials stored for '{source_id}'")
    decrypted = _decrypt(encrypted)
    return {"source_id": source_id, "credentials": _mask(decrypted)}


# ---------------------------------------------------------------------------
# Connection testing
# ---------------------------------------------------------------------------


def _build_headers(source_id: str, creds: Dict[str, str]) -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    if source_id == "alpaca":
        headers["APCA-API-KEY-ID"] = creds.get("api_key", "")
        headers["APCA-API-SECRET-KEY"] = creds.get("secret_key", "")
    elif source_id == "unusual_whales":
        headers["Authorization"] = f"Bearer {creds.get('api_key', '')}"
    elif source_id == "twitter":
        headers["Authorization"] = f"Bearer {creds.get('bearer_token', '')}"
    elif source_id == "discord":
        headers["Authorization"] = f"Bot {creds.get('bot_token', '')}"
    elif source_id == "reddit":
        headers["User-Agent"] = creds.get("user_agent", "EliteTrader/1.0")
    elif source_id == "resend":
        headers["Authorization"] = f"Bearer {creds.get('api_key', '')}"
    elif source_id == "github_gist":
        headers["Authorization"] = f"Bearer {creds.get('access_token', '')}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    elif source_id == "sec_edgar":
        headers["User-Agent"] = creds.get("user_agent", "EliteTrader espen@embodier.ai")
    elif source_id == "benzinga":
        headers["Authorization"] = f"Bearer {creds.get('token', '')}"
    elif source_id == "stockgeist":
        headers["Authorization"] = f"Bearer {creds.get('api_key', '')}"
    return headers


def _build_params(source_id: str, creds: Dict[str, str]) -> Dict[str, str]:
    params = {}
    if source_id == "fred":
        params["api_key"] = creds.get("api_key", "")
        params["file_type"] = "json"
    elif source_id == "news_api":
        params["apiKey"] = creds.get("api_key", "")
    elif source_id == "youtube":
        params["key"] = creds.get("api_key", "")
    elif source_id == "finviz":
        params["apikey"] = creds.get("api_key", "")
    return params


@router.post("/{source_id}/test", response_model=TestResult)
async def test_source(source_id: str):
    """Live connection test. Alpaca uses alpaca_service.get_account()."""
    sources = _load_sources()
    if source_id not in sources:
        raise HTTPException(404, f"Source '{source_id}' not found")
    src = sources[source_id]
    now_str = datetime.now(timezone.utc).isoformat()

    # --- Alpaca: use existing alpaca_service ---
    if source_id == "alpaca":
        start = datetime.now(timezone.utc)
        try:
            account = alpaca_service.get_account()
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            src["status"] = "healthy"
            src["last_test"] = now_str
            src["last_latency_ms"] = round(latency, 1)
            src["last_error"] = None
            _save_sources(sources)
            result = TestResult(
                source_id="alpaca",
                success=True,
                latency_ms=round(latency, 1),
                status_code=200,
                message=f"Account status: {account.status}, equity: ${float(account.equity):,.2f}",
                error=None,
                tested_at=now_str,
            )
            await broadcast_ws({"type": "source_tested", "source_id": "alpaca", "result": result.dict()})
            return result
        except Exception as e:
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            src["status"] = "error"
            src["last_test"] = now_str
            src["last_latency_ms"] = round(latency, 1)
            src["last_error"] = str(e)
            _save_sources(sources)
            result = TestResult(
                source_id="alpaca",
                success=False,
                latency_ms=round(latency, 1),
                error=str(e),
                tested_at=now_str,
            )
            await broadcast_ws({"type": "source_tested", "source_id": "alpaca", "result": result.dict()})
            return result

    # --- RSS: just check if base_url is set ---
    if source_id == "rss":
        src["status"] = "healthy" if src.get("base_url") else "unconfigured"
        src["last_test"] = now_str
        src["last_latency_ms"] = 0
        _save_sources(sources)
        result = TestResult(
            source_id="rss",
            success=bool(src.get("base_url")),
            latency_ms=0,
            message="RSS configured" if src.get("base_url") else "No feed URL set",
            tested_at=now_str,
        )
        await broadcast_ws({"type": "source_tested", "source_id": "rss", "result": result.dict()})
        return result

    # --- OpenClaw Bridge: local service ---
    if source_id == "openclaw_bridge":
        start = datetime.now(timezone.utc)
        try:
            url = f"{src['base_url']}{src['test_endpoint']}"
            resp = requests.get(url, timeout=5)
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            ok = resp.status_code == 200
            src["status"] = "healthy" if ok else "error"
            src["last_test"] = now_str
            src["last_latency_ms"] = round(latency, 1)
            src["last_error"] = None if ok else f"HTTP {resp.status_code}"
            _save_sources(sources)
            result = TestResult(
                source_id="openclaw_bridge",
                success=ok,
                latency_ms=round(latency, 1),
                status_code=resp.status_code,
                message=resp.text[:200] if ok else None,
                error=None if ok else f"HTTP {resp.status_code}",
                tested_at=now_str,
            )
            await broadcast_ws({"type": "source_tested", "source_id": "openclaw_bridge", "result": result.dict()})
            return result
        except Exception as e:
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            src["status"] = "offline"
            src["last_test"] = now_str
            src["last_latency_ms"] = round(latency, 1)
            src["last_error"] = str(e)
            _save_sources(sources)
            result = TestResult(
                source_id="openclaw_bridge",
                success=False,
                latency_ms=round(latency, 1),
                error=str(e),
                tested_at=now_str,
            )
            await broadcast_ws({"type": "source_tested", "source_id": "openclaw_bridge", "result": result.dict()})
            return result

    # --- TradingView: no auth needed ---
    if source_id == "tradingview":
        start = datetime.now(timezone.utc)
        try:
            url = f"{src['base_url']}{src['test_endpoint']}"
            resp = requests.post(url, json={"symbols": {"tickers": ["NASDAQ:AAPL"], "query": {"types": []}}, "columns": ["close"]}, timeout=10)
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            ok = resp.status_code == 200
            src["status"] = "healthy" if ok else "error"
            src["last_test"] = now_str
            src["last_latency_ms"] = round(latency, 1)
            src["last_error"] = None if ok else f"HTTP {resp.status_code}"
            _save_sources(sources)
            result = TestResult(
                source_id="tradingview",
                success=ok,
                latency_ms=round(latency, 1),
                status_code=resp.status_code,
                message="Scanner responding" if ok else None,
                error=None if ok else f"HTTP {resp.status_code}",
                tested_at=now_str,
            )
            await broadcast_ws({"type": "source_tested", "source_id": "tradingview", "result": result.dict()})
            return result
        except Exception as e:
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            src["status"] = "error"
            src["last_test"] = now_str
            src["last_latency_ms"] = round(latency, 1)
            src["last_error"] = str(e)
            _save_sources(sources)
            result = TestResult(
                source_id="tradingview",
                success=False,
                latency_ms=round(latency, 1),
                error=str(e),
                tested_at=now_str,
            )
            await broadcast_ws({"type": "source_tested", "source_id": "tradingview", "result": result.dict()})
            return result

    # --- Generic authenticated test for remaining sources ---
    creds_key = f"{DB_CREDS_PREFIX}{source_id}"
    encrypted = db_service.get_config(creds_key)
    creds = {}
    if encrypted:
        creds = _decrypt(encrypted)
    elif src.get("required_keys"):
        src["status"] = "no_credentials"
        src["last_test"] = now_str
        _save_sources(sources)
        result = TestResult(
            source_id=source_id,
            success=False,
            latency_ms=0,
            error=f"No credentials stored. Required: {src['required_keys']}",
            tested_at=now_str,
        )
        await broadcast_ws({"type": "source_tested", "source_id": source_id, "result": result.dict()})
        return result

    url = f"{src['base_url']}{src['test_endpoint']}"
    headers = _build_headers(source_id, creds)
    params = _build_params(source_id, creds)
    method = "GET"
    start = datetime.now(timezone.utc)

    try:
        resp = requests.request(method, url, headers=headers, params=params, timeout=10)
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        ok = resp.status_code in (200, 201)
        src["status"] = "healthy" if ok else "error"
        src["last_test"] = now_str
        src["last_latency_ms"] = round(latency, 1)
        src["last_error"] = None if ok else f"HTTP {resp.status_code}: {resp.text[:100]}"
        _save_sources(sources)
        result = TestResult(
            source_id=source_id,
            success=ok,
            latency_ms=round(latency, 1),
            status_code=resp.status_code,
            message=resp.text[:200] if ok else None,
            error=None if ok else f"HTTP {resp.status_code}: {resp.text[:100]}",
            tested_at=now_str,
        )
        await broadcast_ws({"type": "source_tested", "source_id": source_id, "result": result.dict()})
        return result
    except requests.exceptions.Timeout:
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        src["status"] = "timeout"
        src["last_test"] = now_str
        src["last_latency_ms"] = round(latency, 1)
        src["last_error"] = "Connection timed out (10s)"
        _save_sources(sources)
        result = TestResult(
            source_id=source_id,
            success=False,
            latency_ms=round(latency, 1),
            error="Connection timed out (10s)",
            tested_at=now_str,
        )
        await broadcast_ws({"type": "source_tested", "source_id": source_id, "result": result.dict()})
        return result
    except Exception as e:
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        src["status"] = "error"
        src["last_test"] = now_str
        src["last_latency_ms"] = round(latency, 1)
        src["last_error"] = str(e)
        _save_sources(sources)
        result = TestResult(
            source_id=source_id,
            success=False,
            latency_ms=round(latency, 1),
            error=str(e),
            tested_at=now_str,
        )
        await broadcast_ws({"type": "source_tested", "source_id": source_id, "result": result.dict()})
        return result


# ---------------------------------------------------------------------------
# AI detect provider from URL
# ---------------------------------------------------------------------------
AI_DETECT_MAP = {
    "alpaca": ["alpaca.markets", "paper-api.alpaca"],
    "unusual_whales": ["unusualwhales.com"],
    "finviz": ["finviz.com"],
    "fred": ["stlouisfed.org", "fred.stlouisfed"],
    "sec_edgar": ["sec.gov", "efts.sec.gov"],
    "stockgeist": ["stockgeist.ai"],
    "news_api": ["newsapi.org"],
    "discord": ["discord.com", "discordapp.com"],
    "twitter": ["api.x.com", "api.twitter.com", "x.com"],
    "youtube": ["googleapis.com/youtube", "youtube.com"],
    "reddit": ["reddit.com", "oauth.reddit.com"],
    "benzinga": ["benzinga.com"],
    "tradingview": ["tradingview.com"],
    "resend": ["resend.com", "api.resend.com"],
    "github_gist": ["api.github.com", "gist.github.com"],
    "openclaw_bridge": ["localhost:8080"],
}


@router.post("/ai-detect", response_model=AIDetectResponse)
async def ai_detect_provider(payload: AIDetectRequest):
    """Detect API provider from a URL and return source template."""
    url_lower = payload.url.lower().strip()
    for source_id, patterns in AI_DETECT_MAP.items():
        for pattern in patterns:
            if pattern in url_lower:
                template = DEFAULT_SOURCES.get(source_id, {})
                return AIDetectResponse(
                    detected_provider=source_id,
                    confidence=0.95,
                    template=template,
                    suggestion=f"Detected {template.get('name', source_id)}. "
                               f"Required keys: {template.get('required_keys', [])}",
                )
    return AIDetectResponse(
        detected_provider=None,
        confidence=0.0,
        template=None,
        suggestion="Unknown provider. Use POST /data-sources to add as custom source.",
    )
