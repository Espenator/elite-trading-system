"""Tests for Execution Simulator — slippage + partial fills."""
import pytest

from app.services.execution_simulator import ExecutionSimulator, SimulatedFill


class TestSlippage:
    """Slippage always worsens price."""

    @pytest.fixture
    def sim(self):
        return ExecutionSimulator(slippage_bps=5.0, seed=42)

    def test_buy_slippage_worsens_price(self, sim):
        """Buy orders fill at higher price than intended."""
        for _ in range(50):
            fill = sim.simulate_fill(price=100.0, side="buy")
            assert fill.fill_price >= fill.intended_price

    def test_sell_slippage_worsens_price(self, sim):
        """Sell orders fill at lower price than intended."""
        for _ in range(50):
            fill = sim.simulate_fill(price=100.0, side="sell")
            assert fill.fill_price <= fill.intended_price

    def test_slippage_bps_positive(self, sim):
        fill = sim.simulate_fill(price=150.0, side="buy")
        assert fill.slippage_bps > 0

    def test_configurable_slippage(self):
        low = ExecutionSimulator(slippage_bps=1.0, seed=42)
        high = ExecutionSimulator(slippage_bps=50.0, seed=42)
        fill_low = low.simulate_fill(price=100.0, side="buy")
        fill_high = high.simulate_fill(price=100.0, side="buy")
        assert fill_high.slippage_bps > fill_low.slippage_bps


class TestPartialFills:
    """Fill ratios in (0, 1]."""

    @pytest.fixture
    def sim(self):
        return ExecutionSimulator(slippage_bps=5.0, seed=42, partial_fill_enabled=True)

    def test_fill_ratio_bounds(self, sim):
        for _ in range(100):
            fill = sim.simulate_fill(price=100.0, side="buy")
            assert 0 < fill.fill_ratio <= 1.0

    def test_large_order_lower_fill(self, sim):
        """Large order relative to volume should have lower fill ratio."""
        fills_small = []
        fills_large = []
        for _ in range(20):
            f = sim.simulate_fill(price=100.0, side="buy", volume=1_000_000, order_qty=100)
            fills_small.append(f.fill_ratio)
        sim_large = ExecutionSimulator(slippage_bps=5.0, seed=42, partial_fill_enabled=True)
        for _ in range(20):
            f = sim_large.simulate_fill(price=100.0, side="buy", volume=1_000_000, order_qty=200_000)
            fills_large.append(f.fill_ratio)
        avg_small = sum(fills_small) / len(fills_small)
        avg_large = sum(fills_large) / len(fills_large)
        assert avg_small > avg_large

    def test_disabled_partial_fills(self):
        sim = ExecutionSimulator(slippage_bps=5.0, seed=42, partial_fill_enabled=False)
        fill = sim.simulate_fill(price=100.0, side="buy")
        assert fill.fill_ratio == 1.0


class TestDeterminism:
    """Fixed seed produces repeatable results."""

    def test_same_seed_same_results(self):
        sim1 = ExecutionSimulator(slippage_bps=5.0, seed=123)
        sim2 = ExecutionSimulator(slippage_bps=5.0, seed=123)
        for _ in range(10):
            f1 = sim1.simulate_fill(price=100.0, side="buy")
            f2 = sim2.simulate_fill(price=100.0, side="buy")
            assert f1.fill_price == f2.fill_price
            assert f1.fill_ratio == f2.fill_ratio
            assert f1.slippage_bps == f2.slippage_bps

    def test_different_seed_different_results(self):
        sim1 = ExecutionSimulator(slippage_bps=5.0, seed=1)
        sim2 = ExecutionSimulator(slippage_bps=5.0, seed=2)
        f1 = sim1.simulate_fill(price=100.0, side="buy")
        f2 = sim2.simulate_fill(price=100.0, side="buy")
        assert f1.fill_price != f2.fill_price


class TestSimulatedFill:
    """SimulatedFill dataclass."""

    def test_fields_present(self):
        sim = ExecutionSimulator(slippage_bps=5.0, seed=42)
        fill = sim.simulate_fill(price=150.0, side="buy")
        assert isinstance(fill, SimulatedFill)
        assert fill.intended_price == 150.0
        assert fill.side == "buy"
        assert fill.timestamp > 0
        assert fill.volume_impact_bps >= 0
        assert fill.spread_cost_bps >= 0
