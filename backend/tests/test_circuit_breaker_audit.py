"""Agent 3: Circuit Breaker & Reflexes audit.

Verifies brainstem reflexes fire BEFORE council and halt trading when triggered.
Produces a JSON report for the launch audit.
"""
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.council.blackboard import BlackboardState
from app.council.reflexes.circuit_breaker import CircuitBreaker, _get_thresholds


# Report populated by tests and written at end
AUDIT_REPORT = {
    "agent": "circuit_breakers",
    "normal_conditions_pass": False,
    "flash_crash_halts": False,
    "vix_spike_halts": False,
    "daily_drawdown_halts": False,
    "position_limit_halts": False,
    "market_hours_halts": False,
    "runner_skips_council_on_halt": False,
    "execution_time_ms": -1,
    "thresholds_from_directives": False,
    "errors": [],
}


def _safe_bb(symbol: str = "SPY"):
    """Blackboard with normal market conditions (no triggers)."""
    return BlackboardState(
        symbol=symbol,
        raw_features={
            "features": {
                "return_5min": 0.001,
                "return_1d": 0.01,
                "vix_close": 20.0,
                "vix": 20.0,
            }
        },
    )


@pytest.mark.anyio
async def test_normal_conditions_pass():
    """With normal market conditions, check_all returns None (safe)."""
    cb = CircuitBreaker()
    bb = _safe_bb()
    with (
        patch("app.council.reflexes.circuit_breaker.datetime") as m_dt,
        patch(
            "app.api.v1.risk.drawdown_check_status",
            new_callable=AsyncMock,
            return_value={"drawdown_breached": False, "daily_pnl_pct": 0.0},
        ),
        patch(
            "app.services.alpaca_service.alpaca_service.get_positions",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        # 10 AM ET Wednesday = within market hours
        et = MagicMock()
        et.hour = 10
        et.weekday.return_value = 2  # Wednesday
        m_dt.now.return_value = et
        result = await cb.check_all(bb)
    try:
        assert result is None, f"Expected None (safe), got {result!r}"
        AUDIT_REPORT["normal_conditions_pass"] = True
    except AssertionError as e:
        AUDIT_REPORT["errors"].append(f"normal_conditions_pass: {e}")


@pytest.mark.anyio
async def test_flash_crash_halts():
    """Inject price_change_5min = -0.06 (>5% drop) -> must return halt reason."""
    cb = CircuitBreaker()
    bb = _safe_bb()
    # Ensure we use price_change_5min, not return_5min from features
    if "features" in bb.raw_features:
        bb.raw_features["features"].pop("return_5min", None)
        bb.raw_features["features"].pop("return_15min", None)
        bb.raw_features["features"].pop("return_1h", None)
    bb.raw_features["price_change_5min"] = -0.06
    with (
        patch.object(cb, "market_hours_check", new_callable=AsyncMock, return_value=None),
        patch(
            "app.api.v1.risk.drawdown_check_status",
            new_callable=AsyncMock,
            return_value={"drawdown_breached": False, "daily_pnl_pct": 0.0},
        ),
        patch(
            "app.services.alpaca_service.alpaca_service.get_positions",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        result = await cb.check_all(bb)
    try:
        assert result is not None, "Expected halt reason for flash crash"
        assert "flash crash" in result.lower() or "intraday" in result.lower()
        AUDIT_REPORT["flash_crash_halts"] = True
    except AssertionError as e:
        AUDIT_REPORT["errors"].append(f"flash_crash_halts: {e}")


@pytest.mark.anyio
async def test_vix_spike_halts():
    """Inject VIX = 40 (>35 threshold) -> must halt."""
    cb = CircuitBreaker()
    bb = _safe_bb()
    # Ensure we use top-level vix; clear from nested features so vix spike is detected
    if "features" in bb.raw_features:
        bb.raw_features["features"].pop("vix_close", None)
        bb.raw_features["features"].pop("vix", None)
    bb.raw_features["vix"] = 40
    with (
        patch.object(cb, "market_hours_check", new_callable=AsyncMock, return_value=None),
        patch(
            "app.api.v1.risk.drawdown_check_status",
            new_callable=AsyncMock,
            return_value={"drawdown_breached": False, "daily_pnl_pct": 0.0},
        ),
        patch(
            "app.services.alpaca_service.alpaca_service.get_positions",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        result = await cb.check_all(bb)
    try:
        assert result is not None, "Expected halt reason for VIX spike"
        assert "VIX" in result
        AUDIT_REPORT["vix_spike_halts"] = True
    except AssertionError as e:
        AUDIT_REPORT["errors"].append(f"vix_spike_halts: {e}")


@pytest.mark.anyio
async def test_daily_drawdown_halts():
    """Portfolio drawdown > 3% -> must halt."""
    cb = CircuitBreaker()
    bb = _safe_bb()
    with (
        patch("app.council.reflexes.circuit_breaker.datetime") as m_dt,
        patch(
            "app.api.v1.risk.drawdown_check_status",
            new_callable=AsyncMock,
            return_value={"drawdown_breached": True},
        ),
        patch(
            "app.services.alpaca_service.alpaca_service.get_positions",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        et = MagicMock()
        et.hour = 10
        et.weekday.return_value = 2
        m_dt.now.return_value = et
        result = await cb.daily_drawdown_limit(bb)
    try:
        assert result is not None, "Expected halt reason for daily drawdown"
        assert "drawdown" in result.lower()
        AUDIT_REPORT["daily_drawdown_halts"] = True
    except AssertionError as e:
        AUDIT_REPORT["errors"].append(f"daily_drawdown_halts: {e}")


@pytest.mark.anyio
async def test_position_limit_halts():
    """11 open positions (>10 max) -> must halt."""
    cb = CircuitBreaker()
    bb = _safe_bb()
    with (
        patch("app.council.reflexes.circuit_breaker.datetime") as m_dt,
        patch(
            "app.api.v1.risk.drawdown_check_status",
            new_callable=AsyncMock,
            return_value={"drawdown_breached": False, "daily_pnl_pct": 0.0},
        ),
        patch(
            "app.services.alpaca_service.alpaca_service.get_positions",
            new_callable=AsyncMock,
            return_value=[{}] * 11,
        ),
    ):
        et = MagicMock()
        et.hour = 10
        et.weekday.return_value = 2
        m_dt.now.return_value = et
        result = await cb.check_all(bb)
    try:
        assert result is not None, "Expected halt reason for position limit"
        assert "position" in result.lower() or "limit" in result.lower()
        AUDIT_REPORT["position_limit_halts"] = True
    except AssertionError as e:
        AUDIT_REPORT["errors"].append(f"position_limit_halts: {e}")


@pytest.mark.anyio
async def test_market_hours_halts():
    """Timestamp 2:00 AM ET -> must halt (outside market hours)."""
    cb = CircuitBreaker()
    bb = _safe_bb()
    with (
        patch("app.council.reflexes.circuit_breaker.datetime") as m_dt,
        patch(
            "app.api.v1.risk.drawdown_check_status",
            new_callable=AsyncMock,
            return_value={"drawdown_breached": False, "daily_pnl_pct": 0.0},
        ),
        patch(
            "app.services.alpaca_service.alpaca_service.get_positions",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        et = MagicMock()
        et.hour = 2  # 2:00 AM ET
        et.weekday.return_value = 2
        m_dt.now.return_value = et
        result = await cb.check_all(bb)
    try:
        assert result is not None, "Expected halt reason for off-hours"
        assert "Market closed" in result or "off-hours" in result
        AUDIT_REPORT["market_hours_halts"] = True
    except AssertionError as e:
        AUDIT_REPORT["errors"].append(f"market_hours_halts: {e}")


@pytest.mark.anyio
async def test_runner_skips_council_on_halt():
    """When circuit breaker fires, runner returns HOLD with halt reason and skips DAG."""
    from app.council.runner import run_council

    with (
        patch("app.council.reflexes.circuit_breaker.datetime") as m_dt,
        patch(
            "app.api.v1.risk.drawdown_check_status",
            new_callable=AsyncMock,
            return_value={"drawdown_breached": False, "daily_pnl_pct": 0.0},
        ),
        patch(
            "app.services.alpaca_service.alpaca_service.get_positions",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        et = MagicMock()
        et.hour = 10
        et.weekday.return_value = 2
        m_dt.now.return_value = et
        # Trigger circuit breaker via VIX spike
        features = {"features": {"vix": 40, "vix_close": 40, "return_1d": 0.01}}
        packet = await run_council("SPY", features=features)
    try:
        assert packet.final_direction == "hold"
        assert packet.vetoed is True
        assert any("circuit breaker" in r.lower() or "VIX" in r for r in (packet.veto_reasons or []))
        assert len(packet.votes) == 0, "Council DAG should be skipped (no votes)"
        AUDIT_REPORT["runner_skips_council_on_halt"] = True
    except AssertionError as e:
        AUDIT_REPORT["errors"].append(f"runner_skips_council_on_halt: {e}")


@pytest.mark.anyio
async def test_execution_time_under_50ms():
    """Circuit breaker check_all completes in < 50ms."""
    cb = CircuitBreaker()
    bb = _safe_bb()
    with (
        patch("app.council.reflexes.circuit_breaker.datetime") as m_dt,
        patch(
            "app.api.v1.risk.drawdown_check_status",
            new_callable=AsyncMock,
            return_value={"drawdown_breached": False, "daily_pnl_pct": 0.0},
        ),
        patch(
            "app.services.alpaca_service.alpaca_service.get_positions",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        et = MagicMock()
        et.hour = 10
        et.weekday.return_value = 2
        m_dt.now.return_value = et
        times_ms = []
        for _ in range(5):
            t0 = time.perf_counter()
            await cb.check_all(bb)
            times_ms.append((time.perf_counter() - t0) * 1000)
    elapsed_ms = min(times_ms)
    AUDIT_REPORT["execution_time_ms"] = int(round(elapsed_ms))
    try:
        assert elapsed_ms < 50, f"check_all took {elapsed_ms:.1f}ms (required <50ms)"
    except AssertionError as e:
        AUDIT_REPORT["errors"].append(f"execution_time_ms: {e}")


def test_thresholds_from_directives():
    """Thresholds are loaded from directives/global.md (via _get_thresholds), not hardcoded."""
    th = _get_thresholds()
    # Values must match directives/global.md: VIX 35, drawdown 3%, flash 5%, max positions 10
    try:
        assert th.get("cb_vix_spike_threshold") == 35.0
        assert th.get("cb_daily_drawdown_limit") == 0.03
        assert th.get("cb_flash_crash_threshold") == 0.05
        assert th.get("cb_max_positions") == 10
        AUDIT_REPORT["thresholds_from_directives"] = True
    except AssertionError as e:
        AUDIT_REPORT["errors"].append(f"thresholds_from_directives: {e}")


@pytest.mark.anyio
async def test_multiple_triggers_first_reason_returned():
    """Multiple simultaneous triggers -> first halt reason is returned."""
    cb = CircuitBreaker()
    bb = _safe_bb()
    bb.raw_features["price_change_5min"] = -0.06
    bb.raw_features["vix"] = 40
    bb.raw_features["features"] = bb.raw_features.get("features", {})
    bb.raw_features["features"]["return_5min"] = -0.06
    bb.raw_features["features"]["vix"] = 40
    with (
        patch("app.council.reflexes.circuit_breaker.datetime") as m_dt,
        patch(
            "app.api.v1.risk.drawdown_check_status",
            new_callable=AsyncMock,
            return_value={"drawdown_breached": True},
        ),
        patch(
            "app.services.alpaca_service.alpaca_service.get_positions",
            new_callable=AsyncMock,
            return_value=[{}] * 11,
        ),
    ):
        et = MagicMock()
        et.hour = 2
        et.weekday.return_value = 2
        m_dt.now.return_value = et
        result = await cb.check_all(bb)
    try:
        assert result is not None
        # Order of checks: flash_crash, vix, drawdown, position, market_hours -> first that fires wins
        assert any(
            x in result.lower()
            for x in ["flash crash", "vix", "drawdown", "position", "market closed"]
        )
        # No error list; we only care that one reason is returned
        pass
    except AssertionError as e:
        AUDIT_REPORT["errors"].append(f"multiple_triggers: {e}")


def test_zz_emit_audit_report_json():
    """Emit JSON report last so other tests have populated AUDIT_REPORT."""
    backend_dir = Path(__file__).resolve().parent.parent
    repo_artifacts = backend_dir.parent / "artifacts"
    backend_artifacts = backend_dir / "artifacts"
    out_dir = repo_artifacts if repo_artifacts.exists() else backend_artifacts
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "circuit_breaker_audit_report.json"
    with open(path, "w") as f:
        json.dump(AUDIT_REPORT, f, indent=2)
    print("\n" + json.dumps(AUDIT_REPORT, indent=2))
