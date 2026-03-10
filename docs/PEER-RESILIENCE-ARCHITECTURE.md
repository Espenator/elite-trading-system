# Peer Resilience Architecture

**Status:** IN PROGRESS
**Created:** March 9, 2026
**Parent Doc:** [ELECTRON-DESKTOP-BUILD-PLAN.md](./ELECTRON-DESKTOP-BUILD-PLAN.md)
**Implements:** Phase 1C of Desktop Build Plan

---

## Overview

When running in 2-PC distributed mode, the system must handle peer disconnection gracefully. The Primary (ESPENMAIN) must continue trading even if the Secondary (Profit Trader) goes offline, losing brain-service (LLM inference) and scanner capabilities.

This document defines the tiered fallback strategy, the peer-monitor state machine, and the recovery process.

---

## Cluster Topology

```
ESPENMAIN (Primary)                    Profit Trader (Secondary)
+---------------------------+          +---------------------------+
| backend (FastAPI)         |  gRPC    | backend (FastAPI)         |
| frontend (Next.js)        |<-------->| frontend (Next.js)        |
| council (35 agents)       |  REST    | brain-service (Ollama)    |
| ml-engine (XGBoost/LSTM)  |          | scanner (OpenClaw)        |
| event-pipeline            |          |                           |
+---------------------------+          +---------------------------+
        |                                        |
        |  Heartbeat every 10s (gRPC health)     |
        +----------------------------------------+
```

### What Primary loses when Secondary goes down:
- **brain-service**: LLM inference for agent reasoning, market analysis
- **scanner**: OpenClaw market scanning for opportunity discovery
- **secondary frontend**: Monitoring view on second machine

### What Primary retains:
- **All 35 council agents** (they run on Primary)
- **ML engine**: XGBoost, LSTM, HMM models (run on Primary)
- **Event pipeline**: Real-time data processing
- **Trading execution**: Alpaca API connection
- **All technical indicators and signals**

---

## Peer State Machine

```
                    heartbeat OK
               +------------------+
               |                  |
               v                  |
+----------+   heartbeat    +-----------+
|          |   timeout      |           |
| UNKNOWN  +--------------->| CONNECTED |
|          |   (on start)   |           |
+----+-----+                +-----+-----+
     |                            |
     |                            | 3 missed heartbeats (30s)
     |                            v
     |                      +-----------+
     |                      |           |
     +--------------------->| DEGRADED  |
        no peer configured  |           |
                            +-----+-----+
                                  |
                                  | 2 minutes no response
                                  v
                            +-----------+
                            |           |
                            |   LOST    |
                            |           |
                            +-----+-----+
                                  |
                                  | heartbeat resumes
                                  v
                            +-----------+
                            |           |
                            | RECOVERED |
                            |           |
                            +-----+-----+
                                  |
                                  | stable for 30s
                                  v
                            +-----------+
                            |           |
                            | CONNECTED |
                            |           |
                            +-----------+
```

---

## Tiered Fallback Strategy

### TIER 1: RETRY (0-30 seconds after lost heartbeat)

**Trigger:** 1-3 missed heartbeats
**Peer State:** DEGRADED

**Actions:**
- gRPC reconnection attempts every 5 seconds
- Queue any pending brain-service requests (max queue: 50 items)
- Continue trading with CACHED intelligence from last brain-service responses
- Dashboard shows: "Warning: Brain Service: Reconnecting..."

**Trading Impact:**
- None. System operates on cached data.
- No risk parameter changes.
- Most recent brain analysis still valid for short-term decisions.

---

### TIER 2: LOCAL FALLBACK (30 seconds - 2 minutes)

**Trigger:** Peer state transitions to DEGRADED for > 30s
**Peer State:** DEGRADED (extended)

**Actions:**
- Attempt to spin up LOCAL Ollama on ESPENMAIN
- Use a SMALLER model for reduced resource usage:
  - Primary model on Profit Trader: llama3.2 (full)
  - Fallback model on ESPENMAIN: llama3.2:1b (1 billion params)
