"""Integration tests for 24/5 trading pipeline components.

Tests council gate threshold adjustments, turbo scanner gating,
alpaca stream polling intervals, and scheduler session awareness.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.data_swarm.session_clock import TradingSession


class TestCouncilGateThresholds:
    """Verify session-aware threshold adjustments in council gate."""

    @pytest.mark.parametrize("session_value,expected_adj", [
        ("regular", 0),
        ("pre_market", 5),
        ("after_hours", 5),
        ("overnight", 10),
        ("weekend", 100),
    ])
    def test_threshold_adjustment_values(self, session_value, expected_adj):
        """Each session should add the correct points to gate threshold."""
        from app.council.agent_config import (
            _SESSION_THRESHOLD_ADJUSTMENTS,
            get_session_threshold_adjustment,
        )
        # Direct lookup
        assert _SESSION_THRESHOLD_ADJUSTMENTS[session_value] == expected_adj

    @pytest.mark.parametrize("session_value,expected_adj", [
        ("regular", 0),
        ("pre_market", 5),
        ("overnight", 10),
    ])
    def test_get_session_threshold_adjustment(self, session_value, expected_adj):
        """get_session_threshold_adjustment() should use SessionClock."""
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = TradingSession(session_value)

        with patch(
            "app.services.data_swarm.session_clock.get_session_clock",
            return_value=mock_clock,
        ):
            from app.council.agent_config import get_session_threshold_adjustment
            adj = get_session_threshold_adjustment()

        assert adj == expected_adj

    def test_weekend_effectively_blocks(self):
        """Weekend +100 adjustment should make any threshold unreachable."""
        from app.council.agent_config import _SESSION_THRESHOLD_ADJUSTMENTS
        # Even the lowest regime threshold (55 for risk_on) + 100 = 155
        # No signal score can reach 155 (scores are 0-100)
        weekend_adj = _SESSION_THRESHOLD_ADJUSTMENTS["weekend"]
        assert weekend_adj >= 100, "Weekend adjustment must be >= 100 to block all signals"


class TestCouncilGateBurstWindow:
    """Verify the 4AM pre-market burst window.

    _is_market_open_burst() does `from datetime import datetime` inside
    the method body, so we can't patch datetime.datetime.now directly
    (immutable C type). Instead we create a mock datetime class that
    returns controlled values from now().
    """

    def _make_gate(self):
        from app.council.council_gate import CouncilGate
        return CouncilGate.__new__(CouncilGate)

    def _run_burst_check(self, weekday, hour, minute):
        """Run _is_market_open_burst with a mocked ET time."""
        import datetime as dt_module
        from datetime import datetime as real_datetime
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo

        mock_now = real_datetime(2026, 3, 16 + weekday, hour, minute,
                                 tzinfo=ZoneInfo("America/New_York"))

        class MockDatetime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                return mock_now

        gate = self._make_gate()
        with patch.object(dt_module, "datetime", MockDatetime):
            return gate._is_market_open_burst()

    def test_burst_window_regular_open(self):
        """9:30-10:00 AM Monday should be a burst window."""
        assert self._run_burst_check(weekday=0, hour=9, minute=45) is True

    def test_burst_window_premarket_4am(self):
        """4:00-4:15 AM Monday should be a burst window (24/5 session transition)."""
        assert self._run_burst_check(weekday=0, hour=4, minute=5) is True

    def test_no_burst_midday(self):
        """12:00 PM Monday should NOT be a burst window."""
        assert self._run_burst_check(weekday=0, hour=12, minute=0) is False

    def test_no_burst_weekend(self):
        """Saturday should NOT be a burst window even at 9:45 AM."""
        assert self._run_burst_check(weekday=5, hour=9, minute=45) is False


class TestTurboScannerGating:
    """Verify turbo scanner uses _is_scanning_active() for 24/5."""

    @pytest.mark.parametrize("session,expected_active", [
        (TradingSession.REGULAR, True),
        (TradingSession.PRE_MARKET, True),
        (TradingSession.AFTER_HOURS, True),
        (TradingSession.OVERNIGHT, True),
        (TradingSession.WEEKEND, False),
    ])
    def test_is_scanning_active(self, session, expected_active):
        """Scanner should be active in all sessions except WEEKEND."""
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = session

        with patch(
            "app.services.data_swarm.session_clock.get_session_clock",
            return_value=mock_clock,
        ):
            from app.services.turbo_scanner import TurboScanner
            result = TurboScanner._is_scanning_active()

        assert result == expected_active, (
            f"Session {session.value}: scanning should be {'active' if expected_active else 'inactive'}"
        )


class TestAlpacaStreamPolling:
    """Verify alpaca stream service polling intervals per session."""

    def test_overnight_poll_interval(self):
        """Overnight should use 60s poll interval (not 30s)."""
        from app.services.alpaca_stream_service import AlpacaStreamService
        svc = AlpacaStreamService.__new__(AlpacaStreamService)
        svc.SNAPSHOT_POLL_INTERVAL = 30
        svc.OVERNIGHT_POLL_INTERVAL = 60
        svc._session = "overnight"
        assert svc._get_poll_interval() == 60

    def test_regular_poll_interval(self):
        """Regular/pre/post should use 30s poll interval."""
        from app.services.alpaca_stream_service import AlpacaStreamService
        svc = AlpacaStreamService.__new__(AlpacaStreamService)
        svc.SNAPSHOT_POLL_INTERVAL = 30
        svc.OVERNIGHT_POLL_INTERVAL = 60
        for session in ["regular", "pre", "post"]:
            svc._session = session
            assert svc._get_poll_interval() == 30, f"Session {session} should use 30s interval"


class TestSchedulerSessionAwareness:
    """Verify scheduler is_trading_session() and get_cycle_interval()."""

    @pytest.mark.parametrize("session,expected_active", [
        (TradingSession.REGULAR, True),
        (TradingSession.PRE_MARKET, True),
        (TradingSession.AFTER_HOURS, True),
        (TradingSession.OVERNIGHT, True),
        (TradingSession.WEEKEND, False),
    ])
    def test_is_trading_session(self, session, expected_active):
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = session

        with patch("app.services.data_swarm.session_clock.get_session_clock", return_value=mock_clock):
            from app.jobs.scheduler import is_trading_session
            assert is_trading_session() == expected_active

    @pytest.mark.parametrize("session_value,expected_interval", [
        ("regular", 900),
        ("pre_market", 1800),
        ("after_hours", 1800),
        ("overnight", 3600),
        ("weekend", 0),
    ])
    def test_cycle_intervals(self, session_value, expected_interval):
        mock_clock = MagicMock()
        mock_clock.get_current_session.return_value = TradingSession(session_value)

        with patch("app.services.data_swarm.session_clock.get_session_clock", return_value=mock_clock):
            from app.jobs.scheduler import get_cycle_interval
            assert get_cycle_interval() == expected_interval


class TestSessionStalenessThresholds:
    """Verify session-specific data staleness thresholds."""

    @pytest.mark.parametrize("session_value,expected_seconds", [
        ("regular", 120),
        ("pre_market", 300),
        ("after_hours", 300),
        ("overnight", 600),
        ("weekend", 3600),
    ])
    def test_staleness_thresholds(self, session_value, expected_seconds):
        from app.council.agent_config import _SESSION_STALENESS_THRESHOLDS
        assert _SESSION_STALENESS_THRESHOLDS[session_value] == expected_seconds
