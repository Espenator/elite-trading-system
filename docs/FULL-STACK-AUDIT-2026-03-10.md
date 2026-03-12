# Full-Stack Debugging Audit — Elite Trading System / Embodier Trader

**Date:** 2026-03-10  
**Scope:** Startup, connectivity, config drift, console/runtime errors, key flows, tests.

---

## 1. Audit Summary

| Area | Status | Notes |
|------|--------|--------|
| Repo structure | OK | Backend (FastAPI), frontend-v2 (Vite+React), desktop (Electron). REPO-MAP.md accurate. |
| Backend config | OK | `app/core/config.py` PORT default 8000; `.env` can override (e.g. PORT=8080). |
| Frontend config | **Fixed** | Vite proxy default was 8080 → changed to 8000 to match backend default. |
| API endpoint mapping | **Fixed** | Added `settings` key to `api.js`; CNS paths already fixed (homeostasis/vitals, etc.). |
| Settings page error | **Fixed** | "signal is aborted" → friendly "Request timed out" + retry when fetch aborts. |
| Backend route mounting | OK | All routers in `main.py` under `/api/v1/*`; settings at `/api/v1/settings`. |
| Frontend routing | OK | App.jsx lazy routes; sidebar matches REPO-MAP. |
| Backend tests | **Partial** | 9 tests passed; then Windows access violation in pytest teardown (likely native lib). |
| Frontend build | Not run | Recommended: `npm run build` in frontend-v2. |

---

## 2. Bugs Fixed

1. **Vite proxy backend port (frontend-v2/vite.config.js)**  
   - **Was:** `VITE_BACKEND_URL || "http://localhost:8080"`  
   - **Now:** `VITE_BACKEND_URL || VITE_API_URL || "http://localhost:8000"`  
   - **Reason:** Backend default in `config.py` is 8000; proxy must match or requests fail.

2. **Settings endpoint missing in api.js (frontend-v2/src/config/api.js)**  
   - **Was:** No `settings` key; `getApiUrl("settings")` fell back to `/api/v1/settings` (worked but logged unmapped warning).  
   - **Now:** `settings: "/settings"` added so Settings page uses explicit endpoint.

3. **Settings page "signal is aborted" error (frontend-v2/src/hooks/useSettings.js)**  
   - **Was:** Aborted fetch (timeout or unmount) set `error` to raw `AbortError` → "Failed to load settings: signal is aborted without reason".  
   - **Now:** If `err.name === 'AbortError'` or message includes "aborted", set a friendly error: "Request timed out. Check that the backend is running and try again." Retry still works.

4. **Frontend .env.example comment (frontend-v2/.env.example)**  
   - **Was:** "Backend default port is 8080".  
   - **Now:** "Backend default port is 8000 (config.py). If your backend uses a different port (e.g. 8080), set VITE_BACKEND_URL=..."

---

## 3. Files Changed

| File | Change |
|------|--------|
| `frontend-v2/vite.config.js` | Proxy default backend URL 8080 → 8000, and use VITE_API_URL if set. |
| `frontend-v2/src/config/api.js` | Added `settings: "/settings"` to endpoints. |
| `frontend-v2/src/hooks/useSettings.js` | AbortError → friendly timeout message; still set error so Retry works. |
| `frontend-v2/.env.example` | Corrected backend default port comment (8080 → 8000). |
| `docs/FULL-STACK-AUDIT-2026-03-10.md` | This audit document. |

**Previously fixed (this session / earlier):**  
- CNS 404s: `api.js` paths for `cnsHomeostasis`, `cnsCircuitBreaker`, `cnsLastVerdict` aligned with backend (`/cns/homeostasis/vitals`, etc.).  
- Data Sources Monitor: button-in-button nesting in `SourceCard` fixed (div + role="button" + stopPropagation).  
- Backtesting: Card titles changed from `<h3>` to `<span>` to avoid nested `<h3>` inside Card.  
- Risk Intelligence: CorrelationMatrixHeatmap list key (Fragment key), and NaN guards for riskScore/agentMonitors.

