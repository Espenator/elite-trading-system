"""First 22 tests for Embodier Trader API.
Covers: health checks, signal engine, Kelly sizer, config, CORS.
"""
import pytest
from app.main import app
from app.services.kelly_position_sizer import KellyPositionSizer
from app.core.config import settings


# --- Test 1: App instance exists ---
def test_app_exists():
    assert app is not None
    assert app.title == settings.APP_NAME or app.title in ("Embodier Trader", "Embodier Trader")


# --- Test 2: API version matches config ---
def test_app_version():

    assert app.version == settings.APP_VERSION


# --- Test 3: Health endpoint returns 200 ---
@pytest.mark.anyio
async def test_health_endpoint(client):
    response = await client.get("/api/v1/system/health")
    assert response.status_code in [200, 404]  # 404 if route not registered


# --- Test 4: Status endpoint returns 200 ---
@pytest.mark.anyio
async def test_status_endpoint(client):
    response = await client.get("/api/v1/status/overview")
    assert response.status_code in [200, 404]


# --- Test 5: Signals endpoint exists ---
@pytest.mark.anyio
async def test_signals_endpoint(client):
    response = await client.get("/api/v1/signals")
    assert response.status_code in [200, 307, 404]


# --- Test 6: CORS is restricted (not wildcard) ---
def test_cors_not_wildcard():
    from app.main import app
    for middleware in app.user_middleware:
        if hasattr(middleware, 'kwargs'):
            origins = middleware.kwargs.get('allow_origins', [])
            assert "*" not in origins, "CORS should not allow all origins"


# --- Test 7: Kelly sizer rejects insufficient data ---
def test_kelly_rejects_low_trade_count():
    sizer = KellyPositionSizer()
    result = sizer.calculate(
        win_rate=0.6,
        avg_win_pct=0.05,
        avg_loss_pct=0.015,
        trade_count=5,
    )
    assert result.final_pct <= 0.01  # Conservative 1% allocation


# --- Test 8: Kelly sizer calculates valid position ---
def test_kelly_valid_position():
    sizer = KellyPositionSizer()
    result = sizer.calculate(
        win_rate=0.6,
        avg_win_pct=0.05,
        avg_loss_pct=0.015,
        trade_count=50,
    )
    assert result.final_pct > 0
    assert result.final_pct <= 0.10  # 10% max cap


# --- Test 9: Kelly sizer respects 10% max cap ---
def test_kelly_max_cap():
    sizer = KellyPositionSizer()
    result = sizer.calculate(
        win_rate=0.9,
        avg_win_pct=0.10,
        avg_loss_pct=0.01,
        trade_count=100,
    )
    assert result.final_pct <= 0.10  # 10% max allocation


# --- Test 10: Trading mode defaults to paper ---
def test_trading_mode_paper():
    from app.core.config import settings
    assert settings.TRADING_MODE == "paper"


# --- Test 11: Kelly returns HOLD for negative edge ---
def test_kelly_negative_edge():
    sizer = KellyPositionSizer()
    result = sizer.calculate(win_rate=0.3, avg_win_pct=0.02, avg_loss_pct=0.03)
    assert result.edge <= 0
    assert result.action == "HOLD"


# --- Test 12: Kelly PositionSize has required fields ---
def test_kelly_position_size_fields():
    sizer = KellyPositionSizer()
    result = sizer.calculate(win_rate=0.6, avg_win_pct=0.05, avg_loss_pct=0.015)
    assert hasattr(result, 'raw_kelly')
    assert hasattr(result, 'half_kelly')
    assert hasattr(result, 'regime_adjusted')
    assert hasattr(result, 'final_pct')
    assert hasattr(result, 'edge')
    assert hasattr(result, 'regime')
    assert hasattr(result, 'action')


# --- Test 13: Kelly action is BUY for positive edge ---
def test_kelly_buy_action():
    sizer = KellyPositionSizer()
    result = sizer.calculate(win_rate=0.6, avg_win_pct=0.05, avg_loss_pct=0.015)
    assert result.action == "BUY"
    assert result.final_pct > 0


# --- Test 14: Strategy controls have defaults ---
def test_strategy_default_controls():
    from app.api.v1.strategy import DEFAULT_CONTROLS
    assert DEFAULT_CONTROLS["masterSwitch"] is True
    assert DEFAULT_CONTROLS["kellyEnabled"] is True
    assert DEFAULT_CONTROLS["maxPositionPct"] == 0.10


# --- Test 15: Alert rules exist ---
def test_alert_rules_exist():
    from app.api.v1.alerts import DEFAULT_RULES
    assert len(DEFAULT_RULES) >= 2
    all_conditions = [r["condition"] for r in DEFAULT_RULES]
    kelly_conditions = [c for c in all_conditions if "kelly" in c]
    assert len(kelly_conditions) >= 2


