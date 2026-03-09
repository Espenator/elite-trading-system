"""Tests for the ExecutionAgent with slippage & liquidity guard."""
import pytest

from app.council.agents.execution_agent import evaluate, _calculate_impact_cost


# ---------------------------------------------------------------------------
# Impact Cost Calculation Tests
# ---------------------------------------------------------------------------
class TestImpactCostCalculation:
    """Test the _calculate_impact_cost function."""

    def test_no_l2_data_returns_zero_impact(self):
        """When no L2 data is available, impact should be 0."""
        impact, reasoning = _calculate_impact_cost(
            side="buy",
            position_value=10000.0,
            bid_levels=[],
            ask_levels=[],
        )
        assert impact == 0.0
        assert "No L2 data available" in reasoning

    def test_buy_single_level_full_fill(self):
        """Buying within a single ask level should have minimal impact."""
        # Ask: $100.00 x 200 shares = $20,000 available
        # Position: $10,000 = 100 shares @ $100
        ask_levels = [(100.00, 200)]
        bid_levels = [(99.90, 100)]

        impact, reasoning = _calculate_impact_cost(
            side="buy",
            position_value=10000.0,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
        )

        # Should fill at $100, which is the best ask, so 0% impact
        assert impact == 0.0
        assert "100.00" in reasoning

    def test_buy_multi_level_partial_fill(self):
        """Buying across multiple levels should calculate weighted average impact."""
        # Ask levels: $100.00 x 50, $100.10 x 50, $100.20 x 100
        # Position: $10,000
        # - Level 1: $100 x 50 = $5,000 (50 shares)
        # - Level 2: $100.10 x 50 = $5,005 (49.95 shares)
        # - Total: 99.95 shares, avg price = $10,005 / 99.95 = ~$100.05
        # - Impact: ($100.05 - $100.00) / $100.00 = 0.05%
        ask_levels = [(100.00, 50), (100.10, 50), (100.20, 100)]
        bid_levels = [(99.90, 100)]

        impact, reasoning = _calculate_impact_cost(
            side="buy",
            position_value=10000.0,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
        )

        # Should be around 0.05% (0.0005)
        assert impact > 0.0
        assert impact < 0.001  # Less than 0.1%
        assert "Avg fill" in reasoning

    def test_buy_insufficient_liquidity(self):
        """When order book can't fill the entire order, impact should account for it."""
        # Ask: $100.00 x 10 = $1,000 available
        # Position: $10,000 (needs 100 shares)
        ask_levels = [(100.00, 10)]
        bid_levels = [(99.90, 100)]

        impact, reasoning = _calculate_impact_cost(
            side="buy",
            position_value=10000.0,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
        )

        # Should still calculate impact based on available liquidity
        assert impact == 0.0  # Filled at best price for available shares
        assert "unfilled" in reasoning  # Should note unfilled portion

    def test_sell_single_level_full_fill(self):
        """Selling within a single bid level should have minimal impact."""
        # Bid: $99.90 x 200 shares = $19,980 available
        # Position: $10,000 (need to sell ~100 shares)
        ask_levels = [(100.00, 100)]
        bid_levels = [(99.90, 200)]

        impact, reasoning = _calculate_impact_cost(
            side="sell",
            position_value=10000.0,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
        )

        # Should fill at $99.90, which is the best bid, so 0% impact
        assert impact == 0.0
        assert "99.90" in reasoning

    def test_sell_multi_level_impact(self):
        """Selling across multiple bid levels should show impact."""
        # Bid levels: $99.90 x 50, $99.80 x 50, $99.70 x 100
        # Position: $10,000 (at mid-price ~$99.85, need ~100 shares)
        # - Level 1: $99.90 x 50 = $4,995
        # - Level 2: $99.80 x 50 = $4,990
        # - Total: ~100 shares, avg = ~$99.85
        # - Impact: ($99.90 - $99.85) / $99.90 = 0.05%
        ask_levels = [(100.00, 100)]
        bid_levels = [(99.90, 50), (99.80, 50), (99.70, 100)]

        impact, reasoning = _calculate_impact_cost(
            side="sell",
            position_value=10000.0,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
        )

        # Should be around 0.05% or more
        assert impact >= 0.0
        assert impact < 0.002  # Less than 0.2%
        assert "Avg fill" in reasoning

    def test_high_impact_scenario(self):
        """Test a scenario with high slippage (thin order book)."""
        # Very thin book with wide spreads
        # Ask: $100.00 x 10, $101.00 x 10, $102.00 x 10
        # Position: $10,000 (need ~100 shares)
        # Will need to walk through all levels at increasing prices
        ask_levels = [(100.00, 10), (101.00, 10), (102.00, 10), (103.00, 100)]
        bid_levels = [(99.00, 100)]

        impact, reasoning = _calculate_impact_cost(
            side="buy",
            position_value=10000.0,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
        )

        # Should have significant impact due to thin book
        assert impact > 0.01  # Greater than 1%
        assert "Avg fill" in reasoning


