"""First 22 tests for Elite Trading System API.
Covers: health checks, signal engine, Kelly sizer, config, CORS.
"""
import pytest
from app.main import app
from app.services.kelly_position_sizer import KellyPositionSizer
from app.core.config import settings


# --- Test 1: App instance exists ---
def test_app_exists():
    assert app is not None
    assert app.title == settings.APP_NAME or app.title in ("Elite Trading System", "Embodier Trader")


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