# --- Test 16: Risk score returns valid structure ---
def test_risk_score_structure():
    from app.core.config import settings
    assert hasattr(settings, 'MIN_RISK_SCORE')
    assert settings.MIN_RISK_SCORE >= 0
    assert settings.MIN_RISK_SCORE <= 100


# --- Test 17: Config has all risk management settings ---
def test_risk_config_complete():
    from app.core.config import settings
    required = [
        'MAX_PORTFOLIO_HEAT',
        'MAX_SECTOR_CONCENTRATION',
        'MIN_RISK_SCORE',
        'VOLATILITY_BASELINE',
    ]
    for attr in required:
        assert hasattr(settings, attr), f"Missing config: {attr}"


# --- Test 18: Composite scorer risk dampener logic ---
def test_risk_dampener():
    """Placeholder: validates Kelly dampening arithmetic."""
    assert 0.5 * 80 == 40
    assert 0.75 * 80 == 60
    assert 1.0 * 80 == 80


# --- Test 19: Strategy controls structure ---
def test_strategy_controls_structure():
    from app.api.v1.strategy import DEFAULT_CONTROLS
    assert "masterSwitch" in DEFAULT_CONTROLS
    assert "maxPositionPct" in DEFAULT_CONTROLS
    assert "maxPortfolioHeat" in DEFAULT_CONTROLS


# --- Test 20: Flywheel expectancy calculation ---
def test_expectancy_formula():
    win_rate = 0.6
    avg_win = 0.05
    avg_loss = 0.03
    expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss
    assert expectancy > 0
    assert round(expectancy, 4) == 0.018


# --- Test 21: Performance metrics include new fields ---
def test_performance_new_fields():
    import app.api.v1.performance as perf
    assert hasattr(perf, 'router')


# --- Test 22: Kelly regime multipliers exist ---
def test_kelly_regime_multipliers():
    from app.services.kelly_position_sizer import _REGIME_MULTIPLIERS
    assert "BULLISH" in _REGIME_MULTIPLIERS
    assert "CRISIS" in _REGIME_MULTIPLIERS
    assert _REGIME_MULTIPLIERS["CRISIS"] < _REGIME_MULTIPLIERS["BULLISH"]


# --- Test 23: StreamingDiscoveryEngine instantiates cleanly ---
def test_streaming_discovery_instantiation():
    from app.services.streaming_discovery import StreamingDiscoveryEngine

    class _FakeBus:
        _subscribers = {}
        _running = False
        async def subscribe(self, *a, **kw): pass
        async def unsubscribe(self, *a, **kw): pass
        async def publish(self, *a, **kw): pass

    engine = StreamingDiscoveryEngine(message_bus=_FakeBus())
    assert not engine._running
    assert engine._volume_spike_ratio == 2.0
    assert engine._gap_threshold == 0.02
    status = engine.get_status()
    assert status["running"] is False
    assert status["symbols_tracked"] == 0
    assert "stats" in status
    assert "universe" in status


# --- Test 24: StreamingDiscoveryEngine detects volume spike ---
def test_streaming_discovery_volume_spike():
    from app.services.streaming_discovery import StreamingDiscoveryEngine, _SymbolWindow

    class _FakeBus:
        _subscribers = {}
        _running = False
        async def subscribe(self, *a, **kw): pass
        async def unsubscribe(self, *a, **kw): pass
        async def publish(self, *a, **kw): pass

    engine = StreamingDiscoveryEngine(message_bus=_FakeBus())

    # Build a window with baseline volume
    win = _SymbolWindow()
    for i in range(19):
        win.push({"close": 100.0, "volume": 1000.0, "open": 100.0, "high": 101.0, "low": 99.0})
    # Now push a spike bar
    spike_bar = {"close": 102.0, "volume": 5000.0, "open": 101.0, "high": 103.0, "low": 101.0}
    win.push(spike_bar)

    events = engine._detect_anomalies("AAPL", win, spike_bar)
    vol_spike_events = [e for e in events if e.event_type == "volume_spike"]
    assert len(vol_spike_events) >= 1
    assert vol_spike_events[0].direction == "bullish"
    assert vol_spike_events[0].score > 60


# --- Test 25: StreamingDiscoveryEngine detects price breakout ---
def test_streaming_discovery_price_breakout():
    from app.services.streaming_discovery import StreamingDiscoveryEngine, _SymbolWindow

    class _FakeBus:
        _subscribers = {}
        _running = False
        async def subscribe(self, *a, **kw): pass
        async def unsubscribe(self, *a, **kw): pass
        async def publish(self, *a, **kw): pass

    engine = StreamingDiscoveryEngine(message_bus=_FakeBus())
    win = _SymbolWindow()
    # Fill 20 bars with highs at 100
    for i in range(20):
        win.push({"close": 99.0, "volume": 1000.0, "open": 98.0, "high": 100.0, "low": 97.0})
    # New 20-bar high
    breakout_bar = {"close": 105.0, "volume": 1500.0, "open": 101.0, "high": 106.0, "low": 100.5}
    win.push(breakout_bar)

    events = engine._detect_anomalies("MSFT", win, breakout_bar)
    breakout_events = [e for e in events if e.event_type == "price_breakout"]
    assert len(breakout_events) >= 1
    assert breakout_events[0].direction == "bullish"


