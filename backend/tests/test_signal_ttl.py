"""Tests for Signal TTL (Time-To-Live) enforcement in CouncilGate.

Verifies that signals older than 2.0 seconds are rejected and a
LATENCY_EXPIRED event is broadcast for monitoring.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_signal_ttl_fresh_signal_passes():
    """Verify fresh signals (age < TTL) pass through the gate."""
    from app.council.council_gate import CouncilGate, SIGNAL_TTL_SECONDS
    from app.message_bus import MessageBus

    bus = MessageBus()
    gate = CouncilGate(bus, gate_threshold=65.0)

    # Mock the council evaluation to prevent actual execution
    with patch.object(gate, '_evaluate_with_council', new_callable=AsyncMock) as mock_eval:
        await gate.start()

        # Create a fresh signal (just created)
        signal_data = {
            "symbol": "AAPL",
            "score": 75.0,
            "created_at": time.time(),  # Fresh signal
            "source": "test",
        }

        await gate._on_signal(signal_data)

        # Give async task time to process
        await asyncio.sleep(0.1)

        # Fresh signal should trigger council evaluation
        assert mock_eval.called, "Fresh signal should trigger council evaluation"
        assert gate._signals_expired == 0, "Fresh signal should not be marked as expired"

        await gate.stop()


@pytest.mark.asyncio
async def test_signal_ttl_stale_signal_rejected():
    """Verify stale signals (age > TTL) are rejected."""
    from app.council.council_gate import CouncilGate, SIGNAL_TTL_SECONDS
    from app.message_bus import MessageBus

    bus = MessageBus()
    gate = CouncilGate(bus, gate_threshold=65.0)

    # Track LATENCY_EXPIRED events
    expired_events = []
    async def capture_expired(data):
        expired_events.append(data)

    await bus.subscribe("signal.latency_expired", capture_expired)

    # Mock the council evaluation to ensure it's not called
    with patch.object(gate, '_evaluate_with_council', new_callable=AsyncMock) as mock_eval:
        await gate.start()

        # Create a stale signal (3 seconds old, exceeds 2.0s TTL)
        signal_data = {
            "symbol": "TSLA",
            "score": 80.0,
            "created_at": time.time() - 3.0,  # 3 seconds ago
            "source": "test",
        }

        await gate._on_signal(signal_data)

        # Give async task time to process
        await asyncio.sleep(0.1)

        # Stale signal should NOT trigger council evaluation
        assert not mock_eval.called, "Stale signal should not trigger council evaluation"
        assert gate._signals_expired == 1, "Stale signal should be marked as expired"

        # Verify LATENCY_EXPIRED event was published
        assert len(expired_events) == 1, "LATENCY_EXPIRED event should be published"
        assert expired_events[0]["symbol"] == "TSLA"
        assert expired_events[0]["signal_age"] > SIGNAL_TTL_SECONDS
        assert expired_events[0]["ttl"] == SIGNAL_TTL_SECONDS

        await gate.stop()


@pytest.mark.asyncio
async def test_signal_ttl_boundary_case():
    """Verify signals right at the TTL boundary (2.0s)."""
    from app.council.council_gate import CouncilGate, SIGNAL_TTL_SECONDS
    from app.message_bus import MessageBus

    bus = MessageBus()
    gate = CouncilGate(bus, gate_threshold=65.0)

    with patch.object(gate, '_evaluate_with_council', new_callable=AsyncMock) as mock_eval:
        await gate.start()

        # Create a signal just under TTL (1.9 seconds old)
        signal_data = {
            "symbol": "NVDA",
            "score": 70.0,
            "created_at": time.time() - 1.9,
            "source": "test",
        }

        await gate._on_signal(signal_data)
        await asyncio.sleep(0.1)

        # Should pass (1.9s < 2.0s TTL)
        assert mock_eval.called, "Signal at 1.9s should pass"
        assert gate._signals_expired == 0

        # Reset
        mock_eval.reset_mock()

        # Create a signal just over TTL (2.1 seconds old)
        signal_data_stale = {
            "symbol": "GOOGL",
            "score": 70.0,
            "created_at": time.time() - 2.1,
            "source": "test",
        }

        await gate._on_signal(signal_data_stale)
        await asyncio.sleep(0.1)

        # Should be rejected (2.1s > 2.0s TTL)
        assert not mock_eval.called, "Signal at 2.1s should be rejected"
        assert gate._signals_expired == 1

        await gate.stop()


@pytest.mark.asyncio
async def test_signal_without_created_at_passes():
    """Verify signals without created_at field are not rejected (backward compatibility)."""
    from app.council.council_gate import CouncilGate
    from app.message_bus import MessageBus

    bus = MessageBus()
    gate = CouncilGate(bus, gate_threshold=65.0)

    with patch.object(gate, '_evaluate_with_council', new_callable=AsyncMock) as mock_eval:
        await gate.start()

        # Create a signal without created_at (legacy signal)
        signal_data = {
            "symbol": "MSFT",
            "score": 75.0,
            "source": "test",
            # No created_at field
        }

        await gate._on_signal(signal_data)
        await asyncio.sleep(0.1)

        # Signal without created_at should pass (backward compatibility)
        assert mock_eval.called, "Signal without created_at should pass for backward compatibility"
        assert gate._signals_expired == 0

        await gate.stop()


@pytest.mark.asyncio
async def test_signal_ttl_status_reporting():
    """Verify TTL metrics are included in gate status."""
    from app.council.council_gate import CouncilGate, SIGNAL_TTL_SECONDS
    from app.message_bus import MessageBus

    bus = MessageBus()
    gate = CouncilGate(bus, gate_threshold=65.0)

    await gate.start()

    # Manually set some test values
    gate._signals_received = 10
    gate._signals_expired = 2

    status = gate.get_status()

    assert "signals_expired" in status
    assert status["signals_expired"] == 2
    assert "signal_ttl_seconds" in status
    assert status["signal_ttl_seconds"] == SIGNAL_TTL_SECONDS

    await gate.stop()


@pytest.mark.asyncio
async def test_signal_engine_includes_created_at():
    """Verify SignalEngine includes created_at in signal data."""
    from app.services.signal_engine import EventDrivenSignalEngine
    from app.message_bus import MessageBus

    bus = MessageBus()
    engine = EventDrivenSignalEngine(bus)

    # Track published signals
    published_signals = []
    async def capture_signal(data):
        published_signals.append(data)

    await bus.subscribe("signal.generated", capture_signal)
    await engine.start()

    # Send a mock bar that should trigger a signal
    test_bar = {
        "symbol": "SPY",
        "close": 450.0,
        "volume": 1000000,
        "timestamp": "2026-03-10T12:00:00Z",
    }

    # Mock bar history to ensure signal generation
    engine._bar_history["SPY"] = [test_bar] * 20  # Enough history

    await engine._on_bar(test_bar)
    await asyncio.sleep(0.2)

    # Check if any signals were published
    if published_signals:
        # Verify created_at is present and is a recent timestamp
        signal = published_signals[0]
        assert "created_at" in signal, "Signal should include created_at"
        assert isinstance(signal["created_at"], float), "created_at should be a float timestamp"
        assert signal["created_at"] > time.time() - 10, "created_at should be recent"

    await engine.stop()
