# OrderExecutor Slippage Refactoring

## Summary

This refactoring addresses critical inconsistencies in slippage handling between live and shadow (paper trading) execution in the OrderExecutor. The changes ensure that both execution paths use the same realistic slippage simulation with market data enrichment, and that quantity adjustments happen at the correct time in the order lifecycle.

## Problems Identified

### 1. Dual-Path Inconsistency
- **Issue**: Live execution (`_execute_order`) did not simulate slippage, while shadow execution (`_shadow_execute`) did
- **Impact**: Paper trading was MORE realistic than live trading, inverting the development workflow
- **Root Cause**: Shadow execution was added later without updating live execution

### 2. Missing Market Context
- **Issue**: Slippage simulation was called without volume, volatility, or spread data
- **Impact**: ExecutionSimulator had to estimate these values from price alone, reducing accuracy
- **Root Cause**: No market data enrichment before simulation

### 3. Post-Kelly Quantity Adjustment
- **Issue**: Quantity was adjusted AFTER Kelly sizing and stop/TP calculation
- **Impact**: Risk/reward ratios were broken (e.g., Kelly sizes for 100 shares, but only executes 75)
- **Root Cause**: `record.qty` was mutated after OrderRecord creation

### 4. Event Schema Mismatch
- **Issue**: Shadow events included slippage fields (`slippage_bps`, `fill_ratio`, etc.) but live events did not
- **Impact**: Downstream consumers (frontend, analytics) saw different schemas
- **Root Cause**: Separate event publishing code paths

## Changes Made

### 1. New Method: `_get_market_data(symbol)` (Lines 323-365)
**Purpose**: Fetch real market microstructure data from DuckDB

**Returns**:
- `volume`: 20-day average daily volume
- `volatility`: 20-day realized volatility
- `spread`: Bid-ask spread (placeholder for future enhancement)

**Data Source**: DuckDB `technical_indicators` table

**Error Handling**: Returns None values on failure, allowing ExecutionSimulator to estimate

### 2. New Method: `_simulate_execution(symbol, side, qty, price)` (Lines 367-424)
**Purpose**: Unified slippage simulation for both live and shadow execution

**Workflow**:
1. Fetch market data via `_get_market_data()`
2. Call ExecutionSimulator with enriched context
3. Calculate adjusted fill quantity: `fill_qty = max(1, int(qty * fill_ratio))`
4. Return comprehensive result dict

**Returns**:
- `fill_price`: Slippage-adjusted price
- `fill_qty`: Partial-fill adjusted quantity
- `slippage_bps`: Total slippage in basis points
- `fill_ratio`: Fill ratio (0, 1]
- `volume_impact_bps`: Volume impact component
- `spread_cost_bps`: Spread cost component

**Error Handling**: Returns safe defaults (no adjustment) if simulator unavailable

### 3. Refactored: `_on_council_verdict` (Lines 261-320)
**Critical Changes**:

**Before**:
```python
qty = kelly_result["qty"]
order_record = OrderRecord(qty=qty, stop_loss=kelly_stop, ...)
await self._execute_order(order_record, price)
```

**After**:
```python
qty = kelly_result["qty"]
# Simulate BEFORE creating record
sim_result = await self._simulate_execution(symbol, side, qty, price)
adjusted_qty = sim_result["fill_qty"]

# Recalculate stop/TP with ADJUSTED qty and price
stop_data = sizer.calculate_trailing_stop(
    entry_price=sim_result["fill_price"],  # Use slippage-adjusted price
    ...
)

order_record = OrderRecord(
    qty=adjusted_qty,  # Already adjusted
    stop_loss=stop_data["stop_loss"],  # Recalculated
    ...
)

await self._execute_order(order_record, price, sim_result)
```

**Key Insight**: Slippage adjustment now happens BEFORE stop/TP calculation, ensuring risk model consistency

### 4. Refactored: `_execute_order` (Lines 426-511)
**Changes**:
- Added `sim_result` parameter
- Uses `sim_result["fill_price"]` for notional calculation
- Publishes comprehensive event with ALL slippage fields
- Logs slippage metrics in execution message

