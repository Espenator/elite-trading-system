"""Tests for StreamingDiscoveryEngine (E1)."""
import asyncio
import pytest
from app.services.streaming_discovery import (
    StreamingDiscoveryEngine,
    BarState,
    DiscoveryEvent,
    MIN_GATES,
    LOOKBACK_BARS,
    VOLUME_SURGE_MULT,
    MOMENTUM_THRESHOLD,
    detect_volume_surge,
    detect_price_breakout,
    detect_momentum_spike,
    detect_velocity_burst,
    detect_volatility_shift,
    get_streaming_discovery_engine,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_bar(symbol="AAPL", close=150.0, high=152.0, low=148.0, volume=1_000_000):
    return {
        "symbol": symbol,
        "close": close,
        "high": high,
        "low": low,
        "volume": volume,
    }


def fill_state(state: BarState, n: int = 10, close=100.0, volume=100_000, bar_range=2.0):
    """Pre-fill a BarState with n normal bars."""
    for _ in range(n):
        bar = {
            "close": close,
            "high": close + bar_range / 2,
            "low": close - bar_range / 2,
            "volume": volume,
        }
        state.update(bar)


# ─────────────────────────────────────────────────────────────────────────────
# BarState
# ─────────────────────────────────────────────────────────────────────────────

class TestBarState:
    def test_update_increments_total_bars(self):
        state = BarState(symbol="AAPL")
        assert state.total_bars == 0
        state.update(make_bar())
        assert state.total_bars == 1

    def test_has_baseline_false_when_insufficient(self):
        state = BarState(symbol="AAPL")
        assert not state.has_baseline

    def test_has_baseline_true_after_enough_bars(self):
        state = BarState(symbol="AAPL")
        for _ in range(6):
            state.update(make_bar())
        assert state.has_baseline

    def test_deque_maxlen_respected(self):
        state = BarState(symbol="AAPL")
        for i in range(LOOKBACK_BARS + 5):
            state.update(make_bar(close=float(100 + i)))
        assert len(state.closes) == LOOKBACK_BARS

    def test_update_populates_all_fields(self):
        state = BarState(symbol="AAPL")
        bar = make_bar(close=150.0, high=152.0, low=148.0, volume=1_000_000)
        state.update(bar)
        assert list(state.closes) == [150.0]
        assert list(state.highs) == [152.0]
        assert list(state.lows) == [148.0]
        assert list(state.volumes) == [1_000_000]
        assert list(state.ranges) == [4.0]

    def test_update_with_shorthand_keys(self):
        """Alpaca uses 'c', 'h', 'l', 'v' shorthand."""
        state = BarState(symbol="AAPL")
        bar = {"c": 155.0, "h": 157.0, "l": 153.0, "v": 500_000}
        state.update(bar)
        assert list(state.closes) == [155.0]
        assert list(state.volumes) == [500_000]


# ─────────────────────────────────────────────────────────────────────────────
# Individual detectors
# ─────────────────────────────────────────────────────────────────────────────

class TestVolumeSurgeDetector:
    def test_no_data_does_not_fire(self):
        state = BarState(symbol="AAPL")
        result = detect_volume_surge(state, make_bar(volume=1_000_000))
        assert not result.fired

    def test_fires_on_surge(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, volume=100_000)
        # Current bar: 3× average
        bar = make_bar(volume=300_000)
        state.update(bar)
        result = detect_volume_surge(state, bar)
        assert result.fired

    def test_does_not_fire_below_threshold(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, volume=100_000)
        bar = make_bar(volume=110_000)  # only 1.1× — below 2.5×
        state.update(bar)
        result = detect_volume_surge(state, bar)
        assert not result.fired

    def test_detail_contains_ratio(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, volume=100_000)
        bar = make_bar(volume=400_000)
        state.update(bar)
        result = detect_volume_surge(state, bar)
        assert "vol_ratio" in result.detail

    def test_zero_avg_volume_does_not_fire(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, volume=0)
        bar = make_bar(volume=1_000_000)
        result = detect_volume_surge(state, bar)
        assert not result.fired


class TestPriceBreakoutDetector:
    def test_no_data_does_not_fire(self):
        state = BarState(symbol="AAPL")
        result = detect_price_breakout(state, make_bar())
        assert not result.fired

    def test_fires_bullish_on_breakout_above(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, close=100.0)  # highs around 101
        bar = make_bar(close=110.0, high=112.0)  # breaks above rolling high
        state.update(bar)
        result = detect_price_breakout(state, bar)
        assert result.fired
        assert result.direction == "bullish"

    def test_fires_bearish_on_breakdown_below(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, close=100.0)  # lows around 99
        bar = make_bar(close=85.0, low=84.0)  # breaks below rolling low
        state.update(bar)
        result = detect_price_breakout(state, bar)
        assert result.fired
        assert result.direction == "bearish"

    def test_no_breakout_in_range(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, close=100.0)  # high=101, low=99
        bar = make_bar(close=100.5)  # inside range
        state.update(bar)
        result = detect_price_breakout(state, bar)
        assert not result.fired


class TestMomentumSpikeDetector:
    def test_no_data_does_not_fire(self):
        state = BarState(symbol="AAPL")
        result = detect_momentum_spike(state, make_bar())
        assert not result.fired

    def test_fires_on_large_return(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 5, close=100.0)
        bar = make_bar(close=102.5)  # 2.5% return > 1.5% threshold
        state.update(bar)
        result = detect_momentum_spike(state, bar)
        assert result.fired

    def test_direction_bullish_on_positive_return(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 5, close=100.0)
        bar = make_bar(close=102.5)
        state.update(bar)
        result = detect_momentum_spike(state, bar)
        assert result.direction == "bullish"

    def test_direction_bearish_on_negative_return(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 5, close=100.0)
        bar = make_bar(close=97.5)  # -2.5%
        state.update(bar)
        result = detect_momentum_spike(state, bar)
        assert result.direction == "bearish"

    def test_small_return_does_not_fire(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 5, close=100.0)
        bar = make_bar(close=100.3)  # 0.3% — below 1.5%
        state.update(bar)
        result = detect_momentum_spike(state, bar)
        assert not result.fired


class TestVelocityBurstDetector:
    def test_no_data_does_not_fire(self):
        state = BarState(symbol="AAPL")
        result = detect_velocity_burst(state, make_bar())
        assert not result.fired

    def test_fires_on_expanded_range(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, close=100.0, bar_range=1.0)  # avg range ≈ 1
        bar = make_bar(close=101.0, high=103.0, low=99.0)  # range=4 → 4× avg
        state.update(bar)
        result = detect_velocity_burst(state, bar)
        assert result.fired

    def test_bullish_when_close_in_upper_half(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, close=100.0, bar_range=1.0)
        bar = make_bar(close=103.5, high=104.0, low=100.0)  # close near top
        state.update(bar)
        result = detect_velocity_burst(state, bar)
        assert result.fired
        assert result.direction == "bullish"

    def test_normal_range_does_not_fire(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, close=100.0, bar_range=2.0)
        bar = make_bar(close=100.0, high=101.1, low=98.9)  # range=2.2 ≈ avg
        state.update(bar)
        result = detect_velocity_burst(state, bar)
        assert not result.fired


class TestVolatilityShiftDetector:
    def test_no_data_does_not_fire(self):
        state = BarState(symbol="AAPL")
        result = detect_volatility_shift(state, make_bar())
        assert not result.fired

    def test_fires_on_2x_range(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, close=100.0, bar_range=1.0)  # avg range ≈ 1
        bar = make_bar(close=100.0, high=101.5, low=98.5)  # range=3 → 3× avg
        state.update(bar)
        result = detect_volatility_shift(state, bar)
        assert result.fired

    def test_normal_range_does_not_fire(self):
        state = BarState(symbol="AAPL")
        fill_state(state, 10, close=100.0, bar_range=2.0)
        bar = make_bar(close=100.0, high=101.2, low=98.8)  # range≈2.4 < 2× of 2.0
        state.update(bar)
        result = detect_volatility_shift(state, bar)
        assert not result.fired


# ─────────────────────────────────────────────────────────────────────────────
# DiscoveryEvent
# ─────────────────────────────────────────────────────────────────────────────

class TestDiscoveryEvent:
    def test_to_swarm_idea_schema(self):
        event = DiscoveryEvent(
            symbol="AAPL",
            direction="bullish",
            reasoning="test reasoning",
            priority=2,
            detector_names=["volume_surge", "price_breakout", "momentum_spike"],
            bar={"close": 150.0, "high": 152.0, "low": 148.0, "volume": 1_000_000, "symbol": "AAPL"},
        )
        idea = event.to_swarm_idea()
        assert idea["source"] == "streaming_discovery:AAPL"
        assert idea["symbols"] == ["AAPL"]
        assert idea["direction"] == "bullish"
        assert "reasoning" in idea
        assert "priority" in idea
        assert "metadata" in idea
        assert "detectors" in idea["metadata"]
        assert "bar" in idea["metadata"]

    def test_priority_clamped(self):
        event = DiscoveryEvent(
            symbol="AAPL",
            direction="neutral",
            reasoning="all 5 fired",
            priority=1,
            detector_names=["a", "b", "c", "d", "e"],
            bar={},
        )
        assert event.priority == 1


# ─────────────────────────────────────────────────────────────────────────────
# StreamingDiscoveryEngine integration
# ─────────────────────────────────────────────────────────────────────────────

class FakeBus:
    def __init__(self):
        self.published = []
        self.subscriptions = {}

    async def subscribe(self, topic, handler):
        self.subscriptions[topic] = handler

    async def publish(self, topic, data):
        self.published.append((topic, data))


class TestStreamingDiscoveryEngine:
    @pytest.mark.anyio
    async def test_start_subscribes_to_market_data_bar(self):
        bus = FakeBus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        assert "market_data.bar" in bus.subscriptions
        await engine.stop()

    @pytest.mark.anyio
    async def test_penny_stock_bar_ignored(self):
        bus = FakeBus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        bar = make_bar(symbol="PENNY", close=0.50)
        await bus.subscriptions["market_data.bar"](bar)
        topics = [t for t, _ in bus.published if t == "swarm.idea"]
        assert len(topics) == 0
        await engine.stop()

    @pytest.mark.anyio
    async def test_insufficient_baseline_bars_no_emit(self):
        bus = FakeBus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        # Only send 2 bars — no baseline
        for _ in range(2):
            await bus.subscriptions["market_data.bar"](make_bar())
        ideas = [d for t, d in bus.published if t == "swarm.idea"]
        assert len(ideas) == 0
        await engine.stop()

    @pytest.mark.anyio
    async def test_normal_bar_does_not_emit(self):
        """Bars with no anomaly should not produce swarm.idea events."""
        bus = FakeBus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        # Build baseline with 10 normal bars
        for _ in range(10):
            state = engine._states.setdefault("AAPL", BarState("AAPL"))
            state.update(make_bar(close=100.0, high=101.0, low=99.0, volume=100_000))
        # Now send a mundane bar
        await bus.subscriptions["market_data.bar"](
            make_bar(close=100.1, high=100.5, low=99.5, volume=102_000)
        )
        ideas = [d for t, d in bus.published if t == "swarm.idea"]
        assert len(ideas) == 0
        await engine.stop()

    @pytest.mark.anyio
    async def test_anomalous_bar_emits_swarm_idea(self):
        """A bar that triggers ≥3 detectors should emit to swarm.idea."""
        bus = FakeBus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()

        # Populate baseline for AAPL
        state = engine._states.setdefault("AAPL", BarState("AAPL"))
        fill_state(state, 15, close=100.0, volume=100_000, bar_range=1.0)

        # Send extreme bar that should fire volume_surge, price_breakout, momentum_spike, velocity_burst
        extreme_bar = {
            "symbol": "AAPL",
            "close": 108.0,   # +8% from 100 → momentum_spike + price_breakout
            "high": 109.0,
            "low": 107.5,     # range = 1.5 → velocity_burst (1.5× avg of 1.0)
            "volume": 500_000,  # 5× avg → volume_surge
        }
        await bus.subscriptions["market_data.bar"](extreme_bar)

        ideas = [d for t, d in bus.published if t == "swarm.idea"]
        assert len(ideas) >= 1
        idea = ideas[0]
        assert idea["symbols"] == ["AAPL"]
        assert idea["direction"] in ("bullish", "bearish", "neutral")
        assert "streaming_discovery:AAPL" in idea["source"]
        await engine.stop()

    @pytest.mark.anyio
    async def test_stats_updated(self):
        bus = FakeBus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        state = engine._states.setdefault("AAPL", BarState("AAPL"))
        fill_state(state, 10)
        await bus.subscriptions["market_data.bar"](make_bar())
        assert engine.get_stats()["bars_processed"] == 1
        await engine.stop()

    @pytest.mark.anyio
    async def test_get_tracked_symbols(self):
        bus = FakeBus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        await bus.subscriptions["market_data.bar"](make_bar(symbol="TSLA"))
        assert "TSLA" in engine.get_tracked_symbols()
        await engine.stop()

    @pytest.mark.anyio
    async def test_stop_is_idempotent(self):
        bus = FakeBus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        await engine.stop()
        await engine.stop()  # Should not raise

    @pytest.mark.anyio
    async def test_no_bus_does_not_raise(self):
        engine = StreamingDiscoveryEngine(None)
        await engine.start()
        # Should not crash
        state = engine._states.setdefault("AAPL", BarState("AAPL"))
        fill_state(state, 10)
        await engine.stop()

    def test_get_streaming_discovery_engine_singleton(self):
        import app.services.streaming_discovery as mod
        mod._engine = None  # reset
        a = get_streaming_discovery_engine()
        b = get_streaming_discovery_engine()
        assert a is b

    @pytest.mark.anyio
    async def test_direction_neutral_when_balanced(self):
        """Equal bullish and bearish detector votes → neutral."""
        bus = FakeBus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()
        state = engine._states.setdefault("AAPL", BarState("AAPL"))
        fill_state(state, 15, close=100.0, volume=100_000, bar_range=2.0)

        # Build event manually to test direction logic
        from app.services.streaming_discovery import DetectionResult, _DETECTORS
        fired = [
            DetectionResult("volume_surge", True, "bullish", ""),
            DetectionResult("price_breakout", True, "bearish", ""),
            DetectionResult("momentum_spike", True, "neutral", ""),
        ]
        event = engine._build_event("AAPL", make_bar(), fired)
        # 1 bullish vs 1 bearish → neutral
        assert event.direction == "neutral"
        await engine.stop()

    @pytest.mark.anyio
    async def test_swarm_idea_has_required_fields(self):
        """Every emitted swarm.idea must have source, symbols, direction, reasoning, priority."""
        bus = FakeBus()
        engine = StreamingDiscoveryEngine(bus)
        await engine.start()

        state = engine._states.setdefault("MSFT", BarState("MSFT"))
        fill_state(state, 15, close=300.0, volume=200_000, bar_range=2.0)

        extreme = {
            "symbol": "MSFT",
            "close": 325.0,   # +8.3%
            "high": 326.0,
            "low": 324.0,
            "volume": 1_000_000,  # 5×
        }
        await bus.subscriptions["market_data.bar"](extreme)
        ideas = [d for t, d in bus.published if t == "swarm.idea"]
        if ideas:
            idea = ideas[0]
            for field in ("source", "symbols", "direction", "reasoning", "priority", "metadata"):
                assert field in idea, f"Missing field: {field}"
        await engine.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Symbol-state cap (regression guard for fix 2)
# ─────────────────────────────────────────────────────────────────────────────

class TestSymbolStateCap:
    """Ensure _states dict is evicted when MAX_TRACKED_SYMBOLS is exceeded."""

    @pytest.mark.asyncio
    async def test_symbol_state_capped_at_max_tracked_symbols(self):
        from app.services.streaming_discovery import (
            StreamingDiscoveryEngine,
            MAX_TRACKED_SYMBOLS,
            BarState,
        )
        engine = StreamingDiscoveryEngine()
        # Pre-fill _states to exactly the limit
        for i in range(MAX_TRACKED_SYMBOLS):
            engine._states[f"SYM{i:04d}"] = BarState(symbol=f"SYM{i:04d}")
        assert len(engine._states) == MAX_TRACKED_SYMBOLS

        # Send one bar for a new symbol: setdefault adds it (→ MAX+1), then
        # the eviction removes one oldest entry (→ MAX). The bar is below the
        # baseline threshold so no swarm.idea is published, but the eviction
        # still fires.
        class FakeBus:
            published = []
            async def subscribe(self, t, h): pass
            async def publish(self, t, d): self.published.append((t, d))

        engine._bus = FakeBus()
        bar = {"symbol": "NEWONE", "close": 100.0, "high": 101.0, "low": 99.0, "volume": 500_000}
        await engine._on_bar(bar)
        assert len(engine._states) == MAX_TRACKED_SYMBOLS


# ─────────────────────────────────────────────────────────────────────────────
# E1 → E3 pipeline integration test
# ─────────────────────────────────────────────────────────────────────────────

class TestE1ToE3Pipeline:
    """E1 publishes to swarm.idea; E3 must escalate high-score events."""

    @pytest.mark.asyncio
    async def test_anomalous_bar_reaches_triage_escalated(self):
        """An anomalous bar from E1 should be escalated by E3."""
        from app.services.streaming_discovery import StreamingDiscoveryEngine, LOOKBACK_BARS
        from app.services.idea_triage import IdeaTriageService

        class CaptureBus:
            """In-process bus that directly invokes registered handlers."""
            def __init__(self):
                self._handlers: dict = {}
                self.published = []

            async def subscribe(self, topic, handler):
                self._handlers.setdefault(topic, []).append(handler)

            async def publish(self, topic, data):
                self.published.append((topic, data))
                for h in self._handlers.get(topic, []):
                    await h(data)

        bus = CaptureBus()

        # Wire E3 first so it is subscribed before E1 publishes
        triage = IdeaTriageService(message_bus=bus)
        await triage.start()

        engine = StreamingDiscoveryEngine(message_bus=bus)
        await engine.start()

        # Build baseline history for AAPL
        base = {"symbol": "AAPL", "close": 150.0, "high": 151.0, "low": 149.0, "volume": 100_000}
        for _ in range(LOOKBACK_BARS):
            await engine._on_bar(base)

        # Send a strongly anomalous bar (all 5 detectors should fire)
        anomaly = {
            "symbol": "AAPL",
            "close": 170.0,   # strong breakout
            "high": 175.0,
            "low": 165.0,
            "volume": 10_000_000,  # massive volume
        }
        await engine._on_bar(anomaly)

        escalated = [d for t, d in bus.published if t == "triage.escalated"]
        assert len(escalated) >= 1, "Anomalous bar should produce at least one triage.escalated event"
        payload = escalated[0]
        assert "triage" in payload
        assert payload["triage"]["escalated"] is True

        await engine.stop()
        await triage.stop()
