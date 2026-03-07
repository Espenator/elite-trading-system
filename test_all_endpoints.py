"""
Comprehensive API endpoint tester for Embodier Trader.
Tests every endpoint defined in the frontend api.js config.
"""
import asyncio
import json
import sys
import time
from collections import defaultdict

import httpx

BASE = "http://localhost:8000"
PREFIX = "/api/v1"

# All endpoints from frontend api.js config
GET_ENDPOINTS = {
    # Core
    "status": "/status",
    "system": "/system",
    "system/event-bus/status": "/system/event-bus/status",
    "stocks": "/stocks",
    "quotes": "/quotes",
    
    # Agents
    "agents": "/agents",
    "agents/swarm-topology": "/agents/swarm-topology",
    "agents/conference": "/agents/conference",
    "agents/teams": "/agents/teams",
    "agents/drift": "/agents/drift",
    "agents/alerts": "/agents/alerts",
    "agents/resources": "/agents/resources",
    "agents/all-config": "/agents/all-config",
    "agents/hitl/buffer": "/agents/hitl/buffer",
    "agents/hitl/stats": "/agents/hitl/stats",
    "agents/attribution": "/agents/attribution",
    "agents/elo-leaderboard": "/agents/elo-leaderboard",
    "agents/ws-channels": "/agents/ws-channels",
    "agents/flow-anomalies": "/agents/flow-anomalies",
    
    # Intelligence
    "signals": "/signals/",
    "sentiment": "/sentiment",
    "data-sources": "/data-sources/",
    
    # ML & Analysis
    "ml-brain": "/ml-brain",
    "ml-brain/models": "/ml-brain/registry/status",
    "flywheel": "/flywheel",
    "flywheel/scheduler": "/flywheel/scheduler",
    "flywheel/kpis": "/flywheel/kpis",
    "flywheel/performance": "/flywheel/performance",
    "flywheel/signals/staged": "/flywheel/signals/staged",
    "flywheel/models": "/flywheel/models",
    "flywheel/logs": "/flywheel/logs",
    "flywheel/features": "/flywheel/features",
    "patterns": "/patterns",
    
    # Backtesting
    "backtest": "/backtest",
    "backtest/runs": "/backtest/runs",
    "backtest/results": "/backtest/results",
    "backtest/optimization": "/backtest/optimization",
    "backtest/walkforward": "/backtest/walkforward",
    "backtest/montecarlo": "/backtest/montecarlo",
    "backtest/regime": "/backtest/regime",
    "backtest/rolling-sharpe": "/backtest/rolling-sharpe",
    "backtest/trade-distribution": "/backtest/trade-distribution",
    "backtest/kelly-comparison": "/backtest/kelly-comparison",
    "backtest/correlation": "/backtest/correlation",
    "backtest/sector-exposure": "/backtest/sector-exposure",
    "backtest/drawdown-analysis": "/backtest/drawdown-analysis",
    
    # Market
    "market": "/market",
    "market/indices": "/market/indices",
    
    # Execution
    "orders": "/orders",
    "portfolio": "/portfolio",
    "trades (performance)": "/performance",
    "performance/trades": "/performance/trades",
    
    # Risk
    "risk": "/risk",
    "risk/risk-score": "/risk/risk-score",
    "risk/drawdown-check": "/risk/drawdown-check",
    "risk/kelly-sizer": "/risk/kelly-sizer",
    "risk/position-sizing": "/risk/position-sizing",
    "risk/risk-gauges": "/risk/risk-gauges",
    
    # Strategy
    "strategy": "/strategy",
    "strategy/regime-params": "/strategy/regime-params",
    
    # OpenClaw
    "openclaw": "/openclaw",
    "openclaw/regime": "/openclaw/regime",
    "openclaw/macro": "/openclaw/macro",
    "openclaw/sectors": "/openclaw/sectors",
    "openclaw/scan": "/openclaw/scan",
    "openclaw/memory": "/openclaw/memory",
    "openclaw/health": "/openclaw/health",
    "openclaw/whale-flow": "/openclaw/whale-flow",
    "openclaw/regime/transitions": "/openclaw/regime/transitions",
    "openclaw/swarm-status": "/openclaw/swarm-status",
    "openclaw/candidates": "/openclaw/candidates",
    
    # Alpaca proxy
    "alpaca/account": "/alpaca/account",
    "alpaca/positions": "/alpaca/positions",
    "alpaca/orders": "/alpaca/orders",
    "alpaca/activities": "/alpaca/activities",
    
    # Alignment
    "alignment/settings": "/alignment/settings",
    "alignment/verdicts": "/alignment/verdicts",
    "alignment/stats": "/alignment/stats",
    "alignment/bright-lines": "/alignment/bright-lines",
    "alignment/constellation": "/alignment/constellation",
    "alignment/metacognition": "/alignment/metacognition",
    "alignment/critique": "/alignment/critique",
    
    # Council
    "council/latest": "/council/latest",
    
    # Features
    "features/latest": "/features/latest",
    
    # CNS
    "cns/homeostasis/vitals": "/cns/homeostasis/vitals",
    "cns/circuit-breaker/status": "/cns/circuit-breaker/status",
    "cns/agents/health": "/cns/agents/health",
    "cns/blackboard/current": "/cns/blackboard/current",
    "cns/postmortems": "/cns/postmortems",
    "cns/postmortems/attribution": "/cns/postmortems/attribution",
    "cns/directives": "/cns/directives",
    "cns/council/last-verdict": "/cns/council/last-verdict",
    "cns/profit-brain": "/cns/profit-brain",
    
    # Cognitive
    "cognitive/dashboard": "/cognitive/dashboard",
    "cognitive/snapshots": "/cognitive/snapshots",
    "cognitive/calibration": "/cognitive/calibration",
    
    # Swarm
    "swarm/turbo/status": "/swarm/turbo/status",
    "swarm/hyper/status": "/swarm/hyper/status",
    "swarm/news/status": "/swarm/news/status",
    "swarm/sweep/status": "/swarm/sweep/status",
    "swarm/unified/status": "/swarm/unified/status",
    "swarm/outcomes/status": "/swarm/outcomes/status",
    "swarm/outcomes/kelly": "/swarm/outcomes/kelly",
    "swarm/positions/managed": "/swarm/positions/managed",
    "swarm/ml/scorer/status": "/swarm/ml/scorer/status",
    
    # Settings
    "settings": "/settings",
    
    # Logs & Alerts
    "logs": "/logs",
    "alerts": "/alerts",
    
    # YouTube
    "youtube-knowledge": "/youtube-knowledge",
    
    # Device
    "system/device": "/system/device",
    
    # Kelly ranked signals
    "signals/kelly-ranked": "/signals/kelly-ranked",
}

