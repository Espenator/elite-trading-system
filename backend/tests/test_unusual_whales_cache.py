"""Tests for UnusualWhales alert cache and flow_perception_agent integration."""
import pytest
import time

from app.services.unusual_whales_service import (
    update_alerts_cache,
    get_alerts_for_symbol,
    get_all_cached_alerts,
    _latest_alerts_cache,
    _cache_timestamp,
)
from app.council.agents.flow_perception_agent import evaluate


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear cache before each test."""
    import app.services.unusual_whales_service as uw_service
    uw_service._latest_alerts_cache = {}
    uw_service._cache_timestamp = 0.0
    yield
    uw_service._latest_alerts_cache = {}
    uw_service._cache_timestamp = 0.0


def test_update_alerts_cache_with_list():
    """Test cache update with list of alerts."""
    event_data = {
        "alerts": [
            {"ticker": "AAPL", "type": "bullish_sweep", "premium": 1000000},
            {"ticker": "TSLA", "type": "bearish_flow", "premium": -500000},
        ],
        "timestamp": time.time(),
    }

    update_alerts_cache(event_data)

    # Check cache was updated
    aapl_alert = get_alerts_for_symbol("AAPL")
    assert aapl_alert is not None
    assert aapl_alert["type"] == "bullish_sweep"
    assert aapl_alert["premium"] == 1000000

    tsla_alert = get_alerts_for_symbol("TSLA")
    assert tsla_alert is not None
    assert tsla_alert["type"] == "bearish_flow"


def test_update_alerts_cache_with_dict():
    """Test cache update with dict response format."""
    event_data = {
        "alerts": {
            "items": [
                {"ticker": "NVDA", "type": "unusual_call_volume", "contracts": 5000},
            ]
        },
        "timestamp": time.time(),
    }

    update_alerts_cache(event_data)

    nvda_alert = get_alerts_for_symbol("NVDA")
    assert nvda_alert is not None
    assert nvda_alert["type"] == "unusual_call_volume"
    assert nvda_alert["contracts"] == 5000


def test_get_alerts_for_symbol_returns_none_when_empty():
    """Test that get_alerts_for_symbol returns None when cache is empty."""
    alert = get_alerts_for_symbol("AAPL")
    assert alert is None


def test_get_alerts_for_symbol_returns_none_when_stale():
    """Test that get_alerts_for_symbol returns None when cache is stale (>5min)."""
    event_data = {
        "alerts": [{"ticker": "AAPL", "type": "test"}],
        "timestamp": time.time() - 301,  # 5 minutes + 1 second ago
    }

    update_alerts_cache(event_data)

    alert = get_alerts_for_symbol("AAPL")
    assert alert is None  # Too old


def test_get_all_cached_alerts():
    """Test get_all_cached_alerts returns metadata."""
    event_data = {
        "alerts": [
            {"ticker": "AAPL", "type": "test1"},
            {"ticker": "TSLA", "type": "test2"},
        ],
        "timestamp": time.time(),
    }

    update_alerts_cache(event_data)

    all_alerts = get_all_cached_alerts()
    assert all_alerts["symbol_count"] == 2
    assert "AAPL" in all_alerts["alerts"]
    assert "TSLA" in all_alerts["alerts"]
    assert all_alerts["cache_age_seconds"] is not None


@pytest.mark.asyncio
async def test_flow_perception_agent_uses_uw_cache():
    """Test that flow_perception_agent reads from UW cache."""
    # Set up cache with a bullish alert
    event_data = {
        "alerts": [{"ticker": "AAPL", "type": "bullish_sweep", "premium": 1000000}],
        "timestamp": time.time(),
    }
    update_alerts_cache(event_data)

    # Call agent with flow features
    features = {
        "flow_call_volume": 10000,
        "flow_put_volume": 5000,
        "flow_net_premium": 500000,
        "flow_pcr": 0.5,  # Bullish PCR
    }

    vote = await evaluate("AAPL", "1d", features, {})

    # Check that agent detected UW alert
    assert vote.metadata.get("unusual_whales_alert") is True
    assert vote.metadata.get("uw_alert_type") == "bullish_sweep"
    assert "UW alert" in vote.reasoning


@pytest.mark.asyncio
async def test_flow_perception_agent_without_uw_cache():
    """Test that flow_perception_agent works without UW data."""
    # No cache data

    features = {
        "flow_call_volume": 10000,
        "flow_put_volume": 5000,
        "flow_net_premium": 500000,
        "flow_pcr": 0.5,
    }

    vote = await evaluate("AAPL", "1d", features, {})

    # Check that agent works without UW alert
    assert vote.metadata.get("unusual_whales_alert", False) is False
    assert "UW alert" not in vote.reasoning


@pytest.mark.asyncio
async def test_flow_perception_agent_uw_boosts_confidence():
    """Test that matching UW alert boosts confidence."""
    # Bullish alert
    event_data = {
        "alerts": [{"ticker": "AAPL", "type": "bullish_sweep"}],
        "timestamp": time.time(),
    }
    update_alerts_cache(event_data)

    features = {
        "flow_call_volume": 10000,
        "flow_put_volume": 5000,
        "flow_net_premium": 500000,
        "flow_pcr": 0.5,  # Bullish
    }

    # Test with UW alert
    vote_with_uw = await evaluate("AAPL", "1d", features, {})

    # Clear cache and test without
    import app.services.unusual_whales_service as uw_service
    uw_service._latest_alerts_cache = {}

    vote_without_uw = await evaluate("AAPL", "1d", features, {})

    # Confidence should be higher with UW alert
    assert vote_with_uw.confidence >= vote_without_uw.confidence
