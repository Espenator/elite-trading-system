"""Tests for Arbiter weighted voting and WeightLearner Bayesian updates.

Covers: unanimous votes, split decisions, veto override, hold abstention,
regime-adaptive execution thresholds, weight learning (up/down/clamp/persist),
and long-horizon convergence over 100 decisions.
"""
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from app.council.schemas import AgentVote, DecisionPacket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AGENT_NAMES_35 = [
    "market_perception", "flow_perception", "regime", "social_perception",
    "news_catalyst", "youtube_knowledge", "intermarket",
    "gex_agent", "insider_agent", "finbert_sentiment_agent",
    "earnings_tone_agent", "dark_pool_agent", "macro_regime_agent",
    "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
    "supply_chain_agent", "institutional_flow_agent", "congressional_agent",
    "hypothesis", "layered_memory_agent",
    "strategy",
    "risk", "execution", "portfolio_optimizer_agent",
    "bull_debater", "bear_debater", "red_team",
    "critic",
    "alt_data_agent", "market_perception_agent",
    "finbert_sentiment_agent_2", "social_perception_agent",
]


def _make_vote(
    name: str,
    direction: str = "buy",
    confidence: float = 0.8,
    weight: float = 1.0,
    veto: bool = False,
    veto_reason: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> AgentVote:
    return AgentVote(
        agent_name=name,
        direction=direction,
        confidence=confidence,
        reasoning=f"{name} votes {direction}",
        veto=veto,
        veto_reason=veto_reason,
        weight=weight,
        metadata=metadata or {},
    )


def _make_35_votes(
    direction: str = "buy",
    confidence: float = 0.8,
    regime_metadata: Optional[Dict[str, Any]] = None,
    exec_ready: bool = True,
) -> List[AgentVote]:
    """Build a full 35-agent vote list with required agents properly configured."""
    votes: List[AgentVote] = []
    for name in AGENT_NAMES_35:
        meta: Dict[str, Any] = {}
        if name == "regime":
            meta = regime_metadata or {"regime_state": "NEUTRAL"}
        elif name == "execution":
            meta = {"execution_ready": exec_ready}
        elif name == "risk":
            meta = {"risk_limits": {"max_position": 5000}}
        votes.append(_make_vote(name, direction=direction, confidence=confidence, metadata=meta))
    return votes


def _make_mixed_votes(
    n_buy: int,
    n_hold: int,
    confidence: float = 0.5,
    regime_state: str = "NEUTRAL",
    exec_ready: bool = True,
) -> List[AgentVote]:
    """Build votes with n_buy agents voting buy and n_hold voting hold.

    Required agents (regime, risk, strategy, execution) always vote buy
    so the decision is not blocked by missing required agents.
    """
    votes: List[AgentVote] = []
    buy_count = 0
    for name in AGENT_NAMES_35[: n_buy + n_hold]:
        forced_buy = name in ("regime", "risk", "strategy", "execution")
        if forced_buy or buy_count < n_buy:
            direction = "buy"
            if not forced_buy:
                buy_count += 1
        else:
            direction = "hold"

        meta: Dict[str, Any] = {}
        if name == "regime":
            meta = {"regime_state": regime_state}
        elif name == "execution":
            meta = {"execution_ready": exec_ready}
        elif name == "risk":
            meta = {"risk_limits": {}}
        votes.append(_make_vote(name, direction=direction, confidence=confidence, metadata=meta))
    return votes


def _noop_thompson():
    ts = MagicMock()
    ts.should_explore.return_value = False
    ts.sample_weights.return_value = {}
    return ts


def _noop_meta_model():
    mm = MagicMock()
    mm.predict.return_value = None
    return mm


def _patch_arbiter():
    return [
        patch("app.council.arbiter._get_learned_weights", return_value={}),
        patch("app.council.arbiter.get_thompson_sampler", return_value=_noop_thompson()),
        patch("app.council.arbiter.get_arbiter_meta_model", return_value=_noop_meta_model()),
    ]


# ---------------------------------------------------------------------------
# 1. Unanimous BUY
# ---------------------------------------------------------------------------

def test_arbiter_unanimous_buy():
    """35 agents all vote BUY at 0.8 confidence -> buy with high confidence."""
    patches = _patch_arbiter()
    for p in patches:
        p.start()
    try:
        from app.council.arbiter import arbitrate

        votes = _make_35_votes("buy", 0.8, regime_metadata={"regime_state": "NEUTRAL"})
        result = arbitrate("AAPL", "1d", "2026-03-14T10:00:00Z", votes)

        assert result.final_direction == "buy"
        assert result.final_confidence > 0.7
        assert result.vetoed is False
        assert result.execution_ready is True
    finally:
        for p in patches:
            p.stop()


# ---------------------------------------------------------------------------
# 2. Split vote
# ---------------------------------------------------------------------------

def test_arbiter_split_vote():
    """18 buy vs 17 sell -> direction follows weighted majority, moderate confidence."""
    patches = _patch_arbiter()
    for p in patches:
        p.start()
    try:
        from app.council.arbiter import arbitrate

        votes: List[AgentVote] = []
        buy_names = AGENT_NAMES_35[:18]
        sell_names = AGENT_NAMES_35[18:]

        for name in buy_names:
            meta: Dict[str, Any] = {}
            if name == "regime":
                meta = {"regime_state": "NEUTRAL"}
            elif name == "execution":
                meta = {"execution_ready": True}
            elif name == "risk":
                meta = {"risk_limits": {}}
            votes.append(_make_vote(name, "buy", 0.7, metadata=meta))

        for name in sell_names:
            meta = {}
            if name == "execution":
                meta = {"execution_ready": True}
            elif name == "risk":
                meta = {"risk_limits": {}}
            votes.append(_make_vote(name, "sell", 0.7, metadata=meta))

        result = arbitrate("MSFT", "1d", "2026-03-14T10:00:00Z", votes)

        assert result.final_direction in ("buy", "sell")
        assert 0.3 < result.final_confidence < 0.9
        assert result.vetoed is False
    finally:
        for p in patches:
            p.stop()


# ---------------------------------------------------------------------------
# 3. Veto overrides majority
# ---------------------------------------------------------------------------

def test_arbiter_veto_overrides_majority():
    """Risk agent veto with 34 BUY -> hold, vetoed=True."""
    patches = _patch_arbiter()
    for p in patches:
        p.start()
    try:
        from app.council.arbiter import arbitrate

        votes = _make_35_votes("buy", 0.9, regime_metadata={"regime_state": "GREEN"})
        risk_idx = next(i for i, v in enumerate(votes) if v.agent_name == "risk")
        votes[risk_idx] = _make_vote(
            "risk", "buy", 0.9,
            veto=True, veto_reason="Max drawdown exceeded",
            metadata={"risk_limits": {}},
        )

        result = arbitrate("TSLA", "1d", "2026-03-14T10:00:00Z", votes)

        assert result.final_direction == "hold"
        assert result.vetoed is True
        assert len(result.veto_reasons) >= 1
        assert "risk" in result.veto_reasons[0]
        assert result.execution_ready is False
    finally:
        for p in patches:
            p.stop()


# ---------------------------------------------------------------------------
# 4. Hold abstention
# ---------------------------------------------------------------------------

def test_arbiter_hold_abstention():
    """All agents vote HOLD -> hold, execution_ready=False."""
    patches = _patch_arbiter()
    for p in patches:
        p.start()
    try:
        from app.council.arbiter import arbitrate

        votes = _make_35_votes("hold", 0.5, regime_metadata={"regime_state": "NEUTRAL"})

        result = arbitrate("SPY", "1d", "2026-03-14T10:00:00Z", votes)

        assert result.final_direction == "hold"
        assert result.execution_ready is False
        assert result.vetoed is False
    finally:
        for p in patches:
            p.stop()


# ---------------------------------------------------------------------------
# 5. Regime-adaptive execution threshold
# ---------------------------------------------------------------------------

def test_arbiter_regime_adaptive_threshold():
    """BULLISH threshold=0.30 passes moderate confidence; CRISIS threshold=0.70 blocks it.

    With a mix of buy/hold votes the final confidence lands ~0.57 which is
    above BULLISH's 0.30 but below CRISIS's 0.70.
    """
    patches = _patch_arbiter()
    for p in patches:
        p.start()
    try:
        from app.council.arbiter import arbitrate

        # 20 buy + 15 hold at confidence 0.5 → weighted confidence ≈ 0.57
        votes_bull = _make_mixed_votes(20, 15, 0.5, regime_state="BULLISH", exec_ready=True)
        result_bull = arbitrate("AAPL", "1d", "2026-03-14T10:00:00Z", votes_bull)

        assert result_bull.final_direction == "buy"
        assert result_bull.final_confidence > 0.30
        assert result_bull.execution_ready is True, (
            f"BULLISH threshold 0.30 should pass confidence {result_bull.final_confidence:.2f}"
        )

        votes_crisis = _make_mixed_votes(20, 15, 0.5, regime_state="CRISIS", exec_ready=True)
        result_crisis = arbitrate("AAPL", "1d", "2026-03-14T10:00:00Z", votes_crisis)

        assert result_crisis.final_confidence < 0.70, (
            f"Expected confidence < 0.70 for CRISIS, got {result_crisis.final_confidence:.2f}"
        )
        assert result_crisis.execution_ready is False, (
            f"CRISIS threshold 0.70 should block confidence {result_crisis.final_confidence:.2f}"
        )
    finally:
        for p in patches:
            p.stop()


# ---------------------------------------------------------------------------
# WeightLearner helpers
# ---------------------------------------------------------------------------

def _make_learner(**kwargs):
    """Create a WeightLearner with DuckDB mocked out."""
    from app.council.weight_learner import WeightLearner

    with patch.object(WeightLearner, "_load_from_store"):
        learner = WeightLearner(**kwargs)
    return learner


@dataclass
class _FakeDecision:
    """Minimal decision object for record_decision()."""
    symbol: str
    timestamp: str
    final_direction: str
    final_confidence: float
    votes: List[AgentVote]
    decision_id: str = ""
    regime: str = "NEUTRAL"


def _learner_update_patches(learner):
    """Context-manager patches to isolate WeightLearner from DuckDB and metrics."""
    return [
        patch.object(learner, "_persist_to_store"),
        patch.object(learner, "_store_attribution"),
        patch.object(learner, "_persist_learner_provenance"),
        patch("app.council.weight_learner.LEARNER_MIN_CONFIDENCE", 0.0),
        patch("app.core.config.settings", MagicMock(STRICT_LEARNER_INPUTS=False)),
    ]


# ---------------------------------------------------------------------------
# 6. Basic weight update (win -> upweight)
# ---------------------------------------------------------------------------

def test_weight_learner_basic_update():
    """Record decision with 3 buy-voters + 1 sell-voter, win -> buy-voters upweighted relative to sell-voter."""
    learner = _make_learner()

    learner._weights = {"agent_a": 1.0, "agent_b": 1.0, "agent_c": 1.0, "agent_d": 1.0}

    votes = [
        _make_vote("agent_a", "buy", 0.8),
        _make_vote("agent_b", "buy", 0.8),
        _make_vote("agent_c", "buy", 0.8),
        _make_vote("agent_d", "sell", 0.8),
    ]
    decision = _FakeDecision(
        symbol="AAPL", timestamp="2026-03-14T10:00:00Z",
        final_direction="buy", final_confidence=0.8,
        votes=votes, decision_id="dec-001",
    )
    learner.record_decision(decision)

    patches = _learner_update_patches(learner)
    for p in patches:
        p.start()
    try:
        learner.update_from_outcome(
            symbol="AAPL", outcome_direction="win", pnl=500,
            trade_id="dec-001", confidence=0.9,
        )
    finally:
        for p in patches:
            p.stop()

    assert learner._weights["agent_a"] > learner._weights["agent_d"], (
        "Buy-voter should have higher weight than sell-voter after win"
    )
    assert learner._weights["agent_b"] > learner._weights["agent_d"]


# ---------------------------------------------------------------------------
# 7. Loss downweights
# ---------------------------------------------------------------------------

def test_weight_learner_loss_downweights():
    """Record decision with 3 buy-voters + 1 sell-voter, loss -> buy-voters downweighted vs sell-voter."""
    learner = _make_learner()

    learner._weights = {"agent_x": 1.0, "agent_y": 1.0, "agent_z": 1.0, "agent_ctrl": 1.0}

    votes = [
        _make_vote("agent_x", "buy", 0.8),
        _make_vote("agent_y", "buy", 0.8),
        _make_vote("agent_z", "buy", 0.8),
        _make_vote("agent_ctrl", "sell", 0.8),
    ]
    decision = _FakeDecision(
        symbol="TSLA", timestamp="2026-03-14T10:00:00Z",
        final_direction="buy", final_confidence=0.8,
        votes=votes, decision_id="dec-002",
    )
    learner.record_decision(decision)

    patches = _learner_update_patches(learner)
    for p in patches:
        p.start()
    try:
        learner.update_from_outcome(
            symbol="TSLA", outcome_direction="loss", pnl=-300,
            trade_id="dec-002", confidence=0.9,
        )
    finally:
        for p in patches:
            p.stop()

    assert learner._weights["agent_x"] < learner._weights["agent_ctrl"], (
        f"Buy-voter ({learner._weights['agent_x']:.4f}) should be lower "
        f"than sell-voter ({learner._weights['agent_ctrl']:.4f}) after loss"
    )
    assert learner._weights["agent_y"] < learner._weights["agent_ctrl"]
    assert learner._weights["agent_z"] < learner._weights["agent_ctrl"]


# ---------------------------------------------------------------------------
# 8. Min/max clamp
# ---------------------------------------------------------------------------

def test_weight_learner_min_max_clamp():
    """Extreme updates are clamped to [min_weight, max_weight] before normalization."""
    learner = _make_learner(min_weight=0.2, max_weight=2.5, learning_rate=0.9)

    learner._weights = {"high_agent": 2.4, "low_agent": 0.3}

    votes = [
        _make_vote("high_agent", "buy", 1.0),
        _make_vote("low_agent", "sell", 1.0),
    ]
    decision = _FakeDecision(
        symbol="AMZN", timestamp="2026-03-14T10:00:00Z",
        final_direction="buy", final_confidence=0.9,
        votes=votes, decision_id="dec-003",
    )
    learner.record_decision(decision)

    with patch.object(learner, "_persist_to_store"), \
         patch.object(learner, "_store_attribution"), \
         patch.object(learner, "_persist_learner_provenance"), \
         patch.object(learner, "_normalize_weights"), \
         patch.object(learner, "_apply_decay"), \
         patch("app.council.weight_learner.LEARNER_MIN_CONFIDENCE", 0.0), \
         patch("app.core.config.settings", MagicMock(STRICT_LEARNER_INPUTS=False)):
        learner.update_from_outcome(
            symbol="AMZN", outcome_direction="win", pnl=1000,
            r_multiple=3.0, trade_id="dec-003", confidence=0.95,
        )

    assert learner._weights["high_agent"] <= learner.max_weight, (
        f"high_agent {learner._weights['high_agent']:.4f} should be clamped to {learner.max_weight}"
    )
    assert learner._weights["low_agent"] >= learner.min_weight, (
        f"low_agent {learner._weights['low_agent']:.4f} should be clamped to {learner.min_weight}"
    )


# ---------------------------------------------------------------------------
# 9. Persistence across restart (mocked DuckDB)
# ---------------------------------------------------------------------------

def test_weight_learner_persistence_across_restart():
    """Updated weights are loaded by a new WeightLearner instance."""
    from app.council.weight_learner import WeightLearner

    saved_rows: List = []

    def fake_persist(self_ref):
        saved_rows.clear()
        for agent, w in self_ref._weights.items():
            saved_rows.append((agent, w))

    def fake_load(self_ref):
        for name, weight in saved_rows:
            if name in self_ref._weights:
                self_ref._weights[name] = weight

    with patch.object(WeightLearner, "_load_from_store", fake_load):
        learner1 = WeightLearner()

    learner1._weights["market_perception"] = 1.75
    learner1._weights["risk"] = 0.85
    fake_persist(learner1)

    with patch.object(WeightLearner, "_load_from_store", fake_load):
        learner2 = WeightLearner()

    assert abs(learner2._weights["market_perception"] - 1.75) < 1e-6
    assert abs(learner2._weights["risk"] - 0.85) < 1e-6


# ---------------------------------------------------------------------------
# 10. Convergence over 100 decisions
# ---------------------------------------------------------------------------

def test_weight_convergence_100_decisions():
    """Agent A (80% correct) should end up with significantly higher weight than Agent B (40%)."""
    learner = _make_learner(learning_rate=0.05, min_weight=0.2, max_weight=2.5)

    learner._weights = {"agent_a": 1.0, "agent_b": 1.0}

    rng = random.Random(42)

    patches = _learner_update_patches(learner)
    for p in patches:
        p.start()
    try:
        for i in range(100):
            votes = [
                _make_vote("agent_a", "buy", 0.7),
                _make_vote("agent_b", "sell", 0.7),
            ]
            dec_id = f"conv-{i:03d}"
            decision = _FakeDecision(
                symbol="TEST", timestamp=f"2026-03-14T{10 + i // 60:02d}:{i % 60:02d}:00Z",
                final_direction="buy", final_confidence=0.7,
                votes=votes, decision_id=dec_id,
            )
            learner.record_decision(decision)

            outcome = "win" if rng.random() < 0.80 else "loss"
            learner.update_from_outcome(
                symbol="TEST", outcome_direction=outcome, pnl=100 if outcome == "win" else -100,
                trade_id=dec_id, confidence=0.9,
            )
    finally:
        for p in patches:
            p.stop()

    w_a = learner._weights.get("agent_a", 1.0)
    w_b = learner._weights.get("agent_b", 1.0)

    assert w_a > w_b, (
        f"After 100 rounds (80% win-rate), agent_a ({w_a:.4f}) "
        f"should have higher weight than agent_b ({w_b:.4f})"
    )
    assert w_a / w_b > 1.1, (
        f"Weight ratio {w_a / w_b:.2f} should be meaningfully > 1"
    )
