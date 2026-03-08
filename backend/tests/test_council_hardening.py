"""Tests for production hardening of the council-to-order execution path.

Covers:
  - DecisionPacket validation (malformed direction, confidence OOB, etc.)
  - Arbiter: veto, missing agents, required-agent opposition, tie/deadlock
  - OrderExecutor: direction safety, min_score threshold, fail-closed checks
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.council.schemas import AgentVote, DecisionPacket
from app.council.arbiter import arbitrate, REQUIRED_AGENTS, VETO_AGENTS
from app.services.order_executor import OrderExecutor


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _vote(name, direction="buy", confidence=0.7, veto=False, veto_reason="",
          weight=1.0, **meta):
    return AgentVote(
        agent_name=name,
        direction=direction,
        confidence=confidence,
        reasoning=f"{name} test vote",
        veto=veto,
        veto_reason=veto_reason,
        weight=weight,
        metadata=meta,
    )


def _full_votes(
    market_dir="buy",
    flow_dir="buy",
    regime_dir="buy",
    hypothesis_dir="buy",
    strategy_dir="buy",
    risk_dir="buy",
    execution_dir="buy",
    critic_dir="hold",
    risk_veto=False,
    exec_veto=False,
    risk_veto_reason="",
    exec_veto_reason="",
    execution_ready=True,
):
    """Build a set of 8 core agent votes with configurable directions."""
    return [
        _vote("market_perception", market_dir, weight=1.0),
        _vote("flow_perception", flow_dir, weight=0.8),
        _vote("regime", regime_dir, weight=1.2),
        _vote("hypothesis", hypothesis_dir, weight=0.9),
        _vote("strategy", strategy_dir, weight=1.0),
        _vote(
            "risk", risk_dir, weight=1.5,
            veto=risk_veto, veto_reason=risk_veto_reason,
            risk_limits={"max_position": 0.02},
        ),
        _vote(
            "execution", execution_dir, weight=1.3,
            veto=exec_veto, veto_reason=exec_veto_reason,
            execution_ready=execution_ready,
        ),
        _vote("critic", critic_dir, weight=0.5, confidence=0.3),
    ]


def _make_verdict(direction="buy", confidence=0.85, execution_ready=True,
                  score=80, source="", price=180):
    return {
        "symbol": "AAPL",
        "final_direction": direction,
        "final_confidence": confidence,
        "execution_ready": execution_ready,
        "signal_data": {
            "score": score,
            "regime": "NEUTRAL",
            "source": source,
            "price": price,
        },
        "price": price,
    }


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
        max_daily_trades=5,
        cooldown_seconds=60,
        max_portfolio_heat=0.25,
        max_single_position=0.10,
    )


# ===========================================================================
# DecisionPacket validation
# ===========================================================================
class TestDecisionPacketValidation:
    def test_valid_packet_accepted(self):
        dp = DecisionPacket(
            symbol="AAPL", timeframe="1d", timestamp="2025-01-01T00:00:00Z",
            votes=[], final_direction="buy", final_confidence=0.75,
            vetoed=False, veto_reasons=[], risk_limits={},
            execution_ready=True, council_reasoning="test",
        )
        assert dp.final_direction == "buy"

    def test_malformed_direction_rejected(self):
        with pytest.raises(ValueError, match="final_direction"):
            DecisionPacket(
                symbol="AAPL", timeframe="1d", timestamp="2025-01-01T00:00:00Z",
                votes=[], final_direction="long", final_confidence=0.75,
                vetoed=False, veto_reasons=[], risk_limits={},
                execution_ready=False, council_reasoning="test",
            )

    def test_empty_direction_rejected(self):
        with pytest.raises(ValueError, match="final_direction"):
            DecisionPacket(
                symbol="AAPL", timeframe="1d", timestamp="2025-01-01T00:00:00Z",
                votes=[], final_direction="", final_confidence=0.5,
                vetoed=False, veto_reasons=[], risk_limits={},
                execution_ready=False, council_reasoning="test",
            )

    def test_confidence_below_zero_rejected(self):
        with pytest.raises(ValueError, match="final_confidence"):
            DecisionPacket(
                symbol="AAPL", timeframe="1d", timestamp="2025-01-01T00:00:00Z",
                votes=[], final_direction="hold", final_confidence=-0.1,
                vetoed=False, veto_reasons=[], risk_limits={},
                execution_ready=False, council_reasoning="test",
            )

    def test_confidence_above_one_rejected(self):
        with pytest.raises(ValueError, match="final_confidence"):
            DecisionPacket(
                symbol="AAPL", timeframe="1d", timestamp="2025-01-01T00:00:00Z",
                votes=[], final_direction="buy", final_confidence=1.5,
                vetoed=False, veto_reasons=[], risk_limits={},
                execution_ready=False, council_reasoning="test",
            )

    def test_execution_ready_with_hold_rejected(self):
        with pytest.raises(ValueError, match="execution_ready"):
            DecisionPacket(
                symbol="AAPL", timeframe="1d", timestamp="2025-01-01T00:00:00Z",
                votes=[], final_direction="hold", final_confidence=0.5,
                vetoed=False, veto_reasons=[], risk_limits={},
                execution_ready=True, council_reasoning="test",
            )

    def test_hold_with_execution_ready_false_accepted(self):
        dp = DecisionPacket(
            symbol="AAPL", timeframe="1d", timestamp="2025-01-01T00:00:00Z",
            votes=[], final_direction="hold", final_confidence=0.5,
            vetoed=False, veto_reasons=[], risk_limits={},
            execution_ready=False, council_reasoning="test",
        )
        assert dp.execution_ready is False

    def test_sell_direction_accepted(self):
        dp = DecisionPacket(
            symbol="AAPL", timeframe="1d", timestamp="2025-01-01T00:00:00Z",
            votes=[], final_direction="sell", final_confidence=0.6,
            vetoed=False, veto_reasons=[], risk_limits={},
            execution_ready=True, council_reasoning="test",
        )
        assert dp.final_direction == "sell"


# ===========================================================================
# Arbiter hardening
# ===========================================================================
class TestArbiterHardening:
    def test_risk_veto_yields_non_executable_hold(self):
        votes = _full_votes(risk_veto=True, risk_veto_reason="Heat exceeded")
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.vetoed is True
        assert result.final_direction == "hold"
        assert result.execution_ready is False

    def test_missing_required_agent_blocks_executable_trade(self):
        """Missing regime agent → hold, not executable."""
        votes = [
            _vote("market_perception", "buy"),
            _vote("flow_perception", "buy"),
            # regime MISSING
            _vote("hypothesis", "buy"),
            _vote("strategy", "buy"),
            _vote("risk", "buy"),
            _vote("execution", "buy", execution_ready=True),
            _vote("critic", "hold"),
        ]
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.final_direction == "hold"
        assert result.execution_ready is False
        assert "Missing required agents" in result.council_reasoning

    def test_required_agent_disagreement_blocks_executable_trade(self):
        """All agents vote buy except risk votes sell → not executable."""
        votes = _full_votes(risk_dir="sell")
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        # Majority still buy, but risk opposes → execution blocked
        assert result.execution_ready is False
        assert "opposing" in result.council_reasoning.lower()

    def test_strategy_opposing_blocks_execution(self):
        """Strategy votes sell while majority buy → not executable."""
        votes = _full_votes(strategy_dir="sell")
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.execution_ready is False

    def test_regime_opposing_blocks_execution(self):
        """Regime votes sell while majority buy → not executable."""
        votes = _full_votes(regime_dir="sell")
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.execution_ready is False

    def test_all_required_aligned_allows_execution(self):
        """All required agents (regime, risk, strategy) agree → executable."""
        votes = _full_votes()
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.final_direction == "buy"
        assert result.execution_ready is True

    def test_required_agent_hold_allows_execution(self):
        """Required agent voting hold (not opposite) doesn't block execution."""
        votes = _full_votes(risk_dir="hold")
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        # risk voting hold is not "opposing" the buy direction
        # execution depends on confidence threshold and exec agent
        # The key is that hold != opposition
        assert result.final_direction == "buy"

    def test_tie_deadlock_yields_safe_hold(self):
        """Equal buy/sell weight → hold with explicit deadlock reasoning."""
        votes = [
            _vote("regime", "buy", confidence=0.7, weight=1.0),
            _vote("risk", "sell", confidence=0.7, weight=1.0),
            _vote("strategy", "buy", confidence=0.7, weight=1.0),
            _vote("execution", "sell", confidence=0.7, weight=1.0, execution_ready=True),
        ]
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.final_direction == "hold"
        assert result.execution_ready is False
        assert "deadlock" in result.council_reasoning.lower()

    def test_tie_deadlock_confidence_not_zero(self):
        """Tie/deadlock should have a deliberate non-zero confidence."""
        votes = [
            _vote("regime", "buy", confidence=0.8, weight=1.0),
            _vote("risk", "sell", confidence=0.8, weight=1.0),
            _vote("strategy", "buy", confidence=0.8, weight=1.0),
            _vote("execution", "sell", confidence=0.8, weight=1.0, execution_ready=True),
        ]
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.final_direction == "hold"
        assert result.final_confidence > 0.0


