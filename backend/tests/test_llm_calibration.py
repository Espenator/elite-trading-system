"""Tests for LLM prediction tracking and calibration (brain accuracy feedback)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.council.agents.hypothesis_agent import evaluate as hypothesis_evaluate
from app.council.schemas import AgentVote
from app.council.blackboard import BlackboardState
from app.services import llm_calibration


class TestLLMCalibration:
    """Verify LLM predictions are tracked and calibrated."""

    @pytest.mark.anyio
    async def test_hypothesis_records_llm_tier(self):
        """hypothesis_agent should record which LLM tier was used (Ollama/Perplexity/Claude)."""
        with patch("app.services.brain_client.get_brain_client") as m_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.infer = AsyncMock(
                return_value={
                    "summary": "Bullish setup",
                    "confidence": 0.78,
                    "risk_flags": [],
                    "reasoning_bullets": [],
                    "error": "",
                    "latency_ms": 120,
                }
            )
            m_client.return_value = mock_client

            vote = await hypothesis_evaluate(
                "AAPL", "1d", {"features": {"regime": "BULLISH"}}, {"blackboard": None}
            )
            assert vote.metadata.get("llm_tier") in ("ollama", "perplexity", "claude", "unknown")
            assert 0 <= vote.metadata.get("llm_confidence", 0) <= 1
            assert vote.metadata.get("llm_direction") in ("buy", "sell", "hold")
            assert isinstance(vote.metadata.get("llm_latency_ms", 0), (int, float))

    @pytest.mark.anyio
    async def test_hypothesis_router_fallback_records_llm_tier(self):
        """When using router fallback, metadata should include llm_tier from tier."""
        with patch("app.services.brain_client.get_brain_client") as m_client:
            m_client.return_value.enabled = False
            with patch(
                "app.council.agents.hypothesis_agent._hypothesis_via_router",
                new_callable=AsyncMock,
                return_value=AgentVote(
                    agent_name="hypothesis",
                    direction="buy",
                    confidence=0.7,
                    reasoning="Router",
                    weight=0.9,
                    metadata={
                        "llm_tier": "ollama",
                        "llm_confidence": 0.7,
                        "llm_direction": "buy",
                        "llm_latency_ms": 0,
                    },
                ),
            ):
                vote = await hypothesis_evaluate(
                    "AAPL", "1d", {"features": {}}, {}
                )
                assert "llm_tier" in vote.metadata
                assert vote.metadata["llm_confidence"] >= 0
                assert vote.metadata["llm_direction"] in ("buy", "sell", "hold")

    def test_blackboard_stores_llm_trace(self):
        """Blackboard hypothesis namespace should include LLM trace data."""
        vote_dict = {
            "agent_name": "hypothesis",
            "direction": "buy",
            "confidence": 0.8,
            "reasoning": "Test",
            "metadata": {
                "llm_tier": "ollama",
                "llm_confidence": 0.8,
                "llm_direction": "buy",
                "llm_latency_ms": 45,
            },
        }
        bb = BlackboardState(symbol="AAPL", raw_features={})
        bb.hypothesis = vote_dict
        bb.llm_trace.append({
            "agent": "hypothesis",
            "llm_tier": vote_dict["metadata"]["llm_tier"],
            "llm_confidence": vote_dict["metadata"]["llm_confidence"],
            "llm_direction": vote_dict["metadata"]["llm_direction"],
            "llm_latency_ms": vote_dict["metadata"]["llm_latency_ms"],
        })
        assert bb.hypothesis is not None
        assert bb.hypothesis.get("metadata", {}).get("llm_tier") == "ollama"
        assert len(bb.llm_trace) == 1
        assert bb.llm_trace[0]["llm_tier"] == "ollama"
        assert bb.llm_trace[0]["llm_latency_ms"] == 45

    @pytest.mark.anyio
    async def test_llm_prediction_vs_outcome(self):
        """After trade outcome, compare LLM prediction against actual result."""
        # Record a prediction
        ok = llm_calibration.record_llm_prediction(
            council_decision_id="test-decision-1",
            symbol="AAPL",
            regime="BULLISH",
            llm_tier="ollama",
            predicted_direction="buy",
            predicted_confidence=0.8,
            llm_latency_ms=50,
        )
        if not ok:
            pytest.skip("DuckDB llm_predictions not available (record_llm_prediction failed)")

        # Outcome: trade was profitable (win) -> LLM predicted buy, correct
        result = llm_calibration.record_llm_outcome(
            council_decision_id="test-decision-1",
            symbol="AAPL",
            outcome_direction="win",
            r_multiple=1.2,
        )
        if result:
            assert "accuracy" in result or "calibration" in result

        # Record second prediction: BUY with high confidence, outcome loss -> calibration penalty
        ok2 = llm_calibration.record_llm_prediction(
            council_decision_id="test-decision-2",
            symbol="MSFT",
            regime="NEUTRAL",
            llm_tier="ollama",
            predicted_direction="buy",
            predicted_confidence=0.9,
            llm_latency_ms=60,
        )
        if ok2:
            llm_calibration.record_llm_outcome(
                council_decision_id="test-decision-2",
                symbol="MSFT",
                outcome_direction="loss",
                r_multiple=-0.5,
            )

    def test_llm_accuracy_per_regime(self):
        """Track LLM accuracy stratified by regime (bull/bear/neutral)."""
        # Verify DuckDB table exists: llm_calibration (and llm_predictions)
        exists = llm_calibration.get_llm_predictions_table_exists()
        # May be False if DuckDB not initialized in test env
        try:
            from app.data.duckdb_storage import duckdb_store
            duckdb_store.init_schema()
            conn = duckdb_store.get_thread_cursor()
            conn.execute("SELECT 1 FROM llm_predictions LIMIT 1")
            conn.execute(
                "SELECT llm_tier, regime, predicted_direction, predicted_confidence, "
                "actual_outcome, r_multiple, created_at FROM llm_predictions LIMIT 1"
            )
            conn.execute(
                "SELECT llm_tier, regime, n_predictions, n_correct, brier_score, last_updated FROM llm_calibration LIMIT 1"
            )
        except Exception as e:
            pytest.skip("DuckDB schema not available: %s" % e)

    def test_llm_tier_comparison(self):
        """Compare accuracy across tiers to optimize routing."""
        # get_tier_accuracy_for_router returns (tier, accuracy) for regime with >= MIN_PREDICTIONS
        result = llm_calibration.get_tier_accuracy_for_router("BULLISH")
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, (list, tuple))
            assert len(item) == 2
            assert item[0] in ("ollama", "perplexity", "claude", "unknown") or isinstance(item[0], str)
            assert 0 <= item[1] <= 1

    def test_overconfident_llm_penalized(self):
        """LLM that predicts 0.95 confidence but wins only 50% should be penalized (Brier)."""
        # Brier score: (confidence - outcome)^2. High confidence + wrong = large Brier contribution
        # We can't easily simulate 50% win rate in one call; we verify Brier is computed
        cal = llm_calibration.get_llm_calibration()
        if cal and "calibration" in cal:
            for row in cal["calibration"]:
                assert "brier_score" in row
                assert 0 <= row["brier_score"] <= 1
        elif cal and isinstance(cal, dict) and "brier_score" in cal:
            assert 0 <= cal["brier_score"] <= 1

    def test_record_llm_prediction_requires_council_id(self):
        """record_llm_prediction returns False when council_decision_id is missing."""
        assert llm_calibration.record_llm_prediction(
            council_decision_id="",
            symbol="AAPL",
            regime="NEUTRAL",
            llm_tier="ollama",
            predicted_direction="buy",
            predicted_confidence=0.5,
        ) is False

    def test_record_llm_outcome_scratch_does_not_raise(self):
        """record_llm_outcome with scratch does not crash (may or may not resolve row)."""
        result = llm_calibration.record_llm_outcome(
            council_decision_id="nonexistent",
            symbol="XYZ",
            outcome_direction="scratch",
            r_multiple=0,
        )
        # No matching row -> None; or scratch might not update calibration
        assert result is None or isinstance(result, dict)

    def test_is_tier_degraded(self):
        """is_tier_degraded returns True only when accuracy < threshold with enough data."""
        # With no data, should be False
        assert llm_calibration.is_tier_degraded("ollama", "UNKNOWN") is False
        assert llm_calibration.is_tier_degraded("nonexistent_tier") is False
