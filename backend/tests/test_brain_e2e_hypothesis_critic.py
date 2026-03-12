"""E2E tests: hypothesis and critic agents with brain service (mocked).

Covers: success path, timeout, malformed response, fallback. Ensures
timeouts/failures do not crash the council and logging metadata indicates
LLM-backed vs fallback-based inference.
"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.council.schemas import AgentVote


class TestHypothesisAgentE2E:
    """Hypothesis agent: success, timeout, malformed, fallback; no crash."""

    @pytest.mark.anyio
    async def test_hypothesis_success_llm_backed(self):
        from app.council.agents import hypothesis_agent

        with patch("app.services.brain_client.get_brain_client") as m:
            client = m.return_value
            client.enabled = True
            client.infer = AsyncMock(
                return_value={
                    "direction": "buy",
                    "confidence": 0.7,
                    "reasoning": "Strong momentum.",
                    "summary": "Bullish.",
                    "risk_flags": [],
                    "reasoning_bullets": ["RSI", "Volume"],
                    "supporting_signals": ["breakout"],
                    "invalidation_notes": ["break 50d"],
                    "error": "",
                }
            )
            vote = await hypothesis_agent.evaluate(
                "AAPL", "1d", {"features": {"regime": "bullish", "rsi_14": 30}}, {}
            )
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "hypothesis"
        assert vote.direction == "buy"
        assert vote.confidence == 0.7
        assert vote.metadata.get("inference_source") == "brain_llm"

    @pytest.mark.anyio
    async def test_hypothesis_timeout_uses_fallback_no_crash(self):
        from app.council.agents import hypothesis_agent

        with patch("app.services.brain_client.get_brain_client") as m:
            client = m.return_value
            client.enabled = True
            client.infer = AsyncMock(
                return_value={
                    "direction": "hold",
                    "reasoning": "Timeout",
                    "summary": "Timeout",
                    "confidence": 0.1,
                    "risk_flags": ["timeout"],
                    "reasoning_bullets": [],
                    "supporting_signals": [],
                    "invalidation_notes": [],
                    "error": "timeout",
                    "degraded_mode": True,
                }
            )
            vote = await hypothesis_agent.evaluate(
                "AAPL", "1d", {"features": {"regime": "neutral", "rsi_14": 50}}, {}
            )
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "hypothesis"
        assert vote.direction in ("buy", "sell", "hold")
        assert vote.confidence <= 0.25
        assert vote.metadata.get("inference_source") == "fallback"

    @pytest.mark.anyio
    async def test_hypothesis_malformed_response_validator_safe(self):
        from app.council.agents import hypothesis_agent

        with patch("app.services.brain_client.get_brain_client") as m:
            client = m.return_value
            client.enabled = True
            # Malformed: invalid direction and high confidence; validator coerces
            client.infer = AsyncMock(
                return_value={
                    "direction": "INVALID",
                    "confidence": 2.0,
                    "reasoning": "x",
                    "summary": "x",
                    "risk_flags": [],
                    "error": "",
                }
            )
            vote = await hypothesis_agent.evaluate(
                "AAPL", "1d", {"features": {"regime": "bullish", "rsi_14": 45}}, {}
            )
        assert isinstance(vote, AgentVote)
        assert vote.direction in ("buy", "sell", "hold")
        assert 0.0 <= vote.confidence <= 1.0

    @pytest.mark.anyio
    async def test_hypothesis_exception_uses_fallback_no_crash(self):
        from app.council.agents import hypothesis_agent

        with patch("app.services.brain_client.get_brain_client") as m:
            m.return_value.enabled = True
            m.return_value.infer = AsyncMock(side_effect=RuntimeError("grpc error"))
            vote = await hypothesis_agent.evaluate(
                "AAPL", "1d", {"features": {"rsi_14": 50}}, {}
            )
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "hypothesis"
        assert vote.metadata.get("inference_source") == "fallback"


class TestCriticAgentE2E:
    """Critic agent: post-trade success, fallback; no crash."""

    @pytest.mark.anyio
    async def test_critic_post_trade_success_llm_backed(self):
        from app.council.agents import critic_agent

        ctx = {
            "post_trade": True,
            "trade_outcome": {
                "trade_id": "t-1",
                "direction": "buy",
                "r_multiple": 1.5,
                "pnl": 150.0,
                "entry_price": 100.0,
                "exit_price": 101.5,
                "confidence": 0.7,
            },
            "blackboard": None,
            "all_votes": [],
        }
        with patch("app.services.brain_client.get_brain_client") as m:
            client = m.return_value
            client.enabled = True
            client.critic = AsyncMock(
                return_value={
                    "analysis": "Good trade.",
                    "lessons": ["Hold winners"],
                    "performance_score": 0.8,
                    "key_takeaways": ["R-multiple positive"],
                    "error": "",
                }
            )
            vote = await critic_agent.evaluate("AAPL", "1d", {"features": {}}, ctx)
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "critic"
        assert vote.metadata.get("inference_source") == "brain_pc2"

    @pytest.mark.anyio
    async def test_critic_post_trade_brain_timeout_fallback_no_crash(self):
        from app.council.agents import critic_agent

        ctx = {
            "post_trade": True,
            "trade_outcome": {
                "trade_id": "t-2",
                "r_multiple": 0.5,
                "pnl": -50.0,
            },
            "blackboard": None,
        }
        with patch("app.services.brain_client.get_brain_client") as m:
            client = m.return_value
            client.enabled = True
            client.critic = AsyncMock(
                return_value={"analysis": "", "lessons": [], "performance_score": 0.0, "error": "timeout"}
            )
            vote = await critic_agent.evaluate("AAPL", "1d", {"features": {}}, ctx)
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "critic"
        assert vote.metadata.get("post_trade") is True

    @pytest.mark.anyio
    async def test_critic_pre_trade_skips_returns_hold(self):
        from app.council.agents import critic_agent

        vote = await critic_agent.evaluate(
            "AAPL", "1d", {"features": {}}, {"post_trade": False}
        )
        assert isinstance(vote, AgentVote)
        assert vote.direction == "hold"
        assert vote.metadata.get("post_trade") is False
