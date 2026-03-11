# Production Game Plan — 8-Step Division of Labor

**Created:** March 11, 2026
**Updated:** March 11, 2026 (PC1 setup complete, main.js wired)
**Status:** ACTIVE — PC1 (ESPENMAIN) is SET UP and building
**Coordination:** This document defines which PC builds what

---

## The 8 Production Steps

Mapped from the [Electron Desktop Build Plan](./ELECTRON-DESKTOP-BUILD-PLAN.md):

| Step | Sub-Phase | Description | Assigned To | Status |
|------|-----------|-------------|-------------|--------|
| **1** | 1A | Setup Wizard (mode selection, peer config, API keys) | **PC1 ESPENMAIN** | DONE — `setup.html` complete, wired in `main.js` |
| **2** | 1B | Backend Process Management (PyInstaller, auto-port, health checks) | **PC1 ESPENMAIN** | DONE — `backend-manager.js` complete |
| **3** | 1C | Peer Monitor & Resilience (heartbeat, state machine, fallback) | **PC1 ESPENMAIN** | DONE — `peer-monitor.js` + `ollama-fallback.js` complete |
| **4** | 1D | Service Orchestrator (role-based service launcher) | **PC2 ProfitTrader** | DONE — `service-orchestrator.js` complete, needs PC2 testing |
| **5** | 1E | Frontend Integration (bundle React/Vite in Electron) | **PC2 ProfitTrader** | IN PROGRESS — `main.js` loads frontend, needs bundling |
| **6** | 1F | Packaging & Distribution (electron-builder, installer) | **PC1 ESPENMAIN** | IN PROGRESS — `package.json` build config done |
| **7** | Phase 2 | iPhone PWA (manifest, mobile dashboard, Tailscale remote) | **PC2 ProfitTrader** | NOT STARTED |
| **8** | Phase 3 | Polish & Reliability (crash recovery, auto-updater, logging) | **SHARED** | PARTIAL — crash recovery in backend-manager |

---

## What PC1 (ESPENMAIN) Has Done

### Completed by PC1 Claude Session:

1. **`desktop/main.js` REWRITTEN** — Now integrates:
   - `service-orchestrator.js` for role-based service startup
   - `peer-monitor.js` for cross-PC heartbeat monitoring
   - `device-config.js` for first-run setup wizard detection
   - Setup wizard → `.env` generation → boot sequence flow
   - IPC handlers for cluster health, orchestrator status, backend control
   - Cluster events forwarded to frontend via IPC (`cluster-event`)
   - Tray menu shows device name + role + cluster status

2. **`desktop/preload.js` UPDATED** — New IPC bridges:
   - `getClusterHealth()` — peer monitor health summary
   - `getOrchestratorStatus()` — service-level status
   - `onClusterEvent(callback)` — real-time peer state changes

3. **`desktop/package.json` UPDATED** — Includes:
   - All desktop modules in build files list
   - Production dependencies: `electron-log`, `electron-store`, `electron-updater`
   - electron-builder config for Windows NSIS installer

4. **`backend/.env` CONFIGURED** for PC1 role — Complete with:
   - `PC_ROLE=primary`, `CLUSTER_PC2_HOST=192.168.1.116`
   - Brain service pointing to PC2 (`BRAIN_HOST=192.168.1.116`)
   - Dual Ollama pool, model pinning, LLM dispatcher
   - Redis bridge, GPU telemetry, risk guardrails, pipeline enforcement

---

## PC1 — ESPENMAIN — What It Runs

### Architecture: Primary Controller

```
ESPENMAIN (PC1 — Primary)
├── Electron Desktop Shell (main.js)
│   ├── ServiceOrchestrator → starts role-based services
│   ├── PeerMonitor → heartbeats PC2 every 10s
│   ├── OllamaFallback → activates if PC2 goes down
│   └── BackendManager → spawns Python/FastAPI backend
├── Backend (FastAPI on port 8001)
│   ├── Council (35-agent DAG, 7 stages)
│   ├── ML Engine (XGBoost, LSTM, HMM)
│   ├── Event Pipeline (MessageBus → CouncilGate → OrderExecutor)
│   ├── NodeDiscovery → auto-discovers PC2 Ollama + Brain
│   └── Redis Bridge → cross-PC pub/sub
├── Frontend (React/Vite on port 3000 in dev)
└── Redis (port 6379 — both PCs connect here)
```

