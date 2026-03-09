# Machine Awareness Migration Guide

**Elite Trading System - Machine Identity & Deployment Architecture**

**Migration Date:** 2026-03-08
**Branch:** `claude/audit-and-implement-machine-awareness`
**Version:** v0.5.0+
**Status:** Implementation Complete, Ready for Deployment

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Migration Overview](#migration-overview)
3. [Before/After Comparison](#beforeafter-comparison)
4. [Prerequisites](#prerequisites)
5. [Settings Schema Migration](#settings-schema-migration)
6. [Deployment Procedures](#deployment-procedures)
7. [Validation & Testing](#validation--testing)
8. [Service Affinity Matrix](#service-affinity-matrix)
9. [Fallback Behavior](#fallback-behavior)
10. [Monitoring & Verification](#monitoring--verification)
11. [Troubleshooting](#troubleshooting)
12. [Rollback Procedures](#rollback-procedures)
13. [Appendix](#appendix)

---

## Executive Summary

This guide documents the migration from an **implicit dual-PC setup** to an **explicit machine-awareness architecture** in the Elite Trading System. The new architecture provides:

- **Deterministic machine role detection** (PC1 vs PC2 vs Standalone)
- **Explicit deployment mode management** (single-PC vs dual-PC)
- **Automatic peer discovery and health monitoring**
- **Service affinity routing** (GPU training → PC2, execution → PC1)
- **Graceful fallback** when peer machines are unavailable
- **Comprehensive machine identity API** for UI/dashboard integration

### What Changed

| Aspect | Before (Implicit) | After (Explicit) |
|--------|------------------|------------------|
| **Role Detection** | Hardcoded assumptions | Priority cascade: settings → env → hostname → fallback |
| **Settings Schema** | Single `device` category | Separate `machine` and `deployment` categories |
| **Peer Awareness** | None | Active health checks via HTTP |
| **Startup Logging** | Generic | Prominent deployment mode banner with role/peer status |
| **API Visibility** | `/device` endpoint only | New `/machine` endpoint with full status |
| **Service Routing** | Manual | Automatic based on machine role |
| **Fallback Mode** | Undefined | Explicit detection and warning |

### Migration Risk Level

**🟢 LOW RISK** — Backward compatible with existing configurations. No database schema changes required.

---

## Migration Overview

### Timeline

- **Phase 1:** Settings schema addition (✅ Complete - Commit c234c4e)
- **Phase 2:** Machine identity service implementation (✅ Complete - Commit c234c4e)
- **Phase 3:** Startup integration and API endpoints (✅ Complete - Commit 2ad021b)
- **Phase 4:** Deployment and validation (📋 This Guide)
- **Phase 5:** UI integration (🔜 Future Work)
- **Phase 6:** Device category deprecation (🔜 Future Work - 6 months)

### Commits Delivered

```
c234c4e - feat: add machine identity service and deployment settings schema
2ad021b - feat: wire machine identity into startup and API
```

### Files Modified/Added

**Core Implementation:**
- `backend/app/services/machine_identity.py` (NEW - 327 lines)
- `backend/app/services/settings_service.py` (MODIFIED - lines 261-305)
- `backend/app/main.py` (MODIFIED - lines 924-952)
- `backend/app/api/v1/system.py` (MODIFIED - lines 204-297)

**Documentation:**
- `docs/MACHINE_AWARENESS_AUDIT.md` (REFERENCE - 830 lines)
- `docs/MACHINE_AWARENESS_MIGRATION_GUIDE.md` (THIS DOCUMENT)

---

## Before/After Comparison

### Before: Implicit Dual-PC Setup

```python
# Old approach (hardcoded assumptions)
if os.path.exists("C:\\Users\\Espen"):
    # Must be ESPENMAIN
    run_api_server = True
    run_training = False
elif os.path.exists("C:\\Users\\ProfitTrader"):
    # Must be ProfitTrader
    run_api_server = False
    run_training = True
```

**Problems:**
- ❌ No explicit role tracking
- ❌ Path-based detection fragile
- ❌ No peer awareness
- ❌ No fallback handling
- ❌ Hard to test or debug
- ❌ Unclear what runs where

### After: Explicit Machine Awareness

```python
# New approach (deterministic detection)
from app.services.machine_identity import get_machine_identity

identity = get_machine_identity()
logger.info(f"Machine: {identity.machine_role}")
logger.info(f"Deployment: {identity.deployment_mode}")
logger.info(f"Peer online: {await identity.check_peer_online()}")

if identity.should_run_service("training"):
    # Service affinity logic handles routing
    scheduler.start_training_jobs()
```

**Benefits:**
- ✅ Explicit role in settings/logs/API
- ✅ Multiple detection methods with priority
- ✅ Active peer health monitoring
- ✅ Graceful fallback mode
- ✅ Easy to test and verify
- ✅ Service affinity routing

---

## Prerequisites

### Required Knowledge

- Basic understanding of the Elite Trading System architecture
- Familiarity with FastAPI application structure
- Access to both PC1 (ESPENMAIN) and PC2 (ProfitTrader) if dual-PC mode
- Network connectivity between machines (if dual-PC)

### System Requirements

**PC1 (ESPENMAIN) - Primary Intelligence Node:**
- Hostname: `ESPENMAIN`
- LAN IP: `192.168.1.105`
- Role: API server, frontend host, DuckDB, execution
- Python 3.11+
- Port 8000 accessible from PC2

**PC2 (ProfitTrader) - Secondary Compute Node:**
- Hostname: `ProfitTrader`
- LAN IP: `192.168.1.116`
- Role: GPU training, Brain gRPC, heavy ML workloads
- Python 3.11+
- Port 8000 accessible from PC1
- NVIDIA GPU (optional but recommended)

**Single-PC Deployments:**
- Any hostname
- Automatic standalone mode detection
- All services run locally

### Network Requirements (Dual-PC Only)

```bash
# From PC1 (ESPENMAIN):
curl http://192.168.1.116:8000/health

# From PC2 (ProfitTrader):
curl http://192.168.1.105:8000/health

# Both should return 200 OK
```

---

## Settings Schema Migration

### New Settings Categories

#### 1. Machine Category (`machine.*`)

Replaces most fields from the old `device` category:

```json
{
  "machine": {
    "machineId": "",
    "machineName": "",
    "machineRole": "auto",
    "isPrimaryNode": null,
    "autoDetectHostname": true,
    "hostnameOverride": "",
    "gpuEnabled": true,
    "gpuDeviceIndex": 0,
    "gpuRole": "mixed",
    "gpuVramHeadroom": 512
  }
}
```

**Field Descriptions:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `machineId` | string | `""` | Machine identifier (e.g., "ESPENMAIN", "ProfitTrader") |
| `machineName` | string | `""` | Friendly display name |
| `machineRole` | string | `"auto"` | Role: `"pc1"`, `"pc2"`, `"standalone"`, or `"auto"` |
| `isPrimaryNode` | bool/null | `null` | Explicit primary flag or null for auto-detect |
| `autoDetectHostname` | bool | `true` | Enable hostname-based detection |
| `hostnameOverride` | string | `""` | Force specific hostname match |
| `gpuEnabled` | bool | `true` | Enable GPU usage |
| `gpuDeviceIndex` | int | `0` | CUDA device index |
| `gpuRole` | string | `"mixed"` | GPU role: `"inference"`, `"training"`, or `"mixed"` |
| `gpuVramHeadroom` | int | `512` | VRAM buffer in MB |

#### 2. Deployment Category (`deployment.*`)

New category for multi-machine coordination:

```json
{
  "deployment": {
    "deploymentMode": "auto",
    "distributedModeEnabled": false,
    "peerMachineHost": "",
    "peerMachineRole": "",
    "peerRequiredForStartup": false,
    "peerRequiredForExecution": false,
    "allowSinglePcFallback": true,
    "fallbackModeActive": false,
    "peerOnline": false,
    "serviceAffinityMode": "auto",
    "runTrainingServices": "auto",
    "runInferenceServices": "auto",
    "runExecutionServices": "auto",
    "runIntelligenceServices": "auto"
  }
}
```

**Field Descriptions:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `deploymentMode` | string | `"auto"` | Deployment: `"single_pc"`, `"dual_pc"`, or `"auto"` |
| `distributedModeEnabled` | bool | `false` | Explicit distributed toggle |
| `peerMachineHost` | string | `""` | Peer IP/hostname (e.g., "192.168.1.116") |
| `peerMachineRole` | string | `""` | Expected peer role: `"pc1"`, `"pc2"`, or `""` |
| `peerRequiredForStartup` | bool | `false` | Block startup if peer offline |
| `peerRequiredForExecution` | bool | `false` | Block trading if peer offline |
| `allowSinglePcFallback` | bool | `true` | Enable fallback to single-PC mode |
| `fallbackModeActive` | bool | `false` | **READ-ONLY:** Runtime fallback state |
| `peerOnline` | bool | `false` | **READ-ONLY:** Peer health status |
| `serviceAffinityMode` | string | `"auto"` | Service routing: `"auto"` or `"manual"` |
| `runTrainingServices` | string | `"auto"` | Training: `"yes"`, `"no"`, or `"auto"` |
| `runInferenceServices` | string | `"auto"` | Inference: `"yes"`, `"no"`, or `"auto"` |
| `runExecutionServices` | string | `"auto"` | Execution: `"yes"`, `"no"`, or `"auto"` |
| `runIntelligenceServices` | string | `"auto"` | Intelligence: `"yes"`, `"no"`, or `"auto"` |

#### 3. Device Category (`device.*`) - DEPRECATED

The old `device` category is **deprecated** but maintained for backward compatibility:

```python
# Migration notes in settings_service.py:296-305
"device": {
    "device_id": "",           # → machine.machineId
    "device_name": "",         # → machine.machineName
    "is_primary": None,        # → machine.isPrimaryNode
    "gpu_enabled": True,       # → machine.gpuEnabled
    "gpu_device_index": 0,     # → machine.gpuDeviceIndex
    # ... other deprecated fields
}
```

**Migration Path:**
1. **Months 0-3:** Both categories coexist (current state)
2. **Month 3:** UI shows migration banner for `device.*` users
3. **Month 6:** Auto-migration script moves `device.*` → `machine.*`
4. **Month 9:** `device` category removed from schema

---

### Manual Settings Migration

If you have customized `device.*` settings, manually migrate them:

#### Example: Manual Override Migration

**Before (device category):**
```json
{
  "device": {
    "device_id": "ESPENMAIN",
    "is_primary": true,
    "gpu_enabled": false
  }
}
```

**After (machine + deployment categories):**
```json
{
  "machine": {
    "machineId": "ESPENMAIN",
    "machineRole": "pc1",
    "isPrimaryNode": true,
    "gpuEnabled": false
  },
  "deployment": {
    "deploymentMode": "dual_pc",
    "peerMachineHost": "192.168.1.116",
    "peerMachineRole": "pc2"
  }
}
```

**Migration via API:**
```bash
# Update machine settings
curl -X PUT http://localhost:8000/api/v1/settings/machine \
  -H "Content-Type: application/json" \
  -d '{
    "machineId": "ESPENMAIN",
    "machineRole": "pc1",
    "isPrimaryNode": true,
    "gpuEnabled": false
  }'

# Update deployment settings
curl -X PUT http://localhost:8000/api/v1/settings/deployment \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentMode": "dual_pc",
    "peerMachineHost": "192.168.1.116",
    "peerMachineRole": "pc2"
  }'
```

---

## Deployment Procedures

### Scenario 1: Dual-PC Deployment (Recommended)

This is the standard production configuration for the Elite Trading System.

#### Step 1: Deploy to PC1 (ESPENMAIN)

```bash
# On PC1 (ESPENMAIN - 192.168.1.105)
cd C:\Users\Espen\elite-trading-system
git checkout claude/audit-and-implement-machine-awareness
git pull origin claude/audit-and-implement-machine-awareness

# Start the system
.\start-embodier.ps1
# OR
python backend/start_server.py
```

**Expected Startup Log (PC1):**
```
================================================================================
Elite Trading System v0.5.0 - Initializing
================================================================================
DEPLOYMENT MODE: DUAL_PC
MACHINE: ESPENMAIN (role=pc1)
DETECTION METHOD: hostname_detection
PEER: 192.168.1.116 (OFFLINE - waiting for PC2)
⚠ FALLBACK MODE ACTIVE - Running in single-PC mode (peer unavailable)
  Services will run locally - some functionality may be degraded
GPU: DISABLED (no suitable device or disabled in settings)
================================================================================
```

#### Step 2: Deploy to PC2 (ProfitTrader)

```bash
# On PC2 (ProfitTrader - 192.168.1.116)
cd C:\Users\ProfitTrader\elite-trading-system
git checkout claude/audit-and-implement-machine-awareness
git pull origin claude/audit-and-implement-machine-awareness

# Start the system
.\start-embodier.ps1
# OR
python backend/start_server.py
```

**Expected Startup Log (PC2):**
```
================================================================================
Elite Trading System v0.5.0 - Initializing
================================================================================
DEPLOYMENT MODE: DUAL_PC
MACHINE: ProfitTrader (role=pc2)
DETECTION METHOD: hostname_detection
PEER: 192.168.1.105 (ONLINE)
GPU: ENABLED (device 0)
================================================================================
```

#### Step 3: Verify Dual-PC Mode

After both machines are running, **restart PC1** to exit fallback mode:

```bash
# On PC1: Ctrl+C, then restart
python backend/start_server.py
```

**Expected Startup Log (PC1 - Second Start):**
```
================================================================================
Elite Trading System v0.5.0 - Initializing
================================================================================
DEPLOYMENT MODE: DUAL_PC
MACHINE: ESPENMAIN (role=pc1)
DETECTION METHOD: hostname_detection
PEER: 192.168.1.116 (ONLINE)
GPU: DISABLED
================================================================================
```

✅ **No fallback mode warning** = Dual-PC mode is active!

---

### Scenario 2: Single-PC Deployment (Standalone)

For development, testing, or single-machine production:

```bash
# On any machine
cd /path/to/elite-trading-system
git checkout claude/audit-and-implement-machine-awareness
git pull

python backend/start_server.py
```

**Expected Startup Log (Unknown Hostname):**
```
================================================================================
Elite Trading System v0.5.0 - Initializing
================================================================================
DEPLOYMENT MODE: SINGLE_PC
MACHINE: my-laptop (role=standalone)
DETECTION METHOD: safe_fallback (hostname not recognized)
GPU: ENABLED (device 0)
================================================================================
```

**No peer warnings** = Standalone mode is correct!

---

### Scenario 3: Manual Role Override (Environment Variable)

Force a specific role regardless of hostname:

```bash
# On PC1 - Force PC1 role
set MACHINE_ROLE=pc1
python backend/start_server.py

# On PC2 - Force PC2 role
set MACHINE_ROLE=pc2
python backend/start_server.py
```

**Expected Startup Log:**
```
DETECTION METHOD: environment_variable
MACHINE: my-custom-hostname (role=pc1)
```

**Use Cases:**
- Testing dual-PC behavior on single machine
- Cloud deployment with custom hostnames
- Docker containers with generic hostnames

---

### Scenario 4: Manual Role Override (Saved Settings)

**Highest priority** - persists across restarts:

```bash
# Via API
curl -X PUT http://localhost:8000/api/v1/settings/machine \
  -H "Content-Type: application/json" \
  -d '{"machineRole": "pc1"}'

# Via Python
from app.services.settings_service import get_settings_service
settings = get_settings_service()
await settings.update_setting("machine", "machineRole", "pc1")
```

**Expected Startup Log:**
```
DETECTION METHOD: saved_settings
MACHINE: my-custom-hostname (role=pc1)
```

**Use Cases:**
- Permanent role assignment
- Renamed hostnames
- Cloud/VM deployments

---

### Scenario 5: Peer Configuration

Configure PC1 to know about PC2:

```bash
# On PC1 - Set peer host
curl -X PUT http://localhost:8000/api/v1/settings/deployment \
  -H "Content-Type: application/json" \
  -d '{
    "peerMachineHost": "192.168.1.116",
    "peerMachineRole": "pc2",
    "deploymentMode": "dual_pc"
  }'

# Restart to apply
# Machine will now check http://192.168.1.116:8000/health
```

**Automatic Peer Discovery (Future):**
- mDNS/Bonjour service discovery
- Redis pub/sub announcements
- Zero-config networking

---

## Validation & Testing

### 8-Scenario Test Plan

Reference: `docs/MACHINE_AWARENESS_AUDIT.md` Section 8

#### Test 1: ESPENMAIN Auto-Detection (PC1)

**Setup:**
- Machine hostname: `ESPENMAIN`
- No saved settings, no env override

**Expected Outcome:**
```
MACHINE: ESPENMAIN (role=pc1)
DETECTION METHOD: hostname_detection
```

**Validation:**
```bash
curl http://localhost:8000/api/v1/system/machine | jq
# Should show: "machine_role": "pc1"
```

✅ **Pass:** Role is `pc1`
❌ **Fail:** Role is not `pc1` or detection method is wrong

---

#### Test 2: ProfitTrader Auto-Detection (PC2)

**Setup:**
- Machine hostname: `ProfitTrader`
- No saved settings, no env override

**Expected Outcome:**
```
MACHINE: ProfitTrader (role=pc2)
DETECTION METHOD: hostname_detection
```

**Validation:**
```bash
curl http://localhost:8000/api/v1/system/machine | jq
# Should show: "machine_role": "pc2"
```

✅ **Pass:** Role is `pc2`
❌ **Fail:** Role is not `pc2` or detection method is wrong

---

#### Test 3: Dual-PC Mode with Peer Online

**Setup:**
- PC1 running at `192.168.1.105`
- PC2 running at `192.168.1.116`
- PC1 configured with `peerMachineHost: "192.168.1.116"`

**Expected Outcome (PC1):**
```
DEPLOYMENT MODE: DUAL_PC
PEER: 192.168.1.116 (ONLINE)
(No fallback mode warning)
```

**Validation:**
```bash
curl http://192.168.1.105:8000/api/v1/system/machine | jq '.peer_online'
# Should return: true
```

✅ **Pass:** Peer online, no fallback mode
❌ **Fail:** Peer shown as offline or fallback mode active

---

#### Test 4: Dual-PC Mode with Peer Offline (Fallback)

**Setup:**
- PC1 running at `192.168.1.105`
- PC2 is **stopped**
- PC1 configured with `peerMachineHost: "192.168.1.116"`

**Expected Outcome (PC1):**
```
DEPLOYMENT MODE: DUAL_PC
PEER: 192.168.1.116 (OFFLINE)
⚠ FALLBACK MODE ACTIVE - Running in single-PC mode (peer unavailable)
```

**Validation:**
```bash
curl http://192.168.1.105:8000/api/v1/system/machine | jq '.fallback_mode'
# Should return: true
```

✅ **Pass:** Fallback mode active, warning shown
❌ **Fail:** No fallback warning or peer shown as online

---

#### Test 5: Saved Settings Override

**Setup:**
```bash
curl -X PUT http://localhost:8000/api/v1/settings/machine \
  -H "Content-Type: application/json" \
  -d '{"machineRole": "pc1"}'
```
- Restart server

**Expected Outcome:**
```
MACHINE: some-hostname (role=pc1)
DETECTION METHOD: saved_settings
```

**Validation:**
```bash
curl http://localhost:8000/api/v1/system/machine | jq '.detection_method'
# Should return: "saved_settings"
```

✅ **Pass:** Detection method is `saved_settings`
❌ **Fail:** Falls back to hostname or environment variable

---

#### Test 6: Environment Variable Override

**Setup:**
```bash
set MACHINE_ROLE=pc2
python backend/start_server.py
```

**Expected Outcome:**
```
MACHINE: some-hostname (role=pc2)
DETECTION METHOD: environment_variable
```

**Validation:**
```bash
curl http://localhost:8000/api/v1/system/machine | jq '.detection_method'
# Should return: "environment_variable"
```

✅ **Pass:** Detection method is `environment_variable`
❌ **Fail:** Falls back to hostname or safe fallback

---

#### Test 7: Unknown Hostname Fallback

**Setup:**
- Machine hostname: `my-laptop` (not ESPENMAIN or ProfitTrader)
- No saved settings, no env override

**Expected Outcome:**
```
DEPLOYMENT MODE: SINGLE_PC
MACHINE: my-laptop (role=standalone)
DETECTION METHOD: safe_fallback
```

**Validation:**
```bash
curl http://localhost:8000/api/v1/system/machine | jq '.machine_role'
# Should return: "standalone"
```

✅ **Pass:** Role is `standalone`, deployment mode is `single_pc`
❌ **Fail:** Wrong role or deployment mode

---

#### Test 8: GPU Enabled/Disabled

**Setup A (GPU Enabled):**
```bash
curl -X PUT http://localhost:8000/api/v1/settings/machine \
  -H "Content-Type: application/json" \
  -d '{"gpuEnabled": true}'
```

**Expected Outcome A:**
```
GPU: ENABLED (device 0)
```

**Setup B (GPU Disabled):**
```bash
curl -X PUT http://localhost:8000/api/v1/settings/machine \
  -H "Content-Type: application/json" \
  -d '{"gpuEnabled": false}'
```

**Expected Outcome B:**
```
GPU: DISABLED
```

**Validation:**
```bash
curl http://localhost:8000/api/v1/system/machine | jq '.gpu_enabled'
# Should match setting (true or false)
```

✅ **Pass:** GPU status matches setting
❌ **Fail:** GPU status doesn't match setting

---

### Automated Test Suite (Future)

```bash
# Run machine identity tests
cd backend
python -m pytest tests/test_machine_identity.py -v

# Expected: All tests pass
# tests/test_machine_identity.py::test_hostname_detection PASSED
# tests/test_machine_identity.py::test_env_override PASSED
# tests/test_machine_identity.py::test_saved_settings_override PASSED
# tests/test_machine_identity.py::test_peer_health_check PASSED
# tests/test_machine_identity.py::test_fallback_mode PASSED
# tests/test_machine_identity.py::test_service_affinity PASSED
```

**Note:** Test file not yet created in this migration. Create as part of Phase 5.

---

## Service Affinity Matrix

How services are distributed in different deployment modes:

### Dual-PC Mode (Peer Online)

| Service Category | PC1 (ESPENMAIN) | PC2 (ProfitTrader) | Auto Logic |
|------------------|-----------------|-------------------|------------|
| **Training Jobs** | ❌ No | ✅ Yes | `is_pc2()` |
| **Inference** | ✅ Yes | ✅ Yes | Both machines |
| **Execution/Trading** | ✅ Yes | ❌ No | `is_pc1()` (has DuckDB) |
| **Intelligence/Orchestration** | ✅ Yes | ❌ No | `is_pc1()` (primary node) |
| **Brain gRPC Service** | ❌ No | ✅ Yes | `is_pc2()` (GPU compute) |
| **FastAPI Server** | ✅ Yes | ✅ Yes | Both (different endpoints) |
| **Frontend React App** | ✅ Yes | ❌ No | `is_pc1()` |

**Service Routing Code:**
```python
from app.services.machine_identity import get_machine_identity

identity = get_machine_identity()

if identity.should_run_service("training"):
    # Only PC2 runs training in dual-PC mode
    scheduler.start_training_jobs()

if identity.should_run_service("execution"):
    # Only PC1 runs execution in dual-PC mode
    order_executor.enable()
```

### Fallback Mode (Peer Offline)

| Service Category | PC1 (ESPENMAIN) | Auto Logic |
|------------------|-----------------|------------|
| **Training Jobs** | ✅ Yes | Fallback to local |
| **Inference** | ✅ Yes | Already local |
| **Execution/Trading** | ✅ Yes | Already local |
| **Intelligence/Orchestration** | ✅ Yes | Already local |
| **Brain gRPC Service** | ✅ Yes | Fallback to local (degraded) |
| **FastAPI Server** | ✅ Yes | Already local |
| **Frontend React App** | ✅ Yes | Already local |

**Warning Banner:**
```
⚠ FALLBACK MODE ACTIVE - Running in single-PC mode (peer unavailable)
  Services will run locally - some functionality may be degraded
```

### Single-PC Mode (Standalone)

| Service Category | Local Machine | Auto Logic |
|------------------|---------------|------------|
| **All Services** | ✅ Yes | `is_standalone()` |

No warnings, all services run normally on single machine.

---

## Fallback Behavior

### Fallback Triggers

Fallback mode activates when **all** conditions are met:

1. `deployment.deploymentMode == "dual_pc"` (expecting peer)
2. `deployment.peerMachineHost` is configured (e.g., "192.168.1.116")
3. Peer health check fails (HTTP GET to `http://{peer}:8000/health` times out or returns non-200)

### Fallback Actions

When fallback mode activates:

1. **Startup Banner:** ⚠ warning displayed prominently
2. **Service Routing:** All services run locally (ignore affinity rules)
3. **API Status:** `/api/v1/system/machine` shows `"fallback_mode": true`
4. **Runtime State:** `deployment.fallbackModeActive` set to `true` (read-only)
5. **Logging:** INFO-level log every startup, WARNING if blocking operations attempted

### Fallback Recovery

Fallback mode **does NOT auto-recover** during runtime. To exit fallback:

1. Ensure peer machine is running and healthy
2. **Restart the primary machine** (PC1)
3. Peer health check succeeds → Fallback mode exits

**Future Enhancement:** Background health checks with auto-recovery (Phase 6)

### Fallback vs Single-PC Mode

| Aspect | Fallback Mode | Single-PC Mode |
|--------|---------------|----------------|
| **Trigger** | Peer configured but offline | No peer configured |
| **Warning** | ⚠ Banner shown | No warning |
| **Intent** | Temporary degraded state | Normal operation |
| **API Flag** | `fallback_mode: true` | `fallback_mode: false` |
| **Deployment Mode** | `dual_pc` | `single_pc` |

### Blocking Operations (Optional)

If `deployment.peerRequiredForExecution == true`:

```python
# In order_executor.py (example)
identity = get_machine_identity()
if identity.fallback_mode and settings.get("deployment", "peerRequiredForExecution"):
    raise RuntimeError("Cannot execute trades in fallback mode - peer required")
```

**Default:** `peerRequiredForExecution == false` (non-blocking fallback)

---

## Monitoring & Verification

### Health Check Endpoints

#### 1. Machine Identity Status

```bash
curl http://localhost:8000/api/v1/system/machine
```

**Response:**
```json
{
  "machine_id": "ESPENMAIN",
  "machine_name": "ESPENMAIN (Primary Intelligence Node)",
  "machine_role": "pc1",
  "deployment_mode": "dual_pc",
  "peer_host": "192.168.1.116",
  "peer_online": true,
  "fallback_mode": false,
  "gpu_enabled": false,
  "gpu_device_index": 0,
  "detection_method": "hostname_detection",
  "system_info": {
    "hostname": "ESPENMAIN",
    "platform": "windows",
    "arch": "AMD64",
    "python_version": "3.11.7",
    "cpu_count": 16
  }
}
```

#### 2. Settings Categories

```bash
# Machine settings
curl http://localhost:8000/api/v1/settings/machine

# Deployment settings
curl http://localhost:8000/api/v1/settings/deployment

# Legacy device settings (deprecated)
curl http://localhost:8000/api/v1/settings/device
```

#### 3. General Health

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-08T23:30:00Z",
  "uptime_seconds": 1234
}
```

### Log File Monitoring

**Startup Logs:**
```bash
# Search for machine identity logs
tail -f backend/logs/app.log | grep "DEPLOYMENT MODE"
tail -f backend/logs/app.log | grep "MACHINE:"
tail -f backend/logs/app.log | grep "FALLBACK MODE"
```

**Expected Patterns:**
```
[INFO] DEPLOYMENT MODE: DUAL_PC
[INFO] MACHINE: ESPENMAIN (role=pc1)
[INFO] DETECTION METHOD: hostname_detection
[INFO] PEER: 192.168.1.116 (ONLINE)
[WARNING] ⚠ FALLBACK MODE ACTIVE - Running in single-PC mode
```

### Dashboard Integration (Future - Phase 5)

New UI section: **Settings → Machine & Deployment**

**Display Elements:**
- 🖥 Machine ID and Role (PC1/PC2/Standalone)
- 🌐 Deployment Mode (Single-PC/Dual-PC)
- 🔗 Peer Status (Online/Offline with live indicator)
- ⚠ Fallback Mode Banner (if active)
- 🎮 GPU Status (Enabled/Disabled with device info)
- 🔧 Detection Method (Saved/Environment/Hostname/Fallback)

**Interactive Elements:**
- Dropdown: Force Machine Role (PC1/PC2/Standalone/Auto)
- Input: Peer Machine Host (IP/hostname)
- Toggle: GPU Enabled/Disabled
- Button: "Test Peer Connection"
- Button: "Save and Restart"

---

## Troubleshooting

### Issue 1: Wrong Machine Role Detected

**Symptom:**
```
MACHINE: ESPENMAIN (role=standalone)  # Should be pc1
DETECTION METHOD: safe_fallback
```

**Cause:** Hostname detection failed (typo or case-sensitivity)

**Solution:**
1. Check actual hostname:
   ```bash
   # Windows
   hostname

   # Linux/Mac
   hostname
   ```

2. Override with environment variable:
   ```bash
   set MACHINE_ROLE=pc1
   python backend/start_server.py
   ```

3. Or save settings permanently:
   ```bash
   curl -X PUT http://localhost:8000/api/v1/settings/machine \
     -d '{"machineRole": "pc1"}'
   ```

---

### Issue 2: Peer Always Shows Offline

**Symptom:**
```
PEER: 192.168.1.116 (OFFLINE)
⚠ FALLBACK MODE ACTIVE
```

**But PC2 is running!**

**Diagnostics:**

1. **Check PC2 is actually running:**
   ```bash
   # From PC1
   curl http://192.168.1.116:8000/health
   ```
   - **Success (200 OK):** Proceed to step 2
   - **Failure (timeout/connection refused):** PC2 not reachable

2. **Check firewall rules:**
   ```bash
   # Windows (on PC2)
   netsh advfirewall firewall add rule name="ETS FastAPI" dir=in action=allow protocol=TCP localport=8000

   # Linux (on PC2)
   sudo ufw allow 8000/tcp
   ```

3. **Check peer host setting:**
   ```bash
   curl http://localhost:8000/api/v1/settings/deployment | jq '.peerMachineHost'
   # Should return: "192.168.1.116"
   ```

   If wrong, update:
   ```bash
   curl -X PUT http://localhost:8000/api/v1/settings/deployment \
     -d '{"peerMachineHost": "192.168.1.116"}'
   ```

4. **Check health endpoint timeout:**
   - Default timeout: 5 seconds
   - If network is slow, peer may appear offline
   - **Future:** Make timeout configurable

5. **Restart PC1 after fixing:**
   - Peer detection runs at startup only (no auto-recovery yet)

---

### Issue 3: GPU Not Detected

**Symptom:**
```
GPU: DISABLED (no suitable device or disabled in settings)
```

**But GPU is installed!**

**Diagnostics:**

1. **Check GPU setting:**
   ```bash
   curl http://localhost:8000/api/v1/settings/machine | jq '.gpuEnabled'
   # Should return: true
   ```

   If false, enable:
   ```bash
   curl -X PUT http://localhost:8000/api/v1/settings/machine \
     -d '{"gpuEnabled": true}'
   ```

2. **Check CUDA installation:**
   ```bash
   nvidia-smi
   # Should show GPU info
   ```

3. **Check PyTorch CUDA:**
   ```python
   import torch
   print(torch.cuda.is_available())  # Should be True
   print(torch.cuda.device_count())  # Should be > 0
   ```

4. **Check device index:**
   ```bash
   curl http://localhost:8000/api/v1/settings/machine | jq '.gpuDeviceIndex'
   # Should be 0 for first GPU, 1 for second, etc.
   ```

---

### Issue 4: Services Running on Wrong Machine

**Symptom:**
- Training jobs running on PC1 (should be PC2)
- Execution blocked on PC2 (should be PC1)

**Diagnostics:**

1. **Check service affinity mode:**
   ```bash
   curl http://localhost:8000/api/v1/settings/deployment | jq '.serviceAffinityMode'
   # Should return: "auto"
   ```

2. **Check manual service overrides:**
   ```bash
   curl http://localhost:8000/api/v1/settings/deployment | jq '.runTrainingServices'
   # Should return: "auto" (not "yes" or "no")
   ```

3. **Verify machine role:**
   ```bash
   curl http://localhost:8000/api/v1/system/machine | jq '.machine_role'
   # PC1 should return: "pc1"
   # PC2 should return: "pc2"
   ```

4. **Check fallback mode:**
   ```bash
   curl http://localhost:8000/api/v1/system/machine | jq '.fallback_mode'
   # If true, all services run locally (expected behavior)
   ```

**Solution:**
- Fix machine role detection (see Issue 1)
- Ensure peer is online to exit fallback mode
- Reset service affinity to auto:
  ```bash
  curl -X PUT http://localhost:8000/api/v1/settings/deployment \
    -d '{
      "serviceAffinityMode": "auto",
      "runTrainingServices": "auto",
      "runInferenceServices": "auto",
      "runExecutionServices": "auto",
      "runIntelligenceServices": "auto"
    }'
  ```

---

### Issue 5: Fallback Mode Won't Exit

**Symptom:**
- PC2 is running and healthy
- PC1 still shows fallback mode after restart

**Diagnostics:**

1. **Verify peer is actually reachable from PC1:**
   ```bash
   # On PC1
   curl http://192.168.1.116:8000/health
   # Should return 200 OK
   ```

2. **Check deployment mode:**
   ```bash
   curl http://localhost:8000/api/v1/settings/deployment | jq '.deploymentMode'
   # Should return: "dual_pc" or "auto"
   # If "single_pc", fallback won't activate (no peer expected)
   ```

3. **Check peer host is configured:**
   ```bash
   curl http://localhost:8000/api/v1/settings/deployment | jq '.peerMachineHost'
   # Should return: "192.168.1.116" (not empty)
   ```

4. **Check startup logs for health check result:**
   ```bash
   tail -f backend/logs/app.log | grep "Peer health check"
   # Should show: "Peer health check succeeded" or "Peer health check failed"
   ```

**Solution:**
1. Ensure all diagnostics pass
2. **Fully restart PC1** (Ctrl+C, then start again)
3. If still in fallback, manually force deployment mode:
   ```bash
   curl -X PUT http://localhost:8000/api/v1/settings/deployment \
     -d '{
       "deploymentMode": "dual_pc",
       "peerMachineHost": "192.168.1.116"
     }'
   ```
4. Restart again

---

### Issue 6: Cannot Access /api/v1/system/machine

**Symptom:**
```bash
curl http://localhost:8000/api/v1/system/machine
# 404 Not Found
```

**Cause:** Old branch without machine identity implementation

**Solution:**
```bash
git checkout claude/audit-and-implement-machine-awareness
git pull
python backend/start_server.py
```

**Verify branch:**
```bash
git log --oneline -n 2
# Should show:
# 2ad021b feat: wire machine identity into startup and API
# c234c4e feat: add machine identity service and deployment settings schema
```

---

## Rollback Procedures

### Rollback Strategy

**Risk Level:** 🟢 **LOW** — Backward compatible, no database migrations

### If Issues Occur During Migration

#### Option 1: Rollback Git Branch (Clean Rollback)

```bash
# On both PC1 and PC2
git checkout main  # or previous stable branch
python backend/start_server.py
```

**Impact:**
- ❌ Loses machine awareness features
- ✅ No data loss (settings in DuckDB are forward-compatible)
- ✅ Old `device` category settings still work
- ✅ System operates as before

#### Option 2: Keep Branch, Disable Features (Partial Rollback)

```bash
# Force standalone mode
curl -X PUT http://localhost:8000/api/v1/settings/deployment \
  -d '{"deploymentMode": "single_pc"}'

# Restart
python backend/start_server.py
```

**Impact:**
- ✅ Keeps machine awareness code
- ✅ Disables dual-PC features
- ✅ No peer health checks
- ✅ All services run locally

#### Option 3: Disable Specific Features (Selective Rollback)

```bash
# Disable peer health checks
curl -X PUT http://localhost:8000/api/v1/settings/deployment \
  -d '{"peerMachineHost": ""}'

# Disable service affinity routing
curl -X PUT http://localhost:8000/api/v1/settings/deployment \
  -d '{
    "serviceAffinityMode": "manual",
    "runTrainingServices": "yes",
    "runInferenceServices": "yes",
    "runExecutionServices": "yes"
  }'
```

**Impact:**
- ✅ Machine identity still active
- ✅ Role detection still works
- ❌ Peer awareness disabled
- ❌ Service routing disabled

### Data Preservation During Rollback

**Settings in DuckDB:**
- `machine.*` settings are ignored on old branches
- `deployment.*` settings are ignored on old branches
- Old `device.*` settings still work (unchanged)

**No data loss** — Rolling back is safe!

### Emergency Rollback (Critical Production Issue)

```bash
# Step 1: Stop all services
# On PC1:
Ctrl+C  # or taskkill /F /IM python.exe

# On PC2:
Ctrl+C  # or taskkill /F /IM python.exe

# Step 2: Rollback git on both machines
git checkout main
git pull

# Step 3: Restart from stable branch
python backend/start_server.py
```

**Recovery Time:** < 5 minutes

---

## Appendix

### A. Detection Method Priority Cascade

Detailed priority order for machine role detection:

1. **Saved Settings** (Highest Priority)
   - Source: DuckDB `settings.machine.machineRole`
   - Condition: Value is not `"auto"` and not empty
   - Example: `"pc1"`, `"pc2"`, `"standalone"`
   - Override: Via API or UI

2. **Environment Variable**
   - Source: `MACHINE_ROLE` env var
   - Condition: Variable exists and not empty
   - Example: `set MACHINE_ROLE=pc1`
   - Override: Set before process start

3. **Hostname Detection**
   - Source: `platform.node()` (system hostname)
   - Condition: Hostname matches known pattern
   - Mappings:
     - `"ESPENMAIN"` → `pc1`
     - `"ProfitTrader"` → `pc2`
   - Case-sensitive on Linux/Mac, case-insensitive on Windows

4. **Safe Fallback** (Lowest Priority)
   - Trigger: None of the above match
   - Result: `role=standalone`, `deployment_mode=single_pc`
   - Safe: All services run locally

### B. Peer Health Check Details

**Endpoint:** `http://{peer_host}:8000/health`

**Method:** `GET`

**Timeout:** 5 seconds (hardcoded)

**Retry:** None (single attempt at startup)

**Success Criteria:**
- HTTP status code: 200
- Response time: < 5 seconds

**Failure Triggers:**
- Connection refused (PC2 not running)
- Timeout (network issue or PC2 slow)
- HTTP error (500, 503, etc.)
- Invalid response body

**Background Checks:** Not implemented (future enhancement)

### C. Service Affinity Logic (Code Reference)

From `backend/app/services/machine_identity.py:263-311`:

```python
def should_run_service(self, service_type: str) -> bool:
    """
    Determine if this machine should run a specific service type.

    Args:
        service_type: "training" | "inference" | "execution" | "intelligence"

    Returns:
        True if this machine should run the service
    """
    # Manual override
    if self.service_affinity_mode == "manual":
        setting_key = f"run{service_type.capitalize()}Services"
        value = self.settings.get("deployment", setting_key, "auto")
        if value == "yes":
            return True
        elif value == "no":
            return False

    # Auto mode (default)
    if self.deployment_mode == "single_pc" or self.machine_role == "standalone":
        # Single-PC: run everything locally
        return True

    if self.fallback_mode:
        # Fallback: run everything locally
        return True

    # Dual-PC mode with peer online
    if service_type == "training":
        # Training on PC2 only
        return self.is_pc2()
    elif service_type == "inference":
        # Inference on both
        return True
    elif service_type == "execution":
        # Execution on PC1 only (has DuckDB)
        return self.is_pc1()
    elif service_type == "intelligence":
        # Intelligence on PC1 only
        return self.is_pc1()
    else:
        # Unknown service type: default to True
        return True
```

### D. Hostname Detection Code

From `backend/app/services/machine_identity.py:148-165`:

```python
def _detect_by_hostname(self) -> Optional[str]:
    """
    Detect machine role based on hostname.

    Returns:
        "pc1", "pc2", or None if hostname not recognized
    """
    hostname = platform.node().lower()

    # Known hostname mappings
    if "espenmain" in hostname:
        logger.info(f"Detected ESPENMAIN hostname → role=pc1")
        return "pc1"
    elif "profittrader" in hostname:
        logger.info(f"Detected ProfitTrader hostname → role=pc2")
        return "pc2"
    else:
        logger.debug(f"Hostname '{hostname}' not recognized for role detection")
        return None
```

### E. API Response Schema

**GET /api/v1/system/machine**

```typescript
interface MachineIdentityResponse {
  machine_id: string;           // e.g., "ESPENMAIN"
  machine_name: string;          // e.g., "ESPENMAIN (Primary Intelligence Node)"
  machine_role: string;          // "pc1" | "pc2" | "standalone"
  deployment_mode: string;       // "single_pc" | "dual_pc"
  peer_host: string;             // e.g., "192.168.1.116" or ""
  peer_online: boolean;          // true | false
  fallback_mode: boolean;        // true | false
  gpu_enabled: boolean;          // true | false
  gpu_device_index: number;      // e.g., 0
  detection_method: string;      // "saved_settings" | "environment_variable" | "hostname_detection" | "safe_fallback"
  system_info: {
    hostname: string;            // e.g., "ESPENMAIN"
    platform: string;            // "windows" | "linux" | "darwin"
    arch: string;                // e.g., "AMD64"
    python_version: string;      // e.g., "3.11.7"
    cpu_count: number;           // e.g., 16
  };
}
```

### F. Environment Variables

| Variable | Values | Purpose |
|----------|--------|---------|
| `MACHINE_ROLE` | `pc1`, `pc2`, `standalone` | Override role detection |

**Future Environment Variables (Planned):**
- `DEPLOYMENT_MODE` — Override deployment mode
- `PEER_MACHINE_HOST` — Override peer host
- `GPU_ENABLED` — Override GPU setting
- `GPU_DEVICE_INDEX` — Override GPU device

### G. Settings API Examples

**Read Machine Settings:**
```bash
curl http://localhost:8000/api/v1/settings/machine
```

**Update Machine Role:**
```bash
curl -X PUT http://localhost:8000/api/v1/settings/machine \
  -H "Content-Type: application/json" \
  -d '{"machineRole": "pc1"}'
```

**Update Peer Configuration:**
```bash
curl -X PUT http://localhost:8000/api/v1/settings/deployment \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentMode": "dual_pc",
    "peerMachineHost": "192.168.1.116",
    "peerMachineRole": "pc2"
  }'
```

**Disable GPU:**
```bash
curl -X PUT http://localhost:8000/api/v1/settings/machine \
  -H "Content-Type: application/json" \
  -d '{"gpuEnabled": false}'
```

**Reset to Auto-Detection:**
```bash
curl -X PUT http://localhost:8000/api/v1/settings/machine \
  -H "Content-Type: application/json" \
  -d '{"machineRole": "auto"}'
```

### H. Related Documentation

- **Comprehensive Audit:** `docs/MACHINE_AWARENESS_AUDIT.md`
- **Network Setup:** `docs/NETWORK_TWO_PC_SETUP.md`
- **Coding Guide:** `docs/AI_TWO_PC_CODING_GUIDE.md`
- **Status Document:** `docs/STATUS-AND-TODO-2026-03-07.md`

### I. Glossary

| Term | Definition |
|------|------------|
| **PC1** | Primary Intelligence Node (ESPENMAIN) - Runs API, frontend, DuckDB, execution |
| **PC2** | Secondary Compute Node (ProfitTrader) - Runs GPU training, Brain gRPC, heavy ML |
| **Standalone** | Single-machine mode - All services run on one machine |
| **Dual-PC Mode** | Two-machine deployment with PC1 and PC2 cooperating |
| **Fallback Mode** | Temporary state when peer is offline - All services run locally on PC1 |
| **Peer** | The other machine in a dual-PC deployment |
| **Service Affinity** | Rules for which services run on which machines |
| **Detection Method** | How the machine determined its role (saved/env/hostname/fallback) |
| **Deployment Mode** | Overall system configuration (single_pc vs dual_pc) |
| **Machine Role** | What this specific machine is doing (pc1, pc2, standalone) |

### J. Support & Feedback

**Questions or Issues?**
- Check troubleshooting section first
- Review logs in `backend/logs/app.log`
- Verify API status: `curl http://localhost:8000/api/v1/system/machine`
- Contact: [Your support channel here]

**Feature Requests:**
- Auto-recovery from fallback mode
- Background peer health checks
- mDNS service discovery
- More granular service affinity controls

---

## Document Metadata

**Document Version:** 1.0
**Last Updated:** 2026-03-08
**Author:** Elite Trading System Team
**Reviewed By:** [Pending]
**Next Review:** 2026-04-08 (1 month)

**Changelog:**
- 2026-03-08: Initial version based on machine awareness audit and implementation

---

**End of Migration Guide**
