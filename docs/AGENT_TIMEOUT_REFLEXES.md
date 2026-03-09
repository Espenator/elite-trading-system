# Agent Timeout Reflexes

## Overview

The Agent Timeout Reflex system provides intelligent, adaptive timeout management for all council agents. It prevents slow or hanging agents from blocking council decisions while automatically learning from historical performance patterns.

## Architecture

### Brainstem Reflexes (<50ms)
Circuit Breaker checks run before the council DAG (see `circuit_breaker.py`):
- Flash crash detection
- VIX spike detection
- Drawdown limits
- Position limits
- Market hours check

### Agent Execution Timeouts (5-30s)
Timeout Reflex checks run during agent execution (see `timeout_reflex.py`):
- Tiered timeouts by agent stage
- Adaptive timeout adjustment based on p95 latency
- Automatic skip for repeatedly failing agents
- Rich telemetry and statistics

## Tiered Timeouts

Different agent stages have different timeout budgets:

| Stage | Agents | Timeout | Rationale |
|-------|--------|---------|-----------|
| 1: Perception | market_perception, flow_perception, regime, social, news, youtube, GEX, insider, sentiment, earnings, dark_pool, macro | 5s | Fast data lookups |
| 2: Technical | rsi, bbv, ema_trend, relative_strength, cycle_timing, supply_chain, institutional, congressional | 10s | Calculations |
| 3: Hypothesis | hypothesis, layered_memory | 15s | LLM inference |
| 4: Strategy | strategy | 12s | Complex decision logic |
| 5: Risk/Execution | risk, execution, portfolio_optimizer | 8s | Real-time critical |
| 6: Critic | critic | 12s | Postmortem analysis |
| Default | unknown agents | 30s | Fallback |

## Adaptive Timeout

After collecting at least 10 execution samples, the timeout manager automatically adjusts timeouts:

```
adaptive_timeout = p95_latency × 1.2
capped_timeout = min(adaptive_timeout, base_timeout × 2.0)
final_timeout = max(capped_timeout, base_timeout)
```

Example:
- Agent "market_perception" has base timeout of 5s
- After 20 executions, p95 latency is 3.5s
- Adaptive timeout = 3.5s × 1.2 = 4.2s
- Final timeout = max(4.2s, 5s) = 5s (stays at base)

If p95 grows to 6s:
- Adaptive timeout = 6s × 1.2 = 7.2s
- Final timeout = max(7.2s, 5s) = 7.2s (increases to 7.2s)
- Capped at max(10s) to prevent runaway timeouts

## Graceful Degradation

### Timeout Streaks
When an agent times out, its timeout_streak counter increments. On successful execution, it resets to 0.

### Automatic Skip
If an agent reaches 5 consecutive timeouts, it is automatically skipped:
- The agent is not executed
- A fallback vote is returned (hold, confidence=0.0)
- The council continues without waiting

### Recovery
Once a skipped agent successfully completes, its streak resets and normal execution resumes.

## Statistics Tracked

Per agent:
- `total_executions` - Total number of executions
- `total_timeouts` - Number of timeouts
- `total_errors` - Number of errors
- `timeout_rate` - Percentage of executions that timed out
- `timeout_streak` - Consecutive timeouts (resets on success)
- `p50_latency` - 50th percentile execution time (ms)
- `p95_latency` - 95th percentile execution time (ms)
- `avg_latency` - Average execution time (ms)
- `last_execution_ms` - Most recent execution time
- `last_timeout` - Timestamp of last timeout

Aggregate:
- `total_executions` - All executions across all agents
- `total_timeouts` - All timeouts across all agents
- `overall_timeout_rate` - System-wide timeout rate
- `agents_tracked` - Number of agents with statistics
- `agents_with_timeouts` - Number of agents that have timed out
- `agents_in_timeout_streak` - Number of agents currently in timeout streak
- `max_timeout_streak` - Highest timeout streak across all agents

## API Endpoints

### Get All Timeout Statistics
```
GET /api/v1/agents/timeout/stats
```

Response:
```json
{
  "aggregate": {
    "total_executions": 1234,
    "total_timeouts": 45,
    "overall_timeout_rate": 0.036,
    "agents_tracked": 35,
    "agents_with_timeouts": 8,
    "agents_in_timeout_streak": 2,
    "max_timeout_streak": 3
  },
  "agents": {
    "market_perception": {
      "total_executions": 100,
      "total_timeouts": 2,
      "timeout_rate": 0.02,
      "p50_latency_ms": 450,
      "p95_latency_ms": 1200,
      "avg_latency_ms": 580,
      "current_timeout_s": 5.0
    },
    ...
  },
  "timestamp": "2026-03-09T03:45:00Z"
}
```

### Get Agent-Specific Statistics
```
GET /api/v1/agents/timeout/stats/{agent_name}
```

### Set Manual Timeout Override
```
POST /api/v1/agents/timeout/override/{agent_name}
Body: timeout_seconds=20.0
```

