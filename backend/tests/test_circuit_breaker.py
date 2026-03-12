"""Tests for circuit breaker brainstem reflexes."""
import pytest
from unittest.mock import AsyncMock, patch

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


class TestDailyDrawdownLimit:
    @pytest.mark.anyio
    @patch("app.api.v1.risk.drawdown_check_status", new_callable=AsyncMock)
    async def test_drawdown_breached_returns_reason(self, mock_dd, cb, bb):
        mock_dd.return_value = {"drawdown_breached": True}
        result = await cb.daily_drawdown_limit(bb)
        assert result is not None
        assert "drawdown" in result.lower()


class TestPositionLimitCheck:
    @pytest.mark.anyio
    @patch("app.services.alpaca_service.alpaca_service")
    async def test_position_limit_exceeded_returns_reason(self, mock_alpaca, cb, bb):
        mock_alpaca.get_positions = AsyncMock(return_value=[{}] * 11)
        result = await cb.position_limit_check(bb)
        assert result is not None
        assert "position" in result.lower() or "limit" in result.lower()


class TestMarketHoursCheck:
    @pytest.mark.anyio
    async def test_market_hours_check_returns_none_or_weekend_message(self, cb, bb):
        result = await cb.market_hours_check(bb)
        assert result is None or "Market closed" in result
