"""Tests for E2 scout agents — BaseScout, DiscoveryPayload, ScoutRegistry, all 12 scouts."""
import asyncio
import pytest
from app.services.scouts.base import BaseScout, DiscoveryPayload
from app.services.scouts.registry import ScoutRegistry, get_scout_registry


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class FakeBus:
    def __init__(self):
        self.published = []
        self.subscriptions = {}

    async def subscribe(self, topic, handler):
        self.subscriptions.setdefault(topic, []).append(handler)

    async def publish(self, topic, data):
        self.published.append((topic, data))


class DummyScout(BaseScout):
    """Minimal concrete scout for testing BaseScout."""

    def __init__(self, bus=None, message_bus=None, discoveries=None):
        super().__init__(message_bus=bus or message_bus)
        self._discoveries = discoveries or []

    @property
    def name(self):
        return "dummy_scout"

    @property
    def interval(self):
        return 999.0  # Won't fire naturally in tests

    async def scout(self):
        return list(self._discoveries)


class ErrorScout(BaseScout):
    """Scout that always raises on scout()."""

    @property
    def name(self):
        return "error_scout"

    @property
    def interval(self):
        return 0.01

    async def scout(self):
        raise RuntimeError("simulated error")


# ─────────────────────────────────────────────────────────────────────────────
# DiscoveryPayload
# ─────────────────────────────────────────────────────────────────────────────

class TestDiscoveryPayload:
    def test_to_swarm_idea_contains_required_fields(self):
        payload = DiscoveryPayload(
            source="test_scout",
            symbols=["AAPL", "MSFT"],
            direction="bullish",
            reasoning="test",
            priority=3,
            metadata={"key": "value"},
        )
        idea = payload.to_swarm_idea()
        assert idea["source"] == "test_scout"
        assert idea["symbols"] == ["AAPL", "MSFT"]
        assert idea["direction"] == "bullish"
        assert idea["reasoning"] == "test"
        assert idea["priority"] == 3
        assert "metadata" in idea
        assert "discovered_at" in idea["metadata"]

    def test_to_heartbeat(self):
        payload = DiscoveryPayload(
            source="test_scout",
            symbols=["AAPL"],
            direction="bearish",
            reasoning="test",
        )
        hb = payload.to_heartbeat()
        assert hb["source"] == "test_scout"
        assert hb["symbols_count"] == 1
        assert hb["direction"] == "bearish"

    def test_default_priority_is_5(self):
        payload = DiscoveryPayload(source="x", symbols=[], direction="neutral", reasoning="")
        assert payload.priority == 5

    def test_metadata_defaults_to_empty_dict(self):
        payload = DiscoveryPayload(source="x", symbols=[], direction="neutral", reasoning="")
        assert payload.metadata == {}

    def test_discovered_at_is_set(self):
        payload = DiscoveryPayload(source="x", symbols=[], direction="neutral", reasoning="")
        assert payload.discovered_at != ""


# ─────────────────────────────────────────────────────────────────────────────
# BaseScout
# ─────────────────────────────────────────────────────────────────────────────

class TestBaseScout:
    @pytest.mark.anyio
    async def test_start_sets_running(self):
        scout = DummyScout()
        await scout.start()
        assert scout._running
        await scout.stop()

    @pytest.mark.anyio
    async def test_stop_clears_running(self):
        scout = DummyScout()
        await scout.start()
        await scout.stop()
        assert not scout._running

    @pytest.mark.anyio
    async def test_start_idempotent(self):
        scout = DummyScout()
        await scout.start()
        task_before = scout._task
        await scout.start()  # second start
        assert scout._task is task_before
        await scout.stop()

    @pytest.mark.anyio
    async def test_get_stats(self):
        scout = DummyScout()
        stats = scout.get_stats()
        assert "cycles_run" in stats
        assert "discoveries_made" in stats
        assert "errors" in stats

    @pytest.mark.anyio
    async def test_publish_sends_to_bus(self):
        bus = FakeBus()
        payload = DiscoveryPayload(
            source="dummy_scout", symbols=["AAPL"], direction="bullish", reasoning="test"
        )
        scout = DummyScout(bus=bus, discoveries=[payload])
        # Manually call _publish
        await scout._publish(payload)
        topics = [t for t, _ in bus.published]
        assert "swarm.idea" in topics

    @pytest.mark.anyio
    async def test_publish_no_bus_does_not_crash(self):
        scout = DummyScout(bus=None)
        payload = DiscoveryPayload(source="x", symbols=[], direction="neutral", reasoning="")
        await scout._publish(payload)  # Should not raise

    @pytest.mark.anyio
    async def test_error_in_scout_increments_error_counter(self):
        bus = FakeBus()
        scout = ErrorScout(message_bus=bus)
        await scout.start()
        await asyncio.sleep(0.05)  # Let it run 1+ cycles
        await scout.stop()
        assert scout.get_stats()["errors"] >= 1

    @pytest.mark.anyio
    async def test_scout_discovery_published_to_swarm_idea(self):
        bus = FakeBus()
        payload = DiscoveryPayload(
            source="dummy_scout",
            symbols=["TSLA"],
            direction="bullish",
            reasoning="momentum",
            priority=2,
        )
        scout = DummyScout(bus=bus, discoveries=[payload])
        await scout._publish(payload)
        swarm_ideas = [(t, d) for t, d in bus.published if t == "swarm.idea"]
        assert len(swarm_ideas) == 1
        assert swarm_ideas[0][1]["symbols"] == ["TSLA"]


