# PC2 (ProfitTrader) Setup Guide

> Last updated: 2026-03-12 — Branch `claude/xgboost-gpu-inference-PMXv9`

## Hardware

| Spec | Value |
|------|-------|
| Hostname | ProfitTrader |
| LAN IP | 192.168.1.116 (DHCP-reserved) |
| GPU | NVIDIA RTX 4080 (16GB VRAM) |
| Role | GPU training, ML inference, brain_service (gRPC), Ollama LLM |
| Repo path | `C:\Users\ProfitTrader\elite-trading-system` |

See `docs/HARDWARE-SPECS.md` for full GPU benchmarks and VRAM budget.
See `docs/CLUSTER-NETWORK-SETUP.md` for firewall and static IP setup.

---

## 1. Pull the Latest Code

Open PowerShell on ProfitTrader:

```powershell
cd C:\Users\ProfitTrader\elite-trading-system

# Fetch the branch with all GPU + channels + architectural fixes
git fetch origin claude/xgboost-gpu-inference-PMXv9

# Check out the branch
git checkout claude/xgboost-gpu-inference-PMXv9

# Pull latest (if you already had the branch)
git pull origin claude/xgboost-gpu-inference-PMXv9
```

### What this branch includes (6 commits):

| Commit | What it does |
|--------|-------------|
| PC-role aware Alpaca keys | Prevents WebSocket conflicts between PC1 and PC2 |
| GPU Phase 1 (Channels 2, 6, 7) | XGBoost `cuda` inference, parallel 4-angle LLM hypothesis, critic gRPC routing to PC2 |
| Redis bridge + persistent DLQ | Cross-PC cluster communication via Redis Streams |
| Architectural fixes (Tier 1+2) | Regime enforcement, learning system fix, adaptive thresholds, confidence floor |
| Channels orchestrator perf | Parallel agent start/stop via `asyncio.gather` |
| Batch-drain architecture | Single worker drains up to N events, processes all concurrently via `asyncio.gather` |

---

## 2. Environment Variables

Edit `backend\.env` on ProfitTrader. Copy from `backend\.env.example` if starting fresh.

### Required — PC Role & GPU

```ini
# === PC2 Identity ===
PC_ROLE=gpu

# === GPU Inference (XGBoost) ===
# GPU device ID — 0 for single-GPU systems
XGBOOST_GPU_ID=0

# === Ollama (Local LLM) ===
# Allow 4 concurrent requests for parallel hypothesis (GPU Channel 6)
OLLAMA_NUM_PARALLEL=4
# Ollama listens on all interfaces so PC1 can reach it
OLLAMA_HOST=0.0.0.0:11434
```

### Required — Brain Service (gRPC)

```ini
# === Brain Service (PC2 hosts, PC1 connects) ===
BRAIN_SERVICE_PORT=50051
BRAIN_SERVICE_HOST=0.0.0.0
```

### Required — Alpaca (PC2 uses Key 2)

```ini
# === Alpaca — Profit Trader account (discovery scanning) ===
ALPACA_API_KEY=<your-key-2>
ALPACA_SECRET_KEY=<your-secret-2>
ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2
ALPACA_ENV=paper
```

### Optional — Redis Bridge (cross-PC messaging)

If Redis is running on PC1 (ESPENMAIN):

```ini
# === Redis Bridge ===
REDIS_URL=redis://192.168.1.105:6379
```

If Redis is running on PC2 instead:

```ini
REDIS_URL=redis://localhost:6379
```

### Optional — Channels Batch Tuning

Defaults are set in code but can be overridden:

```ini
# === Channel Batch Sizes ===
# Higher = more throughput, more memory per cycle
ALPACA_FIREHOSE_BATCH=32
ALPACA_FIREHOSE_QUEUE=5000
UW_FIREHOSE_BATCH=16
UW_FIREHOSE_QUEUE=3000
FINVIZ_FIREHOSE_BATCH=16
DISCORD_FIREHOSE_BATCH=8
NEWS_FIREHOSE_BATCH=8
```

### Optional — Awareness Layer

If PC2 runs the awareness/enrichment HTTP endpoint:

```ini
AWARENESS_MODE=http
AWARENESS_URL=http://localhost:8000
AWARENESS_TIMEOUT_S=6.0
```

---

## 3. Install Dependencies

```powershell
cd C:\Users\ProfitTrader\elite-trading-system\backend

# Create/activate venv
python -m venv venv
venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt

# Verify XGBoost CUDA works
python -c "import xgboost as xgb; dm = xgb.DMatrix([[1.0]], label=[0]); xgb.train({'tree_method':'gpu_hist','device':'cuda:0','max_depth':1}, dm, 1); print('GPU OK')"
```

