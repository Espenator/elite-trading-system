"""Tests for Production Hardening — Tasks 10-14.

Tests overfitting guard, intelligence cache, HITL gates,
data quality monitor, and shadow tracker.
"""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch

from app.council.overfitting_guard import OverfittingGuard, OverfitResult
from app.services.intelligence_cache import IntelligenceCache, CacheEntry, LATENCY_BUDGET_MS
from app.council.hitl_gate import HITLGate, HITLConfig, GateResult
from app.council.data_quality import DataQualityMonitor, DataSourceConfig
from app.council.shadow_tracker import ShadowTracker


# ── Overfitting Guard Tests ───────────────────────────────────────────────────

class TestOverfittingGuard:

    def test_insufficient_trades_warning(self):
        guard = OverfittingGuard()
        result = guard.validate_strategy(trades=[{"pnl": 10}] * 5)
        assert result.passed  # Not enough data to fail
        assert len(result.warnings) > 0
        assert "Insufficient" in result.warnings[0]

    def test_regime_stratification_pass(self):
        guard = OverfittingGuard()
        trades = []
        for regime in ["bullish", "bearish"]:
            for _ in range(15):
                trades.append({"pnl": 100, "regime": regime, "slippage_cost": 1, "commission": 1})
        result = guard.validate_strategy(trades)
        assert result.passed
        assert "regime_stratification" in result.metrics

    def test_regime_stratification_fail(self):
        guard = OverfittingGuard()
        trades = []
        # Good in bullish
        for _ in range(15):
            trades.append({"pnl": 100, "regime": "bullish", "slippage_cost": 1, "commission": 1})
        # Bad in bearish (0% win rate)
        for _ in range(15):
            trades.append({"pnl": -50, "regime": "bearish", "slippage_cost": 1, "commission": 1})
        result = guard.validate_strategy(trades)
        assert not result.passed
        assert any("bearish" in f for f in result.flags)

    def test_sample_divergence_sharpe(self):
        guard = OverfittingGuard()
        trades = [{"pnl": 10, "regime": "bullish", "slippage_cost": 0, "commission": 0}] * 40
        result = guard.validate_strategy(
            trades,
            in_sample_metrics={"sharpe": 3.0, "max_drawdown": -0.05, "win_rate": 0.7},
            out_of_sample_metrics={"sharpe": 0.5, "max_drawdown": -0.15, "win_rate": 0.45},
        )
        assert not result.passed
        assert any("Sharpe" in f for f in result.flags)

    def test_transaction_cost_survival_fail(self):
        guard = OverfittingGuard()
        trades = []
        for _ in range(40):
            trades.append({"pnl": 5, "regime": "bullish", "slippage_cost": 10, "commission": 5})
        result = guard.validate_strategy(trades)
        assert not result.passed
        assert any("costs" in f.lower() for f in result.flags)

    def test_statistical_indicators(self):
        guard = OverfittingGuard()
        trades = [{"pnl": 50, "regime": "bullish", "slippage_cost": 0, "commission": 0}] * 40
        result = guard.validate_strategy(trades)
        assert "statistical" in result.metrics
        assert result.metrics["statistical"]["trade_count"] == 40

    def test_overfit_result_to_dict(self):
        r = OverfitResult()
        r.fail("test failure")
        r.warn("test warning")
        d = r.to_dict()
        assert d["passed"] is False
        assert "test failure" in d["flags"]
        assert "test warning" in d["warnings"]


# ── Intelligence Cache Tests ──────────────────────────────────────────────────

