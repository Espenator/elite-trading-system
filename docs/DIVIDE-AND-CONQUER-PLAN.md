# Divide & Conquer — Two-PC Production Sprint

> **Date:** March 11, 2026 | **Updated:** March 11, 2026 (evening)
> **Goal:** Get Embodier Trader v5.0 to autonomous 24/7 paper trading
> **Base plan:** PLAN.md (8 phases, 15-23 sessions estimated)
> **Strategy:** Split work by PC role. Run in parallel. Halve the timeline.
> **Progress:** Phase 1 COMPLETE. **Lane A COMPLETE** (A0-A9). **Lane B COMPLETE** (B1-B9). **Phase A COMPLETE** (Stop the Bleeding). Now: Phase B+D (PC2) + Phase C (PC1) in parallel.

---

## PC Roles Recap

| | ESPENMAIN (PC1) | ProfitTrader (PC2) |
|---|---|---|
| **IP** | 192.168.1.105 | 192.168.1.116 |
| **Strengths** | Primary backend, frontend, DuckDB, Alpaca execution | RTX 4080 GPU, Ollama (11 models), Brain gRPC, ML training |
| **Claude instance** | Frontend + API wiring, UI controls, council agents | LLM pipeline, ML engine, Brain Service, GPU compute tasks |
| **Port** | 8001 (backend), 3000/5173 (frontend) | 8001 (backend), 50051 (brain gRPC), 11434 (ollama) |
| **Redis** | Hosts Redis broker (6379) | Connects to PC1 Redis |

---

## Sprint Lanes (Parallel Execution)

### LANE A: ESPENMAIN — Frontend & Backend Wiring

**Owner:** PC1 Claude
**Phases:** 2 (Frontend Wiring), 6 (UI Controls), 7 (Monitoring)

| # | Task | Phase | Est. | Status |
|---|------|-------|------|--------|
| A0 | Endpoint audit + route mismatch fixes + scraper services | 2.0 | 1 session | **DONE** |
| A1 | Dashboard page: wire all 18 API calls, fix response shapes | 2.1 | 1 session | **DONE** |
| A2 | Agent Command Center: wire 16 API calls across 10 tabs | 2.2 | 2 sessions | **DONE** |
| A3 | Signal Intelligence + Sentiment: verify all endpoints | 2.3-2.4 | 1 session | **DONE** |
| A4 | Data Sources + ML Brain: add alias fields, fix KPIs | 2.5-2.6 | 1 session | **DONE** |
| A5 | Screener, Backtest, Performance, Market Regime pages | 2.7-2.10 | 2 sessions | **DONE** |
| A6 | Trades, Risk, Trade Execution, Settings pages | 2.11-2.14 | 2 sessions | **DONE** |
| A7 | Wire all UI buttons to real backend actions | 6.1-6.2 | 2 sessions | **DONE** |
| A8 | Slack notifications + TradingView webhook receiver | 7.1 | 1 session | **DONE** |
| A9 | Health monitoring + auto-restart script | 7.2-7.3 | 1 session | **DONE** |

**Total: ~13 sessions — ALL COMPLETE**

---

### LANE B: ProfitTrader — ML, LLM, Council & Auto-Trade

**Owner:** PC2 Claude (THIS MACHINE)
**Phases:** 3 (Council Agents), 4 (Auto-Trade), 5 (Data Firehose)

| # | Task | Phase | Est. |
|---|------|-------|------|
| B1 | Audit all 35 council agents — verify real data, fix neutrals | 3.1 | 2 sessions | **DONE** |
| B2 | Brain Service LLM integration — test InferCandidateContext | 3.2 | 1 session | **DONE** |
| B3 | Fix agents returning neutral votes (add fallback data fetching) | 3.2 | 1 session | **DONE** |
| B4 | Auto-trade loop: enable OrderExecutor, test full pipeline | 4.1 | 2 sessions | **DONE** |
| B5 | PositionManager: trailing stops, time exits, partial TP | 4.2 | 1 session | **DONE** (pre-existing) |
| B6 | OutcomeTracker + WeightLearner feedback loop | 4.3 | 1 session | **DONE** (pre-existing) |
| B7 | Risk guardrails: circuit breaker, heat limits, sector caps | 4.4 | 1 session | **DONE** |
| B8 | Off-hours data: pre-market, after-hours, overnight, weekend | 5.2 | 1 session | **DONE** |
| B9 | Data source health monitoring + Slack alerts | 5.3 | 1 session | **DONE** |

**Total: ~13 sessions — ALL COMPLETE**

---

## Dependency Graph

