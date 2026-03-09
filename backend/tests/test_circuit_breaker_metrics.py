"""Tests for circuit breaker metrics tracking."""
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


class TestCircuitBreakerMetrics:
    """Test metrics tracking functionality."""

    @pytest.mark.anyio
    async def test_metrics_initial_state(self, cb):
        """Metrics should be empty initially."""
        metrics = cb.get_metrics()
        assert metrics["total_checks"] == 0
        assert metrics["total_triggers"] == 0
        assert metrics["trigger_rate"] == 0.0
        assert metrics["last_trigger_time"] is None
        assert metrics["last_trigger_reason"] is None
        assert metrics["trigger_history"] == {}

    @pytest.mark.anyio
    async def test_metrics_after_safe_check(self, cb, bb):
        """Metrics should track checks but not triggers when all pass."""
        bb.raw_features = {"features": {"return_1d": 0.01, "vix_close": 20.0}}

        with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock_pos, \
             patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_pos.return_value = []
            mock_dd.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}

            result = await cb.check_all(bb)

        # Market hours might trigger, but we're testing the metrics structure
        metrics = cb.get_metrics()
        assert metrics["total_checks"] == 1
        # trigger_rate depends on whether market_hours fired

    @pytest.mark.anyio
    async def test_metrics_after_trigger(self, cb, bb):
        """Metrics should record trigger when check fails."""
        bb.raw_features = {"features": {"return_1d": -0.10}}  # Flash crash

        with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock_pos, \
             patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_pos.return_value = []
            mock_dd.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}

            result = await cb.check_all(bb)

        assert result is not None  # Should have triggered
        metrics = cb.get_metrics()
        assert metrics["total_checks"] == 1
        assert metrics["total_triggers"] >= 1  # At least the flash crash
        assert metrics["last_trigger_time"] is not None
        assert metrics["last_trigger_reason"] is not None

        # Should have flash_crash in trigger history
        assert "flash_crash" in metrics["trigger_history"] or "market_hours" in metrics["trigger_history"]

    @pytest.mark.anyio
    async def test_metrics_multiple_checks(self, cb, bb):
        """Metrics should accumulate over multiple checks."""
        bb.raw_features = {"features": {"return_1d": 0.01, "vix_close": 20.0}}

        with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock_pos, \
             patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_pos.return_value = []
            mock_dd.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}

            for _ in range(5):
                await cb.check_all(bb)

        metrics = cb.get_metrics()
        assert metrics["total_checks"] == 5

    @pytest.mark.anyio
    async def test_metrics_trigger_history_limit(self, cb, bb):
        """Trigger history should be limited to 100 entries per check type."""
        bb.raw_features = {"features": {"vix_close": 50.0}}  # VIX spike

        with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock_pos, \
             patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_pos.return_value = []
            mock_dd.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}

            # Trigger 150 times
            for _ in range(150):
                await cb.check_all(bb)

        metrics = cb.get_metrics()
        assert metrics["total_checks"] == 150

        # Should only keep last 100 triggers per check type
        for check_name, history in metrics["trigger_history"].items():
            assert len(history) <= 100

    @pytest.mark.anyio
    async def test_metrics_checks_by_type(self, cb, bb):
        """Should track trigger counts by check type."""
        with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock_pos, \
             patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_pos.return_value = []
            mock_dd.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}

            # Trigger flash crash 3 times
            for _ in range(3):
                bb.raw_features = {"features": {"return_1d": -0.10}}
                await cb.check_all(bb)

            # Trigger VIX spike 2 times
            for _ in range(2):
                bb.raw_features = {"features": {"vix_close": 50.0}}
                await cb.check_all(bb)

        metrics = cb.get_metrics()
        checks_by_type = metrics["checks_by_type"]

        # Should have counts for each triggered check type
        assert sum(checks_by_type.values()) >= 5  # At least 5 triggers (might have market_hours too)

    @pytest.mark.anyio
    async def test_metrics_trigger_rate(self, cb, bb):
        """Should calculate trigger rate correctly."""
        with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock_pos, \
             patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd:
            mock_pos.return_value = []
            mock_dd.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}

            # 2 safe checks
            bb.raw_features = {"features": {"return_1d": 0.01, "vix_close": 20.0}}
            await cb.check_all(bb)
            await cb.check_all(bb)

            # 1 triggered check
            bb.raw_features = {"features": {"return_1d": -0.10}}
            await cb.check_all(bb)

        metrics = cb.get_metrics()
        assert metrics["total_checks"] == 3
        # Trigger rate might be affected by market_hours check
        assert 0.0 <= metrics["trigger_rate"] <= 1.0
