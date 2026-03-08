# Machine Awareness Architecture Audit Report
**Date:** 2026-03-08
**Version:** 4.0.0
**Auditor:** Claude Agent (Anthropic)
**Issue:** Dual-PC Deployment Machine Awareness Implementation

---

## Executive Summary

The Elite Trading System currently has **partial dual-PC infrastructure** but lacks **deterministic machine-awareness** and **robust single-PC fallback**. The system has GPU telemetry, node discovery, and LLM dispatcher capabilities, but no explicit machine identity, role assignment, or graceful degradation when PC2 is unavailable.

### Critical Findings

1. **No explicit machine identity system** - services cannot reliably determine "am I PC1 or PC2?"
2. **No settings UI for machine configuration** - operators must manually edit .env files
3. **Incomplete fallback logic** - PC2 death triggers routing changes but not full service failover
4. **Scattered machine-role assumptions** - PC1/PC2 roles implied but not enforced
5. **Missing deployment mode visibility** - UI doesn't show single vs dual-PC mode

### Recommended Actions

1. Create `MachineIdentityService` for deterministic machine detection
2. Extend settings schema with `machine`, `deployment`, and `infrastructure` categories
3. Add "Machine & Deployment" section to Settings UI
4. Update startup logic to validate deployment mode and surface it prominently
5. Implement comprehensive single-PC fallback for all distributed services

---

## 1. Repository Architecture Inventory

### 1.1 Current Two-PC Infrastructure Files

| File | Purpose | Status | Machine-Aware? |
|------|---------|--------|----------------|
| `docs/NETWORK_TWO_PC_SETUP.md` | Network configuration guide | **Active** | Yes - documents PC1/PC2 IPs |
| `docs/AI_TWO_PC_CODING_GUIDE.md` | AI coding rules for 2-PC dev | **Active** | Yes - PC1/PC2 role definitions |
| `backend/app/core/config.py` | Application settings | **Active** | Partial - has some cluster settings |
| `backend/app/services/node_discovery.py` | PC2 capability discovery | **Active** | Yes - discovers PC2 endpoints |
| `backend/app/services/gpu_telemetry.py` | GPU/VRAM monitoring daemon | **Active** | Partial - broadcasts node telemetry |
| `backend/app/services/llm_dispatcher.py` | Telemetry-aware LLM routing | **Active** | Yes - routes by GPU utilization |
| `backend/app/services/model_pinning.py` | PC1/PC2 model affinity | **Active** | Yes - maps models to nodes |
| `backend/app/services/llm_router.py` | LLM routing abstraction | **Active** | Partial - uses dispatcher |
| `backend/app/services/settings_service.py` | Settings persistence layer | **Active** | No - lacks machine fields |
| `backend/app/api/v1/settings_routes.py` | Settings API | **Active** | No |
| `frontend-v2/src/pages/Settings.jsx` | Settings UI | **Active** | No - lacks deployment section |
| `brain_service/README.md` | gRPC brain service docs | **Active** | Yes - intended for PC2 |

### 1.2 Environment Variable References

**Existing cluster-related settings in `config.py`:**

```python
# Lines 219-227 in config.py
CLUSTER_PC2_HOST: str = ""  # Empty = single-PC mode
CLUSTER_HEALTH_INTERVAL: int = 60

REDIS_URL: str = ""  # for cross-PC MessageBus bridge

# Lines 214-218: Dual-PC Ollama
OLLAMA_PC2_URL: str = "http://localhost:11434"
OLLAMA_SMALL_MODEL: str = "mistral:7b"          # PC-1: fast
OLLAMA_LARGE_MODEL: str = "llama3:70b-q4_K_M"   # PC-2: complex

# Lines 234-242: Model Pinning
MODEL_PIN_PC1: str = "llama3.2,mistral:7b"
MODEL_PIN_PC2: str = "deepseek-r1:14b,mixtral:8x7b"
MODEL_PIN_TASK_AFFINITY: str = "..."
```

