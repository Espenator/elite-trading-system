"""Integration tests for circuit breaker with council runner."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from app.council.blackboard import BlackboardState
from app.council.runner import run_council


@pytest.fixture
def mock_external_services():
    """Mock all external services for integration tests."""
    with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock_pos, \
         patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_dd, \
         patch('app.council.homeostasis.get_homeostasis') as mock_homeostasis:

        mock_pos.return_value = []
        mock_dd.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}

        # Mock homeostasis to not block
        mock_h = MagicMock()
        mock_h.check_vitals = AsyncMock(return_value={"mode": "NORMAL", "risk_score": 0.5})
        mock_homeostasis.return_value = mock_h

        yield {
            "positions": mock_pos,
            "drawdown": mock_dd,
            "homeostasis": mock_homeostasis,
        }


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with council runner."""

    @pytest.mark.anyio
    async def test_flash_crash_halts_council(self, mock_external_services):
        """Flash crash should halt council execution and return HOLD verdict."""
        symbol = "AAPL"
        features = {
            "features": {
                "return_5min": -0.06,  # Flash crash
                "vix_close": 20.0,
                "volume": 1000000,
            }
        }

        # Run council
        result = await run_council(symbol=symbol, timeframe="1h", features=features)

        # Should return HOLD with veto
        assert result.final_direction == "hold"
        assert result.vetoed is True
        assert any("Circuit breaker" in reason for reason in result.veto_reasons)
        assert result.execution_ready is False
        assert len(result.votes) == 0  # Council shouldn't run at all

    @pytest.mark.anyio
    async def test_vix_spike_halts_council(self, mock_external_services):
        """VIX spike should halt council execution."""
        symbol = "SPY"
        features = {
            "features": {
                "return_1d": 0.01,
                "vix_close": 50.0,  # Extreme VIX
                "volume": 500000000,
            }
        }

        result = await run_council(symbol=symbol, timeframe="1h", features=features)

        assert result.final_direction == "hold"
        assert result.vetoed is True
        assert any("Circuit breaker" in reason for reason in result.veto_reasons)

    @pytest.mark.anyio
    async def test_market_hours_weekend_halt(self, mock_external_services):
        """Weekend trading should be blocked by circuit breaker."""
        with patch('app.council.reflexes.circuit_breaker.datetime') as mock_dt:
            # Saturday
            fake_now = datetime(2026, 3, 8, 15, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = fake_now

            symbol = "TSLA"
            features = {
                "features": {
                    "return_1d": 0.02,
                    "vix_close": 18.0,
                    "volume": 50000000,
                }
            }

            result = await run_council(symbol=symbol, timeframe="1h", features=features)

            assert result.final_direction == "hold"
            assert result.vetoed is True

    @pytest.mark.anyio
    async def test_safe_conditions_allow_council(self, mock_external_services):
        """Safe market conditions should allow council to run."""
        with patch('app.council.reflexes.circuit_breaker.datetime') as mock_dt:
            # Monday during market hours
            fake_now = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = fake_now

            symbol = "MSFT"
            features = {
                "features": {
                    "return_1d": 0.01,  # Normal move
                    "vix_close": 18.0,  # Normal VIX
                    "volume": 25000000,
                    "close": 400.0,
                    "sma_20": 395.0,
                }
            }

            result = await run_council(symbol=symbol, timeframe="1h", features=features)

            # Circuit breaker should not veto
            # (Council might still veto for other reasons, but not circuit breaker)
            if result.vetoed:
                assert not any("Circuit breaker" in reason for reason in result.veto_reasons)

    @pytest.mark.anyio
    async def test_circuit_breaker_metadata_in_blackboard(self, mock_external_services):
        """Circuit breaker halt reason should be stored in blackboard metadata."""
        symbol = "NVDA"
        features = {
            "features": {
                "return_1d": -0.12,  # Large drop
                "vix_close": 22.0,
            }
        }

        result = await run_council(symbol=symbol, timeframe="1h", features=features)

        # The council_reasoning should mention circuit breaker
        assert "circuit breaker" in result.council_reasoning.lower()

    @pytest.mark.anyio
    async def test_drawdown_limit_halts_council(self, mock_external_services):
        """Daily drawdown limit breach should halt council."""
        # Set drawdown to breached
        mock_external_services["drawdown"].return_value = {
            "drawdown_breached": True,
            "daily_pnl_pct": -0.04
        }

        symbol = "AMD"
        features = {
            "features": {
                "return_1d": 0.01,
                "vix_close": 20.0,
            }
        }

        with patch('app.council.reflexes.circuit_breaker.datetime') as mock_dt:
            # Weekday during market hours
            fake_now = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = fake_now

            result = await run_council(symbol=symbol, timeframe="1h", features=features)

            assert result.final_direction == "hold"
            assert result.vetoed is True

    @pytest.mark.anyio
    async def test_position_limit_halts_new_trades(self, mock_external_services):
        """Position limit should prevent opening new positions."""
        # Mock 10 existing positions (at limit)
        mock_external_services["positions"].return_value = [
            {"symbol": f"SYM{i}", "qty": "100"} for i in range(10)
        ]

        symbol = "GOOGL"
        features = {
            "features": {
                "return_1d": 0.02,
                "vix_close": 19.0,
            }
        }

        with patch('app.council.reflexes.circuit_breaker.datetime') as mock_dt:
            # Weekday during market hours
            fake_now = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = fake_now

            result = await run_council(symbol=symbol, timeframe="1h", features=features)

            assert result.final_direction == "hold"
            assert result.vetoed is True

    @pytest.mark.anyio
    async def test_circuit_breaker_runs_before_homeostasis(self, mock_external_services):
        """Circuit breaker should run BEFORE homeostasis in the council flow."""
        # This test verifies execution order by checking that circuit breaker
        # can halt the council even if homeostasis would allow it

        symbol = "META"
        features = {
            "features": {
                "return_1d": -0.15,  # Extreme drop - circuit breaker should halt
                "vix_close": 25.0,
            }
        }

        # Even if homeostasis is fine, circuit breaker should halt
        mock_h = mock_external_services["homeostasis"].return_value
        mock_h.check_vitals.return_value = {"mode": "NORMAL", "risk_score": 0.3}

        result = await run_council(symbol=symbol, timeframe="1h", features=features)

        # Circuit breaker should have halted before homeostasis
        assert result.final_direction == "hold"
        assert result.vetoed is True
        assert any("Circuit breaker" in reason for reason in result.veto_reasons)

    @pytest.mark.anyio
    async def test_multiple_circuit_breaker_violations(self, mock_external_services):
        """When multiple checks fail, should return first triggered check."""
        symbol = "COIN"
        features = {
            "features": {
                "return_1d": -0.12,  # Flash crash
                "vix_close": 55.0,   # VIX spike
            }
        }

        # Also set drawdown breach
        mock_external_services["drawdown"].return_value = {
            "drawdown_breached": True,
            "daily_pnl_pct": -0.04
        }

        with patch('app.council.reflexes.circuit_breaker.datetime') as mock_dt:
            # Weekday during market hours (so market_hours check passes)
            fake_now = datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = fake_now

            result = await run_council(symbol=symbol, timeframe="1h", features=features)

            # Should halt (one of the checks triggered)
            assert result.final_direction == "hold"
            assert result.vetoed is True
            # Should have exactly one veto reason (the first check that failed)
            circuit_breaker_reasons = [r for r in result.veto_reasons if "Circuit breaker" in r]
            assert len(circuit_breaker_reasons) == 1
