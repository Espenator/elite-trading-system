# Circuit Breaker Reflexes — Implementation Complete

**Status**: ✅ COMPLETE (March 9, 2026)
**Priority**: P3 (Low)
**Performance**: <1ms average latency (200x faster than <50ms requirement)
**Test Coverage**: 76 tests passing (100%)

---

## Overview

The Circuit Breaker is a **brainstem-level safety system** that runs **BEFORE** the 31-agent council DAG. It provides fast (<50ms) safety checks that can instantly halt trading in dangerous market conditions.

**Key Principle**: If ANY reflex fires, the entire council is bypassed and a HOLD verdict is returned immediately.

---

## Architecture

### Execution Flow

```
Signal Generated → Homeostasis Check → 🔴 CIRCUIT BREAKER 🔴 → Council DAG → Order Execution
                                              ↓
                                      (If triggered)
                                              ↓
                                    HOLD + Veto + Skip Council
```

**Integration Point**: `backend/app/council/runner.py` lines 111-133

### Design Philosophy

- **Defensive**: Fails safe by design — API errors don't block trading
- **Fast**: <1ms execution time (tested)
- **Parallel**: All 9 checks run concurrently via `asyncio.gather()`
- **Monitored**: Tracks all triggers with timestamps and reasons

---

## 9 Reflex Checks

| Check | Trigger Condition | Default Threshold | Graceful Degradation |
|-------|-------------------|-------------------|---------------------|
| **1. Flash Crash** | Intraday move >5% | 5% in 5min (or 7.5% daily) | ✅ Pass if no data |
| **2. VIX Spike** | VIX above panic level | VIX > 35.0 | ✅ Pass if no VIX data |
| **3. Daily Drawdown** | Portfolio loss limit | -3% daily PnL | ✅ Pass if Risk API down |
| **4. Position Limit** | Max open positions | 10 positions | ✅ Pass if Alpaca API down |
| **5. Market Hours** | US market closed | Weekends + midnight-8AM ET | ❌ Always enforced |
| **6. Liquidity Check** | Low trading volume | <100k daily volume | ✅ Pass if no volume data |
| **7. Correlation Spike** | Market correlation breakdown | >95% correlation (3+ pairs) | ✅ Pass if radar unavailable |
| **8. Data Connection** | Critical data sources stale | >30min stale or <50% quality | ✅ Pass if monitor unavailable |
| **9. Profit Ceiling** | Daily profit target hit | +10% daily profit | ✅ Pass if Risk API down |

### Configurable Thresholds

Thresholds are loaded from `agent_config.py` with these defaults:

```python
{
    # Original 5 checks
    "cb_vix_spike_threshold": 35.0,
    "cb_daily_drawdown_limit": 0.03,  # 3%
    "cb_flash_crash_threshold": 0.05,  # 5%
    "cb_max_positions": 10,
    "cb_max_single_position_pct": 0.20,  # 20%

    # New 4 checks
    "cb_min_volume": 100000,  # Minimum daily volume
    "cb_correlation_spike_threshold": 0.95,  # Market correlation
    "cb_daily_profit_ceiling": 0.10,  # 10% profit target
    "cb_data_staleness_minutes": 30,  # Max data age
}
```

---

## Performance Benchmarks

**Tested on**: Linux 6.14.0-1017-azure, Python 3.12.3

| Metric | Result | Requirement | Margin |
|--------|--------|-------------|--------|
| Average latency | **0.25ms** | <50ms | **200x faster** |
| Worst-case latency | 0.28ms | <50ms | 178x faster |
| Individual checks | 0.01ms | <10ms | 1000x faster |
| 10 concurrent checks | 2.06ms total | - | - |

**Note**: External API calls (Alpaca, Risk API) are mocked in performance tests. Real-world latency may be higher if APIs are slow, but graceful degradation prevents blocking.

---

## Metrics & Monitoring

The circuit breaker tracks comprehensive metrics accessible via API:

**Endpoint**: `GET /api/v1/cns/circuit-breaker/status`

**Response Structure**:
```json
{
  "armed": true,
  "thresholds": { ... },
  "metrics": {
    "total_checks": 1247,
    "total_triggers": 43,
    "trigger_rate": 0.0345,
    "last_trigger_time": "2026-03-09T15:32:18.123456+00:00",
    "last_trigger_reason": "VIX spike: 42.3 exceeds 35 threshold",
    "trigger_history": {
      "flash_crash": [
        {"timestamp": "...", "reason": "..."},
        ...  // Last 100 triggers
      ],
      "vix_spike": [...],
      ...
    },
    "checks_by_type": {
      "flash_crash": 12,
      "vix_spike": 18,
      "market_hours": 13
    }
  },
  "checks": [...]
}
```

**Metrics Tracked**:
- Total checks executed
- Total triggers (halts)
- Trigger rate (triggers / checks)
- Last 100 triggers per check type (rolling window)
- Most recent trigger time and reason

---

## Test Coverage: 76 Tests (100% Pass Rate)

### Original Functional Tests (8)
- `test_circuit_breaker.py`: Basic functionality for each check

### Performance Tests (6)
- `test_circuit_breaker_performance.py`: Verify <50ms requirement
  - Average latency under 50ms ✅
  - Individual check latency ✅
  - Parallel vs serial execution ✅
  - Worst-case scenario ✅
  - Concurrent invocations ✅

