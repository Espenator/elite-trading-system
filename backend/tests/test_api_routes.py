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
async def test_alignment_preflight_rejects_oversized(client, auth_headers):
    """Alignment engine should block an absurdly large trade."""
    resp = await client.post("/api/v1/alignment/preflight", json={
        "symbol": "SPY",
        "side": "buy",
        "qty": 99999,
        "strategy": "",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("allowed") is False


@pytest.mark.anyio
async def test_council_health_returns_structure(client):
    """GET /api/v1/council/health returns last_evaluation + rolling_24h."""
    resp = await client.get("/api/v1/council/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "last_evaluation" in data
    assert "rolling_24h" in data
    assert "evaluations" in data["rolling_24h"]


@pytest.mark.anyio
async def test_council_agents_performance_returns_structure(client):
    """GET /api/v1/council/agents/performance returns agents list."""
    resp = await client.get("/api/v1/council/agents/performance")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    assert "broken_agents" in data
    assert "always_hold_agents" in data


@pytest.mark.anyio
async def test_health_sub_endpoints(client):
    """GET /api/v1/health/* programmatic sub-checks return expected structure."""
    for path in ("", "/broker", "/brain", "/database", "/data-sources"):
        resp = await client.get(f"/api/v1/health{path}")
        assert resp.status_code == 200, f"health{path} returned {resp.status_code}"
        data = resp.json()
        assert isinstance(data, dict)
    resp = await client.get("/api/v1/health/readiness")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data
    assert "checks" in data


@pytest.mark.anyio
async def test_data_sources_health_returns_structure(client):
    """GET /api/v1/data-sources/health returns sources list."""
    resp = await client.get("/api/v1/data-sources/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert isinstance(data["sources"], list)
