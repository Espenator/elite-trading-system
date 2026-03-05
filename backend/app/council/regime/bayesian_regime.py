"""Bayesian Regime — maintains probability distributions over market states.

Replaces point-estimate regime classification with a full Dirichlet-based
belief system. Agents should use regime probabilities, not single labels.

Research basis: Bayesian game-theoretic frameworks where agents maintain
probabilistic beliefs about regime achieve robust performance even during
extreme events like COVID.

States:
    trending_bull    — sustained uptrend, momentum-driven
    trending_bear    — sustained downtrend, fear-driven
    mean_revert      — range-bound, oscillating
    high_vol_crisis  — VIX > 30, correlated selloff
    low_vol_grind    — VIX < 15, slow grind higher
    transition       — regime shift in progress
"""
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

STATES = [
    "trending_bull",
    "trending_bear",
    "mean_revert",
    "high_vol_crisis",
    "low_vol_grind",
    "transition",
]

# Default Dirichlet prior (uniform)
DEFAULT_ALPHA = {state: 2.0 for state in STATES}


class BayesianRegime:
    """Bayesian regime classifier using Dirichlet-based belief updates.

    Maintains a probability distribution over 6 market states.
    Updates beliefs using observation likelihoods computed from
    VIX, trend strength, market breadth, and volatility ratio.
    """

    SMOOTHING_FACTOR = 0.85  # exponential smoothing to prevent whiplash

    def __init__(self, alpha: Dict[str, float] = None):
        self._alpha = dict(alpha or DEFAULT_ALPHA)
        self._beliefs = self._normalize_alpha()

    def _normalize_alpha(self) -> Dict[str, float]:
        """Compute beliefs from Dirichlet alpha parameters."""
        total = sum(self._alpha.values())
        if total == 0:
            return {s: 1.0 / len(STATES) for s in STATES}
        return {s: a / total for s, a in self._alpha.items()}

    def update(self, observation_likelihoods: Dict[str, float]) -> Dict[str, float]:
        """Update beliefs given observation likelihoods.

        Args:
            observation_likelihoods: Dict mapping state → likelihood P(obs|state).
                Higher values indicate the observation is more consistent with that state.

        Returns:
            Updated belief distribution
        """
        # Posterior = prior * likelihood
        posterior = {}
        for state in STATES:
            likelihood = observation_likelihoods.get(state, 0.01)
            posterior[state] = self._beliefs[state] * likelihood

        # Normalize
        total = sum(posterior.values())
        if total > 0:
            posterior = {s: p / total for s, p in posterior.items()}
        else:
            posterior = {s: 1.0 / len(STATES) for s in STATES}

        # Exponential smoothing to prevent regime whiplash
        smoothed = {}
        for state in STATES:
            smoothed[state] = (
                self.SMOOTHING_FACTOR * posterior[state]
                + (1 - self.SMOOTHING_FACTOR) * self._beliefs[state]
            )

        # Re-normalize after smoothing
        total = sum(smoothed.values())
        self._beliefs = {s: p / total for s, p in smoothed.items()}

        return dict(self._beliefs)

    def entropy(self) -> float:
        """Compute Shannon entropy of the belief distribution.

        High entropy = high uncertainty about regime.
        Low entropy = confident about regime.
        Max entropy = ln(6) ≈ 1.79 (uniform distribution).
        """
        h = 0.0
        for p in self._beliefs.values():
            if p > 0:
                h -= p * math.log(p)
        return h

    def position_size_modifier(self) -> float:
        """Map entropy to Kelly position size multiplier.

        Low entropy (confident) → 1.0 (full Kelly)
        High entropy (uncertain) → 0.3 (reduce exposure)
        """
        max_entropy = math.log(len(STATES))  # ~1.79
        normalized = self.entropy() / max_entropy  # 0.0 to 1.0
        # Linear interpolation: 1.0 at entropy=0, 0.3 at entropy=max
        return round(1.0 - 0.7 * normalized, 3)

    def dominant_regime(self) -> Tuple[str, float]:
        """Return the most likely regime and its probability."""
        best_state = max(self._beliefs, key=self._beliefs.get)
        return best_state, round(self._beliefs[best_state], 4)

    def get_beliefs(self) -> Dict[str, float]:
        """Return current belief distribution."""
        return {s: round(p, 4) for s, p in self._beliefs.items()}

    def to_dict(self) -> Dict[str, Any]:
        dom, dom_p = self.dominant_regime()
        return {
            "beliefs": self.get_beliefs(),
            "dominant_regime": dom,
            "dominant_probability": dom_p,
            "entropy": round(self.entropy(), 4),
            "position_size_modifier": self.position_size_modifier(),
        }


def compute_likelihoods(
    vix: float = 20.0,
    trend_strength: float = 0.0,
    breadth_ratio: float = 0.5,
    volatility_ratio: float = 1.0,
) -> Dict[str, float]:
    """Compute observation likelihoods for each regime state.

    Uses normal PDF approximations for each indicator's expected
    behavior under each regime.

    Args:
        vix: Current VIX level
        trend_strength: ADX or directional indicator (-1 to +1, positive = bullish)
        breadth_ratio: Market breadth (0 to 1, >0.5 = positive)
        volatility_ratio: Current vol / historical vol (>1 = elevated)

    Returns:
        Dict mapping state → likelihood
    """
    def _gauss(x: float, mu: float, sigma: float) -> float:
        """Unnormalized Gaussian PDF."""
        return math.exp(-0.5 * ((x - mu) / sigma) ** 2)

    likelihoods = {}

    # trending_bull: low VIX, strong positive trend, positive breadth
    likelihoods["trending_bull"] = (
        _gauss(vix, 15, 5)
        * _gauss(trend_strength, 0.7, 0.3)
        * _gauss(breadth_ratio, 0.7, 0.15)
    )

    # trending_bear: moderate VIX, strong negative trend, negative breadth
    likelihoods["trending_bear"] = (
        _gauss(vix, 25, 8)
        * _gauss(trend_strength, -0.7, 0.3)
        * _gauss(breadth_ratio, 0.3, 0.15)
    )

    # mean_revert: low-moderate VIX, no clear trend
    likelihoods["mean_revert"] = (
        _gauss(vix, 18, 5)
        * _gauss(trend_strength, 0.0, 0.2)
        * _gauss(breadth_ratio, 0.5, 0.15)
    )

    # high_vol_crisis: very high VIX, negative trend, negative breadth
    likelihoods["high_vol_crisis"] = (
        _gauss(vix, 40, 10)
        * _gauss(trend_strength, -0.5, 0.4)
        * _gauss(breadth_ratio, 0.2, 0.15)
        * _gauss(volatility_ratio, 2.0, 0.5)
    )

    # low_vol_grind: very low VIX, slight positive trend
    likelihoods["low_vol_grind"] = (
        _gauss(vix, 12, 3)
        * _gauss(trend_strength, 0.3, 0.3)
        * _gauss(volatility_ratio, 0.7, 0.2)
    )

    # transition: moderate everything, high volatility ratio
    likelihoods["transition"] = (
        _gauss(vix, 22, 8)
        * _gauss(abs(trend_strength), 0.3, 0.3)
        * _gauss(volatility_ratio, 1.5, 0.3)
    )

    # Ensure no zero likelihoods
    return {s: max(l, 1e-6) for s, l in likelihoods.items()}


# Singleton
_instance: Optional[BayesianRegime] = None


def get_bayesian_regime() -> BayesianRegime:
    global _instance
    if _instance is None:
        _instance = BayesianRegime()
    return _instance
