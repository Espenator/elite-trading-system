# Claude Code Handoff: 11-Channel GPU Compute Architecture

**Date:** March 11, 2026
**From:** Cowork (architectural review + infrastructure)
**To:** Claude Code (implementation)
**Repo:** github.com/Espenator/elite-trading-system
**Branch:** main (commit `7b009ab`)

---

## CONTEXT

The E0.x infrastructure layer is COMPLETE (AlpacaKeyPool, OllamaNodePool, NodeDiscovery, AlpacaStreamManager, Brain Service, cluster API). The MessageBus Redis bridge is implemented but needs `REDIS_URL` set. PC2 launcher with GPU quick wins (`OLLAMA_NUM_PARALLEL=4`, `OLLAMA_FLASH_ATTENTION=1`) is committed.

**What's NOT done:** Actually using the GPUs for compute. Both RTX 4090s (48GB VRAM combined, 32,768 CUDA cores, 8 Tensor Core units) sit at ~2.5% utilization. PC1's GPU does literally nothing. PC2's wakes up once per minute for a single Ollama call.

---

## THE 11-CHANNEL ARCHITECTURE TO IMPLEMENT

### PC1 Channels (5 channels — ESPENMAIN, 192.168.1.105)

**Channel 1: GPU-Accelerated Feature Compute**
- Replace numpy/pandas feature engineering with cuDF (RAPIDS)
- File: `backend/app/services/signal_engine.py` (feature aggregation section)
- File: `backend/app/council/feature_aggregator.py`
- Target: Feature computation from ~100ms → ~5ms per symbol
- Install: `pip install cudf-cu12 cuml-cu12` (RAPIDS for CUDA 12)
- Pattern: Keep CPU fallback — `try: import cudf; except: import pandas as pd`

**Channel 2: GPU Signal Scoring**
- Move XGBoost inference to GPU
- File: `backend/app/modules/ml_engine/xgboost_trainer.py`
- File: `backend/app/modules/ml_engine/ensemble_scorer.py`
- Change: `tree_method='hist'` → `tree_method='gpu_hist', device='cuda'`
- Target: Batch scoring 200 symbols in ~50ms (currently ~500ms sequential)

**Channel 3: Monte Carlo Risk Simulation**
- Add GPU-accelerated VaR calculation using CuPy
- File: `backend/app/services/risk_service.py` (currently single-day snapshot)
- New: Implement 10,000-path Monte Carlo VaR on GPU
- Install: `pip install cupy-cuda12x`
- Target: Full portfolio VaR in ~20ms (vs impossible on CPU at this path count)

**Channel 4: GPU-Accelerated Discovery Screening**
- Move TurboScanner DuckDB screens to GPU-backed compute
- File: `backend/app/services/turbo_scanner.py`
- Use cuDF for the 10 screening queries (RSI, MACD, volume, etc.)
- Target: 8000+ symbol screen in ~200ms (currently 2-5s)

**Channel 5: Streaming Data Processing**
- GPU-accelerated bar/quote aggregation from Alpaca WebSocket
- File: `backend/app/services/alpaca_stream_service.py`
- Pattern: Batch incoming bars into GPU tensor, compute rolling indicators
- Target: Real-time indicator computation for 500+ symbols

### PC2 Channels (6 channels — ProfitTrader, 192.168.1.116)

**Channel 6: Parallel LLM Hypothesis Generation**
- Run 4 parallel Ollama inferences for hypothesis agent
- Already enabled: `OLLAMA_NUM_PARALLEL=4` in start-profittrader.ps1
- File: `backend/app/council/agents/hypothesis_agent.py`
- Change: Generate 4 hypotheses in parallel, then synthesize
- Target: 4 diverse hypotheses in the same time as 1 today

**Channel 7: GPU Critic Agent**
- Dedicated GPU inference for postmortem analysis
- File: `backend/app/council/agents/critic_agent.py`
- Change: Run critic asynchronously on PC2 via brain_service gRPC
- Target: Critic never blocks the council pipeline

**Channel 8: GPU Regime Classification**
- Move HMM regime detection to GPU
- File: `backend/app/services/regime_detection.py` or equivalent
- Use: cuML's HMM or custom CUDA kernel
- Target: Regime updates every 30s (currently 300s) with full market state

**Channel 9: NLP Pipeline (Transformers)**
- Run FinBERT or similar on PC2 GPU for sentiment analysis
- File: New — `backend/app/services/nlp_pipeline.py`
- Process: Benzinga news, SEC filings, earnings transcripts
- Publish to: `perception.sentiment` topic on MessageBus
- Target: Real-time sentiment scoring for 100+ news items/minute