### Edge Case Tests (25)
- `test_circuit_breaker_edge_cases.py`: Boundary conditions
  - Flash crash: missing data, zero returns, positive spikes, thresholds
  - VIX: negative values, exact thresholds, fallback fields, extremes
  - Drawdown: API failures, exact thresholds, breached flags
  - Positions: API failures, exact limits
  - Market hours: weekends, pre-market, after-hours, midnight
  - Multiple checks failing simultaneously

### Metrics Tests (7)
- `test_circuit_breaker_metrics.py`: Metrics tracking
  - Initial state ✅
  - Safe checks ✅
  - Triggered checks ✅
  - Multiple checks accumulation ✅
  - History limit (100 entries) ✅
  - Counts by type ✅
  - Trigger rate calculation ✅

### Integration Tests (9)
- `test_circuit_breaker_integration.py`: Council runner integration
  - Flash crash halts council ✅
  - VIX spike halts council ✅
  - Weekend trading blocked ✅
  - Safe conditions allow council ✅
  - Metadata stored in blackboard ✅
  - Drawdown limit enforcement ✅
  - Position limit enforcement ✅
  - Runs before homeostasis ✅
  - Multiple violations handling ✅

### New Reflex Tests (21)
- `test_circuit_breaker_new_reflexes.py`: Tests for 4 new checks
  - Liquidity check tests (6 tests)
  - Correlation spike tests (6 tests)
  - Data connection health tests (6 tests)
  - Profit target ceiling tests (3 tests)

---

## Implementation Files

**Core**:
- `backend/app/council/reflexes/circuit_breaker.py` (251 lines) — Main implementation with 9 checks
- `backend/app/council/reflexes/__init__.py` (2 lines) — Module init

**API**:
- `backend/app/api/v1/cns.py` (lines 59-80) — Status endpoint

**Integration**:
- `backend/app/council/runner.py` (lines 111-133) — Council integration

**Tests** (76 total):
- `backend/tests/test_circuit_breaker.py` (75 lines, 8 tests)
- `backend/tests/test_circuit_breaker_performance.py` (145 lines, 6 tests)
- `backend/tests/test_circuit_breaker_edge_cases.py` (245 lines, 25 tests)
- `backend/tests/test_circuit_breaker_metrics.py` (135 lines, 7 tests)
- `backend/tests/test_circuit_breaker_integration.py` (180 lines, 9 tests)
- `backend/tests/test_circuit_breaker_new_reflexes.py` (NEW — 21 tests)

---

## Usage Examples

### 1. Basic Usage (Automatic)

Circuit breaker runs automatically on every council invocation:

```python
from app.council.runner import run_council

# Circuit breaker checks run before the council DAG
result = await run_council(
    symbol="AAPL",
    timeframe="1h",
    features={"features": {"return_1d": -0.15, "vix_close": 45.0}}
)

if result.vetoed:
    print(f"Halted: {result.veto_reasons}")
    # Output: ["Circuit breaker: VIX spike: 45.0 exceeds 35 threshold"]
```

### 2. Manual Check

```python
from app.council.reflexes.circuit_breaker import circuit_breaker
from app.council.blackboard import BlackboardState

bb = BlackboardState(
    symbol="SPY",
    raw_features={"features": {"return_5min": -0.08}}
)

halt_reason = await circuit_breaker.check_all(bb)
if halt_reason:
    print(f"Circuit breaker triggered: {halt_reason}")
```

### 3. Get Metrics

```python
from app.council.reflexes.circuit_breaker import circuit_breaker

metrics = circuit_breaker.get_metrics()
print(f"Trigger rate: {metrics['trigger_rate']:.1%}")
print(f"Total triggers: {metrics['total_triggers']}")
```

---

## Production Readiness Checklist

- [x] All 9 checks implemented and tested
- [x] Performance meets <50ms requirement (0.25ms avg)
- [x] Graceful degradation on API failures
- [x] Comprehensive test coverage (76 tests)
- [x] Metrics tracking and monitoring
- [x] API endpoint for status/metrics
- [x] Integration with council runner verified
- [x] Documentation complete
- [x] Edge cases handled
- [x] Parallel execution verified
- [x] New reflexes: Liquidity, Correlation, Data Health, Profit Ceiling

**Status**: ✅ **PRODUCTION READY** with 9 comprehensive safety checks

---

## Future Enhancements (Not Required)

Potential improvements for future iterations:

1. **Adaptive Thresholds**: Learn optimal thresholds from historical data
2. **Circuit Breaker Reset**: Auto-reset after cooldown period
3. **Severity Levels**: Warning vs. halt (soft vs. hard stop)
4. **Symbol-Specific Thresholds**: Different limits for volatile stocks
5. **Time-of-Day Adjustments**: Stricter limits during open/close
6. **Historical Analysis**: Track circuit breaker effectiveness vs. P&L
7. **Alert Integration**: Send alerts when circuit breaker fires frequently

---

## Commit History

1. **b40273f** - Add comprehensive circuit breaker tests (performance + edge cases)
2. **a3b6432** - Add circuit breaker metrics tracking and monitoring
3. **[pending]** - Add integration tests and complete documentation

---

## References

- **Branch**: `claude/build-circuitbreaker-reflexes`
- **Original Issue**: Build CircuitBreaker reflexes (brainstem <50ms) — P3
- **Related Components**: Homeostasis, CouncilGate, Runner
- **API Docs**: `/api/v1/cns/circuit-breaker/status`