```
                    ┌─────────────────────────────────┐
                    │     BOTH: Phase 1 (COMPLETE)     │
                    │     Backend health, event loop    │
                    └────────────┬────────────────────┘
                                 │
               ┌─────────────────┴─────────────────────┐
               │                                       │
    ┌──────────▼──────────┐              ┌─────────────▼────────────┐
    │   LANE A: ESPENMAIN  │              │    LANE B: ProfitTrader   │
    │                      │              │                          │
    │ A1-A6: Page wiring   │              │ B1-B3: Council agents    │
    │  (no dependency on   │              │  (needs Ollama + Brain)  │
    │   Lane B)            │              │                          │
    │         │            │              │         │                │
    │ A7: UI buttons       │              │ B4-B7: Auto-trade loop   │
    │  (after A1-A6)       │              │  (needs B1-B3 complete)  │
    │         │            │              │         │                │
    │ A8-A9: Monitoring    │              │ B8-B9: Data firehose     │
    │  (after A7)          │              │  (parallel with B4-B7)   │
    └──────────┬───────────┘              └────────────┬─────────────┘
               │                                       │
               └─────────────────┬─────────────────────┘
                                 │
                    ┌────────────▼────────────────────┐
                    │     BOTH: Phase 8 (Final)       │
                    │  Electron packaging, deployment  │
                    │  AUTO_EXECUTE_TRADES=true         │
                    └─────────────────────────────────┘
```

---

## Phase 2: Deep Audit Enhancement Lanes (March 11, 2026 — Evening)

> **Merged:** ESPENMAIN's `debug-production-readiness` branch (Phase A complete, 65→75% ready)
> **Lane B (B1-B9)** merged alongside. All original lanes done. Now tackling deep audit phases.

### Assignment: Who Does What

| Phase | Owner | Description | Est. Sessions | Status |
|-------|-------|-------------|---------------|--------|
| **Phase A** | ESPENMAIN | Stop the Bleeding — critical fixes | 2-3 | **DONE** |
| **Phase B** | **ProfitTrader (PC2)** | Unlock Alpha — remove profit blockers | 3-4 | **IN PROGRESS** |
| **Phase C** | **ESPENMAIN (PC1)** | Sharpen the Brain — weight learner, calibration, audit trail | 3-4 | **NOT STARTED** |
| **Phase D** | **ProfitTrader (PC2)** | Continuous Intelligence — backfill, rate limiting, resilience | 3-4 | **NOT STARTED** |
| **Phase E** | **Both** | Production Hardening — E2E test, desktop packaging | 2-3 | **NOT STARTED** |

### Phase B Tasks (ProfitTrader — THIS SESSION)

| # | Task | Key Files | Status |
|---|------|-----------|--------|
| B1 | Calibrate signal gate threshold (regime-adaptive 55/65/75) | council_gate.py | |
| B2 | Fix short signal generation (remove `100 - blended` inversion) | signal_engine.py | |
| B3 | Smart cooldown (regime-adaptive 30s/120s/300s) | council_gate.py | |
| B4 | Priority queue for concurrency (sort by score, max 5) | council_gate.py | |
| B5 | Limit orders for size (>$5K = limit at NBBO mid) | order_executor.py | |
| B6 | Partial fill re-execution (resubmit remainder, max 3 retries) | order_executor.py | |
| B7 | Fix viability gate (use real win rate, not signal score) | order_executor.py | |
| B8 | Fix portfolio heat (use buying_power / initial equity) | order_executor.py | |

### Phase C Tasks (ESPENMAIN)

| # | Task | Key Files |
|---|------|-----------|
| C1 | Fix weight learner confidence floor (0.5→0.2) + regime-stratified | weight_learner.py |
| C2 | Add confidence calibration (Brier score per agent) | weight_learner.py |
| C3 | Wire debate votes to learning | runner.py |
| C4 | Council decision audit trail (DuckDB log + API) | council_gate.py, new endpoint |
| C5 | Fix trade stats R-multiple (real stop, not assumed 2%) | trade_stats_service.py |
| C6 | Wire homeostasis to sizing | homeostasis.py, order_executor.py |
| C7 | Regime-adaptive thresholds (RSI, Kelly, max trades, arbiter) | multiple |
| C8 | Data source MessageBus publishing (FRED, EDGAR, etc.) | multiple services |
| C9 | Silent failure alerting (degraded council runs) | council_gate.py, feature_aggregator.py |

### Phase D Tasks (ProfitTrader — AFTER Phase B)

| # | Task | Key Files |
|---|------|-----------|
| D1 | Autonomous data backfill (252 days on startup + daily 4:30AM) | data_ingestion.py |
| D2 | Rate limiting framework (per-service asyncio.Semaphore) | new utility |
| D3 | MessageBus resilience (dead-letter queue, alert at 80%) | message_bus.py |
| D4 | Scraper resilience (session refresh, circuit breaker) | benzinga, squeezemetrics |
| D5 | Pre-market / after-hours scanning (4AM gap scanner, 4:30PM earnings) | new service |

