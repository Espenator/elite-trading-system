"""Tests for StreamingDiscoveryEngine (Issue #38 — E1).

Validates:
    - Rolling OHLCV window management
    - Volume spike detector
    - Price surge detector
    - VWAP deviation detector
    - RSI extreme detector
    - Bollinger squeeze + expansion detector
    - Composite score calculation
    - swarm.idea publication on threshold breach
    - Cooldown prevents duplicate discoveries
    - Mock-source bars are rejected
    - get_status() returns expected shape
"""
import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.streaming_discovery_engine import (
    StreamingDiscoveryEngine,
    _Bar,
    _SymbolState,
    _compute_rsi,
    _compute_vwap,
    _compute_bb_width,
    PUBLISH_THRESHOLD,
    ROLLING_WINDOW,
    VOLUME_SPIKE_RATIO,
    PRICE_SURGE_PCT,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    get_streaming_discovery,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_bus(captured: List[Dict[str, Any]]) -> MagicMock:
    """Return a mock MessageBus that records published events."""
    bus = MagicMock()
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()

    async def _publish(topic: str, data: dict):
        captured.append({"topic": topic, "data": data})

    bus.publish = _publish
    return bus


def flat_bar(close: float, volume: float = 100_000, timestamp: str = "2026-01-01T00:00:00Z") -> Dict:
    return {
        "symbol": "AAPL",
        "close": close,
        "open": close,
        "high": close * 1.002,
        "low": close * 0.998,
        "volume": volume,
        "timestamp": timestamp,
        "source": "stream",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Utility function tests
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeRsi:
    def test_returns_50_insufficient_data(self):
        assert _compute_rsi([], period=7) == 50.0
        assert _compute_rsi([100.0, 101.0], period=7) == 50.0

    def test_all_equal_closes_returns_50(self):
        closes = [100.0] * 20
        assert _compute_rsi(closes, period=7) == 50.0

    def test_all_up_bars_returns_100(self):
        closes = [float(i) for i in range(100, 120)]  # monotonically rising
        result = _compute_rsi(closes, period=7)
        assert result == 100.0

    def test_all_down_bars(self):
        closes = [float(i) for i in range(120, 100, -1)]  # monotonically falling
        result = _compute_rsi(closes, period=7)
        assert result < 5.0  # Near 0 for all-down

    def test_oversold_range(self):
        closes = [100, 98, 96, 94, 92, 90, 88, 87, 86, 85]
        rsi = _compute_rsi(closes, period=7)
        # Should be in the oversold zone (< 30-ish)
        assert rsi < 35.0

    def test_overbought_range(self):
        closes = [80, 83, 86, 89, 92, 95, 98, 101, 104, 107]
        rsi = _compute_rsi(closes, period=7)
        # Strong up-trend should produce high RSI
        assert rsi > 70.0


class TestComputeVwap:
    def test_uniform_bars(self):
        bars = [_Bar(close=100.0, open=100.0, high=101.0, low=99.0, volume=1000.0)
                for _ in range(5)]
        vwap = _compute_vwap(bars)
        assert abs(vwap - 100.0) < 0.1

    def test_zero_volume_returns_zero(self):
        bars = [_Bar(close=100.0, open=100.0, high=101.0, low=99.0, volume=0.0)]
        assert _compute_vwap(bars) == 0.0

    def test_weighted_by_volume(self):
        bar_low = _Bar(close=90.0, open=90.0, high=91.0, low=89.0, volume=100.0)
        bar_high = _Bar(close=110.0, open=110.0, high=111.0, low=109.0, volume=900.0)
        vwap = _compute_vwap([bar_low, bar_high])
        # 90 * 100 + 110 * 900 = 9000 + 99000 = 108000 / 1000 ≈ 108
        assert abs(vwap - 108.0) < 1.0


class TestComputeBbWidth:
    def test_insufficient_data_returns_zeros(self):
        result = _compute_bb_width([100.0] * 5, period=20)
        assert result == (0.0, 0.0)

    def test_constant_series_width_is_zero(self):
        closes = [100.0] * 25
        mid, width = _compute_bb_width(closes, period=20)
        assert abs(mid - 100.0) < 0.001
        assert width < 0.001

    def test_volatile_series_has_width(self):
        import math
        closes = [100.0 + 5.0 * math.sin(i) for i in range(30)]
        mid, width = _compute_bb_width(closes, period=20)
        assert width > 0.5


# ─────────────────────────────────────────────────────────────────────────────
# StreamingDiscoveryEngine unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestStreamingDiscoveryEngineLifecycle:
    @pytest.mark.anyio
    async def test_start_subscribes(self):
        captured: List = []
        bus = make_bus(captured)
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        bus.subscribe.assert_called_once_with("market_data.bar", engine._on_bar)
        assert engine._running is True
        await engine.stop()

    @pytest.mark.anyio
    async def test_stop_unsubscribes(self):
        captured: List = []
        bus = make_bus(captured)
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        await engine.stop()
        bus.unsubscribe.assert_called_once_with("market_data.bar", engine._on_bar)
        assert engine._running is False

    @pytest.mark.anyio
    async def test_double_start_is_idempotent(self):
        captured: List = []
        bus = make_bus(captured)
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        await engine.start()  # second start should be a no-op
        assert bus.subscribe.call_count == 1
        await engine.stop()


class TestMockSourceRejection:
    @pytest.mark.anyio
    async def test_mock_source_not_processed(self):
        captured: List = []
        bus = make_bus(captured)
        engine = StreamingDiscoveryEngine(bus, publish_threshold=0.0)
        await engine.start()

        bar = flat_bar(100.0)
        bar["source"] = "mock"
        for _ in range(20):
            await engine._on_bar(bar)

        # Mock-source bars must never produce a swarm.idea event
        swarm_events = [e for e in captured if e["topic"] == "swarm.idea"]
        assert swarm_events == []
        assert engine._discoveries_made == 0
        await engine.stop()


class TestVolumeSpikeDetection:
    @pytest.mark.anyio
    async def test_volume_spike_triggers_discovery(self):
        """A bar with volume >> avg should produce a swarm.idea."""
        captured: List = []
        bus = make_bus(captured)
        engine = StreamingDiscoveryEngine(bus, publish_threshold=10.0, cooldown_seconds=0)
        await engine.start()

        # Seed 15 bars with normal volume (100k)
        for i in range(15):
            await engine._on_bar(flat_bar(100.0, volume=100_000))

        # Fire a spike bar (4× average)
        spike_bar = flat_bar(100.0, volume=400_000)
        await engine._on_bar(spike_bar)

        swarm_events = [e for e in captured if e["topic"] == "swarm.idea"]
        assert len(swarm_events) >= 1
        ev = swarm_events[-1]["data"]
        assert ev["source"] == "streaming_discovery"
        assert ev["symbol"] == "AAPL"
        assert ev["score"] > 0
        assert "volume" in ev["anomaly_details"] or "volume_spike" in ev["anomaly_details"]
        await engine.stop()

    @pytest.mark.anyio
    async def test_normal_volume_no_discovery(self):
        captured: List = []
        bus = make_bus(captured)
        engine = StreamingDiscoveryEngine(bus, publish_threshold=50.0, cooldown_seconds=0)
        await engine.start()

        # Feed bars with tiny alternating moves (±0.3%) that stay below all thresholds:
        #   PRICE_SURGE_PCT = 1.5%, VWAP_DEVIATION_PCT = 0.8%
        #   0.3% << 1.5% → no price surge; VWAP deviation also <0.8%
        #   Constant volume → no spike; balanced RSI ~50 → no extreme
        for i in range(20):
            price = 100.3 if i % 2 == 0 else 99.7
            await engine._on_bar(flat_bar(price, volume=100_000))

        swarm_events = [e for e in captured if e["topic"] == "swarm.idea"]
        assert len(swarm_events) == 0, (
            f"Expected 0 discoveries for sub-threshold oscillation, got {len(swarm_events)}"
        )
        await engine.stop()


class TestPriceSurgeDetection:
    @pytest.mark.anyio
    async def test_price_surge_triggers_discovery(self):
        captured: List = []
        bus = make_bus(captured)
        engine = StreamingDiscoveryEngine(bus, publish_threshold=10.0, cooldown_seconds=0)
        await engine.start()

        # Seed 10 stable bars
        for _ in range(10):
            await engine._on_bar(flat_bar(100.0))

        # Surge bar: +3% price move
        surge_bar = flat_bar(103.0)
        await engine._on_bar(surge_bar)

        swarm_events = [e for e in captured if e["topic"] == "swarm.idea"]
        assert len(swarm_events) >= 1
        ev = swarm_events[-1]["data"]
        details = ev["anomaly_details"]
        assert "price_surge" in details
        assert details["price_surge"]["direction"] == "up"
        await engine.stop()


class TestCooldown:
    @pytest.mark.anyio
    async def test_cooldown_prevents_second_discovery(self):
        captured: List = []
        bus = make_bus(captured)
        engine = StreamingDiscoveryEngine(bus, publish_threshold=10.0, cooldown_seconds=999)
        await engine.start()

        # Seed with sub-threshold oscillation (±0.3%) to keep RSI neutral
        for i in range(10):
            price = 100.3 if i % 2 == 0 else 99.7
            await engine._on_bar(flat_bar(price, volume=100_000))

        # First spike
        await engine._on_bar(flat_bar(104.0, volume=400_000))
        first_count = len([e for e in captured if e["topic"] == "swarm.idea"])

        # Second spike immediately — should be blocked by cooldown
        await engine._on_bar(flat_bar(108.0, volume=600_000))
        second_count = len([e for e in captured if e["topic"] == "swarm.idea"])

        assert first_count >= 1
        assert second_count == first_count  # No additional events
        await engine.stop()

    @pytest.mark.anyio
    async def test_expired_cooldown_allows_second_discovery(self):
        captured: List = []
        bus = make_bus(captured)
        engine = StreamingDiscoveryEngine(bus, publish_threshold=10.0, cooldown_seconds=0)
        await engine.start()

        # Seed with sub-threshold oscillation (±0.3%) to keep RSI neutral
        for i in range(10):
            price = 100.3 if i % 2 == 0 else 99.7
            await engine._on_bar(flat_bar(price, volume=100_000))

        # Two distinct spikes — both should fire (cooldown=0)
        count_before = len([e for e in captured if e["topic"] == "swarm.idea"])
        await engine._on_bar(flat_bar(104.0, volume=400_000))
        await engine._on_bar(flat_bar(108.0, volume=600_000))

        swarm_events = [e for e in captured if e["topic"] == "swarm.idea"]
        assert len(swarm_events) >= count_before + 2
        await engine.stop()


class TestGetStatus:
    @pytest.mark.anyio
    async def test_get_status_shape(self):
        captured: List = []
        bus = make_bus(captured)
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()

        status = engine.get_status()
        assert "running" in status
        assert "bars_processed" in status
        assert "discoveries_made" in status
        assert "cooldowns_skipped" in status
        assert "symbols_tracked" in status
        assert status["running"] is True
        await engine.stop()

    @pytest.mark.anyio
    async def test_bars_processed_counter(self):
        captured: List = []
        bus = make_bus(captured)
        engine = StreamingDiscoveryEngine(bus, publish_threshold=200.0)
        await engine.start()

        for _ in range(7):
            await engine._on_bar(flat_bar(100.0))

        assert engine._bars_processed == 7
        await engine.stop()


class TestSingleton:
    def test_get_streaming_discovery_returns_instance(self):
        from app.services.streaming_discovery_engine import (
            get_streaming_discovery,
            _engine_instance,
        )
        import app.services.streaming_discovery_engine as mod

        # Reset singleton for test isolation
        original = mod._engine_instance
        mod._engine_instance = None
        try:
            bus = MagicMock()
            bus.subscribe = AsyncMock()
            inst = get_streaming_discovery(bus)
            assert isinstance(inst, StreamingDiscoveryEngine)
            # Second call without bus should return same instance
            same = get_streaming_discovery()
            assert same is inst
        finally:
            mod._engine_instance = original
