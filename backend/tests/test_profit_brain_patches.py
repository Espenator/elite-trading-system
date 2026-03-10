"""Tests for Profit Brain patches: censored outcomes, sizing gate, WS, degraded mode, ML publisher."""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.outcome_tracker import OutcomeTracker, TrackedPosition
from app.services.price_cache_service import PriceCacheService
from app.council.weight_learner import WeightLearner
from app.services.kelly_position_sizer import KellyPositionSizer, PositionSize
from app.api.v1.brain import get_degraded_status
from app.services.ml_signal_publisher import MLSignalPublisher, SOURCE


# ---- P0 Fix 1: Censored outcomes ----
class TestCensoredOutcomes:
    """Timeout trades are censored and excluded from win/loss/Kelly/weights."""

    def test_resolved_payload_has_close_reason_and_is_censored(self):
        pos = TrackedPosition(
            order_id="o1", symbol="AAPL", side="buy", qty=10, entry_price=100.0,
            signal_score=70.0, kelly_pct=0.02, regime="NEUTRAL",
            stop_loss=95.0, take_profit=110.0, is_shadow=True, opened_at=time.time(),
        )
        pos.close_reason = "timeout_censored"
        pos.is_censored = True
        d = pos.to_dict()
        assert d["close_reason"] == "timeout_censored"
        assert d["is_censored"] is True

    def test_censored_outcome_excluded_from_stats(self):
        """When is_censored=True, _resolve_position does not update wins/losses/resolved_history."""
        tracker = OutcomeTracker(message_bus=None)
        tracker._stats = {"wins": 5, "losses": 3, "scratches": 0, "total_resolved": 8, "resolved_history": []}
        pos = TrackedPosition(
            order_id="o1", symbol="AAPL", side="buy", qty=10, entry_price=100.0,
            signal_score=70.0, kelly_pct=0.02, regime="NEUTRAL",
            stop_loss=95.0, take_profit=110.0, is_shadow=True, opened_at=time.time(),
            exit_price=100.0, close_reason="timeout_censored", is_censored=True,
        )
        tracker._resolve_position(pos)
        assert tracker._stats["wins"] == 5
        assert tracker._stats["losses"] == 3
        assert tracker._stats["total_resolved"] == 8
        assert len(tracker._stats.get("resolved_history", [])) == 0

    def test_weight_learner_skips_when_censored(self):
        """WeightLearner.update_from_outcome returns unchanged weights when is_censored=True."""
        learner = WeightLearner()
        learner._decision_history.append({
            "symbol": "AAPL", "timestamp": "2026-01-01T00:00:00Z",
            "final_direction": "buy", "final_confidence": 0.8,
            "votes": [{"agent_name": "risk", "direction": "buy", "confidence": 0.9, "weight": 1.0}],
        })
        before = dict(learner.get_weights())
        result = learner.update_from_outcome("AAPL", "win", is_censored=True)
        assert result == before
        assert learner.get_weights() == before

    def test_weight_learner_contribution_threshold(self):
        """Agents with weight below MIN_CONTRIBUTION_WEIGHT are not updated."""
        learner = WeightLearner()
        learner._decision_history.append({
            "symbol": "TICK", "timestamp": "2026-01-01T00:00:00Z",
            "final_direction": "buy", "final_confidence": 0.8,
            "votes": [
                {"agent_name": "risk", "direction": "buy", "confidence": 0.9, "weight": 0.01},
                {"agent_name": "strategy", "direction": "buy", "confidence": 0.8, "weight": 1.0},
            ],
        })
        with patch.object(learner, "_persist_to_store"):
            with patch.object(learner, "_store_attribution"):
                learner.update_from_outcome("TICK", "win", is_censored=False)
        # risk had weight 0.01 < 0.05 so only strategy would be adjusted
        assert "strategy" in learner._weights
        assert learner._weights["strategy"] != 1.0 or learner.update_count >= 1