- Re-route brain-service gRPC requests to localhost:50051
- Scanner functions DISABLED (no OpenClaw without Secondary)
- Drain pending request queue through local model
- Dashboard shows: "Warning: Degraded Mode - Local Brain (reduced quality)"

**Trading Impact:**
- LLM analysis quality reduced (smaller model)
- Scanner-dependent signals unavailable
- Council agents that depend on brain analysis get lower-quality input
- No automatic risk changes yet

**Ollama Fallback Process:**
```
1. Check if Ollama is installed on ESPENMAIN
2. If not installed -> skip to TIER 3
3. If installed -> check if llama3.2:1b model is available
4. If not available -> attempt to pull (if internet available)
5. If available -> start ollama serve (if not already running)
6. Start local brain-service gRPC server pointing to localhost Ollama
7. Update brain-service endpoint in backend config
8. Resume brain-service requests through local model
```

---

### TIER 3: NO-BRAIN MODE (2+ minutes, or local Ollama unavailable)

**Trigger:** Peer state transitions to LOST, AND local Ollama fallback failed
**Peer State:** LOST

**Actions:**
- Disable ALL LLM-dependent features
- Council agents vote WITHOUT brain analysis input
- Agents that critically depend on LLM abstain from voting
- ML-engine + technical signals STILL WORK (they run locally)
- Risk management tightens automatically:

**Risk Parameter Changes:**
```
| Parameter                    | Normal Value | No-Brain Value | Rationale                          |
|------------------------------|--------------|----------------|------------------------------------|  
| Max position size            | 100%         | 50%            | Reduced confidence without LLM     |
| Required consensus threshold | 65%          | 80%            | Higher bar without full analysis   |
| New positions allowed        | Yes          | No             | Only manage existing positions     |
| Stop-loss tightening         | Normal       | +20% tighter   | Protect capital in degraded state  |
| Max concurrent positions     | Normal       | Reduce by 50%  | Reduce exposure                    |
```

- Dashboard shows: "ALERT: No Brain - Conservative Mode"
- Push notification to iPhone PWA: "Brain service down - conservative mode active"
- Log event with timestamp for post-mortem analysis

**Trading Impact:**
- No new positions opened
- Existing positions managed with tighter stops
- Technical-only signals still processed but not acted on
- System is in "protect capital" mode

---

## Recovery Process

**Trigger:** Heartbeat from peer resumes
**Peer State:** RECOVERED -> CONNECTED

```
1. Detect peer heartbeat resumed
2. Verify brain-service gRPC endpoint is responsive on peer
3. Run a test inference request to confirm quality
4. If test passes:
   a. Gracefully shut down local Ollama fallback (if running)
   b. Re-route brain-service requests back to Profit Trader
   c. Re-enable scanner functions
   d. Restore normal risk parameters (gradual, not instant)
   e. Allow new positions after 30s of stable connection
5. Dashboard shows: "Cluster Restored - Full Mode"
6. Log recovery event with outage duration
7. After 30s stable -> transition to CONNECTED state
```

**Risk Parameter Restoration (Gradual):**
```
- At recovery + 0s:   Stop-loss tightening removed
- At recovery + 10s:  Consensus threshold back to normal
- At recovery + 30s:  New positions allowed
- At recovery + 60s:  Max position size restored
- At recovery + 120s: All parameters fully normal
```

This gradual restoration prevents whiplash if the connection is unstable.

---

## Implementation: peer-monitor.js

### Module Responsibilities
```
peer-monitor.js
+-- Heartbeat sender (ping peers every 10s)
+-- State machine (UNKNOWN -> CONNECTED -> DEGRADED -> LOST -> RECOVERED)
+-- Event emitter:
|   +-- "peer:connected"    - peer came online
|   +-- "peer:degraded"     - heartbeats failing
|   +-- "peer:lost"         - peer confirmed down
|   +-- "peer:recovered"    - peer came back
+-- Fallback orchestrator:
|   +-- Triggers Tier 1/2/3 based on state
|   +-- Manages local Ollama lifecycle
|   +-- Adjusts risk parameters via backend API
+-- Cluster health reporter:
    +-- WebSocket events to dashboard
    +-- iPhone PWA push notifications
```

