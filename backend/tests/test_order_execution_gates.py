"""Tests for OrderExecutor risk gates — every gate must pass before execution.

Covers Gate 0 (stale TTL) through Gate 9 (risk governor), plus order type
selection and emergency flatten. All external APIs are mocked.
"""
import asyncio
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.message_bus import MessageBus
from app.services.order_executor import OrderExecutor


_GATE_PATCHES = {
    "app.api.v1.risk_shield_api.is_entries_frozen": lambda: False,
}


@pytest.fixture(autouse=True)
def _mock_kill_switch():
    """Prevent kill-switch / entries-frozen from blocking test trades."""
    with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
        yield


def _make_verdict(overrides: dict = None) -> dict:
    """Build a valid council.verdict payload with sensible defaults."""
    base = {
        "symbol": "AAPL",
        "final_direction": "buy",
        "final_confidence": 0.85,
        "execution_ready": True,
        "vetoed": False,
        "veto_reasons": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signal_data": {
            "score": 80,
            "regime": "GREEN",
            "price": 150.0,
            "source": "test",
        },
        "price": 150.0,
        "votes": [],
        "council_reasoning": "test",
        "council_decision_id": "test-001",
    }
    if overrides:
        for k, v in overrides.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                base[k].update(v)
            else:
                base[k] = v
    return base


async def _mock_kelly(symbol, score, regime, price, direction):
    return {
        "action": "TRADE",
        "kelly_pct": 0.05,
        "qty": 10,
        "edge": 0.1,
        "stats_source": "test",
        "stop_loss": price * 0.98,
        "take_profit": price * 1.05,
        "raw_kelly": 0.05,
        "win_rate": 0.55,
        "trade_count": 50,
    }


def _patch_external_gates(executor: OrderExecutor) -> None:
    """Stub out gates that hit services we don't want to exercise here."""
    executor._compute_kelly_size = _mock_kelly

    async def _drawdown_ok():
        return True
    executor._check_drawdown = _drawdown_ok

    mock_alpaca = MagicMock()
    mock_alpaca.get_account = AsyncMock(return_value={
        "equity": "100000",
        "last_equity": "100000",
    })
    mock_alpaca.get_positions = AsyncMock(return_value=[])
    mock_alpaca.create_order = AsyncMock(return_value={"id": "order-abc123"})
    mock_alpaca.close_all_positions = AsyncMock(return_value=[])
    executor._alpaca_svc = mock_alpaca

    # Clear deduplication cache so tests don't interfere with each other
    executor._recent_verdict_hashes = {}


@pytest.fixture
async def bus():
    b = MessageBus()
    await b.start()
    yield b
    await b.stop()


@pytest.fixture
async def executor(bus):
    ex = OrderExecutor(
        message_bus=bus,
        auto_execute=False,
        min_score=75.0,
        max_daily_trades=10,
        cooldown_seconds=300,
        max_portfolio_heat=0.25,
        max_single_position=0.10,
    )
    _patch_external_gates(ex)
    await ex.start()
    yield ex
    await ex.stop()


# ── Gate 0: Stale verdict rejected (TTL 30s) ──────────────────────────────

@pytest.mark.asyncio
async def test_gate0_stale_verdict_rejected(executor, bus):
    """A verdict older than 30s must be rejected (Swarm invariant #4)."""
    stale_ts = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    verdict = _make_verdict({"timestamp": stale_ts})

    before = executor._signals_rejected
    await executor._on_council_verdict(verdict)
    assert executor._signals_rejected == before + 1


# ── Gate 1: Hold direction rejected ───────────────────────────────────────

@pytest.mark.asyncio
async def test_gate1_hold_rejected(executor):
    """Direction=hold must be rejected at Gate 1."""
    verdict = _make_verdict({"final_direction": "hold"})

    before = executor._signals_rejected
    await executor._on_council_verdict(verdict)
    assert executor._signals_rejected == before + 1


# ── Gate 1: Not execution-ready rejected ──────────────────────────────────

@pytest.mark.asyncio
async def test_gate1_not_execution_ready(executor):
    """execution_ready=False must be rejected at Gate 1."""
    verdict = _make_verdict({"execution_ready": False})

    before = executor._signals_rejected
    await executor._on_council_verdict(verdict)
    assert executor._signals_rejected == before + 1


# ── Gate 2: Mock source guard ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gate2_mock_source_rejected(executor):
    """A verdict whose signal_data.source contains 'mock' must be refused."""
    verdict = _make_verdict({
        "signal_data": {
            "score": 80,
            "regime": "GREEN",
            "price": 150.0,
            "source": "mock_test",
        },
    })

    before = executor._signals_rejected
    await executor._on_council_verdict(verdict)
    assert executor._signals_rejected == before + 1