# ---------------------------------------------------------------------------
# ExecutionAgent evaluate() Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestExecutionAgentEvaluate:
    """Test the execution agent's evaluate function with slippage logic."""

    async def test_no_l2_data_does_not_penalize(self):
        """When no L2 data is available, agent should not penalize confidence."""
        features = {"volume": 1000000}
        context = {}  # No l2_quote data

        vote = await evaluate("AAPL", "1d", features, context)

        assert vote.agent_name == "execution"
        assert vote.direction == "hold"
        assert vote.confidence == 0.5  # Base confidence
        assert "No L2 quote data available" in vote.reasoning

    async def test_low_slippage_maintains_confidence(self):
        """When slippage is below threshold, confidence should remain at base level."""
        features = {"volume": 1000000}
        context = {
            "l2_quote": {
                "bids": [(99.90, 1000)],
                "asks": [(100.00, 1000)],
            },
            "intended_direction": "buy",
            "position_value": 10000.0,
        }

        vote = await evaluate("AAPL", "1d", features, context)

        assert vote.agent_name == "execution"
        assert vote.confidence == 0.5  # Should maintain base confidence
        assert "Slippage OK" in vote.reasoning
        assert vote.metadata["slippage_impact"] == 0.0

    async def test_high_slippage_reduces_confidence(self):
        """When slippage exceeds threshold (0.2%), confidence should be reduced."""
        features = {"volume": 1000000}
        # Create a thin order book that will cause >0.2% slippage
        context = {
            "l2_quote": {
                "bids": [(99.00, 10)],
                "asks": [(100.00, 10), (101.00, 10), (102.00, 10), (103.00, 100)],
            },
            "intended_direction": "buy",
            "position_value": 10000.0,
        }

        vote = await evaluate("AAPL", "1d", features, context)

        assert vote.agent_name == "execution"
        # Confidence should be reduced from base 0.5
        assert vote.confidence < 0.5
        assert vote.confidence >= 0.1  # Should not go below minimum
        assert "HIGH SLIPPAGE" in vote.reasoning
        assert vote.metadata["slippage_impact"] > 0.002  # >0.2%

    async def test_volume_veto_overrides_slippage_check(self):
        """Volume veto should take precedence over slippage checks."""
        features = {"volume": 10000}  # Below min_volume_threshold (50k)
        context = {
            "l2_quote": {
                "bids": [(99.90, 1000)],
                "asks": [(100.00, 1000)],
            },
            "intended_direction": "buy",
            "position_value": 10000.0,
        }

        vote = await evaluate("AAPL", "1d", features, context)

        assert vote.veto is True
        assert "Insufficient liquidity" in vote.veto_reason
        assert vote.direction == "hold"
        assert vote.confidence == 0.9  # Veto confidence

    async def test_sell_side_slippage_calculation(self):
        """Test that slippage works correctly for sell orders."""
        features = {"volume": 1000000}
        # Thin bid side for selling
        context = {
            "l2_quote": {
                "bids": [(99.90, 10), (99.00, 10), (98.00, 10), (97.00, 100)],
                "asks": [(100.00, 1000)],
            },
            "intended_direction": "sell",
            "position_value": 10000.0,
        }

        vote = await evaluate("AAPL", "1d", features, context)

        assert vote.agent_name == "execution"
        # Should have some slippage impact from walking down the bid levels
        assert vote.metadata["slippage_impact"] > 0.0

    async def test_confidence_penalty_scales_with_excess_slippage(self):
        """Confidence penalty should scale linearly with excess slippage."""
        features = {"volume": 1000000}

        # Scenario 1: Moderate slippage (0.3% = 0.003)
        context_moderate = {
            "l2_quote": {
                "bids": [(99.00, 100)],
                "asks": [(100.00, 20), (100.30, 100)],  # ~0.3% impact
            },
            "intended_direction": "buy",
            "position_value": 10000.0,
        }

        vote_moderate = await evaluate("AAPL", "1d", features, context_moderate)

        # Scenario 2: Higher slippage (0.5% = 0.005)
        context_high = {
            "l2_quote": {
                "bids": [(99.00, 100)],
                "asks": [(100.00, 10), (100.50, 100)],  # ~0.5% impact
            },
            "intended_direction": "buy",
            "position_value": 10000.0,
        }

        vote_high = await evaluate("AAPL", "1d", features, context_high)

        # Higher slippage should result in lower confidence
        assert vote_high.confidence < vote_moderate.confidence
        assert vote_moderate.confidence < 0.5  # Both should be penalized

    async def test_metadata_includes_impact_reasoning(self):
        """Vote metadata should include detailed impact reasoning."""
        features = {"volume": 1000000}
        context = {
            "l2_quote": {
                "bids": [(99.90, 1000)],
                "asks": [(100.00, 1000)],
            },
            "intended_direction": "buy",
            "position_value": 10000.0,
        }

        vote = await evaluate("AAPL", "1d", features, context)

        assert "slippage_impact" in vote.metadata
        assert "impact_reasoning" in vote.metadata
        assert isinstance(vote.metadata["slippage_impact"], float)
        assert isinstance(vote.metadata["impact_reasoning"], str)
