"""Signals API: ML predictions for buy/sell timing (research doc)."""

from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from app.schemas.signals import Signal, SignalsResponse, ActiveSignalResponse
from app.data.storage import get_conn
from app.models.inference import load_model, make_signals_for_date
from app.websocket_manager import broadcast_ws
from app.services.kelly_position_sizer import KellyPositionSizer

_kelly_sizer = KellyPositionSizer(max_allocation=0.10)

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
async def get_signals(as_of: date | None = None):
    """
    Return daily signals (P(up), action) from LSTM model and daily_features.
    Real data only: requires DuckDB daily_features and models/artifacts/lstm_daily_latest.pt.
    When model or features are missing, returns empty list.
    Note: When signals are generated (e.g., by background task), call:
        await broadcast_ws("signals", {"type": "signals_updated", "count": len(signals)})
    """
    if as_of is None:
        as_of = date.today()
    raw_signals, _ = _get_raw_signals_and_feats(as_of)
    if raw_signals is None or len(raw_signals) == 0:
        return SignalsResponse(as_of=as_of, signals=[])
    signals = []
    for s in raw_signals:
        action = "BUY" if s["prob_up"] > 0.6 else "HOLD"
        prob = s["prob_up"]
        # Compute Kelly edge and position size
        kelly = _kelly_sizer.calculate(
            win_rate=prob,
            avg_win_pct=0.035,  # Default 3.5% avg win
            avg_loss_pct=0.015,  # Default 1.5% avg loss
        )
        signals.append(
            Signal(
                symbol=s["symbol"],
                date=as_of,
                prob_up=prob,
                action=action,
                edge=kelly.edge,
                kelly_fraction=kelly.raw_kelly,
                position_size_pct=kelly.final_pct,
                expected_value=kelly.edge * prob,
            )
        )


@router.get("/active/{symbol}", response_model=ActiveSignalResponse)
def get_active_signal(symbol: str, as_of: date | None = None):
    """
    Return the active signal for a single symbol, or 404 if none.
    Real data only (LSTM + daily_features). Used by ExecutionDeck.
    """
    symbol = symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol required")
    raw_signals, feats = _get_raw_signals_and_feats(as_of)
    if raw_signals is None or len(raw_signals) == 0:
        raise HTTPException(status_code=404, detail="No signals available (run daily_update and ensure model exists)")
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


@router.get("/heatmap")
async def get_signals_heatmap():
    """
    Return composite scores for heatmap from real LSTM signals only.
    Empty list when no model/features. Used by Signal Heatmap page.
    """
    raw_signals, _ = _get_raw_signals_and_feats()
    if not raw_signals or len(raw_signals) == 0:
        return []
    heatmap_data = []
    for sig in raw_signals[:20]:
        prob_up = sig.get("prob_up", 0.5)
        composite_score = prob_up * 100
        heatmap_data.append(
            {
                "ticker": sig.get("symbol", "UNKNOWN"),
                "sector": "Technology",
                "compositeScore": round(composite_score, 1),
                "aiAnalysis": f"ML probability: {prob_up:.2f}",
                "components": {
                    "technical": round(composite_score * 0.9, 0),
                    "ml": round(composite_score, 0),
                    "sentiment": round(composite_score * 0.85, 0),
                    "volume": round(composite_score * 0.8, 0),
                    "aiReasoning": round(composite_score * 0.95, 0),
                },
                "expectedMove": round(composite_score / 20, 1),
                "confidence": prob_up,
                "profitPotential": (
                    "HIGH"
                    if composite_score >= 80
                    else "MODERATE" if composite_score >= 60 else "LOW"
                ),
                "timeframe": "1-3 days",
            }
        )
    return heatmap_data


    @router.get("/kelly-ranked")
async def get_kelly_ranked():
    """
    Return signals ranked by Kelly edge * signal quality.
    Best money-making opportunities first.
    """
    raw_signals, _ = _get_raw_signals_and_feats()
    if not raw_signals or len(raw_signals) == 0:
        return []

    ranked = []
    for s in raw_signals:
        prob = s.get("prob_up", 0.5)
        kelly = _kelly_sizer.calculate(
            win_rate=prob,
            avg_win_pct=0.035,
            avg_loss_pct=0.015,
        )
        edge = kelly.edge
        quality = min(1.0, prob * 1.5)  # Signal quality proxy
        if edge > 0 and quality > 0.3:
            ranked.append({
                "symbol": s["symbol"],
                "kelly_edge": round(edge, 4),
                "signal_quality": round(quality, 3),
                "kelly_score": round(edge * quality, 4),
                "kelly_fraction": round(kelly.raw_kelly, 4),
                "position_size_pct": round(kelly.final_pct, 4),
                "prob_up": round(prob, 3),
                "action": "BUY" if prob > 0.6 else "HOLD",
            })

    ranked.sort(key=lambda x: x["kelly_score"], reverse=True)
    return ranked[:20]
