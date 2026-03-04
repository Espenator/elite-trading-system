"""Tests for Multi-LLM Intelligence Layer.

Tests the LLM Router, Perplexity Intelligence, Claude Reasoning,
Intelligence Orchestrator, and modified council agent integrations.
"""
import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm_router import (
    LLMRouter, LLMResponse, Tier, TASK_TIER_MAP,
    ProviderCircuitBreaker, AsyncRateLimiter, get_llm_router,
)
from app.services.perplexity_intelligence import PerplexityIntelligence, _parse_json_safe
from app.services.claude_reasoning import ClaudeReasoning
from app.services.intelligence_orchestrator import IntelligenceOrchestrator


# ── LLM Router Tests ─────────────────────────────────────────────────────────

class TestLLMRouter:
    """Test LLM Router core functionality."""

    def test_tier_enum(self):
        assert Tier.BRAINSTEM.value == "brainstem"
        assert Tier.CORTEX.value == "cortex"
        assert Tier.DEEP_CORTEX.value == "deep_cortex"

    def test_task_tier_mapping(self):
        assert TASK_TIER_MAP["regime_classification"] == Tier.BRAINSTEM
        assert TASK_TIER_MAP["news_analysis"] == Tier.CORTEX
        assert TASK_TIER_MAP["strategy_critic"] == Tier.DEEP_CORTEX

    def test_get_tier_for_task(self):
        router = LLMRouter()
        assert router.get_tier_for_task("regime_classification") == Tier.BRAINSTEM
        assert router.get_tier_for_task("news_analysis") == Tier.CORTEX
        assert router.get_tier_for_task("deep_postmortem") == Tier.DEEP_CORTEX
        # Unknown tasks default to brainstem
        assert router.get_tier_for_task("unknown_task") == Tier.BRAINSTEM

    def test_router_status(self):
        router = LLMRouter()
        status = router.get_status()
        assert "tiers" in status
        assert "brainstem" in status["tiers"]
        assert "cortex" in status["tiers"]
        assert "deep_cortex" in status["tiers"]
        assert "stats" in status

    def test_singleton(self):
        import app.services.llm_router as mod
        mod._router = None
        r1 = get_llm_router()
        r2 = get_llm_router()
        assert r1 is r2
        mod._router = None


class TestProviderCircuitBreaker:
    """Test per-provider circuit breaker."""

    def test_initially_closed(self):
        cb = ProviderCircuitBreaker()
        assert not cb.is_open()

    def test_opens_after_threshold(self):
        cb = ProviderCircuitBreaker(failure_threshold=3, failure_window=60, recovery_timeout=300)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open()
        cb.record_failure()
        assert cb.is_open()

    def test_success_resets(self):
        cb = ProviderCircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()
        cb.record_success()
        assert not cb.is_open()

    def test_recovery_timeout(self):
        cb = ProviderCircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()
        time.sleep(0.02)
        assert not cb.is_open()