**Gap:** No `MACHINE_ID`, `MACHINE_ROLE`, `DEPLOYMENT_MODE`, `PEER_HOST`, or `FALLBACK_ENABLED` fields.

### 1.3 Service-Level Machine Awareness

| Service | Detects Own Machine? | Knows Peer Machine? | Handles Peer Offline? |
|---------|---------------------|---------------------|-----------------------|
| NodeDiscovery | No | Yes (via `CLUSTER_PC2_HOST`) | Partial - marks unavailable |
| GPUTelemetryDaemon | No | No | N/A - local only |
| LLMDispatcher | No | Yes (via telemetry) | **Yes** - graceful degradation |
| ModelPinning | No | Yes (via config) | No |
| BrainClient | No | Yes (via `BRAIN_HOST`) | Partial - retries |

**Gap:** No service can answer "which machine am I running on?" without inspecting hostname.

---

## 2. Current Architecture as Discovered

### 2.1 Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     AT&T BGW320-505 Router                  │
│                    192.168.1.254 (Gateway)                  │
└───────────────────┬─────────────────────┬───────────────────┘
                    │                     │
        ┌───────────▼──────────┐  ┌──────▼────────────┐
        │   ESPENMAIN (PC1)    │  │  ProfitTrader     │
        │   192.168.1.105      │  │  (PC2)            │
        │   Primary Node       │  │  192.168.1.116    │
        ├──────────────────────┤  ├───────────────────┤
        │ FastAPI Backend      │  │ GPU Training      │
        │ React Frontend       │  │ Brain gRPC        │
        │ DuckDB Database      │  │ Ollama (heavy)    │
        │ Ollama (fast models) │  │ ML Training       │
        │ MessageBus           │  │                   │
        └──────────────────────┘  └───────────────────┘
