# Embodier Trader - Status & TODO Update

## Date: March 9, 2026

## Author: Espen + Comet (Perplexity)

## Repository: github.com/Espenator/elite-trading-system

## Version: 4.1.0-dev (Electron Desktop App)

---

## EXECUTIVE SUMMARY

**ARCHITECTURE PIVOT: From browser-based to native Electron desktop app.**

Daily operational pain of managing separate frontend/backend processes, port conflicts, and terminal juggling has reached a breaking point. Decision made to package Embodier Trader as a single Electron desktop application with resilient 2-PC distributed compute support.

**Decision:** Build Electron desktop app with 3 operating modes (Full, Primary+Secondary, Degraded) and iPhone PWA for remote monitoring.

**Tracking:** See [ELECTRON-DESKTOP-BUILD-PLAN.md](./ELECTRON-DESKTOP-BUILD-PLAN.md)

---

## CURRENT SYSTEM STATE (as of March 9, 2026)

| Area | Status |
|------|--------|
| Frontend (14 pages) | ALL COMPLETE - pixel-matched to mockups |
| Backend (29 API routes, 24 services) | COMPLETE - all mounted |
| Council (35 agents, 7-stage DAG) | COMPLETE - CouncilGate v3.5.0 |
| ML Pipeline (XGBoost/LSTM/HMM) | COMPLETE |
| Brain Service (gRPC/Ollama) | COMPLETE - runs on Profit Trader |
| Electron Desktop Shell | 80% SCAFFOLDED - needs finishing |
| Peer Resilience | NOT STARTED - architecture designed |
| iPhone PWA | NOT STARTED - planned |
| CI/CD (666 tests) | GREEN |

---

## WHAT WAS DONE (Mar 9 Session)

### Electron Desktop App Planning
- Diagnosed daily startup pain (port conflicts, manual terminal management)
- Evaluated options: Electron vs Tauri vs PWA-only
- Chose Electron with PyInstaller-bundled backend
- Designed 3-mode architecture (Full / Primary+Secondary / Degraded)
- Reviewed existing desktop/ folder code (main.js, device-config.js, backend-manager.js)
- Identified existing 2-PC distributed compute architecture (ESPENMAIN + Profit Trader)
- Designed tiered peer resilience fallback (Tier 1: Retry, Tier 2: Local Ollama, Tier 3: No-Brain)
- Designed iPhone PWA remote access via Tailscale

### Documentation Created
- [x] `docs/ELECTRON-DESKTOP-BUILD-PLAN.md` - Full 3-phase build plan with task checklists
- [x] `docs/PEER-RESILIENCE-ARCHITECTURE.md` - Tiered fallback strategy, state machine, recovery
- [x] `docs/STATUS-AND-TODO-2026-03-09.md` - This document
- [ ] Root README.md update - Add desktop app section

---

## WHAT NEEDS TO BE BUILT

### Phase 1: Core Electron App (Windows) - ~2 weeks

| Task | Sub-phase | Status | Effort |
|------|-----------|--------|--------|
| Setup wizard (mode selection, peer config, API keys) | 1A | NOT STARTED | 3 days |
| PyInstaller backend bundle + process management | 1B | PARTIAL (backend-manager.js exists) | 3 days |
| peer-monitor.js (heartbeat, state machine, fallback) | 1C | NOT STARTED | 3 days |
| service-orchestrator.js (role-based service launcher) | 1D | NOT STARTED | 2 days |
| Frontend integration (bundle Next.js in Electron) | 1E | NOT STARTED | 2 days |
| electron-builder packaging + installer | 1F | NOT STARTED | 3 days |

### Phase 2: iPhone PWA - ~1 week

| Task | Sub-phase | Status | Effort |
|------|-----------|--------|--------|
| PWA manifest + service worker | 2A | NOT STARTED | 2 days |
| Mobile-responsive dashboard | 2B | NOT STARTED | 3 days |
| Tailscale remote access + push notifications | 2C | NOT STARTED | 2 days |

### Phase 3: Polish & Reliability - ~1 week

| Task | Sub-phase | Status | Effort |
|------|-----------|--------|--------|
| Crash recovery + auto-restart | 3A | NOT STARTED | 2 days |
| Auto-updater (GitHub Releases) | 3B | NOT STARTED | 2 days |
| Unified logging + diagnostics | 3C | NOT STARTED | 1 day |

---

## NEW FILES TO CREATE

| File | Purpose | Priority |
|------|---------|----------|
| `desktop/peer-monitor.js` | Peer health monitoring & fallback orchestration | P0 |
| `desktop/service-orchestrator.js` | Role-based service launcher | P0 |
| `desktop/ollama-fallback.js` | Local LLM fallback manager | P1 |
| `desktop/electron-builder.yml` | Build/packaging configuration | P1 |
| `desktop/pyinstaller.spec` | Backend bundling specification | P1 |
| `desktop/pages/setup-welcome.html` | Setup wizard - mode selection | P0 |
| `desktop/pages/setup-peer.html` | Setup wizard - peer configuration | P0 |
| `desktop/pages/setup-keys.html` | Setup wizard - API keys | P0 |
| `desktop/pages/setup-complete.html` | Setup wizard - summary & launch | P0 |
| `frontend-v2/public/manifest.json` | PWA manifest for iPhone | P2 |
| `frontend-v2/public/sw.js` | Service worker for PWA | P2 |

---

## EXISTING FILES TO MODIFY

| File | Changes Needed | Priority |
|------|----------------|----------|
| `desktop/main.js` | Integrate service-orchestrator, peer-monitor | P0 |
| `desktop/backend-manager.js` | Add PyInstaller prod mode, auto-port | P0 |
| `desktop/device-config.js` | Add "full" mode profile, fallback settings | P1 |
| `desktop/package.json` | Add electron-builder, electron-updater deps | P1 |
| `README.md` (root) | Add Desktop App section | P1 |
| `backend/main.py` | Add /health endpoint if missing, risk parameter API | P1 |

---

## PRIORITY ORDER

1. **P0 - Get it running:** Setup wizard + backend process management + service orchestrator
2. **P0 - Make it resilient:** peer-monitor.js + fallback chain
3. **P1 - Package it:** PyInstaller + electron-builder + installer
4. **P2 - Mobile access:** PWA + Tailscale
5. **P3 - Polish:** Auto-updater + logging + crash recovery

---

## GOAL

Double-click one icon. Everything starts. No more BS.

---

## Related Documents

- [ELECTRON-DESKTOP-BUILD-PLAN.md](./ELECTRON-DESKTOP-BUILD-PLAN.md) - Full build plan
- [PEER-RESILIENCE-ARCHITECTURE.md](./PEER-RESILIENCE-ARCHITECTURE.md) - Fallback architecture
- [STATUS-AND-TODO-2026-03-07.md](./STATUS-AND-TODO-2026-03-07.md) - Previous status update
- [CLUSTER-NETWORK-SETUP.md](./CLUSTER-NETWORK-SETUP.md) - Network config
- [AI_TWO_PC_CODING_GUIDE.md](./AI_TWO_PC_CODING_GUIDE.md) - Cross-PC coding rules
