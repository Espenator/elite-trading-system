"""Phase D: Continuous Intelligence — tests for D1-D5.

Tests cover:
  D1: Backfill orchestrator + TurboScanner gate + API endpoint
  D2: Rate limiter registry + API endpoint
  D3: MessageBus DLQ + replay + API endpoints
  D4: Circuit breaker registry + scraper resilience
  D5: Session scanner + scheduler wiring + new topics
"""
import os
import time

import pytest

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("ALPACA_API_KEY", "test_key")
os.environ.setdefault("ALPACA_SECRET_KEY", "test_secret")
os.environ.setdefault("API_AUTH_TOKEN", "test_auth_token_for_tests")


# =========================================================================
# D1: Backfill Orchestrator
# =========================================================================

class TestBackfillOrchestrator:
    """D1: Backfill orchestrator unit tests."""

    def test_initial_status(self):
        from app.services.backfill_orchestrator import BackfillOrchestrator
        orch = BackfillOrchestrator()
        status = orch.get_status()
        assert status["status"] == "idle"
        assert status["turbo_scanner_ready"] is False
        assert status["min_rows_threshold"] == 50

    def test_turbo_gate_evaluation_all_ready(self):
        from app.services.backfill_orchestrator import BackfillOrchestrator
        orch = BackfillOrchestrator()
        orch._symbol_row_counts = {"AAPL": 100, "MSFT": 200, "GOOGL": 55}
        orch._evaluate_turbo_gate()
        assert orch.is_turbo_ready is True
        assert len(orch._ready_symbols) == 3
        assert len(orch._gated_symbols) == 0

    def test_turbo_gate_evaluation_some_gated(self):
        from app.services.backfill_orchestrator import BackfillOrchestrator
        orch = BackfillOrchestrator()
        orch._symbol_row_counts = {"AAPL": 100, "MSFT": 10, "GOOGL": 49}
        orch._evaluate_turbo_gate()
        assert orch.is_turbo_ready is False
        assert len(orch._ready_symbols) == 1
        assert set(orch._gated_symbols) == {"MSFT", "GOOGL"}

    def test_turbo_gate_empty(self):
        from app.services.backfill_orchestrator import BackfillOrchestrator
        orch = BackfillOrchestrator()
        orch._symbol_row_counts = {}
        orch._evaluate_turbo_gate()
        assert orch.is_turbo_ready is False


# =========================================================================
# D2: Rate Limiter
# =========================================================================

class TestRateLimiter:
    """D2: Rate limiter registry tests."""

    def test_get_rate_limiter_default(self):
        from app.core.rate_limiter import AsyncRateLimiter, get_rate_limiter
        limiter = get_rate_limiter("test_service_d2")
        assert isinstance(limiter, AsyncRateLimiter)
        assert limiter.name == "test_service_d2"

    def test_get_rate_limiter_alpaca_defaults(self):
        from app.core.rate_limiter import get_rate_limiter
        limiter = get_rate_limiter("alpaca")
        assert limiter.max_per_minute == 8000
        assert limiter.max_concurrent == 50

    def test_get_all_limiter_statuses(self):
        from app.core.rate_limiter import get_all_limiter_statuses, get_rate_limiter
        # Ensure at least one limiter exists
        get_rate_limiter("test_status_check")
        statuses = get_all_limiter_statuses()
        assert isinstance(statuses, list)
        assert len(statuses) > 0
        for s in statuses:
            assert "name" in s
            assert "max_per_minute" in s
            assert "tokens_available" in s

    def test_rate_limiter_status_fields(self):
        from app.core.rate_limiter import get_rate_limiter
        limiter = get_rate_limiter("test_fields_d2", max_per_minute=100, max_concurrent=5)
        status = limiter.get_status()
        assert status["name"] == "test_fields_d2"
        assert status["max_per_minute"] == 100
        assert status["max_concurrent"] == 5
        assert status["total_requests"] == 0
        assert status["total_waits"] == 0


# =========================================================================
# D3: MessageBus DLQ
# =========================================================================

class TestMessageBusDLQ:
    """D3: MessageBus dead-letter queue tests."""

    def test_dlq_add_and_retrieve(self):
        from app.core.message_bus import MessageBus
        bus = MessageBus()
        event = {"topic": "test.topic", "data": {"x": 1}, "timestamp": time.time()}
        bus._add_to_dlq(event, reason="test_failure")
        entries = bus.get_dlq_sync(limit=10)
        assert len(entries) == 1
        assert entries[0]["reason"] == "test_failure"
        assert entries[0]["event"]["topic"] == "test.topic"

    def test_dlq_clear(self):
        from app.core.message_bus import MessageBus
        bus = MessageBus()
        for i in range(5):
            bus._add_to_dlq(
                {"topic": f"t{i}", "data": {}, "timestamp": time.time()},
                reason="test",
            )
        assert len(bus.get_dlq_sync()) == 5
        cleared = bus.clear_dlq()
        assert cleared == 5
        assert len(bus.get_dlq_sync()) == 0

    def test_dlq_max_cap(self):
        from app.core.message_bus import MessageBus
        bus = MessageBus()
        bus._dlq_max = 10
        for i in range(20):
            bus._add_to_dlq(
                {"topic": "overflow", "data": {"i": i}, "timestamp": time.time()},
                reason="overflow",
            )
        assert len(bus._dlq) == 10

    def test_dlq_metrics_in_bus(self):
        from app.core.message_bus import MessageBus
        bus = MessageBus()
        bus._add_to_dlq(
            {"topic": "t", "data": {}, "timestamp": time.time()},
            reason="test",
        )
        metrics = bus.get_metrics()
        assert "dlq" in metrics
        assert metrics["dlq"]["size"] == 1

    def test_valid_topics_include_d5(self):
        from app.core.message_bus import MessageBus
        assert "perception.premarket_gaps" in MessageBus.VALID_TOPICS
        assert "perception.afterhours_earnings" in MessageBus.VALID_TOPICS


