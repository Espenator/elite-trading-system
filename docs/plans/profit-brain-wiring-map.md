# Profit Brain — Wiring Map (2026-03-10)

## Topic publishers and consumers

| Topic | Publishers | Consumers |
|-------|-------------|-----------|
| `market_data.bar` | AlpacaStreamManager, streaming_discovery, firehose router | EventDrivenSignalEngine, OutcomeTracker (via PriceCache), idea triage |
| `market_data.quote` | (Alpaca/ingestion) | PriceCacheService |
| `signal.generated` | EventDrivenSignalEngine, HyperSwarm, TurboScanner, news_aggregator | CouncilGate, council_invocation fallback, UnifiedProfitEngine, WS bridge |
| `swarm.idea` | Firehose agents, DiscordSwarmBridge, streaming_discovery, pattern_library, news_aggregator | IdeaTriageService, SwarmSpawner, HyperSwarm |
| `council.verdict` | CouncilGate (single canonical), council_invocation (non-executable) | OrderExecutor, WS bridge |
| `order.submitted` | OrderExecutor (live + shadow) | OutcomeTracker |
| `order.filled` | OrderExecutor (_poll_for_fill) | OutcomeTracker |
| `outcome.resolved` | OutcomeTracker (_resolve_position) | main._on_outcome_resolved → WeightLearner, SelfAwareness |

## Key flows

1. **Signal → Council → Order**: `signal.generated` → CouncilGate → run_council() → `council.verdict` → OrderExecutor → `order.submitted` (and optionally Alpaca).
2. **Outcome feedback**: OrderExecutor submits → OutcomeTracker tracks position → on close, OutcomeTracker publishes `outcome.resolved` → WeightLearner.update_from_outcome (only if not censored), SelfAwareness, feedback_loop.
3. **Kelly stats**: OutcomeTracker keeps `resolved_history` in config (and _recompute_kelly_params); TradeStatsService reads DuckDB `trade_outcomes`. Censored outcomes must be excluded from both for learning integrity.
4. **WebSocket**: main.py `websocket_endpoint` accepts connections, parses subscribe/unsubscribe; broadcast_ws(channel, data) sends only to subscribers of that channel (websocket_manager).
