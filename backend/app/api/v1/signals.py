"""Signals API: ML predictions for buy/sell timing (research doc)."""

from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from app.schemas.signals import Signal, SignalsResponse, ActiveSignalResponse
from app.data.storage import get_conn
from app.models.inference import load_model, make_signals_for_date
from app.websocket_manager import broadcast_ws

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


# Stub signals when ML model / features are not available (for demo and UI development)
_STUB_SIGNALS = [
    ("AAPL", 0.72, "BUY"),
    ("MSFT", 0.68, "BUY"),
    ("NVDA", 0.55, "HOLD"),
    ("TSLA", 0.78, "BUY"),
    ("SPY", 0.62, "BUY"),
    ("GOOGL", 0.58, "HOLD"),
    ("META", 0.65, "BUY"),
    ("AMD", 0.71, "BUY"),
]


@router.get("/", response_model=SignalsResponse)
async def get_signals(as_of: date | None = None):
    """
    Return daily signals (P(up), action) for all symbols with features.
    Uses LSTM model if available; otherwise returns stub signals for demo.
    Note: When signals are generated (e.g., by background task), call:
        await broadcast_ws("signals", {"type": "signals_updated", "count": len(signals)})
    """
    if as_of is None:
        as_of = date.today()
    raw_signals, _ = _get_raw_signals_and_feats(as_of)
    if raw_signals is None or len(raw_signals) == 0:
        # Fallback: stub signals so Signal Intelligence page shows cards
        signals = [
            Signal(symbol=sym, date=as_of, prob_up=prob, action=act)
            for sym, prob, act in _STUB_SIGNALS
        ]
        return SignalsResponse(as_of=as_of, signals=signals)
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


@router.get("/heatmap")
async def get_signals_heatmap():
    """
    Return composite scores for heatmap visualization.
    Note: When heatmap data updates, call:
        await broadcast_ws("signals", {"type": "heatmap_updated"})
    """
    """
    Return composite scores for heatmap visualization.
    Includes technical, ML, sentiment, volume, and AI reasoning components.
    Used by Signal Heatmap page.
    """
    # Get signals
    raw_signals, feats = _get_raw_signals_and_feats()

    # Stub heatmap data structure
    stub_heatmap = [
        {
            "ticker": "NVDA",
            "sector": "Technology",
            "compositeScore": 87.5,
            "aiAnalysis": "Strong bullish pattern + positive sentiment + ML confidence",
            "components": {
                "technical": 85,
                "ml": 92,
                "sentiment": 88,
                "volume": 82,
                "aiReasoning": 90,
            },
            "expectedMove": 4.2,
            "confidence": 0.89,
            "profitPotential": "HIGH",
            "timeframe": "1-3 days",
        },
        {
            "ticker": "MSFT",
            "sector": "Technology",
            "compositeScore": 82.3,
            "aiAnalysis": "Bullish momentum with high ML confidence",
            "components": {
                "technical": 80,
                "ml": 85,
                "sentiment": 78,
                "volume": 75,
                "aiReasoning": 88,
            },
            "expectedMove": 3.5,
            "confidence": 0.85,
            "profitPotential": "HIGH",
            "timeframe": "1-3 days",
        },
        {
            "ticker": "AAPL",
            "sector": "Technology",
            "compositeScore": 75.8,
            "aiAnalysis": "Moderate bullish signal with mixed sentiment",
            "components": {
                "technical": 72,
                "ml": 78,
                "sentiment": 70,
                "volume": 68,
                "aiReasoning": 75,
            },
            "expectedMove": 2.8,
            "confidence": 0.72,
            "profitPotential": "MODERATE",
            "timeframe": "2-5 days",
        },
        {
            "ticker": "TSLA",
            "sector": "Consumer Cyclical",
            "compositeScore": 68.2,
            "aiAnalysis": "Neutral to bullish with volatility concerns",
            "components": {
                "technical": 65,
                "ml": 70,
                "sentiment": 65,
                "volume": 72,
                "aiReasoning": 68,
            },
            "expectedMove": 2.1,
            "confidence": 0.65,
            "profitPotential": "MODERATE",
            "timeframe": "3-7 days",
        },
        {
            "ticker": "AMD",
            "sector": "Technology",
            "compositeScore": 79.5,
            "aiAnalysis": "Strong technical setup with good ML support",
            "components": {
                "technical": 78,
                "ml": 82,
                "sentiment": 75,
                "volume": 80,
                "aiReasoning": 77,
            },
            "expectedMove": 3.2,
            "confidence": 0.78,
            "profitPotential": "HIGH",
            "timeframe": "1-3 days",
        },
    ]

    # If we have real signals, transform them; otherwise return stub
    if raw_signals and len(raw_signals) > 0:
        # Transform real signals to heatmap format
        heatmap_data = []
        for sig in raw_signals[:20]:  # Limit to top 20
            prob_up = sig.get("prob_up", 0.5)
            composite_score = prob_up * 100
            heatmap_data.append(
                {
                    "ticker": sig.get("symbol", "UNKNOWN"),
                    "sector": "Technology",  # Would come from real data
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
    return stub_heatmap
