"""Backtest API: run top-N strategy and return equity curve + metrics (research doc)."""

from datetime import date
from pydantic import BaseModel

from app.strategy.backtest import (
    load_features_and_predictions,
    backtest_top_n,
    load_spy_returns,
    evaluate_backtest,
)
from fastapi import APIRouter, HTTPException
from app.websocket_manager import broadcast_ws

router = APIRouter()


class BacktestRequest(BaseModel):
    strategy: str
    startDate: str
    endDate: str
    assets: str | None = None
    capital: float | None = None
    paramA: float | None = None
    paramBMin: float | None = None
    paramBMax: float | None = None
    runMode: str = "single"
    useKelly: bool = False
    kellyFraction: float = 0.5  # Half-Kelly default


@router.get("/runs")
def get_backtest_runs():
    """
    Return list of recent backtest runs (stub). Used by Backtesting page for run history.
    """
    return {
        "runs": [
            {"id": "R001", "strategy": "MeanReversionV2", "status": "Running"},
            {"id": "R002", "strategy": "ArbitrageAlpha", "status": "Completed"},
            {"id": "R003", "strategy": "TrendFollowerV1", "status": "Failed"},
            {"id": "R004", "strategy": "VolSurfaceBeta", "status": "Running"},
        ],
        "runHistory": [
            {"date": "2023-11-28", "strategy": "MeanReversionV1", "pnl": 5200},
            {"date": "2023-11-20", "strategy": "ArbitrageAlpha", "pnl": 3150},
            {"date": "2023-11-15", "strategy": "TrendFollowerV1", "pnl": -1800},
        ],
    }


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
        se = (
            row["equity_strategy"]
            if "equity_strategy" in merged.columns
            else row["equity"]
        )
        pe = row.get("equity_spy", 1.0) if "equity_spy" in merged.columns else 1.0
        equity_curve.append(
            {
                "date": d.date().isoformat() if hasattr(d, "date") else str(d)[:10],
                "strategy_equity": float(se),
                "spy_equity": float(pe),
            }
        )
    return {
        "model_id": model_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "equity_curve": equity_curve,
        "metrics": metrics,
    }


@router.post("/")
async def run_backtest_post(request: BacktestRequest):
    """
    Run a backtest with configuration from request body.
    Broadcasts status updates via WebSocket.
    """
    try:
        start = date.fromisoformat(request.startDate)
        end = date.fromisoformat(request.endDate)

        # Broadcast start
        await broadcast_ws(
            "backtest",
            {
                "type": "backtest_started",
                "strategy": request.strategy,
                "startDate": request.startDate,
                "endDate": request.endDate,
            },
        )

        # Run backtest (simplified - use GET endpoint logic)
        model_id = "lstm_daily_latest"  # Default model
        n_stocks = 20
        df = load_features_and_predictions(start, end, model_id=model_id)

        if df.empty:
            result = {
                "ok": True,
                "runId": f"R{len(df) if df is not None else 0:03d}",
                "strategy": request.strategy,
                "status": "completed",
                "message": "No data available for date range",
            }
        else:
            curve = backtest_top_n(df, n_stocks=n_stocks)
            spy_curve = load_spy_returns(start, end)
            metrics = evaluate_backtest(curve, spy_curve)

            result = {
                "ok": True,
                "runId": f"R{hash(request.strategy + request.startDate) % 1000:03d}",
                "strategy": request.strategy,
                "status": "completed",
                "metrics": metrics,
            }

        # Broadcast completion
        await broadcast_ws(
            "backtest",
            {
                "type": "backtest_completed",
                "runId": result["runId"],
                "strategy": request.strategy,
            },
        )

        return result
    except Exception as e:
        await broadcast_ws(
            "backtest",
            {
                "type": "backtest_failed",
                "strategy": request.strategy,
                "error": str(e),
            },
        )
        return {
            "ok": False,
            "error": str(e),
        }


# -----------------------------------------------------------------
# Kelly A/B Comparison: run same backtest with and without Kelly sizing
# -----------------------------------------------------------------
from app.services.backtest_engine import BacktestEngine
^        [a-zA-Z_]+: .+ = _bt_engine = BacktestEngine()


@router.post("/compare-kelly")
async def compare_kelly_sizing(request: BacktestRequest):
    """
    Run identical backtest twice: fixed sizing vs Kelly sizing.
    Returns side-by-side metrics so user can see Kelly impact.
    """
    try:
        start = request.startDate
        end = request.endDate
        capital = request.capital or 100_000.0

        # Fixed sizing run
        fixed_result = _bt_engine.run_backtest(
            symbol=request.assets,
            start_date=start,
            end_date=end,
            strategy=request.strategy,
            initial_equity=capital,
            shares_per_trade=100,
            use_kelly=False,
        )

        # Kelly sizing run
        kelly_result = _bt_engine.run_backtest(
            symbol=request.assets,
            start_date=start,
            end_date=end,
            strategy=request.strategy,
            initial_equity=capital,
            use_kelly=True,
            kelly_fraction=request.kellyFraction,
        )

        return {
            "ok": True,
            "fixed_sizing": fixed_result,
            "kelly_sizing": kelly_result,
            "kelly_fraction": request.kellyFraction,
            "improvement": {
                "pnl_delta": (
                    kelly_result.get("metrics", {}).get("total_pnl", 0)
                    - fixed_result.get("metrics", {}).get("total_pnl", 0)
                ),
                "sharpe_delta": (
                    kelly_result.get("metrics", {}).get("sharpe", 0)
                    - fixed_result.get("metrics", {}).get("sharpe", 0)
                ),
            },
                        "profit_factor_delta": (
                kelly_result.get("metrics", {}).get("profit_factor", 0)
                - fixed_result.get("metrics", {}).get("profit_factor", 0)
            ),
            "expectancy_delta": (
                kelly_result.get("metrics", {}).get("expectancy", 0)
                - fixed_result.get("metrics", {}).get("expectancy", 0)
            ),
            "kelly_efficiency": kelly_result.get("metrics", {}).get("kelly_efficiency", 0),
            "kelly_advantage": kelly_result.get("metrics", {}).get("kelly_advantage", 0),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