**Event Schema** (now consistent):
```python
{
    "price": sim_result["fill_price"],
    "intended_price": price,
    "slippage_bps": sim_result["slippage_bps"],
    "fill_ratio": sim_result["fill_ratio"],
    "volume_impact_bps": sim_result["volume_impact_bps"],
    "spread_cost_bps": sim_result["spread_cost_bps"],
    # ... existing fields
}
```

### 5. Refactored: `_shadow_execute` (Lines 513-560)
**Changes**:
- Removed inline slippage simulation (now uses shared `_simulate_execution`)
- Added `sim_result` parameter
- Uses same event schema as `_execute_order`
- No longer mutates `record.qty` (already adjusted before call)

**Result**: Shadow and live execution are now identical except for Alpaca API call

## Benefits

### 1. Consistency Across Execution Paths
- ✅ Both live and shadow use the same slippage simulation
- ✅ Paper trading accurately reflects live trading costs
- ✅ No surprises when transitioning from shadow to live

### 2. Improved Accuracy
- ✅ Slippage calculation uses real volume and volatility data
- ✅ More realistic partial fill simulation
- ✅ Better volume impact modeling for large orders

### 3. Correct Risk Management
- ✅ Stop/TP levels calculated with actual fill price and quantity
- ✅ Kelly position sizing respected (no post-hoc qty changes)
- ✅ Portfolio heat calculations accurate

### 4. Unified Event Schema
- ✅ Frontend sees consistent data for live and shadow orders
- ✅ Analytics can track slippage metrics uniformly
- ✅ Easier debugging and monitoring

## Testing

### New Test Suite: `test_order_executor_slippage.py`

**Coverage**:
1. `TestSlippageSimulation`: Validates `_simulate_execution` returns all required fields and handles errors
2. `TestMarketDataEnrichment`: Validates `_get_market_data` fetches volume/volatility from DuckDB
3. `TestEventSchemaConsistency`: Ensures live and shadow publish identical schemas
4. `TestQuantityAdjustmentTiming`: Verifies qty adjustments happen before OrderRecord creation

**Key Tests**:
- Slippage fields present in both live and shadow events
- Market data fetched from DuckDB with fallback to None
- Simulator failures don't crash execution (safe defaults)
- Record.qty not mutated after creation

## Migration Notes

### Breaking Changes
**None** - All changes are internal to OrderExecutor

### Event Schema Changes
**Addition** (backward compatible):
- Live execution events now include: `slippage_bps`, `fill_ratio`, `volume_impact_bps`, `spread_cost_bps`, `intended_price`
- Shadow execution events unchanged (already had these fields)

### Performance Impact
**Minimal**:
- One additional DuckDB query per order (`_get_market_data`)
- Query is fast (indexed, recent data only)
- Benefit: More accurate slippage estimation

## Future Enhancements

1. **Real-time Spread Data**: Replace estimated spread with real bid/ask from market data feed
2. **Adaptive Slippage**: Adjust base slippage based on market conditions (e.g., higher during earnings)
3. **Slippage Analytics**: Track actual vs. simulated slippage for model calibration
4. **Per-Symbol Slippage Profiles**: Learn symbol-specific slippage patterns from historical fills

## Files Modified

1. `backend/app/services/order_executor.py` - Core refactoring
2. `backend/tests/test_order_executor_slippage.py` - New test suite

## Lines of Code

- **Added**: ~200 lines (new methods, enhanced logic, tests)
- **Removed**: ~50 lines (consolidated duplicate code)
- **Net**: +150 lines

## Verification

```bash
# Syntax check
python -m py_compile backend/app/services/order_executor.py

# Run new tests (requires dependencies)
pytest backend/tests/test_order_executor_slippage.py -v

# Run full test suite
pytest backend/tests/test_order_executor.py -v
```

## Related Issues

- Branch: `claude/refactor-order-executor-slippage-again`
- Related: ExecutionSimulator implementation (execution_simulator.py)
- Related: Kelly position sizing (kelly_position_sizer.py)

---

**Summary**: This refactoring eliminates the shadow/live execution gap, adds market data enrichment to slippage simulation, fixes quantity adjustment timing, and unifies event schemas. The result is more accurate, consistent, and maintainable order execution.