### Configuration
```javascript
const PEER_MONITOR_CONFIG = {
  heartbeatInterval: 10000,      // 10 seconds
  degradedThreshold: 30000,      // 30 seconds (3 missed)
  lostThreshold: 120000,         // 2 minutes
  recoveryStableTime: 30000,     // 30s stable before CONNECTED
  maxQueueSize: 50,              // max queued brain requests
  fallbackModel: 'llama3.2:1b',  // smaller model for local fallback
  riskRestorationSteps: [0, 10000, 30000, 60000, 120000], // ms after recovery
};
```

---

## Implementation: ollama-fallback.js

### Module Responsibilities
```
ollama-fallback.js
+-- Check Ollama installation on local machine
+-- Check available models
+-- Start/stop Ollama serve process
+-- Pull fallback model if needed
+-- Start local brain-service gRPC server
+-- Health check local Ollama
+-- Cleanup on shutdown or recovery
```

### States
```
IDLE -> CHECKING -> STARTING -> RUNNING -> STOPPING -> IDLE
                 -> UNAVAILABLE (Ollama not installed)
```

---

## Dashboard UI Indicators

### Cluster Health Widget (top-right of dashboard)
```
Full Mode:     [=====] 2/2 nodes | Brain: Remote (Profit Trader) | Scanner: Active
Degraded:      [===--] 1/2 nodes | Brain: Local Fallback          | Scanner: Off  
No-Brain:      [=----] 1/2 nodes | Brain: Offline                 | Scanner: Off
Recovering:    [====~] 2/2 nodes | Brain: Restoring...            | Scanner: Starting
```

### Alert Banner (full-width, below header)
```
DEGRADED:  "Profit Trader unreachable - using local brain fallback (reduced quality)"
NO-BRAIN:  "CONSERVATIVE MODE - No brain service available - no new positions"
RECOVERY:  "Cluster recovering - risk parameters restoring (2m remaining)"
```

---

## Testing Scenarios

| # | Scenario | Expected Behavior |
|---|----------|--------------------|
| 1 | Start Primary only (no Secondary configured) | Full mode, all services local |
| 2 | Start Primary + Secondary, both healthy | Distributed mode, brain on Secondary |
| 3 | Kill Secondary process | Tier 1 -> 2 -> 3 degradation over 2 min |
| 4 | Restart Secondary after kill | Recovery, gradual parameter restoration |
| 5 | Network cable disconnect (abrupt) | Same as #3 but no graceful shutdown |
| 6 | Secondary flapping (on/off/on/off) | Should not whiplash between modes |
| 7 | Primary has Ollama installed | Tier 2 activates local fallback |
| 8 | Primary does NOT have Ollama | Skips Tier 2, goes directly to Tier 3 |
| 9 | Secondary comes back but brain-service fails | Stay in degraded, don't fully restore |
| 10 | Both PCs reboot simultaneously | Each detects role on startup, reconnects |

---

## Related Documents

- [ELECTRON-DESKTOP-BUILD-PLAN.md](./ELECTRON-DESKTOP-BUILD-PLAN.md) - Parent build plan
- [CLUSTER-NETWORK-SETUP.md](./CLUSTER-NETWORK-SETUP.md) - Network configuration
- [NETWORK_TWO_PC_SETUP.md](./NETWORK_TWO_PC_SETUP.md) - Two-PC setup guide
- [AI_TWO_PC_CODING_GUIDE.md](./AI_TWO_PC_CODING_GUIDE.md) - Cross-PC coding rules
- [HARDWARE-SPECS.md](./HARDWARE-SPECS.md) - Machine specifications
