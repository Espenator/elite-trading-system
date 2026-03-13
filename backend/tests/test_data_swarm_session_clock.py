"""Tests for data_swarm.session_clock — trading session and source availability."""

from datetime import datetime
from unittest.mock import patch

import pytest

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]

from app.services.data_swarm.session_clock import (
    ET,
    SourceAvailability,
    TradingSession,
    get_session_clock,
)


def _et(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    """Build a datetime in ET for testing."""
    return datetime(year, month, day, hour, minute, tzinfo=ET)


class TestTradingSession:
    """TradingSession enum and session boundaries."""

    def test_enum_values(self) -> None:
        assert TradingSession.OVERNIGHT.value == "overnight"
        assert TradingSession.PRE_MARKET.value == "pre_market"
        assert TradingSession.REGULAR.value == "regular"
        assert TradingSession.AFTER_HOURS.value == "after_hours"
        assert TradingSession.WEEKEND.value == "weekend"

    def test_session_sources_has_all_sessions(self) -> None:
        assert set(SourceAvailability.SESSION_SOURCES.keys()) == set(TradingSession)

    def test_session_sources_has_all_collector_keys(self) -> None:
        expected_keys = {
            "alpaca_stream", "alpaca_rest", "alpaca_futures",
            "uw_websocket", "uw_rest", "uw_flow",
            "finviz_screener", "finviz_futures",
        }
        for session, sources in SourceAvailability.SESSION_SOURCES.items():
            assert set(sources.keys()) == expected_keys, f"Missing keys for {session}"


class TestSourceAvailabilityGetCurrentSession:
    """get_current_session() for each session window (ET)."""

    def test_regular_session_midday_tuesday(self) -> None:
        clock = SourceAvailability()
        # Tuesday 2026-03-10 12:00 ET
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 10, 12, 0)
            assert clock.get_current_session() == TradingSession.REGULAR

    def test_regular_session_open_930(self) -> None:
        clock = SourceAvailability()
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 10, 9, 30)
            assert clock.get_current_session() == TradingSession.REGULAR

    def test_pre_market_6am(self) -> None:
        clock = SourceAvailability()
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 10, 6, 0)
            assert clock.get_current_session() == TradingSession.PRE_MARKET

    def test_pre_market_9am(self) -> None:
        clock = SourceAvailability()
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 10, 9, 0)
            assert clock.get_current_session() == TradingSession.PRE_MARKET

    def test_after_hours_5pm(self) -> None:
        clock = SourceAvailability()
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 10, 17, 0)
            assert clock.get_current_session() == TradingSession.AFTER_HOURS

    def test_after_hours_7pm(self) -> None:
        clock = SourceAvailability()
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 10, 19, 30)
            assert clock.get_current_session() == TradingSession.AFTER_HOURS

    def test_overnight_10pm(self) -> None:
        clock = SourceAvailability()
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 10, 22, 0)
            assert clock.get_current_session() == TradingSession.OVERNIGHT

    def test_overnight_2am(self) -> None:
        clock = SourceAvailability()
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 11, 2, 0)
            assert clock.get_current_session() == TradingSession.OVERNIGHT

    def test_weekend_saturday_9pm(self) -> None:
        clock = SourceAvailability()
        # 2026-03-14 is Saturday
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 14, 21, 0)
            assert clock.get_current_session() == TradingSession.WEEKEND

    def test_weekend_sunday_noon(self) -> None:
        clock = SourceAvailability()
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 15, 12, 0)
            assert clock.get_current_session() == TradingSession.WEEKEND

    def test_sunday_8pm_is_overnight_not_weekend(self) -> None:
        clock = SourceAvailability()
        # Sunday 8:00 PM ET → Monday overnight session starts
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 15, 20, 0)
            assert clock.get_current_session() == TradingSession.OVERNIGHT


class TestSourceAvailabilityGetActiveSources:
    """get_active_sources() returns correct collector flags per session."""

    def test_regular_all_sources_active(self) -> None:
        clock = SourceAvailability()
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 10, 12, 0)
            active = clock.get_active_sources()
        assert active["alpaca_stream"] is True
        assert active["uw_flow"] is True
        assert active["finviz_screener"] is True

    def test_weekend_only_uw_rest(self) -> None:
        clock = SourceAvailability()
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 15, 12, 0)
            active = clock.get_active_sources()
        assert active["alpaca_stream"] is False
        assert active["uw_rest"] is True
        assert active["uw_flow"] is False
        assert active["finviz_screener"] is False

    def test_overnight_no_finviz_no_flow(self) -> None:
        clock = SourceAvailability()
        with patch("app.services.data_swarm.session_clock.datetime") as m_dt:
            m_dt.now.return_value = _et(2026, 3, 11, 2, 0)
            active = clock.get_active_sources()
        assert active["alpaca_stream"] is True
        assert active["uw_rest"] is True
        assert active["uw_flow"] is False
        assert active["finviz_screener"] is False


class TestGetSessionClock:
    """Singleton get_session_clock()."""

    def test_returns_source_availability(self) -> None:
        clock = get_session_clock()
        assert isinstance(clock, SourceAvailability)

    def test_singleton(self) -> None:
        c1 = get_session_clock()
        c2 = get_session_clock()
        assert c1 is c2
