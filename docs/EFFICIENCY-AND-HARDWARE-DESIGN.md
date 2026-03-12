# Efficiency & hardware design — one or two PCs

**Goal:** Maximize speed, compute, and data processing so the app runs as efficiently as possible on your hardware, whether one PC or two are available.

**Reference hardware (ESPENMAIN):**
- **CPU:** 13th Gen Intel Core i9-13900 (2.00 GHz) — 24 cores (8P + 16E), 32 threads
- **RAM:** 64 GB (61.7 GB usable)
- **GPU:** NVIDIA RTX 4080

Assume ProfitTrader can have similar or identical specs (e.g. RTX 4080, i9, 64 GB) for dual-PC design.

---

## 1. Design principles

| Principle | Meaning |
|-----------|--------|
| **Never block the event loop** | All heavy work (DuckDB, CPU-bound feature build, XGBoost) runs via `asyncio.to_thread()` or a dedicated thread/process pool. |
| **Batch I/O and compute** | Group bar writes, API calls, and DB reads into batches so we do fewer, larger operations. |
| **Use GPU where it pays** | XGBoost training and inference, embeddings, and LLM (Ollama) on GPU; keep the rest on CPU. |
| **Single writer for shared state** | One machine owns DuckDB writes; the other reads (or gets a synced copy) to avoid lock contention. |
| **Degrade gracefully** | If the second PC is down, the app runs fully on one machine with no hard dependency on the other. |

---

## 2. Single-PC mode (ESPENMAIN only)

When only one machine is running, that machine does everything. Tuning targets your i9 + 64 GB + RTX 4080.

### 2.1 CPU and thread pool

- **Event loop:** One thread; handles HTTP, WebSocket, MessageBus, and orchestration.
- **Default executor:** `ThreadPoolExecutor(max_workers=64)` (already set in `main.py` lifespan).  
  - 64 > 32 logical cores is intentional: many tasks are I/O-bound (DuckDB, HTTP); extra workers reduce queueing when many services call `asyncio.to_thread()` at once.
- **Feature aggregator:** Uses an internal `ThreadPoolExecutor(max_workers=4)` for parallel DuckDB fetches (regime, flow, indicators, intermarket). On a single powerful PC, consider **8** via env, e.g. `FEATURE_AGGREGATOR_WORKERS=8`.

### 2.2 Memory (64 GB)

- **DuckDB:** Columnar and compressed; even large OHLCV/indicator sets stay manageable. No change needed for 64 GB.
- **Python process:** FastAPI + 35-agent council + scanners + ingestion. Monitor RSS; 4–8 GB typical. If you add large in-memory caches, cap them (e.g. feature cache TTL and max entries).
- **Ollama (if on same PC):** Model in VRAM (RTX 4080 16 GB). Leave enough for one 7B–13B model; avoid loading multiple large models at once.

### 2.3 GPU (RTX 4080)

- **XGBoost:** Training and inference use `tree_method='gpu_hist'` and `device='cuda:0'` when available (`xgboost_trainer.py`, `ensemble_scorer.py`). Keep this enabled on the single PC.
- **Embeddings / FinBERT:** `ensemble_scorer` and any embedding path use CUDA when available. Ensures inference is fast on the single machine.
- **Ollama:** Run on GPU so hypothesis/critic and other LLM calls are fast. One model (e.g. 7B–13B) fits in 16 GB.

### 2.4 Data and I/O efficiency

- **Bar persistence:** Bars are buffered and written every **5 s** in a single batch (`main.py`); dedupe by (symbol, date). Reduces DuckDB lock contention and thread-pool usage.
- **Ingestion:** Alpaca bars in batches of **50 symbols**; rate-limited. Backfill uses the same batch size.
- **DuckDB:** Single process, single writer. All writes go through the singleton `duckdb_store` and its lock. No multi-process write sharing.

### 2.5 Concurrency caps (single PC)

| Component | Default | Env override | Note |
|-----------|--------|--------------|------|
| Default executor (DuckDB, etc.) | 64 | `ASYNCIO_THREAD_POOL_WORKERS=64` | Match or slightly exceed logical cores for I/O-heavy load. |
| Feature aggregator internal pool | 4 | `FEATURE_AGGREGATOR_WORKERS=8` | More parallel DuckDB reads per feature build. |
| Council max concurrent evaluations | 3 | `COUNCIL_MAX_CONCURRENT=4` | More parallel council runs; watch CPU. |
| SwarmSpawner workers | 20 | — | Async tasks; no thread per worker. |
| HyperSwarm workers | 50 | — | Same. |
| MarketWideSweep concurrent batches | 10 | — | Parallel Alpaca requests. |

---

## 3. Dual-PC mode (ESPENMAIN + ProfitTrader)

Split work so that the machine with the best fit for each task does it, and the app still runs if one PC is down.

### 3.1 Role split

| Role | ESPENMAIN (PC1) | ProfitTrader (PC2) |
|------|------------------|---------------------|
| **API & frontend** | Primary FastAPI, Vite, DuckDB writer, Alpaca execution | Optional read-only or backup API if desired |
| **Data** | Single writer for DuckDB; ingestion, backfill, bar buffer flush | — |
| **Council** | Stage 2+ and arbiter; coordinates with PC2 for Stage 1 | **Stage 1 (perception)** via brain gRPC; runs 13 agents in parallel |
| **LLM** | Can run Ollama locally (e.g. small model) or rely on PC2 | **Ollama** (11 models); **Brain gRPC** (hypothesis, critic, embeddings) |
| **ML** | XGBoost inference can run on PC1 GPU if present | **XGBoost training** and heavy inference; GPU-accelerated |
| **Awareness** | Sends event batches to PC2 for enrichment | **Awareness worker** (tags, novelty, embeddings) on GPU |

