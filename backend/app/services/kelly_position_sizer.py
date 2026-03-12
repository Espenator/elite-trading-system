"""Kelly Criterion Position Sizing for Signal Engine.

Phase 4: Bayesian Kelly Enhancement.
- Beta distributions for win rate uncertainty quantification
- Regime-conditional Kelly fractions (BULLISH=0.6f*, etc.)
- Portfolio heat cap at 0.6 (60% total allocation)
- DuckDB audit trail for Kelly parameter distributions

Replaces fixed allocation (e.g. 3% trailing stops) with mathematically
optimal position sizing based on historical win rates and R-multiples.
Uses Half-Kelly by default to reduce drawdown risk.

Usage in signal_engine.py:
    from app.services.kelly_position_sizer import KellyPositionSizer
    sizer = KellyPositionSizer(max_allocation=0.10)
    size = sizer.calculate(win_rate=0.62, avg_win=0.035, avg_loss=0.015)

Connects to:
    - signal_engine.py (called after composite scoring)
    - alpaca_service.py (receives kelly_size_pct for order execution)
    - trade_outcomes table (historical stats for win_rate / R-multiples)
    - frontend-v2/src/pages/RiskIntelligence.jsx (displays position sizes)
"""
from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Phase 4: Bayesian Beta Distribution for Win Rate ─────────────────────────

@dataclass
class BetaDistribution:
    """Beta distribution for Bayesian win rate estimation.

    Alpha = prior wins + observed wins
    Beta  = prior losses + observed losses

    The posterior mean gives a shrinkage estimator that naturally handles
    small sample sizes (pulls toward prior) and converges to MLE for
    large samples.
    """
    alpha: float = 2.0   # Prior: 2 wins (weakly informative)
    beta: float = 2.0    # Prior: 2 losses (weakly informative)

    @property
    def mean(self) -> float:
        """Posterior mean: E[p] = α / (α + β)."""
        total = self.alpha + self.beta
        return self.alpha / total if total > 0 else 0.5

    @property
    def variance(self) -> float:
        """Posterior variance: Var[p] = αβ / ((α+β)²(α+β+1))."""
        ab = self.alpha + self.beta
        if ab <= 0:
            return 0.25
        return (self.alpha * self.beta) / (ab * ab * (ab + 1))

    @property
    def std(self) -> float:
        """Posterior standard deviation."""
        return math.sqrt(self.variance)

    @property
    def n_observations(self) -> float:
        """Effective number of observations (excluding prior)."""
        return max(0, self.alpha + self.beta - 4.0)  # Prior contributes 4

    def update(self, wins: int, losses: int) -> None:
        """Update posterior with new observations."""
        self.alpha += wins
        self.beta += losses

    def credible_interval(self, level: float = 0.95) -> tuple:
        """Approximate credible interval using Normal approximation.

        For large samples, Beta ≈ Normal(mean, variance).
        Returns (lower, upper) bounds at given level.
        """
        from math import sqrt
        z = 1.96 if level >= 0.95 else 1.645  # 95% or 90%
        m = self.mean
        s = self.std
        return (max(0, m - z * s), min(1, m + z * s))

    def conservative_estimate(self, percentile: float = 0.05) -> float:
        """Conservative win rate estimate (lower bound of credible interval).

        Uses the lower percentile to be risk-averse when data is limited.
        """
        z = 1.645  # ~5th percentile of Normal
        return max(0, self.mean - z * self.std)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha": round(self.alpha, 4),
            "beta": round(self.beta, 4),
            "mean": round(self.mean, 4),
            "std": round(self.std, 4),
            "n_observations": round(self.n_observations, 1),
            "conservative_estimate": round(self.conservative_estimate(), 4),
        }

    @classmethod
    def from_stats(
        cls,
        win_rate: float,
        trade_count: int,
        prior_alpha: float = 2.0,
        prior_beta: float = 2.0,
    ) -> BetaDistribution:
        """Create from observed win rate and trade count.

        Combines prior (weakly informative) with observed data.
        """
        wins = int(win_rate * trade_count)
        losses = trade_count - wins
        return cls(alpha=prior_alpha + wins, beta=prior_beta + losses)


