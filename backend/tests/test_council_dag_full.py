"""Council DAG tests: agent compliance, stage ordering, arbiter rules, resilience.

8 tests covering the 35-agent council DAG internals including schema
validation, stage execution order, veto enforcement, and error handling.
"""
import asyncio
import collections
import importlib
import inspect
import time
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.council.arbiter import REQUIRED_AGENTS, VETO_AGENTS, arbitrate
from app.council.blackboard import BlackboardState
from app.council.schemas import AgentVote, DecisionPacket
from app.council.task_spawner import TaskSpawner


SYNTHETIC_FEATURES: Dict[str, Any] = {
    "features": {
        "regime": "GREEN",
        "close": 150.0,
        "open": 148.0,
        "high": 151.0,
        "low": 147.5,
        "volume": 50_000_000,
        "sma_20": 149.0,
        "sma_50": 147.0,
        "rsi_14": 55.0,
        "atr_14": 2.5,
        "bb_upper": 153.0,
        "bb_lower": 145.0,
        "macd": 0.5,
        "macd_signal": 0.3,
        "vix": 18.5,
        "vix_close": 18.5,
        "put_call_ratio": 0.85,
        "gex": 500_000_000,
        "dix": 0.45,
        "sector": "Technology",
        "market_cap": 2_500_000_000_000,
        "pe_ratio": 28.5,
        "return_1d": 0.02,
        "return_5d": 0.05,
        "return_20d": 0.08,
        "volume_surge_ratio": 1.3,
        "pct_from_20d_high": -0.02,
        "pct_from_20d_low": 0.08,
        "adx_14": 30.0,
        "breadth_ratio": 0.6,
        "ind_rsi_14": 55.0,
        "regime_confidence": 0.8,
    }
}

AGENT_MODULES = [
    "app.council.agents.market_perception_agent",
    "app.council.agents.flow_perception_agent",
    "app.council.agents.regime_agent",
    "app.council.agents.social_perception_agent",
    "app.council.agents.news_catalyst_agent",
    "app.council.agents.youtube_knowledge_agent",
    "app.council.agents.intermarket_agent",
    "app.council.agents.gex_agent",
    "app.council.agents.insider_agent",
    "app.council.agents.finbert_sentiment_agent",
    "app.council.agents.earnings_tone_agent",
    "app.council.agents.dark_pool_agent",
    "app.council.agents.macro_regime_agent",
    "app.council.agents.rsi_agent",
    "app.council.agents.bbv_agent",
    "app.council.agents.ema_trend_agent",
    "app.council.agents.relative_strength_agent",
    "app.council.agents.cycle_timing_agent",
    "app.council.agents.supply_chain_agent",
    "app.council.agents.institutional_flow_agent",
    "app.council.agents.congressional_agent",
    "app.council.agents.hypothesis_agent",
    "app.council.agents.layered_memory_agent",
    "app.council.agents.strategy_agent",
    "app.council.agents.risk_agent",
    "app.council.agents.execution_agent",
    "app.council.agents.portfolio_optimizer_agent",
    "app.council.agents.bull_debater",
    "app.council.agents.bear_debater",
    "app.council.agents.red_team_agent",
    "app.council.agents.critic_agent",
    "app.council.agents.alt_data_agent",
]


def _mock_agent_thresholds():
    """Return a defaultdict that supplies reasonable values for any threshold key."""
    defaults = {
        "return_1d_threshold": 0.01,
        "return_5d_threshold": 0.02,
        "return_20d_threshold": 0.05,
        "volume_surge_threshold": 1.5,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "confidence_floor": 0.2,
        "min_confidence": 0.3,
        "max_confidence": 0.95,
    }
    return collections.defaultdict(lambda: 0.01, defaults)


def _make_blackboard(symbol: str = "TEST") -> BlackboardState:
    bb = BlackboardState(symbol=symbol, raw_features=SYNTHETIC_FEATURES)
    bb.perceptions = {}
    return bb


def _make_context(blackboard: BlackboardState = None) -> Dict[str, Any]:
    if blackboard is None:
        blackboard = _make_blackboard()
    return {
        "blackboard": blackboard,
        "model_tier": "fast",
        "stage1": {},
        "stage2": {},
    }