### Services started by ServiceOrchestrator (role=primary):
- `backend` (FastAPI)
- `frontend` (Electron BrowserWindow)
- `council` (runs inside backend)
- `ml-engine` (runs inside backend)
- `event-pipeline` (runs inside backend)
- `mobile-server` (PWA access point)

---

## PC2 — ProfitTrader — What It Runs

### Architecture: Compute Node

```
ProfitTrader (PC2 — Secondary)
├── Electron Desktop Shell (main.js) — same codebase
│   ├── ServiceOrchestrator → starts secondary services
│   ├── PeerMonitor → heartbeats PC1 every 10s
│   └── BackendManager → spawns local backend
├── Backend (FastAPI on port 8001)
│   ├── Brain Service (gRPC on port 50051)
│   │   └── Ollama (11 models, RTX 4080 GPU)
│   └── Scanner (OpenClaw)
├── Ollama (port 11434, bound to 0.0.0.0)
│   ├── mistral:7b (fast screening)
│   ├── qwen2.5:14b/32b (reasoning)
│   ├── deepseek-r1:8b, llama3.1:8b, etc.
│   └── nomic-embed-text (embeddings)
└── Connects to PC1 Redis (redis://192.168.1.105:6379/0)
```

### Services started by ServiceOrchestrator (role=secondary):
- `backend` (FastAPI)
- `frontend` (Electron BrowserWindow)
- `brain-service` (Ollama + gRPC server)
- `scanner` (OpenClaw)

---

## Graceful Fallback Chain (When PC2 Goes Down)

Documented in [PEER-RESILIENCE-ARCHITECTURE.md](./PEER-RESILIENCE-ARCHITECTURE.md).

```
PC2 healthy      → CONNECTED   → Full cluster, brain on PC2
2 missed beats   → DEGRADED    → Tier 1: Queue requests, use cached intelligence
5 missed beats   → LOST        → Tier 2: Start local Ollama (smaller model)
                                → Tier 3: No-Brain mode (tighten risk, no new positions)
PC2 returns      → RECOVERED   → Gradual risk parameter restoration over 120s
3 good beats     → CONNECTED   → Full cluster restored
```

### Risk tightening in No-Brain mode:
- Max position size: 50% (was 100%)
- Consensus threshold: 80% (was 65%)
- New positions: BLOCKED
- Stop-losses: +20% tighter
- Max concurrent positions: halved

---

## Instructions for PC2 Claude (ProfitTrader)

### READ THESE DOCS FIRST:
1. **This file** — `docs/PRODUCTION-PLAN-PC-DIVISION.md`
2. **`docs/PC2-SETUP-COMPLETE.md`** — PC2 .env, services, firewall rules
3. **`docs/PEER-RESILIENCE-ARCHITECTURE.md`** — fallback strategy
4. **`docs/ELECTRON-DESKTOP-BUILD-PLAN.md`** — full build plan

### YOUR TASKS (Steps 4, 5, 7, 8):

#### Step 4 — Service Orchestrator (REVIEW & TEST)
`desktop/service-orchestrator.js` is already written. Your job:
- Verify it starts brain-service and scanner correctly on PC2
- Test the `_handlePeerLost` / `_handlePeerRecovered` flow
- Ensure `_getServicesForRole("secondary")` returns correct services
- Test health check endpoints against PC2's actual backend

#### Step 5 — Frontend Integration (BUILD)
- Bundle `frontend-v2` (React/Vite) for Electron production mode
- Add Vite build step that outputs to `frontend-v2/dist/`
- `main.js` already loads from `process.resourcesPath/frontend/index.html` in prod
- Add cluster health indicators to the frontend dashboard:
  - Use `window.embodier.getClusterHealth()` IPC
  - Use `window.embodier.onClusterEvent(callback)` for real-time updates
  - Show peer state: CONNECTED/DEGRADED/LOST/RECOVERED
  - Show degraded mode banner when brain-service is down

