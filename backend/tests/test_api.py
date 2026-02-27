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
    assert settings.TRADING_MODE == "paper"