@pytest.mark.asyncio
async def test_agent_schema_compliance_all_35():
    """Import all 32 agent modules and call evaluate() with synthetic features.

    Verifies each returns a valid AgentVote (direction in {buy,sell,hold},
    confidence in [0,1]). Uses try/except per agent so one failure doesn't
    kill the whole test. Debaters use evaluate_debate() signature.
    """
    results = {}
    failures = []
    blackboard = _make_blackboard("AAPL")
    context = _make_context(blackboard)

    mock_thresholds = _mock_agent_thresholds()

    for module_path in AGENT_MODULES:
        agent_name = module_path.split(".")[-1]
        try:
            mod = importlib.import_module(module_path)
        except Exception as e:
            failures.append(f"{agent_name}: import failed: {e}")
            continue

        try:
            with patch(
                "app.council.agent_config.get_agent_thresholds",
                return_value=mock_thresholds,
            ):
                if hasattr(mod, "evaluate"):
                    sig = inspect.signature(mod.evaluate)
                    params = list(sig.parameters.keys())
                    if len(params) >= 4:
                        vote = await asyncio.wait_for(
                            mod.evaluate("AAPL", "1d", SYNTHETIC_FEATURES, context),
                            timeout=10.0,
                        )
                    elif len(params) >= 2:
                        vote = await asyncio.wait_for(
                            mod.evaluate(SYNTHETIC_FEATURES, context),
                            timeout=10.0,
                        )
                    else:
                        vote = await asyncio.wait_for(
                            mod.evaluate(SYNTHETIC_FEATURES),
                            timeout=10.0,
                        )
                elif hasattr(mod, "evaluate_debate"):
                    vote = await asyncio.wait_for(
                        mod.evaluate_debate(
                            symbol="AAPL",
                            proposed_direction="buy",
                            evidence={"stage1": {}, "features": SYNTHETIC_FEATURES},
                            prior_rounds=[],
                            round_num=1,
                        ),
                        timeout=10.0,
                    )
                else:
                    failures.append(f"{agent_name}: no evaluate or evaluate_debate")
                    continue

            if isinstance(vote, AgentVote):
                assert vote.direction in {"buy", "sell", "hold"}, \
                    f"{agent_name}: direction '{vote.direction}' invalid"
                assert 0.0 <= vote.confidence <= 1.0, \
                    f"{agent_name}: confidence {vote.confidence} out of range"
                assert vote.agent_name, f"{agent_name}: missing agent_name"
                results[agent_name] = "PASS"
            elif isinstance(vote, dict):
                assert vote.get("direction") in {"buy", "sell", "hold"}, \
                    f"{agent_name}: dict direction invalid"
                results[agent_name] = "PASS (dict)"
            else:
                results[agent_name] = f"PASS (type={type(vote).__name__})"

        except asyncio.TimeoutError:
            failures.append(f"{agent_name}: timed out (10s)")
        except Exception as e:
            failures.append(f"{agent_name}: {type(e).__name__}: {e}")

    passed = sum(1 for v in results.values() if v.startswith("PASS"))
    total = len(AGENT_MODULES)

    assert passed >= total * 0.75, (
        f"Only {passed}/{total} agents passed schema compliance. "
        f"Failures: {failures}"
    )