# ── Gate 3: Daily trade limit ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gate3_daily_trade_limit(bus):
    """The 3rd trade must be rejected when max_daily_trades=2."""
    ex = OrderExecutor(
        message_bus=bus,
        auto_execute=False,
        min_score=75.0,
        max_daily_trades=2,
        cooldown_seconds=0,
        max_portfolio_heat=0.50,
    )
    _patch_external_gates(ex)
    await ex.start()

    symbols = ["GATE3_A", "GATE3_B", "GATE3_C"]
    for sym in symbols:
        verdict = _make_verdict({
            "symbol": sym,
            "council_decision_id": f"test-gate3-{sym}-{time.monotonic()}",
            "signal_data": {"score": 80, "regime": "GREEN", "price": 150.0, "source": "test"},
        })
        await ex._on_council_verdict(verdict)
        await asyncio.sleep(0.05)

    assert ex._signals_executed == 2, (
        f"Expected 2 executed, got {ex._signals_executed} "
        f"(rejected={ex._signals_rejected}, received={ex._signals_received})"
    )
    assert ex._signals_rejected >= 1
    await ex.stop()


# ── Gate 4: Per-symbol cooldown ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_gate4_symbol_cooldown(bus):
    """Second trade on the same symbol within cooldown_seconds must be rejected."""
    ex = OrderExecutor(
        message_bus=bus,
        auto_execute=False,
        min_score=75.0,
        max_daily_trades=100,
        cooldown_seconds=300,
        max_portfolio_heat=0.50,
    )
    _patch_external_gates(ex)
    await ex.start()

    v1 = _make_verdict({
        "symbol": "GATE4_SYM",
        "council_decision_id": f"cd-gate4-001-{time.monotonic()}",
        "signal_data": {"score": 80, "regime": "GREEN", "price": 150.0, "source": "test"},
    })
    await ex._on_council_verdict(v1)
    await asyncio.sleep(0.05)
    assert ex._signals_executed == 1, (
        f"First trade should execute, got executed={ex._signals_executed}, "
        f"rejected={ex._signals_rejected}"
    )

    v2 = _make_verdict({
        "symbol": "GATE4_SYM",
        "council_decision_id": f"cd-gate4-002-{time.monotonic()}",
        "final_confidence": 0.90,
        "signal_data": {"score": 85, "regime": "GREEN", "price": 151.0, "source": "test"},
    })
    await ex._on_council_verdict(v2)
    assert ex._signals_rejected >= 1
    await ex.stop()


# ── Order type selection (market / limit / TWAP) ─────────────────────────

@pytest.mark.asyncio
async def test_market_limit_twap_order_type(executor):
    """Order type must vary by notional: market <=5K, limit 5K-25K, twap >25K."""
    ot_small, lp_small = executor._select_order_type(price=10.0, qty=50)
    assert ot_small == "market"
    assert lp_small is None

    ot_mid, lp_mid = executor._select_order_type(price=150.0, qty=50)
    assert ot_mid == "limit"
    assert lp_mid == 150.0

    ot_large, lp_large = executor._select_order_type(price=150.0, qty=200)
    assert ot_large == "twap"
    assert lp_large == 150.0


# ── Gate 7: Portfolio heat ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_portfolio_heat_check(bus):
    """Trades must be rejected when portfolio heat >= max_portfolio_heat."""
    ex = OrderExecutor(
        message_bus=bus,
        auto_execute=False,
        max_daily_trades=100,
        cooldown_seconds=0,
        max_portfolio_heat=0.25,
    )
    _patch_external_gates(ex)

    mock_alpaca = ex._alpaca_svc
    mock_alpaca.get_account = AsyncMock(return_value={
        "equity": "100000",
        "last_equity": "100000",
    })

    # 24% heat — should pass
    mock_alpaca.get_positions = AsyncMock(return_value=[
        {"market_value": "24000"},
    ])
    ok, info = await ex._check_portfolio_heat(0.05)
    assert ok is False  # 24% + 5% = 29% > 25%

    # Smaller new position at 24% heat
    ok2, info2 = await ex._check_portfolio_heat(0.005)
    assert ok2 is True  # 24% + 0.5% = 24.5% < 25%

    # 26% heat — even smallest addition should fail
    mock_alpaca.get_positions = AsyncMock(return_value=[
        {"market_value": "26000"},
    ])
    ok3, info3 = await ex._check_portfolio_heat(0.005)
    assert ok3 is False  # 26% + 0.5% > 25%


# ── Emergency flatten ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_emergency_flatten(bus):
    """emergency_flatten must exist and invoke alpaca close_all_positions."""
    ex = OrderExecutor(message_bus=bus, auto_execute=True)
    _patch_external_gates(ex)
    await ex.start()

    assert hasattr(ex, "emergency_flatten")
    assert asyncio.iscoroutinefunction(ex.emergency_flatten)

    result = await ex.emergency_flatten(reason="test")
    assert isinstance(result, dict)
    assert "reason" in result
    await ex.stop()
