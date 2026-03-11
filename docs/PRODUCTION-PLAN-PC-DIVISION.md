# Production Game Plan — 8-Step Division of Labor

**Created:** March 11, 2026
**Status:** ACTIVE — PC1 (ESPENMAIN) is SET UP and ready
**Coordination:** This document defines which PC builds what

---

## The 8 Production Steps

Mapped from the [Electron Desktop Build Plan](./ELECTRON-DESKTOP-BUILD-PLAN.md):

| Step | Sub-Phase | Description | Assigned To |
|------|-----------|-------------|-------------|
| **1** | 1A | Setup Wizard (mode selection, peer config, API keys) | **PC1 ESPENMAIN** |
| **2** | 1B | Backend Process Management (PyInstaller bundle, auto-port, health checks) | **PC1 ESPENMAIN** |
| **3** | 1C | Peer Monitor & Resilience (heartbeat, state machine, fallback) | **PC1 ESPENMAIN** |
| **4** | 1D | Service Orchestrator (role-based service launcher) | **PC2 ProfitTrader** |
| **5** | 1E | Frontend Integration (bundle Next.js in Electron) | **PC2 ProfitTrader** |
| **6** | 1F | Packaging & Distribution (electron-builder, installer) | **PC1 ESPENMAIN** |
| **7** | Phase 2 | iPhone PWA (manifest, mobile dashboard, Tailscale remote) | **PC2 ProfitTrader** |
| **8** | Phase 3 | Polish & Reliability (crash recovery, auto-updater, logging) | **SHARED** |

---

## PC1 — ESPENMAIN (This Machine) — Claude Session Active

### Role: Primary Controller + Core Desktop Shell

**Owns Steps: 1, 2, 3, 6, 8 (partial)**

| Step | What PC1 Builds | Key Files |
|------|-----------------|-----------|
| **1 (1A)** | Setup wizard flow — first-run detection, mode selection UI, hostname auto-detect, peer config, API key entry, .env generation | `desktop/pages/setup-*.html`, `desktop/device-config.js` |
| **2 (1B)** | Backend process management — PyInstaller spec, child process spawning, auto port selection, health check loop, auto-restart, graceful shutdown | `desktop/backend-manager.js`, `desktop/pyinstaller.spec` |
| **3 (1C)** | Peer monitor & resilience — heartbeat ping, peer state machine (CONNECTED→DEGRADED→LOST→RECOVERED), tiered fallback chain, local Ollama fallback, risk tightening | `desktop/peer-monitor.js`, `desktop/ollama-fallback.js` |
| **6 (1F)** | Packaging — electron-builder config, PyInstaller spec, .exe installer, auto-updater setup | `desktop/electron-builder.yml`, `desktop/auto-updater.js` |
| **8 (3A)** | Crash recovery — backend auto-restart with backoff, agent heartbeat monitoring, crash report logging | `desktop/main.js` integration |

### PC1 Dependencies on PC2
- Needs PC2's brain-service gRPC endpoint for heartbeat testing (Step 3)
- Needs PC2's service-orchestrator output to validate multi-PC launch (Step 6)

---

## PC2 — ProfitTrader — Claude Session (Other Machine)

### Role: Compute Node + Frontend + Mobile

**Owns Steps: 4, 5, 7, 8 (partial)**

| Step | What PC2 Builds | Key Files |
|------|-----------------|-----------|
| **4 (1D)** | Service orchestrator — read device role from config, start only role-assigned services, dependency ordering, brain-service launcher, scanner launcher | `desktop/service-orchestrator.js` |
| **5 (1E)** | Frontend integration — bundle frontend-v2 in Electron, BrowserWindow loads bundled app, dynamic backend port, IPC bridge, cluster health UI indicators | `desktop/main.js` (frontend parts), `frontend-v2/` |
| **7 (Phase 2)** | iPhone PWA — manifest, service worker, mobile-responsive dashboard (P&L, positions, emergency stop), Tailscale setup guide | `frontend-v2/public/manifest.json`, `frontend-v2/public/sw.js`, mobile layouts |
| **8 (3B-3C)** | Auto-updater (GitHub Releases) + unified logging/diagnostics | `desktop/auto-updater.js`, logging integration |

