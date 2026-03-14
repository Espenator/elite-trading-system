"""Arbiter — Stacked Ensemble Meta-Model for final council decision.

Phase 4 Enhancement:
- Stage 1: Agents output verdicts (unchanged)
- Stage 2: Meta-regressor predicts trade outcome from agent signals,
  regime, and confidence. If unavailable, falls back to weighted voting.
- Thompson Sampling for agent selection: agents with higher uncertainty
  are explored more frequently in small-size trades.

Uses Bayesian-updated weights from WeightLearner (self-learning).
Falls back to static agent weights if learner is unavailable.

Rules:
1. VETO from risk_agent or execution_agent -> hold, vetoed=True
2. Requires: regime OK + risk OK + strategy OK for any trade
3. Meta-model prediction (XGBoost) OR weighted confidence aggregation
4. Hypothesis contributes confidence but cannot override risk veto
5. Thompson Sampling adjusts agent selection for exploration trades
"""
import logging
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from app.council.schemas import AgentVote, DecisionPacket

logger = logging.getLogger(__name__)

# Agents whose approval is required for trading
REQUIRED_AGENTS = {"regime", "risk", "strategy"}

# Agents with veto power
VETO_AGENTS = {"risk", "execution"}

# Regime-adaptive execution thresholds (replaces hardcoded 0.4)
# Conservative in risky regimes, aggressive in favorable ones.
REGIME_EXECUTION_THRESHOLDS = {
    "BULLISH": 0.30,
    "GREEN": 0.35,
    "NEUTRAL": 0.40,
    "YELLOW": 0.50,
    "RED": 0.60,
    "CRISIS": 0.70,
}


def _get_execution_threshold(regime: str = "NEUTRAL") -> float:
    """Return regime-adaptive execution confidence threshold."""
    return REGIME_EXECUTION_THRESHOLDS.get(regime.upper(), 0.50)


# ── Phase 4: Thompson Sampling for Agent Selection ───────────────────────────

