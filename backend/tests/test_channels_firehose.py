"""Tests for Firehose channel agents: SensoryEvent, router, base agent, API."""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from app.services.channels.schemas import SensoryEvent
from app.services.channels.router import SensoryRouter
from app.services.channels.base_channel_agent import BaseChannelAgent

# Firehose imports for circuit breaker and backpressure tests
from app.services.firehose.base_agent import BaseFirehoseAgent
from app.services.firehose.schemas import SensoryEvent as FirehoseSensoryEvent
from app.services.firehose.schemas import SensorySource


class DummyBus:
    def __init__(self) -> None:
        self.published: list = []

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        self.published.append((topic, data))

    def get_metrics(self) -> Dict[str, Any]:
        return {"dummy": True}


@pytest.mark.asyncio
async def test_sensory_event_from_alpaca_bar_basic():
    bar = {
        "symbol": "AAPL",
        "timestamp": datetime(2026, 3, 10, tzinfo=timezone.utc).isoformat(),
        "open": 100,
        "high": 110,
        "low": 99,
        "close": 105,
        "volume": 1_000_000,
        "source": "alpaca_websocket",
    }
    ev = SensoryEvent.from_alpaca_bar(bar, data_quality="live")
    assert ev.source == "alpaca"
    assert ev.event_type == "bar"
    assert ev.symbols == ["AAPL"]
    assert ev.data_quality == "live"
    assert ev.normalized["close"] == 105.0


@pytest.mark.asyncio
async def test_sensory_event_from_discord_signal():
    ev = SensoryEvent.from_discord_signal(
        symbols=["SPY", "QQQ"],
        direction="bullish",
        text="Big flow in SPY calls",
        channel="UW-live-options-flow",
        source_type="unusual_whales",
        data_quality="live",
    )
    assert ev.source == "discord"
    assert ev.event_type == "social_post"
    assert ev.symbols == ["SPY", "QQQ"]
    assert "discord" in ev.tags
    assert "bullish" in ev.tags


@pytest.mark.asyncio
async def test_sensory_event_from_uw_source_event():
    """UW SourceEvent-style payload becomes SensoryEvent (flow, congress, darkpool)."""
    flow_payload = {
        "topic": "unusual_whales.flow",
        "source": "unusual_whales",
        "source_kind": "options_flow",
        "symbol": "SPY",
        "entity_id": "flow_123",
        "occurred_at": datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
        "payload_json": {"type": "flow_alert", "data": {"ticker": "SPY", "premium": 1_500_000}},
    }
    ev = SensoryEvent.from_uw_source_event(flow_payload, data_quality="live")
    assert ev.source == "unusual_whales"
    assert ev.event_type == "options_flow"
    assert ev.symbols == ["SPY"]
    assert "options_flow" in ev.tags
    assert ev.normalized.get("premium") == 1_500_000

    congress_payload = {
        "topic": "unusual_whales.congress",
        "source": "unusual_whales",
        "symbol": "AAPL",
        "payload_json": {"type": "congress_trade", "data": {}},
    }
    ev2 = SensoryEvent.from_uw_source_event(congress_payload)
    assert ev2.event_type == "filing"
    assert "congress" in ev2.tags

    dp_payload = {"topic": "unusual_whales.darkpool", "source": "unusual_whales", "symbol": "QQQ", "payload_json": {}}
    ev3 = SensoryEvent.from_uw_source_event(dp_payload)
    assert ev3.event_type == "dark_pool"
    assert "dark_pool" in ev3.tags


@pytest.mark.asyncio
async def test_router_routes_uw_to_swarm_idea():
    bus = DummyBus()
    router = SensoryRouter(bus)
    ev = SensoryEvent(
        source="unusual_whales",
        event_type="options_flow",
        symbols=["SPY"],
        raw={"type": "flow_alert", "data": {"premium": 100000}},
        normalized={"premium": 100000, "payload_type": "flow_alert"},
        tags=["options_flow", "unusual_whales"],
        data_quality="live",
    )
    await router.route_and_publish(ev)
    topics = [t for (t, _) in bus.published]
    assert "swarm.idea" in topics
    assert "ingest.raw" in topics
    idea = next(p for (t, p) in bus.published if t == "swarm.idea")
    assert "firehose:unusual_whales" in idea.get("source", "")
    assert "SPY" in idea.get("symbols", [])


@pytest.mark.asyncio
async def test_sensory_event_from_finviz_source_event():
    """Finviz SourceEvent / screener row becomes SensoryEvent."""
    payload = {
        "topic": "finviz.screener",
        "source": "finviz",
        "source_kind": "screener",
        "symbol": "AAPL",
        "payload_json": {"Ticker": "AAPL", "Price": "175.50", "Market Cap": "2.7T", "Change": "1.2%"},
    }
    ev = SensoryEvent.from_finviz_source_event(payload, data_quality="live")
    assert ev.source == "finviz"
    assert ev.event_type == "screener_hit"
    assert ev.symbols == ["AAPL"]
    assert "finviz" in ev.tags
    assert ev.normalized.get("price") in ("175.50", 175.5)


