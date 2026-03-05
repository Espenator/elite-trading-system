"""Tests for the trading directives system."""
import pytest
from pathlib import Path

from app.council.directives.loader import DirectiveLoader


@pytest.fixture
def loader():
    # Point to the actual directives directory
    directives_dir = Path(__file__).resolve().parent.parent.parent / "directives"
    return DirectiveLoader(directives_dir=directives_dir)


class TestDirectiveLoader:
    def test_load_global(self, loader):
        text = loader.load("unknown")
        assert "Global Trading Directives" in text
        assert "Circuit Breaker" in text

    def test_load_bull_regime(self, loader):
        text = loader.load("bullish")
        assert "Global Trading Directives" in text
        assert "Bull Market" in text
        assert "momentum" in text.lower()

    def test_load_bear_regime(self, loader):
        text = loader.load("bearish")
        assert "Global Trading Directives" in text
        assert "Bear Market" in text
        assert "defensive" in text.lower()

    def test_load_synonyms(self, loader):
        bull_text = loader.load("risk_on")
        assert "Bull Market" in bull_text

        bear_text = loader.load("trending_down")
        assert "Bear Market" in bear_text

    def test_load_unknown_regime_only_global(self, loader):
        text = loader.load("choppy")
        assert "Global Trading Directives" in text
        assert "Bull Market" not in text
        assert "Bear Market" not in text

    def test_get_threshold_vix(self, loader):
        val = loader.get_threshold("VIX spike threshold")
        assert val == 35.0

    def test_get_threshold_percentage(self, loader):
        val = loader.get_threshold("Daily drawdown limit")
        assert val == 0.03  # 3% -> 0.03

    def test_get_threshold_missing(self, loader):
        val = loader.get_threshold("nonexistent threshold")
        assert val is None

    def test_get_regime_bias_bull(self, loader):
        bias = loader.get_regime_bias("bullish")
        assert bias == "LONG"

    def test_get_regime_bias_bear(self, loader):
        bias = loader.get_regime_bias("bearish")
        assert bias == "DEFENSIVE"

    def test_get_regime_bias_unknown(self, loader):
        bias = loader.get_regime_bias("choppy")
        assert bias == "NEUTRAL"

    def test_cache_clear(self, loader):
        loader.load("bullish")
        assert len(loader._cache) > 0
        loader.clear_cache()
        assert len(loader._cache) == 0
