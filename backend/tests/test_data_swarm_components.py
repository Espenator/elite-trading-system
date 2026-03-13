"""Tests for data_swarm components: orchestrator, base collector, health monitor, rate limiter, schemas."""

from datetime import datetime, timezone

import pytest

from app.services.data_swarm.schemas import (
    PriceUpdate,
    FlowUpdate,
    ScreenerUpdate,
    FuturesUpdate,
)
from app.services.data_swarm.health_monitor import HealthMonitor, get_health_monitor
from app.services.data_swarm.rate_limiter import RateLimiter, get_rate_limiter_sync
from app.services.data_swarm.swarm_orchestrator import SwarmOrchestrator, get_swarm_orchestrator
from app.services.data_swarm.collectors import (
    COLLECTOR_REGISTRY,
    AlpacaRestCollector,
    FinvizFuturesCollector,
)


class TestSchemas:
    def test_price_update_to_payload(self) -> None:
        pu = PriceUpdate(
            symbol="AAPL",
            price=150.0,
            bid=149.9,
            ask=150.1,
            volume=1_000_000,
            timestamp=datetime.now(timezone.utc),
            source="alpaca",
            session="regular",
            is_realtime=True,
        )
        payload = pu.to_message_bus_payload()
        assert payload["symbol"] == "AAPL"
        assert payload["price"] == 150.0
        assert payload["source"] == "alpaca"
        assert "timestamp" in payload

    def test_flow_update_to_payload(self) -> None:
        fu = FlowUpdate(
            symbol="AAPL",
            flow_type="options",
            direction="bullish",
            premium=10000.0,
            volume=50,
            open_interest=1000,
            strike=150.0,
            expiry="2026-01-17",
            timestamp=datetime.now(timezone.utc),
            source="unusual_whales",
        )
        payload = fu.to_message_bus_payload()
        assert payload["flow_type"] == "options"
        assert payload["direction"] == "bullish"

    def test_screener_update_to_payload(self) -> None:
        su = ScreenerUpdate(
            symbol="NVDA",
            signal_type="unusual_volume",
            price=900.0,
            change_pct=2.5,
            relative_volume=1.8,
            timestamp=datetime.now(timezone.utc),
            source="finviz",
        )
        payload = su.to_message_bus_payload()
        assert payload["signal_type"] == "unusual_volume"
        assert payload["relative_volume"] == 1.8

    def test_futures_update_to_payload(self) -> None:
        fu = FuturesUpdate(
            symbol="ES",
            price=5500.0,
            change_pct=0.1,
            volume=1_000_000,
            timestamp=datetime.now(timezone.utc),
            source="alpaca",
            is_delayed=False,
        )
        payload = fu.to_message_bus_payload()
        assert payload["symbol"] == "ES"
        assert payload["is_delayed"] is False


class TestHealthMonitor:
    def test_record_heartbeat_and_status(self) -> None:
        h = HealthMonitor()
        h.record_heartbeat("alpaca_rest")
        assert h.get_status().get("alpaca_rest") == "healthy"

    def test_record_price_and_freshness(self) -> None:
        h = HealthMonitor()
        h.record_price("AAPL")
        freshness = h.get_freshness()
        assert "AAPL" in freshness
        assert freshness["AAPL"] >= 0

    def test_get_health_monitor_singleton(self) -> None:
        a = get_health_monitor()
        b = get_health_monitor()
        assert a is b


class TestRateLimiter:
    def test_get_rate_limiter_sync(self) -> None:
        r = get_rate_limiter_sync("alpaca_rest")
        assert r.name == "alpaca_rest"

    @pytest.mark.asyncio
    async def test_acquire_does_not_raise(self) -> None:
        from app.services.data_swarm.rate_limiter import get_rate_limiter
        r = await get_rate_limiter("finviz_screener")
        await r.acquire()
        await r.acquire()


class TestSwarmOrchestrator:
    def test_create_collector(self) -> None:
        o = SwarmOrchestrator(symbol_universe=["AAPL", "MSFT"])
        c = o._create_collector("alpaca_rest")
        assert c.source_name == "alpaca_rest"
        assert c.symbol_universe == ["AAPL", "MSFT"]

    def test_create_collector_unknown_raises(self) -> None:
        o = SwarmOrchestrator(symbol_universe=[])
        with pytest.raises(ValueError, match="Unknown collector"):
            o._create_collector("unknown_source")

    def test_get_swarm_orchestrator_default_universe(self) -> None:
        o = get_swarm_orchestrator()
        assert len(o.symbol_universe) > 50
        assert "SPY" in o.symbol_universe

    def test_get_swarm_orchestrator_custom_universe(self) -> None:
        o = get_swarm_orchestrator(symbol_universe=["X"])
        assert o.symbol_universe == ["X"]


class TestCollectorRegistry:
    def test_all_session_sources_have_collector(self) -> None:
        from app.services.data_swarm.session_clock import SourceAvailability
        clock = SourceAvailability()
        active = clock.get_active_sources()
        for name in active:
            assert name in COLLECTOR_REGISTRY, f"Missing collector for {name}"

    def test_alpaca_rest_instantiate(self) -> None:
        c = AlpacaRestCollector(["AAPL"])
        assert c.source_name == "alpaca_rest"
        assert c.poll_interval == 60.0
        assert c.is_streaming is False

    def test_finviz_futures_instantiate(self) -> None:
        c = FinvizFuturesCollector(["SPY"])
        assert c.source_name == "finviz_futures"
        assert c.poll_interval == 300.0
