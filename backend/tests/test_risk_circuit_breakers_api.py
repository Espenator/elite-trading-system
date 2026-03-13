"""Risk API: GET /api/v1/risk/circuit-breakers returns 10 circuit breaker configs."""
import pytest


@pytest.mark.anyio
async def test_circuit_breakers_endpoint_returns_ten_breakers(client):
    """Risk circuit-breakers endpoint returns 10 breaker definitions."""
    resp = await client.get("/api/v1/risk/circuit-breakers")
    assert resp.status_code == 200
    data = resp.json()
    breakers = data.get("breakers", [])
    assert len(breakers) == 10
    names = {b.get("name") for b in breakers}
    assert "Max Daily Drawdown" in names
    assert "Max Leverage" in names
    assert "Max Concentration" in names
