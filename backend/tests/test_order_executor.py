"""Tests for order_executor.py — Bug 6 (async Kelly) + Bug 19 coverage.

Tests the OrderExecutor class: initialization, gate logic, Kelly integration,
and event handling. Uses mocks for external services (Alpaca, DuckDB).
"""
import pytest
import time
from datetime import datetime, timezone, timedelta
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
        # OrderExecutor subscribes to execution.validated_verdict (from TradeExecutionRouter), not council.verdict
        assert call_args[0][0] == "execution.validated_verdict"

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
        """Verdict with direction='hold' should not submit order; publishes execution.result for audit."""
        await executor.start()
        await executor._on_council_verdict({
            "symbol": "AAPL",
            "final_direction": "hold",
            "final_confidence": 0.0,
            "execution_ready": True,
            "council_decision_id": "dec-hold-1",
            "signal_data": {"score": 80, "regime": "NEUTRAL", "price": 180},
            "price": 180,
        })
        publish_calls = [c[0][0] for c in mock_bus.publish.call_args_list]
        assert "order.submitted" not in publish_calls
        # execution.result published for audit (reject path)
        result_calls = [c for c in mock_bus.publish.call_args_list if c[0][0] == "execution.result"]
        assert len(result_calls) >= 1
        payload = result_calls[0][0][1]
        assert payload.get("success") is False
        assert payload.get("error_code") == "council_hold"

    @pytest.mark.anyio
    async def test_execution_not_ready_is_ignored(self, executor, mock_bus):
        """Verdict with execution_ready=False should not submit order; may publish execution.result for audit."""
        await executor.start()
        await executor._on_council_verdict({
            "symbol": "AAPL",
            "final_direction": "buy",
            "final_confidence": 0.85,
            "execution_ready": False,
            "signal_data": {"score": 80, "regime": "NEUTRAL", "price": 180},
            "price": 180,
        })
        publish_calls = [c[0][0] for c in mock_bus.publish.call_args_list]
        assert "order.submitted" not in publish_calls

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

    @pytest.mark.anyio
    async def test_ttl_expired_rejected(self, executor, mock_bus):
        """Verdict with created_at older than ttl_seconds should be rejected (DECISION_EXPIRED)."""
        await executor.start()
        old_ts = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        await executor._on_council_verdict({
            "symbol": "AAPL",
            "final_direction": "buy",
            "final_confidence": 0.85,
            "execution_ready": True,
            "signal_data": {"score": 80, "regime": "NEUTRAL", "price": 180},
            "price": 180,
            "created_at": old_ts,
            "ttl_seconds": 30,
        })
        assert executor._signals_rejected == 1


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


# ---------------------------------------------------------------------------
# Order type selection (B5: limit for notional > $5K)
# ---------------------------------------------------------------------------

class TestSelectOrderType:
    """_select_order_type: market <= $5K, limit > $5K, TWAP > $25K."""

    def test_market_for_small_notional(self, executor):
        """Notional <= $5K uses market order."""
        order_type, limit_price = executor._select_order_type(price=100.0, qty=40)  # $4K
        assert order_type == "market"
        assert limit_price is None

    def test_limit_for_notional_above_5k(self, executor):
        """Notional > $5K uses limit order."""
        order_type, limit_price = executor._select_order_type(price=100.0, qty=60)  # $6K
        assert order_type == "limit"
        assert limit_price == 100.0

    def test_twap_for_large_notional(self, executor):
        """Notional > $25K uses TWAP (returns twap, limit_price for slices)."""
        order_type, limit_price = executor._select_order_type(price=100.0, qty=300)  # $30K
        assert order_type == "twap"
        assert limit_price == 100.0


# ---------------------------------------------------------------------------
# Kelly sizing uses real DuckDB stats
# ---------------------------------------------------------------------------

class TestKellyUsesDuckDBStats:
    @pytest.mark.anyio
    async def test_compute_kelly_calls_trade_stats(self, executor, mock_bus):
        """_compute_kelly_size uses trade_stats.get_stats when available (real DuckDB path)."""
        mock_stats = MagicMock()
        mock_stats.get_stats.return_value = {
            "win_rate": 0.55,
            "avg_win_pct": 0.02,
            "avg_loss_pct": 0.015,
            "trade_count": 50,
            "data_source": "duckdb",
        }
        executor._get_trade_stats = MagicMock(return_value=mock_stats)
        mock_alpaca = MagicMock()
        mock_alpaca._cache_get = MagicMock(return_value=None)
        mock_alpaca.get_account = AsyncMock(return_value={"equity": "100000"})
        executor._get_alpaca_service = MagicMock(return_value=mock_alpaca)
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value.fetchone.return_value = (0.02,)
        mock_store = MagicMock()
        mock_store.get_thread_cursor.return_value = mock_cursor
        with patch("app.data.duckdb_storage.duckdb_store", mock_store):
            result = await executor._compute_kelly_size("AAPL", 75.0, "NEUTRAL", 180.0, "buy")
        assert mock_stats.get_stats.called
        assert result.get("stats_source") == "duckdb" or "kelly_pct" in result or "action" in result
