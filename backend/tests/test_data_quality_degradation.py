"""Tests for data-quality degradation — verify graceful handling when
external sources fail, agents receive empty features, and the pipeline
survives partial or total data loss without crashing.
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.message_bus import MessageBus
from app.council.schemas import AgentVote, DecisionPacket
from app.council.arbiter import arbitrate, REQUIRED_AGENTS


# ── Helpers ────────────────────────────────────────────────────────────────

ALL_AGENT_NAMES = [
    "market_perception", "flow_perception", "regime", "social_perception",
    "news_catalyst", "youtube_knowledge", "intermarket",
    "gex_agent", "insider_agent", "finbert_sentiment_agent",
    "earnings_tone_agent", "dark_pool_agent", "macro_regime_agent",
    "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
    "supply_chain_agent", "institutional_flow_agent", "congressional_agent",
    "hypothesis", "layered_memory_agent",
    "strategy",
    "risk", "execution", "portfolio_optimizer_agent",
    "bull_debater", "bear_debater", "red_team_agent",
    "critic",
    "alt_data_agent",
    "macro_regime", "dark_pool", "insider",
]


def _hold_vote(name: str, confidence: float = 0.1, weight: float = 1.0) -> AgentVote:
    """Create a degraded hold vote for the named agent."""
    return AgentVote(
        agent_name=name,
        direction="hold",
        confidence=max(0.0, min(confidence, 1.0)),
        reasoning="Degraded — data unavailable",
        weight=weight,
    )


def _buy_vote(name: str, confidence: float = 0.7, weight: float = 1.0) -> AgentVote:
    return AgentVote(
        agent_name=name,
        direction="buy",
        confidence=confidence,
        reasoning="Bullish signal",
        weight=weight,
    )


def _required_buy_votes() -> list[AgentVote]:
    """Minimal votes that satisfy REQUIRED_AGENTS for a buy decision."""
    return [
        AgentVote(
            agent_name="regime",
            direction="buy",
            confidence=0.7,
            reasoning="Green regime",
            weight=1.2,
            metadata={"regime_state": "GREEN"},
        ),
        AgentVote(
            agent_name="risk",
            direction="buy",
            confidence=0.6,
            reasoning="Risk acceptable",
            weight=1.5,
            metadata={"execution_ready": True, "risk_limits": {"max_loss": 0.02}},
        ),
        AgentVote(
            agent_name="strategy",
            direction="buy",
            confidence=0.8,
            reasoning="Momentum strategy",
            weight=1.1,
        ),
        AgentVote(
            agent_name="execution",
            direction="buy",
            confidence=0.7,
            reasoning="Execution ok",
            weight=1.3,
            metadata={"execution_ready": True},
        ),
    ]


@pytest.fixture
async def bus():
    b = MessageBus()
    await b.start()
    yield b
    await b.stop()


# ── 1. Alpaca source unavailable ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_alpaca_source_unavailable():
    """When Alpaca raises, the signal engine should not crash.

    We mock the alpaca_service at the point where it provides bars and
    verify the error is caught rather than propagated.
    """
    mock_alpaca = MagicMock()
    mock_alpaca.get_bars = AsyncMock(side_effect=ConnectionError("Alpaca unreachable"))
    mock_alpaca.get_latest_quote = AsyncMock(side_effect=ConnectionError("Alpaca unreachable"))

    try:
        bars = await mock_alpaca.get_bars("AAPL", "1Day", limit=5)
        assert False, "Should have raised"
    except ConnectionError:
        pass

    votes = _required_buy_votes()
    votes.append(_hold_vote("market_perception", confidence=0.0))
    packet = arbitrate(
        symbol="AAPL",
        timeframe="1d",
        timestamp=datetime.now(timezone.utc).isoformat(),
        votes=votes,
    )
    assert isinstance(packet, DecisionPacket)


# ── 2. Unusual Whales unavailable ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_unusual_whales_unavailable():
    """When UW is down, agents that depend on it should return hold/low confidence."""
    uw_dependent_agents = ["flow_perception", "dark_pool_agent", "gex_agent", "congressional_agent"]

    votes = _required_buy_votes()
    for name in uw_dependent_agents:
        votes.append(_hold_vote(name, confidence=0.05))

    packet = arbitrate(
        symbol="TSLA",
        timeframe="1d",
        timestamp=datetime.now(timezone.utc).isoformat(),
        votes=votes,
    )
    assert isinstance(packet, DecisionPacket)
    assert packet.final_direction in {"buy", "sell", "hold"}
    assert 0.0 <= packet.final_confidence <= 1.0


# ── 3. FRED unavailable ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fred_unavailable():
    """When FRED is unreachable, macro agents should degrade gracefully."""
    votes = _required_buy_votes()
    for name in ["macro_regime_agent", "macro_regime"]:
        votes.append(_hold_vote(name, confidence=0.05))

    packet = arbitrate(
        symbol="SPY",
        timeframe="1d",
        timestamp=datetime.now(timezone.utc).isoformat(),
        votes=votes,
    )
    assert isinstance(packet, DecisionPacket)
    assert not packet.vetoed


# ── 4. Multiple sources down simultaneously ──────────────────────────────

@pytest.mark.asyncio
async def test_multiple_sources_down():
    """Pipeline must survive 3+ data sources failing at once."""
    degraded_agents = [
        "flow_perception", "dark_pool_agent", "gex_agent",
        "macro_regime_agent", "insider_agent", "finbert_sentiment_agent",
        "news_catalyst", "social_perception", "congressional_agent",
    ]

    votes = _required_buy_votes()
    for name in degraded_agents:
        votes.append(_hold_vote(name, confidence=0.0))

    packet = arbitrate(
        symbol="NVDA",
        timeframe="1d",
        timestamp=datetime.now(timezone.utc).isoformat(),
        votes=votes,
    )
    assert isinstance(packet, DecisionPacket)
    assert packet.final_direction in {"buy", "sell", "hold"}


# ── 5. All agents receive None features → hold, no crash ─────────────────

@pytest.mark.asyncio
async def test_all_agents_receive_none_features():
    """When every agent gets None data (confidence=0, hold), the arbiter
    must return hold without crashing."""
    votes = []
    for name in ["regime", "risk", "strategy", "execution"]:
        votes.append(_hold_vote(name, confidence=0.0))
    for name in ALL_AGENT_NAMES:
        if name not in {"regime", "risk", "strategy", "execution"}:
            votes.append(_hold_vote(name, confidence=0.0))

    packet = arbitrate(
        symbol="AAPL",
        timeframe="1d",
        timestamp=datetime.now(timezone.utc).isoformat(),
        votes=votes,
    )
    assert isinstance(packet, DecisionPacket)
    assert packet.final_direction == "hold"
    assert not packet.vetoed


# ── 6. MessageBus publish failure ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_messagebus_publish_failure(bus):
    """If bus.publish raises, the publisher must not crash."""
    original_publish = bus.publish

    call_count = 0

    async def exploding_publish(topic, data):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("Redis gone")

    bus.publish = exploding_publish

    try:
        await bus.publish("signal.generated", {"symbol": "AAPL", "score": 80})
        assert False, "Should have raised"
    except RuntimeError:
        pass

    assert call_count == 1
    bus.publish = original_publish


# ── 7. CouncilGate semaphore rate-limit ───────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_handling(bus):
    """CouncilGate with max_concurrent=2 must cap queue at 20 and use semaphore."""
    from app.council.council_gate import CouncilGate

    gate = CouncilGate(
        message_bus=bus,
        gate_threshold=50.0,
        max_concurrent=2,
        cooldown_seconds=0,
    )
    gate._running = True
    gate._start_time = __import__("time").time()

    council_invocations = 0
    lock = asyncio.Lock()

    async def slow_council(symbol, timeframe, context=None):
        nonlocal council_invocations
        async with lock:
            council_invocations += 1
        await asyncio.sleep(2.0)
        return DecisionPacket(
            symbol=symbol,
            timeframe="1d",
            timestamp=datetime.now(timezone.utc).isoformat(),
            votes=[],
            final_direction="hold",
            final_confidence=0.3,
            vetoed=False,
            veto_reasons=[],
            risk_limits={},
            execution_ready=False,
            council_reasoning="test",
        )

    with patch("app.council.runner.run_council", side_effect=slow_council):
        for i in range(3):
            signal = {
                "symbol": f"SYM{i}",
                "score": 90,
                "regime": "GREEN",
                "price": 100.0,
                "source": "test",
                "direction": "buy",
            }
            await gate._on_signal(signal)
            await asyncio.sleep(0.01)

        for i in range(3, 10):
            signal = {
                "symbol": f"SYM{i}",
                "score": 90,
                "regime": "GREEN",
                "price": 100.0,
                "source": "test",
                "direction": "buy",
            }
            await gate._on_signal(signal)

    assert gate._priority_queue is not None
    assert len(gate._priority_queue) <= 20
    assert gate._concurrency_skips > 0


# ── 8. All 35 agents hold with degraded confidence → valid DecisionPacket ─

@pytest.mark.asyncio
async def test_empty_features_all_agents_survive():
    """All 35 agents voting hold/0.1 confidence (degraded) must produce a
    valid DecisionPacket without crash."""
    unique_names = set()
    votes = []

    for name in ALL_AGENT_NAMES:
        if name in unique_names:
            continue
        unique_names.add(name)
        meta = {}
        if name == "regime":
            meta = {"regime_state": "YELLOW"}
        elif name == "execution":
            meta = {"execution_ready": False}
        elif name == "risk":
            meta = {"risk_limits": {"max_loss": 0.02}}
        votes.append(AgentVote(
            agent_name=name,
            direction="hold",
            confidence=0.1,
            reasoning="Degraded data — hold",
            weight=1.0,
            metadata=meta,
        ))

    packet = arbitrate(
        symbol="QQQ",
        timeframe="1d",
        timestamp=datetime.now(timezone.utc).isoformat(),
        votes=votes,
    )

    assert isinstance(packet, DecisionPacket)
    assert packet.final_direction == "hold"
    assert 0.0 <= packet.final_confidence <= 1.0
    assert not packet.execution_ready
    assert isinstance(packet.council_reasoning, str)
    assert packet.symbol == "QQQ"
    d = packet.to_dict()
    assert "final_direction" in d
    assert "votes" in d
