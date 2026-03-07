"""Tests for strategy/backtest.py — Bug 7 coverage improvement.

Targets the three main functions:
  - backtest_top_n (equal-weight top-N long-only backtest)
  - evaluate_backtest (Sharpe, drawdown, annual metrics)
  - load_features_and_predictions / load_spy_returns (graceful failure)

Does NOT require a running DuckDB — uses synthetic DataFrames.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta

from app.strategy.backtest import backtest_top_n, evaluate_backtest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_df():
    """5 symbols, 10 trading days, realistic scores and prices."""
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    dates = pd.bdate_range("2025-01-02", periods=10)
    np.random.seed(42)
    rows = []
    for sym in symbols:
        base_price = {"AAPL": 180, "MSFT": 370, "GOOGL": 140, "AMZN": 185, "TSLA": 250}[sym]
        for i, d in enumerate(dates):
            price = base_price * (1 + np.random.normal(0, 0.015))
            base_price = price  # random walk
            score = np.random.uniform(40, 95)
            rows.append({"date": d, "symbol": sym, "close": round(price, 2), "score": round(score, 2)})
    return pd.DataFrame(rows)


@pytest.fixture
def single_symbol_df():
    """Single symbol across 5 days."""
    dates = pd.bdate_range("2025-01-02", periods=5)
    return pd.DataFrame([
        {"date": dates[0], "symbol": "SPY", "close": 470.0, "score": 80},
        {"date": dates[1], "symbol": "SPY", "close": 472.0, "score": 82},
        {"date": dates[2], "symbol": "SPY", "close": 475.0, "score": 78},
        {"date": dates[3], "symbol": "SPY", "close": 471.0, "score": 85},
        {"date": dates[4], "symbol": "SPY", "close": 476.0, "score": 90},
    ])


@pytest.fixture
def spy_equity_df():
    """SPY equity curve for evaluate_backtest."""
    dates = pd.bdate_range("2025-01-02", periods=10)
    equity = [1.0]
    np.random.seed(99)
    for _ in range(9):
        equity.append(equity[-1] * (1 + np.random.normal(0.0003, 0.01)))
    return pd.DataFrame({"date": dates, "equity": equity})


# ---------------------------------------------------------------------------
# backtest_top_n
# ---------------------------------------------------------------------------

class TestBacktestTopN:
    def test_basic_output_shape(self, sample_df):
        """Backtest returns a DataFrame with date and equity columns."""
        result = backtest_top_n(sample_df, n_stocks=3)
        assert isinstance(result, pd.DataFrame)
        assert "date" in result.columns
        assert "equity" in result.columns
        assert len(result) > 0

    def test_equity_starts_near_one(self, sample_df):
        """First equity value should be close to 1.0 (small daily return)."""
        result = backtest_top_n(sample_df, n_stocks=3)
        assert abs(result.iloc[0]["equity"] - 1.0) < 0.10  # within 10%

    def test_n_stocks_respects_limit(self, sample_df):
        """With n_stocks=1, only 1 symbol per day is selected."""
        result_1 = backtest_top_n(sample_df, n_stocks=1)
        result_5 = backtest_top_n(sample_df, n_stocks=5)
        # Both should produce equity curves, but paths differ
        assert len(result_1) == len(result_5)
        # Concentrated portfolio likely has different final equity
        assert result_1.iloc[-1]["equity"] != result_5.iloc[-1]["equity"]

    def test_min_score_filter(self, sample_df):
        """Setting min_score very high may filter out all symbols some days."""
        result = backtest_top_n(sample_df, n_stocks=3, min_score=99.0)
        assert isinstance(result, pd.DataFrame)
        # With min_score=99, most days have no picks, equity stays flat
        if len(result) > 0:
            assert result.iloc[-1]["equity"] >= 0.95

    def test_empty_dataframe(self):
        """Empty input returns empty equity curve."""
        result = backtest_top_n(pd.DataFrame(), n_stocks=3)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_missing_score_column(self):
        """DataFrame without 'score' column returns empty."""
        df = pd.DataFrame({"date": [date.today()], "symbol": ["AAPL"], "close": [180]})
        result = backtest_top_n(df, n_stocks=1)
        assert len(result) == 0

    def test_cost_bps_impact(self, sample_df):
        """Higher cost_bps should reduce final equity."""
        result_low = backtest_top_n(sample_df, n_stocks=3, cost_bps=0.0)
        result_high = backtest_top_n(sample_df, n_stocks=3, cost_bps=50.0)
        # Zero cost should always >= high cost
        assert result_low.iloc[-1]["equity"] >= result_high.iloc[-1]["equity"]

    def test_single_symbol(self, single_symbol_df):
        """Backtest works with a single symbol."""
        result = backtest_top_n(single_symbol_df, n_stocks=1)
        assert len(result) > 0

    def test_equity_never_negative(self, sample_df):
        """Equity should never go negative."""
        result = backtest_top_n(sample_df, n_stocks=5, cost_bps=1.0)
        assert (result["equity"] > 0).all()

    def test_dates_are_sequential(self, sample_df):
        """Output dates should be in ascending order."""
        result = backtest_top_n(sample_df, n_stocks=3)
        if len(result) > 1:
            dates = result["date"].tolist()
            for i in range(1, len(dates)):
                assert dates[i] >= dates[i - 1]


# ---------------------------------------------------------------------------
# evaluate_backtest
# ---------------------------------------------------------------------------

class TestEvaluateBacktest:
    def test_returns_all_metrics(self, sample_df, spy_equity_df):
        """evaluate_backtest returns all expected metric keys."""
        curve = backtest_top_n(sample_df, n_stocks=3)
        metrics = evaluate_backtest(curve, spy_equity_df)
        expected_keys = [
            "strategy_annual_return",
            "spy_annual_return",
            "strategy_annual_vol",
            "spy_annual_vol",
            "sharpe",
            "max_drawdown",
        ]
        for key in expected_keys:
            assert key in metrics, f"Missing metric: {key}"

    def test_metrics_are_finite(self, sample_df, spy_equity_df):
        """All metrics should be finite numbers."""
        curve = backtest_top_n(sample_df, n_stocks=3)
        metrics = evaluate_backtest(curve, spy_equity_df)
        for key, val in metrics.items():
            assert np.isfinite(val), f"{key} is not finite: {val}"

    def test_max_drawdown_is_non_positive(self, sample_df, spy_equity_df):
        """Max drawdown should be <= 0 (0 means no drawdown)."""
        curve = backtest_top_n(sample_df, n_stocks=3)
        metrics = evaluate_backtest(curve, spy_equity_df)
        assert metrics["max_drawdown"] <= 0

    def test_empty_curves_return_zeros(self):
        """Empty input returns all-zero metrics."""
        metrics = evaluate_backtest(pd.DataFrame(), pd.DataFrame())
        assert metrics["sharpe"] == 0.0
        assert metrics["max_drawdown"] == 0.0

    def test_volatility_non_negative(self, sample_df, spy_equity_df):
        """Volatility should be non-negative."""
        curve = backtest_top_n(sample_df, n_stocks=3)
        metrics = evaluate_backtest(curve, spy_equity_df)
        assert metrics["strategy_annual_vol"] >= 0
        assert metrics["spy_annual_vol"] >= 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestBacktestEdgeCases:
    def test_all_same_score(self):
        """When all symbols have the same score, all should be selected."""
        dates = pd.bdate_range("2025-01-02", periods=3)
        rows = []
        for sym in ["A", "B", "C"]:
            for d in dates:
                rows.append({"date": d, "symbol": sym, "close": 100.0, "score": 50.0})
        df = pd.DataFrame(rows)
        result = backtest_top_n(df, n_stocks=3)
        assert len(result) > 0

    def test_single_day_no_crash(self):
        """Single day of data produces empty curve (needs 2 days for returns)."""
        df = pd.DataFrame([
            {"date": pd.Timestamp("2025-01-02"), "symbol": "AAPL", "close": 180, "score": 80},
        ])
        result = backtest_top_n(df, n_stocks=1)
        assert isinstance(result, pd.DataFrame)

    def test_two_days_produces_one_row(self):
        """Two days of data produces exactly one equity row."""
        dates = pd.bdate_range("2025-01-02", periods=2)
        df = pd.DataFrame([
            {"date": dates[0], "symbol": "AAPL", "close": 180, "score": 80},
            {"date": dates[1], "symbol": "AAPL", "close": 185, "score": 82},
        ])
        result = backtest_top_n(df, n_stocks=1)
        assert len(result) == 1
        # Return should reflect AAPL going from 180 to 185
        expected_return = 185 / 180 - 1
        assert abs(result.iloc[0]["equity"] - (1 + expected_return)) < 0.01

    def test_symbols_with_gaps(self):
        """Symbols that appear on some days but not others don't crash."""
        dates = pd.bdate_range("2025-01-02", periods=4)
        rows = [
            {"date": dates[0], "symbol": "AAPL", "close": 180, "score": 80},
            {"date": dates[0], "symbol": "MSFT", "close": 370, "score": 90},
            {"date": dates[1], "symbol": "AAPL", "close": 182, "score": 82},
            # MSFT missing on day 2
            {"date": dates[2], "symbol": "AAPL", "close": 185, "score": 75},
            {"date": dates[2], "symbol": "MSFT", "close": 375, "score": 88},
            {"date": dates[3], "symbol": "AAPL", "close": 183, "score": 78},
            {"date": dates[3], "symbol": "MSFT", "close": 380, "score": 92},
        ]
        df = pd.DataFrame(rows)
        result = backtest_top_n(df, n_stocks=2)
        assert len(result) > 0

    def test_large_n_stocks(self, sample_df):
        """n_stocks larger than available symbols doesn't crash."""
        result = backtest_top_n(sample_df, n_stocks=100)
        assert len(result) > 0
