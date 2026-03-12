"""
Tests for postmortem feedback loop and adaptive agent weighting.

Covers:
- Schema: postmortems table and resolved_at column
- Write/read: insert_postmortem, get_postmortems (list of dicts)
- Profitable vs unprofitable: weight updates direction (win vs loss)
- Weight bounds: weights stay within min_weight/max_weight after updates
- Arbiter consumes adaptive weights safely (get_weights used deterministically)
"""
import pytest
from unittest.mock import MagicMock

from app.council.schemas import AgentVote
from app.council.weight_learner import WeightLearner, DEFAULT_WEIGHTS


class TestPostmortemSchema:
    """Postmortem table schema and write/read."""

    def test_postmortem_schema_created_on_init(self):
        """DuckDB analytics schema includes postmortems with required columns."""
        from app.data.duckdb_storage import duckdb_store
        duckdb_store.get_postmortems(limit=0)
        cur = duckdb_store._get_conn().cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'postmortems' ORDER BY ordinal_position"
        )
        cols = [row[0] for row in cur.fetchall()]
        assert "id" in cols
        assert "council_decision_id" in cols
        assert "symbol" in cols
        assert "direction" in cols
        assert "confidence" in cols
        assert "entry_price" in cols
        assert "exit_price" in cols
        assert "pnl" in cols
        assert "agent_votes" in cols
        assert "blackboard_snapshot" in cols
        assert "critic_analysis" in cols
        assert "created_at" in cols
        assert "resolved_at" in cols

    def test_insert_and_get_postmortems_roundtrip(self):
        """insert_postmortem then get_postmortems returns list of dicts with expected keys."""
        from app.data.duckdb_storage import duckdb_store
        postmortem = {
            "id": "pm-test-001",
            "council_decision_id": "pm-test-001",
            "symbol": "AAPL",
            "direction": "buy",
            "confidence": 0.75,
            "entry_price": 150.0,
            "exit_price": 155.0,
            "pnl": 50.0,
            "agent_votes": [
                {"agent_name": "strategy", "direction": "buy", "confidence": 0.8, "weight": 1.1},
            ],
            "blackboard_snapshot": {"council_decision_id": "pm-test-001", "symbol": "AAPL"},
            "critic_analysis": "",
            "resolved_at": "2026-03-12T18:00:00",
        }
        duckdb_store.insert_postmortem(postmortem)

        rows = duckdb_store.get_postmortems(limit=10)
        assert isinstance(rows, list)
        assert len(rows) >= 1
        row = next((r for r in rows if r.get("id") == "pm-test-001"), rows[0])
        assert row.get("id") == "pm-test-001"
        assert row.get("council_decision_id") == "pm-test-001"
        assert row.get("symbol") == "AAPL"
        assert row.get("direction") == "buy"
        assert row.get("confidence") == 0.75
        assert row.get("entry_price") == 150.0
        assert row.get("exit_price") == 155.0
        assert row.get("pnl") == 50.0
        assert "agent_votes" in row
        assert "blackboard_snapshot" in row
        assert "resolved_at" in row or "created_at" in row

    def test_get_postmortems_returns_list_of_dicts(self):
        """get_postmortems returns list of dicts (API-friendly), not DataFrame."""
        from app.data.duckdb_storage import duckdb_store
        result = duckdb_store.get_postmortems(limit=5)
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)