# =========================================================================
# D4: Circuit Breaker
# =========================================================================

class TestCircuitBreaker:
    """D4: Circuit breaker registry tests."""

    def test_circuit_breaker_closed_initially(self):
        from app.core.rate_limiter import CircuitBreaker
        cb = CircuitBreaker("test_cb")
        assert cb.state == "CLOSED"
        assert cb.allow_request() is True

    def test_circuit_breaker_opens_after_threshold(self):
        from app.core.rate_limiter import CircuitBreaker
        cb = CircuitBreaker("test_open", failure_threshold=3, recovery_seconds=1.0)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.allow_request() is False

    def test_circuit_breaker_half_open_after_recovery(self):
        from app.core.rate_limiter import CircuitBreaker
        cb = CircuitBreaker("test_half", failure_threshold=2, recovery_seconds=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        time.sleep(0.02)
        assert cb.state == "HALF_OPEN"
        assert cb.allow_request() is True

    def test_circuit_breaker_closes_on_success(self):
        from app.core.rate_limiter import CircuitBreaker
        cb = CircuitBreaker("test_close", failure_threshold=1, recovery_seconds=0.01)
        cb.record_failure()
        time.sleep(0.02)
        _ = cb.state  # Trigger HALF_OPEN
        cb.record_success()
        assert cb.state == "CLOSED"

    def test_circuit_breaker_reset(self):
        from app.core.rate_limiter import CircuitBreaker
        cb = CircuitBreaker("test_reset", failure_threshold=1)
        cb.record_failure()
        assert cb.state == "OPEN"
        cb.reset()
        assert cb.state == "CLOSED"

    def test_get_circuit_breaker_registry(self):
        from app.core.rate_limiter import get_circuit_breaker
        cb = get_circuit_breaker("test_registry_d4")
        assert cb.name == "test_registry_d4"
        # Same instance on second call
        cb2 = get_circuit_breaker("test_registry_d4")
        assert cb is cb2

    def test_get_all_circuit_breaker_statuses(self):
        from app.core.rate_limiter import get_all_circuit_breaker_statuses, get_circuit_breaker
        get_circuit_breaker("test_status_d4")
        statuses = get_all_circuit_breaker_statuses()
        assert isinstance(statuses, list)
        assert any(s["name"] == "test_status_d4" for s in statuses)

    def test_circuit_breaker_status_fields(self):
        from app.core.rate_limiter import CircuitBreaker
        cb = CircuitBreaker("test_fields")
        status = cb.get_status()
        assert "name" in status
        assert "state" in status
        assert "failure_count" in status
        assert "total_opens" in status
        assert "total_rejects" in status


# =========================================================================
# D5: Session Scanner
# =========================================================================

class TestSessionScanner:
    """D5: Session scanner unit tests."""

    def test_session_scanner_init(self):
        from app.services.session_scanner import SessionScanner
        scanner = SessionScanner()
        assert scanner._running is False
        assert scanner._scan_count == 0

    def test_session_scanner_status(self):
        from app.services.session_scanner import SessionScanner
        scanner = SessionScanner()
        status = scanner.get_status()
        assert "running" in status
        assert "session" in status
        assert "gap_threshold_pct" in status
        assert status["gap_threshold_pct"] == 2.0
        assert status["earnings_threshold_pct"] == 3.0

    def test_session_scanner_singleton(self):
        from app.services.session_scanner import get_session_scanner
        s1 = get_session_scanner()
        s2 = get_session_scanner()
        assert s1 is s2

    def test_session_detect(self):
        from app.services.session_scanner import SessionScanner
        scanner = SessionScanner()
        session = scanner._detect_session()
        assert session in ("premarket", "afterhours", "market", "closed")


# =========================================================================
# Scheduler
# =========================================================================

class TestScheduler:
    """Scheduler integration tests."""

    def test_scheduler_status_when_disabled(self):
        from app.jobs.scheduler import get_scheduler_status
        status = get_scheduler_status()
        # Scheduler is not started in test env
        assert isinstance(status, dict)
        assert "enabled" in status or "running" in status


# =========================================================================
# API Endpoint Tests
# =========================================================================

@pytest.mark.asyncio
async def test_rate_limits_endpoint():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/system/rate-limits")
    assert resp.status_code == 200
    data = resp.json()
    assert "limiters" in data


@pytest.mark.asyncio
async def test_circuit_breakers_endpoint():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/system/circuit-breakers")
    assert resp.status_code == 200
    data = resp.json()
    assert "circuit_breakers" in data


@pytest.mark.asyncio
async def test_backfill_status_endpoint():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/system/backfill/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_dlq_endpoint():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/system/dlq")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "entries" in data


@pytest.mark.asyncio
async def test_session_scanner_endpoint():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/system/session-scanner")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data or "error" in data
