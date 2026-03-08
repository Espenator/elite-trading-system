"""
Test: Every frontend api.js endpoint must resolve to a non-404 backend route.

AUDIT FIX (P4): This test programmatically verifies that every endpoint defined
in frontend-v2/src/api.js has a corresponding route registered in the FastAPI app.

How it works:
  - Extracts all endpoint paths from the FastAPI app's route table
  - Compares against the expected endpoints from api.js
  - Fails with a clear message listing all mismatched routes

This prevents future frontend↔backend drift from silently creating 404s.
"""

import pytest
from app.main import app


# Every endpoint the frontend expects (from api.js → API_CONFIG.endpoints).
# Format: the resolved path after /api/v1 prefix is applied.
EXPECTED_FRONTEND_ENDPOINTS = [
    # ---- Existing core endpoints ----
    "/api/v1/stocks",
    "/api/v1/quotes",
    "/api/v1/orders",
    "/api/v1/system",
    "/api/v1/system/event-bus/status",
    "/api/v1/signals/",
    "/api/v1/backtest",
    "/api/v1/backtest/runs",
    "/api/v1/backtest/results",
    "/api/v1/backtest/optimization",
    "/api/v1/backtest/walkforward",
    "/api/v1/backtest/montecarlo",
    "/api/v1/backtest/regime",
    "/api/v1/backtest/rolling-sharpe",
    "/api/v1/backtest/trade-distribution",
    "/api/v1/backtest/kelly-comparison",
    "/api/v1/backtest/correlation",
    "/api/v1/backtest/sector-exposure",
    "/api/v1/backtest/drawdown-analysis",
    "/api/v1/status",
    "/api/v1/agents",
    "/api/v1/agents/summary",
    "/api/v1/data-sources/",
    "/api/v1/sentiment",
    "/api/v1/youtube-knowledge",
    "/api/v1/flywheel",
    "/api/v1/portfolio",
    "/api/v1/risk",
    "/api/v1/strategy",
    "/api/v1/performance",
    "/api/v1/performance/trades",
    "/api/v1/logs",
    "/api/v1/alerts",
    "/api/v1/patterns",
    "/api/v1/settings",
    "/api/v1/openclaw",
    "/api/v1/market",
    "/api/v1/market/indices",
    "/api/v1/ml-brain",
    "/api/v1/risk-shield",
    "/api/v1/risk/kelly-sizer",
    "/api/v1/risk/position-sizing",
    "/api/v1/risk/drawdown-check",
    "/api/v1/risk/dynamic-stop-loss",
    "/api/v1/risk/risk-score",
    "/api/v1/signals/kelly-ranked",
    "/api/v1/strategy/pre-trade-check/{symbol}",  # path param
    "/api/v1/agents/swarm-topology",
    "/api/v1/agents/conference",
    "/api/v1/agents/teams",
    "/api/v1/agents/drift",
    "/api/v1/agents/alerts",
    "/api/v1/agents/resources",
    # ---- Alpaca proxy ----
    "/api/v1/alpaca/account",
    "/api/v1/alpaca/positions",
    "/api/v1/alpaca/orders",
    "/api/v1/alpaca/activities",
    "/api/v1/orders/advanced",
    # ---- Alignment engine ----
    "/api/v1/alignment/settings",
    "/api/v1/alignment/evaluate",
    "/api/v1/alignment/verdicts",
    "/api/v1/alignment/stats",
    "/api/v1/alignment/bright-lines",
    "/api/v1/alignment/constellation",
    "/api/v1/alignment/metacognition",
    "/api/v1/alignment/critique",
    # ---- Council ----
    "/api/v1/council/evaluate",
    "/api/v1/council/latest",
    # ---- Feature store ----
    "/api/v1/features/latest",
    "/api/v1/features/compute",
    # ---- Device & system ----
    "/api/v1/system/device",
    # ---- Flywheel scheduler ----
    "/api/v1/flywheel/scheduler",
    "/api/v1/flywheel/kpis",
    "/api/v1/flywheel/performance",
    "/api/v1/flywheel/signals/staged",
    "/api/v1/flywheel/models",
    "/api/v1/flywheel/logs",
    "/api/v1/flywheel/features",
    # ---- CNS ----
    "/api/v1/cns/homeostasis/vitals",
    "/api/v1/cns/circuit-breaker/status",
    "/api/v1/cns/agents/health",
    "/api/v1/cns/blackboard/current",
    "/api/v1/cns/postmortems",
    "/api/v1/cns/postmortems/attribution",
    "/api/v1/cns/directives",
    "/api/v1/cns/council/last-verdict",
    "/api/v1/cns/profit-brain",
    # ---- Cognitive ----
    "/api/v1/cognitive/dashboard",
    "/api/v1/cognitive/snapshots",
    "/api/v1/cognitive/calibration",
    # ---- Swarm intelligence (NEW - Bug 3 fix) ----
    "/api/v1/swarm/turbo/status",
    "/api/v1/swarm/hyper/status",
    "/api/v1/swarm/news/status",
    "/api/v1/swarm/sweep/status",
    "/api/v1/swarm/unified/status",
    "/api/v1/swarm/outcomes/status",
    "/api/v1/swarm/outcomes/kelly",
    "/api/v1/swarm/positions/managed",
    "/api/v1/swarm/ml/scorer/status",
    # ---- Agent extended ----
    "/api/v1/agents/all-config",
    "/api/v1/agents/hitl/buffer",
    "/api/v1/agents/hitl/stats",
    "/api/v1/agents/attribution",
    "/api/v1/agents/elo-leaderboard",
    "/api/v1/agents/ws-channels",
    "/api/v1/agents/flow-anomalies",
    # ---- Openclaw (may be dead code) ----
    "/api/v1/openclaw/swarm-status",
    "/api/v1/openclaw/candidates",
    "/api/v1/openclaw/regime",
    "/api/v1/openclaw/macro",
    "/api/v1/openclaw/sectors",
    "/api/v1/openclaw/scan",
    "/api/v1/openclaw/memory",
    "/api/v1/openclaw/health",
    "/api/v1/openclaw/whale-flow",
    "/api/v1/openclaw/regime/transitions",
    "/api/v1/openclaw/macro/override",
    # ---- Risk gauges ----
    "/api/v1/risk/risk-gauges",
    # ---- Strategy ----
    "/api/v1/strategy/regime-params",
]


