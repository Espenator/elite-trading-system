"""Tests for homeostasis monitor."""
import pytest
from app.council.homeostasis import HomeostasisMonitor


class TestHomeostasisMonitor:
    def test_default_mode_normal(self):
        h = HomeostasisMonitor()
        assert h.get_mode() == "NORMAL"
        assert h.get_position_scale() == 1.0

    def test_compute_mode_aggressive(self):
        h = HomeostasisMonitor()
        mode = h._compute_mode({"risk_score": 85, "trading_allowed": True})
        assert mode == "AGGRESSIVE"

    def test_compute_mode_defensive(self):
        h = HomeostasisMonitor()
        mode = h._compute_mode({"risk_score": 40, "trading_allowed": True})
        assert mode == "DEFENSIVE"

    def test_compute_mode_halted_low_risk(self):
        h = HomeostasisMonitor()
        mode = h._compute_mode({"risk_score": 20, "trading_allowed": True})
        assert mode == "HALTED"

    def test_compute_mode_halted_drawdown(self):
        h = HomeostasisMonitor()
        mode = h._compute_mode({"risk_score": 60, "drawdown_breached": True, "trading_allowed": True})
        assert mode == "HALTED"

    def test_compute_mode_halted_trading_disabled(self):
        h = HomeostasisMonitor()
        mode = h._compute_mode({"risk_score": 70, "trading_allowed": False})
        assert mode == "HALTED"

    def test_position_scale_mapping(self):
        h = HomeostasisMonitor()
        h._mode = "AGGRESSIVE"
        assert h.get_position_scale() == 1.5
        h._mode = "NORMAL"
        assert h.get_position_scale() == 1.0
        h._mode = "DEFENSIVE"
        assert h.get_position_scale() == 0.5
        h._mode = "HALTED"
        assert h.get_position_scale() == 0.0

    def test_directive_regime_mapping(self):
        h = HomeostasisMonitor()
        h._mode = "AGGRESSIVE"
        assert h.get_directive_regime() == "bullish"
        h._mode = "DEFENSIVE"
        assert h.get_directive_regime() == "bearish"
        h._mode = "NORMAL"
        assert h.get_directive_regime() == "unknown"

    def test_get_status(self):
        h = HomeostasisMonitor()
        status = h.get_status()
        assert "mode" in status
        assert "position_scale" in status
        assert "directive_regime" in status
        assert "vitals" in status
