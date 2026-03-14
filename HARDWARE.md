# Hardware and Runtime Tuning

This document defines the recommended hardware/runtime profile for local deployment on ESPENMAIN, with tuning values oriented around an RTX 4080 and a hybrid P-core/E-core CPU.

## ESPENMAIN Hardware Profile

- Host: `ESPENMAIN` (primary node)
- Role: backend API, frontend, DuckDB analytics, trading execution
- GPU: NVIDIA RTX 4080 (primary inference/acceleration device)
- CPU class: hybrid architecture (P-cores + E-cores)
- Memory target: 64 GB system RAM with a 48 GB DuckDB ceiling

## RTX 4080 Environment Variables

Use these defaults in Docker and local `.env` files:

### Brain service

```env
OLLAMA_MODEL=qwen2.5:14b-instruct-q4_K_M
OLLAMA_FLASH_ATTENTION=1
OLLAMA_NUM_PARALLEL=4
OLLAMA_MAX_LOADED_MODELS=1
CUDA_VISIBLE_DEVICES=0
BRAIN_MAX_WORKERS=12
```

### Backend service

```env
COUNCIL_WORKERS=8
IO_WORKERS=16
OMP_NUM_THREADS=12
MKL_NUM_THREADS=12
CUDA_VISIBLE_DEVICES=0
```

## CPU P-core / E-core Allocation Strategy

- Reserve P-cores for latency-critical paths: council orchestration, risk checks, order execution, and gRPC request handling.
- Route I/O-heavy and background tasks to E-cores: streaming adapters, telemetry, backfill, and non-critical async tasks.
- Keep thread-heavy numeric workloads bounded with:
  - `OMP_NUM_THREADS=12`
  - `MKL_NUM_THREADS=12`
- Avoid oversubscription by not setting worker/thread counts above effective compute capacity.

## DuckDB Memory Configuration

Recommended baseline for ESPENMAIN:

```env
DUCKDB_MEMORY_LIMIT=48GB
DUCKDB_THREADS=12
```

Notes:
- For ESPENMAIN, keep `DUCKDB_MEMORY_LIMIT=48GB` to maximize in-memory analytics while leaving headroom for OS and GPU transfer buffers.
- Keep `DUCKDB_THREADS` aligned with the compute budget used by OMP/MKL settings to avoid CPU contention.

## Recommended Ollama Model

Use the following default model on RTX 4080:

- `qwen2.5:14b-instruct-q4_K_M`

This model balances quality and throughput for the council hypothesis and reasoning workloads while keeping VRAM pressure stable with `OLLAMA_MAX_LOADED_MODELS=1`.