```

### 2.2 Documented PC Roles (from AI_TWO_PC_CODING_GUIDE.md)

| | PC1 (Primary) | PC2 (Secondary) |
|--|--------------|----------------|
| **Hostname** | ESPENMAIN | ProfitTrader |
| **LAN IP** | 192.168.1.105 | 192.168.1.116 |
| **Role** | Backend API, frontend dev, primary coding | GPU ML training, secondary services |
| **User** | C:\Users\Espen | C:\Users\ProfitTrader |
| **Repo** | C:\Users\Espen\elite-trading-system | C:\Users\ProfitTrader\elite-trading-system |

### 2.3 Current Service Distribution

**Runs on PC1 (ESPENMAIN):**
- FastAPI backend (port 8000)
- React frontend (port 3000)
- DuckDB database
- Council orchestration (31-agent DAG)
- Event-driven signal engine
- Order executor
- Ollama (fast models: llama3.2, mistral:7b)
- MessageBus coordinator

**Runs on PC2 (ProfitTrader) (when available):**
- Brain gRPC service (port 50051)
- Ollama (heavy models: deepseek-r1:14b, mixtral:8x7b, llama3:70b)
- ML model training jobs
- GPU-intensive inference

**Problem:** This distribution is **implicit**, not **explicit**. No startup validation ensures services run on the correct machine.

---

## 3. Gaps and Risks

### 3.1 Settings Schema Gaps

Current `settings_service.py` DEFAULTS (line 23-292) has 18 categories:

1. trading
2. risk
3. kelly
4. dataSources
5. notifications
6. ml
7. agents
8. openclaw
9. ollama
10. tradingview
11. finvizScreener
12. council
13. strategy
14. logging
15. system
16. user
17. device (line 261-269) - **partially relevant**
18. appearance
19. alignment

**Existing `device` category (lines 261-269):**
```python
"device": {
    "deviceName": "",
    "deviceRole": "full",  # ← vague, not PC1/PC2
    "backendPort": 8000,
    "brainHost": "localhost",
    "brainPort": 50051,
    "peerDevices": [],  # ← not used
    "tradingMode": "live",
},
```

**Missing Fields:**
- `machineId` / `machineName`
- `isPrimaryNode` or explicit `nodeRole: "pc1" | "pc2" | "standalone"`
- `deploymentMode: "single_pc" | "dual_pc"`
- `peerMachineHost` / `peerMachineIp`
- `peerOnline: bool`
- `fallbackModeActive: bool`
- `gpuEnabled: bool`
- `gpuDeviceIndex: int`
- `serviceAffinity: {...}`
- `autoDetectMachine: bool`

### 3.2 UI Gaps (Settings.jsx)

Current Settings.jsx has **25 sections** across 5 rows (lines 280-769):

**Row 1:**
1. Identity & Locale
2. Trading Mode
3. Position Rules
4. Risk Limits
5. Circuit Breakers

**Row 2:**
6. Brokerage Connections
7. Data Feed API Keys
8. Data Source Priority
9. Global Local LLM
10. Inference Models

**Row 3:**
11. ML Models
12. Learning Log
13. OpenClaw Agents
14. Agent Thresholds
15. Signal Thresholds

**Row 4:**
16. Trade Management
17. Order Execution
18. Notifications
19. Security & Auth
20. Backup & System

**Row 5:**
21. Appearance
22. Market Data
23. Notification Channels
24. Logging & Audit
25. Strategy Config

**Missing:** No "Machine & Deployment" or "Node Configuration" section.

**Impact:** Operators cannot:
- See which machine the UI is running on
- Select PC1 vs PC2 role
- Configure peer machine address
- See peer online/offline status
- Toggle single-PC fallback mode
- Configure GPU device assignment
- Set workload affinity

### 3.3 Startup Sequence Gaps

`backend/app/main.py` startup (based on standard FastAPI patterns):

**Current startup flow (inferred):**
1. Load settings from `config.py`
2. Initialize database
3. Start MessageBus
4. Start GPUTelemetryDaemon (if enabled)
5. Start NodeDiscovery (if `CLUSTER_PC2_HOST` set)
6. Mount API routes
7. Start Uvicorn server

**Missing:**
- Machine identity detection
- Deployment mode validation
- Service affinity enforcement
- Single-PC fallback checks
- Clear logs: "Deployment Mode: DUAL_PC | Machine: PC1 | Peer: ONLINE"

### 3.4 Fallback Logic Gaps

**LLMDispatcher (llm_dispatcher.py)** has **good** graceful degradation:
- Detects PC2 offline via missed telemetry heartbeats (lines 203-233)
- Degrades heavy models to fallback model (lines 296-311)
- Reroutes requests to healthy nodes

**NodeDiscovery (node_discovery.py)** has **partial** fallback:
- Marks PC2 Ollama/Brain unavailable if unreachable (lines 136-186)
- Does NOT remap services back to PC1

**Missing Fallback:**
- No automatic remap of training jobs from PC2 → PC1 when PC2 dies
- No UI indicator: "Running in FALLBACK MODE (PC2 unavailable)"
- No service startup guard: "Training service disabled (PC2 required)"

### 3.5 Workload Routing Clarity

**ModelPinning (`model_pinning.py`)** exists and maps:
- Models → PC1/PC2 (`MODEL_PIN_PC1`, `MODEL_PIN_PC2`)
- Tasks → PC1/PC2 (`MODEL_PIN_TASK_AFFINITY`)

**Gap:** Not integrated into service startup. Services don't check:
- "Should I start training jobs on this machine?"
- "Should I run heavy inference on this machine?"

---

## 4. Proposed Settings Schema

### 4.1 New `machine` Category

Add to `settings_service.py` DEFAULTS:

```python
"machine": {
    # Identity
    "machineId": "",  # ESPENMAIN | ProfitTrader | custom
    "machineName": "",  # friendly name
    "machineRole": "auto",  # "pc1" | "pc2" | "standalone" | "auto"
    "isPrimaryNode": None,  # bool | None (auto-detect)

    # Auto-detection
    "autoDetectHostname": True,
    "hostnameOverride": "",  # force specific hostname match

    # GPU
    "gpuEnabled": True,
    "gpuDeviceIndex": 0,
    "gpuRole": "mixed",  # "inference" | "training" | "mixed"
    "gpuVramHeadroom": 512,  # MB reserved as buffer
},
```

### 4.2 New `deployment` Category

```python
"deployment": {
    # Mode
    "deploymentMode": "auto",  # "single_pc" | "dual_pc" | "auto"
    "distributedModeEnabled": False,  # explicit toggle

    # Peer Configuration
    "peerMachineHost": "",  # IP or hostname of peer
    "peerMachineRole": "",  # "pc1" | "pc2" | ""
    "peerRequiredForStartup": False,
    "peerRequiredForExecution": False,

    # Fallback
    "allowSinglePcFallback": True,
    "fallbackModeActive": False,  # runtime state (read-only)
    "peerOnline": False,  # runtime state (read-only)

    # Service Affinity
    "serviceAffinityMode": "auto",  # "auto" | "manual"
    "runTrainingServices": "auto",  # "yes" | "no" | "auto"
    "runInferenceServices": "auto",
    "runExecutionServices": "auto",
    "runIntelligenceServices": "auto",
},
```

### 4.3 Update Existing `device` Category

Merge and deprecate unclear fields:

```python
"device": {
    "deviceName": "",  # deprecated - use machine.machineName
    "deviceRole": "full",  # deprecated - use machine.machineRole
    "backendPort": 8000,
    "brainHost": "localhost",  # migrate to deployment.peerMachineHost
    "brainPort": 50051,
    "peerDevices": [],  # deprecated
    "tradingMode": "live",  # already in trading category
},
```

---

## 5. Proposed UI Changes (Settings.jsx)

### 5.1 Add New Section: "Machine & Deployment"

Insert as **first section** in Row 1 or create new dedicated row:

```jsx
<SectionCard title="Machine & Deployment">
  {/* Deployment Mode */}
  <MiniSelect
    label="Deployment Mode"
    value={get("deployment", "deploymentMode", "auto")}
    options={[
      { value: "auto", label: "Auto-Detect" },
      { value: "single_pc", label: "Single PC" },
      { value: "dual_pc", label: "Dual PC" },
    ]}
    onChange={(e) => updateField("deployment", "deploymentMode", e.target.value)}
  />

  {/* Machine Identity */}
  <div className="flex items-center justify-between py-[1px]">
    <span className="text-[10px] text-gray-400">This Machine</span>
    <span className="text-[9px] text-[#00D9FF]">
      {get("machine", "machineId", "Unknown")}
      {get("machine", "machineRole") === "pc1" && " (PC1/Primary)"}
      {get("machine", "machineRole") === "pc2" && " (PC2/Secondary)"}
    </span>
  </div>

  {/* Machine Role Selector */}
  <MiniSelect
    label="Machine Role"
    value={get("machine", "machineRole", "auto")}
    options={[
      { value: "auto", label: "Auto-Detect" },
      { value: "pc1", label: "PC1 (ESPENMAIN/Primary)" },
      { value: "pc2", label: "PC2 (ProfitTrader/Secondary)" },
      { value: "standalone", label: "Standalone" },
    ]}
    onChange={(e) => updateField("machine", "machineRole", e.target.value)}
  />

  {/* Peer Configuration */}
  <MiniField
    label="Peer Machine"
    value={get("deployment", "peerMachineHost", "")}
    onChange={(e) => updateField("deployment", "peerMachineHost", e.target.value)}
    placeholder="192.168.1.116"
  />

  {/* Peer Status */}
  <div className="flex items-center justify-between py-[1px]">
    <span className="text-[10px] text-gray-400">Peer Status</span>
    <StatusDot ok={get("deployment", "peerOnline", false)} testing={false} />
    <span className="text-[9px] text-gray-500">
      {get("deployment", "peerOnline") ? "Online" : "Offline"}
    </span>
  </div>

  {/* Fallback Mode */}
  <MiniToggle
    label="Single-PC Fallback"
    checked={!!get("deployment", "allowSinglePcFallback", true)}
    onChange={(v) => updateField("deployment", "allowSinglePcFallback", v)}
  />

  {get("deployment", "fallbackModeActive") && (
    <div className="text-[9px] text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded px-2 py-1">
      ⚠ FALLBACK MODE ACTIVE (Peer Unavailable)
    </div>
  )}

  {/* GPU */}
  <MiniToggle
    label="GPU Enabled"
    checked={!!get("machine", "gpuEnabled", true)}
    onChange={(v) => updateField("machine", "gpuEnabled", v)}
  />

  <MiniField
    label="GPU Device"
    value={get("machine", "gpuDeviceIndex", 0)}
    type="number"
    onChange={(e) => updateField("machine", "gpuDeviceIndex", Number(e.target.value))}
  />
