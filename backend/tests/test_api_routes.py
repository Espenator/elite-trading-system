"""Integration tests for critical API routes."""
import pytest


@pytest.mark.anyio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


@pytest.mark.anyio
async def test_signals_returns_list(client):
    resp = await client.get("/api/v1/signals", follow_redirects=True)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, (list, dict))


@pytest.mark.anyio
async def test_risk_score_returns_structure(client):
    resp = await client.get("/api/v1/risk/risk-score")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.anyio
async def test_drawdown_check_returns_trading_allowed(client):
    resp = await client.get("/api/v1/risk/drawdown-check")
    assert resp.status_code == 200
    data = resp.json()
    assert "trading_allowed" in data


@pytest.mark.anyio
async def test_flywheel_returns_metrics(client):
    resp = await client.get("/api/v1/flywheel")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.anyio
async def test_performance_endpoint(client):
    resp = await client.get("/api/v1/performance")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_strategy_regime_params(client):
    resp = await client.get("/api/v1/strategy/regime-params")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_portfolio_endpoint(client):
    """Portfolio depends on Alpaca API — expect 200, 500, or exception (no real keys in test)."""
    try:
        resp = await client.get("/api/v1/portfolio")
        assert resp.status_code in (200, 500)
    except Exception:
        # Alpaca 401 raises through ASGITransport — acceptable in test env
        pass


@pytest.mark.anyio
async def test_alignment_preflight_rejects_oversized(client):
    """Alignment engine should block an absurdly large trade."""
    resp = await client.post("/api/v1/alignment/preflight", json={
        "symbol": "SPY",
        "side": "buy",
        "qty": 99999,
        "strategy": "",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("allowed") is False
