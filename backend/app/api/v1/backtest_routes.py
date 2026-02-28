
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
_bt_engine = BacktestEngine()


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


# ----------------------------------------------------------------------
# NEW ENDPOINTS: Added to support enhanced Backtesting.jsx V5 frontend
# These return stub data matching the frontend's useApi hook keys.
# Replace with real service calls when backend services are ready.
# ----------------------------------------------------------------------


@router.get("/results")
def get_backtest_results():
    """Full backtest results with equity curve, drawdown, trades, and all KPIs."""
    return {
        "totalPnl": 345000, "pnlPct": 24.5, "sharpe": 2.35, "sortino": 3.1,
        "calmar": 1.8, "maxDD": -12.4, "winRate": 68.2, "profitFactor": 2.7,
        "avgWin": 1250, "avgLoss": -480, "totalTrades": 1847,
        "avgDuration": "4.2h", "expectancy": 0.42, "kelly": 0.31,
        "equityCurve": [], "drawdown": [], "trades": []
    }


@router.get("/optimization")
def get_backtest_optimization():
    """Parameter optimization results with heatmap data."""
    import random
    return {
        "bestParams": {"stopLoss": 2.5, "takeProfit": 5.0, "lookback": 20, "threshold": 0.65},
        "heatmap": [
            {"x": sl, "y": tp, "z": round(random.uniform(0.5, 3.5), 2)}
            for sl in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
            for tp in [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        ],
        "sensitivity": [
            {"param": p, "impact": round(random.uniform(0.1, 1.0), 2)}
            for p in ["stopLoss", "takeProfit", "lookback", "threshold", "maFast", "maSlow", "atrMult", "rsiPeriod"]
        ]
    }


@router.get("/walk-forward")
def get_backtest_walk_forward():
    """Walk-forward analysis with in-sample/out-of-sample windows."""
    import random
    return {
        "windows": [
            {
                "id": i + 1,
                "inSampleStart": f"2023-{str(i*2+1).zfill(2)}-01",
                "inSampleEnd": f"2023-{str(i*2+2).zfill(2)}-28",
                "outSampleStart": f"2023-{str(i*2+3).zfill(2)}-01",
                "outSampleEnd": f"2023-{str(i*2+4).zfill(2)}-28",
                "inSampleSharpe": round(1.5 + random.random() * 2, 2),
                "outSampleSharpe": round(0.8 + random.random() * 1.5, 2),
                "degradation": round(random.uniform(5, 35), 1)
            }
            for i in range(5)
        ],
        "avgDegradation": 18.5,
        "robustnessScore": 72.3
    }


@router.get("/monte-carlo")
def get_backtest_monte_carlo():
    """Monte Carlo simulation with confidence intervals."""
    import random
    base = 100000
    paths = []
    for p in range(20):
        path = [base]
        for d in range(252):
            path.append(round(path[-1] * (1 + random.gauss(0.0003, 0.015)), 2))
        paths.append(path)
    return {
        "paths": paths,
        "percentiles": {
            "p5": round(base * 0.85, 2),
            "p25": round(base * 0.95, 2),
            "p50": round(base * 1.08, 2),
            "p75": round(base * 1.18, 2),
            "p95": round(base * 1.35, 2)
        },
        "ruinProbability": 2.3,
        "medianReturn": 8.2,
        "simulations": 10000
    }


@router.get("/correlation")
def get_backtest_correlation():
    """Asset correlation matrix for portfolio analysis."""
    import random
    assets = ["BTC", "ETH", "SOL", "AVAX", "MATIC", "LINK", "DOT", "ADA"]
    return {
        "assets": assets,
        "matrix": [
            [
                {"asset": a, **{b: 1.0 if a == b else round(0.2 + random.random() * 0.6, 2)}}
                for b in assets
            ]
            for a in assets
        ]
    }


@router.get("/sector-exposure")
def get_backtest_sector_exposure():
    """Sector allocation breakdown with P&L per sector."""
    return {
        "sectors": [
            {"name": "Crypto", "pct": 45, "pnl": 180000},
            {"name": "Tech", "pct": 25, "pnl": 85000},
            {"name": "Index", "pct": 20, "pnl": 55000},
            {"name": "Commodities", "pct": 10, "pnl": 25000},
        ]
    }


@router.get("/drawdown-analysis")
def get_backtest_drawdown_analysis():
    """Drawdown period analysis with depth, recovery time, and cause."""
    import random
    causes = ["Fed announcement", "Flash crash", "Correlation spike", "Vol expansion",
              "Liquidity drain", "Regime shift", "Black swan", "Earnings"]
    return {
        "periods": [
            {
                "start": f"2023-{str(i+1).zfill(2)}-15",
                "end": f"2023-{str(i+1).zfill(2)}-{20 + int(random.random() * 8)}",
                "depth": round(-(5 + random.random() * 15), 1),
                "recovery": f"{round(random.random() * 10 + 2, 1)}d",
                "cause": causes[i]
            }
            for i in range(8)
        ]
    }
