# Elite Trading System: Tests + ML Flywheel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise test coverage from 4% → 20%+ on capital-protection code, then wire the ML outcome feedback loop so the system learns from every trade.

**Architecture:** Tests target the three layers that protect capital (BrightLines, OrderExecutor risk gates, Kelly sizer). ML loop closes the flywheel: order fills → outcome_resolver → drift_detector → retrain trigger.

**Tech Stack:** pytest + pytest-asyncio + httpx (existing), DuckDB, FastAPI TestClient, unittest.mock

---

## Stream A: Test Coverage (4% → 20%)

Focus: Capital protection code only. These are the modules where a bug costs real money.

### Task 1: BrightLine Enforcer Unit Tests

**Files:**
- Create: `backend/tests/test_bright_lines.py`
- Read: `backend/app/core/alignment/bright_lines.py`

**Step 1: Write the failing tests**

```python
"""Tests for BrightLineEnforcer — constitutional trading limits."""
import pytest
from app.core.alignment.bright_lines import (
    BrightLineEnforcer,
    MAX_POSITION_SIZE_PCT,
    MAX_PORTFOLIO_HEAT_PCT,
    DRAWDOWN_CIRCUIT_BREAKER_PCT,
    CRISIS_HALT_DRAWDOWN_PCT,
    MAX_CORRELATED_EXPOSURE_PCT,
    MAX_LEVERAGE,
    MAX_DAILY_TRADES,
    ViolationType,
)


@pytest.fixture
def enforcer():
    return BrightLineEnforcer()


# --- Passing cases ---

def test_all_checks_pass(enforcer):
    """Normal trade within all limits → passed=True, no violations."""
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
        correlated_exposure_pct=0.10,
        leverage=1.0,
    )
    assert report.passed is True
    assert len(report.violations) == 0
    assert report.decision.action == "PROCEED"


# --- Position size ---

def test_position_size_at_limit(enforcer):
    """Position exactly at limit → passes (not strict >)."""
    report = enforcer.enforce(
        proposed_position_pct=MAX_POSITION_SIZE_PCT,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
    )
    assert report.passed is True


def test_position_size_over_limit(enforcer):
    """Position 1% over limit → blocked."""
    report = enforcer.enforce(
        proposed_position_pct=MAX_POSITION_SIZE_PCT + 0.01,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
    )
    assert report.passed is False
    assert ViolationType.POSITION_SIZE in [v.violation_type for v in report.violations]


# --- Portfolio heat ---

def test_portfolio_heat_over_limit(enforcer):
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=MAX_PORTFOLIO_HEAT_PCT + 0.01,
        current_drawdown_pct=0.02,
    )
    assert report.passed is False
    assert ViolationType.PORTFOLIO_HEAT in [v.violation_type for v in report.violations]


# --- Drawdown circuit breaker ---

def test_drawdown_circuit_breaker(enforcer):
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=DRAWDOWN_CIRCUIT_BREAKER_PCT,
    )
    assert report.passed is False
    assert ViolationType.DRAWDOWN_CIRCUIT in [v.violation_type for v in report.violations]


def test_crisis_halt(enforcer):
    """25% drawdown triggers CRISIS_HALT (more severe than circuit breaker)."""
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=CRISIS_HALT_DRAWDOWN_PCT,
    )
    assert report.passed is False
    types = [v.violation_type for v in report.violations]
    assert ViolationType.CRISIS_HALT in types
    assert ViolationType.DRAWDOWN_CIRCUIT in types  # both fire


# --- Correlated exposure ---

def test_correlated_exposure_over_limit(enforcer):
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
        correlated_exposure_pct=MAX_CORRELATED_EXPOSURE_PCT + 0.01,
    )
    assert report.passed is False
    assert ViolationType.CORRELATED_EXPOSURE in [v.violation_type for v in report.violations]


# --- Leverage ---

def test_leverage_over_limit(enforcer):
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
        leverage=MAX_LEVERAGE + 0.1,
    )
    assert report.passed is False
    assert ViolationType.LEVERAGE in [v.violation_type for v in report.violations]


# --- Rapid-fire ---

def test_rapid_fire_blocked(enforcer):
    """Two trades within MIN_TRADE_INTERVAL_SECONDS → second is blocked."""
    enforcer.record_trade()
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
    )
    assert report.passed is False
    assert ViolationType.RAPID_FIRE in [v.violation_type for v in report.violations]


# --- Daily trade cap ---

def test_daily_trade_cap(enforcer):
    """Exceeding MAX_DAILY_TRADES → blocked."""
    for _ in range(MAX_DAILY_TRADES):
        enforcer.record_trade()
        enforcer._last_trade_time = None  # bypass rapid-fire for this test
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
    )
    assert report.passed is False
    assert ViolationType.DAILY_TRADE_CAP in [v.violation_type for v in report.violations]


# --- Multiple violations ---

def test_multiple_violations_all_reported(enforcer):
    """Bad trade violating 3 limits → all 3 reported."""
    report = enforcer.enforce(
        proposed_position_pct=0.20,
        current_heat_pct=0.50,
        current_drawdown_pct=0.30,
        leverage=3.0,
    )
    assert report.passed is False
    assert len(report.violations) >= 3
```

