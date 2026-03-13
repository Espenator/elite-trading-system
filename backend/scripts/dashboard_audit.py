#!/usr/bin/env python3
"""
Dashboard data path audit — GET each endpoint used by Dashboard.jsx and print status + data summary.
Run from backend/: python scripts/dashboard_audit.py
"""
import sys
from pathlib import Path

# Ensure backend app is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient


def _summary(data, keys):
    """Return a short summary string from response data."""
    if data is None:
        return "null"
    if isinstance(data, list):
        return f"len={len(data)}"
    if not isinstance(data, dict):
        return type(data).__name__
    for key in keys:
        val = data.get(key)
        if val is not None:
            if isinstance(val, list):
                return f"{key}=len({len(val)})"
            if isinstance(val, dict):
                return f"{key}=dict"
            return f"{key}=ok"
    return "dict"


def main():
    from app.main import app
    client = TestClient(app)

    endpoints = [
        ("GET", "/api/v1/signals/", "signals", ["signals"]),
        ("GET", "/api/v1/signals/kelly-ranked", "kellyRanked", ["kellyRanked", "kelly"]),
        ("GET", "/api/v1/portfolio", "portfolio", ["positions", "equity"]),
        ("GET", "/api/v1/market/indices", "marketIndices", ["SPY", "indices"]),
        ("GET", "/api/v1/openclaw", "openclaw", ["regime"]),
        ("GET", "/api/v1/performance", "performance", ["portfolioValue", "winRate"]),
        ("GET", "/api/v1/agents", "agents", ["agents"]),
        ("GET", "/api/v1/agents/consensus", "agentConsensus", ["consensus"]),
        ("GET", "/api/v1/performance/equity", "performanceEquity", ["equity", "curve"]),
        ("GET", "/api/v1/risk/risk-score", "riskScore", ["score"]),
        ("GET", "/api/v1/agents/alerts", "systemAlerts", ["alerts"]),
        ("GET", "/api/v1/flywheel", "flywheel", ["metrics"]),
        ("GET", "/api/v1/sentiment", "sentiment", ["scores", "summary"]),
        ("GET", "/api/v1/cognitive/dashboard", "cognitiveDashboard", ["memory"]),
        ("GET", "/api/v1/signals/SPY/technicals", "signals/SPY/technicals", ["technicals"]),
        ("GET", "/api/v1/agents/swarm-topology/SPY", "swarmTopology/SPY", ["nodes", "topology"]),
        ("GET", "/api/v1/data-sources/", "dataSources", ["id"]),
        ("GET", "/api/v1/risk/proposal/SPY", "risk/proposal/SPY", ["proposal"]),
        ("GET", "/api/v1/quotes/SPY/book", "quotes/SPY/book", ["bids", "asks"]),
        ("GET", "/api/v1/cns/homeostasis/vitals", "cnsHomeostasis", ["mode"]),
        ("GET", "/api/v1/cns/circuit-breaker/status", "cnsCircuitBreaker", ["checks", "fired"]),
        ("GET", "/api/v1/cns/agents/health", "cnsAgentsHealth", ["agents", "summary"]),
        ("GET", "/api/v1/cns/council/last-verdict", "cnsLastVerdict", ["symbol"]),
        ("GET", "/api/v1/cns/profit-brain", "cnsProfitBrain", ["mode", "health"]),
    ]

    print("Dashboard data path audit (http://localhost:5173/dashboard)")
    print("=" * 60)
    ok = 0
    fail = 0
    for method, path, label, keys in endpoints:
        try:
            if method == "GET":
                r = client.get(path)
            else:
                r = client.request(method, path)
            status = r.status_code
            if status == 200:
                ok += 1
                data = r.json()
                summary = _summary(data, keys)
                print(f"  OK   {label:28} -> 200  {summary}")
            else:
                fail += 1
                print(f"  FAIL {label:28} -> {status}  {r.text[:50]}...")
        except Exception as e:
            fail += 1
            print(f"  ERR  {label:28} -> {type(e).__name__}: {e}")
    print("=" * 60)
    print(f"  Total: {ok} OK, {fail} failed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
