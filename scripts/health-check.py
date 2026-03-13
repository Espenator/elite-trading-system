"""Embodier Trader — Full Health Check"""
import urllib.request
import json
import sys

BASE = "http://localhost:8001"
checks = []

def check(name, path, parser=None):
    try:
        req = urllib.request.Request(f"{BASE}{path}")
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        detail = parser(data) if parser else "OK"
        checks.append((name, "OK", detail))
    except Exception as e:
        checks.append((name, "FAIL", str(e)[:60]))

# Core
check("Backend Health", "/healthz")
check("System Status", "/api/v1/status", lambda d: f"status={d.get('status')}, connected={d.get('connected')}")
check("Alpaca Account", "/api/v1/alpaca/account",
      lambda d: f"Status={d.get('status')}, Equity=${d.get('equity','?')}, Blocked={d.get('trading_blocked')}")
check("Alpaca Positions", "/api/v1/alpaca/positions",
      lambda d: f"{len(d)} open positions" if isinstance(d, list) else str(d)[:50])
check("Data Sources", "/api/v1/data-sources/",
      lambda d: f"{len([s for s in (d if isinstance(d,list) else []) if s.get('status')=='active'])}/{len(d if isinstance(d,list) else [])} active")
check("Sentiment", "/api/v1/sentiment", lambda d: f"{d.get('count',0)} items")
check("Signals", "/api/v1/signals/",
      lambda d: f"{len(d if isinstance(d,list) else d.get('signals',[]))} signals")
check("Agents", "/api/v1/agents",
      lambda d: f"{len(d if isinstance(d,list) else d.get('agents',[]))} agents")
check("ML Brain", "/api/v1/ml-brain/", lambda d: f"keys={list(d.keys())[:4]}")
check("Risk", "/api/v1/risk", lambda d: f"keys={list(d.keys())[:4]}")
check("Portfolio", "/api/v1/portfolio", lambda d: f"keys={list(d.keys())[:4]}")
check("Flywheel", "/api/v1/flywheel", lambda d: f"keys={list(d.keys())[:4]}")
check("Patterns", "/api/v1/patterns", lambda d: f"keys={list(d.keys())[:4]}")
check("Settings", "/api/v1/settings", lambda d: f"keys={list(d.keys())[:4]}")
check("Market", "/api/v1/market", lambda d: f"keys={list(d.keys())[:4]}")

# Frontend + WebSocket
try:
    resp = urllib.request.urlopen("http://localhost:3000", timeout=5)
    checks.append(("Frontend", "OK", f"HTTP {resp.status}"))
except Exception as e:
    checks.append(("Frontend", "FAIL", str(e)[:60]))

# WS test via upgrade
try:
    req = urllib.request.Request("http://localhost:3000/ws?token=Hagl03SR4kX1oqxF7jZhYzk8qx3SJlDWlHHZDd1eGlE")
    req.add_header("Connection", "Upgrade")
    req.add_header("Upgrade", "websocket")
    req.add_header("Sec-WebSocket-Version", "13")
    req.add_header("Sec-WebSocket-Key", "dGhlIHNhbXBsZSBub25jZQ==")
    resp = urllib.request.urlopen(req, timeout=5)
    checks.append(("WebSocket Proxy", "OK", f"HTTP {resp.status}"))
except urllib.error.HTTPError as e:
    if e.code == 101:
        checks.append(("WebSocket Proxy", "OK", "HTTP 101 Switching Protocols"))
    else:
        checks.append(("WebSocket Proxy", "FAIL", f"HTTP {e.code}"))
except Exception as e:
    err = str(e)
    if "101" in err or "Switching" in err:
        checks.append(("WebSocket Proxy", "OK", "HTTP 101 Switching Protocols"))
    else:
        checks.append(("WebSocket Proxy", "FAIL", err[:60]))

# Print report
print("\n" + "=" * 65)
print("  EMBODIER TRADER — FULL HEALTH CHECK")
print("=" * 65)
ok = sum(1 for _, s, _ in checks if s == "OK")
fail = sum(1 for _, s, _ in checks if s == "FAIL")
for name, status, detail in checks:
    icon = "  OK " if status == "OK" else " FAIL"
    print(f"  [{icon}] {name:<22} {detail}")
print("-" * 65)
print(f"  TOTAL: {ok} OK, {fail} FAIL out of {len(checks)} checks")
print("=" * 65 + "\n")
sys.exit(0 if fail == 0 else 1)
