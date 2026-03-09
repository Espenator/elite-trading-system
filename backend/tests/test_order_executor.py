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


# ---------------------------------------------------------------------------
# Market context and slippage integration
# ---------------------------------------------------------------------------

class TestMarketContextAndSlippage:
    @pytest.mark.anyio
    async def test_get_market_context_returns_dict(self, executor):
        """_get_market_context should return dict with volume, volatility, spread."""
        with patch.object(executor, "_get_alpaca_service") as mock_alpaca_getter:
            mock_alpaca = AsyncMock()
            mock_alpaca_getter.return_value = mock_alpaca
            mock_alpaca.get_snapshots = AsyncMock(return_value=None)
            mock_alpaca.get_bars = AsyncMock(return_value=None)

            context = await executor._get_market_context("AAPL", 180.0)

            assert isinstance(context, dict)
            assert "volume" in context
            assert "volatility" in context
            assert "spread" in context

    @pytest.mark.anyio
    async def test_get_market_context_with_snapshot_data(self, executor):
        """_get_market_context should extract volume and spread from snapshot."""
        with patch.object(executor, "_get_alpaca_service") as mock_alpaca_getter:
            mock_alpaca = AsyncMock()
            mock_alpaca_getter.return_value = mock_alpaca

            # Mock snapshot with volume and bid-ask data
            mock_alpaca.get_snapshots = AsyncMock(return_value={
                "AAPL": {
                    "dailyBar": {"v": 50000000},  # 50M volume
                    "latestQuote": {"bp": 179.95, "ap": 180.05}  # 10¢ spread
                }
            })
            mock_alpaca.get_bars = AsyncMock(return_value=None)

            context = await executor._get_market_context("AAPL", 180.0)

            assert context["volume"] == 50000000
            assert context["spread"] == pytest.approx(0.10, rel=1e-5)  # 180.05 - 179.95

    @pytest.mark.anyio
    async def test_get_market_context_calculates_volatility(self, executor):
        """_get_market_context should calculate realized volatility from bars."""
        with patch.object(executor, "_get_alpaca_service") as mock_alpaca_getter:
            mock_alpaca = AsyncMock()
            mock_alpaca_getter.return_value = mock_alpaca
            mock_alpaca.get_snapshots = AsyncMock(return_value=None)

            # Mock bar data with price series
            bars = [{"c": 100.0 + i * 0.5} for i in range(21)]  # Trending price series
            mock_alpaca.get_bars = AsyncMock(return_value={"bars": bars})

            context = await executor._get_market_context("AAPL", 180.0)

            assert context["volatility"] is not None
            assert isinstance(context["volatility"], float)
            assert context["volatility"] > 0

    @pytest.mark.anyio
    async def test_get_market_context_handles_errors(self, executor):
        """_get_market_context should handle API errors gracefully."""
        with patch.object(executor, "_get_alpaca_service") as mock_alpaca_getter:
            mock_alpaca = AsyncMock()
            mock_alpaca_getter.return_value = mock_alpaca
            mock_alpaca.get_snapshots = AsyncMock(side_effect=Exception("API error"))
            mock_alpaca.get_bars = AsyncMock(side_effect=Exception("API error"))

            context = await executor._get_market_context("AAPL", 180.0)

            # Should return empty context without crashing
            assert context["volume"] is None
            assert context["volatility"] is None
            assert context["spread"] is None

    @pytest.mark.anyio
    async def test_shadow_execute_uses_market_context(self, executor, mock_bus):
        """_shadow_execute should fetch market context and pass to simulator."""
        with patch.object(executor, "_get_market_context") as mock_get_context:
            mock_get_context.return_value = {
                "volume": 10000000,
                "volatility": 0.35,
                "spread": 0.05,
            }

            with patch("app.services.execution_simulator.get_execution_simulator") as mock_sim_getter:
                mock_sim = MagicMock()
                mock_sim_getter.return_value = mock_sim
                mock_sim.simulate_fill = MagicMock(return_value=MagicMock(
                    fill_price=180.10,
                    fill_ratio=0.95,
                    slippage_bps=5.5,
                ))

                record = OrderRecord(
                    order_id="",
                    client_order_id="test-123",
                    symbol="AAPL",
                    side="buy",
                    qty=100,
                    order_type="market",
                    limit_price=None,
                    stop_loss=None,
                    take_profit=None,
                    signal_score=75.0,
                    council_confidence=0.80,
                    kelly_pct=0.05,
                    regime="BULLISH",
                    status="pending",
                    timestamp=time.time(),
                )

                await executor._shadow_execute(record, 180.0)

                # Verify market context was fetched
                mock_get_context.assert_called_once_with("AAPL", 180.0)

                # Verify simulator was called with market context
                mock_sim.simulate_fill.assert_called_once()
                call_kwargs = mock_sim.simulate_fill.call_args[1]
                assert call_kwargs["price"] == 180.0
                assert call_kwargs["side"] == "buy"
                assert call_kwargs["order_qty"] == 100
                assert call_kwargs["volume"] == 10000000
                assert call_kwargs["volatility"] == 0.35
                assert call_kwargs["spread"] == 0.05

    @pytest.mark.anyio
    async def test_shadow_execute_handles_simulator_errors(self, executor, mock_bus):
        """_shadow_execute should handle simulator errors gracefully."""
        with patch.object(executor, "_get_market_context") as mock_get_context:
            mock_get_context.return_value = {"volume": None, "volatility": None, "spread": None}

            with patch("app.services.execution_simulator.get_execution_simulator") as mock_sim_getter:
                mock_sim_getter.side_effect = Exception("Simulator error")

                record = OrderRecord(
                    order_id="",
                    client_order_id="test-123",
                    symbol="AAPL",
                    side="buy",
                    qty=100,
                    order_type="market",
                    limit_price=None,
                    stop_loss=None,
                    take_profit=None,
                    signal_score=75.0,
                    council_confidence=0.80,
                    kelly_pct=0.05,
                    regime="BULLISH",
                    status="pending",
                    timestamp=time.time(),
                )

                # Should not crash
                await executor._shadow_execute(record, 180.0)
                assert record.status == "shadow"