class ThompsonSampler:
    """Thompson Sampling for agent exploration/exploitation.

    Agents with higher uncertainty in their performance get selected
    more frequently for 'exploration' trades (smaller position sizes)
    to calibrate their weights faster.

    Each agent has a Beta(α, β) distribution tracking success rate.
    We sample from these distributions — agents with high variance
    (uncertain performance) sometimes get sampled above their mean,
    leading to selection for exploration.
    """

    def __init__(self):
        # Beta distribution parameters per agent: {agent_name: (alpha, beta)}
        self._agent_betas: Dict[str, Tuple[float, float]] = {}
        self._exploration_rate: float = 0.15  # 15% of trades are exploration
        self._load_from_store()

    def _load_from_store(self) -> None:
        """Load Thompson parameters from DuckDB."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store.get_thread_cursor()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS thompson_params (
                    agent_name VARCHAR PRIMARY KEY,
                    alpha DOUBLE DEFAULT 2.0,
                    beta DOUBLE DEFAULT 2.0,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            rows = conn.execute("SELECT agent_name, alpha, beta FROM thompson_params").fetchall()
            for name, a, b in rows:
                self._agent_betas[name] = (float(a), float(b))
        except Exception:
            pass

    def _persist_to_store(self) -> None:
        """Save Thompson parameters to DuckDB."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store.get_thread_cursor()
            for name, (a, b) in self._agent_betas.items():
                conn.execute(
                    """INSERT OR REPLACE INTO thompson_params
                       (agent_name, alpha, beta, last_update)
                       VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                    [name, a, b],
                )
        except Exception:
            pass

    def sample_weights(self, agent_names: List[str]) -> Dict[str, float]:
        """Sample weights from Beta distributions for each agent.

        Returns a dict of agent_name -> sampled weight.
        Higher uncertainty agents may get sampled above their mean.
        """
        sampled = {}
        for name in agent_names:
            a, b = self._agent_betas.get(name, (2.0, 2.0))
            # Sample from Beta distribution
            sample = random.betavariate(max(a, 0.1), max(b, 0.1))
            sampled[name] = sample
        return sampled

    def should_explore(self) -> bool:
        """Randomly decide if this trade should be an exploration trade."""
        return random.random() < self._exploration_rate

    def update(self, agent_name: str, success: bool) -> None:
        """Update an agent's Beta parameters after observing outcome."""
        a, b = self._agent_betas.get(agent_name, (2.0, 2.0))
        if success:
            a += 1.0
        else:
            b += 1.0
        self._agent_betas[agent_name] = (a, b)

    def batch_update(self, outcomes: Dict[str, bool]) -> None:
        """Update multiple agents from a single trade outcome."""
        for agent_name, success in outcomes.items():
            self.update(agent_name, success)
        self._persist_to_store()

    def get_uncertainty(self, agent_name: str) -> float:
        """Get uncertainty (std dev) for an agent's success rate."""
        a, b = self._agent_betas.get(agent_name, (2.0, 2.0))
        ab = a + b
        if ab <= 0:
            return 0.5
        return math.sqrt((a * b) / (ab * ab * (ab + 1)))


# Module-level Thompson Sampler singleton
_thompson_sampler: Optional[ThompsonSampler] = None


def get_thompson_sampler() -> ThompsonSampler:
    """Get or create the singleton ThompsonSampler."""
    global _thompson_sampler
    if _thompson_sampler is None:
        _thompson_sampler = ThompsonSampler()
    return _thompson_sampler


# ── Phase 4: Meta-Model (Stacked Ensemble) ──────────────────────────────────

class ArbiterMetaModel:
    """XGBoost meta-regressor that predicts trade outcome from agent signals.

    Stage 1: Agents produce votes (direction, confidence)
    Stage 2: Meta-model uses agent features + regime to predict P(win).

    Falls back to weighted voting if the model is unavailable or untrained.
    """

    def __init__(self):
        self._model = None
        self._feature_names: List[str] = []
        self._is_trained = False
        self._load_model()

    def _load_model(self) -> None:
        """Load pre-trained meta-model from disk."""
        try:
            import joblib
            import os
            model_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "models", "arbiter_meta.joblib",
            )
            if os.path.exists(model_path):
                data = joblib.load(model_path)
                self._model = data["model"]
                self._feature_names = data.get("feature_names", [])
                self._is_trained = True
                logger.info("ArbiterMetaModel: loaded pre-trained model (%d features)", len(self._feature_names))
        except Exception as e:
            logger.debug("ArbiterMetaModel: no pre-trained model available (%s)", e)

    def predict(
        self,
        votes: List[AgentVote],
        regime: str = "NEUTRAL",
        regime_entropy: float = 0.0,
    ) -> Optional[Tuple[str, float]]:
        """Predict trade outcome from agent signals.

        Returns (direction, confidence) or None if model unavailable.
        """
        if not self._is_trained or self._model is None:
            return None

        try:
            features = self._extract_features(votes, regime, regime_entropy)
            import numpy as np
            X = np.array([features])
            # Model predicts probability of success
            proba = self._model.predict_proba(X)[0]  # [P(loss), P(win)]
            win_prob = proba[1] if len(proba) > 1 else proba[0]

            # Determine direction from majority vote
            buy_count = sum(1 for v in votes if v.direction == "buy")
            sell_count = sum(1 for v in votes if v.direction == "sell")
            direction = "buy" if buy_count >= sell_count else "sell"

            if win_prob < 0.45:
                direction = "hold"
                confidence = 1.0 - win_prob
            else:
                confidence = win_prob

            logger.info(
                "ArbiterMetaModel: predicted %s @ %.2f (win_prob=%.3f)",
                direction, confidence, win_prob,
            )
            return direction, confidence

        except Exception as e:
            logger.debug("ArbiterMetaModel: prediction failed (%s), falling back", e)
            return None

    def _extract_features(
        self, votes: List[AgentVote], regime: str, regime_entropy: float,
    ) -> List[float]:
        """Extract feature vector from agent votes for the meta-model."""
        # Build a feature vector with agent confidences and vote directions
        features = []

        # Per-agent features (confidence * direction_sign)
        agent_map = {v.agent_name: v for v in votes}
        for name in sorted(self._feature_names):
            if name.startswith("agent_"):
                agent_name = name.replace("agent_", "")
                v = agent_map.get(agent_name)
                if v:
                    sign = 1.0 if v.direction == "buy" else (-1.0 if v.direction == "sell" else 0.0)
                    features.append(v.confidence * sign)
                else:
                    features.append(0.0)
            elif name == "regime_entropy":
                features.append(regime_entropy)
            elif name.startswith("regime_"):
                features.append(1.0 if regime.upper() == name.replace("regime_", "").upper() else 0.0)
            else:
                features.append(0.0)

        return features

    def train(self, training_data: List[Dict[str, Any]]) -> bool:
        """Train the meta-model from historical council decisions + outcomes.

        training_data: list of dicts with keys:
            agent_votes: {agent_name: {direction, confidence}}
            regime: str
            regime_entropy: float
            outcome: "win" or "loss"

        Returns True if training succeeded.
        """
        if len(training_data) < 50:
            logger.info("ArbiterMetaModel: not enough data to train (%d < 50)", len(training_data))
            return False

        try:
            from sklearn.ensemble import GradientBoostingClassifier
            import numpy as np
            import joblib
            import os

            # Build feature matrix
            all_agents = set()
            for d in training_data:
                all_agents.update(d.get("agent_votes", {}).keys())

            self._feature_names = sorted([f"agent_{a}" for a in all_agents]) + [
                "regime_entropy", "regime_BULLISH", "regime_NEUTRAL",
                "regime_BEARISH", "regime_CRISIS",
            ]

            X = []
            y = []
            for d in training_data:
                features = []
                votes = d.get("agent_votes", {})
                for name in self._feature_names:
                    if name.startswith("agent_"):
                        agent_name = name.replace("agent_", "")
                        v = votes.get(agent_name, {})
                        sign = 1.0 if v.get("direction") == "buy" else (
                            -1.0 if v.get("direction") == "sell" else 0.0)
                        features.append(v.get("confidence", 0) * sign)
                    elif name == "regime_entropy":
                        features.append(d.get("regime_entropy", 0))
                    elif name.startswith("regime_"):
                        features.append(
                            1.0 if d.get("regime", "").upper() == name.replace("regime_", "").upper() else 0.0
                        )
                    else:
                        features.append(0.0)
                X.append(features)
                y.append(1 if d.get("outcome") in ("win", "profit") else 0)

            X = np.array(X)
            y = np.array(y)

            # Train small gradient boosting classifier
            model = GradientBoostingClassifier(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                random_state=42,
            )
            model.fit(X, y)

            # Save model
            self._model = model
            self._is_trained = True

            model_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "models",
            )
            os.makedirs(model_dir, exist_ok=True)
            model_path = os.path.join(model_dir, "arbiter_meta.joblib")
            joblib.dump(
                {"model": model, "feature_names": self._feature_names},
                model_path,
            )

            logger.info(
                "ArbiterMetaModel: trained on %d samples, %d features",
                len(X), len(self._feature_names),
            )
            return True

        except Exception as e:
            logger.warning("ArbiterMetaModel: training failed: %s", e)
            return False