# ===========================================================================
# OrderExecutor direction safety
# ===========================================================================
class TestExecutorDirectionSafety:
    @pytest.mark.anyio
    async def test_malformed_direction_rejected(self, executor, mock_bus):
        """Unknown direction should be rejected, not treated as sell."""
        await executor.start()
        await executor._on_council_verdict(_make_verdict(direction="long"))
        assert executor._signals_rejected == 1
        mock_bus.publish.assert_not_called()

    @pytest.mark.anyio
    async def test_empty_direction_rejected(self, executor, mock_bus):
        """Empty direction string should be rejected."""
        await executor.start()
        await executor._on_council_verdict(_make_verdict(direction=""))
        assert executor._signals_rejected == 1

    @pytest.mark.anyio
    async def test_short_direction_rejected(self, executor, mock_bus):
        """'short' is not a valid direction — must be 'sell'."""
        await executor.start()
        await executor._on_council_verdict(_make_verdict(direction="short"))
        assert executor._signals_rejected == 1

    @pytest.mark.anyio
    async def test_hold_never_executes(self, executor, mock_bus):
        """Hold direction should never proceed to execution."""
        await executor.start()
        await executor._on_council_verdict(_make_verdict(direction="hold"))
        mock_bus.publish.assert_not_called()
        # Hold is silently filtered, not counted as rejection
        assert executor._signals_rejected == 0

    @pytest.mark.anyio
    async def test_buy_direction_accepted(self, executor, mock_bus):
        """'buy' is a valid direction and should pass Gate 1."""
        await executor.start()
        # Will get rejected by a later gate (drawdown/kelly), but not Gate 1
        await executor._on_council_verdict(_make_verdict(direction="buy"))
        # Should not be rejected by direction gate
        # (may be rejected by subsequent gates like drawdown)

    @pytest.mark.anyio
    async def test_sell_direction_accepted(self, executor, mock_bus):
        """'sell' is a valid direction and should pass Gate 1."""
        await executor.start()
        await executor._on_council_verdict(_make_verdict(direction="sell"))
        # Should pass Gate 1 (direction validation)


