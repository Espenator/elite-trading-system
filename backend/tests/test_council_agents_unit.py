"""Unit tests for all 35 council agents — each must return a valid AgentVote (or debate dict).

Tests that each agent's evaluate() (or evaluate_debate for bull/bear) returns valid schema
without calling real APIs. Uses unittest.mock for external deps.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.council.schemas import AgentVote


# Minimal features/context for agents that don't need external data
DEFAULT_FEATURES = {"features": {"return_1d": 0.01, "return_5d": 0.02, "vix_close": 20}}
DEFAULT_CONTEXT = {}


def _agent_vote_valid(v) -> bool:
    """Check AgentVote has required fields and valid values."""
    if not isinstance(v, AgentVote):
        return False
    if v.direction not in ("buy", "sell", "hold"):
        return False
    if not (0.0 <= v.confidence <= 1.0):
        return False
    if v.weight <= 0:
        return False
    return bool(v.agent_name and v.reasoning is not None)


# ─── Agents with evaluate(symbol, timeframe, features, context) ─────────────────
# All use same signature; we patch get_agent_thresholds and external APIs per agent.

@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_market_perception_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {"return_1d_threshold": 0.005, "return_5d_threshold": 0.01,
                            "return_20d_threshold": 0.03, "volume_surge_threshold": 1.5,
                            "near_high_threshold": -0.02, "near_low_threshold": 0.02,
                            "weight_market_perception": 1.0}
    from app.council.agents.market_perception_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_flow_perception_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {"pcr_bullish_threshold": 0.7, "pcr_bearish_threshold": 1.3,
                            "weight_flow_perception": 0.8}
    from app.council.agents.flow_perception_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_regime_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {"weight_regime": 1.2}
    from app.council.agents.regime_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_social_perception_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {"social_bullish_threshold": 62, "social_bearish_threshold": 38,
                            "weight_social_perception": 0.7}
    from app.council.agents.social_perception_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_news_catalyst_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.news_catalyst_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_youtube_knowledge_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.youtube_knowledge_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_intermarket_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.intermarket_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_gex_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.gex_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_insider_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.insider_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_finbert_sentiment_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.finbert_sentiment_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_earnings_tone_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.earnings_tone_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_dark_pool_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.dark_pool_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_macro_regime_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.macro_regime_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
async def test_rsi_returns_agent_vote():
    from app.council.agents.rsi_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
async def test_bbv_returns_agent_vote():
    from app.council.agents.bbv_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_ema_trend_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.ema_trend_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
async def test_relative_strength_returns_agent_vote():
    from app.council.agents.relative_strength_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
async def test_cycle_timing_returns_agent_vote():
    from app.council.agents.cycle_timing_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_supply_chain_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.supply_chain_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_institutional_flow_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.institutional_flow_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_congressional_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.congressional_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
@patch("app.services.brain_client.get_brain_client")
async def test_hypothesis_returns_agent_vote(mock_brain, mock_cfg):
    mock_cfg.return_value = {"weight_hypothesis": 0.9}
    client = MagicMock()
    client.enabled = False
    mock_brain.return_value = client
    from app.council.agents.hypothesis_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_layered_memory_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.layered_memory_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_strategy_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {"rsi_oversold": 30, "rsi_overbought": 70,
                            "adx_trending_threshold": 25, "strategy_buy_pass_rate": 0.6,
                            "strategy_sell_pass_rate": 0.3, "weight_strategy": 1.1}
    from app.council.agents.strategy_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.api.v1.risk.drawdown_check_status", new_callable=AsyncMock)
@patch("app.api.v1.risk.risk_score", new_callable=AsyncMock)
@patch("app.council.agent_config.get_agent_thresholds")
async def test_risk_returns_agent_vote(mock_cfg, mock_risk, mock_dd):
    mock_cfg.return_value = {"risk_score_veto_threshold": 30,
                            "volatility_elevated_threshold": 0.30,
                            "volatility_extreme_threshold": 0.50,
                            "max_portfolio_heat": 0.06, "max_single_position": 0.02,
                            "weight_risk": 1.5}
    mock_risk.return_value = {"risk_score": 60}
    mock_dd.return_value = {"trading_allowed": True, "drawdown_breached": False}
    from app.council.agents.risk_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_execution_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {"min_volume_threshold": 50_000, "weight_execution": 1.3}
    from app.council.agents.execution_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_portfolio_optimizer_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.portfolio_optimizer_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agents.red_team_agent.stress_test", new_callable=AsyncMock)
async def test_red_team_returns_agent_vote(mock_stress):
    from app.council.agents.red_team_agent import evaluate, RedTeamReport, ScenarioResult
    report = RedTeamReport(
        scenario_results=[ScenarioResult("flash_crash", 0.02, 0.5, True, "PROCEED", "")],
        worst_case_loss_pct=0.02, worst_case_loss_r=0.5,
        scenarios_survived=1, total_scenarios=1, overall_recommendation="PROCEED",
    )
    mock_stress.return_value = report
    bb = MagicMock()
    bb.strategy = {"direction": "buy", "confidence": 0.7}
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, {"blackboard": bb})
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_critic_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {"critic_excellent_r": 2.0, "critic_good_r": 1.0,
                            "critic_small_loss_r": -1.0, "weight_critic": 0.5}
    from app.council.agents.critic_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


@pytest.mark.anyio
@patch("app.council.agent_config.get_agent_thresholds")
async def test_alt_data_returns_agent_vote(mock_cfg):
    mock_cfg.return_value = {}
    from app.council.agents.alt_data_agent import evaluate
    v = await evaluate("AAPL", "1d", DEFAULT_FEATURES, DEFAULT_CONTEXT)
    assert _agent_vote_valid(v)


# ─── Bull/Bear debater: evaluate_debate returns dict (used by debate_engine) ───

@pytest.mark.anyio
@patch("app.services.llm_router.get_llm_router")
async def test_bull_debater_evaluate_debate_returns_dict(mock_router):
    route_ret = MagicMock()
    route_ret.content = '{"argument": "Bull case.", "evidence": ["key1"], "confidence": 0.7, "key_catalyst": "Momentum"}'
    mock_router.return_value.route = AsyncMock(return_value=route_ret)
    from app.council.agents.bull_debater import evaluate_debate
    out = await evaluate_debate("AAPL", "buy", {"return_1d": 0.02}, [], 1)
    assert isinstance(out, dict)
    assert "argument" in out or "confidence" in out


@pytest.mark.anyio
@patch("app.services.llm_router.get_llm_router")
async def test_bear_debater_evaluate_debate_returns_dict(mock_router):
    route_ret = MagicMock()
    route_ret.content = '{"argument": "Bear case.", "evidence": ["key1"], "confidence": 0.6, "key_catalyst": "Risk"}'
    mock_router.return_value.route = AsyncMock(return_value=route_ret)
    from app.council.agents.bear_debater import evaluate_debate
    out = await evaluate_debate("AAPL", "sell", {"return_1d": -0.02}, [], 1)
    assert isinstance(out, dict)
    assert "argument" in out or "confidence" in out
