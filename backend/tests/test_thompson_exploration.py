"""Tests for Thompson Sampling exploration: flag in DecisionPacket and reduced position size.

Agent 8: Exploration trades must use 50% of normal position size.
Thompson sampling logic is unchanged; only the is_exploration flag is wired through.
"""
from datetime import datetime, timezone

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.council.schemas import AgentVote, DecisionPacket
from app.council.arbiter import arbitrate, get_thompson_sampler, ThompsonSampler


def _vote(name, direction="buy", confidence=0.7, veto=False, veto_reason="", weight=1.0, **meta):
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


def _full_votes(execution_ready=True):
    """Minimal votes for arbiter to produce an execution-ready BUY."""
    return [
        _vote("market_perception", "buy", weight=1.0),
        _vote("flow_perception", "buy", weight=0.8),
        _vote("regime", "buy", weight=1.2),
        _vote("hypothesis", "buy", weight=0.9),
        _vote("strategy", "buy", weight=1.0),
        _vote("risk", "buy", weight=1.5, metadata={"risk_limits": {}}),
        _vote("execution", "buy", weight=1.3, execution_ready=execution_ready),
        _vote("critic", "hold", weight=0.5, confidence=0.3),
    ]


class TestThompsonExploration:
    """Verify exploration trades use reduced position size."""

    def test_exploration_flag_in_decision_packet(self):
        """DecisionPacket should include is_exploration=True when Thompson sampling triggered."""
        mock_cal = type("Cal", (), {"get_weight_penalty": lambda self, a: 1.0})()
        with patch("app.council.arbiter._get_learned_weights", return_value={}), \
             patch("app.council.arbiter.get_thompson_sampler") as mock_ts, \
             patch("app.council.calibration.get_calibration_tracker", return_value=mock_cal), \
             patch("app.council.arbiter.get_arbiter_meta_model") as mock_meta:
            mock_ts.return_value.should_explore.return_value = True
            mock_ts.return_value.sample_weights.return_value = {}  # no weight overrides
            mock_meta.return_value.predict.return_value = None  # weighted voting path
            votes = _full_votes()
            result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.metadata.get("is_exploration") is True

    @pytest.mark.anyio
    async def test_exploration_trade_sized_down(self):
        """Exploration trades should use 50% of normal position size."""
        from app.services.order_executor import OrderExecutor
        from app.core.message_bus import get_message_bus

        bus = get_message_bus()
        executor = OrderExecutor(
            message_bus=bus,
            min_score=0,
            max_daily_trades=100,
            cooldown_seconds=0,
            max_portfolio_heat=1.0,
            auto_execute=False,
        )
        executor._daily_trade_count = 0
        executor._symbol_last_trade.clear()
        await executor.start()

        verdict_data = {
            "symbol": "AAPL",
            "final_direction": "buy",
            "final_confidence": 0.6,
            "execution_ready": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "council_decision_id": "test-id",
            "metadata": {"is_exploration": True},
            "signal_data": {
                "score": 70,
                "regime": "NEUTRAL",
                "price": 150.0,
                "source": "live",
            },
            "price": 150.0,
        }

        captured_decision = None

        async def _shadow_execute(decision):
            nonlocal captured_decision
            captured_decision = decision

        mock_alpaca = AsyncMock()
        mock_alpaca.get_account = AsyncMock(return_value={"equity": 100000})
        mock_alpaca.get_positions = AsyncMock(return_value=[])

        gov_decision = MagicMock()
        gov_decision.approved = True
        gov_decision.approved_shares = 20
        gov_decision.reason = ""
        mock_gov = MagicMock()
        mock_gov.approve.return_value = gov_decision

        mock_homeo = MagicMock()
        mock_homeo.get_position_scale.return_value = 1.0
        mock_homeo.get_mode.return_value = "NORMAL"

        with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as mock_kelly, \
             patch.object(executor, "_get_alpaca_service", return_value=mock_alpaca), \
             patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=(True, {})), \
             patch.object(executor, "_shadow_execute", side_effect=_shadow_execute), \
             patch("app.modules.openclaw.execution.risk_governor.get_governor", return_value=mock_gov), \
             patch("app.council.homeostasis.get_homeostasis", return_value=mock_homeo):
            mock_kelly.return_value = {
                "action": "BUY",
                "qty": 20,
                "kelly_pct": 0.05,
                "edge": 0.02,
                "stop_loss": 140.0,
                "take_profit": 165.0,
                "raw_kelly": 0.05,
                "stats_source": "duckdb",
                "win_rate": 0.55,
                "trade_count": 100,
            }
            await executor._on_council_verdict(verdict_data)

        await executor.stop()
        assert captured_decision is not None, "Executor should have called _shadow_execute with a decision"
        assert captured_decision.qty == 10, "Exploration trade should be 50% of 20 = 10"

    def test_exploration_rate_is_15_percent(self):
        """Thompson sampler should explore ~15% of the time."""
        with patch.object(ThompsonSampler, "_load_from_store", return_value=None):
            sampler = ThompsonSampler()
        explore_count = sum(1 for _ in range(1000) if sampler.should_explore())
        assert 100 <= explore_count <= 200, (
            f"Exploration rate should be ~15% (100-200 of 1000), got {explore_count}"
        )

    def test_exploration_outcome_feeds_back(self):
        """Exploration trade outcomes should update Thompson sampler's Beta distributions."""
        with patch.object(ThompsonSampler, "_load_from_store", return_value=None), \
             patch.object(ThompsonSampler, "_persist_to_store", return_value=None):
            sampler = ThompsonSampler()
        sampler._agent_betas["risk"] = (2.0, 2.0)
        sampler.update("risk", True)
        assert sampler._agent_betas["risk"] == (3.0, 2.0)
        sampler.update("risk", False)
        assert sampler._agent_betas["risk"] == (3.0, 3.0)
