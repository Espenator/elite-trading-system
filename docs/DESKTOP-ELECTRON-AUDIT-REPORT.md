# Desktop Electron App — Service Orchestration & Resilience Audit

**Date:** March 13, 2026  
**Scope:** Electron wrapper (desktop/), startup sequence, service orchestration, peer monitoring, crash recovery, setup wizard, logging.

---

## 1. Startup Sequence (Traced)

| Step | Component | Behavior |
|------|-----------|----------|
| 1 | `app.whenReady()` | Registers IPC handlers, creates tray. |
| 2 | First-run check | If `deviceConfig.isFirstRun()` → `createSetupWindow()` (setup wizard). Else → `createSplashWindow()` then `bootSystem()`. |
| 3 | Setup path | User completes wizard → IPC `setup-complete` → `validateSetupConfig(config)` (warnings logged) → `deviceConfig.completeSetup(config)` → write `backend/.env` → close setup → `createSplashWindow()` → `bootSystem()`. |
| 4 | `bootSystem()` | `serviceOrchestrator.initialize(role)` (role from device-config) → services started in dependency order → `createMainWindow()`. |
| 5 | Main window | Dev: poll Vite URL, load loading.html then dev URL. Prod: load packed frontend or `http://localhost:${port}`. Splash closed on `ready-to-show`. |

**Conclusion:** Sequence is correct: splash → (optional setup) → service orchestration → main window. Setup wizard state is now validated before boot; warnings are logged and do not block launch.

---

## 2. Service Dependency Ordering (Verified)

Defined in `desktop/lib/role-services.js` and used by `service-orchestrator.js`:

- **Order:** `backend (1) → frontend (2) → council (3) → ml-engine (4) → event-pipeline (5) → brain-service (10) → scanner (11) → mobile-server (12)`.
- **Enforcement:** Orchestrator sorts services by `SERVICE_DEFINITIONS[s].order` and starts them sequentially. Backend and frontend are marked `critical: true`; failure of a critical service throws and stops startup.
- **Tests:** `desktop/tests/desktop-orchestration.test.js` asserts backend order < frontend order and that primary-role services when sorted match this sequence.

---

## 3. Peer Monitoring — PC2 Offline Detection & Fallback

- **Mechanism:** `peer-monitor.js` runs a heartbeat every 10s: HTTP GET to `http://${peer}:${port}/health`. Backend exposes `GET /health` (and `/healthz` for liveness); peer monitor uses `/health`.
- **State machine:** `CONNECTED → DEGRADED` (2 missed) → `LOST` (5 missed) → `RECOVERED` (3 consecutive OK) → `CONNECTED`.
- **Fallback:** When `peer-lost` is emitted, `service-orchestrator._handlePeerLost()` runs only when **this** device is `primary`. If the lost peer’s role implies `brain-service` (e.g. `secondary`), the orchestrator activates local Ollama fallback via `ollamaFallback.activate()` and sets `_fallbackActive = true`. It also POSTs to backend `/api/v1/cluster/degraded`. On `peer-recovered`, it deactivates fallback and POSTs `/api/v1/cluster/restored`.
- **Fix applied:** Peers added in the setup wizard do not store a `services` array; only `role` is stored. Previously `peer.services` was empty, so brain fallback was never triggered. **peer-monitor** now derives `services` from `role` using `deviceConfig.getServicesForRole(peer.config.role)` when `peer.config.services` is missing. **peer-monitor** also uses `config.address` (setup wizard field) for the heartbeat host when `config.ip` / `config.hostname` are absent.
- **Tests:** Test suite asserts that `getServicesForRole('secondary')` includes `brain-service` so that when a secondary peer is lost, the orchestrator will activate fallback.

**Limitation:** There is no automatic “service migration” (e.g. starting brain on another machine). Fallback is local Ollama on PC1 only.

---

## 4. Crash Recovery — Backend Process

- **Implementation:** `backend-manager.js` spawns the backend (venv python, system python, or PyInstaller binary). On `backendProcess.on('exit', (code, signal))`:
  - If `!isShuttingDown && code !== 0`, it increments `restartCount` and schedules `startBackend()` after a delay: `Math.min(3000 * 2^(restartCount-1), 60000)` ms (exponential backoff, cap 60s).
  - After 5 consecutive crash restarts it stops auto-restart and logs “Backend crashed too many times (5), giving up auto-restart”.
- **Health:** Before considering the backend “ready”, `waitForHealth(port, 60_000)` polls `GET http://127.0.0.1:${port}/healthz` until 200. A 15s interval health check runs afterward; it only logs failures and does not restart the process (restart is driven only by `exit`).
- **Conclusion:** Backend crash is detected via process exit; restart is automatic with exponential backoff and a cap of 5 retries. No separate “crash detector” process; Electron’s own crash handler is not used for the backend child process.

