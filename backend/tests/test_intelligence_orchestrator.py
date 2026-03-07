"""Tests for intelligence_orchestrator.py — Bug 12 verification + Bug 19 coverage.

Tests the IntelligenceOrchestrator: singleton, feature summary builder,
and prepare_intelligence_package with mocked external services.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.intelligence_orchestrator import (
    IntelligenceOrchestrator,
    get_intelligence_orchestrator,
)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_returns_instance(self):
        orch = get_intelligence_orchestrator()
        assert isinstance(orch, IntelligenceOrchestrator)

    def test_singleton_returns_same_instance(self):
        a = get_intelligence_orchestrator()
        b = get_intelligence_orchestrator()
        assert a is b


# ---------------------------------------------------------------------------
# Feature summary builder
# ---------------------------------------------------------------------------

class TestFeatureSummary:
    def test_build_feature_summary_basic(self):
        orch = IntelligenceOrchestrator()
        features = {
            "symbol": "AAPL",
            "features": {
                "rsi_14": 55.3,
                "macd": 1.2,
                "sma_20": 178.5,
                "sma_50": 175.0,
                "sma_200": 170.0,
                "atr_14": 3.5,
                "volume": 45000000,
            }
        }
        result = orch._build_feature_summary(features, "BULLISH")
        assert "AAPL" in result
        assert "BULLISH" in result
        assert "rsi_14" in result
        assert "macd" in result

    def test_build_feature_summary_missing_features(self):
        """Missing features should not crash."""
        orch = IntelligenceOrchestrator()
        features = {"symbol": "TSLA"}
        result = orch._build_feature_summary(features, "UNKNOWN")
        assert "TSLA" in result
        assert "UNKNOWN" in result

    def test_build_feature_summary_nested(self):
        """Features can be at top level or nested under 'features' key."""
        orch = IntelligenceOrchestrator()
        features = {
            "rsi_14": 65.0,
            "adx_14": 30.0,
        }
        result = orch._build_feature_summary(features, "NEUTRAL")
        assert "rsi_14" in result


# ---------------------------------------------------------------------------
# prepare_intelligence_package (mocked external calls)
# ---------------------------------------------------------------------------

class TestPrepareIntelligencePackage:
    @pytest.mark.anyio
    async def test_returns_package_structure(self):
        """Package should have required keys even when all services fail."""
        orch = IntelligenceOrchestrator()
        with patch("app.services.intelligence_orchestrator.settings") as mock_settings:
            mock_settings.PERPLEXITY_API_KEY = ""
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_ROUTER_ENABLED = False

            package = await orch.prepare_intelligence_package(
                symbol="AAPL",
                features={"features": {"rsi_14": 50}},
                regime="NEUTRAL",
            )

        assert "symbol" in package
        assert package["symbol"] == "AAPL"
        assert "regime" in package
        assert "gathered_at" in package
        assert "tiers_queried" in package
        assert "errors" in package
        assert "total_latency_ms" in package

    @pytest.mark.anyio
    async def test_graceful_failure_on_social_error(self):
        """Social sentiment failure should not crash the package."""
        orch = IntelligenceOrchestrator()
        with patch("app.services.intelligence_orchestrator.settings") as mock_settings:
            mock_settings.PERPLEXITY_API_KEY = ""
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_ROUTER_ENABLED = False

            package = await orch.prepare_intelligence_package(
                symbol="AAPL",
                regime="NEUTRAL",
            )

        assert isinstance(package, dict)
        assert package["symbol"] == "AAPL"

    @pytest.mark.anyio
    async def test_latency_is_recorded(self):
        """total_latency_ms should be a positive number."""
        orch = IntelligenceOrchestrator()
        with patch("app.services.intelligence_orchestrator.settings") as mock_settings:
            mock_settings.PERPLEXITY_API_KEY = ""
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_ROUTER_ENABLED = False

            package = await orch.prepare_intelligence_package("SPY", regime="NEUTRAL")

        assert package["total_latency_ms"] >= 0


# ---------------------------------------------------------------------------
# validate_pattern_with_context
# ---------------------------------------------------------------------------

class TestValidatePattern:
    @pytest.mark.anyio
    async def test_returns_validation_dict(self):
        """Even with mocked services, should return a validation dict."""
        orch = IntelligenceOrchestrator()

        with patch("app.services.intelligence_orchestrator.get_perplexity_intel") as mock_intel, \
             patch("app.services.intelligence_orchestrator.get_claude_reasoning") as mock_claude:

            mock_intel_instance = MagicMock()
            mock_intel_instance.search_pattern_context = AsyncMock(return_value={
                "data": {"confidence": 70}
            })
            mock_intel.return_value = mock_intel_instance

            mock_claude_instance = MagicMock()
            mock_claude_instance.pattern_interpretation = AsyncMock(return_value={
                "data": {"confidence": 80}
            })
            mock_claude.return_value = mock_claude_instance

            result = await orch.validate_pattern_with_context(
                symbol="AAPL",
                pattern="bull_flag",
                features={"rsi_14": 55},
            )

        assert "symbol" in result
        assert result["symbol"] == "AAPL"
        assert "pattern" in result
        assert "combined_confidence" in result
        # Combined = 70*0.4 + 80*0.6 = 76
        assert abs(result["combined_confidence"] - 76.0) < 0.01
