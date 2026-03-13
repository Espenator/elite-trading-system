#!/usr/bin/env python3
"""
Verify backend is running and data flows for the Dashboard landing page.
Run from repo root or backend/: python scripts/verify_dashboard_data_flow.py
Uses TestClient (no live server needed) or optional live URL.
"""
import os
import sys

# Run from backend directory so app is importable
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

def check_via_test_client():
    """Use FastAPI TestClient to verify endpoints return 200 and expected data."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    ok = True
    # 1. Status
    r = client.get("/api/v1/status")
    if r.status_code != 200:
        print(f"FAIL /api/v1/status -> {r.status_code}")
        ok = False
    else:
        print("OK   /api/v1/status -> 200")
    # 2. Signals (symbols for table)
    r = client.get("/api/v1/signals/")
    if r.status_code != 200:
        print(f"FAIL /api/v1/signals/ -> {r.status_code}")
        ok = False
    else:
        data = r.json()
        signals = data.get("signals") or []
        print(f"OK   /api/v1/signals/ -> 200  (signals: {len(signals)})")
        if signals:
            syms = [s.get("symbol") for s in signals[:5]]
            print(f"     Symbols: {syms}")
    # 3. Market indices (ticker strip)
    r = client.get("/api/v1/market/indices")
    if r.status_code != 200:
        print(f"FAIL /api/v1/market/indices -> {r.status_code}")
        ok = False
    else:
        data = r.json()
        indices = data.get("indices") or data.get("marketIndices") or []
        print(f"OK   /api/v1/market/indices -> 200  (indices: {len(indices)})")
    # 4. Data sources
    r = client.get("/api/v1/data-sources/")
    if r.status_code != 200:
        print(f"FAIL /api/v1/data-sources/ -> {r.status_code}")
        ok = False
    else:
        data = r.json()
        sources = data.get("dataSources") or data.get("sources") or (data if isinstance(data, list) else [])
        print(f"OK   /api/v1/data-sources/ -> 200  (sources: {len(sources)})")
    return ok

if __name__ == "__main__":
    print("Dashboard data flow check (TestClient)")
    print("=" * 50)
    try:
        ok = check_via_test_client()
        print("=" * 50)
        if ok:
            print("Backend and data paths OK. Start backend (uvicorn) and frontend (npm run dev) for real-time flow.")
            sys.exit(0)
        else:
            print("Some checks failed.")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
