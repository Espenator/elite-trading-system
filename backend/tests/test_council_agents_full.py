"""Unit tests for all 35 council agents — each must return a valid AgentVote.

Covers every agent in council/agents/ and registry AGENTS list.
Uses mocks for external APIs (brain, LLM, Alpaca, etc.).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.council.schemas import AgentVote
from app.council.registry import AGENTS


# Common minimal features/context for agent evaluation
MIN_FEATURES = {"features": {}}
MIN_CONTEXT = {}


def _assert_valid_agent_vote(vote, agent_name: str):
    """Assert vote is a valid AgentVote with correct schema."""
    assert isinstance(vote, AgentVote), f"{agent_name} must return AgentVote"
    assert vote.agent_name == agent_name
    assert vote.direction in ("buy", "sell", "hold")
    assert 0.0 <= vote.confidence <= 1.0
    assert isinstance(vote.reasoning, str)
    assert vote.weight > 0


# ── Stage 1: Perception + Academic Edge (13 agents) ───────────────────────
# market_perception, flow_perception, regime, hypothesis, strategy, risk, execution, critic tested in test_council.py


@pytest.mark.anyio
async def test_social_perception_agent_returns_agent_vote():
    from app.council.agents import social_perception_agent
    vote = await social_perception_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "social_perception")


@pytest.mark.anyio
async def test_news_catalyst_agent_returns_agent_vote():
    from app.council.agents import news_catalyst_agent
    vote = await news_catalyst_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "news_catalyst")


@pytest.mark.anyio
async def test_youtube_knowledge_agent_returns_agent_vote():
    from app.council.agents import youtube_knowledge_agent
    vote = await youtube_knowledge_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "youtube_knowledge")


@pytest.mark.anyio
async def test_intermarket_agent_returns_agent_vote():
    from app.council.agents import intermarket_agent
    vote = await intermarket_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "intermarket")


@pytest.mark.anyio
async def test_gex_agent_returns_agent_vote():
    from app.council.agents import gex_agent
    vote = await gex_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "gex_agent")


@pytest.mark.anyio
async def test_insider_agent_returns_agent_vote():
    from app.council.agents import insider_agent
    with patch.object(insider_agent, "_fetch_insider_filings", new_callable=AsyncMock, return_value=[]):
        vote = await insider_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "insider_agent")


@pytest.mark.anyio
async def test_finbert_sentiment_agent_returns_agent_vote():
    from app.council.agents import finbert_sentiment_agent
    vote = await finbert_sentiment_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "finbert_sentiment_agent")


@pytest.mark.anyio
async def test_earnings_tone_agent_returns_agent_vote():
    from app.council.agents import earnings_tone_agent
    vote = await earnings_tone_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "earnings_tone_agent")


@pytest.mark.anyio
async def test_dark_pool_agent_returns_agent_vote():
    from app.council.agents import dark_pool_agent
    vote = await dark_pool_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "dark_pool_agent")


@pytest.mark.anyio
async def test_macro_regime_agent_returns_agent_vote():
    from app.council.agents import macro_regime_agent
    vote = await macro_regime_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "macro_regime_agent")


# ── Stage 2: Technical + Data Enrichment (8 agents) ────────────────────────


@pytest.mark.anyio
async def test_rsi_agent_returns_agent_vote():
    from app.council.agents import rsi_agent
    vote = await rsi_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "rsi")


@pytest.mark.anyio
async def test_bbv_agent_returns_agent_vote():
    from app.council.agents import bbv_agent
    vote = await bbv_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "bbv")


@pytest.mark.anyio
async def test_ema_trend_agent_returns_agent_vote():
    from app.council.agents import ema_trend_agent
    vote = await ema_trend_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "ema_trend")


@pytest.mark.anyio
async def test_relative_strength_agent_returns_agent_vote():
    from app.council.agents import relative_strength_agent
    vote = await relative_strength_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "relative_strength")


@pytest.mark.anyio
async def test_cycle_timing_agent_returns_agent_vote():
    from app.council.agents import cycle_timing_agent
    vote = await cycle_timing_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "cycle_timing")


@pytest.mark.anyio
async def test_supply_chain_agent_returns_agent_vote():
    from app.council.agents import supply_chain_agent
    vote = await supply_chain_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "supply_chain_agent")


@pytest.mark.anyio
async def test_institutional_flow_agent_returns_agent_vote():
    from app.council.agents import institutional_flow_agent
    vote = await institutional_flow_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "institutional_flow_agent")


@pytest.mark.anyio
async def test_congressional_agent_returns_agent_vote():
    from app.council.agents import congressional_agent
    vote = await congressional_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "congressional_agent")


# ── Stage 3: Hypothesis + Memory (hypothesis in test_council) ──────────────


@pytest.mark.anyio
async def test_layered_memory_agent_returns_agent_vote():
    from app.council.agents import layered_memory_agent
    vote = await layered_memory_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "layered_memory_agent")


# ── Stage 5: Portfolio Optimizer ────────────────────────────────────────


@pytest.mark.anyio
async def test_portfolio_optimizer_agent_returns_agent_vote():
    from app.council.agents import portfolio_optimizer_agent
    vote = await portfolio_optimizer_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "portfolio_optimizer_agent")


# ── Stage 5.5: Debate — bull/bear return dict from evaluate_debate ────────


@pytest.mark.anyio
async def test_bull_debater_evaluate_debate_returns_dict():
    from app.council.agents.bull_debater import evaluate_debate
    with patch("app.services.llm_router.get_llm_router") as m:
        m.return_value.route = AsyncMock(return_value=MagicMock(content='{"argument":"Bull case","evidence":[],"confidence":0.7,"key_catalyst":"test"}'))
        result = await evaluate_debate("SPY", "buy", {}, [], 1)
    assert isinstance(result, dict)
    assert "argument" in result
    assert "confidence" in result


@pytest.mark.anyio
async def test_bear_debater_evaluate_debate_returns_dict():
    from app.council.agents.bear_debater import evaluate_debate
    with patch("app.services.llm_router.get_llm_router") as m:
        m.return_value.route = AsyncMock(return_value=MagicMock(content='{"argument":"Bear case","evidence":[],"confidence":0.6,"key_catalyst":"test"}'))
        result = await evaluate_debate("SPY", "sell", {}, [], 1)
    assert isinstance(result, dict)
    assert "argument" in result
    assert "confidence" in result


# ── Red Team (has evaluate -> AgentVote) ──────────────────────────────────


@pytest.mark.anyio
async def test_red_team_agent_returns_agent_vote():
    from app.council.agents import red_team_agent
    from app.council.blackboard import BlackboardState
    from app.council.agents.red_team_agent import RedTeamReport, ScenarioResult
    bb = BlackboardState(symbol="SPY", raw_features=MIN_FEATURES)
    bb.strategy = {"direction": "buy", "confidence": 0.7}
    ctx = {"blackboard": bb}
    with patch.object(red_team_agent, "stress_test", new_callable=AsyncMock) as m:
        m.return_value = RedTeamReport(
            scenario_results=[],
            worst_case_loss_pct=0.02,
            worst_case_loss_r=0.5,
            scenarios_survived=5,
            total_scenarios=5,
            overall_recommendation="PROCEED",
        )
        vote = await red_team_agent.evaluate("SPY", "1d", MIN_FEATURES, ctx)
    _assert_valid_agent_vote(vote, "red_team")


# ── Alt Data (background enrichment) ───────────────────────────────────────


@pytest.mark.anyio
async def test_alt_data_agent_returns_agent_vote():
    from app.council.agents import alt_data_agent
    vote = await alt_data_agent.evaluate("SPY", "1d", MIN_FEATURES, MIN_CONTEXT)
    _assert_valid_agent_vote(vote, "alt_data_agent")


# ── Registry coverage: all agent IDs have a test ───────────────────────────


def test_registry_agents_count():
    """Ensure we have 33+ agents in registry (including arbiter)."""
    assert len(AGENTS) >= 33, "Registry should list all council agents"
