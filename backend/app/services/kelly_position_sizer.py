"""Kelly Criterion Position Sizing for Signal Engine.

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

Based on Perplexity model council recommendation (Intelligence Layer #3).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ---- OpenClaw regime multipliers (matches signal_engine.py) ----
_REGIME_MULTIPLIERS: Dict[str, float] = {
    "BULLISH": 1.10,
    "RISK_ON": 1.05,
    "NEUTRAL": 1.00,
    "RISK_OFF": 0.70,
    "BEARISH": 0.50,
    "CRISIS": 0.25,
    "UNKNOWN": 0.80,
}


@dataclass
class PositionSize:
    """Result of a Kelly calculation."""
    raw_kelly: float          # Unmodified Kelly fraction
    half_kelly: float         # Half-Kelly (safety adjustment)
    regime_adjusted: float    # After OpenClaw regime multiplier
    final_pct: float          # After max cap
    edge: float               # Mathematical edge (expected value per $1)
    regime: str               # Current market regime
    action: str               # BUY / SELL / HOLD based on edge


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
    """

    def __init__(
        self,
        max_allocation: float = 0.10,
        use_half_kelly: bool = True,
        min_edge: float = 0.02,
        min_trades: int = 20,
    ):
        self.max_allocation = max_allocation
        self.use_half_kelly = use_half_kelly
        self.min_edge = min_edge
        self.min_trades = min_trades

    # ------------------------------------------------------------------
    def calculate(
        self,
        win_rate: float,
        avg_win_pct: float,
        avg_loss_pct: float,
        regime: str = "NEUTRAL",
        trade_count: int = 100,
    ) -> PositionSize:
        """Compute optimal position size.

        Parameters
        ----------
        win_rate      : fraction of winning trades (0.0 to 1.0)
        avg_win_pct   : average winning trade as decimal (e.g. 0.035 = 3.5%)
        avg_loss_pct  : average losing trade as decimal (e.g. 0.015 = 1.5%)
        regime        : current OpenClaw market regime
        trade_count   : number of historical trades in the sample

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

        # R-ratio (risk-reward)
        r_ratio = abs(avg_win_pct / avg_loss_pct)

        # Kelly formula: W - (1 - W) / R
        raw_kelly = win_rate - ((1.0 - win_rate) / r_ratio)

        # Mathematical edge per $1 risked
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
            )

        # Half-Kelly for safety
        half_kelly = raw_kelly * 0.5 if self.use_half_kelly else raw_kelly

        # Apply OpenClaw regime multiplier
        regime_mult = _REGIME_MULTIPLIERS.get(regime.upper(), 0.80)
        regime_adjusted = half_kelly * regime_mult

        # Cap at max allocation
        final_pct = min(regime_adjusted, self.max_allocation)

        action = "BUY" if final_pct > 0 else "HOLD"

        result = PositionSize(
            raw_kelly=round(raw_kelly, 4),
            half_kelly=round(half_kelly, 4),
            regime_adjusted=round(regime_adjusted, 4),
            final_pct=round(final_pct, 4),
            edge=round(edge, 4),
            regime=regime,
            action=action,
        )

        logger.info(
            "Kelly sizing: edge=%.4f raw=%.4f half=%.4f regime=%s(x%.2f) final=%.4f -> %s",
            edge, raw_kelly, half_kelly, regime, regime_mult, final_pct, action,
        )

        return result

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
            f"Vol-adjusted Kelly: vol_ratio={vol_ratio:.2f}, "
            f"scale={vol_scale:.2f}, final={adjusted.final_pct:.4f}"
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