class TestIntelligenceCache:

    def test_cache_entry_freshness(self):
        entry = CacheEntry({"test": True}, ttl=1.0)
        assert entry.freshness == "fresh"
        assert not entry.is_expired

    def test_cache_entry_expired(self):
        entry = CacheEntry({"test": True}, ttl=0.01)
        time.sleep(0.02)
        assert entry.is_expired

    def test_cache_miss(self):
        cache = IntelligenceCache()
        assert cache.get("AAPL") is None

    def test_cache_set_and_get(self):
        cache = IntelligenceCache()
        cache._symbol_cache["AAPL"] = CacheEntry({"news": "test"})
        result = cache.get("AAPL")
        assert result is not None
        assert result["news"] == "test"
        assert "_cache_freshness" in result

    def test_watchlist_management(self):
        cache = IntelligenceCache()
        cache.set_watchlist(["AAPL", "MSFT", "GOOG"])
        assert cache._watchlist == {"AAPL", "MSFT", "GOOG"}
        cache.add_symbol("TSLA")
        assert "TSLA" in cache._watchlist
        cache.remove_symbol("GOOG")
        assert "GOOG" not in cache._watchlist

    def test_latency_budgets_defined(self):
        assert "brainstem" in LATENCY_BUDGET_MS
        assert LATENCY_BUDGET_MS["brainstem"] == 500
        assert LATENCY_BUDGET_MS["cortex"] == 3000

    def test_cache_status(self):
        cache = IntelligenceCache()
        cache.set_watchlist(["AAPL"])
        cache._symbol_cache["AAPL"] = CacheEntry({"test": True})
        status = cache.get_status()
        assert "AAPL" in status["watchlist"]
        assert "AAPL" in status["cached_symbols"]
        assert status["running"] is False

    def test_market_cache(self):
        cache = IntelligenceCache()
        cache._market_cache["fear_greed"] = CacheEntry({"value": 55})
        result = cache.get_market("fear_greed")
        assert result["value"] == 55

    def test_cache_read_increments_access_count(self):
        entry = CacheEntry({"test": True})
        assert entry.access_count == 0
        entry.read()
        assert entry.access_count == 1
        entry.read()
        assert entry.access_count == 2


# ── HITL Gate Tests ───────────────────────────────────────────────────────────

class TestHITLGate:

    def test_disabled_gate_passes(self):
        config = HITLConfig(enabled=False)
        gate = HITLGate(config)
        result = gate.check({"final_direction": "buy", "final_confidence": 0.3})
        assert not result.requires_approval

    def test_hold_always_passes(self):
        gate = HITLGate()
        result = gate.check({"final_direction": "hold", "final_confidence": 0.1})
        assert not result.requires_approval

    def test_low_confidence_triggers(self):
        config = HITLConfig(min_confidence_for_auto=0.6)
        gate = HITLGate(config)
        result = gate.check({
            "final_direction": "buy", "final_confidence": 0.4,
            "council_decision_id": "test-1",
        })
        assert result.requires_approval
        assert "low_confidence" in result.gates_triggered

    def test_learning_period_triggers(self):
        config = HITLConfig(learning_period_days=30, learning_start_timestamp=time.time())
        gate = HITLGate(config)
        result = gate.check({
            "final_direction": "buy", "final_confidence": 0.8,
            "council_decision_id": "test-2",
        })
        assert result.requires_approval
        assert "learning_period" in result.gates_triggered

    def test_losing_streak_triggers(self):
        gate = HITLGate(HITLConfig(max_consecutive_losses=3))
        gate.record_outcome(is_win=False)
        gate.record_outcome(is_win=False)
        gate.record_outcome(is_win=False)
        result = gate.check({
            "final_direction": "buy", "final_confidence": 0.8,
            "council_decision_id": "test-3",
        })
        assert result.requires_approval
        assert "losing_streak" in result.gates_triggered

    def test_win_resets_streak(self):
        gate = HITLGate(HITLConfig(max_consecutive_losses=3))
        gate.record_outcome(is_win=False)
        gate.record_outcome(is_win=False)
        gate.record_outcome(is_win=True)
        assert gate._consecutive_losses == 0

    def test_novel_regime_triggers(self):
        gate = HITLGate()
        result = gate.check({
            "final_direction": "buy", "final_confidence": 0.8,
            "council_decision_id": "test-4",
            "metadata": {"regime": "hyperinflation"},
        })
        assert result.requires_approval
        assert "novel_regime" in result.gates_triggered

    def test_approve_and_reject(self):
        gate = HITLGate(HITLConfig(min_confidence_for_auto=0.9))
        result = gate.check({
            "final_direction": "buy", "final_confidence": 0.5,
            "council_decision_id": "approve-me",
        })
        assert result.requires_approval
        assert len(gate.get_pending()) == 1
        gate.approve("approve-me", approver="test")
        assert len(gate.get_pending()) == 0

    def test_sector_concentration_triggers(self):
        gate = HITLGate(HITLConfig(max_sector_concentration=0.35))
        result = gate.check(
            {"final_direction": "buy", "final_confidence": 0.8, "council_decision_id": "test-5"},
            portfolio_context={"sector_allocation": {"Technology": 0.50}},
        )
        assert result.requires_approval
        assert "sector_concentration" in result.gates_triggered

    def test_multiple_gates_triggered(self):
        config = HITLConfig(
            min_confidence_for_auto=0.7,
            learning_period_days=30,
            learning_start_timestamp=time.time(),
        )
        gate = HITLGate(config)
        result = gate.check({
            "final_direction": "sell", "final_confidence": 0.5,
            "council_decision_id": "test-multi",
        })
        assert result.requires_approval
        assert len(result.gates_triggered) >= 2

    def test_gate_status(self):
        gate = HITLGate()
        status = gate.get_status()
        assert "enabled" in status
        assert "config" in status
        assert "pending_count" in status