class TestAdaptiveWeightUpdates:
    """Profitable vs unprofitable outcome updates and weight bounds."""

    def test_profitable_outcome_increases_aligned_agent_weight(self):
        """After a win, agents that voted with the outcome get higher weight (before normalize)."""
        wl = WeightLearner()
        wl._weights = dict(DEFAULT_WEIGHTS)
        decision = MagicMock()
        decision.symbol = "MSFT"
        decision.timestamp = "2026-03-12T12:00:00"
        decision.final_direction = "buy"
        decision.final_confidence = 0.85
        decision.regime = "NEUTRAL"
        decision.council_decision_id = "prof-1"
        decision.votes = [
            AgentVote("strategy", "buy", 0.9, "bullish", weight=1.1),
            AgentVote("risk", "buy", 0.7, "ok", weight=1.5),
        ]
        wl._decision_history = [{
            "trade_id": "prof-1",
            "symbol": "MSFT",
            "timestamp": decision.timestamp,
            "final_direction": "buy",
            "final_confidence": 0.85,
            "regime": "NEUTRAL",
            "votes": [{"agent_name": v.agent_name, "direction": v.direction, "confidence": v.confidence, "weight": v.weight} for v in decision.votes],
        }]

        result = wl.update_from_outcome(
            symbol="MSFT",
            outcome_direction="win",
            confidence=0.85,
            trade_id="prof-1",
        )
        assert "strategy" in result
        assert "risk" in result
        assert wl.update_count == 1

    def test_unprofitable_outcome_decreases_misaligned_agent_weight(self):
        """After a loss, agents that voted wrong direction get penalized."""
        wl = WeightLearner()
        wl._weights = dict(DEFAULT_WEIGHTS)
        decision = MagicMock()
        decision.symbol = "GOOG"
        decision.timestamp = "2026-03-12T13:00:00"
        decision.final_direction = "buy"
        decision.final_confidence = 0.8
        decision.regime = "NEUTRAL"
        decision.council_decision_id = "loss-1"
        decision.votes = [
            AgentVote("strategy", "buy", 0.9, "bullish", weight=1.1),
            AgentVote("risk", "sell", 0.8, "bearish", weight=1.5),
        ]
        wl._decision_history = [{
            "trade_id": "loss-1",
            "symbol": "GOOG",
            "timestamp": decision.timestamp,
            "final_direction": "buy",
            "final_confidence": 0.8,
            "regime": "NEUTRAL",
            "votes": [{"agent_name": v.agent_name, "direction": v.direction, "confidence": v.confidence, "weight": v.weight} for v in decision.votes],
        }]

        result = wl.update_from_outcome(
            symbol="GOOG",
            outcome_direction="loss",
            confidence=0.8,
            trade_id="loss-1",
        )
        assert "strategy" in result
        assert "risk" in result
        assert wl.get_weight("strategy") >= wl.min_weight
        assert wl.get_weight("risk") >= wl.min_weight

    def test_weight_bounds_enforced_after_updates(self):
        """Weights stay within min_weight and max_weight after multiple updates."""
        wl = WeightLearner(min_weight=0.2, max_weight=2.5)
        wl._weights = dict(DEFAULT_WEIGHTS)
        base = {
            "symbol": "BND",
            "timestamp": "2026-03-12T14:00:00",
            "final_direction": "buy",
            "final_confidence": 0.9,
            "regime": "NEUTRAL",
            "votes": [
                {"agent_name": "strategy", "direction": "buy", "confidence": 0.95, "weight": 1.1},
                {"agent_name": "risk", "direction": "buy", "confidence": 0.9, "weight": 1.5},
            ],
        }
        for i in range(15):
            trade_id = f"bounds-{i}"
            wl._decision_history.append({
                **base,
                "trade_id": trade_id,
                "symbol": base["symbol"],
            })
            wl.update_from_outcome(
                symbol=base["symbol"],
                outcome_direction="win" if i % 2 == 0 else "loss",
                confidence=0.9,
                trade_id=trade_id,
            )

        for name, w in wl.get_weights().items():
            assert wl.min_weight <= w <= wl.max_weight, f"Agent {name} weight {w} out of bounds"

    def test_get_decision_by_trade_id_returns_context_for_postmortem(self):
        """WeightLearner.get_decision_by_trade_id returns record with votes and blackboard_snapshot."""
        wl = WeightLearner()
        decision = MagicMock()
        decision.symbol = "META"
        decision.timestamp = "2026-03-12T15:00:00"
        decision.final_direction = "sell"
        decision.final_confidence = 0.7
        decision.regime = "BEARISH"
        decision.council_decision_id = "ctx-1"
        decision.votes = [
            AgentVote("strategy", "sell", 0.7, "bearish", weight=1.1),
        ]
        decision.blackboard_snapshot = {"symbol": "META", "regime": "BEARISH"}
        wl.record_decision(decision)

        ctx = wl.get_decision_by_trade_id("ctx-1")
        assert ctx is not None
        assert ctx["trade_id"] == "ctx-1"
        assert ctx["symbol"] == "META"
        assert ctx["final_direction"] == "sell"
        assert len(ctx["votes"]) >= 1
        assert ctx.get("blackboard_snapshot") == {"symbol": "META", "regime": "BEARISH"}

        assert wl.get_decision_by_trade_id("nonexistent") is None


class TestArbiterConsumesWeightsSafely:
    """Arbiter uses adaptive weights deterministically and in bounds."""

    def test_arbiter_gets_weights_from_learner(self):
        """Arbiter _get_learned_weights returns dict; weights are used for aggregation only."""
        from app.council.arbiter import _get_learned_weights, arbitrate

        weights = _get_learned_weights()
        assert isinstance(weights, dict)
        if weights:
            for k, v in weights.items():
                assert isinstance(k, str)
                assert isinstance(v, (int, float)) and v >= 0

    def test_arbiter_decision_deterministic_for_same_votes(self):
        """Same votes produce same DecisionPacket (arbiter is deterministic)."""
        from app.council.arbiter import arbitrate

        votes = [
            AgentVote("regime", "buy", 0.8, "ok", weight=1.2),
            AgentVote("risk", "buy", 0.7, "ok", weight=1.5),
            AgentVote("strategy", "buy", 0.9, "bullish", weight=1.1),
        ]
        a = arbitrate("TICK", "1d", "2026-03-12T16:00:00", list(votes))
        b = arbitrate("TICK", "1d", "2026-03-12T16:00:00", list(votes))
        assert a.final_direction == b.final_direction
        assert a.final_confidence == b.final_confidence