If the XGBoost GPU test fails, the system automatically falls back to CPU (`tree_method='hist'`). No action needed — it just won't be as fast.

### Ollama Setup

```powershell
# Install Ollama (if not already installed)
winget install Ollama.Ollama

# Pull the model for hypothesis/critic inference
ollama pull mistral

# Verify Ollama is serving
curl http://localhost:11434/api/tags
```

### Redis (Optional)

```powershell
# If running Redis on PC2 (otherwise PC1 hosts it)
winget install Redis.Redis
# Or use Docker: docker run -d -p 6379:6379 redis:7-alpine
```

---

## 4. Start Services

### Terminal 1 — Brain Service (gRPC)

```powershell
cd C:\Users\ProfitTrader\elite-trading-system\backend
venv\Scripts\Activate.ps1
python -m app.services.brain_service
# Should show: "Brain service listening on 0.0.0.0:50051"
```

### Terminal 2 — Backend API

```powershell
cd C:\Users\ProfitTrader\elite-trading-system\backend
venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 3 — Ollama (if not running as a system service)

```powershell
ollama serve
# Listens on 0.0.0.0:11434 (set by OLLAMA_HOST env var)
```

---

## 5. Verify PC2 is Working

### From PC2 (localhost)

```powershell
# Check backend health
curl http://localhost:8000/api/v1/health

# Check cluster status (should show Redis bridge if configured)
curl http://localhost:8000/api/v1/cluster/status

# Check GPU telemetry
curl http://localhost:8000/api/v1/cluster/telemetry

# Check Ollama
curl http://localhost:11434/api/tags
```

### From PC1 (ESPENMAIN) — verify cross-PC connectivity

```powershell
# Test brain service (gRPC)
curl http://192.168.1.116:8000/api/v1/health

# Test Ollama on PC2
curl http://192.168.1.116:11434/api/tags

# Test Redis bridge (if Redis on PC1)
redis-cli ping
# Should return: PONG
```

---

## 6. PC1 (ESPENMAIN) Companion Config

PC1 needs to know where PC2 lives. Add these to `backend\.env` on ESPENMAIN:

```ini
# === PC2 Connection (set on PC1) ===
PC_ROLE=primary
CLUSTER_PC2_HOST=192.168.1.116
PC2_BRAIN_URL=http://192.168.1.116:50051
PC2_OLLAMA_URL=http://192.168.1.116:11434

# Redis (if running on PC1)
REDIS_URL=redis://localhost:6379
```

---

## 7. VRAM Budget (RTX 4080 16GB)

```
RTX 4080 — 16GB VRAM
├── Ollama + Mistral 7B Q4        ~5.0 GB  (24/7 screening + hypothesis)
├── XGBoost CUDA inference         ~1.5 GB  (win probability, ensemble)
├── CUDA overhead + system         ~1.0 GB
└── Headroom for spikes            ~8.5 GB FREE
```

The system probes GPU availability at startup. If VRAM is exhausted, XGBoost
silently falls back to CPU and Ollama queues requests. No crashes.

---

## 8. Firewall Rules (Windows)

If PC1 can't reach PC2, open these ports on PC2:

```powershell
# Run PowerShell as Administrator on PC2
New-NetFirewallRule -DisplayName "Ollama LLM" -Direction Inbound -Port 11434 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Brain gRPC" -Direction Inbound -Port 50051 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Backend API" -Direction Inbound -Port 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Redis" -Direction Inbound -Port 6379 -Protocol TCP -Action Allow
```

Also ensure both PCs have their network profile set to **Private** (not Public).
See `docs/CLUSTER-NETWORK-SETUP.md` for details.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `brain_client unavailable` on PC1 | Check brain_service running on PC2, firewall port 50051 |
| `XGBoost GPU probe failed` | Run `nvidia-smi` — driver OK? Try `pip install xgboost --upgrade` |
| `Ollama connection refused` from PC1 | Set `OLLAMA_HOST=0.0.0.0:11434` on PC2, check firewall port 11434 |
| `Redis connection refused` | Start Redis, check `REDIS_URL` points to correct host |
| High queue drops (`events_dropped_queue_full`) | Increase `ALPACA_FIREHOSE_QUEUE` or `ALPACA_FIREHOSE_BATCH` |
| Channels orchestrator slow | Check `max_batch_seen` in metrics — if always 1, events aren't batching (low volume, normal) |
| `circuit_open` on a channel agent | Downstream failure (MessageBus, Redis). Check logs. Circuit resets after 30s |
