"""Inference: load model and generate daily signals (research doc)."""
from datetime import date
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

SEQ_LEN = 60
FEATURE_COLS = ["return_1d", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel"]


def load_model(path: str, num_features: int):
    """Load trained LSTM from .pt file."""
    try:
        import torch
    except ImportError:
        return None
    from app.models.lstm_daily import DailyLSTM
    model = DailyLSTM(num_features=num_features)
    state = torch.load(path, map_location="cpu", weights_only=True)
    model._module.load_state_dict(state)
    model._module.eval()
    return model


def make_signals_for_date(
    model,
    feats: pd.DataFrame,
    feature_cols: List[str],
    as_of: date,
) -> List[Dict[str, Any]]:
    """For each symbol with enough history, compute P(up) and return list of signal dicts."""
    if model is None or feats is None or feats.empty:
        return []
    try:
        import torch
    except ImportError:
        return []

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model._module.to(device)
    signals = []
    feats = feats.copy()
    feats["_dt"] = pd.to_datetime(feats["date"])
    df_day = feats[feats["_dt"] <= pd.Timestamp(as_of)]
    for symbol, g in df_day.groupby("symbol"):
        g = g.sort_values("date")
        if len(g) < SEQ_LEN:
            continue
        window = g.iloc[-SEQ_LEN:][feature_cols]
        if window.isna().any().any():
            continue
        x = torch.tensor(window.values, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            logit = model._module(x)
            prob_up = torch.sigmoid(logit).item()
        signals.append({"symbol": symbol, "date": as_of.isoformat(), "prob_up": prob_up})
    return signals
