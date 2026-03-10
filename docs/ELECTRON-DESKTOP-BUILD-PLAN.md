# Embodier Trader — Electron Desktop App Build Plan

**Status:** IN PROGRESS
**Created:** March 9, 2026
**Author:** Espen + Comet (Perplexity)
**Version:** v4.1.0-desktop
**Tracking:** GitHub Issue TBD

---

## Executive Summary

Eliminate the daily pain of managing separate frontend/backend processes, port conflicts, and terminal juggling. Package Embodier Trader as a single Electron desktop application that:

1. Runs with a single double-click — no terminals, no ports, no BS
2. Supports 1-PC (full) and 2-PC (distributed compute) modes
3. Gracefully degrades if a peer PC goes offline
4. Provides iPhone PWA access for remote monitoring

---

## Architecture Overview

### Three Operating Modes

#### Mode 1: FULL (Single PC — Standalone)
```
One PC runs EVERYTHING:
backend + frontend + council + ml-engine + event-pipeline + brain-service + scanner

- Brain-service runs locally via Ollama
- Heavier on resources, but fully self-contained
- No network dependency. Works offline.
- Best for: development, travel, single-machine setups
```

#### Mode 2: PRIMARY + SECONDARY (2 PCs — Distributed Compute)
```
ESPENMAIN (Primary — Controller):
- Services: backend, frontend, council, ml-engine, event-pipeline
- Trading execution, ML models, agent orchestration
- Calls Profit Trader for LLM inference via gRPC
- isController: true

Profit Trader (Secondary — Compute Node):
- Services: backend, frontend, brain-service, scanner
- GPU handles LLM inference (Ollama), OpenClaw scanning
- Heartbeats back to Primary every 10s
- isController: false
- NOT a dumb client — dedicated compute workload node
```

#### Mode 3: DEGRADED (2-PC mode, lost peer)
```
Primary detects Profit Trader is gone.
Automatically transitions through tiered fallback.
See: docs/PEER-RESILIENCE-ARCHITECTURE.md
```

---

## What Already Exists (desktop/ folder)

| File | Status | Purpose |
|------|--------|---------|
| `main.js` | 80% done | Electron main process — lifecycle, splash, window management |
| `device-config.js` | 90% done | Device identity, role assignment, peer discovery, env generation |
| `backend-manager.js` | 80% done | Spawns Python/FastAPI backend, health checks, auto-restart |
| `preload.js` | Done | Electron preload script for IPC |
| `tray.js` | Done | System tray with menu |
| `package.json` | Done | Electron dependencies |
| `pages/` | Partial | Setup wizard pages |
| `icons/` | Done | App icons |

### Known Device Profiles (from device-config.js)
```javascript
ESPENMAIN: {
  role: "primary",
  services: ["backend", "frontend", "council", "ml-engine", "event-pipeline"],
  isController: true
}

"Profit Trader": {
  role: "secondary",
  services: ["backend", "frontend", "brain-service", "scanner"],
  isController: false
}
```

---

## Build Phases

### Phase 1: Core Electron App (Windows) — ~2 weeks

#### 1A: Setup Wizard (3 days)
- [ ] First-run detection and wizard flow
- [ ] Mode selection UI: Full / Primary / Secondary
- [ ] Auto-detect hostname to suggest ESPENMAIN vs Profit Trader
- [ ] Peer configuration — IP/hostname of other PC
- [ ] API key entry form (Alpaca, Finviz, etc.)
- [ ] Trading mode selection (paper/live)
- [ ] Generate .env file from wizard inputs
- [ ] Save config to electron-store

#### 1B: Backend Process Management (3 days)
- [ ] PyInstaller bundle of Python backend into single .exe
- [ ] Electron spawns backend .exe as child process on launch
- [ ] Auto port selection — find free port, no conflicts ever
- [ ] Health check loop — ping /health endpoint
- [ ] Auto-restart on crash (max 3 retries, then alert user)
- [ ] Graceful shutdown on app quit
- [ ] Dev mode: run uvicorn directly from source
- [ ] Prod mode: run PyInstaller-bundled .exe

#### 1C: Peer Monitor & Resilience (3 days)
- [ ] New module: `peer-monitor.js`
- [ ] Heartbeat ping to all peers every 10s (gRPC health check)
- [ ] Peer state machine: CONNECTED -> DEGRADED -> LOST -> RECOVERED
- [ ] Tiered fallback chain (see PEER-RESILIENCE-ARCHITECTURE.md)
- [ ] Local Ollama fallback manager (spin up smaller model)
- [ ] Risk parameter tightening in no-brain mode
- [ ] Cluster health events via WebSocket to dashboard
- [ ] Recovery detection and auto-restore

#### 1D: Service Orchestrator (2 days)
- [ ] New module: `service-orchestrator.js`
- [ ] Read device role from config
- [ ] Start only the services assigned to this device's role
- [ ] Service dependency ordering (backend before frontend, etc.)
- [ ] Service health dashboard data
- [ ] Brain-service launcher for secondary role (Ollama + gRPC server)
- [ ] Scanner launcher for secondary role

#### 1E: Frontend Integration (2 days)
- [ ] Bundle frontend-v2 (Next.js) into Electron
- [ ] BrowserWindow loads bundled frontend
- [ ] Frontend connects to dynamically assigned backend port
- [ ] IPC bridge for native features (notifications, tray, etc.)
- [ ] Cluster health indicators in dashboard UI
- [ ] Degraded mode banner in UI

#### 1F: Packaging & Distribution (3 days)
- [ ] electron-builder configuration for Windows
- [ ] PyInstaller spec file for backend bundling
- [ ] Single .exe installer output
- [ ] Code signing (optional, prevents Windows SmartScreen warnings)
- [ ] Auto-updater via electron-updater (GitHub Releases)
- [ ] Install/uninstall cleanup
- [ ] Desktop shortcut and Start Menu entry

