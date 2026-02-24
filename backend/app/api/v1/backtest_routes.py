"""Backtest API: run top-N strategy and return equity curve + metrics (research doc).

Includes:
  GET  /           - existing top-N long-only backtest (strategy/backtest.py)
  POST /run        - OpenClaw signal-based historical backtest (services/backtest_engine.py)
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.strategy.backtest import (
    load_features_and_predictions,
    backtest_top_n,
    load_spy_returns,
    evaluate_backtest,
)
from app.services.backtest_engine import backtest_engine

router = APIRouter()


# ── Existing GET endpoint (top-N strategy backtest) ──────────────────────


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


# ── New POST endpoint (OpenClaw signal backtest) ─────────────────────────


class SignalBacktestRequest(BaseModel):
    symbol: Optional[str] = None
    start_date: str
    end_date: str
    strategy: str = "composite"
    initial_equity: float = 100_000.0
    shares_per_trade: int = 100


class SignalBacktestResponse(BaseModel):
    symbol: str
    strategy: str
    period: str
    trades: int
    winrate: float
    sharpe: float
    maxdd: float
    calmar: float
    avg_r: float
    total_pnl: float
    initial_equity: float
    final_equity: float


@router.post("/run", response_model=SignalBacktestResponse)
async def run_signal_backtest(req: SignalBacktestRequest):
    """Run backtest on historical OpenClaw signals (entry/stop/target R-multiple sim)."""
    result = backtest_engine.run_backtest(
        symbol=req.symbol,
        start_date=req.start_date,
        end_date=req.end_date,
        strategy=req.strategy,
        initial_equity=req.initial_equity,
        shares_per_trade=req.shares_per_trade,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/run/detail")
async def run_signal_backtest_detail(req: SignalBacktestRequest):
    """Same as /run but includes full trades_detail list."""
    result = backtest_engine.run_backtest(
        symbol=req.symbol,
        start_date=req.start_date,
        end_date=req.end_date,
        strategy=req.strategy,
        initial_equity=req.initial_equity,
        shares_per_trade=req.shares_per_trade,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