class TestAsyncRateLimiter:
    """Test async rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_within_burst(self):
        limiter = AsyncRateLimiter(rate=10, burst=5)
        for _ in range(5):
            assert await limiter.acquire(timeout=1)

    @pytest.mark.asyncio
    async def test_acquire_timeout(self):
        limiter = AsyncRateLimiter(rate=0.01, burst=1)
        assert await limiter.acquire(timeout=1)  # First succeeds
        assert not await limiter.acquire(timeout=0.05)  # Should timeout


class TestLLMRouterRouting:
    """Test actual routing with mocked providers."""

    @pytest.mark.asyncio
    async def test_route_brainstem(self):
        router = LLMRouter()
        mock_response = ("test response", "llama3.2", 10, 20, [])
        with patch.object(router, "_call_tier", new_callable=AsyncMock, return_value=mock_response):
            result = await router.route(
                Tier.BRAINSTEM,
                [{"role": "user", "content": "test"}],
                task="test",
            )
        assert result.content == "test response"
        assert result.tier == "brainstem"
        assert not result.error

    @pytest.mark.asyncio
    async def test_route_error_records_failure(self):
        router = LLMRouter()
        with patch.object(router, "_call_tier", new_callable=AsyncMock, side_effect=RuntimeError("fail")):
            result = await router.route(
                Tier.BRAINSTEM,
                [{"role": "user", "content": "test"}],
                task="test",
            )
        assert result.error == "fail"
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_route_with_fallback(self):
        router = LLMRouter()
        call_count = 0

        async def mock_call(tier, messages, temp, max_tok, json_mode, timeout):
            nonlocal call_count
            call_count += 1
            if tier == Tier.BRAINSTEM:
                raise RuntimeError("brainstem down")
            return ("fallback response", "sonar-pro", 10, 20, [])

        with patch.object(router, "_call_tier", side_effect=mock_call):
            result = await router.route_with_fallback(
                Tier.BRAINSTEM,
                [{"role": "user", "content": "test"}],
                task="test",
            )
        assert result.content == "fallback response"
        assert result.fallback_used

    @pytest.mark.asyncio
    async def test_parallel_query(self):
        router = LLMRouter()
        mock_response = ("parallel response", "llama3.2", 10, 20, [])
        with patch.object(router, "_call_tier", new_callable=AsyncMock, return_value=mock_response):
            results = await router.parallel_query([
                {"tier": "brainstem", "messages": [{"role": "user", "content": "q1"}], "task": "t1"},
                {"tier": "brainstem", "messages": [{"role": "user", "content": "q2"}], "task": "t2"},
            ])
        assert len(results) == 2
        assert all(r.content == "parallel response" for r in results)


# ── JSON Parser Tests ─────────────────────────────────────────────────────────

class TestJsonParser:
    def test_direct_json(self):
        result = _parse_json_safe('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_json(self):
        result = _parse_json_safe('Here is the result:\n```json\n{"score": 85}\n```')
        assert result == {"score": 85}

    def test_embedded_json(self):
        result = _parse_json_safe('Analysis complete. {"direction": "buy"} is the verdict.')
        assert result == {"direction": "buy"}

    def test_no_json(self):
        result = _parse_json_safe("No JSON here")
        assert result is None

    def test_empty(self):
        result = _parse_json_safe("")
        assert result is None


# ── Perplexity Intelligence Tests ─────────────────────────────────────────────

class TestPerplexityIntelligence:
    """Test Perplexity intelligence methods."""

    @pytest.mark.asyncio
    async def test_scan_breaking_news(self):
        intel = PerplexityIntelligence()
        mock_result = LLMResponse(
            content='{"symbol": "AAPL", "headlines": [], "overall_sentiment": "bullish", "catalyst_score": 75}',
            tier="cortex", model="sonar-pro", task="breaking_news",
            latency_ms=500, citations=["https://example.com"],
        )
        with patch("app.services.perplexity_intelligence.get_llm_router") as mock_router:
            mock_router.return_value.route_with_fallback = AsyncMock(return_value=mock_result)
            result = await intel.scan_breaking_news("AAPL")
        assert result["task"] == "breaking_news"
        assert result["symbol"] == "AAPL"
        assert result["data"]["overall_sentiment"] == "bullish"

    @pytest.mark.asyncio
    async def test_scan_fear_greed(self):
        intel = PerplexityIntelligence()
        mock_result = LLMResponse(
            content='{"fear_greed_value": 45, "vix_level": 18.5}',
            tier="cortex", model="sonar-pro", task="fear_greed_context",
            latency_ms=400,
        )
        with patch("app.services.perplexity_intelligence.get_llm_router") as mock_router:
            mock_router.return_value.route_with_fallback = AsyncMock(return_value=mock_result)
            result = await intel.get_fear_greed_context()
        assert result["task"] == "fear_greed_context"
        assert result["data"]["fear_greed_value"] == 45

    @pytest.mark.asyncio
    async def test_error_handling(self):
        intel = PerplexityIntelligence()
        mock_result = LLMResponse(
            content="", tier="cortex", model="", task="breaking_news",
            latency_ms=0, error="all_tiers_exhausted",
        )
        with patch("app.services.perplexity_intelligence.get_llm_router") as mock_router:
            mock_router.return_value.route_with_fallback = AsyncMock(return_value=mock_result)
            result = await intel.scan_breaking_news("AAPL")
        assert "error" in result


# ── Claude Reasoning Tests ────────────────────────────────────────────────────

class TestClaudeReasoning:
    """Test Claude deep reasoning methods."""

    @pytest.mark.asyncio
    async def test_strategy_critic(self):
        reasoning = ClaudeReasoning()
        mock_result = LLMResponse(
            content='{"grade": "B+", "strengths": ["good entry"], "weaknesses": ["slow exit"], "confidence": 78}',
            tier="deep_cortex", model="claude-sonnet-4-20250514", task="strategy_critic",
            latency_ms=3000,
        )
        with patch("app.services.claude_reasoning.get_llm_router") as mock_router:
            mock_router.return_value.route_with_fallback = AsyncMock(return_value=mock_result)
            result = await reasoning.strategy_critic({"name": "test_strategy"})
        assert result["task"] == "strategy_critic"
        assert result["data"]["grade"] == "B+"

    @pytest.mark.asyncio
    async def test_deep_postmortem(self):
        reasoning = ClaudeReasoning()
        mock_result = LLMResponse(
            content='{"entry_quality": "good", "overall_score": 72, "key_takeaway": "Timing was off"}',
            tier="deep_cortex", model="claude-sonnet-4-20250514", task="deep_postmortem",
            latency_ms=5000,
        )
        with patch("app.services.claude_reasoning.get_llm_router") as mock_router:
            mock_router.return_value.route_with_fallback = AsyncMock(return_value=mock_result)
            result = await reasoning.deep_postmortem(
                trade={"symbol": "AAPL", "pnl": -50},
            )
        assert result["data"]["overall_score"] == 72

    @pytest.mark.asyncio
    async def test_error_propagation(self):
        reasoning = ClaudeReasoning()
        mock_result = LLMResponse(
            content="", tier="deep_cortex", model="", task="strategy_critic",
            latency_ms=0, error="api_error",
        )
        with patch("app.services.claude_reasoning.get_llm_router") as mock_router:
            mock_router.return_value.route_with_fallback = AsyncMock(return_value=mock_result)
            result = await reasoning.strategy_critic({})
        assert "error" in result


# ── Intelligence Orchestrator Tests ───────────────────────────────────────────

class TestIntelligenceOrchestrator:
    """Test intelligence orchestrator coordination."""

    @pytest.mark.asyncio
    async def test_prepare_package_no_keys(self):
        """Without API keys, should still return a valid package."""
        orchestrator = IntelligenceOrchestrator()
        with patch("app.services.intelligence_orchestrator.settings") as mock_settings:
            mock_settings.PERPLEXITY_API_KEY = ""
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_ROUTER_ENABLED = True
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_settings.OLLAMA_MODEL = "llama3.2"

            # Mock the router to avoid real Ollama calls
            with patch("app.services.intelligence_orchestrator.get_llm_router") as mock_router:
                mock_resp = LLMResponse(
                    content='{"signal": "neutral"}', tier="brainstem",
                    model="llama3.2", task="feature_summary", latency_ms=100,
                )
                mock_router.return_value.route = AsyncMock(return_value=mock_resp)

                package = await orchestrator.prepare_intelligence_package(
                    symbol="AAPL",
                    features={"features": {"rsi_14": 55}},
                    regime="bullish",
                )

        assert package["symbol"] == "AAPL"
        assert package["regime"] == "bullish"
        assert "total_latency_ms" in package

    @pytest.mark.asyncio
    async def test_prepare_package_with_perplexity(self):
        """With Perplexity key, should query cortex tier."""
        orchestrator = IntelligenceOrchestrator()

        mock_news = {"data": {"headlines": []}, "task": "breaking_news"}
        mock_earnings = {"data": {"next_earnings_date": "2026-04-01"}, "task": "earnings_context"}
        mock_flow = {"data": {"institutional_sentiment": "neutral"}, "task": "institutional_flow"}
        mock_fg = {"data": {"fear_greed_value": 50}, "task": "fear_greed_context"}

        with patch("app.services.intelligence_orchestrator.settings") as mock_settings:
            mock_settings.PERPLEXITY_API_KEY = "test-key"
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_ROUTER_ENABLED = True
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_settings.OLLAMA_MODEL = "llama3.2"

            with patch("app.services.intelligence_orchestrator.get_perplexity_intel") as mock_intel:
                mock_instance = MagicMock()
                mock_instance.scan_breaking_news = AsyncMock(return_value=mock_news)
                mock_instance.analyze_earnings = AsyncMock(return_value=mock_earnings)
                mock_instance.get_institutional_flow = AsyncMock(return_value=mock_flow)
                mock_instance.get_fear_greed_context = AsyncMock(return_value=mock_fg)
                mock_intel.return_value = mock_instance

                with patch("app.services.intelligence_orchestrator.get_llm_router") as mock_router:
                    mock_resp = LLMResponse(
                        content='{"signal": "bullish"}', tier="brainstem",
                        model="llama3.2", task="feature_summary", latency_ms=50,
                    )
                    mock_router.return_value.route = AsyncMock(return_value=mock_resp)

                    package = await orchestrator.prepare_intelligence_package(
                        symbol="AAPL",
                        features={"features": {"rsi_14": 65}},
                        regime="bullish",
                    )

        assert "cortex" in package["tiers_queried"]
        assert package["cortex_news"] == mock_news
        assert package["cortex_earnings"] == mock_earnings

    def test_build_feature_summary(self):
        orchestrator = IntelligenceOrchestrator()
        summary = orchestrator._build_feature_summary(
            {"symbol": "AAPL", "features": {"rsi_14": 55, "macd": 0.5}},
            "bullish",
        )
        assert "AAPL" in summary
        assert "bullish" in summary
        assert "rsi_14" in summary


# ── Modified Agent Integration Tests ──────────────────────────────────────────

class TestAgentIntelligenceIntegration:
    """Test that modified agents correctly consume intelligence packages."""

    @pytest.mark.asyncio
    async def test_market_perception_with_intelligence(self):
        from app.council.agents.market_perception_agent import evaluate
        from app.council.blackboard import BlackboardState

        bb = BlackboardState(symbol="AAPL", raw_features={
            "features": {
                "return_1d": 0.02, "return_5d": 0.05, "return_20d": 0.08,
                "volume_surge_ratio": 2.0, "pct_from_20d_high": 0.01,
                "pct_from_20d_low": 0.15,
            }
        })
        bb.metadata["intelligence"] = {
            "cortex_news": {
                "data": {
                    "overall_sentiment": "bullish",
                    "catalyst_score": 75,
                }
            }
        }
        context = {"blackboard": bb}
        vote = await evaluate("AAPL", "1d", bb.raw_features, context)
        assert vote.direction == "buy"
        assert "News: bullish" in vote.reasoning

    @pytest.mark.asyncio
    async def test_regime_agent_with_fear_greed(self):
        from app.council.agents.regime_agent import evaluate
        from app.council.blackboard import BlackboardState

        bb = BlackboardState(symbol="AAPL", raw_features={
            "features": {"regime": "bullish", "regime_confidence": 0.8}
        })
        bb.metadata["intelligence"] = {
            "cortex_fear_greed": {
                "data": {
                    "fear_greed_value": 85,
                    "vix_trend": "falling",
                }
            }
        }
        context = {"blackboard": bb}
        vote = await evaluate("AAPL", "1d", bb.raw_features, context)
        assert "F&G=85" in vote.reasoning
        assert "contrarian caution" in vote.reasoning

    @pytest.mark.asyncio
    async def test_flow_perception_with_institutional(self):
        from app.council.agents.flow_perception_agent import evaluate
        from app.council.blackboard import BlackboardState

        bb = BlackboardState(symbol="AAPL", raw_features={
            "features": {
                "flow_call_volume": 10000, "flow_put_volume": 5000,
                "flow_net_premium": 500000, "flow_pcr": 0.5,
            }
        })
        bb.metadata["intelligence"] = {
            "cortex_institutional": {
                "data": {"institutional_sentiment": "accumulating"}
            }
        }
        context = {"blackboard": bb}
        vote = await evaluate("AAPL", "1d", bb.raw_features, context)
        assert "Institutional: accumulating" in vote.reasoning

    @pytest.mark.asyncio
    async def test_agents_work_without_intelligence(self):
        """Agents should work fine without intelligence package."""
        from app.council.agents.market_perception_agent import evaluate as mp_eval
        from app.council.agents.regime_agent import evaluate as r_eval

        features = {"features": {
            "return_1d": 0.01, "return_5d": 0.02, "return_20d": 0.03,
            "volume_surge_ratio": 1.0, "pct_from_20d_high": 0.05,
            "pct_from_20d_low": 0.10,
            "regime": "unknown", "regime_confidence": 0,
        }}
        context = {}

        vote1 = await mp_eval("AAPL", "1d", features, context)
        assert vote1.agent_name == "market_perception"

        vote2 = await r_eval("AAPL", "1d", features, context)
        assert vote2.agent_name == "regime"


# ── LLM Response Tests ───────────────────────────────────────────────────────

class TestLLMResponse:
    def test_to_dict(self):
        resp = LLMResponse(
            content="test", tier="brainstem", model="llama3.2",
            task="test", latency_ms=100, input_tokens=10,
            output_tokens=20, cost_usd=0.001,
        )
        d = resp.to_dict()
        assert d["content"] == "test"
        assert d["tier"] == "brainstem"
        assert d["latency_ms"] == 100
        assert d["cost_usd"] == 0.001

    def test_defaults(self):
        resp = LLMResponse(
            content="", tier="cortex", model="sonar",
            task="test", latency_ms=0,
        )
        assert resp.citations == []
        assert resp.fallback_used is False
        assert resp.error == ""
