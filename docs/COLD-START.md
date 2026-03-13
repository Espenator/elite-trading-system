# Cold Start — Embodier Trader

When the full stack won't start cleanly (backend, frontend, API, or WebSocket broken), follow this order.

## Step 0: Cleanup first (required)

Run **before** starting backend or frontend:

```powershell
# From repo root
powershell -ExecutionPolicy Bypass -File scripts/cold-start-cleanup.ps1
```

This script:

- Stops all Python and Node processes (uvicorn, pytest, Vite, npm)
- Frees ports **8000** (backend) and **5173** (frontend)
- Removes DuckDB/SQLite WAL and lock files under `backend/` that cause "database locked"

If port 5173 or 8000 is still in use, run the script again or close the app using the port manually.

## Step 1: Backend (Terminal 1)

```powershell
cd backend
venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Wait until you see: `Uvicorn running on http://0.0.0.0:8000`.

**If backend fails:**

- **Missing .env** — Ensure `backend/.env` exists with at least `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` (copy from `.env.example`).
- **DuckDB locked** — Step 0 removes WAL/lock files. If it still fails, close any other process using `backend/data/` and restart.
- **Import errors** — Run `pip install -r requirements.txt` in the backend venv.
- **Port 8000 in use** — Run Step 0 again or: `netstat -ano | findstr :8000` and stop the PID.

## Step 2: Verify backend health

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
```

You should get a JSON object with `status` and service checks. If you get "connection refused", the backend did not start — check Terminal 1 for errors.

## Step 3: Frontend (Terminal 2)

```powershell
cd frontend-v2
npm install
npm run dev
```

Frontend must listen on **5173**. If it says "Port 5173 is in use", run Step 0 again and restart.

**If frontend fails:**

- **Blank white page** — Run `npm install` in `frontend-v2`.
- **Vite proxy ECONNREFUSED to :8000** — Start the backend first (Step 1).
- **Wrong port** — Kill Node processes (Step 0) and run `npm run dev` again.

## Step 4: Frontend → backend

Open **http://localhost:5173/dashboard** and open DevTools → Network.

- API calls to `/api/v1/*` should return **200** (proxied to backend :8000).
- CORS or 502 usually means the backend is down or not on port 8000.
- 401 on trading endpoints is expected when not authenticated; other endpoints should work without auth.

## Step 5: WebSocket

The app connects to `ws://localhost:8000/ws` (or via Vite proxy from the dev server).

- **Backend** — `app/websocket_manager.py` serves `/ws` with 25 channels.
- **Frontend** — `frontend-v2/src/services/websocket.js` uses `getWsBaseUrl()` from `config/api.js`.
- In DevTools → Network → WS you should see the WebSocket connection open.

If WebSocket does not connect:

- Ensure the backend is running first.
- In `frontend-v2/vite.config.js` the proxy must have: `"/ws": { target: "ws://localhost:8000", ws: true }`.
- If auth is enabled, the WebSocket URL may require `?token=<API_AUTH_TOKEN>`.

## Ports and config (do not change)

| Service   | Port | URL                    |
|----------|------|------------------------|
| Backend  | 8000 | http://localhost:8000  |
| Frontend | 5173 | http://localhost:5173  |

- **Vite** — Default backend URL is `http://localhost:8000` in `frontend-v2/vite.config.js` and `frontend-v2/src/config/api.js`.
- **Start order** — Backend first, then frontend (frontend proxies to backend).

## Key files if something is still broken

| Problem            | Check |
|--------------------|--------|
| Backend won't import | `backend/app/main.py` (router imports) |
| DuckDB locked      | `backend/app/data/duckdb_storage.py`; remove `backend/data/*.wal` and lock files |
| API 500            | The route file in `backend/app/api/v1/` for that endpoint |
| Frontend blank     | `frontend-v2/src/main.jsx`, `App.jsx` |
| Proxy broken       | `frontend-v2/vite.config.js` (proxy and default backend URL) |
| WebSocket not connecting | `backend/app/websocket_manager.py`, `frontend-v2/src/services/websocket.js` |
| CORS errors        | `backend/app/main.py` (CORS middleware) |