# ── Data Quality Monitor Tests ────────────────────────────────────────────────

class TestDataQualityMonitor:

    def test_initial_state(self):
        dqm = DataQualityMonitor()
        health = dqm.get_health()
        assert "sources" in health
        assert "overall_quality_score" in health

    def test_record_success(self):
        dqm = DataQualityMonitor()
        dqm.record_fetch("alpaca_quotes", success=True, record_count=100)
        status = dqm.get_source_status("alpaca_quotes")
        assert status["freshness"] == "fresh"
        assert status["quality_score"] > 80

    def test_record_failure(self):
        dqm = DataQualityMonitor()
        dqm.record_fetch("alpaca_quotes", success=False, error="connection refused")
        status = dqm.get_source_status("alpaca_quotes")
        assert status["consecutive_failures"] == 1
        assert status["last_error"] == "connection refused"

    def test_staleness_detection(self):
        config = DataSourceConfig("test_source", expected_interval_seconds=0.01, critical=True, max_stale_seconds=0.03)
        dqm = DataQualityMonitor([config])
        dqm.record_fetch("test_source", success=True)
        time.sleep(0.05)
        assert dqm.should_degrade()

    def test_no_degradation_when_fresh(self):
        config = DataSourceConfig("test_source", expected_interval_seconds=100, critical=True)
        dqm = DataQualityMonitor([config])
        dqm.record_fetch("test_source", success=True)
        assert not dqm.should_degrade()

    def test_register_custom_source(self):
        dqm = DataQualityMonitor()
        dqm.register_source(DataSourceConfig("custom_feed", 60))
        dqm.record_fetch("custom_feed", success=True)
        status = dqm.get_source_status("custom_feed")
        assert status["freshness"] == "fresh"

    def test_quality_score_degrades_with_errors(self):
        dqm = DataQualityMonitor()
        for _ in range(5):
            dqm.record_fetch("alpaca_quotes", success=False, error="timeout")
        status = dqm.get_source_status("alpaca_quotes")
        assert status["quality_score"] < 60

    def test_critical_stale_reported(self):
        config = DataSourceConfig("test_critical", expected_interval_seconds=0.01, critical=True, max_stale_seconds=0.03)
        dqm = DataQualityMonitor([config])
        dqm.record_fetch("test_critical", success=True)
        time.sleep(0.05)
        health = dqm.get_health()
        assert "test_critical" in health["critical_stale"]
        assert health["should_degrade"]

    def test_overall_quality_score(self):
        dqm = DataQualityMonitor()
        dqm.record_fetch("alpaca_quotes", success=True)
        dqm.record_fetch("alpaca_positions", success=True)
        score = dqm.get_quality_score()
        assert 0 <= score <= 100


