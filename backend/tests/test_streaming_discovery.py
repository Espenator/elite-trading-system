"""Tests for streaming_discovery.py — StreamingDiscoveryEngine (Issue #38, E1).

Tests cover:
- DiscoveryEvent dataclass and bus payload schema
- All five anomaly detectors (volume_spike, price_breakout, momentum_surge,
  vwap_deviation, range_expansion)
- Deduplication (DEDUP_TTL_SECONDS)
- Per-symbol cooldown (SYMBOL_COOLDOWN_SECONDS)
- Global rate cap (MAX_DISCOVERIES_PER_SEC)
- get_status() health reporter
- Singleton factory (get_streaming_discovery)
- Lifecycle: start / stop
"""
import asyncio
import time
from collections import deque
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.streaming_discovery import (
    DEDUP_TTL_SECONDS,
    MAX_BAR_HISTORY,
    MAX_DISCOVERIES_PER_SEC,
    MIN_BARS_REQUIRED,
    MOMENTUM_RUN_MIN,
    RANGE_EXPANSION_RATIO,
    SYMBOL_COOLDOWN_SECONDS,
    VOLUME_SPIKE_RATIO,
    VWAP_DEVIATION_PCT,
    DiscoveryEvent,
    StreamingDiscoveryEngine,
    get_streaming_discovery,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_bar(
    symbol="AAPL",
    close=150.0,
    open_=150.0,
    high=151.0,
    low=149.0,
    volume=100_000,
    vwap=150.0,
    ts=None,
) -> dict:
    return {
        "symbol": symbol,
        "close": close,
        "open": open_,
        "high": high,
        "low": low,
        "volume": volume,
        "vwap": vwap,
        "timestamp": ts or datetime.now(timezone.utc).isoformat(),
    }


def _make_history(n: int = 25, base_price: float = 100.0, base_vol: int = 50_000) -> list:
    """Return n normal (non-anomalous) bars."""
    return [
        _make_bar(
            close=base_price,
            open_=base_price,
            high=base_price + 0.5,
            low=base_price - 0.5,
            volume=base_vol,
            vwap=base_price,
        )
        for _ in range(n)
    ]


def _mock_bus() -> MagicMock:
    bus = MagicMock()
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()
    bus.publish = AsyncMock()
    return bus


# ──────────────────────────────────────────────────────────────────────────────
# DiscoveryEvent
# ──────────────────────────────────────────────────────────────────────────────


class TestDiscoveryEvent:
    def test_defaults(self):
        evt = DiscoveryEvent(
            discovery_type="volume_spike",
            symbol="AAPL",
            direction="bullish",
            reasoning="test",
            confidence=0.75,
        )
        assert evt.priority == 5
        assert evt.volume_ratio == 0.0
        assert evt.price_change_pct == 0.0
        assert evt.extra == {}

    def test_to_bus_payload_schema(self):
        evt = DiscoveryEvent(
            discovery_type="price_breakout",
            symbol="TSLA",
            direction="bearish",
            reasoning="broke 10-bar low",
            confidence=0.60,
            volume_ratio=1.5,
            price_change_pct=-0.02,
            bar_timestamp="2026-03-08T10:00:00+00:00",
            extra={"prior_low": 200.0},
            priority=3,
        )
        payload = evt.to_bus_payload()

        assert payload["source"] == "streaming_discovery:price_breakout"
        assert payload["symbols"] == ["TSLA"]
        assert payload["direction"] == "bearish"
        assert payload["priority"] == 3
        assert "reasoning" in payload
        meta = payload["metadata"]
        assert meta["discovery_type"] == "price_breakout"
        assert meta["confidence"] == 0.60
        assert meta["volume_ratio"] == 1.5
        assert meta["price_change_pct"] == -0.02
        assert meta["bar_timestamp"] == "2026-03-08T10:00:00+00:00"
        assert meta["prior_low"] == 200.0

    def test_to_bus_payload_confidence_rounded(self):
        evt = DiscoveryEvent(
            discovery_type="momentum_surge",
            symbol="SPY",
            direction="bullish",
            reasoning="r",
            confidence=0.123456789,
        )
        payload = evt.to_bus_payload()
        assert payload["metadata"]["confidence"] == 0.123


# ──────────────────────────────────────────────────────────────────────────────
# StreamingDiscoveryEngine — lifecycle
# ──────────────────────────────────────────────────────────────────────────────


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_subscribes_to_market_data_bar(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        bus.subscribe.assert_called_once_with("market_data.bar", engine._on_new_bar)
        assert engine._running is True
        await engine.stop()

    @pytest.mark.asyncio
    async def test_stop_unsubscribes(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        await engine.stop()
        bus.unsubscribe.assert_called_once_with("market_data.bar", engine._on_new_bar)
        assert engine._running is False

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        await engine.start()  # second call should be no-op
        assert bus.subscribe.call_count == 1
        await engine.stop()

    @pytest.mark.asyncio
    async def test_on_new_bar_ignores_when_stopped(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        # Don't start — _running stays False
        await engine._on_new_bar(_make_bar())
        assert engine._bars_processed == 0


# ──────────────────────────────────────────────────────────────────────────────
# StreamingDiscoveryEngine — detectors
# ──────────────────────────────────────────────────────────────────────────────


class TestDetectors:
    """Unit tests for each anomaly detector in isolation."""

    def _engine(self) -> StreamingDiscoveryEngine:
        return StreamingDiscoveryEngine(_mock_bus())

    # ── volume_spike ──────────────────────────────────────────────────────────

    def test_volume_spike_triggered(self):
        eng = self._engine()
        bars = _make_history(25, base_vol=50_000)
        spike_bar = _make_bar(volume=int(50_000 * VOLUME_SPIKE_RATIO * 1.2), close=102.0, open_=100.0)
        bars.append(spike_bar)
        result = eng._detect_volume_spike("AAPL", bars)
        assert result is not None
        assert result.discovery_type == "volume_spike"
        assert result.direction == "bullish"
        assert result.volume_ratio >= VOLUME_SPIKE_RATIO

    def test_volume_spike_not_triggered_below_ratio(self):
        eng = self._engine()
        bars = _make_history(25, base_vol=50_000)
        normal_bar = _make_bar(volume=60_000)  # Only 1.2x avg
        bars.append(normal_bar)
        assert eng._detect_volume_spike("AAPL", bars) is None

    def test_volume_spike_bearish_direction(self):
        eng = self._engine()
        bars = _make_history(25, base_vol=50_000)
        spike_bar = _make_bar(
            volume=int(50_000 * VOLUME_SPIKE_RATIO * 1.5),
            close=98.0,
            open_=100.0,
        )
        bars.append(spike_bar)
        result = eng._detect_volume_spike("AAPL", bars)
        assert result is not None
        assert result.direction == "bearish"

    def test_volume_spike_zero_volume_returns_none(self):
        eng = self._engine()
        bars = _make_history(25)
        bars.append(_make_bar(volume=0))
        assert eng._detect_volume_spike("AAPL", bars) is None

    # ── price_breakout ────────────────────────────────────────────────────────

    def test_price_breakout_bullish(self):
        eng = self._engine()
        bars = _make_history(15, base_price=100.0)
        # Make prior highs explicitly 101.0
        for b in bars[-11:-1]:
            b["high"] = 101.0
        # Current close above prior high
        bars[-1]["close"] = 103.0
        result = eng._detect_price_breakout("AAPL", bars)
        assert result is not None
        assert result.direction == "bullish"
        assert result.discovery_type == "price_breakout"

    def test_price_breakout_bearish(self):
        eng = self._engine()
        bars = _make_history(15, base_price=100.0)
        for b in bars[-11:-1]:
            b["low"] = 99.0
        bars[-1]["close"] = 97.0
        result = eng._detect_price_breakout("AAPL", bars)
        assert result is not None
        assert result.direction == "bearish"

    def test_price_breakout_not_triggered_inside_range(self):
        eng = self._engine()
        bars = _make_history(15, base_price=100.0)
        # latest close stays within prior range
        bars[-1]["close"] = 100.0
        assert eng._detect_price_breakout("AAPL", bars) is None

    def test_price_breakout_needs_12_bars(self):
        eng = self._engine()
        bars = _make_history(10)  # only 10
        assert eng._detect_price_breakout("AAPL", bars) is None

    # ── momentum_surge ────────────────────────────────────────────────────────

    def test_momentum_surge_bullish(self):
        eng = self._engine()
        bars = _make_history(20)
        # Add MOMENTUM_RUN_MIN+1 consecutive rising closes
        base = 100.0
        for i in range(MOMENTUM_RUN_MIN + 1):
            bars.append(_make_bar(close=base + i * 0.5, open_=base + i * 0.5 - 0.1))
        result = eng._detect_momentum_surge("AAPL", bars)
        assert result is not None
        assert result.direction == "bullish"
        assert result.discovery_type == "momentum_surge"

    def test_momentum_surge_bearish(self):
        eng = self._engine()
        bars = _make_history(20)
        base = 100.0
        for i in range(MOMENTUM_RUN_MIN + 1):
            bars.append(_make_bar(close=base - i * 0.5, open_=base - i * 0.5 + 0.1))
        result = eng._detect_momentum_surge("AAPL", bars)
        assert result is not None
        assert result.direction == "bearish"

    def test_momentum_surge_mixed_direction_returns_none(self):
        eng = self._engine()
        bars = _make_history(20)
        closes = [100.0, 101.0, 100.5, 101.5, 102.0]  # not monotone
        for c in closes:
            bars.append(_make_bar(close=c))
        assert eng._detect_momentum_surge("AAPL", bars) is None

    # ── vwap_deviation ────────────────────────────────────────────────────────

    def test_vwap_deviation_above(self):
        eng = self._engine()
        bars = _make_history(25)
        deviation = VWAP_DEVIATION_PCT * 1.5
        bars.append(_make_bar(close=100.0 * (1 + deviation), vwap=100.0))
        result = eng._detect_vwap_deviation("AAPL", bars)
        assert result is not None
        assert result.direction == "bullish"
        assert result.discovery_type == "vwap_deviation"

    def test_vwap_deviation_below(self):
        eng = self._engine()
        bars = _make_history(25)
        deviation = VWAP_DEVIATION_PCT * 1.5
        bars.append(_make_bar(close=100.0 * (1 - deviation), vwap=100.0))
        result = eng._detect_vwap_deviation("AAPL", bars)
        assert result is not None
        assert result.direction == "bearish"

    def test_vwap_deviation_within_threshold(self):
        eng = self._engine()
        bars = _make_history(25)
        # Very small deviation — less than VWAP_DEVIATION_PCT
        bars.append(_make_bar(close=100.005, vwap=100.0))
        assert eng._detect_vwap_deviation("AAPL", bars) is None

    def test_vwap_deviation_zero_vwap_returns_none(self):
        eng = self._engine()
        bars = _make_history(25)
        bars.append(_make_bar(close=100.0, vwap=0))
        assert eng._detect_vwap_deviation("AAPL", bars) is None

    # ── range_expansion ───────────────────────────────────────────────────────

    def test_range_expansion_triggered(self):
        eng = self._engine()
        # Normal bars have range=1.0, so a ratio of RANGE_EXPANSION_RATIO*1.2 should trigger
        bars = _make_history(25, base_price=100.0)
        expanded_range = 1.0 * RANGE_EXPANSION_RATIO * 1.2
        bars.append(_make_bar(
            close=101.0, open_=100.0,
            high=100.0 + expanded_range / 2,
            low=100.0 - expanded_range / 2,
        ))
        result = eng._detect_range_expansion("AAPL", bars)
        assert result is not None
        assert result.discovery_type == "range_expansion"

    def test_range_expansion_not_triggered_normal_range(self):
        eng = self._engine()
        bars = _make_history(25, base_price=100.0)
        bars.append(_make_bar(high=100.5, low=99.5))  # range=1.0 == avg range
        assert eng._detect_range_expansion("AAPL", bars) is None


# ──────────────────────────────────────────────────────────────────────────────
# StreamingDiscoveryEngine — emit gates
# ──────────────────────────────────────────────────────────────────────────────


class TestEmitGates:
    @pytest.mark.asyncio
    async def test_deduplication_suppresses_same_type(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()

        evt = DiscoveryEvent(
            discovery_type="volume_spike", symbol="AAPL",
            direction="bullish", reasoning="r", confidence=0.8,
        )
        await engine._emit_discovery(evt)

        # Bypass cooldown (pretend it expired) but leave dedup intact
        engine._symbol_last_emit["AAPL"] = time.time() - SYMBOL_COOLDOWN_SECONDS - 1

        await engine._emit_discovery(evt)  # dedup gate should catch this now

        assert bus.publish.call_count == 1
        assert engine._discoveries_emitted == 1
        assert engine._discoveries_skipped_dedup == 1
        await engine.stop()

    @pytest.mark.asyncio
    async def test_symbol_cooldown_suppresses_different_types(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()

        evt1 = DiscoveryEvent(
            discovery_type="volume_spike", symbol="AAPL",
            direction="bullish", reasoning="r1", confidence=0.8,
        )
        evt2 = DiscoveryEvent(
            discovery_type="price_breakout", symbol="AAPL",
            direction="bullish", reasoning="r2", confidence=0.7,
        )
        await engine._emit_discovery(evt1)
        await engine._emit_discovery(evt2)  # same symbol, different type — cooldown hits

        assert bus.publish.call_count == 1
        assert engine._discoveries_skipped_cooldown == 1
        await engine.stop()

    @pytest.mark.asyncio
    async def test_dedup_ttl_expiry_allows_reemit(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()

        dedup_key = "AAPL:volume_spike"
        # Manually set the last emit time to DEDUP_TTL_SECONDS ago
        engine._dedup_cache[dedup_key] = time.time() - DEDUP_TTL_SECONDS - 1
        engine._symbol_last_emit["AAPL"] = time.time() - SYMBOL_COOLDOWN_SECONDS - 1

        evt = DiscoveryEvent(
            discovery_type="volume_spike", symbol="AAPL",
            direction="bullish", reasoning="r", confidence=0.8,
        )
        await engine._emit_discovery(evt)

        assert bus.publish.call_count == 1
        await engine.stop()

    @pytest.mark.asyncio
    async def test_global_rate_cap(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()

        # Fill the sliding window to capacity
        now = time.time()
        for _ in range(MAX_DISCOVERIES_PER_SEC):
            engine._recent_publish_times.append(now)

        evt = DiscoveryEvent(
            discovery_type="volume_spike", symbol="NVDA",
            direction="bullish", reasoning="r", confidence=0.9,
        )
        await engine._emit_discovery(evt)

        assert bus.publish.call_count == 0
        assert engine._discoveries_skipped_rate == 1
        await engine.stop()

    @pytest.mark.asyncio
    async def test_priority_set_on_emit(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()

        evt = DiscoveryEvent(
            discovery_type="volume_spike", symbol="MSFT",
            direction="bullish", reasoning="r", confidence=0.75,
        )
        await engine._emit_discovery(evt)
        assert evt.priority == 2  # as per _DISCOVERY_PRIORITIES["volume_spike"]

        call_kwargs = bus.publish.call_args
        payload = call_kwargs[0][1]  # positional arg 1 = payload dict
        assert payload["priority"] == 2
        await engine.stop()


# ──────────────────────────────────────────────────────────────────────────────
# StreamingDiscoveryEngine — get_status
# ──────────────────────────────────────────────────────────────────────────────


class TestGetStatus:
    @pytest.mark.asyncio
    async def test_status_keys_present(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        status = engine.get_status()

        required_keys = {
            "running", "uptime_seconds", "symbols_tracked",
            "bars_processed", "discoveries_emitted",
            "discoveries_skipped_dedup", "discoveries_skipped_rate",
            "discoveries_skipped_cooldown", "errors",
            "dedup_cache_size", "config",
        }
        assert required_keys <= set(status.keys())
        assert status["running"] is True
        assert isinstance(status["uptime_seconds"], float)
        await engine.stop()

    @pytest.mark.asyncio
    async def test_status_config_keys(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        config = engine.get_status()["config"]
        assert config["max_bar_history"] == MAX_BAR_HISTORY
        assert config["volume_spike_ratio"] == VOLUME_SPIKE_RATIO
        assert config["dedup_ttl_seconds"] == DEDUP_TTL_SECONDS
        assert config["symbol_cooldown_seconds"] == SYMBOL_COOLDOWN_SECONDS
        assert config["max_discoveries_per_sec"] == MAX_DISCOVERIES_PER_SEC
        await engine.stop()

    @pytest.mark.asyncio
    async def test_status_running_false_after_stop(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        await engine.stop()
        assert engine.get_status()["running"] is False


# ──────────────────────────────────────────────────────────────────────────────
# StreamingDiscoveryEngine — end-to-end bar processing
# ──────────────────────────────────────────────────────────────────────────────


class TestBarProcessing:
    @pytest.mark.asyncio
    async def test_bars_below_min_required_do_not_trigger(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()

        # Send fewer than MIN_BARS_REQUIRED bars
        for _ in range(MIN_BARS_REQUIRED - 1):
            await engine._on_new_bar(_make_bar(symbol="AAPL"))

        bus.publish.assert_not_called()
        await engine.stop()

    @pytest.mark.asyncio
    async def test_bars_processed_counter(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()

        for _ in range(5):
            await engine._on_new_bar(_make_bar(symbol="AAPL"))

        assert engine._bars_processed == 5
        await engine.stop()

    @pytest.mark.asyncio
    async def test_volume_spike_publishes_swarm_idea(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()

        # Build MIN_BARS_REQUIRED bars with consistent low volume, then a spike
        base_vol = 50_000
        for _ in range(MIN_BARS_REQUIRED):
            await engine._on_new_bar(_make_bar(symbol="AAPL", volume=base_vol))

        bus.reset_mock()

        spike_vol = int(base_vol * VOLUME_SPIKE_RATIO * 1.5)
        await engine._on_new_bar(_make_bar(symbol="AAPL", volume=spike_vol, close=102.0, open_=100.0))

        bus.publish.assert_called_once()
        call_args = bus.publish.call_args
        topic = call_args[0][0]
        payload = call_args[0][1]
        assert topic == "swarm.idea"
        assert payload["symbols"] == ["AAPL"]
        assert payload["metadata"]["discovery_type"] == "volume_spike"
        await engine.stop()

    @pytest.mark.asyncio
    async def test_missing_symbol_bar_ignored(self):
        bus = _mock_bus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        await engine._on_new_bar({"close": 100.0})  # no "symbol" key
        assert engine._bars_processed == 0
        await engine.stop()


# ──────────────────────────────────────────────────────────────────────────────
# Singleton factory
# ──────────────────────────────────────────────────────────────────────────────


class TestFactory:
    def setup_method(self):
        """Reset singleton before each test."""
        import app.services.streaming_discovery as _mod
        _mod._instance = None

    def test_factory_creates_instance(self):
        bus = _mock_bus()
        engine = get_streaming_discovery(bus)
        assert isinstance(engine, StreamingDiscoveryEngine)

    def test_factory_returns_same_instance(self):
        bus = _mock_bus()
        e1 = get_streaming_discovery(bus)
        e2 = get_streaming_discovery()  # no bus — cached instance
        assert e1 is e2

    def test_factory_raises_without_bus_on_first_call(self):
        with pytest.raises(RuntimeError, match="before engine was initialised"):
            get_streaming_discovery()  # no bus provided, no cached instance

    def teardown_method(self):
        import app.services.streaming_discovery as _mod
        _mod._instance = None
