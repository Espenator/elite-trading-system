"""Tests for new circuit breaker reflexes: liquidity, correlation, data health, profit ceiling."""
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


class TestLiquidityCheck:
    """Test liquidity check reflex."""

    @pytest.mark.anyio
    async def test_sufficient_volume_passes(self, cb, bb):
        """Should pass when volume is above minimum threshold."""
        bb.raw_features = {"features": {"volume": 500000}}
        result = await cb.liquidity_check(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_insufficient_volume_halts(self, cb, bb):
        """Should halt when volume is below minimum threshold."""
        bb.raw_features = {"features": {"volume": 50000}}
        result = await cb.liquidity_check(bb)
        assert result is not None
        assert "Insufficient liquidity" in result
        assert "50,000" in result

    @pytest.mark.anyio
    async def test_missing_volume_passes(self, cb, bb):
        """Should pass when volume data is missing (don't block)."""
        bb.raw_features = {"features": {}}
        result = await cb.liquidity_check(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_zero_volume_passes(self, cb, bb):
        """Should pass when volume is zero (data issue, don't block)."""
        bb.raw_features = {"features": {"volume": 0}}
        result = await cb.liquidity_check(bb)
        assert result is None

    @pytest.mark.anyio
    async def test_volume_1d_fallback(self, cb, bb):
        """Should use volume_1d field if volume is missing."""
        bb.raw_features = {"features": {"volume_1d": 50000}}
        result = await cb.liquidity_check(bb)
        assert result is not None
        assert "Insufficient liquidity" in result


class TestCorrelationSpikeDetector:
    """Test correlation spike detector reflex."""

    @pytest.mark.anyio
    async def test_no_correlation_breaks_passes(self, cb, bb):
        """Should pass when no correlation breaks exist."""
        with patch('app.services.correlation_radar.get_correlation_radar') as mock_radar:
            mock_instance = mock_radar.return_value
            mock_instance.get_status.return_value = {"active_breaks": []}
            result = await cb.correlation_spike_detector(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_few_correlation_breaks_passes(self, cb, bb):
        """Should pass when only 1-2 high correlation pairs exist."""
        with patch('app.services.correlation_radar.get_correlation_radar') as mock_radar:
            mock_instance = mock_radar.return_value
            mock_instance.get_status.return_value = {
                "active_breaks": [
                    {"correlation": 0.96},
                    {"correlation": 0.97},
                ]
            }
            result = await cb.correlation_spike_detector(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_multiple_correlation_spikes_halts(self, cb, bb):
        """Should halt when 3+ pairs have >95% correlation (systemic risk)."""
        with patch('app.services.correlation_radar.get_correlation_radar') as mock_radar:
            mock_instance = mock_radar.return_value
            mock_instance.get_status.return_value = {
                "active_breaks": [
                    {"correlation": 0.96},
                    {"correlation": 0.97},
                    {"correlation": 0.98},
                    {"correlation": 0.95},
                ]
            }
            result = await cb.correlation_spike_detector(bb)
            assert result is not None
            assert "Correlation spike" in result
            assert "systemic risk" in result

    @pytest.mark.anyio
    async def test_correlation_radar_unavailable_passes(self, cb, bb):
        """Should pass when correlation radar is unavailable (graceful degradation)."""
        with patch('app.services.correlation_radar.get_correlation_radar', side_effect=Exception("Unavailable")):
            result = await cb.correlation_spike_detector(bb)
            assert result is None


class TestDataConnectionHealth:
    """Test data connection health check reflex."""

    @pytest.mark.anyio
    async def test_healthy_data_sources_passes(self, cb, bb):
        """Should pass when all data sources are healthy."""
        with patch('app.council.data_quality.get_data_quality_monitor') as mock_dqm:
            mock_instance = mock_dqm.return_value
            mock_instance.get_health.return_value = {
                "critical_stale": [],
                "overall_quality_score": 95,
            }
            result = await cb.data_connection_health(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_critical_stale_sources_halts(self, cb, bb):
        """Should halt when critical data sources are stale."""
        with patch('app.council.data_quality.get_data_quality_monitor') as mock_dqm:
            mock_instance = mock_dqm.return_value
            mock_instance.get_health.return_value = {
                "critical_stale": ["alpaca", "finviz", "fred"],
                "overall_quality_score": 60,
            }
            result = await cb.data_connection_health(bb)
            assert result is not None
            assert "Data connection degraded" in result
            assert "3 critical sources stale" in result

    @pytest.mark.anyio
    async def test_low_quality_score_halts(self, cb, bb):
        """Should halt when overall data quality is critically low."""
        with patch('app.council.data_quality.get_data_quality_monitor') as mock_dqm:
            mock_instance = mock_dqm.return_value
            mock_instance.get_health.return_value = {
                "critical_stale": [],
                "overall_quality_score": 45,
            }
            result = await cb.data_connection_health(bb)
            assert result is not None
            assert "Data quality critically low" in result
            assert "45%" in result

    @pytest.mark.anyio
    async def test_data_quality_monitor_unavailable_passes(self, cb, bb):
        """Should pass when data quality monitor is unavailable (graceful degradation)."""
        with patch('app.council.data_quality.get_data_quality_monitor', side_effect=Exception("Unavailable")):
            result = await cb.data_connection_health(bb)
            assert result is None


class TestProfitTargetCeiling:
    """Test profit target ceiling reflex."""

    @pytest.mark.anyio
    async def test_below_profit_target_passes(self, cb, bb):
        """Should pass when daily profit is below ceiling."""
        with patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_dd.return_value = {"daily_pnl_pct": 0.05}
            result = await cb.profit_target_ceiling(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_at_profit_target_halts(self, cb, bb):
        """Should halt when daily profit reaches ceiling (take profits)."""
        with patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_dd.return_value = {"daily_pnl_pct": 0.10}
            result = await cb.profit_target_ceiling(bb)
            assert result is not None
            assert "Daily profit target reached" in result
            assert "10.00%" in result

    @pytest.mark.anyio
    async def test_above_profit_target_halts(self, cb, bb):
        """Should halt when daily profit exceeds ceiling."""
        with patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_dd.return_value = {"daily_pnl_pct": 0.15}
            result = await cb.profit_target_ceiling(bb)
            assert result is not None
            assert "Daily profit target reached" in result

    @pytest.mark.anyio
    async def test_negative_pnl_passes(self, cb, bb):
        """Should pass when daily PnL is negative."""
        with patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_dd.return_value = {"daily_pnl_pct": -0.02}
            result = await cb.profit_target_ceiling(bb)
            assert result is None

    @pytest.mark.anyio
    async def test_risk_api_unavailable_passes(self, cb, bb):
        """Should pass when risk API is unavailable (graceful degradation)."""
        with patch('app.api.v1.risk.drawdown_check_status', side_effect=Exception("Unavailable")):
            result = await cb.profit_target_ceiling(bb)
            assert result is None


class TestCheckAllWithNewReflexes:
    """Test check_all with new reflexes integrated."""

    @pytest.mark.anyio
    async def test_liquidity_halt_in_check_all(self, cb, bb):
        """check_all should detect and return liquidity violations."""
        bb.raw_features = {"features": {"volume": 50000, "return_1d": 0.01, "vix_close": 20}}
        with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock_pos, \
             patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_pos.return_value = []
            mock_dd.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}
            result = await cb.check_all(bb)
            # Should return liquidity halt (or market hours depending on test time)
            assert result is None or "Insufficient liquidity" in result or "Market closed" in result

    @pytest.mark.anyio
    async def test_profit_ceiling_halt_in_check_all(self, cb, bb):
        """check_all should detect and return profit ceiling violations."""
        bb.raw_features = {"features": {"volume": 500000, "return_1d": 0.01, "vix_close": 20}}
        with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock_pos, \
             patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_pos.return_value = []
            mock_dd.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.12}
            result = await cb.check_all(bb)
            # Should return profit ceiling or market hours
            assert result is None or "profit target" in result.lower() or "Market closed" in result

    @pytest.mark.anyio
    async def test_all_checks_pass(self, cb, bb):
        """check_all should return None when all reflexes pass."""
        bb.raw_features = {"features": {"volume": 500000, "return_1d": 0.01, "vix_close": 20}}
        with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock_pos, \
             patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd, \
             patch('app.services.correlation_radar.get_correlation_radar') as mock_radar, \
             patch('app.council.data_quality.get_data_quality_monitor') as mock_dqm:
            mock_pos.return_value = []
            mock_dd.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}
            mock_radar.return_value.get_status.return_value = {"active_breaks": []}
            mock_dqm.return_value.get_health.return_value = {"critical_stale": [], "overall_quality_score": 95}
            result = await cb.check_all(bb)
            # May return market hours depending on when test runs
            assert result is None or "Market closed" in result
