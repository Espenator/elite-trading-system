"""Top-N long-only daily backtest (research doc)."""
from datetime import date
from typing import Optional

import pandas as pd

from app.data.storage import get_conn


def load_features_and_predictions(start: date, end: date, model_id: str) -> pd.DataFrame:
    """Load daily_features and daily_predictions from DuckDB, merge on symbol/date."""
    conn = get_conn()
    try:
        df_feat = conn.execute(
            """
            SELECT symbol, date, close
            FROM daily_features
            WHERE date BETWEEN ? AND ?
            """,
            [start, end],
        ).df()
        df_pred = conn.execute(
            """
            SELECT symbol, date, score
            FROM daily_predictions
            WHERE model_id = ? AND date BETWEEN ? AND ?
            """,
            [model_id, start, end],
        ).df()
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

    if df_feat.empty or df_pred.empty:
        return pd.DataFrame()
    df_feat["date"] = pd.to_datetime(df_feat["date"])
    df_pred["date"] = pd.to_datetime(df_pred["date"])
    df = pd.merge(df_feat, df_pred, on=["symbol", "date"], how="inner")
    return df.sort_values(["date", "symbol"])


def backtest_top_n(
    df: pd.DataFrame,
    n_stocks: int = 20,
    min_score: Optional[float] = None,
    cost_bps: float = 1.0,
) -> pd.DataFrame:
    """
    Equal-weight top-N long-only backtest. df must have columns: date, symbol, close, score.
    Returns DataFrame with date, equity.
    """
    if df.empty or "score" not in df.columns:
        return pd.DataFrame(columns=["date", "equity"])

    df = df.sort_values(["date", "symbol"]).copy()
    all_dates = sorted(df["date"].unique())
    equity = 1.0
    equity_curve = []
    prev_holdings = set()

    for i in range(len(all_dates) - 1):
        today = all_dates[i]
        tomorrow = all_dates[i + 1]
        df_today = df[df["date"] == today]
        df_tomorrow = df[df["date"] == tomorrow]
        if df_today.empty or df_tomorrow.empty:
            equity_curve.append({"date": tomorrow, "equity": equity})
            prev_holdings = set()
            continue

        df_today_sorted = df_today.sort_values("score", ascending=False)
        if min_score is not None:
            df_today_sorted = df_today_sorted[df_today_sorted["score"] >= min_score]
        picks = df_today_sorted.head(n_stocks)["symbol"].tolist()
        if not picks:
            equity_curve.append({"date": tomorrow, "equity": equity})
            prev_holdings = set()
            continue

        weight = 1.0 / len(picks)
        df_join = (
            df_today[df_today["symbol"].isin(picks)][["symbol", "close"]]
            .merge(
                df_tomorrow[df_tomorrow["symbol"].isin(picks)][["symbol", "close"]],
                on="symbol",
                suffixes=("_today", "_tomorrow"),
            )
        )
        if df_join.empty:
            equity_curve.append({"date": tomorrow, "equity": equity})
            prev_holdings = set()
            continue

        returns = df_join["close_tomorrow"] / df_join["close_today"] - 1.0
        port_ret = (weight * returns).sum()
        holdings = set(df_join["symbol"])
        traded_symbols = holdings.symmetric_difference(prev_holdings)
        turnover_frac = len(traded_symbols) / max(len(holdings), 1)
        cost = turnover_frac * (cost_bps / 10000.0) * 2.0
        net_ret = port_ret - cost
        equity *= 1.0 + net_ret
        equity_curve.append({"date": tomorrow, "equity": equity})
        prev_holdings = holdings

    return pd.DataFrame(equity_curve)


def load_spy_returns(start: date, end: date) -> pd.DataFrame:
    """Load SPY equity curve from daily_features (symbol = 'SPY')."""
    conn = get_conn()
    try:
        df = conn.execute(
            """
            SELECT date, close
            FROM daily_features
            WHERE symbol = 'SPY' AND date BETWEEN ? AND ?
            ORDER BY date
            """,
            [start, end],
        ).df()
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()
    if df.empty:
        return pd.DataFrame(columns=["date", "equity"])
    df["date"] = pd.to_datetime(df["date"])
    df["ret"] = df["close"].pct_change()
    df["equity"] = (1 + df["ret"].fillna(0)).cumprod()
    return df[["date", "equity"]]


def evaluate_backtest(curve_df: pd.DataFrame, spy_df: pd.DataFrame) -> dict:
    """Compute strategy vs SPY metrics: annual return, vol, Sharpe, max drawdown."""
    if curve_df.empty or spy_df.empty:
        return {
            "strategy_annual_return": 0.0,
            "spy_annual_return": 0.0,
            "strategy_annual_vol": 0.0,
            "spy_annual_vol": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
        }
    df = curve_df.merge(spy_df, on="date", how="inner", suffixes=("_strategy", "_spy"))
    df["ret_strategy"] = df["equity_strategy"].pct_change().fillna(0.0)
    df["ret_spy"] = df["equity_spy"].pct_change().fillna(0.0)
    periods_per_year = 252

    def ann_return(series):
        mean_daily = series.mean()
        return (1 + mean_daily) ** periods_per_year - 1

    def ann_vol(series):
        return series.std() * (periods_per_year ** 0.5)

    strat_ar = ann_return(df["ret_strategy"])
    spy_ar = ann_return(df["ret_spy"])
    strat_vol = ann_vol(df["ret_strategy"])
    spy_vol = ann_vol(df["ret_spy"])
    sharpe = strat_ar / strat_vol if strat_vol > 0 else 0.0
    max_equity = df["equity_strategy"].cummax()
    drawdown = df["equity_strategy"] / max_equity - 1.0
    max_dd = drawdown.min()
    return {
        "strategy_annual_return": round(float(strat_ar), 4),
        "spy_annual_return": round(float(spy_ar), 4),
        "strategy_annual_vol": round(float(strat_vol), 4),
        "spy_annual_vol": round(float(spy_vol), 4),
        "sharpe": round(float(sharpe), 4),
        "max_drawdown": round(float(max_dd), 4),
    }
