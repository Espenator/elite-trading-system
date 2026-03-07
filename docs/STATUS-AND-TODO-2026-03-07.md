# Embodier Trader - Status & TODO Update

## Date: March 7, 2026
## Author: Claude (Senior Engineering Partner) + Espen
## Repository: github.com/Espenator/elite-trading-system
## Version: 3.5.0-dev (Continuous Discovery Architecture)

---

## EXECUTIVE SUMMARY

**ARCHITECTURE PIVOT: From periodic scanning to continuous real-time discovery.**

A full codebase audit revealed the system is 73% analyst, 27% scout. The 17-agent council brain is being starved of ideas — HyperSwarm can process 40 signals/second but gets fed a burst every 60s then sits idle. TurboScanner polls stale DuckDB data. MarketWideSweep runs every 4 hours. UW agents poll REST every 90-900s. The entire market could move while we wait.

**Decision**: Invert the ratio. Build a continuous discovery firehose. Every agent scouts AND analyzes. The brain is always being fed.

**Tracking**: GitHub Issue #38 — Continuous Discovery Architecture

---

## WHAT WAS DONE (Mar 7 Session)

### Integration Sprint (commit 385c7a5)
- [x] Fixed async/sync DuckDB calls across 4 service files
- [x] Wired knowledge layer (MemoryBank, HeuristicEngine) into startup
- [x] Added feedback loop: OutcomeTracker -> heuristic extraction -> knowledge graph
- [x] Restructured services into sub-packages with zero import breakage

