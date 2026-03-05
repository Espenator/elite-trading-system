"""Label generation for 5-day forward return and direction (research doc)."""
import numpy as np
import pandas as pd


def build_labels(feats: pd.DataFrame, threshold: float = 0.0) -> pd.DataFrame:
    """
    Add 5-day forward return and binary direction label to a features DataFrame.
    Expects columns: symbol, date, close, and feature columns.
    Adds: fwd_ret_5d, y_direction (1 if fwd_ret_5d > threshold else 0).
    """
    if feats.empty or "close" not in feats.columns:
        return feats.copy()

    df = feats.sort_values(["symbol", "date"]).copy()
    df["fwd_close_5d"] = df.groupby("symbol")["close"].shift(-5)
    df["fwd_ret_5d"] = np.log(df["fwd_close_5d"] / df["close"].replace(0, np.nan))
    df["y_direction"] = (df["fwd_ret_5d"] > threshold).astype("int8")
    return df