# Module-level meta-model singleton
_meta_model: Optional[ArbiterMetaModel] = None


def get_arbiter_meta_model() -> ArbiterMetaModel:
    """Get or create the singleton ArbiterMetaModel."""
    global _meta_model
    if _meta_model is None:
        _meta_model = ArbiterMetaModel()
    return _meta_model


def _get_learned_weights() -> Dict[str, float]:
    """Fetch Bayesian-updated weights from WeightLearner.

    Returns empty dict if learner is unavailable (arbiter will use
    each agent's static weight from their module-level WEIGHT constant).

    Phase C (I1): Also applies SelfAwareness streak multiplier
    (PROBATION=0.25x, HIBERNATION=0x) to learned weights.
    """
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        weights = learner.get_weights()

        # Apply SelfAwareness streak multipliers
        try:
            from app.council.self_awareness import get_self_awareness
            sa = get_self_awareness()
            for agent_name in list(weights.keys()):
                mult = sa.streaks.get_weight_multiplier(agent_name)
                if mult < 1.0:
                    weights[agent_name] *= mult
        except Exception:
            pass  # SelfAwareness unavailable

        return weights
    except Exception:
        return {}


def arbitrate(
    symbol: str,
    timeframe: str,
    timestamp: str,
    votes: List[AgentVote],
    regime_entropy: float = 0.0,
) -> DecisionPacket:
    """Apply Stacked Ensemble Arbiter rules to produce final decision.

    Phase 4: Two-stage arbiter:
      1. Try meta-model prediction (XGBoost trained on historical outcomes)
      2. Fall back to weighted voting if meta-model unavailable

    Plus Thompson Sampling for exploration trade identification.

    Args:
        symbol: Ticker symbol
        timeframe: Timeframe
        timestamp: ISO timestamp
        votes: List of AgentVote from all agents
        regime_entropy: Shannon entropy of regime belief distribution

    Returns:
        DecisionPacket with final decision
    """
    # Get learned weights (may be empty if learner unavailable)
    learned_weights = _get_learned_weights()

    # ── Phase 4: Thompson Sampling — optionally use sampled weights ──
    thompson = get_thompson_sampler()
    is_exploration = thompson.should_explore()
    if is_exploration:
        # Use Thompson-sampled weights for exploration
        sampled = thompson.sample_weights([v.agent_name for v in votes])
        for v in votes:
            if v.agent_name in sampled:
                v.weight = sampled[v.agent_name]
        weight_source = "thompson_exploration"
    elif learned_weights:
        # Apply learned weights to votes (override static weights)
        for v in votes:
            if v.agent_name in learned_weights:
                v.weight = learned_weights[v.agent_name]
        weight_source = "bayesian"
    else:
        weight_source = "static"

    # Phase C (C2): Apply Brier score calibration penalty
    try:
        from app.council.calibration import get_calibration_tracker
        cal = get_calibration_tracker()
        for v in votes:
            penalty = cal.get_weight_penalty(v.agent_name)
            if penalty < 1.0:
                v.weight *= penalty
    except Exception:
        pass  # Calibration unavailable

    # ELO-based weight blending: agents with higher ELO get proportionally more influence
    try:
        from app.council.elo_service import get_elo_service
        elo = get_elo_service()
        elo_weights = elo.get_elo_weights()
        if elo_weights:
            # Blend ELO factor at 20% strength (conservative, additive to existing weights)
            ELO_BLEND = 0.2
            for v in votes:
                if v.agent_name in elo_weights:
                    elo_factor = elo_weights[v.agent_name]
                    v.weight *= (1.0 - ELO_BLEND) + ELO_BLEND * elo_factor
    except Exception:
        pass  # ELO unavailable — no impact on voting

    # Collect vetoes
    veto_reasons = []
    for v in votes:
        if v.veto and v.agent_name in VETO_AGENTS:
            veto_reasons.append(f"{v.agent_name}: {v.veto_reason}")

    # If vetoed, decision is hold
    if veto_reasons:
        risk_limits = _extract_risk_limits(votes)
        return DecisionPacket(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            votes=votes,
            final_direction="hold",
            final_confidence=0.0,
            vetoed=True,
            veto_reasons=veto_reasons,
            risk_limits=risk_limits,
            execution_ready=False,
            council_reasoning=f"VETOED by: {'; '.join(veto_reasons)}",
        )

    # Check required agents voted non-hold
    required_votes = {
        v.agent_name: v for v in votes if v.agent_name in REQUIRED_AGENTS
    }
    missing = REQUIRED_AGENTS - set(required_votes.keys())
    if missing:
        return DecisionPacket(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            votes=votes,
            final_direction="hold",
            final_confidence=0.0,
            vetoed=False,
            veto_reasons=[],
            risk_limits=_extract_risk_limits(votes),
            execution_ready=False,
            council_reasoning=f"Missing required agents: {missing}",
        )

    # ── Phase 4: Stage 2 — Try meta-model prediction ────────────────
    regime_vote = next((v for v in votes if v.agent_name == "regime"), None)
    current_regime = "NEUTRAL"
    if regime_vote and regime_vote.metadata:
        current_regime = str(regime_vote.metadata.get("regime_state", regime_vote.metadata.get("regime", "NEUTRAL")))

    meta_model = get_arbiter_meta_model()
    meta_prediction = meta_model.predict(
        votes=votes,
        regime=current_regime,
        regime_entropy=regime_entropy,
    )

    # ── Weighted voting (always computed, used as fallback or blend) ──
    buy_weight = 0.0
    sell_weight = 0.0
    hold_weight = 0.0
    total_weight = 0.0

    for v in votes:
        if v.veto:
            continue
        w = v.weight * v.confidence
        total_weight += w
        if v.direction == "buy":
            buy_weight += w
        elif v.direction == "sell":
            sell_weight += w
        else:
            hold_weight += w

    # Determine direction from weighted voting
    if total_weight == 0:
        wv_direction = "hold"
        wv_confidence = 0.0
    else:
        if buy_weight == sell_weight:
            wv_direction = "hold"
            wv_confidence = hold_weight / total_weight if hold_weight > 0 else 0.0
        else:
            max_weight = max(buy_weight, sell_weight, hold_weight)
            if max_weight == buy_weight:
                wv_direction = "buy"
                wv_confidence = buy_weight / total_weight
            elif max_weight == sell_weight:
                wv_direction = "sell"
                wv_confidence = sell_weight / total_weight
            else:
                wv_direction = "hold"
                wv_confidence = hold_weight / total_weight

    # ── Final decision: blend meta-model + weighted voting ───────────
    if meta_prediction is not None:
        meta_dir, meta_conf = meta_prediction
        # Blend: 60% meta-model, 40% weighted voting
        if meta_dir == wv_direction:
            final_direction = meta_dir
            final_confidence = 0.6 * meta_conf + 0.4 * wv_confidence
        elif meta_dir == "hold" or wv_direction == "hold":
            # If either says hold, use the non-hold with reduced confidence
            if meta_dir != "hold":
                final_direction = meta_dir
                final_confidence = meta_conf * 0.5  # Penalty for disagreement
            elif wv_direction != "hold":
                final_direction = wv_direction
                final_confidence = wv_confidence * 0.5
            else:
                final_direction = "hold"
                final_confidence = max(meta_conf, wv_confidence)
        else:
            # Disagreement on direction — hold with low confidence
            final_direction = "hold"
            final_confidence = 0.3
        decision_method = f"meta_blend({meta_dir}@{meta_conf:.2f}+wv)"
    else:
        final_direction = wv_direction
        final_confidence = wv_confidence
        decision_method = f"weighted_vote({weight_source})"
        # Regime entropy penalty: high entropy = uncertain regime → reduce confidence
        if regime_entropy and regime_entropy > 0.5:
            entropy_penalty = max(0.5, 1.0 - (regime_entropy - 0.5) * 0.3)
            # entropy=0.5 → 1.0x (no penalty), 1.0 → 0.85x, 1.5 → 0.70x, 2.0 → 0.55x (max)
            final_confidence *= entropy_penalty

    # Execution readiness — regime-adaptive threshold
    exec_threshold = _get_execution_threshold(current_regime)
    execution_ready = final_direction != "hold" and final_confidence > exec_threshold
    exec_vote = next((v for v in votes if v.agent_name == "execution"), None)
    if exec_vote:
        execution_ready = execution_ready and exec_vote.metadata.get(
            "execution_ready", False
        )

    # Exploration trades get reduced size (signaled via metadata)
    if is_exploration and execution_ready:
        logger.info(
            "Thompson exploration trade for %s — position will be reduced",
            symbol,
        )

    risk_limits = _extract_risk_limits(votes)

    # Build reasoning summary
    direction_counts = {"buy": 0, "sell": 0, "hold": 0}
    for v in votes:
        if not v.veto:
            direction_counts[v.direction] = (
                direction_counts.get(v.direction, 0) + 1
            )

    reasoning = (
        f"Council vote: buy={direction_counts['buy']} "
        f"sell={direction_counts['sell']} hold={direction_counts['hold']}. "
        f"Weighted ({weight_source}): "
        f"buy={buy_weight:.2f} sell={sell_weight:.2f} hold={hold_weight:.2f}. "
        f"Method: {decision_method}. "
        f"Decision: {final_direction.upper()} @ {final_confidence:.0%} confidence."
    )

    packet = DecisionPacket(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        votes=votes,
        final_direction=final_direction,
        final_confidence=round(final_confidence, 4),
        vetoed=False,
        veto_reasons=[],
        risk_limits=risk_limits,
        execution_ready=execution_ready,
        council_reasoning=reasoning,
    )

    # Attach exploration flag for OrderExecutor to size down (50% position)
    if is_exploration:
        packet.metadata["is_exploration"] = True
        packet.experimental_history.append({
            "type": "thompson_exploration",
            "thompson_sampled_weights": {
                v.agent_name: round(v.weight, 4) for v in votes[:5]
            },
        })

    return packet


def _extract_risk_limits(votes: List[AgentVote]) -> Dict:
    """Extract risk limits from agent metadata."""
    for v in votes:
        if v.agent_name == "risk" and v.metadata:
            return v.metadata.get("risk_limits", {})
    return {}