def _get_registered_paths() -> set:
    """Extract all registered route paths from the FastAPI app."""
    paths = set()
    for route in app.routes:
        if hasattr(route, "path"):
            paths.add(route.path)
    return paths


def test_all_frontend_endpoints_have_backend_routes():
    """Every endpoint in api.js must have a registered backend route.

    This test collects all paths the FastAPI app has registered and
    checks them against the frontend's expected endpoint list.
    A missing route means the frontend will get a 404.
    """
    registered = _get_registered_paths()

    missing = []
    for expected in EXPECTED_FRONTEND_ENDPOINTS:
        # Normalize: strip trailing slash for comparison
        normalized = expected.rstrip("/")
        # Check if any registered path matches (with or without trailing slash)
        found = (
            expected in registered
            or normalized in registered
            or (normalized + "/") in registered
        )
        if not found:
            missing.append(expected)

    if missing:
        msg_lines = [
            f"\n{len(missing)} frontend endpoints have NO backend route (will 404):\n",
        ]
        for m in sorted(missing):
            msg_lines.append(f"  ❌ {m}")
        msg_lines.append(
            f"\nTotal registered routes: {len(registered)}"
        )
        pytest.fail("\n".join(msg_lines))


def test_no_duplicate_routes():
    """Ensure no endpoint path is registered twice (causes confusion)."""
    from collections import Counter

    paths = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            for method in route.methods:
                paths.append(f"{method} {route.path}")

    duplicates = {p: c for p, c in Counter(paths).items() if c > 1}
    if duplicates:
        lines = ["\nDuplicate route registrations found:\n"]
        for path, count in sorted(duplicates.items()):
            lines.append(f"  ⚠️ {path} (registered {count}x)")
        pytest.fail("\n".join(lines))