@pytest.mark.asyncio
async def test_router_routes_finviz_to_swarm_idea():
    bus = DummyBus()
    router = SensoryRouter(bus)
    ev = SensoryEvent(
        source="finviz",
        event_type="screener_hit",
        symbols=["MSFT"],
        raw={"Price": "400", "Change": "0.5%"},
        normalized={"price": "400", "change_pct": "0.5%"},
        tags=["screener", "finviz"],
        data_quality="live",
    )
    await router.route_and_publish(ev)
    topics = [t for (t, _) in bus.published]
    assert "swarm.idea" in topics
    assert "ingest.raw" in topics
    idea = next(p for (t, p) in bus.published if t == "swarm.idea")
    assert "firehose:finviz" in idea.get("source", "")
    assert "MSFT" in idea.get("symbols", [])


@pytest.mark.asyncio
async def test_sensory_event_from_news_item():
    """News item becomes SensoryEvent with headline, sentiment, urgency."""
    ev = SensoryEvent.from_news_item(
        headline="Fed signals rate cut in September",
        source="reuters_markets",
        symbols=["SPY", "TLT"],
        sentiment="bullish",
        urgency="breaking",
        sentiment_score=0.6,
        data_quality="live",
    )
    assert ev.source == "news"
    assert ev.event_type == "news"
    assert ev.symbols == ["SPY", "TLT"]
    assert "news" in ev.tags
    assert "breaking" in ev.tags
    assert ev.normalized.get("headline", "").startswith("Fed signals")


@pytest.mark.asyncio
async def test_router_routes_news_to_swarm_idea():
    bus = DummyBus()
    router = SensoryRouter(bus)
    ev = SensoryEvent(
        source="news",
        event_type="news",
        symbols=["AAPL"],
        normalized={"headline": "Apple beats earnings", "news_source": "cnbc_top", "urgency": "breaking", "sentiment": "bullish"},
        tags=["news", "breaking", "bullish"],
        data_quality="live",
    )
    await router.route_and_publish(ev)
    topics = [t for (t, _) in bus.published]
    assert "swarm.idea" in topics
    assert "ingest.raw" in topics
    idea = next(p for (t, p) in bus.published if t == "swarm.idea")
    assert "firehose:news" in idea.get("source", "")
    assert "AAPL" in idea.get("symbols", [])


@pytest.mark.asyncio
async def test_router_routes_bar_to_market_and_swarm_on_anomaly():
    bus = DummyBus()
    router = SensoryRouter(bus)
    bar = {
        "symbol": "SPY",
        "timestamp": datetime(2026, 3, 10, tzinfo=timezone.utc).isoformat(),
        "open": 100,
        "high": 120,
        "low": 95,
        "close": 118,
        "volume": 2_000_000,
        "source": "alpaca_websocket",
    }
    ev = SensoryEvent.from_alpaca_bar(bar, data_quality="live")
    await router.route_and_publish(ev)

    topics = [t for (t, _) in bus.published]
    assert "market_data.bar" in topics
    assert "ingest.raw" in topics
    assert "swarm.idea" in topics


@pytest.mark.asyncio
async def test_base_channel_agent_retry_and_dlq_on_failure():
    from app.services.channels.base_channel_agent import RetryPolicy

    bus = DummyBus()

    class FailingRouter:
        async def route_and_publish(self, ev: SensoryEvent) -> None:
            raise RuntimeError("boom")

    agent = BaseChannelAgent(
        name="test_agent",
        router=FailingRouter(),
        message_bus=bus,
        max_queue_size=10,
        retry=RetryPolicy(max_retries=0, base_delay_s=0.05),
    )
    await agent.start()

    ev = SensoryEvent(
        source="alpaca",
        event_type="bar",
        symbols=["AAPL"],
        raw={"symbol": "AAPL"},
        normalized={"symbol": "AAPL", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},
        data_quality="live",
    )

    await agent.enqueue(ev)

    await asyncio.sleep(0.8)
    await agent.stop()

    topics = [t for (t, _) in bus.published]
    assert "ingest.dlq" in topics
    status = agent.get_status()
    assert status["metrics"]["events_dlq"] >= 1


