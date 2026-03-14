"""E2E full pipeline tests: signal -> CouncilGate -> council -> OrderExecutor -> order.

8 tests covering the complete trading pipeline with real MessageBus,
mocked council and external APIs.
"""
import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.message_bus import MessageBus
from app.council.council_gate import CouncilGate
from app.council.schemas import AgentVote, DecisionPacket
from app.services.order_executor import OrderExecutor


@pytest.fixture(autouse=True)
def _mock_kill_switch():
    """Prevent kill-switch / entries-frozen from blocking test trades."""
    with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
        yield


def _make_decision_packet(
    symbol: str = "AAPL",
    direction: str = "buy",
    confidence: float = 0.85,
    vetoed: bool = False,
    veto_reasons: list = None,
    execution_ready: bool = True,
    timestamp: str = None,
) -> DecisionPacket:
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    votes = [
        AgentVote(
            agent_name="regime", direction=direction if direction != "hold" else "hold",
            confidence=0.8, reasoning="test regime", weight=1.2,
            metadata={"regime_state": "BULLISH"},
        ),
        AgentVote(
            agent_name="risk", direction=direction if direction != "hold" else "hold",
            confidence=0.7, reasoning="test risk", weight=1.5,
            metadata={"risk_limits": {"max_position_pct": 0.05}},
        ),
        AgentVote(
            agent_name="strategy", direction=direction if direction != "hold" else "hold",
            confidence=0.75, reasoning="test strategy", weight=1.1,
        ),
        AgentVote(
            agent_name="execution", direction=direction if direction != "hold" else "hold",
            confidence=0.7, reasoning="test execution", weight=1.3,
            metadata={"execution_ready": True},
        ),
        AgentVote(
            agent_name="market_perception", direction=direction if direction != "hold" else "hold",
            confidence=0.8, reasoning="test perception", weight=1.0,
        ),
    ]
    return DecisionPacket(
        symbol=symbol,
        timeframe="1d",
        timestamp=timestamp,
        votes=votes,
        final_direction="hold" if vetoed else direction,
        final_confidence=0.0 if vetoed else confidence,
        vetoed=vetoed,
        veto_reasons=veto_reasons or [],
        risk_limits={"max_position_pct": 0.05},
        execution_ready=(not vetoed) and execution_ready and direction != "hold",
        council_reasoning=f"Test decision: {direction}",
        council_decision_id=f"test-{symbol}-{int(time.time() * 1000)}",
    )


