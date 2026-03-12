# Council Agents — Status Report (March 12, 2026)

Single source: `backend/app/council/registry.py`, `task_spawner.py`, `runner.py`, and `council/agents/` files.

---

## Summary

| Metric | Value |
|--------|--------|
| **Total agents (registry)** | 35 |
| **Agent files in `council/agents/`** | 32 (unique) |
| **Stages** | 7 + 1 background |
| **Registered in TaskSpawner** | 29 (17 core + 12 academic edge) |
| **Invoked in runner** | All 35 (Stage 1–6 via spawner/debate; Stage 7 arbiter; alt_data post-arbiter) |
| **Have `evaluate` / `evaluate_debate`** | All 32 agent files |

---

## By Stage

### Stage 1 — Perception + Academic Edge (13 agents)

| Agent | File | Wired in runner | TaskSpawner | Status |
|-------|------|-----------------|-------------|--------|
| market_perception | market_perception_agent.py | ✅ | ✅ | Done — features, volume, returns |
| flow_perception | flow_perception_agent.py | ✅ | ✅ | Done — PCR, flow |
| regime | regime_agent.py | ✅ | ✅ | Done — regime alignment |
| social_perception | social_perception_agent.py | ✅ | ✅ | Done — social thresholds |
| news_catalyst | news_catalyst_agent.py | ✅ | ✅ | Done — keyword matching |
| youtube_knowledge | youtube_knowledge_agent.py | ✅ | ✅ | Done — concept matching |
| intermarket | intermarket_agent.py | ✅ | ✅ | Done — cross-market |
| gex_agent | gex_agent.py | ✅ | ✅ | Done — GEX/options flow |
| insider_agent | insider_agent.py | ✅ | ✅ | Done — insider filings |
| finbert_sentiment_agent | finbert_sentiment_agent.py | ✅ | ✅ | Done — FinBERT sentiment |
| earnings_tone_agent | earnings_tone_agent.py | ✅ | ✅ | Done — earnings tone NLP |
| dark_pool_agent | dark_pool_agent.py | ✅ | ✅ | Done — dark pool / DIX |
| macro_regime_agent | macro_regime_agent.py | ✅ | ✅ | Done — macro/VIX regime |

### Stage 2 — Technical + Data Enrichment (8 agents)

| Agent | File | Wired in runner | TaskSpawner | Status |
|-------|------|-----------------|-------------|--------|
| rsi | rsi_agent.py | ✅ | ✅ | Done — RSI multi-timeframe |
| bbv | bbv_agent.py | ✅ | ✅ | Done — Bollinger / mean reversion |
| ema_trend | ema_trend_agent.py | ✅ | ✅ | Done — EMA cascade |
| relative_strength | relative_strength_agent.py | ✅ | ✅ | Done — sector relative strength |
| cycle_timing | cycle_timing_agent.py | ✅ | ✅ | Done — cycle timing |
| supply_chain_agent | supply_chain_agent.py | ✅ | ✅ | Done — supply chain KG |
| institutional_flow_agent | institutional_flow_agent.py | ✅ | ✅ | Done — 13F flow |
| congressional_agent | congressional_agent.py | ✅ | ✅ | Done — congressional trading |

### Stage 3 — Hypothesis + Memory (2 agents)

| Agent | File | Wired in runner | TaskSpawner | Status |
|-------|------|-----------------|-------------|--------|
| hypothesis | hypothesis_agent.py | ✅ | ✅ | Done — brain gRPC / LLM |
| layered_memory_agent | layered_memory_agent.py | ✅ | ✅ | Done — FinMem / memory recall |

### Stage 4 — Strategy (1 agent)

| Agent | File | Wired in runner | TaskSpawner | Status |
|-------|------|-----------------|-------------|--------|
| strategy | strategy_agent.py | ✅ | ✅ | Done — entry/exit/sizing |

### Stage 5 — Risk + Execution + Portfolio (3 agents)

| Agent | File | Wired in runner | TaskSpawner | Status |
|-------|------|-----------------|-------------|--------|
| risk | risk_agent.py | ✅ | ✅ | Done — VETO agent |
| execution | execution_agent.py | ✅ | ✅ | Done — VETO agent |
| portfolio_optimizer_agent | portfolio_optimizer_agent.py | ✅ | ✅ | Done — portfolio constraints |

### Stage 5.5 — Debate + Red Team (3 agents)

