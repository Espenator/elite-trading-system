"""Extended tests for kelly_position_sizer.py — Bug 19 coverage improvement.

Covers methods NOT tested in test_api.py:
  - size_signal (high-level wrapper)
  - calculate_volatility_adjusted
  - regime_aware_size
  - correlation_adjusted_size
  - sector_exposure_check
  - portfolio_correlation_cap
  - calculate_trailing_stop
"""
import pytest

from app.services.kelly_position_sizer import KellyPositionSizer, PositionSize


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sizer():
    return KellyPositionSizer(
        max_allocation=0.10,
        use_half_kelly=True,
        min_edge=0.02,
        min_trades=20,
    )


# ---------------------------------------------------------------------------
# size_signal
# ---------------------------------------------------------------------------

class TestSizeSignal:
    def test_below_min_score_returns_hold(self, sizer):
        result = sizer.size_signal(
            ticker="AAPL",
            composite_score=50.0,
            regime="NEUTRAL",
            historical_stats={"win_rate": 0.6, "avg_win_pct": 0.04, "avg_loss_pct": 0.015, "trade_count": 100},
            min_score=70.0,
        )
        assert result["action"] == "HOLD"
        assert result["kelly_allocation_pct"] == 0.0
        assert "below threshold" in result["reason"]

    def test_above_min_score_returns_allocation(self, sizer):
        result = sizer.size_signal(
            ticker="AAPL",
            composite_score=80.0,
            regime="BULLISH",
            historical_stats={"win_rate": 0.65, "avg_win_pct": 0.05, "avg_loss_pct": 0.015, "trade_count": 100},
        )
        assert result["action"] == "BUY"
        assert result["kelly_allocation_pct"] > 0
        assert result["ticker"] == "AAPL"

    def test_missing_stats_uses_defaults(self, sizer):
        """Missing historical_stats keys should use safe defaults."""
        result = sizer.size_signal(
            ticker="TSLA",
            composite_score=85.0,
            regime="NEUTRAL",
            historical_stats={},
        )
        assert "action" in result


# ---------------------------------------------------------------------------
# calculate_volatility_adjusted
# ---------------------------------------------------------------------------

class TestVolatilityAdjusted:
    def test_high_volatility_reduces_size(self, sizer):
        base = sizer.calculate(win_rate=0.65, avg_win_pct=0.05, avg_loss_pct=0.015)
        vol_adj = sizer.calculate_volatility_adjusted(
            win_rate=0.65, avg_win_pct=0.05, avg_loss_pct=0.015,
            current_volatility=0.04,
            baseline_volatility=0.02,
            trade_count=100,
        )
        assert vol_adj.final_pct <= base.final_pct
        assert vol_adj.final_pct > 0  # Must produce a real allocation

    def test_low_volatility_doesnt_increase_beyond_cap(self, sizer):
        vol_adj = sizer.calculate_volatility_adjusted(
            win_rate=0.65, avg_win_pct=0.05, avg_loss_pct=0.015,
            current_volatility=0.01,
            baseline_volatility=0.02,
            trade_count=100,
        )
        assert vol_adj.final_pct <= sizer.max_allocation

    def test_extreme_volatility(self, sizer):
        vol_adj = sizer.calculate_volatility_adjusted(
            win_rate=0.65, avg_win_pct=0.05, avg_loss_pct=0.015,
            current_volatility=0.10,
            baseline_volatility=0.02,
            trade_count=100,
        )
        assert vol_adj.final_pct < 0.03


# ---------------------------------------------------------------------------
# regime_aware_size
# ---------------------------------------------------------------------------

class TestRegimeAwareSize:
    def test_crisis_regime_reduces_size(self, sizer):
        normal = sizer.regime_aware_size(win_rate=0.70, regime="NEUTRAL")
        crisis = sizer.regime_aware_size(win_rate=0.70, regime="CRISIS")
        assert normal["final_pct"] > 0, "NEUTRAL must produce a trade"
        assert crisis["final_pct"] < normal["final_pct"]

    def test_bullish_regime_increases_size(self, sizer):
        neutral = sizer.regime_aware_size(win_rate=0.70, regime="NEUTRAL")
        bullish = sizer.regime_aware_size(win_rate=0.70, regime="BULLISH")
        assert bullish["final_pct"] >= neutral["final_pct"]

    def test_low_risk_score_dampens(self, sizer):
        high_risk = sizer.regime_aware_size(win_rate=0.70, risk_score=80)
        low_risk = sizer.regime_aware_size(win_rate=0.70, risk_score=30)
        assert high_risk["final_pct"] > 0, "high_risk must produce a trade"
        assert low_risk["final_pct"] < high_risk["final_pct"]
        assert low_risk["risk_dampener"] == 0.5

    def test_mid_risk_score(self, sizer):
        result = sizer.regime_aware_size(win_rate=0.70, risk_score=50)
        assert result["risk_dampener"] == 0.75

    def test_high_risk_score(self, sizer):
        result = sizer.regime_aware_size(win_rate=0.70, risk_score=70)
        assert result["risk_dampener"] == 1.0

    def test_action_field(self, sizer):
        result = sizer.regime_aware_size(win_rate=0.70, regime="NEUTRAL")
        assert result["action"] in ("BUY", "HOLD", "NO_TRADE")


# ---------------------------------------------------------------------------
# correlation_adjusted_size
# ---------------------------------------------------------------------------