#### Step 7 — iPhone PWA (BUILD)
- Add `manifest.json` to `frontend-v2/public/`
- Create service worker (`sw.js`) for offline caching
- Build mobile-responsive dashboard layout:
  - P&L summary card
  - Open positions list
  - Emergency stop button
  - Agent/cluster health status
  - Recent alerts
- Add Tailscale setup instructions to docs

#### Step 8 — Auto-Updater & Logging (BUILD)
- `desktop/auto-updater.js` exists — wire it into main.js
- GitHub Releases integration for update delivery
- Unified log viewer (backend + Electron + agent logs)
- Log rotation and export

### DO NOT TOUCH:
- `desktop/main.js` — PC1 owns this (already rewritten)
- `desktop/peer-monitor.js` — PC1 owns this
- `desktop/ollama-fallback.js` — PC1 owns this
- `desktop/backend-manager.js` — PC1 owns this
- `backend/.env` on PC1 — PC1 manages its own config

### COORDINATE VIA:
- Git commits with clear messages
- Update this document's status table when tasks complete
- Test cross-PC by running both Electron apps simultaneously

---

## Network Configuration — LOCKED

| Property | PC1 (ESPENMAIN) | PC2 (ProfitTrader) |
|----------|-----------------|---------------------|
| LAN IP | 192.168.1.105 | 192.168.1.116 |
| Backend API | http://192.168.1.105:8001 | http://192.168.1.116:8001 |
| WebSocket | ws://192.168.1.105:8001/ws | ws://192.168.1.116:8001/ws |
| Ollama | http://localhost:11434 (fallback) | http://192.168.1.116:11434 (primary) |
| Brain gRPC | — (calls PC2:50051) | localhost:50051 |
| Redis | redis://192.168.1.105:6379/0 (HOST) | redis://192.168.1.105:6379/0 (CLIENT) |

---

## Handshake Status

| PC | Claude Session | Status | Branch |
|----|---------------|--------|--------|
| **PC1 ESPENMAIN** | **ACTIVE** | Building — main.js wired, .env done | `claude/review-production-plan-Vxxdy` |
| **PC2 ProfitTrader** | Pending | Read this doc + begin Steps 4-5-7-8 | TBD |

```
=== PC1 ESPENMAIN — ONLINE ===
Date: March 11, 2026
Session: claude/review-production-plan-Vxxdy
Status: main.js rewritten, all modules wired, .env configured
Completed: Steps 1 (Setup Wizard), 2 (Backend Mgmt), 3 (Peer Monitor) — code exists and is integrated
In Progress: Step 6 (Packaging) — electron-builder config done, needs PyInstaller spec
PC2 should: Begin Steps 4 (test orchestrator), 5 (frontend bundling), 7 (PWA), 8 (auto-updater)
Handshake: READY — waiting for PC2 acknowledgment
===
```

---

## Build Order (Recommended Sequence)

### Wave 1 — Core (Parallel on both PCs) ← CURRENT
- **PC1**: Steps 1-3 DONE, Step 6 IN PROGRESS
- **PC2**: Step 4 (test orchestrator) + Step 5 (frontend bundling)

### Wave 2 — Integration Testing
- **BOTH**: Run both Electron apps, verify peer discovery, test fallback chain

### Wave 3 — Mobile + Polish
- **PC2**: Step 7 (iPhone PWA)
- **BOTH**: Step 8 (crash recovery, auto-updater, logging)

---

## Success Criteria

- [ ] Double-click one icon on ESPENMAIN → entire trading system running in < 30 seconds
- [ ] Double-click same icon on Profit Trader → connects to ESPENMAIN, starts compute services
- [ ] If Profit Trader goes offline → ESPENMAIN continues trading in degraded mode
- [ ] If Profit Trader comes back → auto-recovery, full cluster restored
- [ ] iPhone PWA → view P&L, positions, hit emergency stop from anywhere
- [ ] No more terminals. No more port conflicts. No more BS.
