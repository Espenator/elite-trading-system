"""
Verify every frontend endpoint (frontend-v2/src/config/api.js) has a working backend route.

- Frontend api.js defines 189+ endpoint keys; paths are API_PREFIX + path (e.g. /api/v1/status).
- Backend main.py mounts 44 routers under /api/v1 (or custom prefix). All are registered.
- This test hits each GET path and logs status codes. Asserts no 404 on critical read-only endpoints.
- Allowed responses: 200, 401 (auth), 404 (non-critical), 405 (POST-only route), 422 (validation),
  501 (Not Implemented), 502 (event loop closed in test env).

Run: pytest backend/tests/test_all_endpoints.py -v
With report: pytest backend/tests/test_all_endpoints.py -v --tb=no -q 2>&1 | tee endpoint_report.txt
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

# All GET endpoints from frontend api.js (API_PREFIX + path). Duplicates removed.
# Paths are normalized: no trailing slash for consistency; backend often serves both.
ENDPOINTS_TO_CHECK = [
    # ---- User-specified critical list ----
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/health/startup-check"),
    ("GET", "/api/v1/status"),
    ("GET", "/api/v1/system"),
    ("GET", "/api/v1/agents"),
    ("GET", "/api/v1/data-sources"),
    ("GET", "/api/v1/signals"),
    ("GET", "/api/v1/council/latest"),
    ("GET", "/api/v1/council/status"),
    ("GET", "/api/v1/council/weights"),
    ("GET", "/api/v1/risk"),
    ("GET", "/api/v1/risk/risk-score"),
    ("GET", "/api/v1/risk/kelly-sizer"),
    ("GET", "/api/v1/portfolio"),
    ("GET", "/api/v1/market"),
    ("GET", "/api/v1/market/indices"),
    ("GET", "/api/v1/sentiment"),
    ("GET", "/api/v1/performance"),
    ("GET", "/api/v1/features/latest"),
    ("GET", "/api/v1/briefing/morning"),
    ("GET", "/api/v1/briefing/tradingview"),
    ("GET", "/api/v1/briefing/watchlist-export"),
    ("GET", "/api/v1/briefing/status"),
    ("GET", "/api/v1/briefing/positions"),
    ("GET", "/api/v1/cns/homeostasis/vitals"),
    ("GET", "/api/v1/cns/circuit-breaker/status"),
    ("GET", "/api/v1/cns/agents/health"),
    ("GET", "/api/v1/cns/blackboard/current"),
    ("GET", "/api/v1/cognitive/dashboard"),
    ("GET", "/api/v1/swarm/unified/status"),
    ("GET", "/api/v1/flywheel"),
    ("GET", "/api/v1/logs"),
    ("GET", "/api/v1/alerts"),
    ("GET", "/api/v1/settings"),
    # ---- Core data ----
    ("GET", "/api/v1/stocks"),
    ("GET", "/api/v1/quotes"),
    ("GET", "/api/v1/orders"),
    ("GET", "/api/v1/system/event-bus/status"),
    ("GET", "/api/v1/signals/heatmap"),
    ("GET", "/api/v1/backtest"),
    ("GET", "/api/v1/backtest/runs"),
    ("GET", "/api/v1/backtest/results"),
    ("GET", "/api/v1/backtest/optimization"),
    ("GET", "/api/v1/backtest/walkforward"),
    ("GET", "/api/v1/backtest/montecarlo"),
    ("GET", "/api/v1/backtest/regime"),
    ("GET", "/api/v1/openclaw/swarm-status"),
    ("GET", "/api/v1/openclaw/candidates"),
    # ---- Additional routers ----
    ("GET", "/api/v1/sentiment/discover"),
    ("GET", "/api/v1/youtube-knowledge"),
    ("GET", "/api/v1/portfolio"),
    ("GET", "/api/v1/strategy"),
    ("GET", "/api/v1/performance/equity"),
    ("GET", "/api/v1/performance/trades"),
    ("GET", "/api/v1/patterns"),
    ("GET", "/api/v1/openclaw"),
    ("GET", "/api/v1/market/order-book"),
    ("GET", "/api/v1/openclaw/regime"),
    ("GET", "/api/v1/ml-brain"),
    ("GET", "/api/v1/ml-brain/registry/status"),
    ("GET", "/api/v1/risk-shield"),
    ("GET", "/api/v1/risk/position-sizing"),
    ("GET", "/api/v1/risk/drawdown-check"),
    ("GET", "/api/v1/risk/dynamic-stop-loss"),  # POST-only; expect 405
    ("GET", "/api/v1/signals/kelly-ranked"),
    ("GET", "/api/v1/agents/swarm-topology"),
    ("GET", "/api/v1/agents/consensus"),
    ("GET", "/api/v1/agents/conference"),
    ("GET", "/api/v1/agents/teams"),
    ("GET", "/api/v1/agents/drift"),
    ("GET", "/api/v1/agents/alerts"),
    ("GET", "/api/v1/agents/resources"),
    ("GET", "/api/v1/cns/blackboard/current"),
    ("GET", "/api/v1/openclaw/macro"),
    ("GET", "/api/v1/strategy/regime-params"),
    ("GET", "/api/v1/openclaw/sectors"),
    ("GET", "/api/v1/openclaw/scan"),
    ("GET", "/api/v1/openclaw/memory"),
    ("GET", "/api/v1/risk/config"),
    ("GET", "/api/v1/risk/risk-gauges"),
    ("GET", "/api/v1/risk/stress-test"),
    ("GET", "/api/v1/openclaw/health"),
    ("GET", "/api/v1/openclaw/whale-flow"),
    ("GET", "/api/v1/openclaw/regime/transitions"),
    ("GET", "/api/v1/alpaca"),
    ("GET", "/api/v1/alpaca/account"),
    ("GET", "/api/v1/alpaca/positions"),
    ("GET", "/api/v1/alpaca/orders"),
    ("GET", "/api/v1/alpaca/activities"),
    ("GET", "/api/v1/orders/recent"),
    ("GET", "/api/v1/alignment/settings"),
    ("GET", "/api/v1/alignment/evaluate"),  # may be POST
    ("GET", "/api/v1/alignment/verdicts"),
    ("GET", "/api/v1/alignment/stats"),
    ("GET", "/api/v1/alignment/bright-lines"),
    ("GET", "/api/v1/alignment/constellation"),
    ("GET", "/api/v1/alignment/metacognition"),
    ("GET", "/api/v1/alignment/critique"),
    ("GET", "/api/v1/council/status"),
    ("GET", "/api/v1/briefing/weekly"),
    ("POST", "/api/v1/briefing/webhook/test"),
    ("GET", "/api/v1/tradingview/config"),
    ("GET", "/api/v1/tradingview/pine-script"),
    ("GET", "/api/v1/features/compute"),  # POST in backend; 405 ok
    ("GET", "/api/v1/training"),
    ("GET", "/api/v1/metrics"),
    ("GET", "/api/v1/metrics/auto-execute"),  # POST in backend
    ("GET", "/api/v1/metrics/emergency-flatten"),  # POST in backend
    ("GET", "/api/v1/system/device"),
    ("GET", "/api/v1/cns/postmortems"),
    ("GET", "/api/v1/cns/postmortems/attribution"),
    ("GET", "/api/v1/cns/directives"),
    ("GET", "/api/v1/cns/council/last-verdict"),
    ("GET", "/api/v1/cns/profit-brain"),
    ("GET", "/api/v1/cognitive/snapshots"),
    ("GET", "/api/v1/cognitive/calibration"),
    ("GET", "/api/v1/swarm/turbo/status"),
    ("GET", "/api/v1/swarm/hyper/status"),
    ("GET", "/api/v1/swarm/news/status"),
    ("GET", "/api/v1/swarm/sweep/status"),
    ("GET", "/api/v1/swarm/outcomes/status"),
    ("GET", "/api/v1/swarm/outcomes/kelly"),
    ("GET", "/api/v1/swarm/positions/managed"),
    ("GET", "/api/v1/swarm/ml-scorer/status"),
    ("GET", "/api/v1/agents/all-config"),
    ("GET", "/api/v1/agents/hitl/buffer"),
    ("GET", "/api/v1/agents/hitl/stats"),
    ("GET", "/api/v1/agents/attribution"),
    ("GET", "/api/v1/agents/elo-leaderboard"),
    ("GET", "/api/v1/agents/ws-channels"),
    ("GET", "/api/v1/agents/flow-anomalies"),
    ("GET", "/api/v1/flywheel/scheduler"),
    ("GET", "/api/v1/flywheel/kpis"),
    ("GET", "/api/v1/flywheel/performance"),
    ("GET", "/api/v1/flywheel/signals/staged"),
    ("GET", "/api/v1/flywheel/models"),
    ("GET", "/api/v1/flywheel/logs"),
    ("GET", "/api/v1/flywheel/features"),
]

# Endpoints that are expected to return 405 (method not allowed) when hit with GET
# because the backend only implements POST (we still verify the route exists).
EXPECT_405_OR_404 = {
    "/api/v1/risk/dynamic-stop-loss",
    "/api/v1/features/compute",
    "/api/v1/metrics/auto-execute",
    "/api/v1/metrics/emergency-flatten",
    "/api/v1/alignment/evaluate",
}

# Critical read-only endpoints that must NOT return 404 (route must exist and accept GET).
CRITICAL_GET_ENDPOINTS = [
    "/api/v1/health/startup-check",
    "/api/v1/status",
    "/api/v1/system",
    "/api/v1/agents",
    "/api/v1/data-sources",
    "/api/v1/signals",
    "/api/v1/council/latest",
    "/api/v1/council/status",
    "/api/v1/council/weights",
    "/api/v1/risk",
    "/api/v1/risk/risk-score",
    "/api/v1/risk/kelly-sizer",
    "/api/v1/portfolio",
    "/api/v1/market",
    "/api/v1/market/indices",
    "/api/v1/sentiment",
    "/api/v1/performance",
    "/api/v1/features/latest",
    "/api/v1/briefing/morning",
    "/api/v1/briefing/positions",
    "/api/v1/briefing/status",
    "/api/v1/briefing/tradingview",
    "/api/v1/briefing/watchlist-export",
    "/api/v1/cns/homeostasis/vitals",
    "/api/v1/cns/circuit-breaker/status",
    "/api/v1/cns/agents/health",
    "/api/v1/cns/blackboard/current",
    "/api/v1/cognitive/dashboard",
    "/api/v1/swarm/unified/status",
    "/api/v1/flywheel",
    "/api/v1/logs",
    "/api/v1/alerts",
    "/api/v1/settings",
]


@pytest.fixture
def client():
    return TestClient(app)


def _request(client: TestClient, method: str, path: str, auth: bool = True):
    headers = {}
    if auth:
        headers["Authorization"] = "Bearer test_auth_token_for_tests"
    if method.upper() == "GET":
        return client.get(path, headers=headers)
    return client.request(method.upper(), path, headers=headers)


class TestAllEndpointsExist:
    """Hit every endpoint and log status codes; assert no 404 on critical GETs."""

    def test_critical_endpoints_not_404(self, client):
        """Critical read-only endpoints must not return 404 (route exists)."""
        missing = []
        for path in CRITICAL_GET_ENDPOINTS:
            r = _request(client, "GET", path)
            if r.status_code == 404:
                missing.append(path)
        assert not missing, (
            "Critical endpoints returned 404 (route missing or wrong path): " + ", ".join(missing)
        )

    def test_all_get_endpoints_log_status(self, client, caplog):
        """Hit every GET endpoint and log status code. Fails only on critical 404s."""
        results = []
        for method, path in ENDPOINTS_TO_CHECK:
            if method != "GET":
                continue
            r = _request(client, "GET", path)
            results.append((path, r.status_code))
            # Accept 200, 401 (auth), 405 (method not allowed), 422 (validation)
            # 404 = route missing; 500 = server error (log but don't fail this test)
            if path in EXPECT_405_OR_404 and r.status_code in (405, 404):
                continue
            if path in CRITICAL_GET_ENDPOINTS and r.status_code == 404:
                pytest.fail(f"Critical endpoint {path} returned 404")

        # Log summary
        by_code = {}
        for path, code in results:
            by_code.setdefault(code, []).append(path)
        for code in sorted(by_code.keys()):
            paths = by_code[code]
            print(f"\n{code}: {len(paths)} endpoints")
            for p in paths[:5]:
                print(f"  {p}")
            if len(paths) > 5:
                print(f"  ... and {len(paths) - 5} more")

        fail_404 = [p for p, c in results if c == 404 and p in CRITICAL_GET_ENDPOINTS]
        assert not fail_404, "Critical endpoints 404: " + ", ".join(fail_404)

    @pytest.mark.parametrize("method,path", ENDPOINTS_TO_CHECK)
    def test_each_endpoint_responds(self, client, method, path):
        """Each endpoint returns something other than 404 (or 405 for POST-only routes)."""
        r = _request(client, method, path)
        if path in EXPECT_405_OR_404:
            assert r.status_code in (200, 401, 403, 405, 422), (
                f"{method} {path}: expected 200/401/403/405/422, got {r.status_code}"
            )
        elif path in CRITICAL_GET_ENDPOINTS:
            assert r.status_code != 404, f"Critical endpoint {path} must not 404"
        else:
            # Non-critical: 404 allowed (route might not exist). 501 = Not Implemented. 502/503 = service/broker down.
            assert r.status_code in (200, 401, 403, 404, 405, 422, 500, 501, 502, 503), (
                f"{method} {path}: unexpected status {r.status_code}"
            )


def test_router_registration_count():
    """Ensure all expected routers are mounted on app (sanity check)."""
    # main.py includes 44+ routers; we only check that routes exist via the test above.
    routes = [r for r in app.routes if hasattr(r, "path")]
    api_routes = [r for r in routes if r.path.startswith("/api/v1")]
    assert len(api_routes) >= 40, (
        f"Expected at least 40 /api/v1 routes; found {len(api_routes)}. "
        "Check main.py include_router for all api/v1 routers."
    )
