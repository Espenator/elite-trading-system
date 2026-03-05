"""Tests for data-source perception agents (social, news, youtube)."""
import pytest
from unittest.mock import patch, MagicMock
from app.council.schemas import AgentVote
from app.council.blackboard import BlackboardState


@pytest.fixture
def blackboard():
    return BlackboardState(symbol="AAPL", raw_features={"features": {"regime": "bullish"}})


@pytest.fixture
def context(blackboard):
    return {"blackboard": blackboard}


# ── Social Perception Agent ─────────────────────────────────────────


class TestSocialPerceptionAgent:
    @pytest.mark.anyio
    async def test_no_data_returns_hold(self, context):
        from app.council.agents.social_perception_agent import evaluate

        with patch("app.council.agents.social_perception_agent._fetch_social_data", return_value=[]):
            vote = await evaluate("AAPL", "1d", {"features": {}}, context)
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "social_perception"
        assert vote.direction == "hold"
        assert vote.confidence <= 0.2
        assert vote.metadata["data_available"] is False

    @pytest.mark.anyio
    async def test_bullish_data(self, context):
        from app.council.agents.social_perception_agent import evaluate

        mock_items = [
            {"source": "news_api", "ticker": "AAPL", "text": "Apple bullish surge rally beat expectations upgrade"},
            {"source": "stockgeist", "ticker": "AAPL", "text": "AAPL strong bullish breakout moon"},
        ]
        with patch("app.council.agents.social_perception_agent._fetch_social_data", return_value=mock_items):
            vote = await evaluate("AAPL", "1d", {"features": {}}, context)
        assert vote.direction == "buy"
        assert vote.confidence > 0.3
        assert vote.metadata["data_available"] is True

    @pytest.mark.anyio
    async def test_writes_to_blackboard(self, blackboard, context):
        from app.council.agents.social_perception_agent import evaluate

        mock_items = [
            {"source": "news_api", "ticker": "AAPL", "text": "strong bullish rally"},
        ]
        with patch("app.council.agents.social_perception_agent._fetch_social_data", return_value=mock_items):
            await evaluate("AAPL", "1d", {"features": {}}, context)
        assert "social_sentiment" in blackboard.metadata


# ── News Catalyst Agent ─────────────────────────────────────────────


class TestNewsCatalystAgent:
    @pytest.mark.anyio
    async def test_no_headlines_returns_hold(self, context):
        from app.council.agents.news_catalyst_agent import evaluate

        with patch("app.council.agents.news_catalyst_agent._fetch_headlines", return_value=[]):
            vote = await evaluate("AAPL", "1d", {"features": {}}, context)
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "news_catalyst"
        assert vote.direction == "hold"
        assert vote.metadata["data_available"] is False

    @pytest.mark.anyio
    async def test_bullish_catalyst_detected(self, context):
        from app.council.agents.news_catalyst_agent import evaluate

        mock_headlines = [
            {"text": "Apple FDA approval for new health monitoring device", "timestamp": "2026-03-04T12:00:00Z"},
            {"text": "Analyst upgrade: Goldman raises AAPL price target", "timestamp": "2026-03-04T11:00:00Z"},
        ]
        with patch("app.council.agents.news_catalyst_agent._fetch_headlines", return_value=mock_headlines):
            vote = await evaluate("AAPL", "1d", {"features": {}}, context)
        assert vote.direction == "buy"
        assert vote.metadata["bullish_catalysts"] >= 1

    @pytest.mark.anyio
    async def test_bearish_catalyst_detected(self, context):
        from app.council.agents.news_catalyst_agent import evaluate

        mock_headlines = [
            {"text": "SEC probe into Apple accounting practices", "timestamp": "2026-03-04T12:00:00Z"},
            {"text": "Apple earnings miss expectations, shares plunge", "timestamp": "2026-03-04T11:00:00Z"},
        ]
        with patch("app.council.agents.news_catalyst_agent._fetch_headlines", return_value=mock_headlines):
            vote = await evaluate("AAPL", "1d", {"features": {}}, context)
        assert vote.direction == "sell"
        assert vote.metadata["bearish_catalysts"] >= 1

    @pytest.mark.anyio
    async def test_no_catalysts_in_neutral_headlines(self, context):
        from app.council.agents.news_catalyst_agent import evaluate

        mock_headlines = [
            {"text": "Apple releases new MacBook model at WWDC event", "timestamp": "2026-03-04T12:00:00Z"},
        ]
        with patch("app.council.agents.news_catalyst_agent._fetch_headlines", return_value=mock_headlines):
            vote = await evaluate("AAPL", "1d", {"features": {}}, context)
        assert vote.direction == "hold"
        assert vote.metadata["bullish_catalysts"] == 0
        assert vote.metadata["bearish_catalysts"] == 0

    @pytest.mark.anyio
    async def test_writes_to_blackboard(self, blackboard, context):
        from app.council.agents.news_catalyst_agent import evaluate

        mock_headlines = [
            {"text": "Apple stock upgraded by multiple analysts", "timestamp": "2026-03-04T12:00:00Z"},
        ]
        with patch("app.council.agents.news_catalyst_agent._fetch_headlines", return_value=mock_headlines):
            await evaluate("AAPL", "1d", {"features": {}}, context)
        assert "news_catalysts" in blackboard.metadata