# ── Shadow Tracker Tests ──────────────────────────────────────────────────────

class TestShadowTracker:

    def test_record_shadow_trade(self):
        tracker = ShadowTracker()
        tracker.record_shadow_trade(
            symbol="AAPL", direction="buy", confidence=0.8,
            entry_price=150.0, simulated_fill_price=150.05,
            qty=10, council_decision_id="test-1",
        )
        assert len(tracker._shadow_trades) == 1
        assert tracker._shadow_trades[0]["status"] == "open"

    def test_close_shadow_trade(self):
        tracker = ShadowTracker()
        tracker.record_shadow_trade(
            symbol="AAPL", direction="buy", confidence=0.8,
            entry_price=150.0, simulated_fill_price=150.05,
            qty=10,
        )
        result = tracker.close_shadow_trade("AAPL", exit_price=155.0)
        assert result is not None
        assert result["pnl"] == pytest.approx((155.0 - 150.05) * 10)
        assert tracker._shadow_pnl > 0

    def test_close_sell_trade(self):
        tracker = ShadowTracker()
        tracker.record_shadow_trade(
            symbol="TSLA", direction="sell", confidence=0.7,
            entry_price=200.0, simulated_fill_price=199.95,
            qty=5,
        )
        result = tracker.close_shadow_trade("TSLA", exit_price=190.0)
        assert result["pnl"] == pytest.approx((199.95 - 190.0) * 5)

    def test_record_live_trade(self):
        tracker = ShadowTracker()
        tracker.record_live_trade("AAPL", "buy", pnl=100)
        assert tracker._live_pnl == 100
        assert len(tracker._live_trades) == 1

    def test_comparison_no_data(self):
        tracker = ShadowTracker()
        comp = tracker.get_comparison()
        assert comp["comparison"]["status"] == "no_data"

    def test_comparison_with_data(self):
        tracker = ShadowTracker()
        # Shadow trades
        for _ in range(5):
            tracker.record_shadow_trade("AAPL", "buy", 0.8, 150, 150.05, 10)
            tracker.close_shadow_trade("AAPL", 155)
        # Live trades
        for _ in range(5):
            tracker.record_live_trade("AAPL", "buy", pnl=40)
        comp = tracker.get_comparison()
        assert comp["shadow"]["total_trades"] == 5
        assert comp["live"]["total_trades"] == 5

    def test_equity_curves(self):
        tracker = ShadowTracker()
        tracker.record_shadow_trade("AAPL", "buy", 0.8, 150, 150.05, 10)
        tracker.close_shadow_trade("AAPL", 155)
        tracker.record_live_trade("AAPL", "buy", pnl=30)
        assert len(tracker.get_shadow_equity_curve()) == 1
        assert len(tracker.get_live_equity_curve()) == 1

    def test_status(self):
        tracker = ShadowTracker()
        tracker.record_shadow_trade("AAPL", "buy", 0.8, 150, 150.05, 10)
        status = tracker.get_status()
        assert status["shadow_trade_count"] == 1
        assert status["open_shadow_positions"] == 1

    def test_slippage_tracked(self):
        tracker = ShadowTracker()
        tracker.record_shadow_trade("AAPL", "buy", 0.8, 150.0, 150.10, 100)
        tracker.close_shadow_trade("AAPL", 155)
        comp = tracker.get_comparison()
        assert comp["shadow"]["total_slippage"] > 0