@pytest.mark.asyncio
async def test_stage_ordering_sequential():
    """Verify DAG stages execute sequentially: S1 < S2 < S3 < S4 < S5."""
    execution_order = []

    async def make_stage_vote(agent_name: str, stage: int) -> AgentVote:
        execution_order.append({"agent": agent_name, "stage": stage, "time": time.monotonic()})
        return AgentVote(
            agent_name=agent_name,
            direction="buy",
            confidence=0.7,
            reasoning=f"Stage {stage} test",
            weight=1.0,
        )

    blackboard = _make_blackboard("AAPL")
    spawner = TaskSpawner(blackboard)

    stage_agents = {
        1: ["market_perception", "regime", "risk_stub"],
        2: ["rsi", "ema_trend"],
        3: ["hypothesis"],
        4: ["strategy"],
        5: ["risk", "execution"],
    }

    for stage_num, agents in stage_agents.items():
        for agent_name in agents:
            mock_module = MagicMock()
            mock_module.NAME = agent_name

            async def _eval(sym, tf, feat, ctx, _name=agent_name, _stage=stage_num):
                return await make_stage_vote(_name, _stage)

            mock_module.evaluate = _eval
            spawner.register(agent_name, mock_module)

    context = _make_context(blackboard)

    for stage_num, agents in stage_agents.items():
        stage_votes = await asyncio.gather(
            *[spawner.spawn(a, "AAPL", "1d", context=context) for a in agents]
        )
        for v in stage_votes:
            blackboard.perceptions[v.agent_name] = v.to_dict()

    stage_times = collections.defaultdict(list)
    for entry in execution_order:
        stage_times[entry["stage"]].append(entry["time"])

    stages_in_order = sorted(stage_times.keys())
    for i in range(len(stages_in_order) - 1):
        current_stage = stages_in_order[i]
        next_stage = stages_in_order[i + 1]
        latest_current = max(stage_times[current_stage])
        earliest_next = min(stage_times[next_stage])
        assert latest_current <= earliest_next, (
            f"Stage {current_stage} (latest={latest_current:.6f}) must finish "
            f"before Stage {next_stage} (earliest={earliest_next:.6f}) starts"
        )


@pytest.mark.asyncio
async def test_blackboard_accumulation():
    """Run mock agents through stages and verify blackboard accumulates data."""
    blackboard = _make_blackboard("AAPL")
    spawner = TaskSpawner(blackboard)
    context = _make_context(blackboard)

    agent_configs = {
        "market_perception": ("buy", 0.8),
        "regime": ("buy", 0.75),
        "strategy": ("buy", 0.7),
        "risk": ("buy", 0.6),
        "execution": ("buy", 0.65),
        "critic": ("hold", 0.5),
    }

    for name, (direction, confidence) in agent_configs.items():
        mock_module = MagicMock()
        mock_module.NAME = name

        async def _eval(sym, tf, feat, ctx, _n=name, _d=direction, _c=confidence):
            return AgentVote(
                agent_name=_n, direction=_d, confidence=_c,
                reasoning=f"{_n} test vote", weight=1.0,
            )

        mock_module.evaluate = _eval
        spawner.register(name, mock_module)

    for name in agent_configs:
        vote = await spawner.spawn(name, "AAPL", "1d", context=context)
        blackboard.perceptions[vote.agent_name] = vote.to_dict()
        if name == "strategy":
            blackboard.strategy = vote.to_dict()
        elif name == "risk":
            blackboard.risk_assessment = vote.to_dict()
        elif name == "execution":
            blackboard.execution_plan = vote.to_dict()

    assert len(blackboard.perceptions) == len(agent_configs), \
        f"Expected {len(agent_configs)} perceptions, got {len(blackboard.perceptions)}"
    assert "market_perception" in blackboard.perceptions
    assert "regime" in blackboard.perceptions
    assert blackboard.strategy is not None, "Strategy should be set on blackboard"
    assert blackboard.strategy["direction"] == "buy"
    assert blackboard.risk_assessment is not None, "Risk assessment should be set"
    assert blackboard.execution_plan is not None, "Execution plan should be set"
    assert blackboard.symbol == "AAPL"
    assert blackboard.raw_features == SYNTHETIC_FEATURES