| Agent | File | Wired in runner | TaskSpawner | Status |
|-------|------|-----------------|-------------|--------|
| bull_debater | bull_debater.py | ✅ (via DebateEngine) | ❌ | Done — debate_engine calls evaluate_debate |
| bear_debater | bear_debater.py | ✅ (via DebateEngine) | ❌ | Done — debate_engine calls evaluate_debate |
| red_team | red_team_agent.py | ✅ (stress_test) | ❌ | Done — runner calls stress_test, vote appended |

Note: bull_debater and bear_debater are not in TaskSpawner; they are invoked inside `debate_engine.run_debate()`. Red team is invoked via `red_team_agent.stress_test()` and one vote is appended. Debate can also append a `debate_engine` veto vote.

### Stage 6 — Critic (1 agent)

| Agent | File | Wired in runner | TaskSpawner | Status |
|-------|------|-----------------|-------------|--------|
| critic | critic_agent.py | ✅ | ✅ | Done — postmortem / R-multiple |

### Stage 7 — Arbiter (1)

| Agent | File | Wired in runner | TaskSpawner | Status |
|-------|------|-----------------|-------------|--------|
| arbiter | arbiter.py (council/) | ✅ | N/A | Done — Bayesian-weighted BUY/SELL/HOLD |

### Background — Enrichment (1 agent)

| Agent | File | Wired in runner | TaskSpawner | Status |
|-------|------|-----------------|-------------|--------|
| alt_data_agent | alt_data_agent.py | ✅ (post-arbiter) | ✅ | Done — background enrichment |

---

## What Is Done

- All 35 agents are defined in `registry.AGENTS` and in the DAG.
- All 32 agent modules in `council/agents/` have `NAME` and either `evaluate()` or `evaluate_debate()`.
- All Stage 1–4 and Stage 5–6 agents are registered in TaskSpawner and invoked from runner (Stage 1–2 can run distributed on PC2 when brain is available).
- Debate (bull/bear/red_team) is invoked from runner via DebateEngine and `red_team_agent.stress_test()`; votes are merged into `all_votes`.
- Arbiter runs in runner after Stage 6; alt_data runs post-arbiter (background).
- Weights and thresholds are in `agent_config.py` and `weight_learner.DEFAULT_WEIGHTS`; regime-stratified weights in WeightLearner.
- Council health uses `total_registered=35` and classifies degraded/critical; debate history is written to DuckDB when debate runs.

---

## What Is Not Done / Gaps

- **Supplemental agent weights (Issue #52):** Six supplemental agents (RSI, BBV, EMA trend, relative_strength, cycle_timing, intermarket) have default weights in `weight_learner.DEFAULT_WEIGHTS` and in `agent_config`; no open “not implemented” gap. Issue #52 may refer to tuning or ELO exposure — not “not wired”.
- **Unusual Whales → agents:** MessageBus topics `unusual_whales.flow`, `.congress`, `.darkpool`, `.insider` are PUBLISH_ONLY (no subscribers in main). Agents that need UW data (e.g. dark_pool_agent, congressional_agent, gex_agent, insider_agent) get data via feature aggregator / blackboard / services, not necessarily from those topics. So “UW not wired to MessageBus consumers” is a data-path gap, not an “agent not implemented” gap.
- **Debate votes in outcome.resolved:** Bull/bear/red_team votes are not currently included in the outcome.resolved payload for WeightLearner/SelfAwareness; learning uses the 13-agent fallback when agent_votes is empty (see FINAL-PRE-PRODUCTION-AUDIT).
- **Agent-specific tests:** No single test file that runs every agent’s `evaluate()`; coverage is via council integration tests (e.g. test_council_agents_full, test_council_dag_integration).

---

## Quick Reference: Registry vs Runner

- **Registry** (`registry.py`): `AGENTS` (35), `DAG_STAGES` (8 stages). Used by API, WeightLearner, UI.
- **Runner** (`runner.py`): Builds stage configs from lists; Stage 1 uses `_stage1_agent_types` (13); Stage 2 uses `stage2_configs` (8); Stage 5.5 uses DebateEngine + red_team; Stage 7 is arbitrate().
- **TaskSpawner** (`task_spawner.py`): Registers 17 core + 12 academic edge (29). Bull/bear/red_team are not registered; they are called by debate_engine and runner.

---

*Generated from codebase state March 12, 2026.*