---

## 4. What Was Tested

- **Backend config load:** `python -c "from app.core.config import settings; print(settings.effective_port)"` → 8080 (this workspace has backend/.env with PORT=8080).  
- **Backend tests:** `python -m pytest tests/ -v --tb=short` — 9 tests passed (alignment_contract, etc.); then run hit Windows fatal exception (access violation) during teardown.  
- **Frontend:** No automated run; manual verification recommended (see Commands below).

---

## 5. What Still Remains Broken / Uncertain

1. **Backend pytest on Windows:** After several tests pass, a Windows access violation occurs in pytest teardown. Likely a native dependency (e.g. DuckDB, numpy). Suggest running tests in WSL or Linux, or isolating the failing test and skipping on Windows.  
2. **Backend startup:** Not started in this audit (lifespan is heavy: MessageBus, DuckDB, event pipeline). If backend runs on 8080 via `.env`, set `VITE_BACKEND_URL=http://localhost:8080` in frontend-v2 `.env` so the proxy targets the correct port.  
3. **WebSocket auth:** Backend requires `?token=` when `API_AUTH_TOKEN` is set. Frontend uses `getWsUrl()` with `localStorage.auth_token` or `VITE_API_AUTH_TOKEN`. Ensure token is set when testing WS.  
4. **Settings 404/timeout:** If backend is not running, Settings page will show the new timeout message and Retry. Once backend is up and proxy port matches, GET /api/v1/settings should succeed.

---

## 6. Exact Commands Used to Run and Validate

```powershell
# Backend — config check (from backend dir, with venv activated)
cd C:\Users\Espen\elite-trading-system\backend
.\.venv\Scripts\Activate.ps1   # or: .\venv\Scripts\Activate.ps1
python -c "from app.core.config import settings; print('PORT', settings.effective_port)"

# Backend — run server (optional; may take 30s+ to reach “ONLINE”)
python start_server.py
# Or: uvicorn app.main:app --host 0.0.0.0 --port 8000

# Backend — tests (partial run; may crash on Windows)
python -m pytest tests/ -v --tb=short -x -q

# Frontend — install and dev (from repo root)
cd C:\Users\Espen\elite-trading-system\frontend-v2
npm install
npm run dev
# Then open http://localhost:3000 (or VITE_PORT) and check Settings, Dashboard, Data Sources, etc.

# Frontend — build
npm run build
```

---

## 7. Suggested Next Fixes (If Blocked)

1. **Port mismatch:** If backend runs on 8080, create `frontend-v2/.env` with `VITE_BACKEND_URL=http://localhost:8080`.  
2. **Settings still timeout:** Ensure backend is running and reachable at the proxy target; check browser Network tab for /api/v1/settings (status 200 vs 404/timeout).  
3. **Pytest crash:** Run a minimal subset, e.g. `pytest tests/test_endpoints.py -v`, or run tests in Docker/Linux.  
4. **WebSocket not connecting:** Confirm backend `/ws` is up; pass `token` in query if API_AUTH_TOKEN is set; check CORS and WS URL (same host as page when using proxy).  
5. **Stale docs:** REPO-MAP says "666 tests passing" — update after stabilizing pytest run on your environment.

---

## 8. Data Flow / Connectivity Checklist

- [ ] Backend starts without fatal errors.  
- [ ] `GET /health` or `GET /healthz` returns 200.  
- [ ] Frontend dev server starts; no console errors on load.  
- [ ] `GET /api/v1/settings` returns 200 when backend is up and proxy port matches.  
- [ ] Dashboard loads; CNS endpoints return 200 (homeostasis/vitals, circuit-breaker/status, council/last-verdict).  
- [ ] WebSocket `/ws` connects when token is set (if required).  
- [ ] Settings page shows "Request timed out" + Retry when backend is down; loads when backend is up.

---

*End of audit.*
