"""Signals API: ML predictions for buy/sell timing (research doc)."""
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from app.schemas.signals import Signal, SignalsResponse, ActiveSignalResponse
from app.data.storage import get_conn
from app.models.inference import load_model, make_signals_for_date

router = APIRouter()

FEATURE_COLS = ["return_1d", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel"]
# Model path: backend/models/artifacts or project root models/artifacts
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
MODEL_ARTIFACTS = _BACKEND_DIR / "models" / "artifacts"
DEFAULT_MODEL_PATH = MODEL_ARTIFACTS / "lstm_daily_latest.pt"


def _get_raw_signals_and_feats(as_of: date | None = None):
    """Shared logic: load feats, model, and produce raw signal dicts. Returns (raw_signals, feats) or (None, None) on failure."""
    if as_of is None:
        as_of = date.today()
    try:
        conn = get_conn()
        feats = conn.execute("SELECT * FROM daily_features").df()
        conn.close()
    except Exception:
        return None, None
    if feats is None or feats.empty:
        return None, None
    if not Path(str(DEFAULT_MODEL_PATH)).exists():
        return None, None
    try:
        model = load_model(str(DEFAULT_MODEL_PATH), num_features=len(FEATURE_COLS))
    except Exception:
        return None, None
    raw_signals = make_signals_for_date(model, feats, FEATURE_COLS, as_of)
    return raw_signals, feats


@router.get("/", response_model=SignalsResponse)
def get_signals(as_of: date | None = None):
    """
    Return daily signals (P(up), action) for all symbols with features.
    Uses LSTM model if available; otherwise returns empty list.
    """
    if as_of is None:
        as_of = date.today()
    raw_signals, _ = _get_raw_signals_and_feats(as_of)
    if raw_signals is None:
        return SignalsResponse(as_of=as_of, signals=[])
    signals = []
    for s in raw_signals:
        action = "BUY" if s["prob_up"] > 0.6 else "HOLD"
        signals.append(
            Signal(symbol=s["symbol"], date=as_of, prob_up=s["prob_up"], action=action)
        )
    return SignalsResponse(as_of=as_of, signals=signals)


@router.get("/active/{symbol}", response_model=ActiveSignalResponse)
def get_active_signal(symbol: str, as_of: date | None = None):
    """
    Return the active signal for a single symbol, or 404 if none.
    Used by ExecutionDeck. Includes entry (last close), target/stop placeholders, and confidence.
    """
    symbol = symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol required")
    raw_signals, feats = _get_raw_signals_and_feats(as_of)
    if raw_signals is None:
        raise HTTPException(status_code=404, detail="No signals available")
    match = next((s for s in raw_signals if s["symbol"].upper() == symbol), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"No active signal for {symbol}")
    action = "BUY" if match["prob_up"] > 0.6 else "HOLD"
    # Entry = latest close for this symbol from features
    sym_feats = feats[feats["symbol"].str.upper() == symbol].sort_values("date")
    if sym_feats.empty or "close" not in sym_feats.columns:
        entry = 0.0
    else:
        entry = float(sym_feats["close"].iloc[-1])
    # Simple placeholders when we don't have levels from strategy
    target = entry * 1.02 if entry else 0.0
    stop = entry * 0.98 if entry else 0.0
    risk_reward = 2.0
    as_of_val = as_of if as_of else date.today()
    return ActiveSignalResponse(
        symbol=match["symbol"],
        date=as_of_val,
        prob_up=match["prob_up"],
        action=action,
        entry=entry,
        target=target,
        stop=stop,
        risk_reward=risk_reward,
        type=action,
        confidence=round(match["prob_up"] * 100),
    )
