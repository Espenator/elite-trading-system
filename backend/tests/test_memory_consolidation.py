"""Tests for decision history and memory consolidation (Agent 5).

Verifies that decision history survives long enough for outcome matching:
- In-memory cache (500) + DuckDB fallback so swing trades can match after 30+ days.
- feedback_loop and weight_learner both use DuckDB as canonical store for matching.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from app.council.weight_learner import WeightLearner, get_weight_learner
from app.council import feedback_loop


def _make_decision(symbol: str, trade_id: str, direction: str = "buy"):
    """Minimal decision-like object for record_decision."""
    class Vote:
        def __init__(self, agent_name, direction, confidence, weight=1.0):
            self.agent_name = agent_name
            self.direction = direction
            self.confidence = confidence
            self.weight = weight
    return type("Decision", (), {
        "symbol": symbol,
        "timestamp": "2025-01-01T10:00:00Z",
        "final_direction": direction,
        "final_confidence": 0.75,
        "decision_id": trade_id,
        "council_decision_id": trade_id,
        "regime": "BULL",
        "votes": [
            Vote("regime", direction, 0.8),
            Vote("strategy", direction, 0.7),
            Vote("risk", direction, 0.6),
        ],
    })()


def _make_duckdb_row(decision_id: str, symbol: str, final_verdict: str = "buy"):
    """Build a fake DuckDB row (tuple + description) for fallback tests."""
    votes_json = json.dumps([
        {"agent": "regime", "vote": final_verdict, "confidence": 0.8},
        {"agent": "strategy", "vote": final_verdict, "confidence": 0.7},
        {"agent": "risk", "vote": final_verdict, "confidence": 0.6},
    ])
    cols = [
        "decision_id", "signal_id", "symbol", "regime", "timestamp",
        "agent_votes", "final_verdict", "final_confidence",
        "arbiter_weighted_score", "gate_threshold_used", "was_gated",
        "was_executed", "execution_result", "degraded", "homeostasis_mode",
    ]
    row = (
        decision_id,
        "",
        symbol.upper(),
        "BULL",
        "2025-01-01 10:00:00",
        votes_json,
        final_verdict,
        0.75,
        0.75,
        65.0,
        False,
        False,
        "",
        False,
        "NORMAL",
    )
    return row, cols


class TestMemoryConsolidation:
    """Verify decision history survives long enough for outcome matching."""

    def test_decision_history_truncation_point(self):
        """Identify when decisions start being lost from in-memory only."""
        learner = WeightLearner()
        # Record 600 decisions so in-memory keeps only last 500
        for i in range(600):
            dec = _make_decision(f"SYM{i}", f"trade_{i}")
            learner.record_decision(dec)
        # In-memory only has trade_100..trade_599 (500 entries); trade_0 is evicted
        assert len(learner._decision_history) == 500
        # Match for trade_599 (in memory) should succeed
        matched, source = learner._find_matching_decision("trade_599", None, "SYM599")
        assert matched is not None
        assert source == "memory"
        # Match for trade_0 from in-memory fails (evicted); without DuckDB row, source is "failed"
        matched_old, source_old = learner._find_matching_decision("trade_0", None, "SYM0")
        assert source_old in ("failed", "duckdb")
        if source_old == "failed":
            assert matched_old is None

    def test_duckdb_has_full_history(self):
        """DuckDB council_decisions table is the canonical store (no 500 cap)."""
        # Verify the fallback path exists: _find_matching_decision can return from DuckDB.
        trade_id = "test_full_hist_id"
        row, cols = _make_duckdb_row(trade_id, "FULL1", "buy")
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [row, None]
        mock_cursor.description = [(c,) for c in cols]
        mock_store = MagicMock()
        mock_store.get_thread_cursor.return_value = mock_cursor
        with patch("app.data.duckdb_storage.duckdb_store", mock_store):
            learner = WeightLearner()
            matched, source = learner._find_matching_decision(trade_id, None, "FULL1")
        assert matched is not None
        assert source == "duckdb"
        assert matched["trade_id"] == trade_id
        assert matched["symbol"] == "FULL1"

    @pytest.mark.anyio
    async def test_outcome_matches_from_duckdb_fallback(self):
        """If in-memory history truncated, fall back to DuckDB lookup."""
        trade_id = "trade_duckdb_fallback_001"
        row, cols = _make_duckdb_row(trade_id, "FBK", "buy")
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = row
        mock_cursor.description = [(c,) for c in cols]
        mock_store = MagicMock()
        mock_store.get_thread_cursor.return_value = mock_cursor
        with patch("app.data.duckdb_storage.duckdb_store", mock_store):
            learner = WeightLearner()
            learner._decision_history.clear()
            updated = learner.update_from_outcome(
                symbol="FBK",
                outcome_direction="win",
                trade_id=trade_id,
                confidence=1.0,
            )
        assert updated is not None
        assert len(updated) > 0

    def test_feedback_loop_and_weight_learner_same_history(self):
        """Both systems can resolve the same decision via DuckDB (canonical store)."""
        feedback_loop.reset_feedback()
        trade_id = "trade_shared_001"
        symbol = "SHARED"
        row, cols = _make_duckdb_row(trade_id, symbol, "buy")
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = row
        mock_cursor.description = [(c,) for c in cols]
        mock_store = MagicMock()
        mock_store.get_thread_cursor.return_value = mock_cursor
        # Patch at source so both feedback_loop and weight_learner get the same mock
        with patch("app.data.duckdb_storage.duckdb_store", mock_store):
            result = feedback_loop.record_outcome(trade_id, symbol, "win", r_multiple=1.0)
        assert "agent_stats" in result
        with patch("app.data.duckdb_storage.duckdb_store", mock_store):
            learner = WeightLearner()
            matched, source = learner._find_matching_decision(trade_id, None, symbol)
        assert matched is not None
        assert source == "duckdb"
        assert matched.get("symbol") == symbol
        assert matched.get("final_direction") == "buy"

    def test_swing_trade_outcome_30_days_later(self):
        """A trade opened 30 days ago should still match when it closes (via DuckDB)."""
        trade_id_day1 = "swing_trade_30d_001"
        symbol = "SWING"
        row, cols = _make_duckdb_row(trade_id_day1, symbol, "buy")
        learner = WeightLearner()
        for i in range(501):
            dec = _make_decision(f"OTHER{i}", f"other_trade_{i}")
            learner.record_decision(dec)
        assert len(learner._decision_history) == 500
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = row
        mock_cursor.description = [(c,) for c in cols]
        mock_store = MagicMock()
        mock_store.get_thread_cursor.return_value = mock_cursor
        with patch("app.data.duckdb_storage.duckdb_store", mock_store):
            matched, source = learner._find_matching_decision(trade_id_day1, None, symbol)
        assert matched is not None
        assert source == "duckdb"
        assert matched["trade_id"] == trade_id_day1
        assert matched["symbol"] == symbol
        with patch("app.data.duckdb_storage.duckdb_store", mock_store):
            updated = learner.update_from_outcome(
                symbol=symbol,
                outcome_direction="win",
                trade_id=trade_id_day1,
                confidence=1.0,
            )
        assert updated is not None and len(updated) > 0
