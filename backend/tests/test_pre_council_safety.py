"""Tests for pre-council safety reflex: gate runs circuit breaker before council."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.anyio


async def test_pre_council_safety_fires_hold_without_invoking_council():
    """When circuit breaker fires, CouncilGate returns HOLD and does not call run_council."""
    from app.core.message_bus import get_message_bus
    from app.council.council_gate import CouncilGate

    bus = get_message_bus()
    await bus.start()
    gate = CouncilGate(
        message_bus=bus,
        gate_threshold=0.0,
        max_concurrent=2,
        cooldown_seconds=0,
    )
    await gate.start()

    verdicts = []

    async def capture_verdict(payload):
        verdicts.append(payload)

    await bus.subscribe("council.verdict", capture_verdict)

    signal_data = {
        "symbol": "TEST",
        "score": 99,
        "regime": "NEUTRAL",
        "direction": "buy",
        "close": 100.0,
    }

    with patch("app.council.reflexes.circuit_breaker.circuit_breaker") as mock_cb:
        mock_cb.check_all = AsyncMock(return_value="Market closed: weekend")
        with patch("app.council.runner.run_council", new_callable=AsyncMock) as mock_run:
            await gate._evaluate_with_council("TEST", signal_data)

            mock_cb.check_all.assert_called_once()
            mock_run.assert_not_called()

    assert len(verdicts) == 1
    v = verdicts[0]
    assert v.get("final_direction") == "hold"
    assert v.get("vetoed") is True
    assert "Pre-council safety" in str(v.get("veto_reasons", [])) or "safety" in str(v.get("council_reasoning", ""))
    assert v.get("execution_ready") is False

    await bus.unsubscribe("council.verdict", capture_verdict)
    await gate.stop()


async def test_pre_council_safety_pass_invokes_council():
    """When circuit breaker passes, CouncilGate invokes run_council."""
    from app.core.message_bus import get_message_bus
    from app.council.council_gate import CouncilGate
    from app.council.schemas import DecisionPacket, CognitiveMeta
    from datetime import datetime, timezone

    bus = get_message_bus()
    await bus.start()
    gate = CouncilGate(
        message_bus=bus,
        gate_threshold=0.0,
        max_concurrent=2,
        cooldown_seconds=0,
    )
    await gate.start()

    verdicts = []
    async def capture_verdict(payload):
        verdicts.append(payload)
    await bus.subscribe("council.verdict", capture_verdict)

    signal_data = {
        "symbol": "TEST",
        "score": 99,
        "regime": "NEUTRAL",
        "direction": "buy",
        "close": 100.0,
    }

    stub_decision = DecisionPacket(
        symbol="TEST",
        timeframe="1d",
        timestamp=datetime.now(timezone.utc).isoformat(),
        votes=[],
        final_direction="hold",
        final_confidence=0.5,
        vetoed=False,
        veto_reasons=[],
        risk_limits={},
        execution_ready=False,
        council_reasoning="Stub",
        council_decision_id="stub-id",
        cognitive=CognitiveMeta(),
    )

    mock_run = AsyncMock(return_value=stub_decision)
    with patch("app.council.reflexes.circuit_breaker.circuit_breaker") as mock_cb:
        mock_cb.check_all = AsyncMock(return_value=None)
        with patch("app.council.runner.run_council", mock_run):
            await gate._evaluate_with_council("TEST", signal_data)
            mock_cb.check_all.assert_called_once()
            mock_run.assert_called_once()

    await bus.unsubscribe("council.verdict", capture_verdict)
    await gate.stop()
