"""
OpenClaw Bridge API — Phase 2 (DB-backed)
POST /signals    → ingest batch from OpenClaw PC1
GET  /signals/latest → latest scored signals (DB query)
GET  /health     → bridge health + DB stats
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.openclaw_db import openclaw_db

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
    bridge_version: str = "2.0"
    total_ingests: int
    total_signals: int
    last_ingest: Optional[Dict] = None
    signals_last_24h: int


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


# -- endpoints ----------------------------------------------------------------

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
