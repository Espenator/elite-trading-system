# Perplexity Model Council — Consolidated Enhancement Prompt

> **Date:** 2026-03-05
> **Purpose:** Submit to Perplexity Model Council for 3 detailed architectural enhancement plans
> **Codebase:** [github.com/Espenator/elite-trading-system](https://github.com/Espenator/elite-trading-system)

---

## Context

You are advising on the **Embodier Trader** — a production algorithmic trading system at github.com/Espenator/elite-trading-system. The system runs a 17-agent council DAG (7 stages, parallel within stages), a Bayesian WeightLearner for self-learning agent weights, an OutcomeTracker feedback loop, Kelly criterion position sizing calibrated from real trade data, and ML models (XGBoost, LSTM, HMM) for signal generation. It trades via Alpaca Markets API with both live and shadow positions.

**Infrastructure:** Two PCs with NVIDIA RTX GPUs, gigabit internet, Ollama installed for local LLM inference. The owner also has access to Perplexity API and Claude API for cloud-based reasoning where it provides an edge over local models.

## Existing Architecture Highlights

- **Council Runner** (`backend/app/council/runner.py`): 7-stage DAG with 17 agents — Stage 1 perception agents (market, flow, social, news, YouTube, intermarket), Stage 2 technical agents (RSI, BBV, EMA trend, relative strength, cycle timing), Stage 3 hypothesis, Stage 4 strategy, Stage 5 risk+execution, Stage 6 critic, Stage 7 deterministic arbiter
- **WeightLearner** (`backend/app/council/weight_learner.py`): Bayesian updater — learning_rate=0.05, min_weight=0.2, max_weight=2.5, decay_rate=0.001. Agents that vote correctly gain weight, wrong agents get dampened. Normalizes to mean=1.0, persists to DuckDB
- **OutcomeTracker** (`backend/app/services/outcome_tracker.py`): Polls positions every 30s, computes PnL/R-multiple, feeds to feedback_loop and ML outcome_resolver, recomputes Kelly params from real win/loss history
- **BlackboardState** (`backend/app/council/blackboard.py`): Shared context passed through all agents

## Research Findings to Incorporate

### 1. TradingAgents Framework (UCLA/MIT)

Multi-agent LLM trading with Bull/Bear researcher agents engaging in structured debate, a risk management team, and traders synthesizing insights from debates. **Key insight:** agentic debate between opposing viewpoints significantly improves decision quality.

### 2. Bayesian Adversarial Robustness

Bayesian game-theoretic frameworks where a trading agent maintains beliefs over market macro state and trains against adversarial perturbations, achieving robust performance even during extreme events like COVID. **Key insight:** agents should maintain probabilistic beliefs about regime, not point estimates.

### 3. Fine-Grained Task Decomposition

Research shows finer-grained task assignment to trading agents yields statistically superior risk-adjusted returns vs coarse-grained approaches. Technical agent identified as primary performance driver.

### 4. Hybrid Local/Cloud LLM Routing (HERA Framework)

Demonstrates 30% cost reduction by routing 45% of subtasks to local SLMs while preserving accuracy within 2-5% of cloud-only. Routing thresholds: simple tasks → local small model, moderate → local large model, complex reasoning → cloud LLM.

### 5. Exponential Memory Architecture

Advanced agent memory uses tiered storage with abstraction layers that derive higher-order knowledge from concrete observations, forming operational heuristics and conceptual models. Neuromorphic-inspired spike-timing plasticity for adaptive knowledge retention.

### 6. RTX Local Inference Optimization

Ollama on RTX GPUs achieves 30% throughput boost with CUDA graph enablement and Flash Attention. Dual RTX configs can match H100 performance for 70B models at 25% cost.

---

## TASK

Provide **3 detailed, actionable responses** for how to enhance the Embodier Trader codebase. Each response should be a complete architectural enhancement plan with specific code-level changes referencing our existing modules. Keep these constraints:

### Enhancement 1: Hybrid LLM Integration

Design an intelligent router that sends perception-stage agents (news analysis, social sentiment, YouTube knowledge) to local Ollama models (fast, private, zero-cost) for initial processing, but escalates to Perplexity API for real-time web-grounded research and Claude API for complex multi-step reasoning (hypothesis generation, strategy formulation, critic evaluation). The router should track latency, accuracy, and cost per call, learning over time which tasks benefit from cloud vs local. Modify `council_runner.py` to support this hybrid execution.

### Enhancement 2: Exponential Knowledge Growth ("Cognitive 1000")

Transform the WeightLearner from simple Bayesian weight updates into a compound intelligence system where:

- **(a)** Agents develop persistent memory banks that accumulate market pattern knowledge across thousands of trades
- **(b)** Meta-learning layers abstract recurring patterns into transferable heuristics (e.g., "RSI divergence in trending regimes predicts reversals 73% of the time")
- **(c)** A knowledge graph connects agent insights across time, creating exponential compounding of institutional knowledge

Design the memory architecture to use DuckDB for fast retrieval and the RTX GPUs for embedding similarity search.

### Enhancement 3: Adversarial Robustness + Structured Debate

Add a Bull/Bear debate mechanism before the arbiter stage where opposing agents argue for and against the trade thesis using evidence from the blackboard. Implement a Bayesian belief system in the regime agent that maintains probability distributions over market states rather than point classifications. Add a "red team" shadow agent that stress-tests every decision against adversarial scenarios (flash crash, liquidity gap, correlated drawdown). Feed debate quality scores back into the WeightLearner.

---

## Required Output Format

For each response, specify:

- **Exact files to modify/create** — referencing `backend/app/council/`, `backend/app/services/`, etc.
- **Data structures and schemas** — DuckDB tables, dataclasses, Pydantic models
- **Integration points** with existing OutcomeTracker, WeightLearner, and BlackboardState
- **How the dual RTX PCs and gigabit internet are leveraged**
- **Expected performance improvement rationale**