### PC2 Dependencies on PC1
- Needs PC1's peer-monitor events to validate recovery flow (Step 4)
- Needs PC1's backend-manager port assignment for frontend connection (Step 5)

---

## Network Configuration — LOCKED

| Property | PC1 (ESPENMAIN) | PC2 (ProfitTrader) |
|----------|-----------------|---------------------|
| LAN IP | 192.168.1.105 | 192.168.1.116 |
| Backend API | http://192.168.1.105:8001 | http://192.168.1.116:8001 |
| WebSocket | ws://192.168.1.105:8001/ws | ws://192.168.1.116:8001/ws |
| Ollama | http://localhost:11434 | http://192.168.1.116:11434 |
| Brain gRPC | — (calls PC2) | localhost:50051 |
| Redis | redis://192.168.1.105:6379/0 (runs here) | redis://192.168.1.105:6379/0 (connects to PC1) |

---

## Handshake Status

| PC | Claude Session | Status | Branch |
|----|---------------|--------|--------|
| **PC1 ESPENMAIN** | **ACTIVE** | SET UP and ready | `claude/review-production-plan-Vxxdy` |
| **PC2 ProfitTrader** | Pending | Awaiting setup — read this doc | TBD |

### Instructions for PC2 Claude (ProfitTrader)

When you start your session on PC2:

1. **Read this document** (`docs/PRODUCTION-PLAN-PC-DIVISION.md`)
2. **Read** `docs/PC2-SETUP-COMPLETE.md` — your machine is already configured
3. **Your scope**: Steps 4, 5, 7, and 8 (3B-3C) from the table above
4. **Do NOT touch**: Steps 1, 2, 3, 6 — those are PC1's domain
5. **Coordinate via**: Commit messages and this document
6. **Key files you own**: `desktop/service-orchestrator.js`, frontend integration, PWA, auto-updater
7. **Your .env is already set** per `docs/PC2-SETUP-COMPLETE.md`

### Ping from PC1 to PC2

```
=== PC1 ESPENMAIN — ONLINE ===
Date: March 11, 2026
Session: claude/review-production-plan-Vxxdy
Status: Production plan reviewed, work divided
PC1 is taking: Steps 1 (Setup Wizard), 2 (Backend Process Mgmt), 3 (Peer Monitor), 6 (Packaging)
PC2 should take: Steps 4 (Service Orchestrator), 5 (Frontend Integration), 7 (PWA), 8 (Auto-updater/Logging)
Handshake: READY — waiting for PC2 acknowledgment
===
```

---

## Build Order (Recommended Sequence)

### Wave 1 — Core (Parallel on both PCs)
- **PC1**: Step 1 (Setup Wizard) + Step 2 (Backend Process Mgmt)
- **PC2**: Step 4 (Service Orchestrator) + Step 5 (Frontend Integration)

### Wave 2 — Resilience + Packaging
- **PC1**: Step 3 (Peer Monitor & Resilience) — needs PC2's service orchestrator for testing
- **PC1**: Step 6 (Packaging) — needs both PCs' work integrated

### Wave 3 — Mobile + Polish
- **PC2**: Step 7 (iPhone PWA)
- **BOTH**: Step 8 (Crash recovery, auto-updater, logging)

---

## Success Criteria (Same as Build Plan)

- [ ] Double-click one icon on ESPENMAIN → entire trading system running in < 30 seconds
- [ ] Double-click same icon on Profit Trader → connects to ESPENMAIN, starts compute services
- [ ] If Profit Trader goes offline → ESPENMAIN continues trading in degraded mode
- [ ] If Profit Trader comes back → auto-recovery, full cluster restored
- [ ] iPhone PWA → view P&L, positions, hit emergency stop from anywhere
- [ ] No more terminals. No more port conflicts. No more BS.