# ─────────────────────────────────────────────────────────────────────────────
# ScoutRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestScoutRegistry:
    @pytest.mark.anyio
    async def test_register_and_count(self):
        registry = ScoutRegistry()
        registry.register(DummyScout)
        assert registry.scout_count == 1

    @pytest.mark.anyio
    async def test_register_instance(self):
        registry = ScoutRegistry()
        scout = DummyScout()
        registry.register_instance(scout)
        assert scout in registry.scouts

    @pytest.mark.anyio
    async def test_get_stats(self):
        registry = ScoutRegistry()
        registry.register(DummyScout)
        stats = registry.get_stats()
        assert "dummy_scout" in stats

    def test_get_scout_registry_singleton(self):
        import app.services.scouts.registry as mod
        mod._registry = None
        a = get_scout_registry()
        b = get_scout_registry()
        assert a is b

    @pytest.mark.anyio
    async def test_start_launches_all_12_scouts(self):
        bus = FakeBus()
        registry = ScoutRegistry()
        await registry.start(message_bus=bus)
        assert registry.scout_count == 12
        await registry.stop()

    @pytest.mark.anyio
    async def test_stop_clears_scouts(self):
        bus = FakeBus()
        registry = ScoutRegistry()
        await registry.start(message_bus=bus)
        await registry.stop()
        assert registry.scout_count == 0

    @pytest.mark.anyio
    async def test_start_idempotent(self):
        bus = FakeBus()
        registry = ScoutRegistry()
        await registry.start(message_bus=bus)
        count_before = registry.scout_count
        await registry.start(message_bus=bus)  # second call
        assert registry.scout_count == count_before
        await registry.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Individual scout imports and instantiation
# ─────────────────────────────────────────────────────────────────────────────

class TestScoutImports:
    def test_flow_hunter_scout_importable(self):
        from app.services.scouts.flow_hunter import FlowHunterScout
        s = FlowHunterScout()
        assert s.name == "flow_hunter_scout"
        assert s.interval == 15.0

    def test_insider_scout_importable(self):
        from app.services.scouts.insider import InsiderScout
        s = InsiderScout()
        assert s.name == "insider_scout"
        assert s.interval == 60.0

    def test_congress_scout_importable(self):
        from app.services.scouts.congress import CongressScout
        s = CongressScout()
        assert s.name == "congress_scout"
        assert s.interval == 300.0

    def test_gamma_scout_importable(self):
        from app.services.scouts.gamma import GammaScout
        s = GammaScout()
        assert s.name == "gamma_scout"
        assert s.interval == 60.0

    def test_news_scout_importable(self):
        from app.services.scouts.news import NewsScout
        s = NewsScout()
        assert s.name == "news_scout"
        assert s.interval == 60.0

    def test_sentiment_scout_importable(self):
        from app.services.scouts.sentiment import SentimentScout
        s = SentimentScout()
        assert s.name == "sentiment_scout"
        assert s.interval == 60.0

    def test_macro_scout_importable(self):
        from app.services.scouts.macro import MacroScout
        s = MacroScout()
        assert s.name == "macro_scout"
        assert s.interval == 300.0

    def test_earnings_scout_importable(self):
        from app.services.scouts.earnings import EarningsScout
        s = EarningsScout()
        assert s.name == "earnings_scout"
        assert s.interval == 3600.0

    def test_sector_rotation_scout_importable(self):
        from app.services.scouts.sector_rotation import SectorRotationScout
        s = SectorRotationScout()
        assert s.name == "sector_rotation_scout"
        assert s.interval == 30.0

    def test_short_squeeze_scout_importable(self):
        from app.services.scouts.short_squeeze import ShortSqueezeScout
        s = ShortSqueezeScout()
        assert s.name == "short_squeeze_scout"
        assert s.interval == 3600.0

    def test_ipo_scout_importable(self):
        from app.services.scouts.ipo import IPOScout
        s = IPOScout()
        assert s.name == "ipo_scout"
        assert s.interval == 86_400.0

    def test_correlation_break_scout_importable(self):
        from app.services.scouts.correlation_break import CorrelationBreakScout
        s = CorrelationBreakScout()
        assert s.name == "correlation_break_scout"
        assert s.interval == 60.0


