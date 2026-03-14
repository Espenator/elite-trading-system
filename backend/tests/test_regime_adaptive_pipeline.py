"""Tests for regime-adaptive CouncilGate thresholds, cooldowns, and arbiter execution scaling.

Covers: GREEN/RED/CRISIS gate thresholds, regime transitions, Kelly/execution
threshold scaling by regime, per-direction cooldown variation, and unknown-regime
defaults.
"""
import asyncio
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from app.council.schemas import AgentVote, DecisionPacket


# ---------------------------------------------------------------------------
# Lightweight async MessageBus stub
# ---------------------------------------------------------------------------

class MockMessageBus:
    """Minimal MessageBus that dispatches synchronously for test control."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.published: List[Dict[str, Any]] = []

    async def subscribe(self, topic: str, handler: Callable) -> None:
        self._handlers[topic].append(handler)

    async def unsubscribe(self, topic: str, handler: Callable) -> None:
        handlers = self._handlers.get(topic, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        self.published.append({"topic": topic, "data": data})
        for handler in self._handlers.get(topic, []):
            await handler(data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_vote(name, direction="buy", confidence=0.7, **kwargs):
    meta = kwargs.pop("metadata", {})
    return AgentVote(
        agent_name=name,
        direction=direction,
        confidence=confidence,
        reasoning=f"{name} votes {direction}",
        metadata=meta,
        **kwargs,
    )


def _create_gate(bus: MockMessageBus, **overrides) -> "CouncilGate":
    from app.council.council_gate import CouncilGate
    defaults = dict(
        message_bus=bus,
        gate_threshold=65.0,
        max_concurrent=5,
        cooldown_seconds=120,
    )
    defaults.update(overrides)
    return CouncilGate(**defaults)


def _install_tracker(gate) -> List[str]:
    """Replace _evaluate_with_council with an async stub that records symbols.

    Also sets the per-symbol-direction cooldown timestamp (normally done
    inside the real _evaluate_with_council) so subsequent cooldown checks work.

    Returns the list that symbols are appended to.
    """
    council_calls: List[str] = []

    async def _fake_eval(symbol, signal_data):
        council_calls.append(symbol)
        direction = signal_data.get("direction", "buy")
        now = time.time()
        gate._symbol_last_eval[symbol] = now
        gate._symbol_direction_last_eval[f"{symbol}:{direction}"] = now

    gate._evaluate_with_council = _fake_eval
    return council_calls


# ---------------------------------------------------------------------------
# 1. GREEN regime threshold (55): score 60 passes, score 50 blocked
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gate_threshold_green_regime():
    """GREEN regime lowers threshold to 55: score 60 passes, score 50 is blocked."""
    bus = MockMessageBus()
    gate = _create_gate(bus)
    gate._current_regime = "GREEN"
    gate._running = True
    council_calls = _install_tracker(gate)

    await gate._on_signal({"symbol": "PASS", "score": 60, "direction": "buy"})
    await asyncio.sleep(0)
    await gate._on_signal({"symbol": "BLOCK", "score": 50, "direction": "buy"})
    await asyncio.sleep(0)

    assert "PASS" in council_calls, "Score 60 should pass GREEN threshold 55"
    assert "BLOCK" not in council_calls, "Score 50 should be blocked by GREEN threshold 55"


# ---------------------------------------------------------------------------
# 2. RED regime threshold (75): score 70 blocked, score 80 passes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gate_threshold_red_regime():
    """RED regime raises threshold to 75: score 70 blocked, score 80 passes."""
    bus = MockMessageBus()
    gate = _create_gate(bus)
    gate._current_regime = "RED"
    gate._running = True
    council_calls = _install_tracker(gate)

    await gate._on_signal({"symbol": "BLOCKED", "score": 70, "direction": "buy"})
    await asyncio.sleep(0)
    await gate._on_signal({"symbol": "PASSED", "score": 80, "direction": "buy"})
    await asyncio.sleep(0)

    assert "BLOCKED" not in council_calls, "Score 70 should be blocked by RED threshold 75"
    assert "PASSED" in council_calls, "Score 80 should pass RED threshold 75"


# ---------------------------------------------------------------------------
# 3. CRISIS regime threshold (75)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gate_threshold_crisis():
    """CRISIS regime uses threshold 75: score 74 blocked, score 76 passes."""
    bus = MockMessageBus()
    gate = _create_gate(bus)
    gate._current_regime = "CRISIS"
    gate._running = True
    council_calls = _install_tracker(gate)

    await gate._on_signal({"symbol": "LOW", "score": 74, "direction": "buy"})
    await asyncio.sleep(0)
    await gate._on_signal({"symbol": "HIGH", "score": 76, "direction": "buy"})
    await asyncio.sleep(0)

    assert "LOW" not in council_calls, "Score 74 should be blocked by CRISIS threshold 75"
    assert "HIGH" in council_calls, "Score 76 should pass CRISIS threshold 75"


# ---------------------------------------------------------------------------
# 4. Regime transition updates threshold
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_regime_transition_updates_threshold():
    """Sending a signal with regime=RED updates the gate's current regime and threshold."""
    bus = MockMessageBus()
    gate = _create_gate(bus)
    gate._current_regime = "GREEN"
    gate._running = True

    assert gate._get_regime_threshold() == 55.0, "Should start with GREEN threshold"

    council_calls = _install_tracker(gate)

    await gate._on_signal({
        "symbol": "REGIME_SHIFT", "score": 80, "regime": "RED", "direction": "buy",
    })
    await asyncio.sleep(0)

    assert gate._current_regime == "RED"
    assert gate._get_regime_threshold() == 75.0, "After RED signal, threshold should be 75"


