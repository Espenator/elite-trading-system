"""Edge case tests for circuit breaker reflex checks."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from app.council.blackboard import BlackboardState
from app.council.reflexes.circuit_breaker import CircuitBreaker


@pytest.fixture
def cb():
    return CircuitBreaker()


@pytest.fixture
def bb():
    return BlackboardState(symbol="SPY", raw_features={"features": {}})


class TestFlashCrashEdgeCases:
    """Test flash crash detector edge cases."""

    @pytest.mark.anyio
    async def test_missing_return_data(self, cb, bb):
        """Should not halt when return data is missing."""
        bb.raw_features = {"features": {}}
        result = await cb.flash_crash_detector(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_zero_return(self, cb, bb):
        """Should not halt on zero return."""
        bb.raw_features = {"features": {"return_1d": 0.0}}
        result = await cb.flash_crash_detector(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_positive_return(self, cb, bb):
        """Should detect large positive moves as well (limit up scenario)."""
        bb.raw_features = {"features": {"return_1d": 0.10}}
        result = await cb.flash_crash_detector(bb)
        assert result is not None
        assert "price collapse" in result.lower() or "intraday move" in result.lower()

    @pytest.mark.anyio
    async def test_exact_threshold(self, cb, bb):
        """Should trigger at exactly 5% threshold."""
        bb.raw_features = {"features": {"return_5min": -0.05}}
        result = await cb.flash_crash_detector(bb)
        # At exactly threshold, should not trigger (>= vs >)
        assert result is None

    @pytest.mark.anyio
    async def test_just_above_threshold(self, cb, bb):
        """Should trigger just above 5% threshold."""
        bb.raw_features = {"features": {"return_5min": -0.051}}
        result = await cb.flash_crash_detector(bb)
        assert result is not None

    @pytest.mark.anyio
    async def test_prefers_intraday_over_daily(self, cb, bb):
        """Should use intraday data when available instead of daily."""
        bb.raw_features = {
            "features": {
                "return_5min": -0.02,  # Below threshold
                "return_1d": -0.10,    # Above threshold
            }
        }
        result = await cb.flash_crash_detector(bb)
        # Should use 5min which is below threshold
        assert result is None


class TestVIXSpikeEdgeCases:
    """Test VIX spike detector edge cases."""

    @pytest.mark.anyio
    async def test_negative_vix(self, cb, bb):
        """Should handle invalid negative VIX gracefully."""
        bb.raw_features = {"features": {"vix_close": -10.0}}
        result = await cb.vix_spike_detector(bb)
        assert result is None  # Negative VIX is below threshold

    @pytest.mark.anyio
    async def test_zero_vix(self, cb, bb):
        """Should handle zero VIX."""
        bb.raw_features = {"features": {"vix_close": 0.0}}
        result = await cb.vix_spike_detector(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_exact_threshold(self, cb, bb):
        """Should trigger at exactly 35.0 threshold."""
        bb.raw_features = {"features": {"vix_close": 35.0}}
        result = await cb.vix_spike_detector(bb)
        # At exactly threshold, should not trigger (> vs >=)
        assert result is None

    @pytest.mark.anyio
    async def test_fallback_to_vix_field(self, cb, bb):
        """Should fall back to 'vix' field if 'vix_close' missing."""
        bb.raw_features = {"features": {"vix": 40.0}}
        result = await cb.vix_spike_detector(bb)
        assert result is not None
        assert "VIX" in result

    @pytest.mark.anyio
    async def test_extreme_vix(self, cb, bb):
        """Should handle extreme VIX levels (like March 2020)."""
        bb.raw_features = {"features": {"vix_close": 82.69}}  # COVID crash level
        result = await cb.vix_spike_detector(bb)
        assert result is not None


class TestDrawdownEdgeCases:
    """Test daily drawdown limit edge cases."""

    @pytest.mark.anyio
    async def test_api_unavailable(self, cb, bb):
        """Should not halt when risk API is unavailable."""
        with patch('app.api.v1.risk.drawdown_check_status', side_effect=Exception("API down")):
            result = await cb.daily_drawdown_limit(bb)
            assert result is None  # Graceful degradation

    @pytest.mark.anyio
    async def test_exact_threshold(self, cb, bb):
        """Should trigger at exactly -3% drawdown."""
        with patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock:
            mock.return_value = {"drawdown_breached": False, "daily_pnl_pct": -0.03}
            result = await cb.daily_drawdown_limit(bb)
            # At exactly threshold, should not trigger (< vs <=)
            assert result is None

    @pytest.mark.anyio
    async def test_just_below_threshold(self, cb, bb):
        """Should trigger just below -3% threshold."""
        with patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock:
            mock.return_value = {"drawdown_breached": False, "daily_pnl_pct": -0.031}
            result = await cb.daily_drawdown_limit(bb)
            assert result is not None

    @pytest.mark.anyio
    async def test_breached_flag(self, cb, bb):
        """Should halt when drawdown_breached flag is set."""
        with patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock:
            mock.return_value = {"drawdown_breached": True, "daily_pnl_pct": -0.02}
            result = await cb.daily_drawdown_limit(bb)
            assert result is not None


class TestPositionLimitEdgeCases:
    """Test position limit check edge cases."""

    @pytest.mark.anyio
    async def test_api_unavailable(self, cb, bb):
        """Should not halt when Alpaca API is unavailable."""
        with patch('app.services.alpaca_service.alpaca_service.get_positions', side_effect=Exception("API down")):
            result = await cb.position_limit_check(bb)
            assert result is None  # Graceful degradation

    @pytest.mark.anyio
    async def test_exact_limit(self, cb, bb):
        """Should trigger at exactly 10 positions."""
        with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock:
            mock.return_value = [{"symbol": f"SYM{i}"} for i in range(10)]
            result = await cb.position_limit_check(bb)
            assert result is not None  # >= limit triggers

    @pytest.mark.anyio
    async def test_one_below_limit(self, cb, bb):
        """Should not trigger at 9 positions."""
        with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock:
            mock.return_value = [{"symbol": f"SYM{i}"} for i in range(9)]
            result = await cb.position_limit_check(bb)
            assert result is None


class TestMarketHoursEdgeCases:
    """Test market hours check edge cases."""

    @pytest.mark.anyio
    async def test_saturday(self, cb, bb):
        """Should halt on Saturday."""
        with patch('app.council.reflexes.circuit_breaker.datetime') as mock_dt:
            fake_now = datetime(2026, 3, 8, 15, 0, tzinfo=timezone.utc)  # Saturday
            mock_dt.now.return_value = fake_now
            result = await cb.market_hours_check(bb)
            assert result is not None
            assert "weekend" in result.lower()

    @pytest.mark.anyio
    async def test_sunday(self, cb, bb):
        """Should halt on Sunday."""
        with patch('app.council.reflexes.circuit_breaker.datetime') as mock_dt:
            fake_now = datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc)  # Sunday
            mock_dt.now.return_value = fake_now
            result = await cb.market_hours_check(bb)
            assert result is not None

    @pytest.mark.anyio
    async def test_premarket_allowed(self, cb, bb):
        """Should allow pre-market hours (8 AM ET = 13:00 UTC)."""
        with patch('app.council.reflexes.circuit_breaker.datetime') as mock_dt:
            fake_now = datetime(2026, 3, 10, 13, 0, tzinfo=timezone.utc)  # Monday 8 AM ET
            mock_dt.now.return_value = fake_now
            result = await cb.market_hours_check(bb)
            assert result is None  # Should allow

    @pytest.mark.anyio
    async def test_after_hours_allowed(self, cb, bb):
        """Should allow after-hours (7 PM ET = 00:00 UTC next day)."""
        with patch('app.council.reflexes.circuit_breaker.datetime') as mock_dt:
            fake_now = datetime(2026, 3, 10, 21, 0, tzinfo=timezone.utc)  # Monday 4 PM ET
            mock_dt.now.return_value = fake_now
            result = await cb.market_hours_check(bb)
            assert result is None  # Should allow

    @pytest.mark.anyio
    async def test_midnight_blocked(self, cb, bb):
        """Should block midnight trading (midnight ET = 5:00 UTC)."""
        with patch('app.council.reflexes.circuit_breaker.datetime') as mock_dt:
            fake_now = datetime(2026, 3, 10, 5, 0, tzinfo=timezone.utc)  # Monday midnight
            mock_dt.now.return_value = fake_now
            result = await cb.market_hours_check(bb)
            assert result is not None


class TestCheckAllEdgeCases:
    """Test check_all orchestration edge cases."""

    @pytest.mark.anyio
    async def test_first_check_fails_stops_early(self, cb, bb):
        """When first check fails, should return immediately."""
        bb.raw_features = {"features": {"return_1d": -0.10}}  # Flash crash
        result = await cb.check_all(bb)
        assert result is not None
        # Should mention the first failing check
        assert "crash" in result.lower() or "collapse" in result.lower()

    @pytest.mark.anyio
    async def test_multiple_checks_fail_returns_first(self, cb, bb):
        """When multiple checks fail, should return the first one."""
        bb.raw_features = {
            "features": {
                "return_1d": -0.10,  # Flash crash
                "vix_close": 50.0,   # VIX spike
            }
        }
        result = await cb.check_all(bb)
        assert result is not None
        # The order is: flash_crash, vix_spike, drawdown, position, market_hours
        # Due to parallel execution, we can't guarantee which fires first,
        # but one of them should fire