---

## 5. Role Detection — PC1 vs PC2

- **Source:** `device-config.js` stores `deviceRole` and `deviceName` in electron-store (set at first run or by user). `KNOWN_DEVICES` maps display names (e.g. `ESPENMAIN`, `Profit Trader`) to roles and service lists; the wizard uses these for quick selection. No automatic hostname → role mapping at runtime; role is whatever was saved.
- **Services per role:** `getServicesForRole(role)` (in `desktop/lib/role-services.js`, used by device-config and peer-monitor) returns:
  - **full:** backend, frontend, council, ml-engine, event-pipeline, brain-service, scanner, mobile-server.
  - **primary:** backend, frontend, council, ml-engine, event-pipeline, mobile-server (no brain-service; expects PC2).
  - **secondary:** backend, frontend, brain-service, scanner.
  - **brain-only / scanner-only:** single-service sets.
- **Conclusion:** Role is user-configured; hostname/IP are not used to override it. Device-config and peer-monitor now share the same role → services mapping via `lib/role-services.js`.

---

## 6. Service Logging — Persistent Files

- **Electron main process:** `electron-log` is used in `service-orchestrator.js` and `backend-manager.js`. By default it writes to a persistent file (e.g. Windows: `%USERPROFILE%\AppData\Roaming\<app name>\logs\main.log`), with rotation (e.g. 1MB then archive).
- **Backend child process:** `backend-manager.js` attaches `backendProcess.stdout` / `stderr` to `log.info` / `log.warn`, so backend stdout/stderr are captured into the same electron-log stream and thus into the same persistent log file.
- **Gap:** There is no separate “service log” path exposed in the UI (e.g. “Open service logs”). Operators can open the app’s log directory via electron-log’s `log.transports.file.getFile().path` or the app data directory.
- **Recommendation:** Optionally expose “Open logs folder” in the tray or Settings that opens the directory containing `main.log` (or the path from `log.transports.file.getFile().path`).

---

## 7. Setup Wizard — Skipped API Key Entry

- **Before:** User could finish the wizard with empty Alpaca (or other) keys. Summary showed “Not set (will use mock data)” but no validation or warning.
- **After:** `setup-validator.js` implements `validateSetupConfig(config)`. It returns `{ valid, warnings }` for:
  - Missing Alpaca API key or secret → warning that trading will be disabled until set in Settings.
  - Backend port outside 1024–65535 → warning.
  - Peer configured but peer IP/address missing → warning.
- **Integration:** On `setup-completed`, `main.js` calls `validateSetupConfig(config)` and logs each warning with `[main] Setup warning:`. It does **not** block closing the wizard or starting services; launch continues so the user can set keys later in Settings.
- **Tests:** `desktop/tests/desktop-orchestration.test.js` asserts that missing Alpaca keys yield a warning, valid Alpaca keys do not, invalid port and missing peer IP yield the expected warnings.

---

## 8. Mobile Server Security

- **Auth:** In `mobile-server.js`, requests to `/api/*` require `Authorization: Bearer <token>`. Missing or non-Bearer auth receives 401. Static assets (PWA) are served without auth (local network only).
- **CORS:** Scoped to the request origin (LAN). Path traversal is guarded: `filePath` must stay under `_staticDir`.
- **Conclusion:** API proxy is protected by Bearer token; static content is unauthenticated on the LAN, which is acceptable for a local PWA.

---

## 9. Build Targets & Paths

- **package.json** defines `dist:win`, `dist:mac`, `dist:linux` and `dist:all`. `extraResources` copies:
  - `../backend/dist/embodier-backend` → `backend/embodier-backend` (binary name differs on Windows: `embodier-backend.exe`; builder may need `embodier-backend.exe` in `from` on Windows).
  - `../frontend-v2/dist` → `frontend`.
- Paths are relative to the project root; CI or build machines must run from repo root so `../backend` and `../frontend-v2` resolve correctly.

---

## 10. Deliverables Summary

| Deliverable | Status |
|------------|--------|
| Test: service startup ordering (backend before frontend) | Done in `desktop/tests/desktop-orchestration.test.js` |
| Test: peer offline detection → fallback (secondary includes brain-service) | Done in same file |
| Test: setup wizard validation (missing API keys → warning) | Done in same file |
| Report: crash recovery strategy | Documented in §4 (process exit + auto-restart with backoff, max 5) |

**Run desktop tests:** From repo root, `node desktop/tests/desktop-orchestration.test.js`, or from `desktop/`: `npm run test`.