</SectionCard>
```

### 5.2 Visual Mockup

```
┌─────────────────────────────────────────┐
│  MACHINE & DEPLOYMENT                   │
├─────────────────────────────────────────┤
│ Deployment Mode    [Dual PC        ▼]  │
│ This Machine       ESPENMAIN (PC1)      │
│ Machine Role       [PC1/Primary    ▼]  │
│ Peer Machine       [192.168.1.116    ]  │
│ Peer Status        ● Online             │
│ Single-PC Fallback [ON              ]  │
│ GPU Enabled        [ON              ]  │
│ GPU Device         [0               ]  │
└─────────────────────────────────────────┘
```

---

## 6. Proposed Startup & Fallback Logic

### 6.1 New Service: `MachineIdentityService`

Create `backend/app/services/machine_identity.py`:

```python
"""Machine Identity Service — Deterministic machine detection and role assignment."""
import os
import socket
import logging
from typing import Optional, Literal

logger = logging.getLogger(__name__)

MachineRole = Literal["pc1", "pc2", "standalone"]
DeploymentMode = Literal["single_pc", "dual_pc"]


class MachineIdentityService:
    """Determines which machine we're running on and what mode we're in."""

    def __init__(self):
        self.machine_id: str = ""
        self.machine_name: str = ""
        self.machine_role: MachineRole = "standalone"
        self.deployment_mode: DeploymentMode = "single_pc"
        self.peer_host: str = ""
        self.peer_online: bool = False
        self.fallback_mode: bool = False
        self.gpu_enabled: bool = False

        self._detect()

    def _detect(self):
        """Priority: saved settings > env override > hostname detection > safe fallback."""
        from app.services.settings_service import get_settings_by_category

        machine_settings = get_settings_by_category("machine")
        deployment_settings = get_settings_by_category("deployment")

        # 1. Saved settings
        saved_role = machine_settings.get("machineRole", "auto")
        if saved_role in ("pc1", "pc2", "standalone"):
            self.machine_role = saved_role
            logger.info("MachineIdentity: using saved role=%s", saved_role)

        # 2. Environment override
        elif os.getenv("MACHINE_ROLE"):
            env_role = os.getenv("MACHINE_ROLE", "").lower()
            if env_role in ("pc1", "pc2", "standalone"):
                self.machine_role = env_role
                logger.info("MachineIdentity: using env MACHINE_ROLE=%s", env_role)

        # 3. Hostname detection
        else:
            hostname = socket.gethostname().upper()
            self.machine_id = hostname

            if "ESPENMAIN" in hostname:
                self.machine_role = "pc1"
                logger.info("MachineIdentity: detected hostname=%s → role=pc1", hostname)
            elif "PROFITTRADER" in hostname:
                self.machine_role = "pc2"
                logger.info("MachineIdentity: detected hostname=%s → role=pc2", hostname)
            else:
                self.machine_role = "standalone"
                logger.warning("MachineIdentity: unknown hostname=%s → role=standalone", hostname)

        # Deployment mode
        self.peer_host = deployment_settings.get("peerMachineHost", "").strip()
        if self.peer_host:
            self.deployment_mode = "dual_pc"
        else:
            self.deployment_mode = "single_pc"

        # GPU
        self.gpu_enabled = machine_settings.get("gpuEnabled", True)

    def check_peer_online(self) -> bool:
        """Ping peer to check if it's reachable."""
        if not self.peer_host:
            return False

        import httpx
        try:
            resp = httpx.get(f"http://{self.peer_host}:8000/api/v1/health", timeout=3.0)
            self.peer_online = resp.status_code == 200
        except Exception:
            self.peer_online = False

        self.fallback_mode = (self.deployment_mode == "dual_pc" and not self.peer_online)
        return self.peer_online

    def get_status(self):
        return {
            "machine_id": self.machine_id,
            "machine_name": self.machine_name,
            "machine_role": self.machine_role,
            "deployment_mode": self.deployment_mode,
            "peer_host": self.peer_host,
            "peer_online": self.peer_online,
            "fallback_mode": self.fallback_mode,
            "gpu_enabled": self.gpu_enabled,
        }