@pytest.mark.asyncio
async def test_dlq_flow_channel_agent_failure_reaches_ingest_dlq():
    """Verify failed channel agent events reach ingest.dlq with correct payload shape."""
    from app.services.channels.base_channel_agent import RetryPolicy

    bus = DummyBus()

    class FailingRouter:
        async def route_and_publish(self, ev: SensoryEvent) -> None:
            raise ValueError("publish_failed")

    agent = BaseChannelAgent(
        name="dlq_test_agent",
        router=FailingRouter(),
        message_bus=bus,
        max_queue_size=10,
        batch_size=1,
        retry=RetryPolicy(max_retries=0, base_delay_s=0.01),
    )
    await agent.start()

    ev = SensoryEvent(
        source="unusual_whales",
        event_type="options_flow",
        symbols=["SPY"],
        raw={"premium": 100000},
        normalized={"premium": 100000},
        data_quality="live",
    )
    await agent.enqueue(ev)
    await asyncio.sleep(0.5)
    await agent.stop()

    dlq_publishes = [(t, d) for (t, d) in bus.published if t == "ingest.dlq"]
    assert len(dlq_publishes) >= 1
    topic, payload = dlq_publishes[0]
    assert topic == "ingest.dlq"
    assert payload.get("agent") == "dlq_test_agent"
    assert "error" in payload
    assert "publish_failed" in payload["error"] or "publish_failed" in str(payload.get("error", ""))
    assert "event" in payload
    assert payload["event"].get("source") == "unusual_whales"
    assert payload["event"].get("event_type") == "options_flow"
    assert "ts" in payload
    assert agent.get_status()["metrics"]["events_dlq"] >= 1


@pytest.mark.asyncio
async def test_firehose_circuit_breaker_five_failures_then_reset():
    """Five consecutive failures open circuit; after reset_timeout agent processes again."""
    publish_count = 0

    class FailingThenSucceedBus:
        def __init__(self):
            self.published: list = []

        async def publish(self, topic: str, data: Dict[str, Any]) -> None:
            nonlocal publish_count
            publish_count += 1
            if publish_count <= 5:
                raise RuntimeError("simulated failure")
            self.published.append((topic, data))

    bus = FailingThenSucceedBus()

    class TestFirehoseAgent(BaseFirehoseAgent):
        agent_id = "test_circuit_agent"
        circuit_failures = 5
        circuit_reset_sec = 0.6  # long enough to assert circuit open

        async def fetch(self):
            return []

    agent = TestFirehoseAgent(bus)
    await agent.start()

    for _ in range(6):
        ev = FirehoseSensoryEvent(
            source=SensorySource.UNUSUAL_WHALES,
            symbols=["SPY"],
            topic_hint="swarm.idea",
            payload={"reasoning": "test"},
        )
        agent.enqueue(ev)

    for _ in range(30):
        await asyncio.sleep(0.05)
        status = agent.get_status()
        if status["failures"] >= 5:
            assert status["circuit_open"] is True, "Circuit should open after 5 failures"
            break
    else:
        pytest.fail("Expected 5 failures to trigger circuit open")

    await asyncio.sleep(2.0)
    await agent.stop()

    assert len(bus.published) >= 1, "After reset window, 6th event should be published"
    assert any(t == "swarm.idea" for t, _ in bus.published)


@pytest.mark.asyncio
async def test_backpressure_message_bus_queue_full_event_to_dlq():
    """When MessageBus queue is full, publish puts event in DLQ (queue_full)."""
    from app.core.message_bus import MessageBus

    bus = MessageBus(max_queue_size=2)
    slow_done = asyncio.Event()

    async def slow_handler(_):
        await asyncio.sleep(0.5)
        slow_done.set()

    await bus.subscribe("ingest.health", slow_handler)
    await bus.start()

    try:
        for i in range(4):
            await bus.publish("ingest.health", {"agent": f"a{i}", "ts": "2026-01-01T00:00:00Z"})
        await asyncio.sleep(0.2)

        dlq = bus.get_dlq_sync(limit=20)
        queue_full_dlq = [e for e in dlq if e.get("reason") == "queue_full"]
        assert len(queue_full_dlq) >= 1, "Event should land in DLQ when queue is full"
    finally:
        await slow_done.wait()
        await bus.stop()


@pytest.mark.asyncio
async def test_ingestion_status_and_metrics_endpoints(client):
    r1 = await client.get("/api/v1/ingestion/status")
    assert r1.status_code in (200, 503), f"status returned {r1.status_code}"

    r2 = await client.get("/api/v1/ingestion/metrics")
    assert r2.status_code in (200, 503), f"metrics returned {r2.status_code}"

    if r1.status_code == 200:
        data = r1.json()
        assert "running" in data or "agents" in data
        if data.get("agents"):
            assert "uw_firehose" in data["agents"]
            assert "finviz_firehose" in data["agents"]
            assert "news_firehose" in data["agents"]


@pytest.mark.asyncio
async def test_awareness_enrich_endpoint(client, auth_headers):
    """POST /awareness/enrich accepts events and returns stub-enriched list."""
    r = await client.post(
        "/api/v1/awareness/enrich",
        json={"events": [{"event_id": "e1", "source": "discord", "event_type": "social_post", "symbols": ["SPY"]}]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "enriched" in data
    assert len(data["enriched"]) == 1
    assert data["enriched"][0].get("embedding_ref") == "stub"
    assert data["enriched"][0].get("novelty_score") == 0.5
    assert "awareness_stub" in data["enriched"][0].get("tags", [])