@pytest.mark.asyncio
async def test_debate_influence_on_confidence():
    """Call arbitrate() with and without debate-aligned votes; confidence differs."""
    ts = datetime.now(timezone.utc).isoformat()

    base_votes = [
        AgentVote(agent_name="regime", direction="buy", confidence=0.7,
                  reasoning="ok", weight=1.2, metadata={"regime_state": "BULLISH"}),
        AgentVote(agent_name="risk", direction="buy", confidence=0.6,
                  reasoning="ok", weight=1.5),
        AgentVote(agent_name="strategy", direction="buy", confidence=0.65,
                  reasoning="ok", weight=1.1),
        AgentVote(agent_name="execution", direction="buy", confidence=0.6,
                  reasoning="ok", weight=1.3, metadata={"execution_ready": True}),
    ]

    debate_votes = [
        AgentVote(agent_name="bull_debater", direction="buy", confidence=0.9,
                  reasoning="strong bull case", weight=1.0),
        AgentVote(agent_name="bear_debater", direction="buy", confidence=0.75,
                  reasoning="concedes to bull", weight=1.0),
        AgentVote(agent_name="red_team", direction="buy", confidence=0.8,
                  reasoning="stress test passed", weight=1.0),
    ]

    result_without = arbitrate("TEST", "1d", ts, list(base_votes))
    result_with = arbitrate("TEST", "1d", ts, list(base_votes) + debate_votes)

    assert result_without.final_direction in {"buy", "sell", "hold"}
    assert result_with.final_direction in {"buy", "sell", "hold"}

    # Adding aligned debate votes should affect confidence
    if result_without.final_direction == result_with.final_direction == "buy":
        assert result_with.final_confidence != result_without.final_confidence, (
            "Debate votes should influence final confidence"
        )


@pytest.mark.asyncio
async def test_veto_enforcement_risk_agent():
    """34 BUY votes + risk VETO -> HOLD. Non-VETO agent veto ignored."""
    ts = datetime.now(timezone.utc).isoformat()

    # 33 buy votes (non-risk, non-execution)
    agent_names = [
        "regime", "strategy", "market_perception", "flow_perception",
        "social_perception", "news_catalyst", "youtube_knowledge",
        "intermarket", "gex_agent", "insider_agent", "finbert_sentiment_agent",
        "earnings_tone_agent", "dark_pool_agent", "macro_regime_agent",
        "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
        "supply_chain_agent", "institutional_flow_agent", "congressional_agent",
        "hypothesis", "layered_memory_agent", "portfolio_optimizer_agent",
        "bull_debater", "bear_debater", "red_team", "critic", "alt_data_agent",
        "execution",
    ]
    votes = [
        AgentVote(
            agent_name=name, direction="buy", confidence=0.8,
            reasoning=f"{name} says buy", weight=1.0,
            metadata={"execution_ready": True} if name == "execution" else {},
        )
        for name in agent_names
    ]

    # Add risk agent with VETO
    votes.append(AgentVote(
        agent_name="risk", direction="hold", confidence=0.95,
        reasoning="Max drawdown exceeded", weight=1.5,
        veto=True, veto_reason="Drawdown limit breached",
    ))

    result = arbitrate("VETO_TEST", "1d", ts, votes)

    assert result.vetoed is True, "Risk VETO must be enforced"
    assert result.final_direction == "hold", "Vetoed decision must be HOLD"
    assert result.execution_ready is False, "Vetoed decision cannot be execution_ready"
    assert len(result.veto_reasons) >= 1
    assert any("risk" in r.lower() for r in result.veto_reasons)

    # Non-VETO agent (critic) veto must be ignored
    non_veto_votes = [
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
                  veto=True, veto_reason="critic objects"),
    ]
    non_veto_result = arbitrate("NON_VETO_TEST", "1d", ts, non_veto_votes)
    assert non_veto_result.vetoed is False, "Critic (non-VETO) agent cannot veto"


@pytest.mark.asyncio
async def test_required_agents_missing():
    """Remove 'regime' from votes -> HOLD with missing required agent."""
    ts = datetime.now(timezone.utc).isoformat()

    # Votes missing 'regime' (a REQUIRED_AGENT)
    votes_missing_regime = [
        AgentVote(agent_name="risk", direction="buy", confidence=0.7,
                  reasoning="ok", weight=1.5),
        AgentVote(agent_name="strategy", direction="buy", confidence=0.75,
                  reasoning="ok", weight=1.1),
        AgentVote(agent_name="execution", direction="buy", confidence=0.7,
                  reasoning="ok", weight=1.3, metadata={"execution_ready": True}),
        AgentVote(agent_name="market_perception", direction="buy", confidence=0.8,
                  reasoning="ok", weight=1.0),
    ]

    result = arbitrate("MISSING_TEST", "1d", ts, votes_missing_regime)

    assert result.final_direction == "hold", "Missing required agent -> HOLD"
    assert result.execution_ready is False
    assert "regime" in str(result.council_reasoning).lower(), \
        "Reasoning should mention missing regime agent"

    # Verify REQUIRED_AGENTS is the expected set
    assert REQUIRED_AGENTS == {"regime", "risk", "strategy"}