Use cases:
- Debugging a slow agent
- Temporarily increase timeout during high load
- Testing timeout behavior

### Clear Timeout Override
```
DELETE /api/v1/agents/timeout/override/{agent_name}
```

### Reset Statistics
```
POST /api/v1/agents/timeout/reset
Body (optional): agent_name="market_perception"
```

Resets all statistics for one agent or all agents (if agent_name omitted).

## Configuration

All timeout settings are in `backend/app/council/agent_config.py`:

```python
# Timeout Reflex Configuration
"timeout_adaptive_enabled": True,
"timeout_adaptive_multiplier": 1.2,  # Add 20% buffer to p95 latency
"timeout_min_samples": 10,  # Minimum executions before using adaptive timeout
"timeout_skip_streak_threshold": 5,  # Skip agent after this many consecutive timeouts
"timeout_tier_perception": 5.0,  # seconds
"timeout_tier_technical": 10.0,
"timeout_tier_hypothesis": 15.0,
"timeout_tier_strategy": 12.0,
"timeout_tier_risk_execution": 8.0,
"timeout_tier_critic": 12.0,
"timeout_tier_default": 30.0,
```

These can be overridden via the settings service under the "council" category.

## Usage in Code

### TaskSpawner (Automatic)
The timeout reflex system is automatically used by TaskSpawner. No code changes needed.

```python
from app.council.task_spawner import TaskSpawner
from app.council.blackboard import BlackboardState

blackboard = BlackboardState(symbol="AAPL", raw_features={})
spawner = TaskSpawner(blackboard)
spawner.register_all_agents()

# Timeouts handled automatically
vote = await spawner.spawn("market_perception", "AAPL")
```

### Manual Timeout Manager Access
```python
from app.council.reflexes.timeout_reflex import get_timeout_manager

tm = get_timeout_manager()

# Get adaptive timeout for an agent
timeout = tm.get_timeout("market_perception")

# Record execution (done automatically by TaskSpawner)
tm.record_execution("market_perception", elapsed_ms=450, timed_out=False)

# Check if agent should be skipped
if tm.should_skip_agent("slow_agent"):
    print("Agent is being skipped due to repeated timeouts")

# Get statistics
stats = tm.get_stats("market_perception")
print(f"Timeout rate: {stats['timeout_rate']:.1%}")
```

## Monitoring & Alerting

### Dashboard Integration
Frontend can display:
- Real-time timeout rate per agent
- Timeout streak indicators (warning at 3, critical at 5)
- p95 latency trends
- Agents currently being skipped

### Log Messages
```
WARNING: Agent hypothesis timed out after 15234ms (limit=15.0s)
WARNING: Agent hypothesis has 3 consecutive timeouts (streak=3, rate=12.5%)
ERROR: Agent hypothesis has 5 consecutive timeouts! Consider increasing timeout or investigating issue.
WARNING: Skipping agent hypothesis due to 5 consecutive timeouts
```

### WebSocket Events
Timeout events are broadcast on the "agents" channel:
```json
{
  "type": "timeout_override",
  "agent_name": "hypothesis",
  "timeout_seconds": 20.0
}
```

## Best Practices

1. **Monitor timeout rates** - Agents with >5% timeout rate need investigation
2. **Check timeout streaks** - Any streak >2 indicates a problem
3. **Review p95 latency** - If p95 >> base timeout, increase tier timeout
4. **Use overrides sparingly** - Prefer fixing slow agents over increasing timeouts
5. **Reset stats after changes** - After fixing an agent, reset its stats to measure improvement
6. **Watch for cascades** - Multiple agents timing out simultaneously suggests system-wide issue (CPU, network, external API)

## Troubleshooting

### Agent constantly times out
1. Check `GET /timeout/stats/{agent_name}` for p95 latency
2. If p95 > base timeout, temporarily increase with POST /timeout/override
3. Investigate why agent is slow:
   - External API latency (use caching)
   - Complex computation (optimize algorithm)
   - LLM inference (use faster model or reduce context)
4. Fix root cause and DELETE /timeout/override
5. POST /timeout/reset to clear statistics

### Multiple agents timing out
1. Check system resources (CPU, memory, network)
2. Check external API status (Alpaca, Unusual Whales, Finviz, etc.)
3. Review homeostasis vitals (`GET /api/v1/cns/homeostasis/vitals`)
4. Consider reducing concurrent agent execution

### Adaptive timeout too aggressive
1. Increase `timeout_adaptive_multiplier` from 1.2 to 1.5
2. Increase `timeout_min_samples` from 10 to 20 (more conservative)
3. Or disable adaptive: `timeout_adaptive_enabled: False`

## Future Enhancements

- **Timeout trend analysis** - Detect gradual degradation over time
- **Automatic alerts** - Notify when agent consistently near timeout
- **ML-based prediction** - Predict optimal timeout based on market conditions
- **Circuit breaker integration** - Prevent timeout cascades
- **Per-symbol timeouts** - Some symbols may need more time (low liquidity, complex options chains)
