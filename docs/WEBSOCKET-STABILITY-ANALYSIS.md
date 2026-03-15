# WebSocket & Backend Stability Analysis

**Date**: March 14, 2026
**Version**: v5.0.0
**Scope**: Backend crash loops, WebSocket resilience, Alpaca connection management

---

## 1. Executive Summary

Analysis of `logs/backend_autorestart.log` (250+ entries) and `logs/startup-audit.log` reveals
recurring backend crash loops (exit_code=1), watchdog kills (exit_code=-1), and Alpaca WebSocket
"connection limit exceeded" errors. This document maps root causes to existing mitigations and
identifies remaining gaps.

**Key finding**: The codebase already implements **most** of the proposed mitigations. The remaining
gaps are targeted improvements to startup grace timing, file-based crash logging, and Alpaca WS
connect delay.

---

## 2. Log Patterns

| Exit Code | Meaning | Pattern |
|-----------|---------|---------|
| -1 | Watchdog kill (`process.Kill()`) | Health check fails 3x → backend killed |
| 1 | Python exception | Crash within ~5-6s of start |
| 2 | DuckDB lock (`os._exit(2)`) | Another process holds DuckDB |
| 3 | Process lock (`os._exit(3)`) | Another backend already running |

**Observed**: exit_code=1 very frequent (20:09-20:16, ~100 runs in ~7 min) = crash loop on startup.
exit_code=-1 every ~3-4 min = backend hangs, watchdog kills it.

---

## 3. Root Causes & Existing Mitigations

### A. Startup / Crash Loop (exit_code=1)

| Cause | Mitigation | Status |
|-------|-----------|--------|
| DuckDB lock (stale WAL) | Progressive retry 2+4+8+16s, WAL cleanup | **IMPLEMENTED** (`main.py:1480-1547`) |
| Import/init error | Process exits immediately | Partially handled — see Gap #1 |
| Port 8000 conflict | Process lock + port check in autorestart | **IMPLEMENTED** (`run_backend_autorestart.ps1:100-105`) |
| Duplicate backend instance | Process lock with PID file | **IMPLEMENTED** (`main.py:1437-1441`, `process_lock.py`) |

### B. Hang / Watchdog Kill (exit_code=-1)

| Cause | Mitigation | Status |
|-------|-----------|--------|
| Lifespan blocks event loop | Deferred heavy services (15s delay) | **IMPLEMENTED** (`main.py:876`, `DEFERRED_STARTUP_DELAY`) |
| ConnectionResetError flood | Windows ProactorEventLoop patch | **IMPLEMENTED** (`main.py:20-34`) |
| Startup grace too short | 120s grace period | **IMPLEMENTED** but could increase — see Gap #2 |
| Heavy scouts/streams at startup | `SCOUTS_ENABLED=false`, `DISABLE_ALPACA_DATA_STREAM=1` | **IMPLEMENTED** (`main.py:453, 764`) |

### C. WebSocket Down

| Cause | Mitigation | Status |
|-------|-----------|--------|
| Backend down → WS fails | Frontend exponential backoff (10 attempts) | **IMPLEMENTED** (`websocket.js:170-208`) |
| No reconnection UI | Yellow pulsing "RECONNECTING" indicator | **IMPLEMENTED** (`Header.jsx:211-234`) |
| WS handler blocks event loop | Async `broadcast_ws()` with dead connection cleanup | **IMPLEMENTED** (`websocket_manager.py:123-148`) |
| Polling fallback after max retries | Falls back after 10 failed attempts | **IMPLEMENTED** (`websocket.js:180-187`) |

### D. Alpaca "connection limit exceeded"

| Cause | Mitigation | Status |
|-------|-----------|--------|
| Multiple WS per account | Fallback to REST snapshots after 1 failure | **IMPLEMENTED** (`alpaca_stream_service.py:163-178`) |
| Restart loop opens new WS | Guarded auth + backoff | **IMPLEMENTED** (`alpaca_stream_service.py:466-487`) |
| 10+ consecutive failures | Circuit breaker → permanent REST | **IMPLEMENTED** (`alpaca_stream_service.py:196-218`) |
| New backend connects before old disconnects | No explicit delay | **GAP** — see Gap #3 |

---

## 4. Remaining Gaps

### Gap #1: No file-based logging for crash diagnosis

**Problem**: When the autorestart script kills the backend, stdout is lost (hidden window).
The autorestart script logs exit codes to `logs/backend_autorestart.log`, but the Python
traceback that caused the crash is not captured.

**Fix**: Add a `RotatingFileHandler` to the root logger in `main.py` so crash tracebacks
persist in `logs/backend.log`.