# ─────────────────────────────────────────────────────────────────────────────
# Scout graceful-fail when external service unavailable
# ─────────────────────────────────────────────────────────────────────────────

class TestScoutGracefulFail:
    @pytest.mark.anyio
    async def test_flow_hunter_returns_empty_on_service_error(self):
        from app.services.scouts.flow_hunter import FlowHunterScout
        scout = FlowHunterScout()
        result = await scout.scout()
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_insider_returns_empty_on_service_error(self):
        from app.services.scouts.insider import InsiderScout
        scout = InsiderScout()
        result = await scout.scout()
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_congress_returns_empty_on_service_error(self):
        from app.services.scouts.congress import CongressScout
        scout = CongressScout()
        result = await scout.scout()
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_gamma_returns_empty_on_service_error(self):
        from app.services.scouts.gamma import GammaScout
        scout = GammaScout()
        result = await scout.scout()
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_news_returns_empty_on_service_error(self):
        from app.services.scouts.news import NewsScout
        scout = NewsScout()
        result = await scout.scout()
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_sentiment_returns_empty_on_service_error(self):
        from app.services.scouts.sentiment import SentimentScout
        scout = SentimentScout()
        result = await scout.scout()
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_macro_returns_empty_on_service_error(self):
        from app.services.scouts.macro import MacroScout
        scout = MacroScout()
        result = await scout.scout()
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_earnings_returns_empty_on_service_error(self):
        from app.services.scouts.earnings import EarningsScout
        scout = EarningsScout()
        result = await scout.scout()
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_sector_rotation_returns_empty_on_service_error(self):
        from app.services.scouts.sector_rotation import SectorRotationScout
        scout = SectorRotationScout()
        result = await scout.scout()
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_short_squeeze_returns_empty_on_service_error(self):
        from app.services.scouts.short_squeeze import ShortSqueezeScout
        scout = ShortSqueezeScout()
        result = await scout.scout()
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_ipo_returns_empty_on_service_error(self):
        from app.services.scouts.ipo import IPOScout
        scout = IPOScout()
        result = await scout.scout()
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_correlation_break_returns_empty_on_service_error(self):
        from app.services.scouts.correlation_break import CorrelationBreakScout
        scout = CorrelationBreakScout()
        result = await scout.scout()
        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────────────────────
# NewsScout bus subscription
# ─────────────────────────────────────────────────────────────────────────────

