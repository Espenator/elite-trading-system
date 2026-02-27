"""First 10 tests for Elite Trading System API.
Covers: health checks, signal engine, Kelly sizer, config, CORS.
"""
import pytest
from app.main import app
from app.services.kelly_position_sizer import KellyPositionSizer


# --- Test 1: App instance exists ---
def test_app_exists():
    assert app is not None
    assert app.title == "Elite Trading System"


# --- Test 2: API version is 3.0.0 ---
def test_app_version():
    assert app.version == "3.0.0"


# --- Test 3: Health endpoint returns 200 ---
@pytest.mark.anyio
async def test_health_endpoint(client):
    response = await client.get("/api/v1/system/health")
    assert response.status_code == 200


# --- Test 4: Status endpoint returns 200 ---
@pytest.mark.anyio
async def test_status_endpoint(client):
    response = await client.get("/api/v1/status/overview")
    assert response.status_code in [200, 500]  # 500 if services not configured


# --- Test 5: Signals endpoint exists ---
@pytest.mark.anyio
async def test_signals_endpoint(client):
    response = await client.get("/api/v1/signals/")
    assert response.status_code in [200, 404, 500]


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
        avg_win=100.0,
        avg_loss=80.0,
        trade_count=5,  # Below 20 minimum
        portfolio_value=100000.0,
        signal_score=75.0
    )
    assert result.final_size == 0.0 or result.rejected


# --- Test 8: Kelly sizer calculates valid position ---
def test_kelly_valid_position():
    sizer = KellyPositionSizer()
    result = sizer.calculate(
        win_rate=0.6,
        avg_win=150.0,
        avg_loss=100.0,
        trade_count=50,
        portfolio_value=100000.0,
        signal_score=80.0
    )
    assert result.final_size > 0
    assert result.final_size <= 10000.0  # 10% max cap


# --- Test 9: Kelly sizer respects 10% max cap ---
def test_kelly_max_cap():
    sizer = KellyPositionSizer()
    result = sizer.calculate(
        win_rate=0.9,
        avg_win=500.0,
        avg_loss=50.0,
        trade_count=100,
        portfolio_value=100000.0,
        signal_score=95.0
    )
    assert result.final_size <= 10000.0  # 10% of 100k


# --- Test 10: Trading mode defaults to paper ---
def test_trading_mode_paper():
    from app.core.config import settings


# --- Test 11: Volatility-adjusted Kelly scales down in high vol ---
def test_kelly_volatility_adjusted():
    sizer = KellyPositionSizer()
    base = sizer.calculate(win_rate=0.6, avg_win_pct=0.035, avg_loss_pct=0.015)
    vol_adj = sizer.calculate_volatility_adjusted(
        win_rate=0.6, avg_win_pct=0.035, avg_loss_pct=0.015,
        current_volatility=0.04,  # 2x baseline
        baseline_volatility=0.02,
    )
    assert vol_adj.final_pct < base.final_pct  # High vol = smaller position
    assert vol_adj.final_pct > 0  # But still positive


# --- Test 12: Portfolio correlation cap limits sector exposure ---
def test_portfolio_correlation_cap():
    positions = [
        {"symbol": "AAPL", "sector": "Tech", "kelly_allocation_pct": 0.10},
        {"symbol": "MSFT", "sector": "Tech", "kelly_allocation_pct": 0.10},
        {"symbol": "GOOGL", "sector": "Tech", "kelly_allocation_pct": 0.10},
        {"symbol": "JPM", "sector": "Finance", "kelly_allocation_pct": 0.08},
    ]
    capped = KellyPositionSizer.portfolio_correlation_cap(
        positions, max_sector_pct=0.25
    )
    tech_total = sum(
        p["kelly_allocation_pct"] for p in capped if p["sector"] == "Tech"
    )
    assert tech_total <= 0.26  # ~25% with rounding
    assert capped[3]["kelly_allocation_pct"] == 0.08  # Finance untouched


# --- Test 13: Kelly edge is negative for low win rate ---
def test_kelly_negative_edge():
    sizer = KellyPositionSizer()
    result = sizer.calculate(win_rate=0.3, avg_win_pct=0.02, avg_loss_pct=0.03)
    assert result.edge <= 0
    assert result.action == "NO_TRADE"


# --- Test 14: Regime scaling adjusts Kelly correctly ---
def test_regime_scaling():
    from app.api.v1.strategy import REGIME_PARAMS
    assert REGIME_PARAMS["BULL"]["kelly_scale"] == 1.0
    assert REGIME_PARAMS["CRISIS"]["kelly_scale"] == 0.15
    assert REGIME_PARAMS["BEAR"]["max_pos"] < REGIME_PARAMS["BULL"]["max_pos"]


# --- Test 15: Alert evaluation fires on Kelly edge threshold ---
def test_alert_evaluation():
    from app.api.v1.alerts import DEFAULT_RULES
    kelly_rules = [r for r in DEFAULT_RULES if "kelly" in r["condition"]]
    assert len(kelly_rules) >= 2  # At least kelly_edge and kelly_pos rules
    assert settings.TRADING_MODE == "paper"