"""Tests for Brain Service gRPC client."""
import time

import pytest

from app.services.brain_client import BrainClient, CircuitBreaker, CircuitState


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_success_resets_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN


class TestBrainClientDisabled:
    @pytest.fixture
    def client(self):
        return BrainClient(enabled=False)

    @pytest.mark.anyio
    async def test_infer_returns_stub(self, client):
        result = await client.infer("AAPL", "1d", "{}")
        assert result["confidence"] == 0.1
        assert "brain_disabled" in result["risk_flags"]
        assert result["summary"] != ""

    @pytest.mark.anyio
    async def test_critic_returns_stub(self, client):
        result = await client.critic("t-001", "AAPL")
        assert result["performance_score"] == 0.0
        assert result["analysis"] != ""

    def test_status_shows_disabled(self, client):
        status = client.get_status()
        assert status["enabled"] is False
        assert status["circuit_state"] == "closed"


class TestBrainClientEnabled:
    @pytest.fixture
    def client(self):
        """Enabled client pointed at a non-existent server."""
        return BrainClient(enabled=True, host="localhost", port=59999)

    @pytest.mark.anyio
    async def test_infer_returns_error_when_unavailable(self, client):
        result = await client.infer("AAPL", "1d", "{}")
        assert result["error"] != ""
        assert result["confidence"] <= 0.1

    @pytest.mark.anyio
    async def test_circuit_opens_after_failures(self, client):
        for _ in range(3):
            await client.infer("AAPL", "1d", "{}")
        assert client._circuit.state == CircuitState.OPEN
        result = await client.infer("AAPL", "1d", "{}")
        assert result["error"] == "circuit_breaker_open"
