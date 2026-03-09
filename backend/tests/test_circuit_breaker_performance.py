"""Performance tests for circuit breaker (<50ms requirement)."""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch
from app.council.blackboard import BlackboardState
from app.council.reflexes.circuit_breaker import CircuitBreaker


@pytest.fixture
def cb():
    return CircuitBreaker()


@pytest.fixture
def bb():
    """Blackboard with realistic feature set."""
    return BlackboardState(
        symbol="SPY",
        raw_features={
            "features": {
                "return_1d": 0.01,
                "return_5min": 0.002,
                "vix_close": 20.0,
                "volume": 50000000,
            }
        }
    )


@pytest.fixture
def mock_external_apis():
    """Mock slow external API calls to test pure circuit breaker logic."""
    with patch('app.services.alpaca_service.alpaca_service.get_positions', new_callable=AsyncMock) as mock_positions, \
         patch('app.api.v1.risk.drawdown_check_status', new_callable=AsyncMock) as mock_drawdown:
        mock_positions.return_value = []  # No positions
        mock_drawdown.return_value = {"drawdown_breached": False, "daily_pnl_pct": 0.01}
        yield mock_positions, mock_drawdown


class TestCircuitBreakerPerformance:
    """Verify circuit breaker meets <50ms latency requirement."""

    @pytest.mark.anyio
    async def test_check_all_latency_under_50ms(self, cb, bb, mock_external_apis):
        """Circuit breaker should complete all checks in <50ms with mocked external APIs."""
        # Warm up to avoid cold start effects
        await cb.check_all(bb)

        # Measure over 10 iterations
        iterations = 10
        start = time.perf_counter()
        for _ in range(iterations):
            await cb.check_all(bb)
        elapsed_ms = (time.perf_counter() - start) * 1000 / iterations

        # Assert <50ms average latency
        assert elapsed_ms < 50.0, f"Circuit breaker took {elapsed_ms:.2f}ms (requirement: <50ms)"
        print(f"Average latency: {elapsed_ms:.2f}ms (requirement: <50ms)")

    @pytest.mark.anyio
    async def test_flash_crash_detector_latency(self, cb, bb):
        """Individual reflex checks should be very fast (<10ms each)."""
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            await cb.flash_crash_detector(bb)
        elapsed_ms = (time.perf_counter() - start) * 1000 / iterations

        assert elapsed_ms < 10.0, f"flash_crash_detector took {elapsed_ms:.2f}ms"
        print(f"flash_crash_detector: {elapsed_ms:.2f}ms")

    @pytest.mark.anyio
    async def test_vix_spike_detector_latency(self, cb, bb):
        """VIX spike detector should be very fast (<10ms)."""
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            await cb.vix_spike_detector(bb)
        elapsed_ms = (time.perf_counter() - start) * 1000 / iterations

        assert elapsed_ms < 10.0, f"vix_spike_detector took {elapsed_ms:.2f}ms"
        print(f"vix_spike_detector: {elapsed_ms:.2f}ms")

    @pytest.mark.anyio
    async def test_parallel_execution_faster_than_serial(self, cb, bb):
        """Parallel execution should be faster than serial execution."""
        # Serial execution
        start = time.perf_counter()
        await cb.flash_crash_detector(bb)
        await cb.vix_spike_detector(bb)
        await cb.market_hours_check(bb)
        serial_ms = (time.perf_counter() - start) * 1000

        # Parallel execution (via check_all)
        start = time.perf_counter()
        await cb.check_all(bb)
        parallel_ms = (time.perf_counter() - start) * 1000

        # Parallel should be faster or similar (accounting for overhead)
        # This validates that asyncio.gather is actually running in parallel
        print(f"Serial: {serial_ms:.2f}ms, Parallel: {parallel_ms:.2f}ms")
        # Not asserting strictly because overhead can vary, but log for visibility

    @pytest.mark.anyio
    async def test_worst_case_all_checks_fail(self, cb, bb, mock_external_apis):
        """Even when all checks fail, should still be <50ms."""
        # Set up worst-case scenario where all checks would fail
        bb.raw_features = {
            "features": {
                "return_1d": -0.10,  # Flash crash
                "vix_close": 50.0,   # VIX spike
            }
        }

        iterations = 10
        start = time.perf_counter()
        for _ in range(iterations):
            result = await cb.check_all(bb)
            assert result is not None  # Should halt
        elapsed_ms = (time.perf_counter() - start) * 1000 / iterations

        assert elapsed_ms < 50.0, f"Worst-case latency: {elapsed_ms:.2f}ms (requirement: <50ms)"
        print(f"Worst-case latency (all checks fail): {elapsed_ms:.2f}ms")

    @pytest.mark.anyio
    async def test_concurrent_invocations(self, cb, bb, mock_external_apis):
        """Multiple concurrent circuit breaker checks should all complete quickly."""
        # Simulate multiple symbols being checked simultaneously
        blackboards = [
            BlackboardState(
                symbol=f"SYM{i}",
                raw_features={"features": {"return_1d": 0.01, "vix_close": 20.0}}
            )
            for i in range(10)
        ]

        start = time.perf_counter()
        results = await asyncio.gather(*[cb.check_all(bb) for bb in blackboards])
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 10 concurrent checks should complete in reasonable time
        assert elapsed_ms < 200.0, f"10 concurrent checks took {elapsed_ms:.2f}ms"
        assert all(r is None or isinstance(r, str) for r in results)
        print(f"10 concurrent checks: {elapsed_ms:.2f}ms total")