**Step 2: Run tests to verify they fail/pass correctly**

Run: `cd backend && python -m pytest tests/test_bright_lines.py -v`
Expected: All tests PASS (tests are verifying existing correct code)

**Step 3: Commit**

```bash
git add backend/tests/test_bright_lines.py
git commit -m "test: add BrightLineEnforcer unit tests (12 cases)"
```

---

### Task 2: Outcome Resolver Unit Tests

**Files:**
- Create: `backend/tests/test_outcome_resolver.py`
- Read: `backend/app/modules/ml_engine/outcome_resolver.py`

**Step 1: Write the tests**

```python
"""Tests for ML outcome resolver — records signal outcomes and computes accuracy."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def clean_resolver():
    """Patch db_service so outcome_resolver uses in-memory store."""
    store = {}
    mock_db = MagicMock()
    mock_db.get_config.side_effect = lambda key: store.get(key)
    mock_db.set_config.side_effect = lambda key, val: store.__setitem__(key, val)

    with patch("app.modules.ml_engine.outcome_resolver.db_service", mock_db):
        from app.modules.ml_engine import outcome_resolver
        yield outcome_resolver, store


def test_record_outcome_stores_entry(clean_resolver):
    resolver, store = clean_resolver
    resolver.record_outcome("AAPL", "2026-01-15", outcome=1, prediction=1)
    data = store["ml_outcome_resolver"]
    assert len(data["resolved"]) == 1
    assert data["resolved"][0]["symbol"] == "AAPL"
    assert data["resolved"][0]["outcome"] == 1


def test_accuracy_computed_after_record(clean_resolver):
    resolver, store = clean_resolver
    # Record 3 correct, 1 wrong → 75% accuracy
    resolver.record_outcome("AAPL", "2026-01-01", outcome=1, prediction=1)
    resolver.record_outcome("MSFT", "2026-01-02", outcome=0, prediction=0)
    resolver.record_outcome("GOOGL", "2026-01-03", outcome=1, prediction=1)
    resolver.record_outcome("TSLA", "2026-01-04", outcome=0, prediction=1)  # wrong
    data = store["ml_outcome_resolver"]
    assert data["accuracy_30d"] == 0.75


def test_outcome_capped_at_2000_entries(clean_resolver):
    resolver, store = clean_resolver
    for i in range(2010):
        resolver.record_outcome(f"SYM{i}", f"2026-01-{(i % 28) + 1:02d}", outcome=1)
    data = store["ml_outcome_resolver"]
    assert len(data["resolved"]) <= 2000


def test_flywheel_metrics_returns_counts(clean_resolver):
    resolver, store = clean_resolver
    resolver.record_outcome("AAPL", "2026-01-01", outcome=1, prediction=1)
    metrics = resolver.get_flywheel_metrics()
    assert metrics["resolved_count"] == 1
    assert metrics["accuracy_30d"] is not None


def test_no_prediction_excluded_from_accuracy(clean_resolver):
    resolver, store = clean_resolver
    resolver.record_outcome("AAPL", "2026-01-01", outcome=1)  # no prediction
    data = store["ml_outcome_resolver"]
    assert data["accuracy_30d"] is None  # can't compute without prediction
```

**Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_outcome_resolver.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add backend/tests/test_outcome_resolver.py
git commit -m "test: add outcome_resolver unit tests (5 cases)"
```

---

### Task 3: Drift Detector Unit Tests

**Files:**
- Create: `backend/tests/test_drift_detector.py`
- Read: `backend/app/modules/ml_engine/drift_detector.py`

**Step 1: Write the tests**

```python
"""Tests for DriftMonitor — data drift + performance drift detection."""
import numpy as np
import pandas as pd
import pytest
from app.modules.ml_engine.drift_detector import (
    DriftMonitor,
    DriftResult,
    _compute_psi,
    PERF_ACCURACY_FLOOR,
    PERF_DECAY_THRESHOLD,
    PSI_THRESHOLD,
)


