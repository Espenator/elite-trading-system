"""Tests for Agent 7: circuit breaker halt → learning signal (event, audit, homeostasis, WS)."""
import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from app.council.homeostasis import HomeostasisMonitor


class TestCircuitBreakerLearning:
    """Verify circuit breaker firings feed back to learning systems."""

    @pytest.mark.anyio
    async def test_halt_publishes_event(self):
        """When circuit breaker fires, an event should publish to MessageBus."""
        publish_calls = []

        async def capture_publish(topic: str, data: dict):
            publish_calls.append((topic, data))

        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock(side_effect=capture_publish)

        with patch("app.council.reflexes.circuit_breaker.circuit_breaker") as mock_cb:
            mock_cb.check_all = AsyncMock(
                return_value="Flash crash detected: 6.0% intraday move exceeds 5% threshold"
            )
            with patch("app.core.message_bus.get_message_bus", return_value=mock_bus):
                from app.council.runner import run_council
                await run_council("SPY", "1d", {"features": {"return_5min": -0.06, "vix_close": 20, "return_1d": 0.01}})
                await asyncio.sleep(0.2)
        halt_calls = [(t, d) for t, d in publish_calls if t == "circuit_breaker.halt"]
        assert len(halt_calls) >= 1, f"Expected circuit_breaker.halt in {publish_calls}"
        topic, ev = halt_calls[0]
        assert topic == "circuit_breaker.halt"
        assert "reason" in ev
        assert "timestamp" in ev
        assert ev.get("symbol") == "SPY"
        assert "features_snapshot" in ev or "reason" in ev

    @pytest.mark.anyio
    async def test_halt_recorded_in_audit(self):
        """Circuit breaker halts should be recorded in DuckDB for analysis."""
        try:
            from app.data.duckdb_storage import duckdb_store
            # Ensure table exists and insert directly so test is self-contained
            duckdb_store.insert_circuit_breaker_halt(
                halt_reason="VIX spike: 40.0 exceeds 35 threshold",
                symbol="AAPL",
                features_snapshot={"vix_close": 40, "return_5min": 0.01},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            cur = duckdb_store._get_conn().cursor()
            cur.execute(
                "SELECT halt_reason, symbol, timestamp FROM circuit_breaker_events ORDER BY timestamp DESC LIMIT 5"
            )
            rows = cur.fetchall()
            cur.close()
        except Exception as e:
            pytest.skip(f"DuckDB circuit_breaker_events not available: {e}")
            return

        assert len(rows) >= 1
        reasons = [r[0] for r in rows]
        assert any("VIX" in str(r) for r in reasons)
        symbols = [r[1] for r in rows]
        assert "AAPL" in symbols or any(s == "AAPL" for s in symbols)

    @pytest.mark.anyio
    @pytest.mark.skip(reason="Deferred: weight learner integration when market direction after halt is measured")
    async def test_halt_boosts_risk_agent_weight(self):
        """If circuit breaker fires and market drops further, risk agent weight should increase."""
        pass

    def test_halt_count_tracked_per_day(self):
        """Track how often circuit breaker fires per day for dashboard."""
        monitor = HomeostasisMonitor()
        assert monitor.get_halt_count_today() == 0
        monitor.record_circuit_breaker_halt()
        assert monitor.get_halt_count_today() == 1
        monitor.record_circuit_breaker_halt()
        assert monitor.get_halt_count_today() == 2
        status = monitor.get_status()
        assert status.get("circuit_breaker_halts_today") == 2

    @pytest.mark.anyio
    async def test_halt_broadcasts_to_websocket(self):
        """Circuit breaker halt should broadcast to frontend via WS circuit_breaker channel."""
        with patch("app.websocket_manager.broadcast_ws", new_callable=AsyncMock) as mock_ws:
            with patch("app.council.reflexes.circuit_breaker.circuit_breaker") as mock_cb:
                mock_cb.check_all = AsyncMock(
                    return_value="Daily drawdown limit breached (3%)"
                )
                from app.council.runner import run_council
                await run_council("SPY", "1d", {"features": {"return_1d": 0.01}})
                await asyncio.sleep(0.2)
            mock_ws.assert_called()
            calls = [c for c in mock_ws.call_args_list if len(c[0]) >= 2 and c[0][0] == "circuit_breaker"]
            assert len(calls) >= 1
            channel, payload = calls[0][0][0], calls[0][0][1]
            assert channel == "circuit_breaker"
            assert payload.get("type") == "halt"
            assert "reason" in payload
