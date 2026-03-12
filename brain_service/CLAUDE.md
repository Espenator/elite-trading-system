# CLAUDE.md — Embodier Trader Brain Service
# gRPC LLM Inference Server (PC2 / RTX GPU)
# Last updated: March 12, 2026 — v4.1.0-dev

## Overview

The brain_service is a **gRPC server** that provides local LLM inference using Ollama on an RTX GPU. It runs on **PC2 (ProfitTrader, 192.168.1.116)** and serves as the primary LLM backend for the trading system.

## Architecture

```
PC1 (ESPENMAIN)                        PC2 (ProfitTrader)
┌─────────────────┐                    ┌──────────────────────┐
│ backend/        │   gRPC :50051      │ brain_service/       │
│  services/      │ ──────────────►    │  server.py           │
│   brain_client  │                    │  ollama_client.py    │
│   hypothesis_   │                    │  ↓                   │
│   agent.py      │   ◄────────────    │  Ollama (RTX GPU)    │
│                 │   LLM response     │  :11434              │
└─────────────────┘                    └──────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `server.py` | gRPC server — listens on port 50051 |
| `ollama_client.py` | Ollama API client for local LLM inference |
| `models.py` | Request/response schemas |
| `proto/` | Protobuf service definitions |
| `compile_proto.py` | Protobuf compilation script |
| `requirements.txt` | Python dependencies |

## 3-Tier LLM Router

The brain_service is part of a 3-tier LLM intelligence system:

| Tier | Provider | When Used | Cost |
|------|----------|-----------|------|
| **Tier 1** | Ollama (local, via brain_service) | Routine tasks, hypothesis generation | Free |
| **Tier 2** | Perplexity (sonar-pro) | Web search + synthesis needed | Moderate |
| **Tier 3** | Claude (Anthropic) | 6 deep-reasoning tasks ONLY | Higher |

### Claude-Reserved Tasks (Tier 3 — 6 tasks only)
1. `strategy_critic` — Deep strategy analysis
2. `strategy_evolution` — Strategy improvement suggestions
3. `deep_postmortem` — Detailed trade postmortem
4. `trade_thesis` — Complex trade thesis generation
5. `overnight_analysis` — Overnight market analysis
6. `directive_evolution` — Trading directive improvement

All other LLM tasks go through Ollama (Tier 1) or Perplexity (Tier 2).

## Primary Consumer

**`hypothesis_agent.py`** in the council is the primary consumer of brain_service. It calls the gRPC endpoint to generate trade hypotheses using local LLM inference on the RTX GPU.

Backend client: `backend/app/services/brain_client.py`

## Configuration

Environment variables (in `backend/.env`):

```bash
BRAIN_SERVICE_URL=           # Full URL override (e.g., localhost:50051)
BRAIN_ENABLED=true
BRAIN_HOST=localhost         # Use 192.168.1.116 for cross-PC
BRAIN_PORT=50051
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
LOCAL_LLM_MODEL=qwen3:14b
```

## How to Start

```bash
# On PC2 (ProfitTrader)
cd C:\Users\ProfitTrader\elite-trading-system\brain_service
pip install -r requirements.txt
python server.py              # gRPC server on :50051

# Ensure Ollama is running
ollama serve                  # Ollama on :11434
ollama pull qwen3:14b         # Pull the model
```

## Model Pinning (Asymmetric Routing)

Models are pinned by PC role:

| PC | Models | Tasks |
|----|--------|-------|
| PC1 (ESPENMAIN) | llama3.2, mistral:7b | Fast tactical: regime_classification, signal_scoring, risk_check |
| PC2 (ProfitTrader) | deepseek-r1:14b, mixtral:8x7b | Heavy thinking: trade_thesis, strategy_critic, deep_postmortem |

Configured via `MODEL_PIN_PC1`, `MODEL_PIN_PC2`, `MODEL_PIN_TASK_AFFINITY` env vars.

## Hardware

- **PC2 Hostname**: ProfitTrader
- **PC2 IP**: 192.168.1.116
- **GPU**: RTX (CUDA-accelerated inference)
- **Connection**: gRPC over LAN (DHCP-reserved IP)
