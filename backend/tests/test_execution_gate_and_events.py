"""Tests for execution gate denial reasons and event contract validation.

- ExecutionDecision required: no broker call without approved decision.
- Gate denials use ExecutionDenyReason and emit metrics.
- Event contract: validate_payload and publish_event reject malformed payloads.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.services.execution_decision import ExecutionDecision, ExecutionDenyReason
from app.events.contracts import (
    validate_payload,
    ensure_event_metadata,
    PIPELINE_TOPICS,
    TOPIC_SWARM_IDEA,
    TOPIC_COUNCIL_VERDICT,
    TOPIC_ORDER_SUBMITTED,
    TOPIC_OUTCOME_RESOLVED,
    check_critical_subscribers,
    run_startup_integrity_check,
)


# ---------------------------------------------------------------------------
# ExecutionDecision
# ---------------------------------------------------------------------------

def test_execution_decision_to_order_payload():
    decision = ExecutionDecision(
        symbol="AAPL",
        side="buy",
        qty=10,
        price=175.0,
        direction="buy",
        execution_ready=True,
        signal_score=80.0,
        council_confidence=0.75,
        regime="BULLISH",
        kelly_pct=0.05,
        stop_loss=170.0,
        take_profit=185.0,
        sizing_metadata={"action": "BUY", "edge": 0.1},
        risk_checks_passed=True,
        verdict_timestamp=1000.0,
    )
    payload = decision.to_order_payload(order_id="ord-1", client_order_id="et-AAPL-abc")
    assert payload["symbol"] == "AAPL"
    assert payload["side"] == "buy"
    assert payload["qty"] == 10
    assert payload["order_id"] == "ord-1"
    assert payload["sizing_gate_passed"] is True


def test_deny_reason_enum():
    assert ExecutionDenyReason.COUNCIL_HOLD.value == "council_hold"
    assert ExecutionDenyReason.SIZING_HOLD.value == "sizing_hold"
    assert ExecutionDenyReason.DEGRADED.value == "degraded"
    assert ExecutionDenyReason.VIABILITY_DENIED.value == "viability_denied"
    assert ExecutionDenyReason.KILL_SWITCH_ACTIVE.value == "kill_switch_active"
    assert ExecutionDenyReason.PORTFOLIO_RISK_LIMIT.value == "portfolio_risk_limit"


# ---------------------------------------------------------------------------
# Event contract validation
# ---------------------------------------------------------------------------

def test_validate_swarm_idea_requires_symbols():
    ok, err = validate_payload(TOPIC_SWARM_IDEA, {})
    assert ok is False
    assert "symbol" in (err or "").lower()

    ok, err = validate_payload(TOPIC_SWARM_IDEA, {"symbols": ["AAPL"]})
    assert ok is True
    assert err is None

    ok, err = validate_payload(TOPIC_SWARM_IDEA, {"symbol": "AAPL"})
    assert ok is True


def test_validate_council_verdict_requires_symbol():
    ok, err = validate_payload(TOPIC_COUNCIL_VERDICT, {"final_direction": "buy"})
    assert ok is False
    assert "symbol" in (err or "").lower()

    ok, err = validate_payload(TOPIC_COUNCIL_VERDICT, {"symbol": "AAPL", "final_direction": "buy"})
    assert ok is True


def test_validate_order_submitted_requires_order_id():
    ok, err = validate_payload(TOPIC_ORDER_SUBMITTED, {"symbol": "AAPL"})
    assert ok is False
    assert "order" in (err or "").lower()

    ok, err = validate_payload(TOPIC_ORDER_SUBMITTED, {"order_id": "ord-1", "symbol": "AAPL"})
    assert ok is True


def test_ensure_event_metadata_injects_meta():
    data = {"symbol": "AAPL"}
    out = ensure_event_metadata(data, producer="test", pipeline_stage="triage")
    assert "_event_meta" in out
    meta = out["_event_meta"]
    assert meta["producer"] == "test"
    assert meta["pipeline_stage"] == "triage"
    assert "event_id" in meta
    assert "trace_id" in meta
    assert "created_at" in meta
    assert meta["schema_version"] == "1.0"


def test_pipeline_topics_include_critical():
    assert TOPIC_SWARM_IDEA in PIPELINE_TOPICS
    assert TOPIC_COUNCIL_VERDICT in PIPELINE_TOPICS
    assert TOPIC_ORDER_SUBMITTED in PIPELINE_TOPICS


# ---------------------------------------------------------------------------
# Execution gate: verdict without symbol/price is rejected (integration-style)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_executor_rejects_verdict_without_symbol_and_emits_deny_metric():
    from app.core.metrics import get_counters
    from app.services.order_executor import OrderExecutor

    bus = AsyncMock()
    bus.subscribe = AsyncMock()
    bus.publish = AsyncMock()
    bus.unsubscribe = AsyncMock()

    executor = OrderExecutor(message_bus=bus, auto_execute=False)
    await executor.start()

    # Send verdict with missing symbol/price -> should not call create_order
    handler = bus.subscribe.call_args[0][1]
    await handler({
        "symbol": "",
        "final_direction": "buy",
        "final_confidence": 0.8,
        "execution_ready": True,
        "price": 0,
        "signal_data": {"score": 80},
    })

    await executor.stop()
    assert executor._signals_received == 1
    assert executor._signals_executed == 0
    assert executor._signals_rejected == 1
    # Metric should have been incremented
    counters = get_counters()
    deny_keys = [k for k in counters if "execution_gate_denied" in str(k) or "execution_attempt" in str(k)]
    assert len(deny_keys) >= 1  # at least one metric touched


# ---------------------------------------------------------------------------
# Critical subscriber check
# ---------------------------------------------------------------------------

def test_check_critical_subscribers_no_bus():
    ok, details = check_critical_subscribers(None)
    assert ok is False
    assert "error" in details


def test_check_critical_subscribers_with_bus():
    # All critical topics have at least one subscriber -> all_ok True
    bus = type("Bus", (), {
        "_subscribers": {
            "swarm.idea": [lambda x: None],
            "triage.escalated": [lambda x: None],
            "council.verdict": [lambda x: None],
            "order.submitted": [lambda x: None],
        }
    })()
    ok, details = check_critical_subscribers(bus)
    assert ok is True
    assert details.get("missing") == []
    assert details.get("swarm.idea") == 1


def test_validate_outcome_resolved_requires_symbol_or_order_id():
    ok, err = validate_payload(TOPIC_OUTCOME_RESOLVED, {})
    assert ok is False
    assert err is not None
    ok, err = validate_payload(TOPIC_OUTCOME_RESOLVED, {"symbol": "AAPL"})
    assert ok is True
    ok, err = validate_payload(TOPIC_OUTCOME_RESOLVED, {"order_id": "ord-1"})
    assert ok is True


def test_run_startup_integrity_check_returns_details():
    bus = type("Bus", (), {
        "_subscribers": {
            "swarm.idea": [lambda x: None],
            "triage.escalated": [lambda x: None],
            "council.verdict": [lambda x: None],
            "order.submitted": [lambda x: None],
        }
    })()
    ok, details = run_startup_integrity_check(bus)
    assert ok is True
    assert "critical_topics" in details
    bus_empty = type("Bus", (), {"_subscribers": {}})()
    ok2, details2 = run_startup_integrity_check(bus_empty)
    assert ok2 is True  # does not fail unless FAIL_ON_CRITICAL_SUBSCRIBER_MISSING
    assert len(details2.get("missing", [])) > 0