### Architecture Audit & Discovery Plan
- [x] Full audit of signal engine, ML pipeline, council intelligence, data sources
- [x] Mapped exact flow: symbol exists in market -> enters council evaluation
- [x] Identified bottlenecks: 8000 symbols scanned, only 10-20 reach council per cycle
- [x] Created 8-enhancement plan for continuous discovery (Issue #38)
- [x] Updated all repo documentation (this file, project_state.md, AI-CONTEXT-GUIDE.md, REPO-MAP.md)

---

## CURRENT STATE

### What's Working
| Component | Status | Notes |
|-----------|--------|-------|
| CI | GREEN | 151 tests, Run #452 |
| Frontend | 14/14 pages COMPLETE | Pixel-matched to mockups |
| Council DAG | 17 agents, 7 stages | Bayesian weight learning active |
| Event Pipeline | Connected | SignalEngine -> CouncilGate -> Council -> OrderExecutor |
| Knowledge Layer | Wired | MemoryBank + HeuristicEngine + KnowledgeGraph |
| Outcome Tracking | Working | Feeds weight learner + heuristic extraction |
| TurboScanner | Working | 10 parallel screens, 8000+ symbols/cycle |
| HyperSwarm | Working | 50 workers, Ollama triage |
| Safety | Working | CircuitBreaker + Homeostasis + Veto agents |

### What's Broken / Missing
| Issue | Impact | Priority |
|-------|--------|----------|
| All discovery is polling (60-900s) | Missing real-time opportunities | CRITICAL |
| No streaming symbol discovery | Blind to intraday events | CRITICAL |
| HyperSwarm fed in bursts, idle between | 80% worker idle time | HIGH |
| Universe is semi-static (55 Tier 1) | Missing new opportunities | HIGH |
| Council has one speed (17 agents for everything) | Bottleneck at 20 concurrent | HIGH |
| 17 council agents only activate when handed symbols | Passive between evaluations | MEDIUM |
| No multi-timeframe scanning | Missing intraday setups | MEDIUM |
| No feedback-driven discovery tuning | Scouts don't learn from outcomes | MEDIUM |

---

## ROADMAP: Multi-PC Compute Infrastructure (Issue #39) — PREREQUISITE

### Phase 0: Compute Infrastructure (Week 0-1)
- [ ] **E0.1**: AlpacaKeyPool — Multi-key management with role assignment (trading, discovery_a, discovery_b)
- [ ] **E0.2**: AlpacaStreamManager — Multi-WebSocket orchestrator (1 stream per key, 1000+ symbols)
- [ ] **E0.3**: OllamaNodePool — Shared Ollama pool extracted from HyperSwarm (2-node, health checks)
- [ ] **E0.4**: Enable Brain Service — Fix config, activate gRPC on PC2
- [ ] **E0.5**: NodeDiscovery — Auto-detect PC2, graceful 1-PC fallback
- [ ] **E0.6**: Unusual Whales Optimization — 30s polling, congress/insider/darkpool endpoints
- [ ] **E0.7**: Finviz Elite Optimization — Intraday timeframes, parallel presets, retry logic
- [ ] **E0.8**: Config Updates — Multi-key env vars, cluster settings

---

## ROADMAP: Continuous Discovery Architecture (Issue #38)

### Phase 1: Foundation — Continuous Feed (Week 1-2)
- [ ] **E1**: Streaming Discovery Engine — Alpaca `*` trade stream, news stream, faster UW polling, dynamic universe manager
- [ ] **E2**: 12 Dedicated Scout Agents — FlowHunter, Insider, Congress, Gamma, News, Sentiment, Macro, Earnings, SectorRotation, ShortSqueeze, IPO, CorrelationBreak

### Phase 2: Scale — Real-Time Processing (Week 3-4)
- [ ] **E3**: HyperSwarm Continuous Triage — priority queue, adaptive threshold, sub-swarm spawning
- [ ] **E5**: Dynamic Universe — self-healing, sector-aware expansion, 500-2000 symbols active

### Phase 3: Architecture — Dual-Mode Everything (Week 5-6)
- [ ] **E4**: Multi-Tier Council — Fast (5 agents, <200ms) + Deep (17 agents, <2s)
- [ ] **E6**: Dual-Mode Agents — every analyst gets background scout mode

### Phase 4: Intelligence — Self-Evolving Discovery (Week 7-8)
- [ ] **E7**: Feedback-Driven Amplification — Signal DNA, win registry, scout priming
- [ ] **E8**: Multi-Timeframe Scanning — 5min/15min/1hr/daily/weekly parallel scan loops

### Success Metrics
| Metric | Current | Target |
|--------|---------|--------|
| Discovery latency | 60-900s | <1s |
| Signals/hour into brain | ~200 | ~2000+ |
| Council utilization | ~20% | ~80% |
| Active universe | 55-200 | 500-2000 |
| Scout/analyst ratio | 27/73 | 50/50 |

---

## PREVIOUS COMPLETIONS

### v3.4.0 (Mar 6) — Frontend Complete
- All 14 pages pixel-matched to mockups
- ACC rebuilt into 5 component files with 8 tabs
- 20 orphaned files cleaned up

### v3.2.0 (Mar 5) — Council Pipeline Connected
- CouncilGate bridges SignalEngine -> Council -> OrderExecutor
- Bayesian WeightLearner
- 151 tests passing

---

## BLOCKERS (Unchanged)
- [ ] **BLOCKER-1**: Start backend end-to-end (`uvicorn app.main:app`)
- [ ] **BLOCKER-2**: Establish WebSocket real-time connectivity
- [ ] **BLOCKER-3**: Add JWT authentication for live trading endpoints

---

## FILE REFERENCE

| Document | Path | What It Contains |
|----------|------|------------------|
| **This Status Doc** | `docs/STATUS-AND-TODO-2026-03-07.md` | Current priorities |
| **Discovery Issue** | GitHub Issue #38 | Full 8-enhancement plan |
| **Project State** | `project_state.md` | Architecture, roadmap, rules |
| **Previous Status** | `docs/STATUS-AND-TODO-2026-03-06.md` | Frontend completion details |
| **Audit Report** | `docs/MOCKUP-FIDELITY-AUDIT.md` | UI audit (all resolved) |
| **Design System** | `docs/UI-DESIGN-SYSTEM.md` | Colors, typography, layout |
