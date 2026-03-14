# Two-PC Architecture -- Embodier Trader

## Executive Summary

The Elite Trading System runs across two Windows PCs on the same LAN:

- **PC1 (ESPENMAIN)** = Control Plane -- orchestration, monitoring, frontend, development
- **PC2 (ProfitTrader)** = Execution Plane -- GPU inference, council DAG, trading engine

ProfitTrader IS the profit engine. ESPENMAIN supervises, deploys, and monitors.

## Network & Service Map

```
ESPENMAIN (192.168.1.105)              ProfitTrader (192.168.1.116)
========================               ============================

[Frontend Vite :5173] ----proxy----->  [FastAPI :8001]
[Backend API :8001]                    [brain_service gRPC :50051]
[Redis :6379] <----event bus-------->  [Redis client]
                                       [GPU Worker (Redis queue)]
                                       [Ollama :11434 (localhost only)]
                                       [WebSocket :8001/ws]

      LAN: 192.168.1.0/24
      Router: AT&T BGW320-505 (192.168.1.254)
```

## What Runs Where

### PC1 -- ESPENMAIN (Control Plane)
| Service | Port | Purpose |
|---------|------|---------|
| Backend API | 8001 | Full monolith -- signals, council, execution |
| Frontend (Vite) | 5173 | React dashboard |
| Redis | 6379 | Cross-PC event bus |
| Health Monitor | -- | Watches PC2 status |
| Data Swarm | -- | Alpaca, UW, FinViz collectors |
| DuckDB | -- | Primary analytics store |

### PC2 -- ProfitTrader (Execution Plane)
| Service | Port | Purpose |
|---------|------|---------|
| API Server (lightweight) | 8001 | FastAPI without heavy engine |
| brain_service | 50051 | gRPC -- Ollama LLM inference |
| Ollama | 11434 | Local only -- gemma3:12b + qwen3:8b |
| GPU Worker | Redis | PyTorch CUDA feature engineering |
| Council Worker | Redis | Distributed agent execution |
| Frontend (optional) | 5173+ | Local dashboard mirror |

## Hardware-Aware Optimization (PC2)

### CPU: i7-13700 (8P + 8E cores, 24 threads)

```
P-cores (logical 0-15) -- Latency-sensitive:
  - FastAPI / uvicorn
  - brain_service gRPC
  - Council runner
  - WebSocket event loop
  - Order executor
  - Alpaca stream handler

E-cores (logical 16-23) -- Background work:
  - GPU Worker (batch feature computation)
  - DuckDB analytics queries
  - Postmortem writes
  - Retraining jobs
  - Health monitoring
  - Log processing
```

### GPU: RTX 4080 (16GB VRAM, 9728 CUDA cores)

```
VRAM Budget:
  gemma3:12b (primary)     8,100 MB  -- hypothesis, trade thesis, deep reasoning
  qwen3:8b (secondary)     5,200 MB  -- critic, fast tasks, postmortems
  nomic-embed-text           274 MB  -- knowledge embeddings
  PyTorch tensors          1,000 MB  -- GPU feature engineering
  XGBoost CUDA               500 MB  -- tree scoring
  CUDA runtime               500 MB  -- context overhead
  Safety headroom          1,000 MB  -- spike protection
                          --------
  Total:                  16,574 MB  (models swap, not simultaneous)

Model Strategy:
  - Primary + embed can co-reside (8,374 MB)
  - Secondary + embed can co-reside (5,474 MB)
  - Primary + secondary CANNOT co-reside (13,300 MB > safe limit)
  - Ollama handles swapping automatically
  - OLLAMA_KEEP_ALIVE=10m keeps primary loaded between tasks
```

### RAM: 32 GB

```
  Python main process:    2 GB
  DuckDB (WAL + buffers): 4 GB
  Ollama (model overflow): 12 GB
  GPU Worker (staging):    2 GB
  brain_service:           1 GB
  OS + System:             4 GB
  Headroom:                7 GB
```

## Communication Paths