# ---------------------------------------------------------------------------
# 5. Kelly/execution threshold scaling by regime (arbiter test)
# ---------------------------------------------------------------------------

def test_kelly_scaling_by_regime():
    """Arbiter execution threshold varies: BULLISH=0.30 passes conf~0.57, CRISIS=0.70 blocks it."""
    from app.council.arbiter import arbitrate, REGIME_EXECUTION_THRESHOLDS

    assert REGIME_EXECUTION_THRESHOLDS["BULLISH"] == 0.30
    assert REGIME_EXECUTION_THRESHOLDS["CRISIS"] == 0.70

    def _build_votes(regime_state: str):
        """Build 9 agents: 5 buy + 4 hold -> confidence ≈ 0.56."""
        buy_names = ["market_perception", "regime", "strategy", "risk", "execution"]
        hold_names = ["flow_perception", "social_perception", "hypothesis", "critic"]
        votes = []
        for n in buy_names:
            meta: Dict[str, Any] = {}
            if n == "regime":
                meta = {"regime_state": regime_state}
            elif n == "execution":
                meta = {"execution_ready": True}
            elif n == "risk":
                meta = {"risk_limits": {}}
            votes.append(_make_vote(n, "buy", 0.50, metadata=meta))
        for n in hold_names:
            votes.append(_make_vote(n, "hold", 0.50))
        return votes

    patches = [
        patch("app.council.arbiter._get_learned_weights", return_value={}),
        patch("app.council.arbiter.get_thompson_sampler", return_value=MagicMock(
            should_explore=MagicMock(return_value=False),
        )),
        patch("app.council.arbiter.get_arbiter_meta_model", return_value=MagicMock(
            predict=MagicMock(return_value=None),
        )),
    ]
    for p in patches:
        p.start()
    try:
        result_bull = arbitrate("SPY", "1d", "2026-03-14T10:00:00Z", _build_votes("BULLISH"))
        assert result_bull.final_direction == "buy"
        assert result_bull.final_confidence > 0.30
        assert result_bull.execution_ready is True, (
            f"BULLISH (threshold 0.30) should pass confidence {result_bull.final_confidence:.2f}"
        )

        result_crisis = arbitrate("SPY", "1d", "2026-03-14T10:00:00Z", _build_votes("CRISIS"))
        assert result_crisis.final_confidence < 0.70, (
            f"Expected final confidence < 0.70, got {result_crisis.final_confidence:.2f}"
        )
        assert result_crisis.execution_ready is False, (
            f"CRISIS (threshold 0.70) should block confidence {result_crisis.final_confidence:.2f}"
        )
    finally:
        for p in patches:
            p.stop()


# ---------------------------------------------------------------------------
# 6. Cooldown varies by regime
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cooldown_varies_by_regime():
    """GREEN cooldown=30s (second signal within 30s skipped); RED cooldown=300s."""
    from app.council.council_gate import _REGIME_COOLDOWNS

    assert _REGIME_COOLDOWNS["GREEN"] == 30
    assert _REGIME_COOLDOWNS["RED"] == 300

    bus = MockMessageBus()
    gate = _create_gate(bus, cooldown_seconds=120)
    gate._running = True
    council_calls = _install_tracker(gate)

    # --- GREEN regime: cooldown 30s ---
    gate._current_regime = "GREEN"

    await gate._on_signal({"symbol": "AAA", "score": 60, "direction": "buy"})
    await asyncio.sleep(0)  # let task run
    assert "AAA" in council_calls, "First GREEN signal should pass"

    council_calls.clear()
    await gate._on_signal({"symbol": "AAA", "score": 60, "direction": "buy"})
    await asyncio.sleep(0)
    assert "AAA" not in council_calls, "Second AAA:buy within GREEN 30s cooldown should be skipped"

    # --- RED regime: cooldown 300s ---
    gate._current_regime = "RED"
    gate._symbol_direction_last_eval.clear()
    gate._symbol_last_eval.clear()
    council_calls.clear()

    await gate._on_signal({"symbol": "BBB", "score": 80, "direction": "buy"})
    await asyncio.sleep(0)
    assert "BBB" in council_calls, "First RED signal should pass"

    council_calls.clear()
    await gate._on_signal({"symbol": "BBB", "score": 80, "direction": "buy"})
    await asyncio.sleep(0)
    assert "BBB" not in council_calls, "Second BBB:buy within RED 300s cooldown should be skipped"

    assert gate._cooldown_skips >= 2


# ---------------------------------------------------------------------------
# 7. Unknown regime defaults to NEUTRAL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_regime_unknown_defaults():
    """Unknown/unrecognized regime falls back to base threshold and base cooldown."""
    bus = MockMessageBus()
    gate = _create_gate(bus, cooldown_seconds=120)
    gate._current_regime = "XYZZY"
    gate._running = True

    actual_threshold = gate._get_regime_threshold()
    assert actual_threshold == gate.base_gate_threshold, (
        f"Unknown regime should use base threshold {gate.base_gate_threshold}, got {actual_threshold}"
    )

    actual_cooldown = gate._get_regime_cooldown()
    assert actual_cooldown == 120, (
        f"Unknown regime should use base cooldown 120s, got {actual_cooldown}"
    )

    council_calls = _install_tracker(gate)

    await gate._on_signal({"symbol": "PASS", "score": 70, "direction": "buy"})
    await asyncio.sleep(0)
    await gate._on_signal({"symbol": "BLOCK", "score": 60, "direction": "buy"})
    await asyncio.sleep(0)

    assert "PASS" in council_calls, "Score 70 should pass default threshold 65"
    assert "BLOCK" not in council_calls, "Score 60 should be blocked by default threshold 65"