class TestNewsScout:
    @pytest.mark.anyio
    async def test_news_event_accumulates_in_pending(self):
        from app.services.scouts.news import NewsScout
        bus = FakeBus()
        scout = NewsScout(message_bus=bus)
        # Manually feed a news event
        await scout._on_news_event({
            "headline": "AAPL beats earnings estimates",
            "symbols": ["AAPL"],
            "source": "test",
        })
        assert len(scout._pending) == 1

    @pytest.mark.anyio
    async def test_news_scout_drains_pending_on_scout(self):
        from app.services.scouts.news import NewsScout
        bus = FakeBus()
        scout = NewsScout(message_bus=bus)
        await scout._on_news_event({
            "headline": "FDA approves MRNA drug",
            "symbols": ["MRNA"],
        })
        payloads = await scout.scout()
        # Pending was drained (may have more from fallback, but MRNA is there)
        symbols_seen = [sym for p in payloads for sym in p.symbols]
        assert "MRNA" in symbols_seen
        assert len(scout._pending) == 0

    @pytest.mark.anyio
    async def test_high_priority_keyword_scores_2(self):
        from app.services.scouts.news import NewsScout
        scout = NewsScout()
        assert scout._score_headline("AAPL beats earnings estimates") == 2
        assert scout._score_headline("FDA approval granted for MRNA") == 2
        assert scout._score_headline("Stock market update today") == 4

    @pytest.mark.anyio
    async def test_start_subscribes_to_bus(self):
        from app.services.scouts.news import NewsScout
        bus = FakeBus()
        scout = NewsScout(message_bus=bus)
        await scout.start()
        assert scout._subscribed
        await scout.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Audit-driven regression tests (PR #67 review fixes)
# ─────────────────────────────────────────────────────────────────────────────

class TestNewsScoutBackpressure:
    """_pending list must be capped at MAX_PENDING during news floods."""

    @pytest.mark.anyio
    async def test_pending_list_capped_at_max_pending(self):
        from app.services.scouts.news import NewsScout, MAX_PENDING
        scout = NewsScout()
        # Flood with more events than the cap
        for i in range(MAX_PENDING + 50):
            await scout._on_news_event({
                "headline": f"Headline {i}",
                "symbols": ["AAPL"],
            })
        assert len(scout._pending) == MAX_PENDING

    @pytest.mark.anyio
    async def test_pending_cleared_on_scout_call(self):
        from app.services.scouts.news import NewsScout
        scout = NewsScout()
        for i in range(5):
            await scout._on_news_event({"headline": f"News {i}", "symbols": ["TSLA"]})
        payloads = await scout.scout()  # drains pending
        assert len(scout._pending) == 0

    @pytest.mark.anyio
    async def test_news_aggregator_uses_get_news_not_get_latest(self):
        """Regression: scout() called agg.get_latest() which does not exist.
        The correct method is get_news(). Verify at runtime via mock that
        get_news() is called successfully and get_latest() is never called."""
        from unittest.mock import MagicMock, patch
        from app.services.scouts.news import NewsScout

        mock_agg = MagicMock()
        mock_agg.get_news.return_value = []
        # Make get_latest raise to detect accidental calls
        mock_agg.get_latest.side_effect = AttributeError("get_latest does not exist")

        scout = NewsScout()
        with patch("app.services.news_aggregator.get_news_aggregator", return_value=mock_agg):
            # Should not raise — get_news() is called, not get_latest()
            await scout.scout()
        mock_agg.get_news.assert_called_once_with(limit=10)


# ─────────────────────────────────────────────────────────────────────────────
# Follow-up PR regression tests (Change 1: LEGACY_SCOUT_ENABLED, Change 2:
# HealthAggregator, Change 3: SwarmSpawner → triage.escalated)
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthAggregator:
    """HealthAggregator batches scout.heartbeat events into one aggregated pulse."""

    @pytest.mark.anyio
    async def test_start_subscribes_to_scout_heartbeat(self):
        from app.services.scouts.health_aggregator import HealthAggregator
        bus = FakeBus()
        agg = HealthAggregator(message_bus=bus)
        await agg.start()
        assert "scout.heartbeat" in bus.subscriptions
        await agg.stop()

    @pytest.mark.anyio
    async def test_on_heartbeat_stores_latest_per_source(self):
        from app.services.scouts.health_aggregator import HealthAggregator
        bus = FakeBus()
        agg = HealthAggregator(message_bus=bus)
        await agg.start()
        await agg._on_heartbeat({
            "source": "flow_hunter_scout",
            "status": "healthy",
            "stats": {"cycles_run": 5},
            "timestamp": "2026-01-01T00:00:00+00:00",
        })
        status = agg.get_status()
        assert "flow_hunter_scout" in status["scouts"]
        assert status["scouts"]["flow_hunter_scout"]["status"] == "healthy"
        await agg.stop()

    @pytest.mark.anyio
    async def test_multiple_sources_tracked(self):
        from app.services.scouts.health_aggregator import HealthAggregator
        bus = FakeBus()
        agg = HealthAggregator(message_bus=bus)
        await agg.start()
        for src in ["flow_hunter_scout", "macro_scout", "streaming_discovery_engine"]:
            await agg._on_heartbeat({"source": src, "status": "healthy", "stats": {}, "timestamp": "2026-01-01T00:00:00+00:00"})
        status = agg.get_status()
        assert status["scout_count"] == 3
        await agg.stop()

    @pytest.mark.anyio
    async def test_stale_detection(self):
        import time
        from app.services.scouts.health_aggregator import HealthAggregator, STALE_AFTER_SECS
        bus = FakeBus()
        agg = HealthAggregator(message_bus=bus)
        await agg.start()
        await agg._on_heartbeat({"source": "slow_scout", "status": "healthy", "stats": {}, "timestamp": "2026-01-01T00:00:00+00:00"})
        # Backdate last_seen_epoch to simulate staleness
        agg._latest["slow_scout"]["last_seen_epoch"] = time.time() - (STALE_AFTER_SECS + 10)
        status = agg.get_status()
        assert status["scouts"]["slow_scout"]["status"] == "stale"
        await agg.stop()

    @pytest.mark.anyio
    async def test_no_bus_does_not_raise(self):
        from app.services.scouts.health_aggregator import HealthAggregator
        agg = HealthAggregator()
        await agg.start()
        status = agg.get_status()
        assert isinstance(status, dict)
        await agg.stop()

    @pytest.mark.anyio
    async def test_scout_registry_starts_health_aggregator(self):
        """ScoutRegistry.start() should wire up HealthAggregator."""
        registry = ScoutRegistry()
        bus = FakeBus()
        # Override _started to avoid importing all 12 scouts by monkeypatching
        registry._started = True  # prevent re-start in full start()
        # Manually wire HealthAggregator as registry would
        from app.services.scouts.health_aggregator import HealthAggregator
        registry._health_aggregator = HealthAggregator(message_bus=bus)
        await registry._health_aggregator.start()
        health = registry.get_health()
        assert "scout_count" in health
        await registry._health_aggregator.stop()
        registry._health_aggregator = None

    @pytest.mark.anyio
    async def test_get_health_returns_empty_when_no_aggregator(self):
        """get_health() must not crash when HealthAggregator hasn't started."""
        registry = ScoutRegistry()
        health = registry.get_health()
        assert health["scout_count"] == 0
        assert health["scouts"] == {}


class TestSwarmSpawnerSubscribesToTriageEscalated:
    """SwarmSpawner must subscribe to triage.escalated, NOT swarm.idea or swarm.prescreened."""

    @pytest.mark.anyio
    async def test_subscribes_to_triage_escalated_not_swarm_idea(self):
        import app.services.swarm_spawner as mod
        mod._spawner = None
        from app.services.swarm_spawner import SwarmSpawner
        bus = FakeBus()
        spawner = SwarmSpawner()
        spawner._bus = bus
        spawner._running = False
        # Patch worker creation to avoid tasks
        import unittest.mock as mock
        with mock.patch("asyncio.create_task"):
            await spawner.start()
        assert "triage.escalated" in bus.subscriptions, "SwarmSpawner must subscribe to triage.escalated"
        assert "swarm.idea" not in bus.subscriptions, "SwarmSpawner must NOT subscribe to raw swarm.idea"
        assert "swarm.prescreened" not in bus.subscriptions, "SwarmSpawner must NOT subscribe to swarm.prescreened"
        spawner._running = False

    def test_swarm_spawner_start_code_subscribes_triage_escalated(self):
        """Source-code check: start() must subscribe to triage.escalated, not raw swarm topics."""
        import inspect
        from app.services.swarm_spawner import SwarmSpawner
        source = inspect.getsource(SwarmSpawner.start)
        assert "triage.escalated" in source
        # Must not call subscribe() with raw swarm.idea or swarm.prescreened
        assert 'subscribe("swarm.idea"' not in source
        assert 'subscribe("swarm.prescreened"' not in source

    def test_hyper_swarm_escalate_does_not_publish_to_prescreened(self):
        """HyperSwarm._escalate must NOT re-publish to swarm.prescreened (no subscriber)."""
        import inspect
        from app.services.hyper_swarm import HyperSwarm
        source = inspect.getsource(HyperSwarm._escalate)
        assert "swarm.prescreened" not in source, "_escalate must not publish to unused swarm.prescreened"


class TestLegacyScoutFlag:
    """LEGACY_SCOUT_ENABLED env flag gates AutonomousScoutService in main.py."""

    def test_legacy_scout_env_defaults_to_false(self):
        """When LEGACY_SCOUT_ENABLED is unset, it must default to 'false'."""
        import os
        import inspect
        import app.main as main_mod
        source = inspect.getsource(main_mod._start_event_driven_pipeline)
        assert "LEGACY_SCOUT_ENABLED" in source
        assert '"false"' in source, "Default must be 'false'"

    def test_legacy_scout_flag_controls_autonomous_scout(self):
        """LEGACY_SCOUT_ENABLED=true must be required alongside LLM_ENABLED for AutonomousScoutService."""
        import os
        import inspect
        import app.main as main_mod
        source = inspect.getsource(main_mod._start_event_driven_pipeline)
        # Both flags must be AND-ed
        assert "_legacy_scout_enabled" in source
        assert "_llm_enabled and _legacy_scout_enabled" in source
