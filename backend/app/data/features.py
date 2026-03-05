"""Feature engineering for daily bars (research doc: returns, MAs, volatility, volume)."""
import pandas as pd
import numpy as np


def build_features(bars: pd.DataFrame) -> pd.DataFrame:
    """
    Build daily features from OHLCV bars. Expects columns: symbol, date, open, high, low, close, volume.
    Returns DataFrame with symbol, date, close, return_1d, return_5d, ma_10, ma_20, ma_10_dist, ma_20_dist, vol_20, vol_rel.
    """
    if bars.empty or "close" not in bars.columns:
        return pd.DataFrame()

    df = bars.sort_values(["symbol", "date"]).copy()
    df["return_1d"] = df.groupby("symbol")["close"].pct_change()
    df["return_5d"] = df.groupby("symbol")["close"].pct_change(5)
    df["ma_10"] = df.groupby("symbol")["close"].transform(lambda s: s.rolling(10, min_periods=1).mean())
    df["ma_20"] = df.groupby("symbol")["close"].transform(lambda s: s.rolling(20, min_periods=1).mean())
    df["vol_20"] = df.groupby("symbol")["return_1d"].transform(lambda s: s.rolling(20, min_periods=1).std())
    df["vol_rel"] = df.groupby("symbol")["volume"].transform(
        lambda s: s / s.rolling(20, min_periods=1).mean().replace(0, np.nan)
    )
    df["ma_10_dist"] = (df["close"] / df["ma_10"]).replace([np.inf, -np.inf], np.nan) - 1
    df["ma_20_dist"] = (df["close"] / df["ma_20"]).replace([np.inf, -np.inf], np.nan) - 1
    return df