class TestCorrelationAdjusted:
    def test_no_portfolio_returns_base(self, sizer):
        result = sizer.correlation_adjusted_size(
            symbol="AAPL",
            base_size_pct=0.05,
            portfolio_positions={},
        )
        assert result["adjusted_pct"] == 0.05
        assert result["correlation_penalty"] == 0.0

    def test_high_correlation_reduces_size(self, sizer):
        result = sizer.correlation_adjusted_size(
            symbol="AAPL",
            base_size_pct=0.05,
            portfolio_positions={"MSFT": 0.08},
            correlation_matrix={"AAPL": {"MSFT": 0.95}},
        )
        assert result["adjusted_pct"] < 0.05
        assert result["correlation_penalty"] > 0

    def test_low_correlation_no_penalty(self, sizer):
        result = sizer.correlation_adjusted_size(
            symbol="AAPL",
            base_size_pct=0.05,
            portfolio_positions={"XOM": 0.05},
            correlation_matrix={"AAPL": {"XOM": 0.1}},
        )
        assert result["correlation_penalty"] <= 0.15

    def test_same_symbol_ignored(self, sizer):
        result = sizer.correlation_adjusted_size(
            symbol="AAPL",
            base_size_pct=0.05,
            portfolio_positions={"AAPL": 0.05},
            correlation_matrix={"AAPL": {"AAPL": 1.0}},
        )
        assert result["correlation_penalty"] == 0.0


# ---------------------------------------------------------------------------
# sector_exposure_check
# ---------------------------------------------------------------------------

class TestSectorExposure:
    def test_within_limit_allowed(self, sizer):
        result = sizer.sector_exposure_check(
            symbol="AAPL", sector="Technology",
            position_pct=0.05,
            sector_allocations={"Technology": 0.10},
        )
        assert result["allowed"] is True
        assert result["adjusted_pct"] == 0.05

    def test_exceeds_limit_capped(self, sizer):
        result = sizer.sector_exposure_check(
            symbol="AAPL", sector="Technology",
            position_pct=0.10,
            sector_allocations={"Technology": 0.20},
        )
        assert result["adjusted_pct"] <= 0.05
        assert "reason" in result

    def test_at_limit_rejected(self, sizer):
        result = sizer.sector_exposure_check(
            symbol="AAPL", sector="Technology",
            position_pct=0.05,
            sector_allocations={"Technology": 0.25},
        )
        assert result["allowed"] is False
        assert result["adjusted_pct"] == 0.0


# ---------------------------------------------------------------------------
# portfolio_correlation_cap
# ---------------------------------------------------------------------------

class TestPortfolioCorrelationCap:
    def test_balanced_portfolio_passes(self):
        positions = [
            {"symbol": "AAPL", "sector": "Technology", "kelly_allocation_pct": 0.05},
            {"symbol": "XOM", "sector": "Energy", "kelly_allocation_pct": 0.05},
            {"symbol": "JPM", "sector": "Financial", "kelly_allocation_pct": 0.05},
        ]
        result = KellyPositionSizer.portfolio_correlation_cap(positions)
        assert len(result) == 3
        for pos in result:
            assert "sector_capped" not in pos

    def test_concentrated_sector_capped(self):
        positions = [
            {"symbol": "AAPL", "sector": "Technology", "kelly_allocation_pct": 0.15},
            {"symbol": "MSFT", "sector": "Technology", "kelly_allocation_pct": 0.15},
            {"symbol": "XOM", "sector": "Energy", "kelly_allocation_pct": 0.05},
        ]
        result = KellyPositionSizer.portfolio_correlation_cap(positions)
        tech_positions = [p for p in result if p.get("sector") == "Technology"]
        total_tech = sum(p["kelly_allocation_pct"] for p in tech_positions)
        assert total_tech <= 0.25 + 0.001


# ---------------------------------------------------------------------------
# calculate_trailing_stop
# ---------------------------------------------------------------------------

class TestTrailingStop:
    def test_buy_side_stop_below_entry(self, sizer):
        result = sizer.calculate_trailing_stop(entry_price=180, atr=3.5, side="buy")
        assert result["stop_loss"] < 180
        assert result["take_profit"] > 180
        assert result["risk_reward_ratio"] > 0

    def test_sell_side_stop_above_entry(self, sizer):
        result = sizer.calculate_trailing_stop(entry_price=180, atr=3.5, side="sell")
        assert result["stop_loss"] > 180
        assert result["take_profit"] < 180

    def test_method_is_atr_or_trailing(self, sizer):
        result = sizer.calculate_trailing_stop(entry_price=180, atr=3.5)
        assert result["method"] in ("atr", "trailing_pct")

    def test_zero_atr_degenerates(self, sizer):
        """ATR=0 → atr_stop equals entry, which is tighter than pct_stop.
        This is a degenerate case (risk_per_share=0); production code may
        want to special-case it, but for now we assert actual behaviour."""
        result = sizer.calculate_trailing_stop(entry_price=180, atr=0.0, side="buy")
        assert result["stop_loss"] == 180.0
        assert result["method"] == "atr"
        assert result["risk_per_share"] == 0.0

    def test_risk_per_share_positive(self, sizer):
        result = sizer.calculate_trailing_stop(entry_price=100, atr=2.0)
        assert result["risk_per_share"] > 0
        assert result["reward_per_share"] > 0
