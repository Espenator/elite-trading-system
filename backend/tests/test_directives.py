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

    def test_get_directives_merged_global(self, loader):
        """Threshold loading: get_directives_merged returns parsed keys from global.md."""
        merged = loader.get_directives_merged(None)
        assert "cb_vix_spike_threshold" in merged
        assert merged["cb_vix_spike_threshold"] == 35.0
        assert merged.get("cb_daily_drawdown_limit") == 0.03
        assert merged.get("cb_max_positions") == 10
        assert merged.get("cb_flash_crash_threshold") == 0.05

    def test_get_directives_merged_regime_overlay(self, loader):
        """Regime overlay: bear/bull directives can override or add keys."""
        global_only = loader.get_directives_merged(None)
        with_regime = loader.get_directives_merged("BEARISH")
        # Global keys still present
        assert with_regime.get("cb_vix_spike_threshold") == 35.0
        # Regime file may add position scale etc. (if we add to map later)
        assert isinstance(with_regime, dict)


class TestAgentConfigUsesDirectives:
    """agent_config.get_agent_thresholds() merges directives (no more magic numbers)."""

    def test_get_agent_thresholds_includes_directive_values(self):
        from app.council.agent_config import get_agent_thresholds
        cfg = get_agent_thresholds()
        assert "cb_vix_spike_threshold" in cfg
        assert cfg["cb_vix_spike_threshold"] == 35.0
        assert cfg.get("cb_daily_drawdown_limit") == 0.03

    def test_get_agent_thresholds_accepts_regime(self):
        from app.council.agent_config import get_agent_thresholds
        cfg = get_agent_thresholds(regime="BULLISH")
        assert "cb_vix_spike_threshold" in cfg
        assert isinstance(cfg, dict)
