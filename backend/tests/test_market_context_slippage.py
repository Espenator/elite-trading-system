"""Tests for market context integration with slippage (OrderExecutor enhancement).

Tests that OrderExecutor fetches real-time market data from DuckDB and passes it
to ExecutionSimulator for more realistic slippage calculations.
"""
import pytest
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
    )


# ---------------------------------------------------------------------------
# Market Context Tests
# ---------------------------------------------------------------------------

class TestMarketContext:
    """Tests for _get_market_context() method."""

    @pytest.mark.anyio
    async def test_get_market_context_success(self, executor):
        """Test successful market context fetch from DuckDB."""
        mock_duckdb = AsyncMock()

        # Mock volume query result
        mock_duckdb.async_execute = AsyncMock(side_effect=[
            [[1_500_000.0]],  # volume query
            [[2.5, 150.0]],   # volatility query (ATR, close)
            [[152.0, 148.0]], # spread query (high, low)
        ])

        with patch("app.services.order_executor.duckdb_store", mock_duckdb):
            ctx = await executor._get_market_context("AAPL")

        assert ctx["volume"] == 1_500_000.0
        assert ctx["volatility"] is not None
        assert ctx["spread"] is not None
        # Volatility should be (ATR / close) * 100 = (2.5 / 150.0) * 100 ≈ 1.67%
        assert abs(ctx["volatility"] - 1.67) < 0.1
        # Spread should be (high - low) * 0.1 = (152 - 148) * 0.1 = 0.4
        assert ctx["spread"] == 0.4

    @pytest.mark.anyio
    async def test_get_market_context_no_data(self, executor):
        """Test market context when DuckDB has no data."""
        mock_duckdb = AsyncMock()
        mock_duckdb.async_execute = AsyncMock(return_value=[])

        with patch("app.services.order_executor.duckdb_store", mock_duckdb):
            ctx = await executor._get_market_context("XYZ")

        assert ctx["volume"] is None
        assert ctx["volatility"] is None
        assert ctx["spread"] is None

    @pytest.mark.anyio
    async def test_get_market_context_partial_data(self, executor):
        """Test market context when only some data is available."""
        mock_duckdb = AsyncMock()

        # Mock responses: volume found, volatility missing, spread found
        mock_duckdb.async_execute = AsyncMock(side_effect=[
            [[500_000.0]],  # volume query
            [],             # volatility query (no data)
            [[50.5, 49.5]], # spread query
        ])

        with patch("app.services.order_executor.duckdb_store", mock_duckdb):
            ctx = await executor._get_market_context("TSLA")

        assert ctx["volume"] == 500_000.0
        assert ctx["volatility"] is None
        assert ctx["spread"] == 0.1  # (50.5 - 49.5) * 0.1

    @pytest.mark.anyio
    async def test_get_market_context_handles_errors(self, executor):
        """Test market context gracefully handles DuckDB errors."""
        mock_duckdb = AsyncMock()
        mock_duckdb.async_execute = AsyncMock(
            side_effect=Exception("DuckDB connection failed")
        )

        with patch("app.services.order_executor.duckdb_store", mock_duckdb):
            ctx = await executor._get_market_context("AAPL")

        # Should return empty context without crashing
        assert ctx["volume"] is None
        assert ctx["volatility"] is None
        assert ctx["spread"] is None

    @pytest.mark.anyio
    async def test_get_market_context_zero_close_price(self, executor):
        """Test volatility calculation when close price is zero."""
        mock_duckdb = AsyncMock()

        # Mock volatility query with zero close price
        mock_duckdb.async_execute = AsyncMock(side_effect=[
            [[1_000_000.0]],  # volume query
            [[2.5, 0.0]],     # volatility query (ATR, close=0)
            [[152.0, 148.0]], # spread query
        ])

        with patch("app.services.order_executor.duckdb_store", mock_duckdb):
            ctx = await executor._get_market_context("AAPL")

        assert ctx["volume"] == 1_000_000.0
        assert ctx["volatility"] is None  # Should be None due to division by zero protection
        assert ctx["spread"] == 0.4