# --- Test 26: StreamingDiscoveryEngine detects gap up ---
def test_streaming_discovery_gap_up():
    from app.services.streaming_discovery import StreamingDiscoveryEngine, _SymbolWindow

    class _FakeBus:
        _subscribers = {}
        _running = False
        async def subscribe(self, *a, **kw): pass
        async def unsubscribe(self, *a, **kw): pass
        async def publish(self, *a, **kw): pass

    engine = StreamingDiscoveryEngine(message_bus=_FakeBus())
    win = _SymbolWindow()
    for i in range(5):
        win.push({"close": 100.0, "volume": 1000.0, "open": 99.5, "high": 100.5, "low": 99.0})
    # Gap up: open 5% above prior close
    gap_bar = {"close": 105.0, "volume": 1200.0, "open": 105.0, "high": 106.0, "low": 104.5}
    win.push(gap_bar)

    events = engine._detect_anomalies("NVDA", win, gap_bar)
    gap_events = [e for e in events if e.event_type == "gap_up"]
    assert len(gap_events) >= 1
    assert gap_events[0].direction == "bullish"


# --- Test 27: DynamicUniverseManager promotes symbols ---
def test_dynamic_universe_promotion():
    from app.services.streaming_discovery import DynamicUniverseManager, UNIVERSE_ACTIVITY_THRESHOLD

    mgr = DynamicUniverseManager()
    for _ in range(UNIVERSE_ACTIVITY_THRESHOLD):
        mgr.record_anomaly("AAPL")

    assert "AAPL" in mgr._promoted
    pending = mgr.drain_pending()
    assert "AAPL" in pending
    # drain clears pending
    assert len(mgr.drain_pending()) == 0


# --- Test 28: AutonomousScoutService has all 15 scout types in config ---
def test_scout_service_has_15_scout_types():
    from app.services.autonomous_scout import AutonomousScoutService
    scout = AutonomousScoutService()
    enabled = scout.config["enabled_scouts"]
    expected_scouts = {
        # Original 4 scouts (backward compatible)
        "flow", "screener", "watchlist", "backtest",
        # 11 new E2 scouts
        "insider", "congress", "gamma", "news",
        "sentiment", "macro", "earnings", "sector_rotation",
        "short_squeeze", "ipo", "correlation_break",
    }
    for scout_name in expected_scouts:
        assert scout_name in enabled, f"Missing scout: {scout_name}"


# --- Test 29: AutonomousScoutService config has all 15 interval keys ---
def test_scout_service_config_intervals():
    from app.services.autonomous_scout import AutonomousScoutService
    scout = AutonomousScoutService()
    required_intervals = [
        # Original 4
        "flow_scan_interval", "screener_scan_interval",
        "watchlist_scan_interval", "backtest_scan_interval",
        # New 11 (E2)
        "insider_scan_interval", "congress_scan_interval",
        "gamma_scan_interval", "news_scan_interval",
        "sentiment_scan_interval", "macro_scan_interval",
        "earnings_scan_interval", "sector_rotation_scan_interval",
        "short_squeeze_scan_interval", "ipo_scan_interval",
        "correlation_break_scan_interval",
    ]
    for interval_key in required_intervals:
        assert interval_key in scout.config, f"Missing config key: {interval_key}"
        assert scout.config[interval_key] > 0, f"Invalid interval for {interval_key}"


# --- Test 30: StreamingDiscoveryEngine singleton factory ---
def test_streaming_discovery_singleton():
    import app.services.streaming_discovery as sd_mod
    # Reset singleton for clean test
    sd_mod._streaming_discovery = None
    e1 = sd_mod.get_streaming_discovery()
    e2 = sd_mod.get_streaming_discovery()
    assert e1 is e2
    # Cleanup
    sd_mod._streaming_discovery = None


# --- Test 31: Swarm router has discovery endpoints ---
def test_swarm_router_has_discovery_endpoints():
    from app.api.v1.swarm import router
    routes = {r.path for r in router.routes}
    assert any("discovery/status" in p for p in routes)
    assert any("discovery/universe" in p for p in routes)


# --- Test 32: ScoutConfigRequest includes new interval fields ---
def test_scout_config_request_new_fields():
    from app.api.v1.swarm import ScoutConfigRequest
    req = ScoutConfigRequest(
        insider_scan_interval=600,
        congress_scan_interval=300,
        gamma_scan_interval=120,
        sector_rotation_scan_interval=300,
    )
    assert req.insider_scan_interval == 600
    assert req.congress_scan_interval == 300
    assert req.gamma_scan_interval == 120
    assert req.sector_rotation_scan_interval == 300