# ── Phase 4: Regime-Conditional Kelly Fractions ──────────────────────────────
# These replace the old multiplicative regime multipliers with fractions
# of f* (full Kelly). This gives tighter risk control per regime.

_REGIME_KELLY_FRACTIONS: Dict[str, float] = {
    "BULLISH": 0.60,     # 60% of f* — confident, full swing
    "RISK_ON": 0.55,
    "NEUTRAL": 0.50,     # 50% of f* — standard Half-Kelly
    "RISK_OFF": 0.35,
    "BEARISH": 0.30,     # 30% of f* — conservative in downtrends
    "CRISIS": 0.15,      # 15% of f* — minimal exposure
    "UNKNOWN": 0.25,     # 25% of f* — uncertain = cautious
    # HMM regime mappings
    "GREEN": 0.55,
    "YELLOW": 0.35,
    "RED": 0.20,
}

# Short-side fractions (inverted: bearish allows larger shorts)
_SHORT_REGIME_KELLY_FRACTIONS: Dict[str, float] = {
    "BULLISH": 0.25,
    "RISK_ON": 0.30,
    "NEUTRAL": 0.50,
    "RISK_OFF": 0.55,
    "BEARISH": 0.60,
    "CRISIS": 0.50,
    "UNKNOWN": 0.25,
    "GREEN": 0.30,
    "YELLOW": 0.50,
    "RED": 0.55,
}

# Legacy multipliers kept for backward compatibility in size_signal()
_REGIME_MULTIPLIERS: Dict[str, float] = {
    "BULLISH": 1.10, "RISK_ON": 1.05, "NEUTRAL": 1.00,
    "RISK_OFF": 0.70, "BEARISH": 0.50, "CRISIS": 0.25, "UNKNOWN": 0.80,
    "GREEN": 1.05, "YELLOW": 0.65, "RED": 0.35,
}
_SHORT_REGIME_MULTIPLIERS: Dict[str, float] = {
    "BULLISH": 0.50, "RISK_ON": 0.70, "NEUTRAL": 1.00,
    "RISK_OFF": 1.05, "BEARISH": 1.10, "CRISIS": 1.15, "UNKNOWN": 0.80,
    "GREEN": 0.70, "YELLOW": 1.00, "RED": 1.10,
}

# Phase 4: Total portfolio Kelly allocation cap (never exceed 60% of capital)
PORTFOLIO_KELLY_CAP = 0.60


@dataclass
class PositionSize:
    """Result of a Kelly calculation."""
    raw_kelly: float          # Unmodified Kelly fraction (f*)
    half_kelly: float         # Half-Kelly (safety adjustment)
    regime_adjusted: float    # After regime-conditional fraction
    final_pct: float          # After max cap + portfolio heat
    edge: float               # Mathematical edge (expected value per $1)
    regime: str               # Current market regime
    action: str               # BUY / SELL / HOLD based on edge
    # Phase 4: Bayesian fields
    bayesian_win_rate: float = 0.0      # Beta posterior mean
    bayesian_uncertainty: float = 0.0   # Beta posterior std
    kelly_fraction_used: float = 0.5    # Regime-conditional fraction of f*
    portfolio_heat_scale: float = 1.0   # Scale factor from portfolio heat cap


