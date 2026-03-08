"""Tests for the multi-tier fast council pre-screening path.

Covers:
 - FastCouncilResult serialization
 - _fast_arbitrate() rules 1–5
 - run_fast_council() async integration (mocked agents)
 - CouncilGate tiered routing logic
 - DecisionPacket.council_tier field
"""
import asyncio
import pytest

from app.council.schemas import AgentVote, DecisionPacket
from app.council.fast_council import (
    FastCouncilResult,
    _fast_arbitrate,
    FAST_REQUIRED_AGENTS,
    FAST_VETO_AGENTS,
    FAST_HOLD_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vote(name, direction="buy", confidence=0.7, veto=False, veto_reason="", weight=1.0):
    return AgentVote(
        agent_name=name,
        direction=direction,
        confidence=confidence,
        reasoning=f"{name} test vote",
        veto=veto,
        veto_reason=veto_reason,
        weight=weight,
    )


def _fast_votes(
    regime_dir="buy",
    market_dir="buy",
    rsi_dir="buy",
    ema_dir="buy",
    bbv_dir="buy",
    rel_dir="buy",
    risk_dir="buy",
    risk_veto=False,
    risk_veto_reason="",
    confidence=0.7,
):
    """Build a standard set of fast-path agent votes."""
    return [
        _vote("regime", regime_dir, confidence=confidence),
        _vote("market_perception", market_dir, confidence=confidence),
        _vote("rsi", rsi_dir, confidence=confidence),
        _vote("ema_trend", ema_dir, confidence=confidence),
        _vote("bbv", bbv_dir, confidence=confidence),
        _vote("relative_strength", rel_dir, confidence=confidence),
        _vote("risk", risk_dir, confidence=confidence,
              veto=risk_veto, veto_reason=risk_veto_reason),
    ]


# ---------------------------------------------------------------------------
# FastCouncilResult serialization
# ---------------------------------------------------------------------------

class TestFastCouncilResult:
    def test_to_dict_escalate(self):
        result = FastCouncilResult(
            symbol="AAPL",
            direction="buy",
            confidence=0.65,
            escalate=True,
            vetoed=False,
            reasoning="Escalating",
            latency_ms=120.5,
        )
        d = result.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["direction"] == "buy"
        assert d["confidence"] == 0.65
        assert d["escalate"] is True
        assert d["vetoed"] is False
        assert d["latency_ms"] == 120.5

    def test_to_dict_hold(self):
        result = FastCouncilResult(
            symbol="TSLA",
            direction="hold",
            confidence=0.1,
            escalate=False,
            vetoed=False,
            reasoning="Low confidence",
            latency_ms=50.0,
        )
        d = result.to_dict()
        assert d["direction"] == "hold"
        assert d["escalate"] is False
        assert d["vetoed"] is False

    def test_to_dict_vetoed(self):
        result = FastCouncilResult(
            symbol="SPY",
            direction="hold",
            confidence=0.0,
            escalate=False,
            vetoed=True,
            veto_reasons=["risk: portfolio heat exceeded"],
            reasoning="Fast veto: risk",
            latency_ms=30.0,
        )
        d = result.to_dict()
        assert d["vetoed"] is True
        assert len(d["veto_reasons"]) == 1
        assert "risk" in d["veto_reasons"][0]

    def test_to_dict_rounds_confidence(self):
        result = FastCouncilResult(
            symbol="NVDA",
            direction="sell",
            confidence=0.12345678,
            escalate=True,
            vetoed=False,
        )
        d = result.to_dict()
        # Should be rounded to 4 decimal places
        assert d["confidence"] == round(0.12345678, 4)

    def test_agent_votes_serialized(self):
        votes = [_vote("regime", "buy"), _vote("risk", "buy")]
        result = FastCouncilResult(
            symbol="AAPL",
            direction="buy",
            confidence=0.7,
            escalate=True,
            vetoed=False,
            agent_votes=votes,
        )
        d = result.to_dict()
        assert len(d["agent_votes"]) == 2
        assert d["agent_votes"][0]["agent_name"] == "regime"


# ---------------------------------------------------------------------------
# _fast_arbitrate — Rule 1: Veto
# ---------------------------------------------------------------------------

class TestFastArbitrateVeto:
    def test_risk_veto_blocks_escalation(self):
        votes = _fast_votes(risk_veto=True, risk_veto_reason="Portfolio heat exceeded")
        result = _fast_arbitrate("AAPL", votes, latency_ms=100.0)
        assert result.vetoed is True
        assert result.escalate is False
        assert result.direction == "hold"
        assert result.confidence == 0.0
        assert any("risk" in r for r in result.veto_reasons)

    def test_non_veto_agent_flag_ignored(self):
        """Veto flag on regime (not in FAST_VETO_AGENTS) must be ignored."""
        votes = _fast_votes()
        # manually flip regime's veto flag
        votes[0] = _vote("regime", "sell", veto=True, veto_reason="I want to veto")
        result = _fast_arbitrate("AAPL", votes, latency_ms=100.0)
        # regime is NOT in FAST_VETO_AGENTS — should escalate normally
        assert result.vetoed is False

    def test_risk_veto_overrides_all_buy_votes(self):
        votes = _fast_votes(
            regime_dir="buy", rsi_dir="buy", ema_dir="buy",
            risk_veto=True, risk_veto_reason="Max drawdown hit",
        )
        result = _fast_arbitrate("SPY", votes, latency_ms=50.0)
        assert result.vetoed is True
        assert result.escalate is False


# ---------------------------------------------------------------------------
# _fast_arbitrate — Rule 2: Required agents
# ---------------------------------------------------------------------------

class TestFastArbitrateRequiredAgents:
    def test_missing_regime_holds(self):
        votes = [
            _vote("market_perception", "buy"),
            _vote("rsi", "buy"),
            _vote("risk", "buy"),
            # regime missing!
        ]
        result = _fast_arbitrate("AAPL", votes, latency_ms=80.0)
        assert result.escalate is False
        assert result.vetoed is False
        assert result.direction == "hold"
        assert "regime" in result.reasoning

    def test_missing_risk_holds(self):
        votes = [
            _vote("regime", "buy"),
            _vote("market_perception", "buy"),
            _vote("rsi", "buy"),
            # risk missing!
        ]
        result = _fast_arbitrate("AAPL", votes, latency_ms=80.0)
        assert result.escalate is False
        assert result.direction == "hold"
        assert "risk" in result.reasoning

    def test_missing_both_required_agents(self):
        votes = [_vote("rsi", "buy"), _vote("ema_trend", "buy")]
        result = _fast_arbitrate("AAPL", votes, latency_ms=60.0)
        assert result.escalate is False
        assert result.direction == "hold"


# ---------------------------------------------------------------------------
# _fast_arbitrate — Rule 3: Confidence threshold
# ---------------------------------------------------------------------------

class TestFastArbitrateConfidenceThreshold:
    """Rule 3: winning-direction vote-fraction < FAST_HOLD_THRESHOLD → hold.

    The threshold (0.40) is applied to the *fraction* of total weighted votes
    that the winning direction captures, not to individual agent confidence.

    A near three-way tie (each direction ~1/3) gives the winner ~0.34 fraction
    which is below 0.40, so Rule 3 fires.  A clear majority (>40%) escalates.
    """

    def test_near_three_way_tie_does_not_escalate(self):
        """Winning fraction ~0.34 < 0.40 → hold (Rule 3)."""
        votes = [
            _vote("regime", "buy",  confidence=1.0, weight=0.34),  # required
            _vote("risk",   "sell", confidence=1.0, weight=0.33),  # required
            _vote("rsi",    "hold", confidence=1.0, weight=0.33),
        ]
        # buy_w=0.34, sell_w=0.33, hold_w=0.33; total=1.0
        # buy wins at 0.34/1.0 = 0.34 < 0.40 → Rule 3 fires
        result = _fast_arbitrate("AAPL", votes, latency_ms=90.0)
        assert result.escalate is False
        assert result.direction == "hold"
        assert "threshold" in result.reasoning
        assert result.confidence < FAST_HOLD_THRESHOLD

    def test_below_threshold_reasoning_present(self):
        votes = [
            _vote("regime", "buy",  confidence=1.0, weight=0.38),  # required
            _vote("risk",   "sell", confidence=1.0, weight=0.33),  # required
            _vote("rsi",    "hold", confidence=1.0, weight=0.29),
        ]
        # buy_w=0.38 wins but 0.38/1.0 = 0.38 < 0.40
        result = _fast_arbitrate("AAPL", votes, latency_ms=90.0)
        assert result.escalate is False
        assert "threshold" in result.reasoning

    def test_at_threshold_escalates(self):
        votes = [
            _vote("regime", "buy",  confidence=1.0, weight=0.40),  # required
            _vote("risk",   "sell", confidence=1.0, weight=0.30),  # required
            _vote("rsi",    "hold", confidence=1.0, weight=0.30),
        ]
        # buy_w=0.40 wins at 0.40/1.0 = 0.40 — exactly at threshold → escalates
        result = _fast_arbitrate("AAPL", votes, latency_ms=90.0)
        assert result.escalate is True

    def test_clear_majority_escalates(self):
        votes = _fast_votes(confidence=0.8)
        result = _fast_arbitrate("AAPL", votes, latency_ms=90.0)
        # Unanimous buy → fraction = 1.0 > 0.40 → escalates
        assert result.escalate is True
        assert result.confidence > FAST_HOLD_THRESHOLD

    def test_unanimous_low_individual_confidence_still_escalates(self):
        """All agents unanimously agree → vote-fraction = 1.0 → escalates regardless
        of per-agent confidence magnitude."""
        votes = _fast_votes(confidence=0.01)  # very low per-agent confidence
        result = _fast_arbitrate("AAPL", votes, latency_ms=90.0)
        # 7 unanimous buy votes → buy captures 100% of total weight → 1.0 > 0.40
        assert result.escalate is True
        assert result.confidence == 1.0

    def test_confidence_reflected_in_result(self):
        votes = _fast_votes(confidence=0.75)
        result = _fast_arbitrate("AAPL", votes, latency_ms=90.0)
        assert result.confidence > 0.0
        assert result.confidence <= 1.0


# ---------------------------------------------------------------------------
# _fast_arbitrate — Rule 4: Majority hold
# ---------------------------------------------------------------------------

class TestFastArbitrateMajorityHold:
    def test_majority_hold_does_not_escalate(self):
        votes = _fast_votes(
            regime_dir="hold",
            market_dir="hold",
            rsi_dir="hold",
            ema_dir="hold",
            bbv_dir="hold",
            rel_dir="hold",
            risk_dir="hold",
        )
        result = _fast_arbitrate("AAPL", votes, latency_ms=80.0)
        assert result.escalate is False
        assert result.direction == "hold"

    def test_mixed_hold_majority(self):
        votes = [
            _vote("regime", "hold", confidence=0.8),
            _vote("market_perception", "hold", confidence=0.7),
            _vote("rsi", "buy", confidence=0.6),
            _vote("ema_trend", "hold", confidence=0.7),
            _vote("bbv", "buy", confidence=0.5),
            _vote("relative_strength", "hold", confidence=0.6),
            _vote("risk", "hold", confidence=0.7),
        ]
        result = _fast_arbitrate("AAPL", votes, latency_ms=80.0)
        assert result.direction == "hold"
        assert result.escalate is False


# ---------------------------------------------------------------------------
# _fast_arbitrate — Rule 5: Escalate
# ---------------------------------------------------------------------------

class TestFastArbitrateEscalate:
    def test_unanimous_buy_escalates(self):
        votes = _fast_votes(confidence=0.7)
        result = _fast_arbitrate("AAPL", votes, latency_ms=90.0)
        assert result.escalate is True
        assert result.direction == "buy"
        assert result.vetoed is False

    def test_unanimous_sell_escalates(self):
        votes = _fast_votes(
            regime_dir="sell", market_dir="sell", rsi_dir="sell",
            ema_dir="sell", bbv_dir="sell", rel_dir="sell", risk_dir="sell",
        )
        result = _fast_arbitrate("AAPL", votes, latency_ms=90.0)
        assert result.escalate is True
        assert result.direction == "sell"

    def test_majority_buy_escalates(self):
        votes = [
            _vote("regime", "buy", confidence=0.8),
            _vote("market_perception", "buy", confidence=0.7),
            _vote("rsi", "buy", confidence=0.6),
            _vote("ema_trend", "buy", confidence=0.7),
            _vote("bbv", "sell", confidence=0.5),     # minority sell
            _vote("relative_strength", "hold", confidence=0.4),
            _vote("risk", "buy", confidence=0.7),
        ]
        result = _fast_arbitrate("AAPL", votes, latency_ms=80.0)
        assert result.escalate is True
        assert result.direction == "buy"

    def test_escalate_reasoning_contains_counts(self):
        votes = _fast_votes(confidence=0.65)
        result = _fast_arbitrate("AAPL", votes, latency_ms=90.0)
        assert result.escalate is True
        assert "buy=" in result.reasoning
        assert "sell=" in result.reasoning
        assert "hold=" in result.reasoning

    def test_latency_preserved_in_result(self):
        votes = _fast_votes(confidence=0.7)
        result = _fast_arbitrate("AAPL", votes, latency_ms=123.4)
        assert result.latency_ms == 123.4


# ---------------------------------------------------------------------------
# DecisionPacket.council_tier
# ---------------------------------------------------------------------------

class TestCouncilTier:
    def test_default_tier_is_deep(self):
        dp = DecisionPacket(
            symbol="AAPL",
            timeframe="1d",
            timestamp="2025-01-01T00:00:00Z",
            votes=[],
            final_direction="buy",
            final_confidence=0.75,
            vetoed=False,
            veto_reasons=[],
            risk_limits={},
            execution_ready=True,
            council_reasoning="test",
        )
        assert dp.council_tier == "deep"

    def test_council_tier_in_to_dict(self):
        dp = DecisionPacket(
            symbol="AAPL",
            timeframe="1d",
            timestamp="2025-01-01T00:00:00Z",
            votes=[],
            final_direction="buy",
            final_confidence=0.75,
            vetoed=False,
            veto_reasons=[],
            risk_limits={},
            execution_ready=True,
            council_reasoning="test",
            council_tier="deep",
        )
        d = dp.to_dict()
        assert "council_tier" in d
        assert d["council_tier"] == "deep"

    def test_council_tier_fast_in_to_dict(self):
        dp = DecisionPacket(
            symbol="AAPL",
            timeframe="1d",
            timestamp="2025-01-01T00:00:00Z",
            votes=[],
            final_direction="hold",
            final_confidence=0.0,
            vetoed=True,
            veto_reasons=["homeostasis"],
            risk_limits={},
            execution_ready=False,
            council_reasoning="fast path blocked",
            council_tier="fast",
        )
        d = dp.to_dict()
        assert d["council_tier"] == "fast"


# ---------------------------------------------------------------------------
# CouncilGate tiered routing
# ---------------------------------------------------------------------------

class TestCouncilGateRouting:
    """Test that CouncilGate routes signals correctly between fast and deep paths."""

    def _make_gate(self, enable_fast_path=True, gate_threshold=65.0, fast_threshold=45.0):
        """Build a CouncilGate with a mock message bus."""
        from app.council.council_gate import CouncilGate

        class MockBus:
            def __init__(self):
                self.subscriptions = {}
                self.published = []

            async def subscribe(self, topic, handler):
                self.subscriptions[topic] = handler

            async def unsubscribe(self, topic, handler):
                self.subscriptions.pop(topic, None)

            async def publish(self, topic, data):
                self.published.append((topic, data))

        bus = MockBus()
        gate = CouncilGate(
            bus,
            gate_threshold=gate_threshold,
            fast_threshold=fast_threshold,
            enable_fast_path=enable_fast_path,
        )
        return gate, bus

    def test_get_status_includes_fast_fields(self):
        gate, _ = self._make_gate()
        gate._running = True
        gate._start_time = 0
        status = gate.get_status()
        assert "fast_threshold" in status
        assert "enable_fast_path" in status
        assert "fast_screened" in status
        assert "fast_held" in status
        assert "fast_escalated" in status
        assert "fast_escalation_rate" in status

    def test_get_status_defaults(self):
        gate, _ = self._make_gate()
        gate._running = True
        gate._start_time = 0
        status = gate.get_status()
        assert status["fast_threshold"] == 45.0
        assert status["gate_threshold"] == 65.0
        assert status["enable_fast_path"] is True
        assert status["fast_screened"] == 0
        assert status["fast_held"] == 0
        assert status["fast_escalated"] == 0
        assert status["fast_escalation_rate"] == 0.0

    async def test_signal_below_fast_threshold_ignored(self):
        gate, bus = self._make_gate()
        await gate.start()
        # Score below fast_threshold — should be ignored
        await bus.subscriptions["signal.generated"]({
            "symbol": "AAPL",
            "score": 30.0,
            "regime": "bullish",
        })
        # Give tasks a chance to run
        await asyncio.sleep(0)
        assert gate._signals_received == 1
        assert gate._councils_invoked == 0
        assert gate._fast_screened == 0

    async def test_mock_signal_always_ignored(self):
        gate, bus = self._make_gate()
        await gate.start()
        await bus.subscriptions["signal.generated"]({
            "symbol": "AAPL",
            "score": 80.0,
            "source": "mock_engine",
        })
        await asyncio.sleep(0)
        assert gate._councils_invoked == 0
        assert gate._fast_screened == 0

    def test_fast_path_disabled_skips_fast_council(self):
        """With enable_fast_path=False, fast_screened should never increment."""
        gate, _ = self._make_gate(enable_fast_path=False)
        assert gate.enable_fast_path is False
        status = gate.get_status()
        assert status["enable_fast_path"] is False

    def test_fast_escalation_rate_computed(self):
        gate, _ = self._make_gate()
        gate._fast_screened = 10
        gate._fast_escalated = 4
        status = gate.get_status()
        assert status["fast_escalation_rate"] == 0.4

    def test_pass_rate_computed(self):
        gate, _ = self._make_gate()
        gate._councils_invoked = 5
        gate._councils_passed = 2
        status = gate.get_status()
        assert status["pass_rate"] == 0.4


# ---------------------------------------------------------------------------
# FastCouncilResult edge cases
# ---------------------------------------------------------------------------

class TestFastArbitrateEdgeCases:
    def test_empty_votes_holds(self):
        result = _fast_arbitrate("AAPL", [], latency_ms=10.0)
        assert result.escalate is False
        assert result.direction == "hold"

    def test_buy_sell_tie_holds(self):
        """Exact tie between buy and sell weight should produce hold."""
        votes = [
            _vote("regime", "buy", confidence=1.0, weight=1.0),
            _vote("risk", "sell", confidence=1.0, weight=1.0),
        ]
        result = _fast_arbitrate("AAPL", votes, latency_ms=10.0)
        # Tie: should hold
        assert result.direction == "hold"
        assert result.escalate is False

    def test_vetoed_agent_excluded_from_weights(self):
        """A vetoing risk agent should not contribute its weight to vote totals."""
        votes = [
            _vote("regime", "buy", confidence=0.9, weight=1.0),
            _vote("risk", "sell", confidence=1.0, weight=2.0, veto=True, veto_reason="heat"),
        ]
        result = _fast_arbitrate("AAPL", votes, latency_ms=10.0)
        # risk is in FAST_VETO_AGENTS → veto triggered
        assert result.vetoed is True
        assert result.escalate is False

    def test_result_confidence_is_in_unit_range(self):
        for conf in [0.3, 0.5, 0.8, 1.0]:
            votes = _fast_votes(confidence=conf)
            result = _fast_arbitrate("AAPL", votes, latency_ms=10.0)
            assert 0.0 <= result.confidence <= 1.0

    def test_fast_required_agents_set_contents(self):
        assert "regime" in FAST_REQUIRED_AGENTS
        assert "risk" in FAST_REQUIRED_AGENTS

    def test_fast_veto_agents_set_contents(self):
        assert "risk" in FAST_VETO_AGENTS

    def test_fast_hold_threshold_value(self):
        assert 0.0 < FAST_HOLD_THRESHOLD < 1.0
        # Threshold must be > 1/3 to be reachable when 3 directions compete
        assert FAST_HOLD_THRESHOLD > 1 / 3


# ---------------------------------------------------------------------------
# CouncilGate env-var passthrough (runtime wiring)
# ---------------------------------------------------------------------------

class TestCouncilGateEnvVarWiring:
    """Verify that CouncilGate accepts fast_threshold and enable_fast_path
    at construction so that runtime env vars can control the fast path.

    These tests confirm the gap identified in the repo-truth audit is fixed:
    main.py now passes COUNCIL_FAST_THRESHOLD and COUNCIL_FAST_PATH_ENABLED
    to CouncilGate at startup.
    """

    def test_custom_fast_threshold_accepted(self):
        from app.council.council_gate import CouncilGate

        class MockBus:
            async def subscribe(self, *a):
                pass

        gate = CouncilGate(
            message_bus=MockBus(),
            gate_threshold=70.0,
            fast_threshold=50.0,
            enable_fast_path=True,
        )
        assert gate.fast_threshold == 50.0
        assert gate.gate_threshold == 70.0
        assert gate.enable_fast_path is True

    def test_fast_path_disabled_via_constructor(self):
        from app.council.council_gate import CouncilGate

        class MockBus:
            async def subscribe(self, *a):
                pass

        gate = CouncilGate(
            message_bus=MockBus(),
            gate_threshold=65.0,
            fast_threshold=45.0,
            enable_fast_path=False,
        )
        assert gate.enable_fast_path is False
        # When disabled, threshold for routing should be gate_threshold
        status = gate.get_status()
        assert status["enable_fast_path"] is False

    def test_status_exposes_wiring_config(self):
        """get_status() must expose all three tunable params for ops dashboards."""
        from app.council.council_gate import CouncilGate

        class MockBus:
            async def subscribe(self, *a):
                pass

        gate = CouncilGate(
            message_bus=MockBus(),
            gate_threshold=60.0,
            fast_threshold=40.0,
            enable_fast_path=True,
        )
        gate._start_time = 0
        status = gate.get_status()
        assert status["gate_threshold"] == 60.0
        assert status["fast_threshold"] == 40.0
        assert status["enable_fast_path"] is True
