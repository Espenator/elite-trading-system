"""Tests for circuit breaker 24/5 session awareness.

Verifies market_hours_check() only blocks WEEKEND and that
get_session_position_limit() returns correct sizing per session.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.data_swarm.session_clock import TradingSession
from app.council.reflexes.circuit_breaker import CircuitBreaker


@pytest.fixture
def breaker():
    return CircuitBreaker()


class TestMarketHoursCheck:
    """Verify circuit breaker only blocks WEEKEND, not other sessions."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("session,should_block", [
        (TradingSession.REGULAR, False),
        (TradingSession.PRE_MARKET, False),
        (TradingSession.AFTER_HOURS, False),
        (TradingSession.OVERNIGHT, False),
        (TradingSession.WEEKEND, True),
    ])
    async def test_market_hours_per_session(self, breaker, session, should_block):
        """Only WEEKEND should return a blocking message."""
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = session

        with patch(
            "app.services.data_swarm.session_clock.get_session_clock",
            return_value=mock_clock,
        ):
            blackboard = MagicMock()
            result = await breaker.market_hours_check(blackboard)

        if should_block:
            assert result is not None, f"WEEKEND should block trading"
            assert "weekend" in result.lower()
        else:
            assert result is None, (
                f"Session {session.value} should NOT block trading, got: {result}"
            )

    @pytest.mark.asyncio
    async def test_overnight_is_not_blocked(self, breaker):
        """Critical: overnight must NOT be blocked for 24/5 trading."""
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = TradingSession.OVERNIGHT

        with patch(
            "app.services.data_swarm.session_clock.get_session_clock",
            return_value=mock_clock,
        ):
            result = await breaker.market_hours_check(MagicMock())

        assert result is None, "Overnight should be active for 24/5 trading"


class TestSessionPositionLimit:
    """Verify position sizing limits per session."""

    @pytest.mark.parametrize("session,expected_limit", [
        (TradingSession.REGULAR, 1.0),
        (TradingSession.PRE_MARKET, 0.75),
        (TradingSession.AFTER_HOURS, 0.75),
        (TradingSession.OVERNIGHT, 0.50),
        (TradingSession.WEEKEND, 0.0),
    ])
    def test_position_limit_per_session(self, breaker, session, expected_limit):
        """Each session should have the correct position sizing limit."""
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = session

        with patch(
            "app.services.data_swarm.session_clock.get_session_clock",
            return_value=mock_clock,
        ):
            limit = breaker.get_session_position_limit()

        assert limit == expected_limit, (
            f"Session {session.value}: expected limit {expected_limit}, got {limit}"
        )

    def test_regular_full_size(self, breaker):
        """Regular hours should allow full position sizes (1.0 = 100%)."""
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = TradingSession.REGULAR

        with patch(
            "app.services.data_swarm.session_clock.get_session_clock",
            return_value=mock_clock,
        ):
            assert breaker.get_session_position_limit() == 1.0

    def test_weekend_zero_size(self, breaker):
        """Weekend should block all positions (0.0 = 0%)."""
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = TradingSession.WEEKEND

        with patch(
            "app.services.data_swarm.session_clock.get_session_clock",
            return_value=mock_clock,
        ):
            assert breaker.get_session_position_limit() == 0.0