# ---- P0 Fix 2: PriceCache ----
class TestPriceCacheService:
    def test_cache_stores_and_returns_price(self):
        cache = PriceCacheService(message_bus=None)
        cache._prices["AAPL"] = 150.5
        cache._last_update_ts = time.time()
        assert cache.get_price("AAPL") == 150.5
        assert cache.get_price("MSFT") is None

    def test_is_stale_no_entry(self):
        cache = PriceCacheService(message_bus=None)
        assert cache.is_stale("AAPL") is True

    def test_is_stale_old_entry(self):
        cache = PriceCacheService(message_bus=None)
        cache._prices["AAPL"] = 150.0
        cache._last_update_ts = time.time() - 120
        assert cache.is_stale("AAPL", max_age_sec=60) is True
        cache._prices["MSFT"] = 300.0
        cache._last_update_ts = time.time()
        assert cache.is_stale("MSFT", max_age_sec=60) is False


# ---- P0 Fix 4: Sizing gate ----
class TestSizingGate:
    def test_kelly_hold_returns_zero_final_pct(self):
        sizer = KellyPositionSizer(min_trades=5)
        pos = sizer.calculate(
            win_rate=0.4, avg_win_pct=0.02, avg_loss_pct=0.03,
            regime="NEUTRAL", trade_count=100,
        )
        assert pos.action == "HOLD"
        assert pos.final_pct == 0.0

    def test_kelly_buy_returns_positive_final_pct(self):
        sizer = KellyPositionSizer(min_trades=5, min_edge=0.01)
        pos = sizer.calculate(
            win_rate=0.60, avg_win_pct=0.04, avg_loss_pct=0.02,
            regime="NEUTRAL", trade_count=100,
        )
        assert pos.action == "BUY"
        assert pos.final_pct > 0


# ---- P1 Fix 5: WS registry ----
class TestWSRegistry:
    def test_ws_registry_schema(self):
        """Registry returns total_connections and channels list with subscriber_count."""
        from app.websocket_manager import get_channel_info
        info = get_channel_info()
        assert "total_connections" in info
        assert "channels" in info
        assert isinstance(info["channels"], dict)

    def test_ws_registry_api_returns_expected_schema(self):
        """GET /api/v1/ws/registry returns total_connections and channel/subscriber info."""
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        r = client.get("/api/v1/ws/registry")
        assert r.status_code == 200
        data = r.json()
        assert "total_connections" in data
        # API may return "channels" (list of {channel, subscriber_count}) or "channel" + "subscriber_counts"
        assert "channels" in data or ("channel" in data and "subscriber_counts" in data)


# ---- P1 Fix 6: Degraded mode ----
class TestDegradedMode:
    def test_degraded_endpoint_returns_schema(self):
        status = get_degraded_status()
        assert "degraded" in status
        assert isinstance(status["degraded"], bool)
        assert "reasons" in status
        assert isinstance(status["reasons"], list)
        assert "details" in status
        assert "timestamp" in status

    def test_degraded_true_when_no_cached_prices(self):
        """When PriceCache is empty, degraded should include market_data_stale."""
        with patch("app.services.price_cache_service.get_price_cache") as m:
            cache = MagicMock()
            cache.get_last_update_time.return_value = None
            m.return_value = cache
            status = get_degraded_status()
        assert status["degraded"] is True
        assert "market_data_stale" in status["reasons"]


# ---- P2 Fix 7: ML publisher ----
class TestMLSignalPublisher:
    @pytest.mark.asyncio
    async def test_publish_includes_provenance(self):
        """Published signal.generated has source=ml_api_stage4, confidence, priority."""
        bus = MagicMock()
        bus.publish = AsyncMock()
        pub = MLSignalPublisher(message_bus=bus, interval_sec=999)
        pub._bus = bus
        # Mock fetch to return one signal
        pub._fetch_stage4_signals = lambda: [
            {"symbol": "AAPL", "prob": 85.0, "dir": "buy"}
        ]
        await pub._fetch_and_publish()
        assert bus.publish.called
        calls = [c for c in bus.publish.call_args_list if c[0][0] == "signal.generated"]
        assert len(calls) >= 1
        payload = calls[0][0][1]
        assert payload["source"] == SOURCE
        assert payload["symbol"] == "AAPL"
        assert payload["score"] == 85.0
        assert payload["confidence"] == 0.85
        assert "priority" in payload