### 3.2 Data flow (efficient, single writer)

- **ESPENMAIN** is the **single writer** for DuckDB (`backend/data/analytics.duckdb`). All bar persistence, ingestion, and backfill run only on PC1.
- **ProfitTrader** either:
  - **Option A:** Uses a **synced copy** of DuckDB (e.g. one-way sync of the file or key tables from PC1), so it can run scans and ML locally without writing, or  
  - **Option B:** Calls **PC1’s API** for any data it needs (e.g. training window, features). No local DuckDB.

Option A minimizes latency for PC2’s ML and scans; Option B is simpler (no sync). Choose based on whether you run heavy scans/training on PC2.

### 3.3 Council latency (distributed Stage 1)

- When **brain gRPC** is available, **Stage 1** (13 perception agents) runs on **PC2** in parallel with **Stage 2** (8 agents) on **PC1**.
- So Stage 1 + Stage 2 time ≈ `max(Stage1_latency, Stage2_latency)` instead of sum. That already cuts council latency when both PCs are up.
- If PC2 or brain is down, council falls back to **local** Stage 1 + Stage 2 on PC1 (no hard failure).

### 3.4 GPU use (both PCs)

- **ESPENMAIN:** Use RTX 4080 for XGBoost inference (and training if you don’t offload to PC2), and optionally a small Ollama model for fallback.
- **ProfitTrader:** Use RTX 4080 for Ollama (multiple models), Brain gRPC (hypothesis, critic, embeddings), XGBoost training, and awareness embeddings. LLM dispatcher can route by GPU utilization (already considers `gpu_utilization_pct`).

---

## 4. Recommended env-driven tuning

Expose key knobs so you can tune for one vs two PCs and for your exact hardware without code changes.

| Env var | Default | Purpose |
|---------|--------|---------|
| `ASYNCIO_THREAD_POOL_WORKERS` | 64 | Default executor size (DuckDB, blocking calls). |
| `FEATURE_AGGREGATOR_WORKERS` | 4 | Internal parallel fetches per feature build. Increase to 6–8 on i9. |
| `COUNCIL_MAX_CONCURRENT` | 3 | Max concurrent council evaluations. 4 if CPU allows. |
| `BAR_BUFFER_FLUSH_SEC` | 5 | Seconds between DuckDB bar batch writes. |
| `XGBOOST_GPU_ID` | 0 | GPU device for XGBoost. |
| `DISABLE_ALPACA_DATA_STREAM` | 0 | Set to 1 to disable live stream (e.g. if only backfill). |
| `STARTUP_BACKFILL_ENABLED` | true | Set to false to skip 252-day backfill on startup. |
| `CLUSTER_PC2_HOST` | — | PC2 host (e.g. 192.168.1.116) for distributed council and brain. |
| `AWARENESS_WORKER_URL` | — | PC2 URL for awareness enrichment (optional). |

(Some of these may already exist; add any missing ones in `config.py` and wire them where needed.)

---

## 5. Final architecture sketch

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    ESPENMAIN (PC1)                        │
                    │  i9-13900 · 64 GB · RTX 4080                             │
                    │  • FastAPI + frontend + MessageBus                        │
                    │  • DuckDB single writer (bars, indicators, outcomes)      │
                    │  • Bar buffer → 5s batch flush                           │
                    │  • Council Stage 2–7 + arbiter                            │
                    │  • XGBoost inference (GPU) / optional Ollama             │
                    │  • Alpaca execution + data ingestion                     │
                    │  • Thread pool 64 · Feature workers 4–8                  │
                    └───────────────────────────┬─────────────────────────────┘
                                                 │
                         Optional / when PC2 up   │  gRPC (brain) · HTTP (awareness)
                                                 │  Stage 1 votes · enriched events
                                                 ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │                  ProfitTrader (PC2)                      │
                    │  i9 · 64 GB · RTX 4080                                   │
                    │  • Brain gRPC: Stage 1 (13 agents) + hypothesis + critic │
                    │  • Ollama: 11 models (GPU)                               │
                    │  • Awareness: batch embeddings, tags, novelty (GPU)       │
                    │  • XGBoost training (GPU) · optional inference           │
                    │  • Reads: synced DuckDB or API to PC1                     │
                    └─────────────────────────────────────────────────────────┘
```

**Single-PC:** Run everything on ESPENMAIN; leave `CLUSTER_PC2_HOST` / brain URL unset so council and LLM run locally. No dependency on PC2.

**Dual-PC:** Set `CLUSTER_PC2_HOST` and brain URL; Stage 1 and heavy LLM/GPU work run on PC2; PC1 remains the data and execution hub.

---

## 6. Summary

- **Single PC:** One process uses the i9 (64-thread pool), 64 GB RAM, and RTX 4080 (XGBoost + optional Ollama). Batching and non-blocking I/O keep the app efficient.
- **Two PCs:** PC1 = data + API + execution + council Stage 2+; PC2 = GPU-heavy Stage 1, Ollama, Brain, awareness, and ML training. One DuckDB writer (PC1); PC2 reads via sync or API.
- **Efficiency:** Batch bars (5 s), batch API/DB where possible, keep all heavy work off the event loop, use GPU for XGBoost and LLMs, and tune workers via env so the same code scales across one or two PCs and your exact hardware.