### Phase 2: iPhone PWA — ~1 week

#### 2A: PWA Infrastructure (2 days)
- [ ] Add PWA manifest to frontend-v2
- [ ] Service worker for offline caching
- [ ] Installable on iPhone home screen
- [ ] App icon for iOS

#### 2B: Mobile-Responsive Dashboard (3 days)
- [ ] Simplified mobile layout for key views:
  - P&L summary
  - Open positions
  - Agent status / cluster health
  - Emergency stop button
  - Recent alerts
- [ ] Touch-optimized controls
- [ ] Dark mode (match desktop theme)

#### 2C: Remote Access (2 days)
- [ ] Tailscale/WireGuard setup guide for secure remote access
- [ ] No port forwarding needed — zero-config VPN
- [ ] iPhone connects to ESPENMAIN's backend via Tailscale IP
- [ ] Web push notifications for critical alerts
- [ ] Connection status indicator

### Phase 3: Polish & Reliability — ~1 week

#### 3A: Crash Recovery (2 days)
- [ ] Backend auto-restart with exponential backoff
- [ ] Agent heartbeat monitoring from Electron layer
- [ ] Auto-restart agents if heartbeat lost > 60s
- [ ] Crash report logging to file
- [ ] Notification to user on recovery

#### 3B: Auto-Updater (2 days)
- [ ] GitHub Releases integration
- [ ] Check for updates on app launch
- [ ] Download and install in background
- [ ] User prompt to restart for update
- [ ] Rollback capability

#### 3C: Logging & Diagnostics (1 day)
- [ ] Unified log viewer inside the app
- [ ] Backend logs + Electron logs + agent logs in one place
- [ ] Log rotation and cleanup
- [ ] Export logs for debugging

---

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Desktop framework | Electron | Already scaffolded, team familiarity, same codebase as web |
| Backend bundling | PyInstaller | Single .exe, no Python install required on target machine |
| Remote iPhone access | Tailscale + PWA | Zero-config VPN, no App Store needed, reuses existing frontend |
| Peer communication | gRPC (brain-service) + REST (backend API) | Already implemented in brain_service/ |
| Config storage | electron-store | Already in device-config.js |
| Installer | electron-builder | Industry standard, produces .msi/.exe |
| Auto-update | electron-updater + GitHub Releases | Free, integrates with existing repo |
| Local LLM fallback | Ollama with smaller model | Already using Ollama on Profit Trader |

---

## File Structure (Target)

```
desktop/
├── main.js                    # Electron main process (exists)
├── backend-manager.js         # Backend process lifecycle (exists)
├── device-config.js           # Device identity & roles (exists)
├── peer-monitor.js            # NEW — Peer health & fallback
├── service-orchestrator.js    # NEW — Role-based service launcher
├── ollama-fallback.js         # NEW — Local LLM fallback manager
├── preload.js                 # IPC bridge (exists)
├── tray.js                    # System tray (exists)
├── package.json               # Electron deps (exists)
├── electron-builder.yml       # NEW — Build/packaging config
├── pyinstaller.spec           # NEW — Backend bundling spec
├── icons/                     # App icons (exists)
└── pages/                     # Setup wizard UI (exists, partial)
    ├── setup-welcome.html     # Mode selection
    ├── setup-peer.html        # Peer configuration
    ├── setup-keys.html        # API key entry
    └── setup-complete.html    # Summary & launch
```

---

## Dependencies to Add

### Electron (desktop/package.json)
```json
{
  "electron-updater": "auto-update support",
  "electron-log": "already present",
  "electron-store": "already present",
  "bonjour-service": "LAN peer auto-discovery (optional)"
}
```

### Python (backend)
```
pyinstaller — for bundling backend to .exe
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| PyInstaller bundle too large | Use --onedir instead of --onefile, exclude unused packages |
| Port conflicts | Auto-detect free port on startup, never hardcode |
| Backend crash loops | Max 3 restart attempts, then alert user, enter safe mode |
| Peer connection lost | Tiered degradation (see PEER-RESILIENCE-ARCHITECTURE.md) |
| Windows SmartScreen blocks installer | Code signing certificate ($200-400/yr) or user instructions to bypass |
| Ollama not installed on fallback PC | Bundle Ollama or provide one-click install from setup wizard |

---

## Success Criteria

- [ ] Double-click one icon on ESPENMAIN -> entire trading system running in < 30 seconds
- [ ] Double-click same icon on Profit Trader -> connects to ESPENMAIN, starts compute services
- [ ] If Profit Trader goes offline -> ESPENMAIN continues trading in degraded mode
- [ ] If Profit Trader comes back -> auto-recovery, full cluster restored
- [ ] iPhone PWA -> view P&L, positions, hit emergency stop from anywhere
- [ ] No more terminals. No more port conflicts. No more BS.

---

## Related Documents

- [PEER-RESILIENCE-ARCHITECTURE.md](./PEER-RESILIENCE-ARCHITECTURE.md) — Detailed fallback strategy
- [STATUS-AND-TODO-2026-03-09.md](./STATUS-AND-TODO-2026-03-09.md) — Current project status
- [CLUSTER-NETWORK-SETUP.md](./CLUSTER-NETWORK-SETUP.md) — Existing 2-PC network config
- [NETWORK_TWO_PC_SETUP.md](./NETWORK_TWO_PC_SETUP.md) — Two-PC network setup guide
- [AI_TWO_PC_CODING_GUIDE.md](./AI_TWO_PC_CODING_GUIDE.md) — Cross-PC development rules
- [HARDWARE-SPECS.md](./HARDWARE-SPECS.md) — Machine specifications
