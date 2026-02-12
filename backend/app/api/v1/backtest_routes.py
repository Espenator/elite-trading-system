"""Backtest API: run top-N strategy and return equity curve + metrics (research doc)."""
from datetime import date

from fastapi import APIRouter
from app.strategy.backtest import (
    load_features_and_predictions,
    backtest_top_n,
    load_spy_returns,
    evaluate_backtest,
)

router = APIRouter()


@router.get("/")
def run_backtest(
    start: date,
    end: date,
    model_id: str,
    n_stocks: int = 20,
    min_score: float | None = None,
):
    """
    Run top-N long-only backtest for date range and model_id.
    Returns equity_curve (strategy + SPY) and metrics (Sharpe, max_drawdown, etc.).
    """
    df = load_features_and_predictions(start, end, model_id=model_id)
    if df.empty:
        return {
            "model_id": model_id,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "equity_curve": [],
            "metrics": {
                "strategy_annual_return": 0.0,
                "spy_annual_return": 0.0,
                "strategy_annual_vol": 0.0,
                "spy_annual_vol": 0.0,
                "sharpe": 0.0,
                "max_drawdown": 0.0,
            },
        }
    curve = backtest_top_n(df, n_stocks=n_stocks, min_score=min_score)
    spy_curve = load_spy_returns(start, end)
    metrics = evaluate_backtest(curve, spy_curve)

    merged = curve.merge(
        spy_curve, on="date", how="left", suffixes=("_strategy", "_spy")
    )
    equity_curve = []
    for _, row in merged.iterrows():
        d = row["date"]
        se = row["equity_strategy"] if "equity_strategy" in merged.columns else row["equity"]
        pe = row.get("equity_spy", 1.0) if "equity_spy" in merged.columns else 1.0
        equity_curve.append({
            "date": d.date().isoformat() if hasattr(d, "date") else str(d)[:10],
            "strategy_equity": float(se),
            "spy_equity": float(pe),
        })
    return {
        "model_id": model_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "equity_curve": equity_curve,
        "metrics": metrics,
    }