# ── YouTube Knowledge Agent ─────────────────────────────────────────


class TestYouTubeKnowledgeAgent:
    @pytest.mark.anyio
    async def test_no_knowledge_returns_hold(self, context):
        from app.council.agents.youtube_knowledge_agent import evaluate

        with patch("app.council.agents.youtube_knowledge_agent._get_relevant_knowledge", return_value=[]):
            vote = await evaluate("AAPL", "1d", {"features": {}}, context)
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "youtube_knowledge"
        assert vote.direction == "hold"
        assert vote.metadata["data_available"] is False

    @pytest.mark.anyio
    async def test_bullish_concepts(self, context):
        from app.council.agents.youtube_knowledge_agent import evaluate

        mock_knowledge = [
            {
                "video_id": "abc123",
                "title": "Test Video",
                "ideas": ["bullish momentum play", "buy the dip"],
                "concepts": ["breakout", "bull flag", "golden cross"],
                "symbols": ["AAPL"],
            },
        ]
        with patch("app.council.agents.youtube_knowledge_agent._get_relevant_knowledge", return_value=mock_knowledge):
            vote = await evaluate("AAPL", "1d", {"features": {}}, context)
        assert vote.direction == "buy"
        assert vote.metadata["bull_signals"] > 0

    @pytest.mark.anyio
    async def test_bearish_concepts(self, context):
        from app.council.agents.youtube_knowledge_agent import evaluate

        mock_knowledge = [
            {
                "video_id": "xyz789",
                "title": "Bear Market Warning",
                "ideas": ["bearish setup", "short opportunity"],
                "concepts": ["head and shoulders", "death cross", "breakdown"],
                "symbols": ["AAPL"],
            },
        ]
        with patch("app.council.agents.youtube_knowledge_agent._get_relevant_knowledge", return_value=mock_knowledge):
            vote = await evaluate("AAPL", "1d", {"features": {}}, context)
        assert vote.direction == "sell"
        assert vote.metadata["bear_signals"] > 0

    @pytest.mark.anyio
    async def test_writes_to_blackboard(self, blackboard, context):
        from app.council.agents.youtube_knowledge_agent import evaluate

        mock_knowledge = [
            {
                "video_id": "abc123",
                "ideas": ["breakout play"],
                "concepts": ["momentum"],
                "symbols": ["AAPL"],
            },
        ]
        with patch("app.council.agents.youtube_knowledge_agent._get_relevant_knowledge", return_value=mock_knowledge):
            await evaluate("AAPL", "1d", {"features": {}}, context)
        assert "youtube_knowledge" in blackboard.metadata
