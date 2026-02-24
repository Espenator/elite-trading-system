"""OpenClaw Bridge API: receive composite scores, regime state, and signals from OpenClaw (PC1).

This is the ingest endpoint for the Apex Predator convergence architecture.
OpenClaw pushes batch signals here after each scan cycle; Elite Trader persists
them and exposes them through the existing /api/v1/signals UI flow.

Ref: openclaw Issue #8 - Phase 1 Bridge API
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_OPENCLAW_DIR = _DATA_DIR / "openclaw"


def _ensure_dirs():
    _OPENCLAW_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Pydantic v1 contract schemas
# ---------------------------------------------------------------------------

class RegimeIn(BaseModel):
    """Market regime snapshot from OpenClaw HMM."""
    state: Literal["GREEN", "YELLOW", "RED"]
    confidence: Optional[float] = None
    source: Optional[str] = None


class OpenClawSignalIn(BaseModel):
    """Single scored signal from OpenClaw composite scorer."""
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
    """Batch ingest payload from an OpenClaw scan cycle."""
    run_id: str
    timestamp: datetime
    regime: Optional[RegimeIn] = None
    universe: Optional[Dict[str, Any]] = None
    signals: List[OpenClawSignalIn]


class IngestOut(BaseModel):
    run_id: str
    accepted: int


class HealthOut(BaseModel):
    status: str
    regime: Optional[Dict[str, Any]] = None
    last_run_id: Optional[str] = None
    last_ingest: Optional[str] = None
    total_signals_stored: int = 0


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _auth(token: Optional[str], expected: Optional[str]):
    """Validate bridge token if one is configured."""
    if expected and token != expected:
        raise HTTPException(status_code=401, detail="Invalid bridge token")


# ---------------------------------------------------------------------------
# Module state (latest ingest for /health)
# ---------------------------------------------------------------------------
_last_run_id: Optional[str] = None
_last_ingest: Optional[str] = None
_last_regime: Optional[Dict] = None
_total_signals: int = 0


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/signals", response_model=IngestOut)
async def ingest_openclaw_signals(
    payload: OpenClawIngestIn,
    x_openclaw_token: Optional[str] = Header(default=None),
):
    """
    Receive a batch of scored signals from OpenClaw.

    OpenClaw calls this after each scan cycle with composite scores,
    regime state, and trade recommendations.
    """
    global _last_run_id, _last_ingest, _last_regime, _total_signals

    # Auth
    expected = os.getenv("OPENCLAW_BRIDGE_TOKEN")
    _auth(x_openclaw_token, expected)

    # Persist to JSON (simple file store for Phase 1; migrate to SQLite in Phase 2)
    _ensure_dirs()
    ts_slug = payload.timestamp.strftime("%Y%m%d_%H%M%S")
    out_path = _OPENCLAW_DIR / f"ingest_{ts_slug}_{payload.run_id[:32]}.json"

    record = {
        "run_id": payload.run_id,
        "timestamp": payload.timestamp.isoformat(),
        "regime": payload.regime.model_dump() if payload.regime else None,
        "universe": payload.universe,
        "signals": [s.model_dump() for s in payload.signals],
    }

    try:
        out_path.write_text(json.dumps(record, indent=2, default=str))
        logger.info(
            "[OpenClaw] Ingested %d signals from run %s -> %s",
            len(payload.signals), payload.run_id, out_path.name,
        )
    except Exception as exc:
        logger.error("[OpenClaw] Failed to persist ingest: %s", exc)
        raise HTTPException(status_code=500, detail="Persistence failed")

    # Update module state
    _last_run_id = payload.run_id
    _last_ingest = payload.timestamp.isoformat()
    _last_regime = payload.regime.model_dump() if payload.regime else None
    _total_signals += len(payload.signals)

    return IngestOut(run_id=payload.run_id, accepted=len(payload.signals))


@router.get("/health", response_model=HealthOut)
async def openclaw_health():
    """Health/status endpoint for the OpenClaw bridge."""
    return HealthOut(
        status="ok",
        regime=_last_regime,
        last_run_id=_last_run_id,
        last_ingest=_last_ingest,
        total_signals_stored=_total_signals,
    )


@router.get("/signals/latest")
async def get_latest_openclaw_signals():
    """Return the most recent OpenClaw ingest payload."""
    _ensure_dirs()
    files = sorted(_OPENCLAW_DIR.glob("ingest_*.json"), reverse=True)
    if not files:
        return {"signals": [], "message": "No OpenClaw ingests yet"}
    try:
        data = json.loads(files[0].read_text())
        return data
    except Exception as exc:
        logger.error("[OpenClaw] Failed to read latest ingest: %s", exc)
        raise HTTPException(status_code=500, detail="Read failed")