```

### 6.2 Startup Sequence Update (main.py)

```python
from app.services.machine_identity import MachineIdentityService

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 80)
    logger.info("Elite Trading System v%s - Starting", settings.APP_VERSION)

    # 1. Detect machine identity
    machine_identity = MachineIdentityService()
    status = machine_identity.get_status()

    logger.info("=" * 80)
    logger.info("DEPLOYMENT MODE: %s", status["deployment_mode"].upper())
    logger.info("MACHINE: %s (role=%s)", status["machine_id"], status["machine_role"])
    if status["deployment_mode"] == "dual_pc":
        logger.info("PEER: %s (%s)", status["peer_host"], "ONLINE" if status["peer_online"] else "OFFLINE")
        if status["fallback_mode"]:
            logger.warning("FALLBACK MODE ACTIVE - Running in single-PC mode (peer unavailable)")
    logger.info("GPU: %s", "ENABLED" if status["gpu_enabled"] else "DISABLED")
    logger.info("=" * 80)

    # 2. Start services based on role
    # ...existing startup code...

    yield

    logger.info("Shutting down...")
```

### 6.3 Fallback Behavior

**When `deployment_mode=dual_pc` and `peer_online=false`:**

1. **LLMDispatcher:** Already handles this - routes all to PC1 Ollama ✓
2. **Training Jobs:** Skip startup if `machine_role=pc1` and peer offline
3. **Brain gRPC:** Disable hypothesis_agent if brain unavailable
4. **UI:** Show amber badge "FALLBACK MODE" in header
5. **Logs:** Surface "Running degraded - PC2 unavailable"

---

## 7. Stale vs Active File Classification

### 7.1 Active (In Use)

| File | Purpose | Notes |
|------|---------|-------|
| `backend/app/core/config.py` | Settings schema | Needs extension |
| `backend/app/services/node_discovery.py` | PC2 discovery | Good foundation |
| `backend/app/services/gpu_telemetry.py` | GPU monitoring | Works well |
| `backend/app/services/llm_dispatcher.py` | Smart routing | Has graceful degradation |
| `backend/app/services/model_pinning.py` | Model affinity | Needs UI integration |
| `backend/app/services/settings_service.py` | Settings persistence | Needs schema update |
| `backend/app/api/v1/settings_routes.py` | Settings API | Works |
| `frontend-v2/src/pages/Settings.jsx` | Settings UI | Needs new section |

### 7.2 Documentation (Active Guides)

| File | Purpose | Notes |
|------|---------|-------|
| `docs/NETWORK_TWO_PC_SETUP.md` | Network config | **Current** - accurate |
| `docs/AI_TWO_PC_CODING_GUIDE.md` | AI dev rules | **Current** - accurate |
| `README.md` | Project overview | Mentions dual-PC but vague |

### 7.3 Stale or Incomplete

| File | Issue |
|------|-------|
| None identified | Existing dual-PC infrastructure is recent and accurate |

---

## 8. Proposed Implementation Plan

### Phase 1: Settings Schema (1-2 hours)
1. Add `machine` category to `settings_service.py` DEFAULTS
2. Add `deployment` category
3. Update `device` category with deprecation notices
4. Add validation helpers
5. Test schema loading

### Phase 2: Machine Identity Service (2-3 hours)
1. Create `machine_identity.py`
2. Implement detection logic (saved > env > hostname > fallback)
3. Add peer online check
4. Write unit tests
5. Wire into startup in `main.py`

### Phase 3: UI Updates (2-3 hours)
1. Add "Machine & Deployment" section to `Settings.jsx`
2. Add machine selector dropdown
3. Add peer configuration fields
4. Add peer status indicator
5. Add fallback mode warning badge
6. Test UI flow

### Phase 4: Startup Logic (1-2 hours)
1. Update `main.py` lifespan to call machine identity
2. Add prominent deployment mode logs
3. Add service startup guards based on role
4. Test both single and dual-PC startup

### Phase 5: Service Affinity (2-3 hours)
1. Update `node_discovery.py` to use machine identity
2. Update services to check role before starting GPU jobs
3. Add training service guard
4. Test workload routing

### Phase 6: Testing & Documentation (2-3 hours)
1. Test on ESPENMAIN as PC1
2. Test on ProfitTrader as PC2
3. Test peer offline fallback
4. Test hostname auto-detect
5. Update README.md with deployment mode docs

**Total Estimate:** 10-16 hours of development time

---

## 9. Test Plan

### Test Scenario 1: ESPENMAIN as PC1
- [x] Set `machine.machineRole = "auto"`
- [ ] Start backend on ESPENMAIN
- [ ] Verify logs: "MACHINE: ESPENMAIN (role=pc1)"
- [ ] Verify Settings UI shows "This Machine: ESPENMAIN (PC1/Primary)"
- [ ] Verify fast Ollama models loaded

### Test Scenario 2: ProfitTrader as PC2
- [ ] Set `machine.machineRole = "auto"`
- [ ] Start backend on ProfitTrader
- [ ] Verify logs: "MACHINE: ProfitTrader (role=pc2)"
- [ ] Verify Settings UI shows "This Machine: ProfitTrader (PC2/Secondary)"
- [ ] Verify heavy Ollama models loaded

### Test Scenario 3: Dual-PC Mode (Peer Online)
- [ ] Set `deployment.peerMachineHost = "192.168.1.116"` on PC1
- [ ] Start both backends
- [ ] Verify logs: "DEPLOYMENT MODE: DUAL_PC | PEER: 192.168.1.116 (ONLINE)"
- [ ] Verify Settings UI: Peer Status = ● Online
- [ ] Verify LLM requests route to both nodes

### Test Scenario 4: Dual-PC Fallback (Peer Offline)
- [ ] Stop PC2 backend
- [ ] Wait for heartbeat timeout (3 intervals × 3s = 9s)
- [ ] Verify logs: "FALLBACK MODE ACTIVE"
- [ ] Verify Settings UI: amber badge "⚠ FALLBACK MODE"
- [ ] Verify all LLM requests route to PC1 only
- [ ] Verify model degradation (deepseek → llama3.2)

### Test Scenario 5: Saved Settings Override
- [ ] Save `machine.machineRole = "pc2"` in DuckDB
- [ ] Start backend on ESPENMAIN (hostname would suggest pc1)
- [ ] Verify logs: "using saved role=pc2"
- [ ] Verify Settings UI reflects PC2 role

### Test Scenario 6: Environment Override
- [ ] Set `MACHINE_ROLE=pc1` in .env
- [ ] Unset saved settings
- [ ] Start backend
- [ ] Verify logs: "using env MACHINE_ROLE=pc1"

### Test Scenario 7: Hostname Auto-Detect
- [ ] Remove saved settings and env var
- [ ] Start on unknown hostname
- [ ] Verify logs: "unknown hostname → role=standalone"
- [ ] Verify Settings UI: "Standalone" mode

### Test Scenario 8: GPU On/Off Behavior
- [ ] Set `machine.gpuEnabled = false`
- [ ] Start backend
- [ ] Verify GPUTelemetryDaemon does not start
- [ ] Verify LLMDispatcher doesn't use GPU routing

---

## 10. Deliverables Checklist

- [ ] This audit report (`docs/MACHINE_AWARENESS_AUDIT.md`)
- [ ] Architecture summary (this document, Section 2)
- [ ] Stale vs active files (Section 7)
- [ ] Settings schema design (Section 4)
- [ ] UI mockup & changes (Section 5)
- [ ] Startup logic proposal (Section 6)
- [ ] Implementation plan (Section 8)
- [ ] Test plan (Section 9)
- [ ] Code changes:
  - [ ] `backend/app/services/machine_identity.py` (new)
  - [ ] `backend/app/services/settings_service.py` (schema update)
  - [ ] `backend/app/main.py` (startup logic)
  - [ ] `frontend-v2/src/pages/Settings.jsx` (UI section)
  - [ ] `backend/app/services/node_discovery.py` (role integration)
  - [ ] `backend/app/services/gpu_telemetry.py` (role awareness)

---

## Appendices

### Appendix A: Key Environment Variables

**Existing (from config.py):**
```bash
CLUSTER_PC2_HOST=192.168.1.116
CLUSTER_HEALTH_INTERVAL=60
REDIS_URL=redis://192.168.1.105:6379/0
OLLAMA_PC2_URL=http://192.168.1.116:11434
MODEL_PIN_PC1=llama3.2,mistral:7b
MODEL_PIN_PC2=deepseek-r1:14b,mixtral:8x7b
GPU_TELEMETRY_ENABLED=true
GPU_TELEMETRY_INTERVAL=3.0
LLM_DISPATCHER_ENABLED=true
LLM_DISPATCHER_HEARTBEAT_TIMEOUT=3
LLM_DISPATCHER_GPU_UTIL_THRESHOLD=85.0
LLM_DISPATCHER_FALLBACK_MODEL=llama3.2
```

**Proposed (new):**
```bash
# Machine Identity
MACHINE_ID=ESPENMAIN
MACHINE_ROLE=auto  # pc1 | pc2 | standalone | auto
MACHINE_NAME="Primary Intelligence Node"
AUTO_DETECT_HOSTNAME=true
GPU_ENABLED=true
GPU_DEVICE_INDEX=0

# Deployment
DEPLOYMENT_MODE=auto  # single_pc | dual_pc | auto
PEER_MACHINE_HOST=192.168.1.116
PEER_REQUIRED_FOR_STARTUP=false
PEER_REQUIRED_FOR_EXECUTION=false
ALLOW_SINGLE_PC_FALLBACK=true
```

### Appendix B: References

- **README.md** - Lines 334-337: "Hardware (Dual-PC Setup)"
- **NETWORK_TWO_PC_SETUP.md** - Complete network topology
- **AI_TWO_PC_CODING_GUIDE.md** - PC1/PC2 role definitions
- **config.py** - Lines 214-242: Cluster + GPU settings
- **node_discovery.py** - Lines 31-348: PC2 discovery logic
- **gpu_telemetry.py** - Lines 1-350: GPU monitoring daemon
- **llm_dispatcher.py** - Lines 1-455: Telemetry-aware routing
- **model_pinning.py** - Model → node affinity mapping
- **settings_service.py** - Lines 23-292: Current settings schema

---

**End of Audit Report**
