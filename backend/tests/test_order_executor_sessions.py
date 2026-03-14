"""Tests for order executor 24/5 session-aware order parameters.

Verifies _get_session_order_params() returns correct time_in_force
and extended_hours values for each TradingSession.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.data_swarm.session_clock import TradingSession


class TestGetSessionOrderParams:
    """Test _get_session_order_params() mapping for each session."""

    @pytest.mark.parametrize("session,expected_extended", [
        (TradingSession.REGULAR, False),
        (TradingSession.PRE_MARKET, True),
        (TradingSession.AFTER_HOURS, True),
        (TradingSession.OVERNIGHT, True),
        (TradingSession.WEEKEND, False),
    ])
    def test_session_order_params(self, session, expected_extended):
        """Each session should map to correct extended_hours flag."""
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = session

        with patch(
            "app.services.order_executor.get_session_clock",
            return_value=mock_clock,
        ):
            from app.services.order_executor import _get_session_order_params
            params = _get_session_order_params()

        assert params["time_in_force"] == "day", "time_in_force should always be 'day'"
        assert params["extended_hours"] == expected_extended, (
            f"Session {session.value}: expected extended_hours={expected_extended}"
        )

    def test_regular_hours_no_extended(self):
        """Regular hours should NOT set extended_hours (standard market order)."""
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = TradingSession.REGULAR

        with patch(
            "app.services.order_executor.get_session_clock",
            return_value=mock_clock,
        ):
            from app.services.order_executor import _get_session_order_params
            params = _get_session_order_params()

        assert params == {"time_in_force": "day", "extended_hours": False}

    def test_overnight_enables_extended(self):
        """Overnight session MUST enable extended_hours for Alpaca 24/5."""
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = TradingSession.OVERNIGHT

        with patch(
            "app.services.order_executor.get_session_clock",
            return_value=mock_clock,
        ):
            from app.services.order_executor import _get_session_order_params
            params = _get_session_order_params()

        assert params == {"time_in_force": "day", "extended_hours": True}

    def test_weekend_queues_for_next_open(self):
        """Weekend orders should use day TIF without extended (queued for Mon open)."""
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = TradingSession.WEEKEND

        with patch(
            "app.services.order_executor.get_session_clock",
            return_value=mock_clock,
        ):
            from app.services.order_executor import _get_session_order_params
            params = _get_session_order_params()

        assert params["extended_hours"] is False


class TestOrderParamsUsedInExecutor:
    """Verify that _get_session_order_params is actually called in order paths."""

    def test_no_hardcoded_time_in_force(self):
        """Ensure no remaining hardcoded time_in_force='day' in order_executor.py."""
        import inspect
        from app.services import order_executor

        source = inspect.getsource(order_executor)
        # Count occurrences of the old pattern
        hardcoded = source.count('"time_in_force": "day"')
        # The only place it should appear is inside _get_session_order_params itself (2 return statements)
        assert hardcoded == 2, (
            f"Found {hardcoded} hardcoded time_in_force='day' — expected exactly 2 "
            f"(inside _get_session_order_params return statements)"
        )