---

## ARCHIVED: Original ProfitTrader Session Plans (COMPLETED)



### Session 1: Council Agent Audit (B1 — Part 1)

**Goal:** Identify which of the 35 agents are actually producing real votes vs neutral fallbacks.

1. Read `backend/app/council/runner.py` — understand the vote collection flow
2. Read each agent in `backend/app/council/agents/` — check data sources
3. For each agent, categorize:
   - **GREEN**: Gets real data, produces meaningful votes
   - **YELLOW**: Has data source but sometimes falls back to neutral
   - **RED**: Always returns neutral (missing data, stubbed, or erroring)
4. Fix RED agents that have available data sources (Alpaca, DuckDB, UW, Finviz)
5. Log which agents need external data we don't have yet

### Session 2: Brain Service LLM Pipeline (B2-B3)

**Goal:** Get the Brain Service actually producing LLM-backed council votes.

1. Test `InferCandidateContext` gRPC call with real market data
2. Test `CriticPostmortem` with a sample trade outcome
3. Wire `hypothesis` agent to use Brain Service instead of fallback
4. Wire `strategy` agent to use LLM for thesis generation
5. Benchmark inference latency (target: <2s per call on RTX 4080)

### Session 3: Auto-Trade Loop (B4)

**Goal:** Complete the bar → signal → council → order → outcome pipeline.

1. Enable `AUTO_EXECUTE_TRADES=true` in paper mode
2. Submit a manual signal to council, verify 35-agent vote
3. Verify OrderExecutor creates a real Alpaca paper order
4. Verify bracket orders (stop-loss + take-profit) are placed
5. Wait for fill, verify OutcomeTracker records it
6. Verify WeightLearner updates Bayesian weights

---

## Sync Points (When Both PCs Must Coordinate)

| Milestone | What Happens | When |
|-----------|-------------|------|
| **Council votes visible in UI** | Lane A wires Agent Command Center tab to show real votes from Lane B's fixed agents | After A2 + B1 |
| **Trade execution end-to-end** | Lane A wires Trade Execution page, Lane B enables auto-trade loop | After A6 + B4 |
| **LLM Brain visible in UI** | Lane A wires ML Brain page, Lane B has working inference pipeline | After A4 + B2 |
| **Production go-live** | Both lanes merge, full smoke test, enable AUTO_EXECUTE | After all A + all B |

---

## Redis Bridge — How PCs Stay in Sync

The MessageBus bridges these topics via Redis (`redis://192.168.1.105:6379/0`):

| Topic | Producer | Consumer | Purpose |
|-------|----------|----------|---------|
| `signal.generated` | PC1 SignalEngine | PC2 Council | Signals trigger council evaluation |
| `council.verdict` | PC2 Council | PC1 UI + OrderExecutor | Council decisions flow to execution |
| `order.submitted` | PC1 OrderExecutor | PC2 OutcomeTracker | Track order lifecycle |
| `order.filled` | PC1 Alpaca | PC2 WeightLearner | Update agent weights on fills |
| `cluster.telemetry` | Both | Both | GPU utilization, health |
| `swarm.idea` | PC2 Scouts | PC1 SignalEngine | Discovery feeds signal pipeline |
| `model.updated` | PC2 ML | PC1 SignalEngine | New model deployed |

---

## Success Criteria

| Metric | Target | How to Verify |
|--------|--------|---------------|
| All 14 frontend pages show real data | 100% | Manual walkthrough |
| Council produces non-neutral verdicts | >80% of votes | `/api/v1/council/latest` |
| Auto-trade loop completes full cycle | 1+ paper trade | Alpaca dashboard |
| Brain Service inference latency | <2s per call | Brain Service logs |
| System uptime without freeze | >24 hours | `/health` endpoint |
| Data firehose running 24/7 | All sources green | `/api/v1/data-sources/` |
| Redis cross-PC messaging | <10ms latency | MessageBus logs |

---

## Timeline Estimate

| Week | ESPENMAIN | ProfitTrader |
|------|-----------|-------------|
| Week 1 | A1-A4 (Dashboard, ACC, Signals, Data) | B1-B3 (Council audit, Brain LLM) |
| Week 2 | A5-A6 (Remaining pages) | B4-B5 (Auto-trade, Position mgmt) |
| Week 3 | A7 (UI buttons) | B6-B7 (Outcome tracking, Risk) |
| Week 4 | A8-A9 (Slack, monitoring) | B8-B9 (Data firehose, health) |
| Week 5 | Joint: Phase 8 (Electron, deployment, go-live) |

**Target: Production-ready paper trading in 5 weeks with parallel execution.**
Without parallel execution this would be 8-10 weeks.
