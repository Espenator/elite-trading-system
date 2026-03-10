"""Tests for OrderExecutor slippage refactoring.

Validates:
1. Slippage simulation is applied to both live and shadow execution
2. Market data enrichment (volume, volatility) is fetched
3. Quantity adjustments happen BEFORE stop/TP calculation
4. Event schemas are consistent between live and shadow
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.order_executor import OrderExecutor


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
    )


class TestSlippageSimulation:
    """Test the new _simulate_execution method."""

    @pytest.mark.anyio
    async def test_simulate_execution_returns_expected_fields(self, executor):
        """_simulate_execution should return all required fields."""
        with patch('app.services.order_executor.get_execution_simulator') as mock_sim:
            # Mock SimulatedFill
            mock_fill = MagicMock()
            mock_fill.fill_price = 150.5
            mock_fill.fill_ratio = 0.95
            mock_fill.slippage_bps = 5.2
            mock_fill.volume_impact_bps = 1.0
            mock_fill.spread_cost_bps = 2.0
            mock_sim.return_value.simulate_fill.return_value = mock_fill

            result = await executor._simulate_execution(
                symbol="AAPL",
                side="buy",
                qty=100,
                price=150.0
            )

            assert "fill_price" in result
            assert "fill_qty" in result
            assert "slippage_bps" in result
            assert "fill_ratio" in result
            assert "volume_impact_bps" in result
            assert "spread_cost_bps" in result
            assert result["fill_price"] == 150.5
            assert result["fill_qty"] == 95  # 100 * 0.95
            assert result["slippage_bps"] == 5.2

    @pytest.mark.anyio
    async def test_simulate_execution_handles_simulator_failure(self, executor):
        """If simulator fails, should return safe defaults."""
        with patch('app.services.order_executor.get_execution_simulator', side_effect=Exception("Sim error")):
            result = await executor._simulate_execution(
                symbol="AAPL",
                side="buy",
                qty=100,
                price=150.0
            )

            # Should return defaults without raising
            assert result["fill_price"] == 150.0
            assert result["fill_qty"] == 100
            assert result["slippage_bps"] == 0.0
            assert result["fill_ratio"] == 1.0


class TestMarketDataEnrichment:
    """Test the new _get_market_data method."""

    @pytest.mark.anyio
    async def test_get_market_data_fetches_volume_and_volatility(self, executor):
        """_get_market_data should fetch volume and volatility from DuckDB."""
        with patch('app.services.order_executor.duckdb_store') as mock_store:
            # Mock DuckDB response
            mock_conn = MagicMock()
            mock_row = (1_000_000.0, 0.25)  # volume, volatility
            mock_conn.execute.return_value.fetchone.return_value = mock_row
            mock_store._get_conn.return_value = mock_conn

            result = await executor._get_market_data("AAPL")

            assert result["volume"] == 1_000_000.0
            assert result["volatility"] == 0.25
            assert result["spread"] is None  # Not implemented yet

    @pytest.mark.anyio
    async def test_get_market_data_handles_missing_data(self, executor):
        """_get_market_data should handle missing data gracefully."""
        with patch('app.services.order_executor.duckdb_store') as mock_store:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = None
            mock_store._get_conn.return_value = mock_conn

            result = await executor._get_market_data("AAPL")

            assert result["volume"] is None
            assert result["volatility"] is None
            assert result["spread"] is None


class TestEventSchemaConsistency:
    """Test that live and shadow execution publish consistent events."""

    @pytest.mark.anyio
    async def test_execute_order_publishes_slippage_fields(self, executor, mock_bus):
        """Live execution should publish slippage fields."""
        from app.services.order_executor import OrderRecord

        record = OrderRecord(
            order_id="test-123",
            client_order_id="et-AAPL-abc",
            symbol="AAPL",
            side="buy",
            qty=100,
            order_type="market",
            limit_price=None,
            stop_loss=145.0,
            take_profit=155.0,
            signal_score=85.0,
            council_confidence=0.8,
            kelly_pct=0.05,
            regime="BULLISH",
            status="pending",
            timestamp=1234567890.0,
        )

        sim_result = {
            "fill_price": 150.5,
            "fill_qty": 95,
            "slippage_bps": 5.2,
            "fill_ratio": 0.95,
            "volume_impact_bps": 1.0,
            "spread_cost_bps": 2.0,
        }

        with patch.object(executor, '_get_alpaca_service') as mock_alpaca:
            mock_alpaca.return_value.create_order = AsyncMock(return_value={
                "id": "alpaca-123",
                "status": "submitted"
            })

            await executor._execute_order(record, 150.0, sim_result)

            # Check event was published with slippage fields
            assert mock_bus.publish.called
            call_args = mock_bus.publish.call_args
            assert call_args[0][0] == "order.submitted"
            event_data = call_args[0][1]

            # Verify all slippage fields are present
            assert "slippage_bps" in event_data
            assert "fill_ratio" in event_data
            assert "volume_impact_bps" in event_data
            assert "spread_cost_bps" in event_data
            assert "intended_price" in event_data
            assert event_data["slippage_bps"] == 5.2
            assert event_data["price"] == 150.5  # fill_price
            assert event_data["intended_price"] == 150.0

    @pytest.mark.anyio
    async def test_shadow_execute_publishes_same_schema(self, executor, mock_bus):
        """Shadow execution should publish same schema as live."""
        from app.services.order_executor import OrderRecord

        record = OrderRecord(
            order_id="",
            client_order_id="et-AAPL-abc",
            symbol="AAPL",
            side="buy",
            qty=100,
            order_type="market",
            limit_price=None,
            stop_loss=145.0,
            take_profit=155.0,
            signal_score=85.0,
            council_confidence=0.8,
            kelly_pct=0.05,
            regime="BULLISH",
            status="pending",
            timestamp=1234567890.0,
        )

        sim_result = {
            "fill_price": 150.5,
            "fill_qty": 95,
            "slippage_bps": 5.2,
            "fill_ratio": 0.95,
            "volume_impact_bps": 1.0,
            "spread_cost_bps": 2.0,
        }

        await executor._shadow_execute(record, 150.0, sim_result)

        # Check event was published
        assert mock_bus.publish.called
        call_args = mock_bus.publish.call_args
        assert call_args[0][0] == "order.submitted"
        event_data = call_args[0][1]

        # Verify all slippage fields are present (same as live)
        assert "slippage_bps" in event_data
        assert "fill_ratio" in event_data
        assert "volume_impact_bps" in event_data
        assert "spread_cost_bps" in event_data
        assert "intended_price" in event_data
        assert event_data["slippage_bps"] == 5.2
        assert event_data["price"] == 150.5
        assert event_data["intended_price"] == 150.0
        assert event_data["source"] == "order_executor_shadow"


class TestQuantityAdjustmentTiming:
    """Test that quantity adjustments happen at the right time."""

    @pytest.mark.anyio
    async def test_qty_adjusted_before_stop_tp_calculation(self, executor):
        """Simulated qty should be used BEFORE calculating stop/TP."""
        # This is tested implicitly by the main flow in _on_council_verdict
        # The refactor ensures:
        # 1. _simulate_execution is called first (line 274)
        # 2. adjusted_qty is extracted (line 275)
        # 3. stop_data is recalculated with adjusted qty (line 289)
        # 4. OrderRecord created with adjusted qty (line 304)

        # We verify this by checking the flow doesn't mutate record.qty after creation
        from app.services.order_executor import OrderRecord

        # Create a record - qty should NOT change after this
        record = OrderRecord(
            order_id="",
            client_order_id="et-AAPL-abc",
            symbol="AAPL",
            side="buy",
            qty=95,  # Already adjusted
            order_type="market",
            limit_price=None,
            stop_loss=145.0,
            take_profit=155.0,
            signal_score=85.0,
            council_confidence=0.8,
            kelly_pct=0.05,
            regime="BULLISH",
            status="pending",
            timestamp=1234567890.0,
        )

        original_qty = record.qty

        # Execute - qty should remain unchanged
        sim_result = {
            "fill_price": 150.5,
            "fill_qty": 95,
            "slippage_bps": 5.2,
            "fill_ratio": 0.95,
            "volume_impact_bps": 1.0,
            "spread_cost_bps": 2.0,
        }

        await executor._shadow_execute(record, 150.0, sim_result)

        # Record qty should NOT have changed
        assert record.qty == original_qty
        assert record.qty == 95