def _make_signal(
    symbol: str = "AAPL",
    score: float = 80,
    regime: str = "GREEN",
    price: float = 150.0,
    direction: str = "buy",
) -> dict:
    return {
        "symbol": symbol,
        "score": score,
        "regime": regime,
        "price": price,
        "close": price,
        "direction": direction,
        "source": "test_engine",
        "volume": 50_000_000,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _stub_kelly(symbol, score, regime, price, direction="buy"):
    return {
        "action": "TRADE",
        "kelly_pct": 0.05,
        "qty": 10,
        "edge": 0.1,
        "stats_source": "test",
        "stop_loss": price * 0.98,
        "take_profit": price * 1.05,
        "raw_kelly": 0.05,
        "win_rate": 0.55,
        "trade_count": 50,
    }


def _patch_executor_gates(executor):
    """Stub all external gates so the executor processes verdicts in tests."""
    executor._compute_kelly_size = _stub_kelly

    async def _drawdown_ok():
        return True
    executor._check_drawdown = _drawdown_ok

    mock_alpaca = MagicMock()
    mock_alpaca.get_account = AsyncMock(return_value={
        "equity": "100000", "last_equity": "100000",
    })
    mock_alpaca.get_positions = AsyncMock(return_value=[])
    mock_alpaca.create_order = AsyncMock(return_value={"id": "order-test"})
    executor._alpaca_svc = mock_alpaca
    executor._recent_verdict_hashes = {}


@pytest.mark.asyncio
async def test_buy_pipeline_signal_to_order():
    """Publish signal(score=80, regime=GREEN, BUY) -> council BUY -> order.submitted."""
    verdicts = []
    orders_submitted = []

    bus = MessageBus()
    await bus.start()

    async def on_verdict(data):
        verdicts.append(data)

    async def on_order(data):
        orders_submitted.append(data)

    await bus.subscribe("council.verdict", on_verdict)
    await bus.subscribe("order.submitted", on_order)

    decision = _make_decision_packet(symbol="AAPL", direction="buy", confidence=0.85)

    async def mock_run_council(symbol=None, timeframe=None, context=None, **kw):
        return decision

    with patch("app.council.runner.run_council", side_effect=mock_run_council):
        gate = CouncilGate(
            message_bus=bus, gate_threshold=0.0,
            max_concurrent=5, cooldown_seconds=0,
        )
        await gate.start()

        executor = OrderExecutor(
            message_bus=bus, auto_execute=False,
            min_score=0, max_daily_trades=100, cooldown_seconds=0,
        )
        _patch_executor_gates(executor)
        await executor.start()

        await bus.publish("signal.generated", _make_signal(
            symbol="AAPL", score=80, regime="GREEN", price=150.0, direction="buy",
        ))

        for _ in range(80):
            await asyncio.sleep(0.05)
            if orders_submitted:
                break

        await executor.stop()
        await gate.stop()

    await bus.stop()

    assert len(verdicts) >= 1, "CouncilGate should publish council.verdict"
    assert verdicts[0]["final_direction"] == "buy"
    assert len(orders_submitted) >= 1, "OrderExecutor should publish order.submitted"
    assert orders_submitted[0]["symbol"] == "AAPL"
    assert orders_submitted[0].get("side") == "buy"


@pytest.mark.asyncio
async def test_sell_pipeline():
    """Signal with direction=sell -> council SELL -> order side=sell."""
    orders_submitted = []

    bus = MessageBus()
    await bus.start()

    async def on_order(data):
        orders_submitted.append(data)

    await bus.subscribe("order.submitted", on_order)

    decision = _make_decision_packet(symbol="TSLA", direction="sell", confidence=0.80)

    async def mock_run_council(symbol=None, timeframe=None, context=None, **kw):
        return decision

    with patch("app.council.runner.run_council", side_effect=mock_run_council):
        gate = CouncilGate(
            message_bus=bus, gate_threshold=0.0,
            max_concurrent=5, cooldown_seconds=0,
        )
        await gate.start()

        executor = OrderExecutor(
            message_bus=bus, auto_execute=False,
            min_score=0, max_daily_trades=100, cooldown_seconds=0,
        )
        _patch_executor_gates(executor)
        await executor.start()

        await bus.publish("signal.generated", _make_signal(
            symbol="TSLA", score=80, regime="GREEN", price=200.0, direction="sell",
        ))

        for _ in range(80):
            await asyncio.sleep(0.05)
            if orders_submitted:
                break

        await executor.stop()
        await gate.stop()

    await bus.stop()

    assert len(orders_submitted) >= 1, "OrderExecutor should publish order.submitted for SELL"
    assert orders_submitted[0]["side"] == "sell"
    assert orders_submitted[0]["symbol"] == "TSLA"


@pytest.mark.asyncio
async def test_hold_pipeline_no_order():
    """Council returns HOLD -> gate does not publish verdict -> no order.submitted."""
    verdicts = []
    orders_submitted = []

    bus = MessageBus()
    await bus.start()

    async def on_verdict(data):
        verdicts.append(data)

    async def on_order(data):
        orders_submitted.append(data)

    await bus.subscribe("council.verdict", on_verdict)
    await bus.subscribe("order.submitted", on_order)

    hold_decision = _make_decision_packet(
        symbol="MSFT", direction="hold", confidence=0.4, execution_ready=False,
    )

    async def mock_run_council(symbol=None, timeframe=None, context=None, **kw):
        return hold_decision

    with patch("app.council.runner.run_council", side_effect=mock_run_council):
        gate = CouncilGate(
            message_bus=bus, gate_threshold=0.0,
            max_concurrent=5, cooldown_seconds=0,
        )
        await gate.start()

        executor = OrderExecutor(
            message_bus=bus, auto_execute=False,
            min_score=0, max_daily_trades=100, cooldown_seconds=0,
        )
        _patch_executor_gates(executor)
        await executor.start()

        await bus.publish("signal.generated", _make_signal(
            symbol="MSFT", score=80, regime="GREEN", price=300.0, direction="buy",
        ))

        await asyncio.sleep(1.0)

        await executor.stop()
        await gate.stop()

    await bus.stop()

    assert len(verdicts) == 0, "HOLD verdict must not be published by gate"
    assert len(orders_submitted) == 0, "HOLD must not produce order.submitted"
    assert gate._councils_held >= 1, "Gate should track held decisions"


@pytest.mark.asyncio
async def test_veto_blocks_trade():
    """VETO by risk agent -> no order. Non-VETO agent veto is ignored by arbiter."""
    from app.council.arbiter import VETO_AGENTS, arbitrate

    orders_submitted = []

    bus = MessageBus()
    await bus.start()

    async def on_order(data):
        orders_submitted.append(data)

    await bus.subscribe("order.submitted", on_order)

    vetoed_decision = _make_decision_packet(
        symbol="NVDA", direction="buy", vetoed=True,
        veto_reasons=["risk: excessive drawdown"],
    )

    async def mock_run_council(symbol=None, timeframe=None, context=None, **kw):
        return vetoed_decision

    with patch("app.council.runner.run_council", side_effect=mock_run_council):
        gate = CouncilGate(
            message_bus=bus, gate_threshold=0.0,
            max_concurrent=5, cooldown_seconds=0,
        )
        await gate.start()

        executor = OrderExecutor(
            message_bus=bus, auto_execute=False,
            min_score=0, max_daily_trades=100, cooldown_seconds=0,
        )
        _patch_executor_gates(executor)
        await executor.start()

        await bus.publish("signal.generated", _make_signal(
            symbol="NVDA", score=80, regime="GREEN", price=500.0,
        ))

        await asyncio.sleep(1.0)

        await executor.stop()
        await gate.stop()

    await bus.stop()

    assert len(orders_submitted) == 0, "Vetoed decision must not produce order"
    assert gate._councils_vetoed >= 1

    # Verify arbiter: non-VETO agent (critic) cannot veto
    ts = datetime.now(timezone.utc).isoformat()
    votes = [
        AgentVote(agent_name="regime", direction="buy", confidence=0.8,
                  reasoning="ok", weight=1.2, metadata={"regime_state": "BULLISH"}),
        AgentVote(agent_name="risk", direction="buy", confidence=0.7,
                  reasoning="ok", weight=1.5),
        AgentVote(agent_name="strategy", direction="buy", confidence=0.75,
                  reasoning="ok", weight=1.1),
        AgentVote(agent_name="execution", direction="buy", confidence=0.7,
                  reasoning="ok", weight=1.3, metadata={"execution_ready": True}),
        AgentVote(agent_name="critic", direction="buy", confidence=0.6,
                  reasoning="ok", weight=0.5,
                  veto=True, veto_reason="critic disagrees"),
    ]
    result = arbitrate("TEST", "1d", ts, votes)
    assert result.vetoed is False, "Non-VETO agent (critic) cannot veto"
    assert "critic" not in VETO_AGENTS


@pytest.mark.asyncio
async def test_decision_expiry_30s():
    """Verdict timestamp 60s in past -> OrderExecutor rejects as stale (TTL 30s)."""
    orders_submitted = []

    bus = MessageBus()
    await bus.start()

    async def on_order(data):
        orders_submitted.append(data)

    await bus.subscribe("order.submitted", on_order)

    executor = OrderExecutor(
        message_bus=bus, auto_execute=False,
        min_score=0, max_daily_trades=100, cooldown_seconds=0,
    )
    _patch_executor_gates(executor)
    await executor.start()

    stale_ts = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    stale_verdict = {
        "symbol": "AMZN",
        "final_direction": "buy",
        "final_confidence": 0.9,
        "execution_ready": True,
        "vetoed": False,
        "veto_reasons": [],
        "votes": [],
        "council_reasoning": "test stale verdict",
        "timestamp": stale_ts,
        "price": 180.0,
        "signal_data": {
            "score": 80, "regime": "GREEN", "price": 180.0, "source": "test",
        },
    }

    await bus.publish("council.verdict", stale_verdict)

    for _ in range(40):
        await asyncio.sleep(0.05)
        if executor._signals_rejected >= 1:
            break

    await executor.stop()
    await bus.stop()

    assert len(orders_submitted) == 0, "Stale verdict (60s old) must be rejected"
    assert executor._signals_rejected >= 1, "Executor should count the rejection"


@pytest.mark.asyncio
async def test_concurrent_signals_semaphore():
    """3 signals with max_concurrent=2 -> third is queued, eventually processed."""
    councils_called = []

    bus = MessageBus()
    await bus.start()

    async def slow_council(symbol=None, timeframe=None, context=None, **kw):
        councils_called.append(symbol)
        await asyncio.sleep(0.3)
        return _make_decision_packet(symbol=symbol or "TEST", direction="buy")

    with patch("app.council.runner.run_council", side_effect=slow_council):
        gate = CouncilGate(
            message_bus=bus, gate_threshold=0.0,
            max_concurrent=2, cooldown_seconds=0,
        )
        await gate.start()

        for sym in ["SIG_A", "SIG_B", "SIG_C"]:
            await bus.publish("signal.generated", _make_signal(
                symbol=sym, score=90, regime="GREEN", price=100.0,
            ))
            await asyncio.sleep(0.02)

        for _ in range(120):
            await asyncio.sleep(0.05)
            if gate._councils_invoked >= 2 and (
                gate._concurrency_skips >= 1 or gate._queue_dispatched >= 1
            ):
                break

        # Allow queue drain cycle (2s interval)
        for _ in range(60):
            await asyncio.sleep(0.1)
            if gate._councils_invoked >= 3 or gate._queue_dispatched >= 1:
                break

        await gate.stop()

    await bus.stop()

    assert gate._signals_received >= 3, "All 3 signals should be received"
    assert gate._councils_invoked >= 2, "At least 2 councils should run immediately"
    total_handled = gate._councils_invoked + gate._concurrency_skips
    assert total_handled >= 3, (
        f"All 3 signals accounted for: invoked={gate._councils_invoked}, "
        f"skipped/queued={gate._concurrency_skips}"
    )


@pytest.mark.asyncio
async def test_signal_below_threshold_no_council():
    """score=50 below GREEN threshold (55) -> council never invoked."""
    bus = MessageBus()
    await bus.start()

    async def should_not_be_called(symbol=None, **kw):
        raise AssertionError("Council should not be invoked for sub-threshold signal")

    with patch("app.council.runner.run_council", side_effect=should_not_be_called):
        gate = CouncilGate(
            message_bus=bus, gate_threshold=55.0,
            max_concurrent=5, cooldown_seconds=0,
        )
        await gate.start()

        await bus.publish("signal.generated", _make_signal(
            symbol="LOW", score=50, regime="GREEN", price=100.0,
        ))

        await asyncio.sleep(0.5)

        await gate.stop()

    await bus.stop()

    assert gate._councils_invoked == 0, "Sub-threshold signal must not invoke council"
    assert gate._signals_received >= 1, "Signal should still be counted as received"


@pytest.mark.asyncio
async def test_pipeline_latency_under_5s():
    """Measure time from signal.generated to council.verdict, assert < 5s."""
    verdicts = []

    bus = MessageBus()
    await bus.start()

    async def on_verdict(data):
        verdicts.append({"data": data, "received_at": time.monotonic()})

    await bus.subscribe("council.verdict", on_verdict)

    async def fast_council(symbol=None, timeframe=None, context=None, **kw):
        return _make_decision_packet(symbol=symbol or "FAST", direction="buy")

    with patch("app.council.runner.run_council", side_effect=fast_council):
        gate = CouncilGate(
            message_bus=bus, gate_threshold=0.0,
            max_concurrent=5, cooldown_seconds=0,
        )
        await gate.start()

        t_start = time.monotonic()
        await bus.publish("signal.generated", _make_signal(
            symbol="FAST", score=90, regime="GREEN", price=100.0,
        ))

        for _ in range(80):
            await asyncio.sleep(0.05)
            if verdicts:
                break

        await gate.stop()

    await bus.stop()

    assert len(verdicts) >= 1, "Verdict should be published"
    elapsed = verdicts[0]["received_at"] - t_start
    assert elapsed < 5.0, f"Pipeline latency {elapsed:.2f}s exceeds 5s limit"
