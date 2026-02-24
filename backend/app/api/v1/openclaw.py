"""
OpenClaw Bridge API — Phase 2.1 (DB-backed + ClawBot Panel endpoints)

POST /signals      → ingest batch from OpenClaw PC1
GET  /signals/latest → latest scored signals (DB query)
GET  /health       → bridge health + DB stats
GET  /macro        → Macro Brain state (wave gauge + regime)
GET  /swarm-status → active clawbot team count and states
POST /macro/override → operator bias slider adjustment
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.openclaw_db import openclaw_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["openclaw"])


# -- request / response schemas -----------------------------------------------

class RegimeIn(BaseModel):
    state: Literal["GREEN", "YELLOW", "RED"]
    confidence: Optional[float] = None
    source: Optional[str] = None


class OpenClawSignalIn(BaseModel):
    symbol: str = Field(..., min_length=1)
    direction: Literal["LONG", "SHORT"]
    score: float
    subscores: Optional[Dict[str, float]] = None
    entry: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None
    timeframe: Optional[str] = None
    reasons: Optional[List[str]] = None
    raw: Optional[Dict[str, Any]] = None


class OpenClawIngestIn(BaseModel):
    run_id: str
    timestamp: datetime
    regime: Optional[RegimeIn] = None
    universe: Optional[Dict[str, Any]] = None
    signals: List[OpenClawSignalIn]


class IngestOut(BaseModel):
    run_id: str
    accepted: int
    ingest_id: int


class SignalOut(BaseModel):
    id: int
    symbol: str
    direction: str
    score: float
    subscores: Optional[Dict] = None
    entry: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None
    timeframe: Optional[str] = None
    reasons: Optional[List[str]] = None
    regime_state: Optional[str] = None
    regime_confidence: Optional[float] = None
    received_at: str
    run_id: str


class HealthOut(BaseModel):
    status: str
    bridge_version: str = "2.1"
    total_ingests: int
    total_signals: int
    last_ingest: Optional[Dict] = None
    signals_last_24h: int


# -- ClawBot Panel schemas (Phase 2.1) ----------------------------------------

class MacroOut(BaseModel):
    """Macro Brain state for wave gauge + regime banner."""
    oscillator: float = 0.0
    wave_state: str = "NEUTRAL"
    bias: float = 1.0
    regime: str = "YELLOW"
    vix: Optional[float] = None
    hy_spread: Optional[float] = None
    fear_greed_index: Optional[int] = None


class SwarmTeamOut(BaseModel):
    id: str
    status: str
    agents: List[str] = []


class SwarmStatusOut(BaseModel):
    """Active clawbot team count and states."""
    active: int = 0
    total: int = 0
    teams: List[SwarmTeamOut] = []


class MacroOverrideIn(BaseModel):
    """Operator bias slider adjustment."""
    bias_multiplier: float = Field(..., ge=0.0, le=5.0)


class MacroOverrideOut(BaseModel):
    success: bool
    bias_multiplier: float
    message: str


# -- auth helper --------------------------------------------------------------

def _check_token(token: Optional[str]):
    expected = settings.OPENCLAW_BRIDGE_TOKEN
    if expected and expected.strip():
        if not token or token != expected:
            raise HTTPException(status_code=401, detail="Invalid or missing X-OpenClaw-Token")


# -- helpers ------------------------------------------------------------------

def _payload_hash(payload: OpenClawIngestIn) -> str:
    raw = json.dumps(payload.model_dump(), default=str, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _row_to_signal(row: Dict) -> Dict:
    """Normalise a DB row dict into the SignalOut shape."""
    out = dict(row)
    # deserialise JSON columns
    for col, key in [("subscores_json", "subscores"),
                     ("reasons_json", "reasons")]:
        val = out.pop(col, None)
        out[key] = json.loads(val) if val else None
    # drop internal columns the client doesn't need
    out.pop("raw_json", None)
    out.pop("ingest_id", None)
    return out


async def _proxy_get(path: str) -> Optional[Dict]:
    """Forward a GET request to OpenClaw PC1 and return JSON or None."""
    base = settings.OPENCLAW_API_URL
    if not base:
        return None
    url = f"{base.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {}
            if settings.OPENCLAW_BRIDGE_TOKEN:
                headers["X-OpenClaw-Token"] = settings.OPENCLAW_BRIDGE_TOKEN
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("proxy GET %s failed: %s", url, exc)
        return None


async def _proxy_post(path: str, body: Dict) -> Optional[Dict]:
    """Forward a POST request to OpenClaw PC1 and return JSON or None."""
    base = settings.OPENCLAW_API_URL
    if not base:
        return None
    url = f"{base.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Content-Type": "application/json"}
            if settings.OPENCLAW_BRIDGE_TOKEN:
                headers["X-OpenClaw-Token"] = settings.OPENCLAW_BRIDGE_TOKEN
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("proxy POST %s failed: %s", url, exc)
        return None


# -- endpoints (existing) -----------------------------------------------------

@router.post("/signals", response_model=IngestOut)
async def ingest_openclaw_signals(
    payload: OpenClawIngestIn,
    x_openclaw_token: Optional[str] = Header(default=None),
):
    """Receive a batch of scored signals from OpenClaw (PC1)."""
    _check_token(x_openclaw_token)

    regime_dict = payload.regime.model_dump() if payload.regime else None
    universe_dict = payload.universe

    ingest_id = openclaw_db.insert_ingest(
        run_id=payload.run_id,
        timestamp=payload.timestamp.isoformat(),
        regime=regime_dict,
        universe=universe_dict,
        signal_count=len(payload.signals),
        payload_hash=_payload_hash(payload),
    )

    signals_dicts = [s.model_dump() for s in payload.signals]
    accepted = openclaw_db.insert_signals(ingest_id, payload.run_id, signals_dicts)

    return IngestOut(run_id=payload.run_id, accepted=accepted, ingest_id=ingest_id)


@router.get("/signals/latest")
async def get_latest_signals(
    limit: int = 50,
    symbol: Optional[str] = None,
    x_openclaw_token: Optional[str] = Header(default=None),
):
    """Return the most recent OpenClaw signals from DB."""
    _check_token(x_openclaw_token)
    if symbol:
        rows = openclaw_db.get_signals_by_symbol(symbol, limit=limit)
    else:
        rows = openclaw_db.get_latest_signals(limit=limit)
    return [_row_to_signal(r) for r in rows]


@router.get("/health", response_model=HealthOut)
async def bridge_health():
    """Bridge health check — no auth required."""
    last = openclaw_db.get_latest_ingest()
    since_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
    history = openclaw_db.get_ingest_history(limit=1000)
    total_ingests = len(history)  # cheap for now
    total_signals = openclaw_db.count_signals()
    signals_24h = openclaw_db.count_signals(since=since_24h)

    status = "operational"
    if last:
        age_minutes = (
            datetime.utcnow()
            - datetime.fromisoformat(last["received_at"].replace("Z", ""))
        ).total_seconds() / 60
        if age_minutes > 60:
            status = "stale"

    return HealthOut(
        status=status,
        total_ingests=total_ingests,
        total_signals=total_signals,
        last_ingest=last,
        signals_last_24h=signals_24h,
    )


# -- ClawBot Panel endpoints (Phase 2.1) --------------------------------------

@router.get("/macro", response_model=MacroOut)
async def get_macro_state(
    x_openclaw_token: Optional[str] = Header(default=None),
):
    """
    Macro Brain state for the wave gauge + regime banner.

    Proxies to OpenClaw PC1 /api/v1/openclaw/macro when OPENCLAW_API_URL is
    configured.  Falls back to the latest regime data stored in the local
    ingest DB so the frontend always gets *something*.
    """
    _check_token(x_openclaw_token)

    # --- try live data from PC1 first ---
    live = await _proxy_get("/api/v1/openclaw/macro")
    if live:
        return MacroOut(**live)

    # --- fallback: derive from latest ingest regime stored in DB ---
    last = openclaw_db.get_latest_ingest()
    if last:
        regime_json = last.get("regime_json")
        regime = json.loads(regime_json) if regime_json else {}
        return MacroOut(
            oscillator=regime.get("confidence", 0.0),
            wave_state=regime.get("source", "NEUTRAL"),
            bias=1.0,
            regime=regime.get("state", "YELLOW"),
        )

    # --- no data at all ---
    return MacroOut()


@router.get("/swarm-status", response_model=SwarmStatusOut)
async def get_swarm_status(
    x_openclaw_token: Optional[str] = Header(default=None),
):
    """
    Active clawbot team count and states.

    Proxies to OpenClaw PC1 /api/v1/openclaw/swarm-status.  Returns an empty
    swarm payload when PC1 is unreachable so the frontend can still render.
    """
    _check_token(x_openclaw_token)

    live = await _proxy_get("/api/v1/openclaw/swarm-status")
    if live:
        return SwarmStatusOut(**live)

    # --- offline fallback ---
    return SwarmStatusOut()


@router.post("/macro/override", response_model=MacroOverrideOut)
async def macro_override(
    body: MacroOverrideIn,
    x_openclaw_token: Optional[str] = Header(default=None),
):
    """
    Operator bias slider adjustment.

    Forwards the bias_multiplier to OpenClaw PC1 which applies it to the
    composite scorer in real-time.  Returns an error if PC1 is unreachable
    since the override must actually take effect.
    """
    _check_token(x_openclaw_token)

    result = await _proxy_post(
        "/api/v1/openclaw/macro/override",
        {"bias_multiplier": body.bias_multiplier},
    )
    if result:
        return MacroOverrideOut(**result)

    raise HTTPException(
        status_code=503,
        detail=(
            "OpenClaw PC1 is unreachable — cannot apply bias override. "
            "Ensure OPENCLAW_API_URL is configured and PC1 is running."
        ),
    )
