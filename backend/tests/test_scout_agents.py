"""Tests for the 12 dedicated scout agents — E2 continuous discovery architecture.

Tests cover:
  - DiscoveryPayload schema validation and serialisation
  - ScoutHealth schema
  - BaseScout lifecycle (start/stop/get_health)
  - BaseScout run loop: scan called, discoveries published, heartbeat sent
  - BaseScout error handling: timeout, exceptions, back-off
  - BaseScout circuit-breaker state
  - ScoutRegistry: register, start_all, stop_all, restart_scout, get_status
  - Individual scouts: AlpacaTrade, AlpacaNews, AlpacaPremarket
  - Individual scouts: UnusualWhalesFlow, UnusualWhalesDarkpool
  - Individual scouts: FinvizMomentum, FinvizBreakout
  - Individual scouts: FredMacro, SecEdgar
  - Individual scouts: NewsSentiment, SocialSentiment, SectorRotation
  - MessageBus topic registration (scout.heartbeat present)
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bus():
    """Return a minimal mock MessageBus."""
    bus = MagicMock()
    bus.publish = AsyncMock()
    bus.subscribe = AsyncMock()
    return bus


# ===========================================================================
# DiscoveryPayload schema
# ===========================================================================

class TestDiscoveryPayload:
    def test_basic_construction(self):
        from app.services.scouts.schemas import DiscoveryPayload
        p = DiscoveryPayload(
            scout_id="test_scout",
            source="Test",
            source_type="test",
            symbol="aapl",       # lower-case → should be upper-cased
            direction="bullish",
            signal_type="momentum",
            confidence=0.75,
            score=80,
            reasoning="Test reasoning",
        )
        assert p.symbol == "AAPL"
        assert p.confidence == 0.75
        assert p.score == 80
        assert p.priority == 3          # default
        assert p.ttl_seconds == 300     # default
        assert p.feedback_key != ""

    def test_confidence_clamped(self):
        from app.services.scouts.schemas import DiscoveryPayload
        p = DiscoveryPayload(
            scout_id="s", source="S", source_type="t", symbol="X",
            direction="neutral", signal_type="x", confidence=5.0, score=200, reasoning="",
        )
        assert p.confidence == 1.0
        assert p.score == 100

    def test_to_dict_keys(self):
        from app.services.scouts.schemas import DiscoveryPayload
        p = DiscoveryPayload(
            scout_id="s", source="S", source_type="t", symbol="TSLA",
            direction="bearish", signal_type="dark_pool", confidence=0.5, score=60, reasoning="x",
        )
        d = p.to_dict()
        required_keys = {
            "scout_id", "source", "source_type", "symbol", "direction",
            "signal_type", "confidence", "score", "reasoning", "priority",
            "ttl_seconds", "attributes", "related_symbols", "discovered_at",
            "feedback_key",
        }
        assert required_keys.issubset(set(d.keys()))

    def test_round_trip_from_dict(self):
        from app.services.scouts.schemas import DiscoveryPayload
        p = DiscoveryPayload(
            scout_id="s", source="S", source_type="t", symbol="AMD",
            direction="bullish", signal_type="breakout", confidence=0.8, score=70,
            reasoning="round trip test", attributes={"vol_ratio": 3.5}, related_symbols=["QQQ"],
        )
        p2 = DiscoveryPayload.from_dict(p.to_dict())
        assert p2.symbol == p.symbol
        assert p2.score == p.score
        assert p2.attributes["vol_ratio"] == 3.5
        assert p2.related_symbols == ["QQQ"]

    def test_feedback_key_stable(self):
        from app.services.scouts.schemas import DiscoveryPayload
        p = DiscoveryPayload(
            scout_id="my_scout", source="S", source_type="t", symbol="NVDA",
            direction="bullish", signal_type="x", confidence=0.5, score=50, reasoning="",
        )
        assert p.feedback_key.startswith("my_scout:NVDA:")


# ===========================================================================
# ScoutHealth schema
# ===========================================================================

class TestScoutHealth:
    def test_to_dict(self):
        from app.services.scouts.schemas import ScoutHealth
        h = ScoutHealth(
            scout_id="test", status="running",
            total_scans=5, total_discoveries=2,
        )
        d = h.to_dict()
        assert d["scout_id"] == "test"
        assert d["status"] == "running"
        assert d["total_scans"] == 5


# ===========================================================================
# BaseScout contract
# ===========================================================================

class ConcreteScout:
    """Minimal concrete scout for lifecycle testing."""

    from app.services.scouts.base_scout import BaseScout as _Base

    scout_id = "test_concrete"
    source = "Test"
    source_type = "test"
    scan_interval = 0.05   # fast for tests
    timeout = 2.0
    heartbeat_interval = 0.1

    async def setup(self):
        pass

    async def teardown(self):
        pass

    async def scan(self):
        return []


def _make_concrete_scout():
    """Return a fresh concrete scout instance."""
    from app.services.scouts.base_scout import BaseScout
    from app.services.scouts.schemas import DiscoveryPayload

    class _Scout(BaseScout):
        scout_id = "test_concrete"
        source = "Test"
        source_type = "test"
        scan_interval = 0.05
        timeout = 2.0
        heartbeat_interval = 0.1

        async def scan(self) -> List[DiscoveryPayload]:
            return []

    return _Scout()


class TestBaseScoutLifecycle:
    @pytest.mark.anyio
    async def test_start_creates_task(self):
        scout = _make_concrete_scout()
        bus = _make_bus()
        await scout.start(bus)
        assert scout._running is True
        assert scout._task is not None
        await scout.stop()
        assert scout._running is False

    @pytest.mark.anyio
    async def test_double_start_is_idempotent(self):
        scout = _make_concrete_scout()
        bus = _make_bus()
        await scout.start(bus)
        task1 = scout._task
        await scout.start(bus)   # second call should be no-op
        assert scout._task is task1
        await scout.stop()

    @pytest.mark.anyio
    async def test_get_health_after_start(self):
        scout = _make_concrete_scout()
        bus = _make_bus()
        await scout.start(bus)
        await asyncio.sleep(0.15)
        health = scout.get_health()
        assert health.scout_id == "test_concrete"
        assert health.status == "running"
        assert health.uptime_seconds >= 0
        await scout.stop()

    @pytest.mark.anyio
    async def test_get_health_after_stop(self):
        scout = _make_concrete_scout()
        bus = _make_bus()
        await scout.start(bus)
        await scout.stop()
        health = scout.get_health()
        assert health.status == "stopped"

    @pytest.mark.anyio
    async def test_discoveries_published_to_swarm_idea(self):
        from app.services.scouts.base_scout import BaseScout
        from app.services.scouts.schemas import DiscoveryPayload

        class _ScoutWithFind(BaseScout):
            scout_id = "discoverer"
            source = "X"
            source_type = "test"
            scan_interval = 0.05
            timeout = 2.0
            heartbeat_interval = 999.0  # suppress heartbeat noise

            async def scan(self):
                return [DiscoveryPayload(
                    scout_id=self.scout_id, source="X", source_type="test",
                    symbol="NVDA", direction="bullish", signal_type="breakout",
                    confidence=0.9, score=90, reasoning="Test find",
                )]

        scout = _ScoutWithFind()
        bus = _make_bus()
        await scout.start(bus)
        await asyncio.sleep(0.2)
        await scout.stop()

        calls = [c for c in bus.publish.call_args_list if c.args[0] == "swarm.idea"]
        assert len(calls) >= 1
        payload_dict = calls[0].args[1]
        assert payload_dict["symbol"] == "NVDA"
        assert payload_dict["direction"] == "bullish"

    @pytest.mark.anyio
    async def test_heartbeat_published_to_scout_heartbeat(self):
        from app.services.scouts.base_scout import BaseScout
        from app.services.scouts.schemas import DiscoveryPayload

        class _HBScout(BaseScout):
            scout_id = "hb_scout"
            source = "HB"
            source_type = "test"
            scan_interval = 0.05
            timeout = 2.0
            heartbeat_interval = 0.05

            async def scan(self):
                return []

        scout = _HBScout()
        bus = _make_bus()
        await scout.start(bus)
        await asyncio.sleep(0.3)
        await scout.stop()

        hb_calls = [c for c in bus.publish.call_args_list if c.args[0] == "scout.heartbeat"]
        assert len(hb_calls) >= 1

    @pytest.mark.anyio
    async def test_scan_timeout_increments_errors(self):
        from app.services.scouts.base_scout import BaseScout
        from app.services.scouts.schemas import DiscoveryPayload

        class _SlowScout(BaseScout):
            scout_id = "slow_scout"
            source = "Slow"
            source_type = "test"
            scan_interval = 0.05
            timeout = 0.05      # very short timeout
            heartbeat_interval = 999.0

            async def scan(self):
                await asyncio.sleep(5.0)   # always exceeds timeout
                return []

        scout = _SlowScout()
        bus = _make_bus()
        await scout.start(bus)
        await asyncio.sleep(0.4)
        await scout.stop()
        assert scout._consecutive_errors >= 1

    @pytest.mark.anyio
    async def test_scan_exception_increments_errors(self):
        from app.services.scouts.base_scout import BaseScout
        from app.services.scouts.schemas import DiscoveryPayload

        class _ErrorScout(BaseScout):
            scout_id = "error_scout"
            source = "Error"
            source_type = "test"
            scan_interval = 0.05
            timeout = 2.0
            heartbeat_interval = 999.0

            async def scan(self):
                raise RuntimeError("simulated scan error")

        scout = _ErrorScout()
        bus = _make_bus()
        await scout.start(bus)
        await asyncio.sleep(0.3)
        await scout.stop()
        assert scout._consecutive_errors >= 1
        assert "simulated scan error" in scout._last_error

    def test_backoff_grows_exponentially(self):
        scout = _make_concrete_scout()
        scout._consecutive_errors = 0
        assert scout._compute_backoff() == scout.scan_interval

        scout._consecutive_errors = 1
        b1 = scout._compute_backoff()
        scout._consecutive_errors = 2
        b2 = scout._compute_backoff()
        assert b2 > b1

    def test_backoff_capped_at_max(self):
        scout = _make_concrete_scout()
        scout._consecutive_errors = 100
        assert scout._compute_backoff() == scout.max_backoff

    def test_circuit_breaker_status_in_health(self):
        scout = _make_concrete_scout()
        scout._running = True
        scout._consecutive_errors = scout.max_consecutive_errors
        health = scout.get_health()
        assert health.status == "error"

    @pytest.mark.anyio
    async def test_analyst_evaluate_returns_none_by_default(self):
        scout = _make_concrete_scout()
        result = await scout.analyst_evaluate("AAPL", "1d", {}, {})
        assert result is None


# ===========================================================================
# ScoutRegistry
# ===========================================================================

class TestScoutRegistry:
    def _make_registry_with_scouts(self):
        from app.services.scouts.registry import ScoutRegistry
        from app.services.scouts.base_scout import BaseScout
        from app.services.scouts.schemas import DiscoveryPayload

        class _MockScout(BaseScout):
            def __init__(self, sid):
                super().__init__()
                self.scout_id = sid
                self.source = sid
                self.source_type = "test"
                self.scan_interval = 0.05
                self.timeout = 1.0
                self.heartbeat_interval = 999.0

            async def scan(self):
                return []

        registry = ScoutRegistry()
        scouts = [_MockScout("scout_a"), _MockScout("scout_b"), _MockScout("scout_c")]
        for s in scouts:
            registry.register(s)
        return registry

    @pytest.mark.anyio
    async def test_start_all_starts_scouts(self):
        registry = self._make_registry_with_scouts()
        bus = _make_bus()
        await registry.start_all(bus)
        status = registry.get_status()
        assert status["running_scouts"] == 3
        await registry.stop_all()

    @pytest.mark.anyio
    async def test_stop_all_stops_scouts(self):
        registry = self._make_registry_with_scouts()
        bus = _make_bus()
        await registry.start_all(bus)
        await registry.stop_all()
        status = registry.get_status()
        assert status["running_scouts"] == 0

    @pytest.mark.anyio
    async def test_restart_scout(self):
        registry = self._make_registry_with_scouts()
        bus = _make_bus()
        await registry.start_all(bus)
        await registry.restart_scout("scout_a")
        status = registry.get_status()
        assert status["scouts"]["scout_a"]["status"] in ("running", "stopped")
        await registry.stop_all()

    def test_duplicate_registration_raises(self):
        from app.services.scouts.registry import ScoutRegistry
        from app.services.scouts.base_scout import BaseScout
        from app.services.scouts.schemas import DiscoveryPayload

        class _S(BaseScout):
            scout_id = "dup"
            source = "D"
            source_type = "test"
            async def scan(self): return []

        registry = ScoutRegistry()
        registry.register(_S())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(_S())

    def test_restart_unknown_scout_raises(self):
        from app.services.scouts.registry import ScoutRegistry
        registry = ScoutRegistry()

        async def _run():
            await registry.restart_scout("nonexistent")

        with pytest.raises(KeyError):
            asyncio.get_event_loop().run_until_complete(_run())

    def test_get_status_structure(self):
        registry = self._make_registry_with_scouts()
        status = registry.get_status()
        assert "fleet_running" in status
        assert "total_scouts" in status
        assert "running_scouts" in status
        assert "error_scouts" in status
        assert "total_discoveries" in status
        assert "scouts" in status
        assert status["total_scouts"] == 3

    def test_get_scout_ids(self):
        registry = self._make_registry_with_scouts()
        ids = registry.get_scout_ids()
        assert "scout_a" in ids
        assert "scout_b" in ids
        assert len(ids) == 3

    def test_get_scout_by_id(self):
        registry = self._make_registry_with_scouts()
        scout = registry.get_scout("scout_a")
        assert scout is not None
        assert scout.scout_id == "scout_a"

    def test_get_scout_unknown_returns_none(self):
        registry = self._make_registry_with_scouts()
        assert registry.get_scout("nonexistent") is None


# ===========================================================================
# Individual scouts — evaluate logic (unit tests, no real HTTP)
# ===========================================================================

class TestAlpacaTradeScout:
    def test_evaluate_bar_volume_spike(self):
        from app.services.scouts.alpaca_trade_scout import AlpacaTradeScout
        scout = AlpacaTradeScout()
        bar = {"c": 150.0, "prev_close": 148.0, "v": 3_000_000, "avg_volume": 500_000}
        payload = scout._evaluate_bar("AAPL", bar)
        assert payload is not None
        assert payload.symbol == "AAPL"
        assert payload.direction == "bullish"
        assert payload.score > 0

    def test_evaluate_bar_no_spike_returns_none(self):
        from app.services.scouts.alpaca_trade_scout import AlpacaTradeScout
        scout = AlpacaTradeScout()
        bar = {"c": 150.0, "prev_close": 150.0, "v": 100_000, "avg_volume": 500_000}
        assert scout._evaluate_bar("AAPL", bar) is None

    def test_evaluate_bar_bearish(self):
        from app.services.scouts.alpaca_trade_scout import AlpacaTradeScout
        scout = AlpacaTradeScout()
        bar = {"c": 140.0, "prev_close": 150.0, "v": 5_000_000, "avg_volume": 500_000}
        payload = scout._evaluate_bar("TSLA", bar)
        assert payload is not None
        assert payload.direction == "bearish"


class TestAlpacaNewsScout:
    def test_evaluate_article_bullish(self):
        from app.services.scouts.alpaca_news_scout import AlpacaNewsScout
        scout = AlpacaNewsScout()
        article = {
            "id": "123",
            "headline": "Apple beats earnings record upgrade buy",
            "symbols": ["AAPL"],
        }
        payload = scout._evaluate_article(article)
        assert payload is not None
        assert payload.symbol == "AAPL"
        assert payload.direction == "bullish"

    def test_evaluate_article_bearish(self):
        from app.services.scouts.alpaca_news_scout import AlpacaNewsScout
        scout = AlpacaNewsScout()
        article = {
            "id": "456",
            "headline": "Tesla miss disappoints loss cuts downgrade",
            "symbols": ["TSLA"],
        }
        payload = scout._evaluate_article(article)
        assert payload is not None
        assert payload.direction == "bearish"

    def test_evaluate_article_no_keywords_returns_none(self):
        from app.services.scouts.alpaca_news_scout import AlpacaNewsScout
        scout = AlpacaNewsScout()
        article = {"id": "789", "headline": "Company announces quarterly results", "symbols": ["X"]}
        payload = scout._evaluate_article(article)
        assert payload is None

    def test_deduplication_prevents_reprocess(self):
        from app.services.scouts.alpaca_news_scout import AlpacaNewsScout
        scout = AlpacaNewsScout()
        article = {"id": "dup1", "headline": "Apple beats record", "symbols": ["AAPL"]}
        p1 = scout._evaluate_article(article)
        p2 = scout._evaluate_article(article)
        assert p1 is not None
        assert p2 is None


class TestAlpacaPremarketScout:
    def test_evaluate_bar_gap_up(self):
        from app.services.scouts.alpaca_premarket_scout import AlpacaPremarketScout
        scout = AlpacaPremarketScout()
        bar = {"c": 155.0, "prev_close": 150.0, "v": 200_000}
        payload = scout._evaluate_bar("NVDA", bar)
        assert payload is not None
        assert payload.direction == "bullish"
        assert payload.signal_type == "premarket_gap"

    def test_evaluate_bar_gap_below_threshold_returns_none(self):
        from app.services.scouts.alpaca_premarket_scout import AlpacaPremarketScout
        scout = AlpacaPremarketScout()
        bar = {"c": 150.5, "prev_close": 150.0, "v": 200_000}
        assert scout._evaluate_bar("NVDA", bar) is None

    def test_evaluate_bar_low_volume_returns_none(self):
        from app.services.scouts.alpaca_premarket_scout import AlpacaPremarketScout
        scout = AlpacaPremarketScout()
        bar = {"c": 160.0, "prev_close": 150.0, "v": 1_000}
        assert scout._evaluate_bar("NVDA", bar) is None


class TestUnusualWhalesFlowScout:
    def test_evaluate_alert_large_call(self):
        from app.services.scouts.unusual_whales_flow_scout import UnusualWhalesFlowScout
        scout = UnusualWhalesFlowScout()
        alert = {"ticker": "MSFT", "premium": 500_000, "put_call": "call", "is_sweep": True}
        payload = scout._evaluate_alert(alert)
        assert payload is not None
        assert payload.symbol == "MSFT"
        assert payload.direction == "bullish"
        assert payload.priority <= 2

    def test_evaluate_alert_below_threshold_returns_none(self):
        from app.services.scouts.unusual_whales_flow_scout import UnusualWhalesFlowScout
        scout = UnusualWhalesFlowScout()
        alert = {"ticker": "AMD", "premium": 10_000, "put_call": "call"}
        assert scout._evaluate_alert(alert) is None

    def test_evaluate_alert_put(self):
        from app.services.scouts.unusual_whales_flow_scout import UnusualWhalesFlowScout
        scout = UnusualWhalesFlowScout()
        alert = {"ticker": "SPY", "premium": 1_000_000, "put_call": "put"}
        payload = scout._evaluate_alert(alert)
        assert payload.direction == "bearish"


class TestUnusualWhalesDarkpoolScout:
    def test_evaluate_print_large_buy(self):
        from app.services.scouts.unusual_whales_darkpool_scout import UnusualWhalesDarkpoolScout
        scout = UnusualWhalesDarkpoolScout()
        print_ = {"ticker": "GOOGL", "size": 5_000_000, "side": "buy"}
        payload = scout._evaluate_print(print_)
        assert payload is not None
        assert payload.direction == "bullish"

    def test_evaluate_print_below_threshold_returns_none(self):
        from app.services.scouts.unusual_whales_darkpool_scout import UnusualWhalesDarkpoolScout
        scout = UnusualWhalesDarkpoolScout()
        print_ = {"ticker": "X", "size": 100_000, "side": "buy"}
        assert scout._evaluate_print(print_) is None


class TestFinvizMomentumScout:
    def test_evaluate_row_momentum(self):
        from app.services.scouts.finviz_momentum_scout import FinvizMomentumScout
        scout = FinvizMomentumScout()
        row = {"Ticker": "crm", "RSI (14)": "62", "Change": "2.5%", "Volume": "1,200,000"}
        payload = scout._evaluate_row(row)
        assert payload is not None
        assert payload.symbol == "CRM"
        assert payload.direction == "bullish"

    def test_evaluate_row_no_ticker_returns_none(self):
        from app.services.scouts.finviz_momentum_scout import FinvizMomentumScout
        scout = FinvizMomentumScout()
        assert scout._evaluate_row({}) is None


class TestFinvizBreakoutScout:
    def test_evaluate_row_breakout(self):
        from app.services.scouts.finviz_breakout_scout import FinvizBreakoutScout
        scout = FinvizBreakoutScout()
        row = {"Ticker": "NVDA", "Change": "4.2%", "Rel Volume": "3.5"}
        payload = scout._evaluate_row(row)
        assert payload is not None
        assert payload.symbol == "NVDA"
        assert payload.signal_type == "technical_breakout"

    def test_evaluate_row_empty_returns_none(self):
        from app.services.scouts.finviz_breakout_scout import FinvizBreakoutScout
        scout = FinvizBreakoutScout()
        assert scout._evaluate_row({}) is None


class TestFredMacroScout:
    def test_evaluate_series_shift_detected(self):
        from app.services.scouts.fred_macro_scout import FredMacroScout
        scout = FredMacroScout()
        obs = [{"value": "5.5", "date": "2026-03-08"}, {"value": "5.0", "date": "2026-02-08"}]
        payload = scout._evaluate_series("FEDFUNDS", "Fed Funds Rate", "bearish", obs)
        assert payload is not None
        assert payload.symbol == "SPY"
        assert payload.signal_type == "macro_shift"
        assert payload.attributes["change_pct"] > 0

    def test_evaluate_series_no_change_returns_none(self):
        from app.services.scouts.fred_macro_scout import FredMacroScout
        scout = FredMacroScout()
        obs = [{"value": "5.0", "date": "2026-03-08"}, {"value": "5.0", "date": "2026-02-08"}]
        assert scout._evaluate_series("FEDFUNDS", "Fed Funds Rate", "bearish", obs) is None

    def test_evaluate_series_needs_two_observations(self):
        from app.services.scouts.fred_macro_scout import FredMacroScout
        scout = FredMacroScout()
        assert scout._evaluate_series("FEDFUNDS", "Fed Funds Rate", "bearish", []) is None


class TestSecEdgarScout:
    @pytest.mark.anyio
    async def test_scan_ticker_no_cik_returns_empty(self):
        from app.services.scouts.sec_edgar_scout import SecEdgarScout
        scout = SecEdgarScout()
        tickers_data = {}   # empty — no CIK found
        with patch("app.services.sec_edgar_service.SecEdgarService") as MockSvc:
            instance = MockSvc.return_value
            instance.find_cik_by_ticker = MagicMock(return_value=None)
            results = await scout._scan_ticker("AAPL", tickers_data)
        assert results == []

    @pytest.mark.anyio
    async def test_scan_ticker_recent_8k_detected(self):
        from app.services.scouts.sec_edgar_scout import SecEdgarScout
        from datetime import datetime, timezone, timedelta
        scout = SecEdgarScout()

        recent_ts = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

        with patch("app.services.sec_edgar_service.SecEdgarService") as MockSvc:
            instance = MockSvc.return_value
            instance.find_cik_by_ticker = MagicMock(return_value="0000320193")
            instance.get_submissions = AsyncMock(return_value={
                "filings": {"recent": {
                    "form": ["8-K"],
                    "filingDate": [recent_ts],
                    "accessionNumber": ["0001234-26-000001"],
                    "primaryDocument": ["form8k.htm"],
                }}
            })
            results = await scout._scan_ticker("AAPL", {})

        assert len(results) == 1
        assert results[0].signal_type == "filing_catalyst"


class TestNewsSentimentScout:
    def test_extract_tickers_dollar_prefix(self):
        from app.services.scouts.news_sentiment_scout import NewsSentimentScout
        scout = NewsSentimentScout()
        tickers = scout._extract_tickers("$AAPL surges after earnings beat")
        assert "AAPL" in tickers

    def test_extract_tickers_plain(self):
        from app.services.scouts.news_sentiment_scout import NewsSentimentScout
        scout = NewsSentimentScout()
        tickers = scout._extract_tickers("NVDA reports record revenue")
        assert "NVDA" in tickers

    def test_extract_tickers_unknown_word_excluded(self):
        from app.services.scouts.news_sentiment_scout import NewsSentimentScout
        scout = NewsSentimentScout()
        tickers = scout._extract_tickers("CEO says FAKEWORD XYZ gains momentum")
        assert "FAKEWORD" not in tickers


class TestSocialSentimentScout:
    def test_evaluate_entry_spike(self):
        from app.services.scouts.social_sentiment_scout import SocialSentimentScout
        scout = SocialSentimentScout()
        entry = {
            "ticker": "GME", "mentions": 500, "avg_mentions": 50,
            "bullish": 0.8, "bearish": 0.1, "platform": "reddit",
        }
        payload = scout._evaluate_entry(entry)
        assert payload is not None
        assert payload.symbol == "GME"
        assert payload.direction == "bullish"

    def test_evaluate_entry_no_spike_returns_none(self):
        from app.services.scouts.social_sentiment_scout import SocialSentimentScout
        scout = SocialSentimentScout()
        entry = {
            "ticker": "GME", "mentions": 5, "avg_mentions": 50,
            "bullish": 0.5, "bearish": 0.5,
        }
        assert scout._evaluate_entry(entry) is None

    def test_evaluate_entry_no_symbol_returns_none(self):
        from app.services.scouts.social_sentiment_scout import SocialSentimentScout
        scout = SocialSentimentScout()
        assert scout._evaluate_entry({"mentions": 500, "avg_mentions": 50}) is None


class TestSectorRotationScout:
    def test_bar_change_positive(self):
        from app.services.scouts.sector_rotation_scout import SectorRotationScout
        assert SectorRotationScout._bar_change({"c": 105.0, "prev_close": 100.0}) == pytest.approx(0.05)

    def test_bar_change_zero_prev_close(self):
        from app.services.scouts.sector_rotation_scout import SectorRotationScout
        assert SectorRotationScout._bar_change({"c": 100.0, "prev_close": 0.0}) == 0.0

    def test_bar_change_missing_returns_zero(self):
        from app.services.scouts.sector_rotation_scout import SectorRotationScout
        assert SectorRotationScout._bar_change({}) == 0.0


# ===========================================================================
# MessageBus topic registration
# ===========================================================================

class TestMessageBusTopics:
    def test_scout_heartbeat_topic_registered(self):
        from app.core.message_bus import MessageBus
        assert "scout.heartbeat" in MessageBus.VALID_TOPICS

    def test_swarm_idea_topic_registered(self):
        from app.core.message_bus import MessageBus
        assert "swarm.idea" in MessageBus.VALID_TOPICS

    def test_scout_discovery_topic_registered(self):
        from app.core.message_bus import MessageBus
        assert "scout.discovery" in MessageBus.VALID_TOPICS