### Gap #2: Startup grace period may be too short

**Problem**: With DuckDB WAL recovery (up to 30s) + deferred services (15s) + ML bootstrap,
total startup can exceed 120s. The watchdog starts counting health failures too early.

**Fix**: Increase `StartupGraceSeconds` from 120 to 180 in `run_backend_autorestart.ps1`.

### Gap #3: Alpaca WS connects too early after restart

**Problem**: When the backend restarts, it immediately tries to open an Alpaca WebSocket.
If the previous connection hasn't fully closed on Alpaca's side, the new connection gets
"connection limit exceeded". The existing fallback works, but it means the restart always
starts in degraded (snapshot polling) mode.

**Fix**: Add a configurable delay (`ALPACA_WS_CONNECT_DELAY`, default 30s) before the
AlpacaStreamManager starts its WebSocket connection. This gives the previous connection
time to close on Alpaca's side.

---

## 5. Proposed Plan Assessment

### Already Implemented (no action needed)

| Proposed Item | Status | Location |
|---------------|--------|----------|
| Phase 1.2: Log exit code in autorestart | DONE | `run_backend_autorestart.ps1:200` |
| Phase 1.3: Startup phase timing | DONE | `main.py:1441-1872` (`[STARTUP] Phase X:` logs) |
| Phase 2.1: Early /healthz response | DONE | `main.py` `/healthz` endpoint (<50ms, zero deps) |
| Phase 2.2: SCOUTS_ENABLED=false | DONE | `main.py:453` |
| Phase 2.3: DISABLE_ALPACA_DATA_STREAM | DONE | `main.py:764` |
| Phase 3.1: DuckDB WAL cleanup on shutdown | DONE | `main.py:1520-1547`, `duckdb_storage.py` |
| Phase 3.2: Pre-start port + process check | DONE | `run_backend_autorestart.ps1:100-105`, `process_lock.py` |
| Phase 3.4: Alpaca connection limit backoff | DONE | `alpaca_stream_service.py:161-223` (circuit breaker) |
| Phase 4.1: Frontend exponential backoff | DONE | `websocket.js:170-208` (10-attempt escalation) |
| Phase 4.2: "Reconnecting..." UI | DONE | `Header.jsx:211-234` (yellow pulsing pill) |

### Implementing Now

| Proposed Item | Gap | Change |
|---------------|-----|--------|
| Phase 1.1: File logging | Gap #1 | Add `RotatingFileHandler` to `main.py` |
| Phase 2.4: Increase startup grace | Gap #2 | 120s → 180s in autorestart script |
| Phase 2.5: Delay before Alpaca WS | Gap #3 | Add `ALPACA_WS_CONNECT_DELAY` env var |

### Not Needed (already covered)

| Proposed Item | Reason |
|---------------|--------|
| Phase 3.3: Wrap lifespan in try/except | Already wrapped — each phase has try/except |
| Phase 4.3: Audit WS handler for blocking | `broadcast_ws()` is fully async, no blocking |
| Phase 5.2: "Run from primary only" docs | Covered by `RUNBOOK.md` and process lock |

---

## 6. Architecture Strengths (Do Not Break)

1. **Circuit breaker** in autorestart: 5 crashes in 10min → stops restarting
2. **DuckDB WAL recovery**: Progressive retry with stale file cleanup
3. **Alpaca WS circuit breaker**: 10 failures → permanent REST fallback
4. **Frontend WS resilience**: 10-attempt escalation + polling fallback + "RECONNECTING" UI
5. **Process lock**: Single backend per machine enforced
6. **Deferred startup**: Heavy services delayed 15s to keep API responsive
7. **Supervised loops**: Background tasks auto-restart (3 retries + Slack alert)
8. **Heartbeat system**: Backend pings every 30s, timeout 60s, dead connection cleanup

---

## 7. Open Questions (from original analysis)

1. **Do you run from both primary and Dev copies?** — Process lock prevents this per-machine,
   but cross-machine (PC1 + PC2) both running backends would cause DuckDB conflicts if sharing
   the same DB file. The dual-PC architecture uses separate Alpaca keys per PC to avoid WS conflicts.

2. **Is Ollama expected on this machine?** — Ollama runs on PC2 (ProfitTrader, 192.168.1.116).
   The 404 on localhost:11434 is expected on PC1. Set `LLM_ENABLED=false` on PC1 if brain_service
   on PC2 is the only LLM provider.

3. **Priority order** — Implementing Gap #1 (file logging), Gap #2 (grace period), Gap #3
   (Alpaca WS delay) in this commit.
