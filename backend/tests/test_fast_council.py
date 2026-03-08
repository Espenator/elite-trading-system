"""Tests for FastCouncil pre-screening tier (Issue #38 — E4).

Validates:
    - FastCouncilResult dataclass construction and to_dict()
    - run_fast_council() with mocked agents
    - VETO propagation from individual agents
    - Hold quorum logic (>= 3 of 5 agents say hold)
    - Low-confidence signal produces skip_deep=True
    - Timeout handling produces a safe hold
    - Escalation path: skip_deep=False when signal is strong
    - CouncilGate.fast_council_enabled flag
    - CouncilGate fast_skipped counter increments correctly
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.council.fast_council import (
    FastCouncilResult,
    run_fast_council,
    CONFIDENCE_MIN,
    HOLD_QUORUM,
    FAST_AGENTS,
    DEFAULT_TIMEOUT,
)
from app.council.schemas import AgentVote


# ─────────────────────────────────────────────────────────────────────────────
# FastCouncilResult dataclass
# ─────────────────────────────────────────────────────────────────────────────

class TestFastCouncilResult:
    def test_defaults(self):
        r = FastCouncilResult()
        assert r.direction == "hold"
        assert r.confidence == 0.0
        assert r.skip_deep is False
        assert r.veto is False
        assert r.veto_reasons == []
        assert r.votes == []
        assert r.latency_ms == 0.0

    def test_to_dict_shape(self):
        vote = AgentVote(
            agent_name="rsi",
            direction="buy",
            confidence=0.7,
            reasoning="RSI oversold",
            veto=False,
        )
        r = FastCouncilResult(
            direction="buy",
            confidence=0.7,
            skip_deep=False,
            votes=[vote],
            latency_ms=45.2,
        )
        d = r.to_dict()
        assert d["direction"] == "buy"
        assert d["confidence"] == 0.7
        assert d["skip_deep"] is False
        assert d["latency_ms"] == 45.2
        assert len(d["votes"]) == 1
        assert d["votes"][0]["agent"] == "rsi"

    def test_veto_result(self):
        r = FastCouncilResult(
            direction="hold",
            confidence=0.0,
            skip_deep=True,
            veto=True,
            veto_reasons=["Extreme volatility"],
        )
        assert r.veto is True
        d = r.to_dict()
        assert "Extreme volatility" in d["veto_reasons"]


# ─────────────────────────────────────────────────────────────────────────────
# run_fast_council — mocked agent behaviour
# ─────────────────────────────────────────────────────────────────────────────

def _make_vote(name: str, direction: str, confidence: float, veto: bool = False,
               veto_reason: str = "") -> AgentVote:
    return AgentVote(
        agent_name=name,
        direction=direction,
        confidence=confidence,
        reasoning=f"{name} says {direction}",
        veto=veto,
        veto_reason=veto_reason,
    )


def _agent_patch(votes_map: dict):
    """Return a context manager that patches _run_agent_safe with given votes."""
    async def _fake_agent(name, symbol, timeframe, features, context):
        return votes_map.get(name)

    return patch("app.council.fast_council._run_agent_safe", side_effect=_fake_agent)


class TestRunFastCouncilBuySignal:
    @pytest.mark.anyio
    async def test_strong_buy_not_skipped(self):
        votes = {
            "market_perception": _make_vote("market_perception", "buy", 0.75),
            "rsi": _make_vote("rsi", "buy", 0.70),
            "ema_trend": _make_vote("ema_trend", "buy", 0.65),
            "risk": _make_vote("risk", "hold", 0.50),
            "execution": _make_vote("execution", "buy", 0.60),
        }
        with _agent_patch(votes):
            result = await run_fast_council("AAPL", features={}, context={})

        assert result.direction == "buy"
        assert result.skip_deep is False
        assert result.veto is False
        assert len(result.votes) == 5

    @pytest.mark.anyio
    async def test_returns_latency(self):
        votes = {n: _make_vote(n, "buy", 0.65) for n in FAST_AGENTS}
        with _agent_patch(votes):
            result = await run_fast_council("MSFT")

        assert result.latency_ms >= 0.0


class TestRunFastCouncilHoldQuorum:
    @pytest.mark.anyio
    async def test_hold_quorum_skips_deep(self):
        """3+ hold votes → skip_deep=True."""
        votes = {
            "market_perception": _make_vote("market_perception", "hold", 0.40),
            "rsi": _make_vote("rsi", "hold", 0.35),
            "ema_trend": _make_vote("ema_trend", "hold", 0.30),
            "risk": _make_vote("risk", "buy", 0.55),
            "execution": _make_vote("execution", "buy", 0.55),
        }
        with _agent_patch(votes):
            result = await run_fast_council("SPY")

        assert result.skip_deep is True
        assert result.veto is False

    @pytest.mark.anyio
    async def test_two_holds_does_not_skip(self):
        """Only 2 hold votes → should NOT automatically skip."""
        votes = {
            "market_perception": _make_vote("market_perception", "hold", 0.40),
            "rsi": _make_vote("rsi", "hold", 0.40),
            "ema_trend": _make_vote("ema_trend", "buy", 0.70),
            "risk": _make_vote("risk", "buy", 0.65),
            "execution": _make_vote("execution", "buy", 0.60),
        }
        with _agent_patch(votes):
            result = await run_fast_council("NVDA")

        assert result.skip_deep is False
        assert result.direction == "buy"


class TestRunFastCouncilVeto:
    @pytest.mark.anyio
    async def test_single_veto_skips_deep(self):
        votes = {
            "market_perception": _make_vote("market_perception", "buy", 0.80),
            "rsi": _make_vote("rsi", "buy", 0.75),
            "ema_trend": _make_vote("ema_trend", "buy", 0.70),
            "risk": _make_vote("risk", "hold", 0.0, veto=True,
                               veto_reason="Extreme volatility"),
            "execution": _make_vote("execution", "buy", 0.60),
        }
        with _agent_patch(votes):
            result = await run_fast_council("TSLA")

        assert result.skip_deep is True
        assert result.veto is True
        assert "Extreme volatility" in result.veto_reasons

    @pytest.mark.anyio
    async def test_double_veto(self):
        votes = {
            "market_perception": _make_vote("market_perception", "buy", 0.80),
            "rsi": _make_vote("rsi", "buy", 0.70),
            "ema_trend": _make_vote("ema_trend", "sell", 0.65),
            "risk": _make_vote("risk", "hold", 0.0, veto=True, veto_reason="Drawdown"),
            "execution": _make_vote("execution", "hold", 0.0, veto=True,
                                    veto_reason="Market closed"),
        }
        with _agent_patch(votes):
            result = await run_fast_council("AMZN")

        assert result.veto is True
        assert len(result.veto_reasons) == 2


class TestRunFastCouncilLowConfidence:
    @pytest.mark.anyio
    async def test_low_avg_confidence_skips_deep(self):
        """Average confidence below CONFIDENCE_MIN → skip_deep."""
        low = CONFIDENCE_MIN - 0.05
        votes = {n: _make_vote(n, "buy", low) for n in FAST_AGENTS}
        with _agent_patch(votes):
            result = await run_fast_council("AMD")

        assert result.skip_deep is True


class TestRunFastCouncilNoAgents:
    @pytest.mark.anyio
    async def test_all_agents_fail_returns_hold(self):
        """All agents fail → safe hold, skip_deep=True."""
        async def _fail(*args, **kwargs):
            return None

        with patch("app.council.fast_council._run_agent_safe", side_effect=_fail):
            result = await run_fast_council("FAIL")

        assert result.skip_deep is True
        assert result.direction == "hold"
        assert result.confidence == 0.0


class TestRunFastCouncilTimeout:
    @pytest.mark.anyio
    async def test_timeout_returns_safe_hold(self):
        """Timeout in fast council → conservative hold, skip_deep=True."""
        async def _slow(*args, **kwargs):
            await asyncio.sleep(10)
            return _make_vote("slow", "buy", 0.9)

        with patch("app.council.fast_council._run_agent_safe", side_effect=_slow):
            result = await run_fast_council("SLOW", timeout=0.01)

        assert result.skip_deep is True
        assert result.direction == "hold"


# ─────────────────────────────────────────────────────────────────────────────
# CouncilGate fast_council_enabled integration
# ─────────────────────────────────────────────────────────────────────────────

class TestCouncilGateFastCouncil:
    def _make_bus(self):
        bus = MagicMock()
        bus.subscribe = AsyncMock()
        bus.unsubscribe = AsyncMock()
        bus.publish = AsyncMock()
        return bus

    def test_fast_council_enabled_by_default(self):
        from app.council.council_gate import CouncilGate
        gate = CouncilGate(self._make_bus())
        assert gate.fast_council_enabled is True

    def test_fast_council_disabled_via_kwarg(self):
        from app.council.council_gate import CouncilGate
        gate = CouncilGate(self._make_bus(), fast_council_enabled=False)
        assert gate.fast_council_enabled is False

    def test_fast_council_disabled_via_env(self, monkeypatch):
        monkeypatch.setenv("FAST_COUNCIL_ENABLED", "false")
        from app.council.council_gate import CouncilGate
        gate = CouncilGate(self._make_bus())
        assert gate.fast_council_enabled is False

    @pytest.mark.anyio
    async def test_get_status_includes_fast_council_fields(self):
        from app.council.council_gate import CouncilGate
        gate = CouncilGate(self._make_bus())
        await gate.start()
        status = gate.get_status()
        assert "fast_council_enabled" in status
        assert "fast_skipped" in status
        await gate.stop()

    @pytest.mark.anyio
    async def test_fast_council_veto_increments_fast_skipped(self):
        """When FastCouncil vetoes, fast_skipped and councils_vetoed both increment."""
        from app.council.council_gate import CouncilGate

        bus = self._make_bus()
        gate = CouncilGate(bus, gate_threshold=50.0, cooldown_seconds=0,
                           fast_council_enabled=True)
        await gate.start()

        # Patch FastCouncil to always veto
        veto_result = FastCouncilResult(
            direction="hold", confidence=0.0, skip_deep=True,
            veto=True, veto_reasons=["test veto"],
        )
        with patch(
            "app.council.council_gate.CouncilGate._evaluate_with_council",
            wraps=gate._evaluate_with_council,
        ):
            with patch("app.council.fast_council.run_fast_council",
                       AsyncMock(return_value=veto_result)):
                signal_data = {
                    "symbol": "TEST",
                    "score": 80.0,
                    "features": {},
                    "source": "stream",
                }
                await gate._evaluate_with_council("TEST", signal_data)

        assert gate._fast_skipped == 1
        assert gate._councils_vetoed == 1
        # Full council should NOT have been invoked (bus.publish not called with council.verdict)
        for call in bus.publish.call_args_list:
            assert call.args[0] != "council.verdict"

        await gate.stop()
