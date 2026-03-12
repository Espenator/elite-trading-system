"""Contract test for /api/v1/alignment/preflight.

Purpose: Prevent "governance-by-appearance" failures where the endpoint
exists but returns a schema the frontend can't render, silently breaking
the alignment UI.

The frontend (AlignmentEngine.jsx + AlignmentPreflight.jsx) depends on
this EXACT response shape:
  {
    "allowed": bool,
    "blockedBy": str | null,
    "summary": str,
    "checks": [{"name": str, "passed": bool, "detail": str | null}, ...],
    "timestamp": str (ISO 8601)
  }

If ANY field is missing or changes type, the UI breaks silently.
This test locks the contract so future merges can't break it.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
REQUIRED_TOP_KEYS = {"allowed", "blockedBy", "summary", "checks", "timestamp"}
REQUIRED_CHECK_KEYS = {"name", "passed"}

DEFAULT_PAYLOAD = {
    "symbol": "SPY",
    "side": "buy",
    "quantity": 1,
    "strategy": "manual",
}

BLOCKED_PAYLOAD = {
    "symbol": "SPY",
    "side": "buy",
    "quantity": 99999,  # exceeds position limit
    "strategy": "",       # empty strategy fails mandate check
}

def _auth_headers():
    """Build auth headers at call time (after conftest sets API_AUTH_TOKEN)."""
    import os
    return {"Authorization": f"Bearer {os.environ.get('API_AUTH_TOKEN', '')}"}


# ---------------------------------------------------------------------------
# Contract Tests
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_preflight_returns_200():
    """POST /preflight must return 200, never 404/500."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/alignment/preflight", json=DEFAULT_PAYLOAD, headers=_auth_headers())
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


@pytest.mark.anyio
async def test_preflight_schema_has_required_top_keys():
    """Response must include all keys the frontend destructures."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/alignment/preflight", json=DEFAULT_PAYLOAD, headers=_auth_headers())
    body = r.json()
    missing = REQUIRED_TOP_KEYS - set(body.keys())
    assert not missing, f"Missing top-level keys: {missing}. Got: {list(body.keys())}"


@pytest.mark.anyio
async def test_preflight_allowed_is_bool():
    """'allowed' must be a boolean — frontend does `if (verdict.allowed)`."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/alignment/preflight", json=DEFAULT_PAYLOAD, headers=_auth_headers())
    body = r.json()
    assert isinstance(body["allowed"], bool), f"'allowed' must be bool, got {type(body['allowed'])}"


@pytest.mark.anyio
async def test_preflight_checks_is_list_of_dicts():
    """'checks' must be a list of objects with at least {name, passed}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/alignment/preflight", json=DEFAULT_PAYLOAD, headers=_auth_headers())
    checks = r.json()["checks"]
    assert isinstance(checks, list), f"'checks' must be list, got {type(checks)}"
    assert len(checks) >= 1, "Must have at least 1 check"
    for i, c in enumerate(checks):
        missing = REQUIRED_CHECK_KEYS - set(c.keys())
        assert not missing, f"Check[{i}] missing keys: {missing}. Got: {c}"
        assert isinstance(c["passed"], bool), f"Check[{i}].passed must be bool"


@pytest.mark.anyio
async def test_preflight_timestamp_is_iso_string():
    """'timestamp' must be ISO 8601 parseable."""
    from datetime import datetime
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/alignment/preflight", json=DEFAULT_PAYLOAD, headers=_auth_headers())
    ts = r.json()["timestamp"]
    assert isinstance(ts, str), f"'timestamp' must be str, got {type(ts)}"
    try:
        datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"'timestamp' is not valid ISO 8601: {ts}")


@pytest.mark.anyio
async def test_preflight_allowed_trade_passes():
    """Normal small trade should be ALLOWED."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/alignment/preflight", json=DEFAULT_PAYLOAD, headers=_auth_headers())
    body = r.json()
    assert body["allowed"] is True, f"Expected allowed=True: {body['summary']}"
    assert body["blockedBy"] is None


@pytest.mark.anyio
async def test_preflight_blocked_trade_returns_blocker():
    """Over-sized trade with empty strategy should be BLOCKED."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/alignment/preflight", json=BLOCKED_PAYLOAD, headers=_auth_headers())
    body = r.json()
    assert body["allowed"] is False, f"Expected allowed=False: {body['summary']}"
    assert body["blockedBy"] is not None, "blockedBy must name the blocking check"
    assert isinstance(body["blockedBy"], str)


@pytest.mark.anyio
async def test_preflight_summary_contains_symbol():
    """Summary must mention the symbol so the UI can display context."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/alignment/preflight", json=DEFAULT_PAYLOAD, headers=_auth_headers())
    summary = r.json()["summary"]
    assert "SPY" in summary, f"Summary must contain symbol: {summary}"


@pytest.mark.anyio
async def test_preflight_six_checks():
    """Must run all 6 constitutive design pattern checks."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/alignment/preflight", json=DEFAULT_PAYLOAD, headers=_auth_headers())
    checks = r.json()["checks"]
    assert len(checks) == 6, f"Expected 6 checks (one per design pattern), got {len(checks)}"


# ---------------------------------------------------------------------------
# Smoke: other alignment endpoints exist and return 200
# ---------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.parametrize("path", [
    "/api/v1/alignment/state",
    "/api/v1/alignment/patterns",
    "/api/v1/alignment/audit",
    "/api/v1/alignment/constitution",
    "/api/v1/alignment/drift-history",
    "/api/v1/alignment/verdicts",
])
async def test_alignment_get_endpoints_return_200(path):
    """All GET alignment endpoints must return 200, not 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(path)
    assert r.status_code == 200, f"{path} returned {r.status_code}: {r.text}"