async def test_endpoint(client, name, path):
    url = f"{BASE}{PREFIX}{path}"
    try:
        r = await client.get(url, timeout=10.0)
        status = r.status_code
        try:
            body = r.json()
            body_preview = json.dumps(body)[:200]
        except:
            body_preview = r.text[:200]
        
        if status == 200:
            return {"name": name, "path": path, "status": status, "result": "OK", "preview": body_preview}
        elif status == 404:
            return {"name": name, "path": path, "status": status, "result": "NOT_FOUND", "preview": body_preview}
        elif status == 405:
            return {"name": name, "path": path, "status": status, "result": "METHOD_NOT_ALLOWED", "preview": body_preview}
        elif status == 422:
            return {"name": name, "path": path, "status": status, "result": "VALIDATION_ERROR", "preview": body_preview}
        elif status == 500:
            return {"name": name, "path": path, "status": status, "result": "SERVER_ERROR", "preview": body_preview}
        else:
            return {"name": name, "path": path, "status": status, "result": f"HTTP_{status}", "preview": body_preview}
    except httpx.TimeoutException:
        return {"name": name, "path": path, "status": 0, "result": "TIMEOUT", "preview": "Request timed out after 10s"}
    except Exception as e:
        return {"name": name, "path": path, "status": 0, "result": "CONNECTION_ERROR", "preview": str(e)[:200]}

async def main():
    results = []
    async with httpx.AsyncClient() as client:
        # Test in batches of 10 to avoid overwhelming the server
        items = list(GET_ENDPOINTS.items())
        for i in range(0, len(items), 10):
            batch = items[i:i+10]
            tasks = [test_endpoint(client, name, path) for name, path in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            await asyncio.sleep(0.5)  # Brief pause between batches
    
    # Categorize results
    ok = [r for r in results if r["result"] == "OK"]
    not_found = [r for r in results if r["result"] == "NOT_FOUND"]
    errors = [r for r in results if r["result"] == "SERVER_ERROR"]
    validation = [r for r in results if r["result"] == "VALIDATION_ERROR"]
    timeout = [r for r in results if r["result"] == "TIMEOUT"]
    method_errors = [r for r in results if r["result"] == "METHOD_NOT_ALLOWED"]
    other = [r for r in results if r["result"] not in ("OK", "NOT_FOUND", "SERVER_ERROR", "VALIDATION_ERROR", "TIMEOUT", "METHOD_NOT_ALLOWED")]
    
    print("=" * 80)
    print(f"EMBODIER TRADER - API ENDPOINT TEST RESULTS")
    print(f"Total endpoints tested: {len(results)}")
    print(f"  ✅ OK (200):              {len(ok)}")
    print(f"  ❌ NOT FOUND (404):        {len(not_found)}")
    print(f"  💥 SERVER ERROR (500):     {len(errors)}")
    print(f"  ⚠️  VALIDATION (422):      {len(validation)}")
    print(f"  ⏱  TIMEOUT:               {len(timeout)}")
    print(f"  🚫 METHOD NOT ALLOWED:     {len(method_errors)}")
    print(f"  ❓ OTHER:                  {len(other)}")
    print("=" * 80)
    
    if ok:
        print(f"\n✅ WORKING ENDPOINTS ({len(ok)}):")
        for r in ok:
            print(f"  {r['name']:40s} {r['path']:45s} → {r['preview'][:80]}")
    
    if not_found:
        print(f"\n❌ NOT FOUND ({len(not_found)}):")
        for r in not_found:
            print(f"  {r['name']:40s} {r['path']:45s} → {r['preview'][:80]}")
    
    if errors:
        print(f"\n💥 SERVER ERRORS ({len(errors)}):")
        for r in errors:
            print(f"  {r['name']:40s} {r['path']:45s} → {r['preview'][:120]}")
    
    if validation:
        print(f"\n⚠️  VALIDATION ERRORS ({len(validation)}):")
        for r in validation:
            print(f"  {r['name']:40s} {r['path']:45s} → {r['preview'][:120]}")
    
    if timeout:
        print(f"\n⏱  TIMEOUTS ({len(timeout)}):")
        for r in timeout:
            print(f"  {r['name']:40s} {r['path']}")
    
    if method_errors:
        print(f"\n🚫 METHOD NOT ALLOWED ({len(method_errors)}):")
        for r in method_errors:
            print(f"  {r['name']:40s} {r['path']:45s} → {r['preview'][:80]}")
    
    if other:
        print(f"\n❓ OTHER ({len(other)}):")
        for r in other:
            print(f"  {r['name']:40s} {r['path']:45s} → {r['status']} {r['preview'][:80]}")

    # Save full results as JSON for reference
    with open("/home/user/workspace/elite-trading-system/test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nFull results saved to test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
