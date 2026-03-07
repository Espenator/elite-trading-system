"""Tests for order_executor.py — Bug 6 (async Kelly) + Bug 19 coverage.

Tests the OrderExecutor class: initialization, gate logic, Kelly integration,
and event handling. Uses mocks for external services (Alpaca, DuckDB).
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.order_executor import OrderExecutor, OrderRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_bus():
    bus = AsyncMock()
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def executor(mock_bus):
    return OrderExecutor(
        message_bus=mock_bus,
        auto_execute=False,
        min_score=70.0,
        max_daily_trades=5,
        cooldown_seconds=60,
        max_portfolio_heat=0.25,
        max_single_position=0.10,
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestOrderExecutorInit:
    def test_default_state(self, executor):
        assert executor._running is False
        assert executor._signals_received == 0
        assert executor._signals_executed == 0
        assert executor._signals_rejected == 0

    def test_parameter_validation(self, mock_bus):
        """Parameters are range-validated."""
        exe = OrderExecutor(
            message_bus=mock_bus,
            min_score=-10,
            max_daily_trades=0,
            cooldown_seconds=-100,
            max_portfolio_heat=5.0,
        )
        assert exe.min_score >= 0.0
        assert exe.max_daily_trades >= 1
        assert exe.cooldown_seconds >= 0
        assert exe.max_portfolio_heat <= 1.0

    @pytest.mark.anyio
    async def test_start_subscribes_to_council_verdict(self, executor, mock_bus):
        await executor.start()
        assert executor._running is True
        mock_bus.subscribe.assert_called()
        call_args = mock_bus.subscribe.call_args
        assert call_args[0][0] == "council.verdict"

    @pytest.mark.anyio
    async def test_stop_unsubscribes(self, executor, mock_bus):
        await executor.start()
        await executor.stop()
        assert executor._running is False
        mock_bus.unsubscribe.assert_called()


# ---------------------------------------------------------------------------
# OrderRecord
# ---------------------------------------------------------------------------

class TestOrderRecord:
    def test_create_record(self):
        record = OrderRecord(
            order_id="test-123",
            client_order_id="et-AAPL-abc12345",
            symbol="AAPL",
            side="buy",
            qty=10,
            order_type="market",
            limit_price=None,
            stop_loss=175.0,
            take_profit=195.0,
            signal_score=82.5,
            council_confidence=0.78,
            kelly_pct=0.045,
            regime="BULLISH",
            status="pending",
            timestamp=time.time(),
        )
        assert record.symbol == "AAPL"
        assert record.side == "buy"
        assert record.qty == 10
        assert record.status == "pending"
        assert record.reject_reason is None


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------

class TestGateLogic:
    @pytest.mark.anyio
    async def test_hold_verdict_is_ignored(self, executor, mock_bus):
        """Verdict with direction='hold' should be silently skipped."""
        await executor.start()
        await executor._on_council_verdict({
            "symbol": "AAPL",
            "final_direction": "hold",
            "final_confidence": 0.0,
            "execution_ready": True,
            "signal_data": {"score": 80, "regime": "NEUTRAL", "price": 180},
            "price": 180,
        })
        mock_bus.publish.assert_not_called()

    @pytest.mark.anyio
    async def test_execution_not_ready_is_ignored(self, executor, mock_bus):
        """Verdict with execution_ready=False should be skipped."""
        await executor.start()
        await executor._on_council_verdict({
            "symbol": "AAPL",
            "final_direction": "buy",
            "final_confidence": 0.85,
            "execution_ready": False,
            "signal_data": {"score": 80, "regime": "NEUTRAL", "price": 180},
            "price": 180,
        })
        mock_bus.publish.assert_not_called()

    @pytest.mark.anyio
    async def test_mock_source_rejected(self, executor, mock_bus):
        """Mock data source should be rejected."""
        await executor.start()
        await executor._on_council_verdict({
            "symbol": "AAPL",
            "final_direction": "buy",
            "final_confidence": 0.85,
            "execution_ready": True,
            "signal_data": {
                "score": 80,
                "regime": "NEUTRAL",
                "source": "mock_data",
                "price": 180,
            },
            "price": 180,
        })
        assert executor._signals_rejected == 1

    @pytest.mark.anyio
    async def test_daily_trade_limit(self, executor, mock_bus):
        """After max_daily_trades, new signals should be rejected."""
        await executor.start()
        executor._daily_trade_count = 5
        executor._daily_reset_date = time.strftime("%Y-%m-%d")
        await executor._on_council_verdict({
            "symbol": "AAPL",
            "final_direction": "buy",
            "final_confidence": 0.85,
            "execution_ready": True,
            "signal_data": {"score": 80, "regime": "NEUTRAL", "price": 180},
            "price": 180,
        })
        assert executor._signals_rejected >= 1

    @pytest.mark.anyio
    async def test_cooldown_rejects_rapid_fire(self, executor, mock_bus):
        """Same symbol within cooldown period should be rejected."""
        await executor.start()
        executor._symbol_last_trade["AAPL"] = time.time()
        await executor._on_council_verdict({
            "symbol": "AAPL",
            "final_direction": "buy",
            "final_confidence": 0.85,
            "execution_ready": True,
            "signal_data": {"score": 80, "regime": "NEUTRAL", "price": 180},
            "price": 180,
        })
        assert executor._signals_rejected >= 1

    @pytest.mark.anyio
    async def test_missing_symbol_is_ignored(self, executor, mock_bus):
        """Verdict without symbol should be silently ignored."""
        await executor.start()
        await executor._on_council_verdict({
            "final_direction": "buy",
            "final_confidence": 0.85,
            "execution_ready": True,
        })

    @pytest.mark.anyio
    async def test_zero_price_is_ignored(self, executor, mock_bus):
        """Verdict with price=0 should be silently ignored."""
        await executor.start()
        await executor._on_council_verdict({
            "symbol": "AAPL",
            "final_direction": "buy",
            "final_confidence": 0.85,
            "execution_ready": True,
            "signal_data": {"score": 80, "regime": "NEUTRAL", "price": 0},
            "price": 0,
        })


# ---------------------------------------------------------------------------
# Lazy service loading
# ---------------------------------------------------------------------------

class TestServiceLoading:
    def test_kelly_sizer_lazy_load(self, executor):
        """Kelly sizer should be loaded on first access."""
        assert executor._kelly_sizer is None
        sizer = executor._get_kelly_sizer()
        assert sizer is not None
        assert executor._get_kelly_sizer() is sizer

    def test_kelly_sizer_respects_max_position(self, mock_bus):
        """Kelly sizer should use the executor's max_single_position."""
        exe = OrderExecutor(message_bus=mock_bus, max_single_position=0.05)
        sizer = exe._get_kelly_sizer()
        assert sizer.max_allocation == 0.05