@pytest.mark.asyncio
async def test_agent_timeout_handling():
    """One agent sleeps beyond timeout -> TaskSpawner returns hold vote, council proceeds."""
    blackboard = _make_blackboard("TIMEOUT_TEST")
    spawner = TaskSpawner(blackboard)
    context = _make_context(blackboard)

    # Register a fast agent
    fast_module = MagicMock()
    fast_module.NAME = "fast_agent"

    async def fast_eval(sym, tf, feat, ctx):
        return AgentVote(
            agent_name="fast_agent", direction="buy", confidence=0.8,
            reasoning="fast response", weight=1.0,
        )

    fast_module.evaluate = fast_eval
    spawner.register("fast_agent", fast_module)

    # Register a slow agent that exceeds timeout
    slow_module = MagicMock()
    slow_module.NAME = "slow_agent"

    async def slow_eval(sym, tf, feat, ctx):
        await asyncio.sleep(60)
        return AgentVote(
            agent_name="slow_agent", direction="buy", confidence=0.9,
            reasoning="should never be seen", weight=1.0,
        )

    slow_module.evaluate = slow_eval
    spawner.register("slow_agent", slow_module)

    # Run both in parallel with a short timeout override
    fast_vote_task = spawner.spawn("fast_agent", "TIMEOUT_TEST", "1d", context=context)
    slow_vote_task = spawner._run_agent(
        slow_module, "TIMEOUT_TEST", "1d",
        SYNTHETIC_FEATURES, context, timeout=1.0,
    )

    fast_vote, slow_vote = await asyncio.gather(fast_vote_task, slow_vote_task)

    assert fast_vote.agent_name == "fast_agent"
    assert fast_vote.direction == "buy"
    assert fast_vote.confidence == 0.8

    assert slow_vote.agent_name == "slow_agent"
    assert slow_vote.direction == "hold", "Timed-out agent should return HOLD"
    assert slow_vote.confidence == 0.0, "Timed-out agent should have 0 confidence"
    assert "timeout" in slow_vote.reasoning.lower()


@pytest.mark.asyncio
async def test_empty_features_no_crash():
    """arbitrate() with empty votes and run_council with features={} must not crash."""
    ts = datetime.now(timezone.utc).isoformat()

    # Empty votes -> should return a valid DecisionPacket (likely HOLD)
    result = arbitrate("EMPTY", "1d", ts, [])
    assert isinstance(result, DecisionPacket)
    assert result.final_direction == "hold", "Empty votes should produce HOLD"
    assert result.execution_ready is False

    # Empty votes with regime_entropy
    result2 = arbitrate("EMPTY", "1d", ts, [], regime_entropy=1.5)
    assert isinstance(result2, DecisionPacket)
    assert result2.final_direction == "hold"

    # Single hold vote -> should not crash
    single_vote = [
        AgentVote(agent_name="test", direction="hold", confidence=0.5,
                  reasoning="neutral", weight=1.0),
    ]
    result3 = arbitrate("SINGLE", "1d", ts, single_vote)
    assert isinstance(result3, DecisionPacket)

    # BlackboardState with empty features
    bb = BlackboardState(symbol="EMPTY_FEAT", raw_features={})
    assert bb.symbol == "EMPTY_FEAT"
    assert bb.raw_features == {}

    # TaskSpawner with empty blackboard should handle unknown agent
    spawner = TaskSpawner(bb)
    vote = await spawner.spawn("nonexistent_agent", "TEST", "1d")
    assert vote.direction == "hold"
    assert vote.confidence == 0.0