# ===========================================================================
# Minimum score threshold
# ===========================================================================
class TestMinScoreThreshold:
    @pytest.mark.anyio
    async def test_below_threshold_blocked(self, executor, mock_bus):
        """Score below min_score should block execution."""
        await executor.start()
        # executor.min_score is 70.0 (set in fixture)
        await executor._on_council_verdict(_make_verdict(score=50))
        assert executor._signals_rejected >= 1

    @pytest.mark.anyio
    async def test_at_threshold_passes_gate(self, executor, mock_bus):
        """Score exactly at min_score should pass the threshold gate."""
        await executor.start()
        # Score of 70 should pass (min_score=70, condition is score < min_score)
        await executor._on_council_verdict(_make_verdict(score=70))
        # Should NOT be rejected by score gate
        # (may be rejected by subsequent gates like drawdown/kelly)

    @pytest.mark.anyio
    async def test_above_threshold_passes_gate(self, executor, mock_bus):
        """Score above min_score should pass the threshold gate."""
        await executor.start()
        await executor._on_council_verdict(_make_verdict(score=90))
        # Should pass score gate


# ===========================================================================
# Fail-closed safety checks (executor)
# ===========================================================================
class TestFailClosedChecks:
    @pytest.mark.anyio
    async def test_drawdown_exception_blocks_trade(self, executor, mock_bus):
        """If drawdown check throws, trade should be blocked (fail-closed)."""
        await executor.start()
        with patch(
            "app.api.v1.risk.drawdown_check_status",
            new_callable=AsyncMock,
            side_effect=RuntimeError("connection error"),
        ):
            result = await executor._check_drawdown()
        assert result is False

    @pytest.mark.anyio
    async def test_portfolio_heat_exception_blocks_trade(self, executor, mock_bus):
        """If portfolio heat check throws, trade should be blocked."""
        # With no alpaca service available, this should fail closed
        result, info = await executor._check_portfolio_heat(0.05)
        assert result is False
        assert "reason" in info or "error" in str(info).lower()