**Channel 10: Embedding Service**
- GPU-accelerated text embeddings for KnowledgeGraph
- File: New — `backend/app/services/embedding_service.py`
- Model: `all-MiniLM-L6-v2` or `bge-small-en` on GPU
- Target: 1000+ embeddings/second for knowledge ingestion

**Channel 11: GPU Training Pipeline**
- XGBoost + LSTM training on PC2's GPU
- File: `backend/app/services/ml_training.py`
- File: `backend/app/modules/ml_engine/xgboost_trainer.py`
- Change: Train on GPU during off-hours, publish updated model
- Target: Nightly retraining with walk-forward validation

---

## IMPLEMENTATION ORDER

Build in this order (each channel is independent, but infrastructure first):

### Phase 1: Quick Wins (1-2 sessions)
1. **Channel 2** — XGBoost GPU inference (one-line change: `gpu_hist`)
2. **Channel 6** — Parallel LLM hypothesis (already enabled, just code the parallelism)
3. **Channel 7** — Critic on PC2 (route via existing brain_service gRPC)

### Phase 2: Core Compute (3-5 sessions)
4. **Channel 1** — cuDF feature compute (biggest latency win)
5. **Channel 3** — Monte Carlo VaR (biggest risk management win)
6. **Channel 8** — GPU regime classification (30s refresh → catch transitions faster)

### Phase 3: Intelligence Layer (3-5 sessions)
7. **Channel 4** — GPU screening
8. **Channel 9** — NLP pipeline
9. **Channel 10** — Embedding service
10. **Channel 5** — Streaming data processing
11. **Channel 11** — GPU training pipeline

---

## RULES (CRITICAL — DO NOT VIOLATE)

1. **Every GPU feature MUST have a CPU fallback** — `try: import cudf; except: import pandas`
2. **DO NOT modify signal_engine.py core logic** — only the feature computation paths
3. **DO NOT modify council/ agent voting logic** — only inference backends
4. **DO NOT modify order_executor.py** — execution gates are correct, don't touch them
5. **4-space Python indentation, NEVER tabs**
6. **All GPU services must degrade gracefully** if no GPU is present
7. **MessageBus topics** — use existing topics, add new ones to VALID_TOPICS if needed
8. **Test on CPU first** — ensure CPU fallback works before adding GPU paths
9. **PC2 work goes through brain_service gRPC** — don't add new network protocols
10. **pip install with --break-system-packages if in venv**

## KEY FILES TO READ FIRST

| File | Why |
|------|-----|
| `backend/app/core/message_bus.py` | Understand the event bus (already has Redis bridge) |
| `backend/app/services/signal_engine.py` | Core signal pipeline — features computed here |
| `backend/app/council/runner.py` | How the 33-agent council executes |
| `backend/app/modules/ml_engine/xgboost_trainer.py` | Current XGBoost setup |
| `backend/app/services/brain_client.py` | gRPC client for PC2 offload |
| `brain_service/server.py` | gRPC server running on PC2 |
| `docs/SUPERCOMPUTER-ARCHITECTURE.md` | Current two-PC architecture |
| `ARCHITECTURAL-REVIEW-2026-03-11.md` | Deep audit with compounding failure analysis |
| `CLAUDE.md` | Master project context |

## HARDWARE REFERENCE

| | PC1 (ESPENMAIN) | PC2 (ProfitTrader) |
|---|---|---|
| GPU | RTX 4090 (24GB VRAM) | RTX 4090 (24GB VRAM) |
| CPU | i9-13900 (24 cores) | Similar spec |
| RAM | 64GB | 64GB |
| CUDA Cores | 16,384 | 16,384 |
| Tensor Cores | 4th gen (FP8) | 4th gen (FP8) |
| Role | Command + Execution + Features | Intelligence + Training + LLM |

## EXPECTED OUTCOMES

| Metric | Before | After Phase 1 | After Phase 3 |
|--------|--------|---------------|---------------|
| GPU utilization (combined) | ~2.5% | ~15-25% | ~40-60% |
| Feature computation | ~100ms | ~100ms | ~5ms (cuDF) |
| XGBoost inference | ~500ms batch | ~50ms GPU | ~50ms GPU |
| VaR calculation | 1-day snapshot | 1-day snapshot | 10K-path Monte Carlo |
| Regime refresh | 300s | 300s | 30s |
| LLM parallel inferences | 1 | 4 | 4 |
| Sentiment analysis | None | None | Real-time NLP |
| Total pipeline latency | ~1.5-2s | ~0.8-1.2s | ~0.3-0.5s |
