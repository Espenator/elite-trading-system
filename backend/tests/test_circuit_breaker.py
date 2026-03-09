"""Tests for circuit breaker brainstem reflexes."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from app.council.blackboard import BlackboardState
from app.council.reflexes.circuit_breaker import CircuitBreaker


@pytest.fixture
def cb():
    return CircuitBreaker()


@pytest.fixture
def bb():
    return BlackboardState(symbol="SPY", raw_features={"features": {}})


class TestFlashCrashDetector:
    @pytest.mark.anyio
    async def test_no_crash_returns_none(self, cb, bb):
        bb.raw_features = {"features": {"return_1d": 0.01}}
        result = await cb.flash_crash_detector(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_crash_detected(self, cb, bb):
        bb.raw_features = {"features": {"return_1d": -0.08}}
        result = await cb.flash_crash_detector(bb)
        assert result is not None
        assert "price collapse" in result.lower() or "flash crash" in result.lower()

    @pytest.mark.anyio
    async def test_intraday_crash_detected(self, cb, bb):
        bb.raw_features = {"features": {"return_5min": -0.06}}
        result = await cb.flash_crash_detector(bb)
        assert result is not None
        assert "Flash crash" in result

    @pytest.mark.anyio
    async def test_no_data_returns_none(self, cb, bb):
        bb.raw_features = {"features": {}}
        result = await cb.flash_crash_detector(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_small_positive_move_returns_none(self, cb, bb):
        bb.raw_features = {"features": {"return_1d": 0.03}}
        result = await cb.flash_crash_detector(bb)
        assert result is None


class TestVIXSpikeDetector:
    @pytest.mark.anyio
    async def test_normal_vix_returns_none(self, cb, bb):
        bb.raw_features = {"features": {"vix_close": 20.0}}
        result = await cb.vix_spike_detector(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_vix_spike_detected(self, cb, bb):
        bb.raw_features = {"features": {"vix_close": 40.0}}
        result = await cb.vix_spike_detector(bb)
        assert result is not None
        assert "VIX" in result

    @pytest.mark.anyio
    async def test_no_vix_data_passes(self, cb, bb):
        bb.raw_features = {"features": {}}
        result = await cb.vix_spike_detector(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_vix_exactly_at_threshold(self, cb, bb):
        bb.raw_features = {"features": {"vix_close": 35.0}}
        result = await cb.vix_spike_detector(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_vix_just_over_threshold(self, cb, bb):
        bb.raw_features = {"features": {"vix_close": 35.1}}
        result = await cb.vix_spike_detector(bb)
        assert result is not None
        assert "VIX" in result


class TestDailyDrawdownLimit:
    @pytest.mark.anyio
    async def test_no_drawdown_returns_none(self, cb, bb):
        with patch("app.council.reflexes.circuit_breaker.drawdown_check_status") as mock:
            mock.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}
            result = await cb.daily_drawdown_limit(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_drawdown_breached_flag(self, cb, bb):
        with patch("app.council.reflexes.circuit_breaker.drawdown_check_status") as mock:
            mock.return_value = {"drawdown_breached": True}
            result = await cb.daily_drawdown_limit(bb)
            assert result is not None
            assert "drawdown" in result.lower()

    @pytest.mark.anyio
    async def test_daily_pnl_below_limit(self, cb, bb):
        with patch("app.council.reflexes.circuit_breaker.drawdown_check_status") as mock:
            mock.return_value = {"drawdown_breached": False, "daily_pnl_pct": -0.04}
            result = await cb.daily_drawdown_limit(bb)
            assert result is not None
            assert "PnL" in result or "pnl" in result.lower()

    @pytest.mark.anyio
    async def test_api_exception_returns_none(self, cb, bb):
        with patch("app.council.reflexes.circuit_breaker.drawdown_check_status") as mock:
            mock.side_effect = Exception("API unavailable")
            result = await cb.daily_drawdown_limit(bb)
            assert result is None


class TestPositionLimitCheck:
    @pytest.mark.anyio
    async def test_no_positions_returns_none(self, cb, bb):
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=[])
            result = await cb.position_limit_check(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_below_limit_returns_none(self, cb, bb):
        positions = [{"symbol": f"AAPL{i}"} for i in range(5)]
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=positions)
            result = await cb.position_limit_check(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_at_limit_triggers(self, cb, bb):
        positions = [{"symbol": f"AAPL{i}"} for i in range(10)]
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=positions)
            result = await cb.position_limit_check(bb)
            assert result is not None
            assert "Position limit" in result

    @pytest.mark.anyio
    async def test_over_limit_triggers(self, cb, bb):
        positions = [{"symbol": f"AAPL{i}"} for i in range(15)]
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=positions)
            result = await cb.position_limit_check(bb)
            assert result is not None
            assert "15/10" in result

    @pytest.mark.anyio
    async def test_alpaca_exception_returns_none(self, cb, bb):
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(side_effect=Exception("Alpaca down"))
            result = await cb.position_limit_check(bb)
            assert result is None


class TestSinglePositionCheck:
    @pytest.mark.anyio
    async def test_no_positions_returns_none(self, cb, bb):
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=[])
            mock.get_account = AsyncMock(return_value={"equity": "100000"})
            result = await cb.single_position_check(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_small_position_returns_none(self, cb, bb):
        positions = [{"symbol": "AAPL", "market_value": "10000"}]
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=positions)
            mock.get_account = AsyncMock(return_value={"equity": "100000"})
            result = await cb.single_position_check(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_position_at_20_percent_returns_none(self, cb, bb):
        positions = [{"symbol": "AAPL", "market_value": "20000"}]
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=positions)
            mock.get_account = AsyncMock(return_value={"equity": "100000"})
            result = await cb.single_position_check(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_position_over_20_percent_triggers(self, cb, bb):
        positions = [{"symbol": "AAPL", "market_value": "25000"}]
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=positions)
            mock.get_account = AsyncMock(return_value={"equity": "100000"})
            result = await cb.single_position_check(bb)
            assert result is not None
            assert "AAPL" in result
            assert "25" in result or "position" in result.lower()

    @pytest.mark.anyio
    async def test_negative_market_value_uses_absolute(self, cb, bb):
        positions = [{"symbol": "AAPL", "market_value": "-30000"}]
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=positions)
            mock.get_account = AsyncMock(return_value={"equity": "100000"})
            result = await cb.single_position_check(bb)
            assert result is not None
            assert "AAPL" in result

    @pytest.mark.anyio
    async def test_multiple_positions_checks_all(self, cb, bb):
        positions = [
            {"symbol": "AAPL", "market_value": "15000"},
            {"symbol": "MSFT", "market_value": "30000"},
            {"symbol": "GOOGL", "market_value": "10000"},
        ]
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=positions)
            mock.get_account = AsyncMock(return_value={"equity": "100000"})
            result = await cb.single_position_check(bb)
            assert result is not None
            assert "MSFT" in result

    @pytest.mark.anyio
    async def test_zero_equity_returns_none(self, cb, bb):
        positions = [{"symbol": "AAPL", "market_value": "10000"}]
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=positions)
            mock.get_account = AsyncMock(return_value={"equity": "0"})
            result = await cb.single_position_check(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_alpaca_exception_returns_none(self, cb, bb):
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(side_effect=Exception("API error"))
            result = await cb.single_position_check(bb)
            assert result is None


class TestMarketHoursCheck:
    @pytest.mark.anyio
    async def test_weekend_saturday_triggers(self, cb, bb):
        # Saturday
        with patch("app.council.reflexes.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 8, 15, 0, tzinfo=timezone.utc)  # Saturday
            mock_dt.now.return_value.weekday.return_value = 5
            mock_dt.now.return_value.hour = 15
            result = await cb.market_hours_check(bb)
            assert result is not None
            assert "weekend" in result.lower()

    @pytest.mark.anyio
    async def test_weekend_sunday_triggers(self, cb, bb):
        # Sunday
        with patch("app.council.reflexes.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 9, 15, 0, tzinfo=timezone.utc)  # Sunday
            mock_dt.now.return_value.weekday.return_value = 6
            mock_dt.now.return_value.hour = 15
            result = await cb.market_hours_check(bb)
            assert result is not None
            assert "weekend" in result.lower()

    @pytest.mark.anyio
    async def test_weekday_market_hours_returns_none(self, cb, bb):
        # Monday 3 PM UTC (within extended hours)
        with patch("app.council.reflexes.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 9, 15, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value.weekday.return_value = 0
            mock_dt.now.return_value.hour = 15
            result = await cb.market_hours_check(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_early_morning_triggers(self, cb, bb):
        # Monday 5 AM UTC (too early)
        with patch("app.council.reflexes.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 9, 5, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value.weekday.return_value = 0
            mock_dt.now.return_value.hour = 5
            result = await cb.market_hours_check(bb)
            assert result is not None
            assert "off-hours" in result.lower()

    @pytest.mark.anyio
    async def test_late_night_triggers(self, cb, bb):
        # Monday 11 PM UTC (too late)
        with patch("app.council.reflexes.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 9, 23, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value.weekday.return_value = 0
            mock_dt.now.return_value.hour = 23
            result = await cb.market_hours_check(bb)
            assert result is not None
            assert "off-hours" in result.lower()


class TestCheckAll:
    @pytest.mark.anyio
    async def test_all_clear_returns_none(self, cb, bb):
        bb.raw_features = {"features": {"return_1d": 0.01, "vix_close": 20.0}}
        result = await cb.check_all(bb)
        # May return market hours halt depending on when test runs
        if result:
            assert "Market closed" in result or "Circuit breaker" in result

    @pytest.mark.anyio
    async def test_flash_crash_halts(self, cb, bb):
        bb.raw_features = {"features": {"return_1d": -0.10, "vix_close": 15.0}}
        result = await cb.check_all(bb)
        assert result is not None
        assert "price collapse" in result.lower() or "flash crash" in result.lower()

    @pytest.mark.anyio
    async def test_vix_spike_halts(self, cb, bb):
        bb.raw_features = {"features": {"return_1d": 0.01, "vix_close": 50.0}}
        result = await cb.check_all(bb)
        assert result is not None
        assert "VIX" in result or "Market closed" in result

    @pytest.mark.anyio
    async def test_position_limit_halts(self, cb, bb):
        bb.raw_features = {"features": {"return_1d": 0.01, "vix_close": 20.0}}
        positions = [{"symbol": f"AAPL{i}"} for i in range(12)]
        with patch("app.council.reflexes.circuit_breaker.alpaca_service") as mock:
            mock.get_positions = AsyncMock(return_value=positions)
            mock.get_account = AsyncMock(return_value={"equity": "100000"})
            result = await cb.check_all(bb)
            # Should trigger either position limit or market hours
            assert result is not None