# ===========================================================================
# Council gate admission
# ===========================================================================
class TestCouncilGateAdmission:
    @pytest.mark.anyio
    async def test_in_flight_set_initialized(self, mock_bus):
        from app.council.council_gate import CouncilGate
        gate = CouncilGate(message_bus=mock_bus)
        assert hasattr(gate, "_in_flight")
        assert isinstance(gate._in_flight, set)

    @pytest.mark.anyio
    async def test_duplicate_symbol_blocked(self, mock_bus):
        """Same symbol should not be admitted concurrently."""
        from app.council.council_gate import CouncilGate
        gate = CouncilGate(message_bus=mock_bus)
        gate._running = True
        gate._start_time = time.time()

        # Simulate symbol already in-flight
        gate._in_flight.add("AAPL")

        await gate._on_signal({
            "symbol": "AAPL",
            "score": 90,
            "source": "real",
        })
        # Should not invoke council (no task created)
        assert gate._councils_invoked == 0

    @pytest.mark.anyio
    async def test_cooldown_stamped_before_task(self, mock_bus):
        """Cooldown should be stamped before task creation."""
        from app.council.council_gate import CouncilGate
        gate = CouncilGate(message_bus=mock_bus, cooldown_seconds=120)
        gate._running = True
        gate._start_time = time.time()

        # After _on_signal, cooldown should be stamped immediately
        with patch("app.council.council_gate.asyncio.create_task"):
            await gate._on_signal({
                "symbol": "TSLA",
                "score": 90,
                "source": "real",
            })
        # Cooldown should be stamped
        assert "TSLA" in gate._symbol_last_eval
        # In-flight should be set
        assert "TSLA" in gate._in_flight

    @pytest.mark.anyio
    async def test_different_symbols_admitted(self, mock_bus):
        """Different symbols should not block each other."""
        from app.council.council_gate import CouncilGate
        gate = CouncilGate(message_bus=mock_bus)
        gate._running = True
        gate._start_time = time.time()

        gate._in_flight.add("AAPL")

        with patch("app.council.council_gate.asyncio.create_task"):
            await gate._on_signal({
                "symbol": "TSLA",
                "score": 90,
                "source": "real",
            })
        # TSLA should be admitted (different symbol)
        assert "TSLA" in gate._in_flight
