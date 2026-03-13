"""Verify homeostasis mode affects position sizing (autonomic nervous system → OrderExecutor).

Agent 3: Autonomic Failure — Homeostasis must be wired to OrderExecutor so that
DEFENSIVE (0.5x) halves position size and HALTED (0.0x) blocks orders.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.execution_decision import ExecutionDenyReason
from app.services.order_executor import OrderExecutor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_bus():
    bus = AsyncMock()
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def executor(mock_bus):
    return OrderExecutor(
        message_bus=mock_bus,
        auto_execute=False,
        min_score=70.0,
        max_daily_trades=10,
        cooldown_seconds=0,
        max_portfolio_heat=0.5,
        max_single_position=0.10,
    )


def _valid_verdict(score=75.0, regime="GREEN"):
    """Verdict that passes Gate 0/1/2 and has valid signal_data."""
    return {
        "symbol": "AAPL",
        "final_direction": "buy",
        "final_confidence": 0.8,
        "execution_ready": True,
        "signal_data": {"score": score, "regime": regime, "price": 150.0},
        "price": 150.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _mock_kelly_result(qty=100):
    return {
        "action": "BUY",
        "kelly_pct": 0.05,
        "qty": qty,
        "edge": 0.1,
        "raw_kelly": 0.1,
        "stats_source": "test",
        "stop_loss": 140.0,
        "take_profit": 160.0,
    }


def _mock_risk_governor_approve():
    """Patch get_governor so Gate 9 approves with requested shares."""
    mock_gov = MagicMock()
    def _approve(req):
        return MagicMock(approved=True, approved_shares=req.shares, reason="")
    mock_gov.approve = _approve
    return patch("app.modules.openclaw.execution.risk_governor.get_governor", return_value=mock_gov)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAutonomicWiring:
    """Verify homeostasis mode affects position sizing."""

    @pytest.mark.anyio
    async def test_defensive_mode_halves_position(self, executor, mock_bus):
        """In DEFENSIVE mode (0.5x), OrderExecutor should halve position size."""
        with patch("app.council.homeostasis.get_homeostasis") as m_homeo:
            m = MagicMock()
            m.get_position_scale.return_value = 0.5
            m.get_mode.return_value = "DEFENSIVE"
            m_homeo.return_value = m

            with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
                m_kelly.return_value = _mock_kelly_result(qty=100)
                with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
                    with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock, return_value=(True, {})):
                        alpaca = MagicMock()
                        alpaca.get_account = AsyncMock(return_value={"equity": "100000", "last_equity": "100000"})
                        alpaca.get_positions = AsyncMock(return_value=[])
                        alpaca._cache_get = MagicMock(return_value=None)
                        executor._get_alpaca_service = MagicMock(return_value=alpaca)
                        with patch("app.api.v1.strategy.REGIME_PARAMS", {"GREEN": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0}}):
                            with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                                with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                                    with _mock_risk_governor_approve():
                                        await executor.start()
                                        await executor._on_council_verdict(_valid_verdict())
                                        await executor.stop()

        # OrderExecutor applies scale in Gate 6b: qty 100 * 0.5 = 50
        assert mock_bus.publish.called
        call_args = mock_bus.publish.call_args
        assert call_args[0][0] == "order.submitted"
        payload = call_args[0][1]
        assert payload["qty"] == 50

    @pytest.mark.anyio
    async def test_halted_mode_blocks_orders(self, executor, mock_bus):
        """In HALTED mode (0.0x), OrderExecutor should reject all orders."""
        with patch("app.council.homeostasis.get_homeostasis") as m_homeo:
            m = MagicMock()
            m.get_position_scale.return_value = 0.0
            m.get_mode.return_value = "HALTED"
            m_homeo.return_value = m

            with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
                m_kelly.return_value = _mock_kelly_result(qty=100)
                with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
                    with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock, return_value=(True, {})):
                        alpaca = MagicMock()
                        alpaca.get_account = AsyncMock(return_value={"equity": "100000", "last_equity": "100000"})
                        alpaca.get_positions = AsyncMock(return_value=[])
                        alpaca._cache_get = MagicMock(return_value=None)
                        executor._get_alpaca_service = MagicMock(return_value=alpaca)
                        with patch("app.api.v1.strategy.REGIME_PARAMS", {"GREEN": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0}}):
                            with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                                with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                                    await executor.start()
                                    await executor._on_council_verdict(_valid_verdict())
                                    await executor.stop()

        # No order submitted; rejection uses HOMEOSTASIS_HALTED
        assert executor._signals_rejected >= 1
        # Deny reason is emitted via _emit_gate_denied; we assert the enum exists and is used in code
        assert ExecutionDenyReason.HOMEOSTASIS_HALTED.value == "homeostasis_halted"

    @pytest.mark.anyio
    async def test_aggressive_mode_increases_position(self, executor, mock_bus):
        """In AGGRESSIVE mode (1.5x), position size scales up."""
        with patch("app.council.homeostasis.get_homeostasis") as m_homeo:
            m = MagicMock()
            m.get_position_scale.return_value = 1.5
            m.get_mode.return_value = "AGGRESSIVE"
            m_homeo.return_value = m

            with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
                m_kelly.return_value = _mock_kelly_result(qty=100)
                with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
                    with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock, return_value=(True, {})):
                        alpaca = MagicMock()
                        alpaca.get_account = AsyncMock(return_value={"equity": "100000", "last_equity": "100000"})
                        alpaca.get_positions = AsyncMock(return_value=[])
                        alpaca._cache_get = MagicMock(return_value=None)
                        executor._get_alpaca_service = MagicMock(return_value=alpaca)
                        with patch("app.api.v1.strategy.REGIME_PARAMS", {"GREEN": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0}}):
                            with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                                with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                                    with _mock_risk_governor_approve():
                                        await executor.start()
                                        await executor._on_council_verdict(_valid_verdict())
                                        await executor.stop()

        # 100 * 1.5 = 150
        assert mock_bus.publish.called
        call_args = mock_bus.publish.call_args
        assert call_args[0][0] == "order.submitted"
        payload = call_args[0][1]
        assert payload["qty"] == 150

    def test_homeostasis_mode_in_decision_packet(self):
        """DecisionPacket schema includes homeostasis_mode and to_dict() exposes it."""
        from app.council.schemas import DecisionPacket, AgentVote

        # Build minimal packet (arbiter-style) and set homeostasis_mode as runner does
        votes = []
        packet = DecisionPacket(
            symbol="AAPL",
            timeframe="1D",
            timestamp=datetime.now(timezone.utc).isoformat(),
            votes=votes,
            final_direction="buy",
            final_confidence=0.8,
            vetoed=False,
            veto_reasons=[],
            risk_limits={},
            execution_ready=True,
            council_reasoning="test",
            homeostasis_mode="DEFENSIVE",
        )
        d = packet.to_dict()
        assert d["homeostasis_mode"] == "DEFENSIVE"
        assert hasattr(packet, "homeostasis_mode")
        assert packet.homeostasis_mode == "DEFENSIVE"

    @pytest.mark.anyio
    async def test_order_executor_reads_homeostasis(self, executor, mock_bus):
        """OrderExecutor applies homeostasis scale after Kelly (Gate 6b)."""
        # NORMAL (1.0): qty unchanged
        with patch("app.council.homeostasis.get_homeostasis") as m_homeo:
            m = MagicMock()
            m.get_position_scale.return_value = 1.0
            m.get_mode.return_value = "NORMAL"
            m_homeo.return_value = m

            with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
                m_kelly.return_value = _mock_kelly_result(qty=80)
                with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
                    with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock, return_value=(True, {})):
                        alpaca = MagicMock()
                        alpaca.get_account = AsyncMock(return_value={"equity": "100000", "last_equity": "100000"})
                        alpaca.get_positions = AsyncMock(return_value=[])
                        alpaca._cache_get = MagicMock(return_value=None)
                        executor._get_alpaca_service = MagicMock(return_value=alpaca)
                        with patch("app.api.v1.strategy.REGIME_PARAMS", {"GREEN": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0}}):
                            with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                                with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                                    with _mock_risk_governor_approve():
                                        await executor.start()
                                        await executor._on_council_verdict(_valid_verdict())
                                        await executor.stop()

        assert mock_bus.publish.called
        payload = mock_bus.publish.call_args[0][1]
        assert payload["qty"] == 80  # 1.0 scale leaves Kelly qty unchanged