class KellyPositionSizer:
    """Optimal position sizing using the Kelly Criterion.

    Kelly % = W - [(1 - W) / R]
    Where:
        W = historical win rate (0.0 to 1.0)
        R = avg_win / avg_loss (risk-reward ratio)

    Parameters
    ----------
    max_allocation : float
        Maximum % of account equity per trade (default 10%).
    use_half_kelly : bool
        Apply Half-Kelly (standard institutional practice) to reduce
        variance and drawdown risk.
    min_edge : float
        Minimum mathematical edge required to take a position.
        Below this, the sizer returns 0.0 (HOLD).
    min_trades : int
        Minimum historical trade count to trust the statistics.
        If fewer trades, returns conservative default.
    volatility_baseline : float
        Baseline daily volatility for volatility-adjusted sizing.
        Position sizes are scaled inversely when current vol exceeds this.
    """

    def __init__(
        self,
        max_allocation: float = 0.10,
        use_half_kelly: bool = True,
        min_edge: float = 0.02,
        min_trades: int = 20,
        volatility_baseline: float = 0.02,
    ):
        self.max_allocation = max_allocation
        self.use_half_kelly = use_half_kelly
        self.min_edge = min_edge
        self.min_trades = min_trades
        self.volatility_baseline = volatility_baseline

    # ------------------------------------------------------------------
    def calculate(
        self,
        win_rate: float,
        avg_win_pct: float,
        avg_loss_pct: float,
        regime: str = "NEUTRAL",
        side: str = "buy",
        trade_count: int = 100,
        current_positions: Optional[Dict[str, float]] = None,
    ) -> PositionSize:
        """Compute optimal position size using Bayesian Kelly criterion.

        Phase 4 Enhancement:
        - Uses Beta distribution posterior for win rate uncertainty
        - Applies regime-conditional Kelly fractions (not multiplicative)
        - Enforces portfolio heat cap (0.6 total allocation)
        - Stores parameter distributions for audit trail

        Parameters
        ----------
        win_rate      : fraction of winning trades (0.0 to 1.0)
        avg_win_pct   : average winning trade as decimal (e.g. 0.035 = 3.5%)
        avg_loss_pct  : average losing trade as decimal (e.g. 0.015 = 1.5%)
        regime        : current OpenClaw market regime
        side          : "buy" or "sell"/"short"
        trade_count   : number of historical trades in the sample
        current_positions : dict of {symbol: allocation_pct} for portfolio heat check

        Returns
        -------
        PositionSize with all intermediate and final values
        """
        # Guard: insufficient data
        if trade_count < self.min_trades:
            logger.warning(
                "Only %d trades (need %d). Using conservative 1%% allocation.",
                trade_count, self.min_trades,
            )
            return PositionSize(
                raw_kelly=0.0, half_kelly=0.0,
                regime_adjusted=0.0, final_pct=0.01,
                edge=0.0, regime=regime, action="HOLD",
            )

        # Guard: zero denominators
        if avg_loss_pct == 0 or win_rate <= 0:
            return PositionSize(
                raw_kelly=0.0, half_kelly=0.0,
                regime_adjusted=0.0, final_pct=0.0,
                edge=0.0, regime=regime, action="HOLD",
            )

        # ── Phase 4: Bayesian win rate via Beta distribution ─────────
        beta_dist = BetaDistribution.from_stats(
            win_rate=win_rate,
            trade_count=trade_count,
        )
        # Use conservative estimate (lower credible bound) when data is limited
        if trade_count < 50:
            bayesian_win_rate = beta_dist.conservative_estimate()
        else:
            bayesian_win_rate = beta_dist.mean

        # R-ratio (risk-reward)
        r_ratio = abs(avg_win_pct / avg_loss_pct)

        # Kelly formula using Bayesian win rate: W - (1 - W) / R
        raw_kelly = bayesian_win_rate - ((1.0 - bayesian_win_rate) / r_ratio)

        # Mathematical edge per $1 risked — use OBSERVED win rate for edge detection
        # (Bayesian shrinkage is for conservative sizing, not edge existence check)
        edge = (win_rate * avg_win_pct) - ((1.0 - win_rate) * avg_loss_pct)

        # Negative edge = no trade
        if raw_kelly <= 0 or edge < self.min_edge:
            return PositionSize(
                raw_kelly=round(raw_kelly, 4),
                half_kelly=0.0,
                regime_adjusted=0.0,
                final_pct=0.0,
                edge=round(edge, 4),
                regime=regime,
                action="HOLD",
                bayesian_win_rate=round(bayesian_win_rate, 4),
                bayesian_uncertainty=round(beta_dist.std, 4),
            )

        # ── Phase 4: Regime-conditional Kelly fraction (replaces Half-Kelly × multiplier) ──
        frac_table = (
            _SHORT_REGIME_KELLY_FRACTIONS
            if side.lower() in ("sell", "short")
            else _REGIME_KELLY_FRACTIONS
        )
        kelly_fraction = frac_table.get(regime.upper(), 0.25)

        # Apply regime fraction to full Kelly
        half_kelly = raw_kelly * 0.5  # Record standard half-kelly for reference
        regime_adjusted = raw_kelly * kelly_fraction

        # Cap at max allocation
        capped_pct = min(regime_adjusted, self.max_allocation)

        # ── Phase 4: Portfolio heat cap — proportional shrinkage ──────
        heat_scale = 1.0
        if current_positions:
            current_heat = sum(current_positions.values())
            remaining_capacity = max(0.0, PORTFOLIO_KELLY_CAP - current_heat)
            if remaining_capacity <= 0:
                capped_pct = 0.0
                heat_scale = 0.0
            elif capped_pct > remaining_capacity:
                heat_scale = remaining_capacity / capped_pct
                capped_pct = remaining_capacity

        final_pct = capped_pct
        action = ("SELL" if side.lower() in ("sell", "short") else "BUY") if final_pct > 0 else "HOLD"

        result = PositionSize(
            raw_kelly=round(raw_kelly, 4),
            half_kelly=round(half_kelly, 4),
            regime_adjusted=round(regime_adjusted, 4),
            final_pct=round(final_pct, 4),
            edge=round(edge, 4),
            regime=regime,
            action=action,
            bayesian_win_rate=round(bayesian_win_rate, 4),
            bayesian_uncertainty=round(beta_dist.std, 4),
            kelly_fraction_used=kelly_fraction,
            portfolio_heat_scale=round(heat_scale, 4),
        )

        logger.info(
            "Bayesian Kelly: edge=%.4f raw_f*=%.4f regime=%s(frac=%.2f) "
            "bayesian_wr=%.4f±%.4f heat_scale=%.2f final=%.4f -> %s",
            edge, raw_kelly, regime, kelly_fraction,
            bayesian_win_rate, beta_dist.std, heat_scale, final_pct, action,
        )

        # ── Phase 4: Audit trail to DuckDB ───────────────────────────
        self._audit_kelly_params(
            regime=regime,
            beta_dist=beta_dist,
            raw_kelly=raw_kelly,
            kelly_fraction=kelly_fraction,
            final_pct=final_pct,
            trade_count=trade_count,
            heat_scale=heat_scale,
        )

        return result

    def _audit_kelly_params(
        self,
        regime: str,
        beta_dist: BetaDistribution,
        raw_kelly: float,
        kelly_fraction: float,
        final_pct: float,
        trade_count: int,
        heat_scale: float,
    ) -> None:
        """Store Kelly parameter distributions in DuckDB for audit trail."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store.get_thread_cursor()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kelly_audit (
                    id INTEGER PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    regime VARCHAR,
                    beta_alpha DOUBLE,
                    beta_beta DOUBLE,
                    bayesian_win_rate DOUBLE,
                    bayesian_uncertainty DOUBLE,
                    raw_kelly DOUBLE,
                    kelly_fraction DOUBLE,
                    final_pct DOUBLE,
                    trade_count INTEGER,
                    heat_scale DOUBLE,
                    beta_params_json VARCHAR
                )
            """)
            conn.execute(
                """INSERT INTO kelly_audit
                   (id, regime, beta_alpha, beta_beta, bayesian_win_rate,
                    bayesian_uncertainty, raw_kelly, kelly_fraction,
                    final_pct, trade_count, heat_scale, beta_params_json)
                   VALUES ((SELECT COALESCE(MAX(id),0)+1 FROM kelly_audit),
                           ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    regime,
                    round(beta_dist.alpha, 4),
                    round(beta_dist.beta, 4),
                    round(beta_dist.mean, 4),
                    round(beta_dist.std, 4),
                    round(raw_kelly, 4),
                    kelly_fraction,
                    round(final_pct, 4),
                    trade_count,
                    round(heat_scale, 4),
                    json.dumps(beta_dist.to_dict()),
                ],
            )
        except Exception as e:
            logger.debug("Kelly audit trail failed: %s", e)

    # ------------------------------------------------------------------
    def size_signal(
        self,
        ticker: str,
        composite_score: float,
        regime: str,
        historical_stats: Dict[str, float],
        min_score: float = 70.0,
    ) -> Dict:
        """High-level wrapper for the signal engine pipeline.

        Called after composite scoring in signal_engine.py.
        Fetches historical stats and returns a sized signal dict
        ready for alpaca_service.py execution.

        Parameters
        ----------
        ticker           : stock symbol
        composite_score  : 0-100 signal score from signal_engine.py
        regime           : OpenClaw market regime string
        historical_stats : dict with keys:
            win_rate, avg_win_pct, avg_loss_pct, trade_count
        min_score        : minimum composite score to consider
        """
        if composite_score < min_score:
            return {
                "ticker": ticker,
                "composite_score": composite_score,
                "regime": regime,
                "kelly_allocation_pct": 0.0,
                "action": "HOLD",
                "reason": f"Score {composite_score} below threshold {min_score}",
            }

        pos = self.calculate(
            win_rate=historical_stats.get("win_rate", 0.50),
            avg_win_pct=historical_stats.get("avg_win_pct", 0.02),
            avg_loss_pct=historical_stats.get("avg_loss_pct", 0.01),
            regime=regime,
            trade_count=historical_stats.get("trade_count", 0),
        )

        return {
            "ticker": ticker,
            "composite_score": composite_score,
            "regime": regime,
            "kelly_allocation_pct": pos.final_pct,
            "raw_kelly": pos.raw_kelly,
            "half_kelly": pos.half_kelly,
            "edge": pos.edge,
            "action": pos.action,
        }

    def calculate_volatility_adjusted(
        self,
        win_rate: float,
        avg_win_pct: float,
        avg_loss_pct: float,
        current_volatility: float,
        baseline_volatility: float = 0.02,
        regime: str = "NEUTRAL",
        trade_count: int = 0,
    ) -> PositionSize:
        """Volatility-adjusted Kelly: scales position inversely with volatility.

        When volatility is 2x baseline, position is halved.
        This prevents over-sizing in turbulent markets.
        """
        base = self.calculate(
            win_rate=win_rate,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            regime=regime,
            trade_count=trade_count,
        )
        vol_ratio = max(baseline_volatility, current_volatility) / baseline_volatility
        vol_scale = 1.0 / vol_ratio  # Inverse scaling
        adjusted = PositionSize(
            raw_kelly=base.raw_kelly,
            half_kelly=base.half_kelly,
            regime_adjusted=base.regime_adjusted * vol_scale,
            final_pct=min(base.final_pct * vol_scale, self.max_allocation),
            edge=base.edge,
            regime=base.regime,
            action=base.action,
        )
        logger.info(
            "Vol-adjusted Kelly: vol_ratio=%.2f, scale=%.2f, final=%.4f",
            vol_ratio, vol_scale, adjusted.final_pct,
        )
        return adjusted

    @staticmethod
    def portfolio_correlation_cap(
        positions: list[Dict],
        max_sector_pct: float = 0.25,
        max_correlated_pct: float = 0.40,
    ) -> list[Dict]:
        """Cap total allocation to correlated positions.

        Ensures no single sector exceeds max_sector_pct of portfolio
        and total correlated exposure stays under max_correlated_pct.
        """
        sector_totals: Dict[str, float] = {}
        for pos in positions:
            sector = pos.get("sector", "UNKNOWN")
            sector_totals[sector] = sector_totals.get(sector, 0) + pos.get("kelly_allocation_pct", 0)

        adjusted = []
        for pos in positions:
            sector = pos.get("sector", "UNKNOWN")
            alloc = pos.get("kelly_allocation_pct", 0)
            total = sector_totals.get(sector, 0)
            if total > max_sector_pct and alloc > 0:
                scale = max_sector_pct / total
                pos = {**pos, "kelly_allocation_pct": alloc * scale}
                pos["sector_capped"] = True
            adjusted.append(pos)
        return adjusted

    @staticmethod
    def calculate_trailing_stop(
        entry_price: float,
        atr: float,
        side: str = "buy",
        atr_multiplier: float = 2.0,
        trailing_pct: float = 0.03,
    ) -> Dict:
        """Calculate ATR-based trailing stop + fixed % trailing.

        Uses the tighter of ATR-based or percentage-based stop.
        This maximizes profit capture while limiting downside.
        """
        if side.lower() == "buy":
            atr_stop = entry_price - (atr * atr_multiplier)
            pct_stop = entry_price * (1 - trailing_pct)
            stop = max(atr_stop, pct_stop)  # Tighter stop
            take_profit = entry_price + (atr * atr_multiplier * 1.5)
        else:
            atr_stop = entry_price + (atr * atr_multiplier)
            pct_stop = entry_price * (1 + trailing_pct)
            stop = min(atr_stop, pct_stop)
            take_profit = entry_price - (atr * atr_multiplier * 1.5)

        risk_per_share = abs(entry_price - stop)
        reward_per_share = abs(take_profit - entry_price)
        rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0

        return {
            "stop_loss": round(stop, 2),
            "take_profit": round(take_profit, 2),
            "risk_per_share": round(risk_per_share, 2),
            "reward_per_share": round(reward_per_share, 2),
            "risk_reward_ratio": round(rr_ratio, 2),
            "method": (
                "atr"
                if (side == "buy" and atr_stop > pct_stop)
                or (side != "buy" and atr_stop < pct_stop)
                else "trailing_pct"
            ),
        }

    def regime_aware_size(
        self,
        win_rate: float,
        avg_win_pct: float = 0.035,
        avg_loss_pct: float = 0.015,
        regime: str = "NEUTRAL",
        risk_score: int = 100,
        volatility: float = 0.02,
    ) -> Dict:
        """Full regime + risk + volatility aware position sizing.

        Combines Kelly, regime scaling, risk score dampening,
        and volatility adjustment into one call.
        """
        # 1. Base Kelly
        base = self.calculate(
            win_rate=win_rate,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            regime=regime,
        )

        # 2. Volatility adjustment (uses self.volatility_baseline from __init__)
        vol_scale = 1.0 / max(volatility / self.volatility_baseline, 1.0)

        # 3. Risk score dampener
        if risk_score < 40:
            risk_dampener = 0.5
        elif risk_score < 60:
            risk_dampener = 0.75
        else:
            risk_dampener = 1.0

        # 4. Final combined size
        final_pct = min(
            base.final_pct * vol_scale * risk_dampener,
            self.max_allocation,
        )

        return {
            "raw_kelly": base.raw_kelly,
            "half_kelly": base.half_kelly,
            "regime": regime,
            "regime_adjusted": base.regime_adjusted,
            "vol_scale": round(vol_scale, 4),
            "risk_dampener": risk_dampener,
            "final_pct": round(final_pct, 4),
            "edge": base.edge,
            "action": base.action if final_pct > 0 else "NO_TRADE",
            "risk_score": risk_score,
        }

    def correlation_adjusted_size(
        self,
        symbol: str,
        base_size_pct: float,
        portfolio_positions: Dict[str, float],
        correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> Dict:
        """Reduce position size when correlated assets already in portfolio.
        High correlation = reduce size to avoid concentration risk."""
        if not portfolio_positions or correlation_matrix is None:
            return {"adjusted_pct": base_size_pct, "correlation_penalty": 0.0, "max_correlated": 0.0}

        max_corr = 0.0
        total_corr_exposure = 0.0
        for held_sym, held_pct in portfolio_positions.items():
            if held_sym == symbol:
                continue
            corr = abs(correlation_matrix.get(symbol, {}).get(held_sym, 0.0))
            max_corr = max(max_corr, corr)
            total_corr_exposure += corr * held_pct

        # Penalty: high correlation with large existing positions = reduce size
        if max_corr > 0.9:
            corr_penalty = 0.5
        elif max_corr > 0.7:
            corr_penalty = 0.3
        elif max_corr > 0.5:
            corr_penalty = 0.15
        else:
            corr_penalty = 0.0

        # Additional penalty for total correlated exposure
        exposure_penalty = min(0.3, total_corr_exposure * 0.5)
        total_penalty = min(0.7, corr_penalty + exposure_penalty)
        adjusted = base_size_pct * (1.0 - total_penalty)

        return {
            "adjusted_pct": round(max(0.005, adjusted), 4),
            "correlation_penalty": round(total_penalty, 4),
            "max_correlated": round(max_corr, 4),
            "total_corr_exposure": round(total_corr_exposure, 4),
        }

    def sector_exposure_check(
        self,
        symbol: str,
        sector: str,
        position_pct: float,
        sector_allocations: Dict[str, float],
        max_sector_pct: float = 0.25,
    ) -> Dict:
        """Check and limit sector concentration. Returns adjusted size."""
        current_sector_pct = sector_allocations.get(sector, 0.0)
        remaining = max(0.0, max_sector_pct - current_sector_pct)
        if position_pct <= remaining:
            return {
                "allowed": True,
                "adjusted_pct": position_pct,
                "sector": sector,
                "sector_current": round(current_sector_pct, 4),
                "sector_remaining": round(remaining, 4),
            }
        return {
            "allowed": remaining > 0.005,
            "adjusted_pct": round(max(0.0, remaining), 4),
            "sector": sector,
            "sector_current": round(current_sector_pct, 4),
            "sector_remaining": round(remaining, 4),
            "reason": f"Sector {sector} at {current_sector_pct:.1%}, cap={max_sector_pct:.1%}",
        }

    def portfolio_heat_check(
        self,
        position_pct: float,
        current_positions: Dict[str, float],
        max_heat: float = 0.60,
    ) -> Dict:
        """Check total portfolio heat (sum of all Kelly allocations).

        Phase 4: Default cap raised to 0.60 (60% of capital) as the
        Bayesian Kelly fractions already enforce per-regime risk limits.
        When approaching the cap, positions get proportionally smaller.
        """
        current_heat = sum(current_positions.values())
        remaining = max(0.0, max_heat - current_heat)

        # Proportional shrinkage: as heat approaches cap, scale new positions down
        if remaining <= 0:
            allowed_pct = 0.0
            shrinkage_factor = 0.0
        elif current_heat > max_heat * 0.8:
            # Within 80-100% of cap: proportional reduction
            shrinkage_factor = remaining / (max_heat * 0.2)
            allowed_pct = min(position_pct * shrinkage_factor, remaining)
        else:
            shrinkage_factor = 1.0
            allowed_pct = min(position_pct, remaining)

        return {
            "allowed": allowed_pct > 0.005,
            "adjusted_pct": round(allowed_pct, 4),
            "current_heat": round(current_heat, 4),
            "max_heat": max_heat,
            "remaining_capacity": round(remaining, 4),
            "shrinkage_factor": round(shrinkage_factor, 4),
        }
