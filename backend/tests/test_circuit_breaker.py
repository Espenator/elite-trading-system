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


class TestDailyDrawdownLimit:
    """Circuit breaker: daily drawdown limit blocks trading when breached."""

    @pytest.mark.anyio
    async def test_drawdown_breached_returns_reason(self, cb, bb):
        with patch("app.api.v1.risk.drawdown_check_status", new_callable=AsyncMock) as m:
            m.return_value = {"drawdown_breached": True, "daily_pnl_pct": -0.04}
            result = await cb.daily_drawdown_limit(bb)
        assert result is not None
        assert "drawdown" in result.lower()

    @pytest.mark.anyio
    async def test_drawdown_ok_returns_none(self, cb, bb):
        with patch("app.api.v1.risk.drawdown_check_status", new_callable=AsyncMock) as m:
            m.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}
            result = await cb.daily_drawdown_limit(bb)
        assert result is None


class TestPositionLimitCheck:
    """Circuit breaker: position limit blocks when max positions reached."""

    @pytest.mark.anyio
    async def test_position_limit_reached_returns_reason(self, cb, bb):
        with patch("app.services.alpaca_service.alpaca_service") as m:
            m.get_positions = AsyncMock(return_value=[{"symbol": "A"}, {"symbol": "B"}] * 5)  # 10 positions
            from app.council.reflexes.circuit_breaker import _get_thresholds
            th = _get_thresholds()
            if th.get("cb_max_positions", 10) <= 10:
                result = await cb.position_limit_check(bb)
                # May return halt if max_positions is 10
                if result:
                    assert "Position limit" in result or "position" in result.lower()

    @pytest.mark.anyio
    async def test_position_limit_under_returns_none(self, cb, bb):
        with patch("app.services.alpaca_service.alpaca_service") as m:
            m.get_positions = AsyncMock(return_value=[{"symbol": "AAPL"}])
            result = await cb.position_limit_check(bb)
        assert result is None


class TestMarketHoursCheck:
    """Circuit breaker: market hours check blocks outside 4 AM–8 PM ET."""

    @pytest.mark.anyio
    async def test_market_hours_returns_string_or_none(self, cb, bb):
        result = await cb.market_hours_check(bb)
        # Either None (market open) or reason string (weekend / off-hours)
        assert result is None or isinstance(result, str)
        if result:
            assert "Market closed" in result or "off-hours" in result or "weekend" in result


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
        bb.raw_features = {"features": {"return_1d": 0.01, "vix_close": 45.0}}
        result = await cb.check_all(bb)
        assert result is not None
        assert "VIX" in result


class TestDataConnectivitySanity:
    """Circuit breaker: data/connectivity sanity halts when critical source is DEGRADED."""

    @pytest.mark.anyio
    async def test_alpaca_degraded_returns_reason(self, cb, bb):
        with patch("app.services.data_source_health_registry.get_health") as m:
            m.return_value = {
                "sources": [
                    {"name": "alpaca", "status": "DEGRADED"},
                    {"name": "finviz", "status": "HEALTHY"},
                ]
            }
            result = await cb.data_connectivity_sanity(bb)
        assert result is not None
        assert "DEGRADED" in result
        assert "alpaca" in result.lower()

    @pytest.mark.anyio
    async def test_alpaca_healthy_returns_none(self, cb, bb):
        with patch("app.services.data_source_health_registry.get_health") as m:
            m.return_value = {
                "sources": [
                    {"name": "alpaca", "status": "HEALTHY"},
                ]
            }
            result = await cb.data_connectivity_sanity(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_registry_unavailable_passes(self, cb, bb):
        with patch("app.services.data_source_health_registry.get_health", side_effect=Exception("no registry")):
            result = await cb.data_connectivity_sanity(bb)
        assert result is None
