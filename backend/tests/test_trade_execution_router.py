"""Tests for TradeExecutionRouter and execution validation.

Covers: validation (decision_id, expiry, market hours, veto, symbol/price),
idempotency/duplicate prevention, audit persistence, and integration with
execution.validated_verdict / execution.result.
"""
import pytest
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.execution_decision import (
    ExecutionDenyReason,
    ValidationResult,
)
from app.services.trade_execution_router import (
    DECISION_EXPIRY_SECONDS,
    validate_verdict,
    TradeExecutionRouter,
    _parse_verdict_timestamp,
    _is_market_open,
)
from app.services.execution_audit_store import ExecutionAuditStore


# ---------------------------------------------------------------------------
# validate_verdict
# ---------------------------------------------------------------------------

def _valid_verdict(overrides=None):
    now = datetime.now(timezone.utc)
    ts = now.isoformat().replace("+00:00", "Z")
    base = {
        "council_decision_id": "dec-abc123",
        "symbol": "AAPL",
        "final_direction": "buy",
        "execution_ready": True,
        "vetoed": False,
        "veto_reasons": [],
        "timestamp": ts,
        "price": 150.0,
        "signal_data": {"price": 150.0, "close": 150.0},
    }
    if overrides:
        base.update(overrides)
    return base


class TestValidateVerdict:
    def test_valid_verdict_passes(self):
        v = _valid_verdict()
        r = validate_verdict(v)
        assert r.valid is True
        assert r.error_code is None

    def test_missing_council_decision_id_fails(self):
        v = _valid_verdict({"council_decision_id": ""})
        r = validate_verdict(v)
        assert r.valid is False
        assert r.error_code == ExecutionDenyReason.DECISION_ID_MISSING.value

    def test_expired_verdict_fails(self):
        old = datetime.now(timezone.utc) - timedelta(seconds=60)
        ts = old.isoformat().replace("+00:00", "Z")
        v = _valid_verdict({"timestamp": ts})
        r = validate_verdict(v, expiry_seconds=30)
        assert r.valid is False
        assert r.error_code == ExecutionDenyReason.DECISION_EXPIRED.value

    def test_missing_timestamp_treated_as_expired(self):
        v = _valid_verdict()
        del v["timestamp"]
        r = validate_verdict(v)
        assert r.valid is False
        assert r.error_code == ExecutionDenyReason.DECISION_EXPIRED.value

    def test_vetoed_fails(self):
        v = _valid_verdict({"vetoed": True, "veto_reasons": ["risk veto"]})
        r = validate_verdict(v)
        assert r.valid is False
        assert r.error_code == ExecutionDenyReason.VETOED.value

    def test_hold_direction_fails(self):
        v = _valid_verdict({"final_direction": "hold"})
        r = validate_verdict(v)
        assert r.valid is False
        assert r.error_code == ExecutionDenyReason.COUNCIL_HOLD.value

    def test_missing_symbol_fails(self):
        v = _valid_verdict({"symbol": ""})
        r = validate_verdict(v)
        assert r.valid is False
        assert r.error_code == ExecutionDenyReason.MISSING_SYMBOL_PRICE.value

    def test_invalid_price_fails(self):
        v = _valid_verdict({"price": 0, "signal_data": {}})
        r = validate_verdict(v)
        assert r.valid is False
        assert r.error_code == ExecutionDenyReason.MISSING_SYMBOL_PRICE.value


class TestParseVerdictTimestamp:
    def test_iso_timestamp_parsed(self):
        now = datetime.now(timezone.utc)
        ts = now.isoformat().replace("+00:00", "Z")
        v = {"timestamp": ts}
        got = _parse_verdict_timestamp(v)
        assert got is not None
        assert abs(got - now.timestamp()) < 2

    def test_missing_returns_none(self):
        assert _parse_verdict_timestamp({}) is None

    def test_unix_seconds_passthrough(self):
        t = time.time()
        v = {"timestamp": t}
        got = _parse_verdict_timestamp(v)
        assert got is not None
        assert abs(got - t) < 1


class TestMarketHours:
    def test_returns_tuple(self):
        ok, reason = _is_market_open()
        assert isinstance(ok, bool)
        assert reason is None or isinstance(reason, str)


# ---------------------------------------------------------------------------
# ExecutionAuditStore
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_audit_path(tmp_path):
    return tmp_path / "execution_audit.jsonl"


