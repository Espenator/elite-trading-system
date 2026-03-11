# PC2 (ProfitTrader) Setup — COMPLETE

> **Date:** 2026-03-10
> **Hostname:** ProfitTrader | **IP:** 192.168.1.116
> **Status:** Running and ready for handshake with ESPENMAIN

## What's Running on PC2

| Service | Port | Bind | Status |
|---------|------|------|--------|
| Backend API (FastAPI) | 8001 | 0.0.0.0 | Healthy, Redis-bridged to PC1 |
| Brain Service (gRPC) | 50051 | [::] (all) | Ready, 4 workers, Ollama-backed |
| Ollama | 11434 | 0.0.0.0 | 11 models loaded |
| GPU (RTX 4080) | — | — | 16GB VRAM, idle |

## Models Available on PC2 Ollama

- `mistral:7b` (4.4GB) — fast screening
- `qwen2.5:14b` (9GB) — medium reasoning
- `qwen2.5:32b` (20GB) — heavy reasoning
- `qwen3:8b`, `deepseek-r1:8b`, `llama3.1:8b`, `gemma3:12b`
- `granite3.3:8b`, `phi4-mini`, `0xroyce/plutus`
- `nomic-embed-text` — embeddings

## PC2's .env Key Settings

```env
# Identity
HOST=0.0.0.0
PC_ROLE=secondary
PC_HOSTNAME=ProfitTrader
PC_IP=192.168.1.116

# Reach ESPENMAIN
PC1_API_URL=http://192.168.1.105:8001
PC1_WS_URL=ws://192.168.1.105:8001/ws

# Cluster (empty = this IS PC2)
CLUSTER_PC2_HOST=
CLUSTER_HEALTH_INTERVAL=60

# Brain Service (local on PC2)
BRAIN_ENABLED=true
BRAIN_HOST=localhost
BRAIN_PORT=50051

# Ollama (local)
OLLAMA_PC2_URL=http://localhost:11434
SCANNER_OLLAMA_URLS=http://localhost:11434

# Redis bridge to PC1
REDIS_URL=redis://192.168.1.105:6379/0

# GPU telemetry
GPU_TELEMETRY_ENABLED=true
GPU_TELEMETRY_INTERVAL=3.0
```

---

## ESPENMAIN (PC1) — Required .env Additions

Add these to `backend/.env` on ESPENMAIN to complete the handshake:

```env
# ── PC Identity (ESPENMAIN — PC1 Primary) ─────────────────
HOST=0.0.0.0
PC_ROLE=primary
PC_HOSTNAME=ESPENMAIN
PC_IP=192.168.1.105

# ── Cross-PC: Reach ProfitTrader (PC2) ────────────────────
PC2_API_URL=http://192.168.1.116:8001
PC2_WS_URL=ws://192.168.1.116:8001/ws

# ── Cluster / Multi-PC ────────────────────────────────────
CLUSTER_PC2_HOST=192.168.1.116
CLUSTER_HEALTH_INTERVAL=60

# ── Brain Service (on PC2) ────────────────────────────────
BRAIN_ENABLED=true
BRAIN_HOST=192.168.1.116
BRAIN_PORT=50051

# ── Dual-PC Ollama (both PCs in the pool) ─────────────────
OLLAMA_PC2_URL=http://192.168.1.116:11434
SCANNER_OLLAMA_URLS=http://localhost:11434,http://192.168.1.116:11434

# ── Redis (runs on PC1, both PCs connect) ─────────────────
REDIS_URL=redis://192.168.1.105:6379/0

# ── GPU Telemetry ─────────────────────────────────────────
GPU_TELEMETRY_ENABLED=true
GPU_TELEMETRY_INTERVAL=3.0
```

## ESPENMAIN — Redis Setup (if not already running)

```bash
# Docker (recommended)
docker run -d --name cluster-redis -p 6379:6379 --restart unless-stopped redis:7-alpine redis-server --save 60 1 --loglevel warning --maxmemory 256mb
```

Or install Redis for Windows. PC2 is already connecting to `redis://192.168.1.105:6379/0`.

## ESPENMAIN — Firewall Rules (Admin PowerShell)

```powershell
New-NetFirewallRule -DisplayName "Embodier Backend API" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow -Profile Private
New-NetFirewallRule -DisplayName "Redis Cluster" -Direction Inbound -Protocol TCP -LocalPort 6379 -Action Allow -Profile Private
```

## Verification — Run from ESPENMAIN After Setup

```bash
# Ping PC2
ping 192.168.1.116

# PC2 Backend health
curl http://192.168.1.116:8001/health

# PC2 Ollama models
curl http://192.168.1.116:11434/api/tags

# PC2 Brain gRPC (TCP test)
# PowerShell: Test-NetConnection -ComputerName 192.168.1.116 -Port 50051

# Cluster status (after ESPENMAIN backend starts)
curl http://localhost:8001/api/v1/cluster/status
```

Expected cluster status:
```json
{
  "cluster_mode": true,
  "pc2": {
    "host": "192.168.1.116",
    "ollama": { "available": true, "models": 11 },
    "brain_service": { "available": true, "port": 50051 }
  },
  "redis": { "connected": true, "url": "redis://192.168.1.105:6379/0" }
}
```

## PC2 Firewall (Needs Admin — Run Once)

```powershell
New-NetFirewallRule -DisplayName "Brain gRPC" -Direction Inbound -Protocol TCP -LocalPort 50051 -Action Allow -Profile Private
New-NetFirewallRule -DisplayName "Embodier Backend API" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow -Profile Private
```