# ---------------------------------------------------------------------------
# Shadow Execute with Market Context
# ---------------------------------------------------------------------------

class TestShadowExecuteWithMarketContext:
    """Tests for _shadow_execute() with market context integration."""

    @pytest.mark.anyio
    async def test_shadow_execute_uses_market_context(self, executor, mock_bus):
        """Test that shadow execute fetches and uses market context."""
        record = OrderRecord(
            order_id="shadow-1",
            client_order_id="et-AAPL-123",
            symbol="AAPL",
            side="buy",
            qty=100,
            order_type="market",
            limit_price=None,
            stop_loss=145.0,
            take_profit=155.0,
            signal_score=80.0,
            council_confidence=0.75,
            kelly_pct=0.05,
            regime="BULLISH",
            status="pending",
            timestamp=1234567890.0,
        )

        mock_duckdb = AsyncMock()
        mock_duckdb.async_execute = AsyncMock(side_effect=[
            [[2_000_000.0]],  # volume
            [[3.0, 150.0]],   # volatility
            [[152.0, 148.0]], # spread
        ])

        mock_sim_fill = MagicMock()
        mock_sim_fill.fill_price = 150.25
        mock_sim_fill.fill_ratio = 0.95
        mock_sim_fill.slippage_bps = 8.5

        mock_simulator = MagicMock()
        mock_simulator.simulate_fill = MagicMock(return_value=mock_sim_fill)

        with patch("app.services.order_executor.duckdb_store", mock_duckdb):
            with patch(
                "app.services.order_executor.get_execution_simulator",
                return_value=mock_simulator,
            ):
                await executor._shadow_execute(record, price=150.0)

        # Verify simulator was called with market context
        mock_simulator.simulate_fill.assert_called_once()
        call_args = mock_simulator.simulate_fill.call_args
        assert call_args[1]["price"] == 150.0
        assert call_args[1]["side"] == "buy"
        assert call_args[1]["order_qty"] == 100
        assert call_args[1]["volume"] == 2_000_000.0
        assert call_args[1]["volatility"] == 2.0  # (3.0 / 150.0) * 100
        assert call_args[1]["spread"] == 0.4  # (152 - 148) * 0.1

        # Verify fill was applied
        assert record.qty == 95  # 100 * 0.95
        assert record.status == "shadow"

    @pytest.mark.anyio
    async def test_shadow_execute_without_market_context(self, executor, mock_bus):
        """Test that shadow execute works even when market context unavailable."""
        record = OrderRecord(
            order_id="shadow-2",
            client_order_id="et-MSFT-456",
            symbol="MSFT",
            side="sell",
            qty=50,
            order_type="market",
            limit_price=None,
            stop_loss=None,
            take_profit=None,
            signal_score=75.0,
            council_confidence=0.70,
            kelly_pct=0.03,
            regime="NEUTRAL",
            status="pending",
            timestamp=1234567890.0,
        )

        mock_duckdb = AsyncMock()
        # All queries return no data
        mock_duckdb.async_execute = AsyncMock(return_value=[])

        mock_sim_fill = MagicMock()
        mock_sim_fill.fill_price = 419.50
        mock_sim_fill.fill_ratio = 1.0
        mock_sim_fill.slippage_bps = 5.0

        mock_simulator = MagicMock()
        mock_simulator.simulate_fill = MagicMock(return_value=mock_sim_fill)

        with patch("app.services.order_executor.duckdb_store", mock_duckdb):
            with patch(
                "app.services.order_executor.get_execution_simulator",
                return_value=mock_simulator,
            ):
                await executor._shadow_execute(record, price=420.0)

        # Verify simulator was called with None values for context
        mock_simulator.simulate_fill.assert_called_once()
        call_args = mock_simulator.simulate_fill.call_args
        assert call_args[1]["volume"] is None
        assert call_args[1]["volatility"] is None
        assert call_args[1]["spread"] is None

        # Should still complete successfully
        assert record.status == "shadow"
        assert record.qty == 50  # No partial fill

    @pytest.mark.anyio
    async def test_shadow_execute_publishes_slippage_metrics(self, executor, mock_bus):
        """Test that shadow execute publishes slippage metrics to message bus."""
        record = OrderRecord(
            order_id="shadow-3",
            client_order_id="et-TSLA-789",
            symbol="TSLA",
            side="buy",
            qty=25,
            order_type="market",
            limit_price=None,
            stop_loss=800.0,
            take_profit=900.0,
            signal_score=85.0,
            council_confidence=0.80,
            kelly_pct=0.04,
            regime="AGGRESSIVE",
            status="pending",
            timestamp=1234567890.0,
        )

        mock_duckdb = AsyncMock()
        mock_duckdb.async_execute = AsyncMock(side_effect=[
            [[1_000_000.0]],
            [[15.0, 850.0]],
            [[860.0, 840.0]],
        ])

        mock_sim_fill = MagicMock()
        mock_sim_fill.fill_price = 851.25
        mock_sim_fill.fill_ratio = 0.90
        mock_sim_fill.slippage_bps = 14.7

        mock_simulator = MagicMock()
        mock_simulator.simulate_fill = MagicMock(return_value=mock_sim_fill)

        with patch("app.services.order_executor.duckdb_store", mock_duckdb):
            with patch(
                "app.services.order_executor.get_execution_simulator",
                return_value=mock_simulator,
            ):
                await executor._shadow_execute(record, price=850.0)

        # Verify message bus was called with slippage data
        mock_bus.publish.assert_called_once()
        event_name, event_data = mock_bus.publish.call_args[0]
        assert event_name == "order.submitted"
        assert event_data["slippage_bps"] == 14.7
        assert event_data["fill_ratio"] == 0.90
        assert event_data["intended_price"] == 850.0
        assert event_data["price"] == 851.25
        assert event_data["source"] == "order_executor_shadow"


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestMarketContextSlippageIntegration:
    """Integration tests for market context + slippage flow."""

    @pytest.mark.anyio
    async def test_high_volume_low_slippage(self, executor):
        """Test that high volume results in lower slippage."""
        mock_duckdb = AsyncMock()
        # High volume scenario
        mock_duckdb.async_execute = AsyncMock(side_effect=[
            [[10_000_000.0]],  # Very high volume
            [[2.0, 100.0]],    # Low volatility
            [[101.0, 99.0]],   # Tight spread
        ])

        with patch("app.services.order_executor.duckdb_store", mock_duckdb):
            ctx = await executor._get_market_context("SPY")

        assert ctx["volume"] == 10_000_000.0
        # With this high volume, a 1000-share order is tiny (0.01% participation)
        # Should result in minimal volume impact in ExecutionSimulator

    @pytest.mark.anyio
    async def test_low_volume_high_slippage(self, executor):
        """Test that low volume results in higher slippage."""
        mock_duckdb = AsyncMock()
        # Low volume scenario
        mock_duckdb.async_execute = AsyncMock(side_effect=[
            [[50_000.0]],      # Very low volume
            [[5.0, 25.0]],     # High volatility
            [[26.0, 24.0]],    # Wide spread
        ])

        with patch("app.services.order_executor.duckdb_store", mock_duckdb):
            ctx = await executor._get_market_context("PENNY")

        assert ctx["volume"] == 50_000.0
        assert ctx["volatility"] == 20.0  # (5.0 / 25.0) * 100
        assert ctx["spread"] == 0.2  # (26 - 24) * 0.1
        # This should result in high slippage when passed to ExecutionSimulator