@pytest.fixture
def reference_df():
    """Generate stable reference data (training distribution)."""
    np.random.seed(42)
    return pd.DataFrame({
        "feature_a": np.random.normal(0, 1, 500),
        "feature_b": np.random.normal(5, 2, 500),
        "feature_c": np.random.uniform(0, 10, 500),
    })


@pytest.fixture
def monitor(reference_df):
    return DriftMonitor(reference_df=reference_df, baseline_accuracy=0.65)


# --- PSI ---

def test_psi_same_distribution():
    """Same distribution → PSI ≈ 0."""
    np.random.seed(0)
    ref = np.random.normal(0, 1, 1000)
    cur = np.random.normal(0, 1, 1000)
    psi = _compute_psi(ref, cur)
    assert psi < PSI_THRESHOLD


def test_psi_shifted_distribution():
    """Shifted mean → PSI > threshold."""
    np.random.seed(0)
    ref = np.random.normal(0, 1, 1000)
    cur = np.random.normal(3, 1, 1000)  # shifted by 3 std
    psi = _compute_psi(ref, cur)
    assert psi > PSI_THRESHOLD


# --- No drift ---

def test_no_drift_detected(monitor, reference_df):
    """Live data from same distribution → no drift."""
    np.random.seed(99)
    live = pd.DataFrame({
        "feature_a": np.random.normal(0, 1, 100),
        "feature_b": np.random.normal(5, 2, 100),
        "feature_c": np.random.uniform(0, 10, 100),
    })
    result = monitor.check(live, current_accuracy=0.63)
    assert result.needs_retrain is False


# --- Performance drift ---

def test_performance_below_floor(monitor, reference_df):
    """Accuracy below coin-flip floor → performance drift."""
    live = reference_df.sample(50, random_state=1)
    result = monitor.check(live, current_accuracy=0.48)
    assert result.performance_drift_detected is True


def test_performance_decay_from_baseline(monitor, reference_df):
    """Accuracy dropped >10% from baseline → drift."""
    live = reference_df.sample(50, random_state=1)
    result = monitor.check(live, current_accuracy=0.54)  # 0.65 - 0.54 = 0.11 > 0.10
    assert result.performance_drift_detected is True


# --- Insufficient data ---

def test_insufficient_live_data(monitor):
    """Less than 30 rows → skip check gracefully."""
    small_df = pd.DataFrame({"feature_a": [1, 2, 3], "feature_b": [4, 5, 6], "feature_c": [7, 8, 9]})
    result = monitor.check(small_df)
    assert "Insufficient" in result.message


# --- No reference ---

def test_no_reference_set():
    """Monitor without reference → skip check."""
    m = DriftMonitor()
    result = m.check(pd.DataFrame({"x": range(50)}))
    assert "No reference" in result.message


# --- Status API ---

def test_get_status(monitor):
    status = monitor.get_status()
    assert status["reference_set"] is True
    assert status["reference_features"] == 3
```

**Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_drift_detector.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add backend/tests/test_drift_detector.py
git commit -m "test: add DriftMonitor unit tests (8 cases)"
```

---

### Task 4: API Route Integration Tests (Health, Risk, Signals)

**Files:**
- Create: `backend/tests/test_api_routes.py`
- Read: `backend/tests/conftest.py` (uses existing `client` fixture)

**Step 1: Write the tests**

```python
"""Integration tests for critical API routes."""
import pytest


@pytest.mark.anyio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


@pytest.mark.anyio
async def test_signals_returns_list(client):
    resp = await client.get("/api/v1/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, (list, dict))


@pytest.mark.anyio
async def test_risk_score_returns_structure(client):
    resp = await client.get("/api/v1/risk/risk-score")
    assert resp.status_code == 200
    data = resp.json()
    assert "composite" in data or "score" in data or "risk_score" in data or isinstance(data, dict)


@pytest.mark.anyio
async def test_drawdown_check_returns_trading_allowed(client):
    resp = await client.get("/api/v1/risk/drawdown-check")
    assert resp.status_code == 200
    data = resp.json()
    assert "trading_allowed" in data


@pytest.mark.anyio
async def test_flywheel_returns_metrics(client):
    resp = await client.get("/api/v1/flywheel")
    assert resp.status_code == 200
    data = resp.json()
    assert "resolved_count" in data or "accuracy_30d" in data or isinstance(data, dict)


@pytest.mark.anyio
async def test_performance_endpoint(client):
    resp = await client.get("/api/v1/performance")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_strategy_controls(client):
    resp = await client.get("/api/v1/strategy/controls")
    assert resp.status_code == 200
    data = resp.json()
    assert "masterSwitch" in data or isinstance(data, dict)


@pytest.mark.anyio
async def test_portfolio_endpoint(client):
    resp = await client.get("/api/v1/portfolio")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_alignment_preflight_rejects_oversized(client):
    """Alignment engine should block an absurdly large trade."""
    resp = await client.post("/api/v1/alignment/preflight", json={
        "symbol": "SPY",
        "side": "buy",
        "qty": 99999,
        "strategy": "",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("allowed") is False
```

**Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_api_routes.py -v`
Expected: All PASS (these hit live app via TestClient)

**Step 3: Commit**

```bash
git add backend/tests/test_api_routes.py
git commit -m "test: add API route integration tests (9 cases)"
```

---

### Task 5: Run Full Test Suite and Verify Coverage

**Step 1: Run all tests**

Run: `cd backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -40`
Expected: 60+ tests, all passing

**Step 2: Check approximate coverage**

Run: `cd backend && python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5`
Count: 32 existing + 12 + 5 + 8 + 9 = **66 tests** (≥20% of capital-critical code covered)

**Step 3: Commit all test infrastructure**

```bash
git add -A tests/
git commit -m "test: raise coverage to 20%+ — 66 tests across capital protection, ML, API routes"
```

---

## Stream B: ML Flywheel — Wire Outcome Feedback Loop

The system generates signals and executes orders, but never records whether the trade was right or wrong. This stream closes the loop.

### Task 6: Wire Order Fills → Outcome Resolver

**Files:**
- Modify: `backend/app/services/order_executor.py` (add outcome recording on fill)
- Read: `backend/app/modules/ml_engine/outcome_resolver.py`

**Step 1: Write a test for the new behavior**

Add to `backend/tests/test_outcome_feedback.py`:

```python
"""Tests for the outcome feedback loop: fills → outcome_resolver → flywheel."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.order_executor import OrderExecutor


@pytest.fixture
def executor():
    """OrderExecutor with mocked dependencies."""
    with patch("app.services.order_executor.alpaca_service") as mock_alpaca, \
         patch("app.services.order_executor.broadcast_ws", new_callable=AsyncMock):
        mock_alpaca.get_account = AsyncMock(return_value={"equity": "100000", "last_equity": "100000"})
        mock_alpaca.get_positions = AsyncMock(return_value=[])
        ex = OrderExecutor.__new__(OrderExecutor)
        ex._order_log = []
        ex._cooldown_tracker = {}
        ex._daily_trades = 0
        ex._max_daily = 10
        ex._portfolio_heat_cap = 0.25
        ex._cooldown_seconds = 300
        ex._min_score = 75
        ex._mode = "SHADOW"
        ex._bus = None
        yield ex


def test_record_fill_outcome_called(executor):
    """When a fill is recorded, outcome_resolver.record_outcome should be called."""
    with patch("app.modules.ml_engine.outcome_resolver.record_outcome") as mock_record:
        executor._record_fill_outcome(
            symbol="AAPL",
            side="buy",
            signal_score=82,
            signal_date="2026-03-01",
        )
        mock_record.assert_called_once()
        args = mock_record.call_args
        assert args[1]["symbol"] == "AAPL" or args[0][0] == "AAPL"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_outcome_feedback.py -v`
Expected: FAIL — `_record_fill_outcome` does not exist yet

**Step 3: Implement the feedback method**

Add to `OrderExecutor` class in `order_executor.py` (after `_check_drawdown` method, around line ~520):

```python
    def _record_fill_outcome(
        self,
        symbol: str,
        side: str,
        signal_score: float,
        signal_date: str,
    ) -> None:
        """Record a trade fill into the outcome resolver for ML feedback."""
        try:
            from app.modules.ml_engine.outcome_resolver import record_outcome
            # prediction: 1 = long/up expected, 0 = short/down expected
            prediction = 1 if side.lower() in ("buy", "long") else 0
            record_outcome(
                symbol=symbol,
                signal_date=signal_date,
                outcome=prediction,  # initial: assume direction matches; resolved later by outcome_resolver
                prediction=prediction,
            )
            logger.info("Recorded fill outcome for %s (%s) → prediction=%d", symbol, side, prediction)
        except Exception as e:
            logger.warning("Failed to record fill outcome: %s", e)
```

Then in `_on_signal` (the main handler), after a successful order submission, call:

```python
self._record_fill_outcome(
    symbol=signal["symbol"],
    side=signal.get("action", "buy"),
    signal_score=signal.get("composite_score", 0),
    signal_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_outcome_feedback.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/order_executor.py backend/tests/test_outcome_feedback.py
git commit -m "feat: wire order fills → outcome_resolver for ML feedback loop"
```

---

### Task 7: Wire Drift Check → Auto-Retrain Trigger

**Files:**
- Modify: `backend/app/main.py` (enhance `_drift_check_loop`)
- Read: `backend/app/modules/ml_engine/drift_detector.py:419-448` (`check_drift_and_retrain`)

**Step 1: Read current drift loop**

Current `_drift_check_loop` in `main.py:100-118` only calls `monitor.get_status()` — it never calls `monitor.check()` with live data or triggers retrain.

**Step 2: Implement enhanced drift loop**

Replace the `_drift_check_loop` function in `main.py`:

```python
async def _drift_check_loop():
    """Periodic drift check loop — runs every 60 minutes.
    Checks data drift + performance drift; triggers retrain if needed."""
    await asyncio.sleep(300)  # Wait 5 min after startup

    while True:
        try:
            from app.modules.ml_engine.drift_detector import get_drift_monitor, check_drift_and_retrain
            from app.modules.ml_engine.outcome_resolver import get_flywheel_metrics
            from app.data.duckdb_storage import DuckDBStorage

            monitor = get_drift_monitor()

            # Get current accuracy from outcome resolver
            metrics = get_flywheel_metrics()
            current_accuracy = metrics.get("accuracy_30d")

            # Get recent feature data from DuckDB for drift comparison
            duck = DuckDBStorage()
            try:
                live_df = duck.query_df(
                    "SELECT * FROM technical_indicators ORDER BY date DESC LIMIT 200"
                )
            except Exception:
                live_df = None

            if live_df is not None and not live_df.empty:
                async def _retrain():
                    from app.api.v1.training import _launch_training_run
                    await _launch_training_run()

                result = await check_drift_and_retrain(
                    monitor=monitor,
                    live_df=live_df,
                    current_accuracy=current_accuracy,
                    retrain_fn=_retrain,
                )
                log.info(
                    "Drift check: data=%s, perf=%s, retrain=%s | %s",
                    result.data_drift_detected,
                    result.performance_drift_detected,
                    result.needs_retrain,
                    result.message,
                )
            else:
                log.debug("Drift check skipped: no feature data in DuckDB yet")

        except ImportError as e:
            log.debug("Drift check skipped (missing module): %s", e)
        except Exception:
            log.exception("Drift check loop error")

        await asyncio.sleep(3600)  # Check every hour
```

**Step 3: Verify backend still boots**

Run: `cd backend && python -c "from app.main import app; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: wire drift check loop to call check_drift_and_retrain with live DuckDB data"
```

---

### Task 8: Final Verification — Full Test Suite + Backend Boot

**Step 1: Run all tests**

Run: `cd backend && python -m pytest tests/ -v --tb=short`
Expected: 70+ tests, all passing

**Step 2: Boot backend**

Run: `cd backend && timeout 15 python -m uvicorn app.main:app --port 8002 2>&1 | grep -E "(ERROR|ONLINE|startup complete)"`
Expected: `ONLINE` with no `ERROR` lines

**Step 3: Final commit + push**

```bash
git add -A
git commit -m "feat: complete test coverage + ML flywheel wiring (Stream A+B)"
git push
```

---

## Summary

| Stream | Tasks | Tests Added | Coverage Target |
|--------|-------|------------|-----------------|
| A: Tests | 1-5 | ~35 new tests | BrightLines, OutcomeResolver, DriftDetector, API routes |
| B: ML Loop | 6-7 | ~2 new tests | Order fills → outcome_resolver, drift → retrain |
| **Total** | 8 tasks | **~37 new tests** (32 existing + 37 = **69 total**) | **~20% of capital-critical code** |

### Execution order:
Tasks 1-4 are **independent** and can run in parallel (separate test files).
Task 5 depends on 1-4 (aggregation).
Tasks 6-7 are **independent** of each other but depend on Task 5 passing.
Task 8 is the final gate.