@pytest.fixture
def audit_store(temp_audit_path):
    return ExecutionAuditStore(audit_path=temp_audit_path)


class TestExecutionAuditStore:
    def test_record_request_and_get_status(self, audit_store):
        audit_store.record_request(
            council_decision_id="dec-1",
            symbol="AAPL",
            side="buy",
            status="pending",
        )
        rec = audit_store.get_status("dec-1")
        assert rec is not None
        assert rec.get("council_decision_id") == "dec-1"
        assert rec.get("status") == "pending"

    def test_record_result_then_is_already_completed(self, audit_store):
        audit_store.record_result(
            council_decision_id="dec-2",
            success=True,
            order_id="ord-1",
            client_order_id="et-AAPL-abc",
            symbol="AAPL",
            side="buy",
        )
        assert audit_store.is_already_completed("dec-2") is True

    def test_pending_not_completed(self, audit_store):
        audit_store.record_request(
            council_decision_id="dec-3",
            symbol="MSFT",
            side="sell",
            status="pending",
        )
        assert audit_store.is_already_completed("dec-3") is False

    def test_failed_is_completed(self, audit_store):
        audit_store.record_result(
            council_decision_id="dec-4",
            success=False,
            error_code="broker_error",
            error_message="Alpaca timeout",
        )
        assert audit_store.is_already_completed("dec-4") is True


# ---------------------------------------------------------------------------
# TradeExecutionRouter integration
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_bus():
    bus = AsyncMock()
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.mark.anyio
class TestTradeExecutionRouterFlow:
    async def test_valid_verdict_forwarded(self, mock_bus, temp_audit_path):
        router = TradeExecutionRouter(
            message_bus=mock_bus,
            expiry_seconds=30,
            audit_path=temp_audit_path,
        )
        router.audit = ExecutionAuditStore(audit_path=temp_audit_path)
        await router.start()
        mock_bus.publish.reset_mock()

        v = _valid_verdict()
        await router._on_council_verdict(v)

        mock_bus.publish.assert_any_call("execution.validated_verdict", v)
        await router.stop()

    async def test_invalid_verdict_not_forwarded(self, mock_bus, temp_audit_path):
        router = TradeExecutionRouter(
            message_bus=mock_bus,
            expiry_seconds=30,
            audit_path=temp_audit_path,
        )
        router.audit = ExecutionAuditStore(audit_path=temp_audit_path)
        await router.start()
        mock_bus.publish.reset_mock()

        v = _valid_verdict({"council_decision_id": ""})
        await router._on_council_verdict(v)

        validated_calls = [c for c in mock_bus.publish.call_args_list if c[0][0] == "execution.validated_verdict"]
        assert len(validated_calls) == 0
        await router.stop()

    async def test_duplicate_verdict_suppressed(self, mock_bus, temp_audit_path):
        router = TradeExecutionRouter(
            message_bus=mock_bus,
            expiry_seconds=30,
            audit_path=temp_audit_path,
        )
        store = ExecutionAuditStore(audit_path=temp_audit_path)
        store.record_result(
            council_decision_id="dec-dup",
            success=True,
            order_id="ord-1",
            symbol="AAPL",
            side="buy",
        )
        router.audit = store
        await router.start()

        v = _valid_verdict({"council_decision_id": "dec-dup"})
        await router._on_council_verdict(v)

        validated_calls = [c for c in mock_bus.publish.call_args_list if c[0][0] == "execution.validated_verdict"]
        assert len(validated_calls) == 0
        await router.stop()

    async def test_execution_result_persisted(self, mock_bus, temp_audit_path):
        router = TradeExecutionRouter(
            message_bus=mock_bus,
            expiry_seconds=30,
            audit_path=temp_audit_path,
        )
        router.audit = ExecutionAuditStore(audit_path=temp_audit_path)
        await router.start()

        await router._on_execution_result({
            "council_decision_id": "dec-result",
            "success": True,
            "order_id": "ord-1",
            "client_order_id": "et-AAPL-x",
            "symbol": "AAPL",
            "side": "buy",
            "mode": "paper",
        })

        rec = router.audit.get_status("dec-result")
        assert rec is not None
        assert rec.get("success") is True
        assert rec.get("order_id") == "ord-1"
        await router.stop()