| From | To | Method | Purpose |
|------|-----|--------|---------|
| PC1 Backend | PC2 brain_service | gRPC :50051 | LLM inference (hypothesis, critic) |
| PC1 Backend | PC2 Council Worker | Redis Streams | Distributed agent execution |
| PC1 Backend | PC2 GPU Worker | Redis Streams | Feature computation requests |
| PC2 Backend | PC1 Redis | Redis :6379 | Event bus (signals, positions, health) |
| PC1 Frontend | PC1 Backend | HTTP :8001 | Dashboard API |
| PC2 Frontend | PC2 API Server | HTTP :8001 | Local dashboard (lightweight) |

## Security Boundaries

- **Ollama**: Bound to `localhost:11434` on PC2 only. Never exposed to LAN.
  brain_service is the secure wrapper.
- **Redis**: LAN-only (192.168.1.0/24). No public exposure.
- **gRPC**: LAN-only. No TLS needed for home LAN. Add if deploying to cloud.
- **FastAPI**: LAN-only. CORS allows both PC IPs.
- **Windows Firewall**: Open ports 8001, 50051, 6379 for LAN subnet only.

## Startup Order

### PC2 (ProfitTrader) -- start first
```
1. Ollama (if not running as Windows service)
2. brain_service (gRPC :50051)
3. GPU Worker (Redis consumer)
4. API Server (lightweight :8001)
5. Frontend (optional :5173)
```

### PC1 (ESPENMAIN) -- start second
```
1. Redis (if not running as Windows service)
2. Backend API (full monolith :8001)
3. Frontend (:5173)
4. Remote health monitor starts automatically
```

## Failure Modes

| Failure | Impact | Fallback |
|---------|--------|----------|
| PC2 down | No GPU inference | PC1 uses local Ollama (mistral:7b) or deterministic logic |
| PC2 brain_service down | No LLM hypothesis | Council runs without hypothesis (25 agents still vote) |
| Redis down | No cross-PC events | Each PC runs independently |
| PC2 GPU OOM | Inference fails | Ollama auto-offloads to CPU. Slower but functional |
| PC1 down | No dashboard/frontend | PC2 continues trading autonomously |
| Network partition | PCs isolated | Each operates standalone |

## Configuration Files

```
backend/.env              -- Active config (gitignored, machine-specific)
backend/.env.pc1.template -- Template for ESPENMAIN
backend/.env.pc2.template -- Template for ProfitTrader
```

## Key Code Files

```
backend/app/core/hardware_profile.py  -- CPU topology, GPU detection, VRAM budget
backend/app/core/pc_role.py           -- Role detection, service manifest, affinity maps
backend/app/core/gpu_config.py        -- Ollama model strategy, VRAM allocation
backend/app/core/remote_health.py     -- Cross-PC health monitoring
backend/app/core/pc2_health.py        -- Startup infrastructure checks
backend/app/core/config.py            -- Settings with PC_ROLE, MODEL_PIN, etc.
backend/api_server.py                 -- PC2 lightweight API server
backend/gpu_worker.py                 -- PC2 GPU worker (PyTorch CUDA)
backend/redis_mesh.py                 -- Redis Streams event bridge
start_pc1.py                          -- PC1 launcher
start_pc2.py                          -- PC2 launcher (with CPU affinity)
brain_service/server.py               -- PC2 gRPC LLM server
brain_service/ollama_client.py        -- Ollama inference client
```

## Phased Implementation

### Phase 1: Minimum Viable Two-PC (DONE)
- [x] brain_service gRPC on PC2
- [x] Council coordinator with Redis Streams
- [x] Model pinning (fast tasks PC1, deep tasks PC2)
- [x] GPU worker with PyTorch CUDA
- [x] Lightweight API server for PC2
- [x] start_pc2.py launcher
- [x] Hardware profile detection

### Phase 2: Performance Optimization (IN PROGRESS)
- [x] CPU affinity (P-cores vs E-cores) on PC2
- [x] VRAM budgeting for Ollama models
- [x] Dual-model strategy (gemma3:12b + qwen3:8b)
- [ ] Ollama model pre-loading at startup
- [ ] XGBoost CUDA histogram method
- [ ] cuDF for pandas hot paths (if installed)

### Phase 3: Resilience & Self-Healing
- [x] Remote health monitoring
- [x] Graceful fallback when PC2 unavailable
- [ ] Auto-restart of crashed services
- [ ] Health dashboard page in frontend
- [ ] Slack alerts on PC2 failure
- [ ] Connection pooling for gRPC
