"""CorrelationRadar — real-time cross-asset correlation and rotation detection.

Tracks hundreds of pair correlations across sectors, asset classes, and
individual symbols. Detects when correlations break, shift, or intensify —
which signals regime changes, rotation, and trading opportunities.

Key Capabilities:
  - Rolling correlation matrix across all tracked symbols
  - Sector rotation detection (money flowing between sectors)
  - Correlation breakdown alerts (pair divergence = opportunity)
  - Mean-reversion signal generation (overextended pairs snap back)
  - Intraday rhythm detection (time-of-day patterns)
  - Next-day reversal probability scoring
  - Fear/greed cycle tracking per sector

Data Flow:
  DuckDB (daily_ohlcv + technical_indicators)
    -> CorrelationRadar computes rolling correlations
    -> Detects breaks/shifts
    -> Triggers swarm analysis for affected symbols
"""
import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Sector/Asset Class Definitions
# ═══════════════════════════════════════════════════════════════════════════════

SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLI": "Industrials",
    "XLP": "Consumer Staples",
    "XLY": "Consumer Discretionary",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLB": "Materials",
    "XLC": "Communications",
}

MACRO_INSTRUMENTS = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000",
    "DIA": "Dow Jones",
    "TLT": "20Y Treasuries",
    "GLD": "Gold",
    "USO": "Oil",
    "UUP": "US Dollar",
    "EEM": "Emerging Markets",
    "HYG": "High Yield Credit",
    "VIX": "Volatility",
}

# Known correlation pairs — when these break, something is changing
KEY_PAIRS = [
    ("SPY", "QQQ", "equity_breadth"),        # Should be highly correlated
    ("SPY", "IWM", "risk_appetite"),          # Small cap divergence = rotation
    ("SPY", "TLT", "stocks_vs_bonds"),       # Inverse = normal, positive = crisis
    ("SPY", "GLD", "risk_on_off"),            # Gold divergence = fear
    ("SPY", "HYG", "credit_risk"),            # Credit divergence = stress
    ("XLK", "XLE", "growth_vs_value"),        # Tech vs Energy = style rotation
    ("XLF", "TLT", "rate_sensitivity"),       # Banks vs Bonds = rate expectations
    ("USO", "XLE", "oil_vs_energy_stocks"),   # Should be correlated
    ("GLD", "TLT", "safe_haven"),             # Both safe havens
    ("QQQ", "IWM", "growth_vs_small"),        # Growth vs small cap rotation
    ("EEM", "UUP", "em_vs_dollar"),           # Inverse = normal
    ("XLY", "XLP", "consumer_cycle"),         # Discretionary vs Staples = cycle
]

# Mean reversion thresholds
REVERSION_LOOKBACK = 20       # Days to measure extension
REVERSION_ZSCORE_THRESHOLD = 2.0  # Z-score threshold for "overextended"
ROTATION_THRESHOLD = 0.03     # 3% relative move = significant rotation


@dataclass
class CorrelationBreak:
    """A detected correlation breakdown between two symbols."""
    pair: Tuple[str, str]
    pair_type: str
    normal_corr: float       # Historical normal correlation
    current_corr: float      # Current rolling correlation
    deviation: float          # How far from normal
    interpretation: str       # What this means
    trade_idea: str           # Suggested trade
    symbols_to_analyze: List[str]
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair": list(self.pair),
            "pair_type": self.pair_type,
            "normal_corr": round(self.normal_corr, 3),
            "current_corr": round(self.current_corr, 3),
            "deviation": round(self.deviation, 3),
            "interpretation": self.interpretation,
            "trade_idea": self.trade_idea,
            "symbols_to_analyze": self.symbols_to_analyze,
            "detected_at": self.detected_at,
        }


@dataclass
class RotationSignal:
    """A detected sector/style rotation."""
    from_sector: str
    to_sector: str
    strength: float          # 0-1 how strong is the rotation
    from_return: float       # Recent return of "from" sector
    to_return: float         # Recent return of "to" sector
    spread: float            # Return difference
    trade_ideas: List[Dict[str, str]]
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_sector": self.from_sector,
            "to_sector": self.to_sector,
            "strength": round(self.strength, 3),
            "from_return_pct": round(self.from_return * 100, 2),
            "to_return_pct": round(self.to_return * 100, 2),
            "spread_pct": round(self.spread * 100, 2),
            "trade_ideas": self.trade_ideas,
            "detected_at": self.detected_at,
        }


@dataclass
class MeanReversionSignal:
    """A symbol that's overextended and likely to snap back."""
    symbol: str
    direction: str           # "oversold" or "overbought"
    zscore: float            # How many std devs from mean
    return_5d: float         # Recent 5-day return
    rsi: float               # Current RSI
    bollinger_pct: float     # Position within Bollinger Bands (0=lower, 1=upper)
    reversal_probability: float
    trade_idea: str
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "zscore": round(self.zscore, 2),
            "return_5d_pct": round(self.return_5d * 100, 2),
            "rsi": round(self.rsi, 1),
            "bollinger_pct": round(self.bollinger_pct, 2),
            "reversal_probability": round(self.reversal_probability, 2),
            "trade_idea": self.trade_idea,
            "detected_at": self.detected_at,
        }


class CorrelationRadar:
    """Continuous cross-asset correlation scanner and rotation detector."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._scan_interval = 300  # 5 minutes
        self._correlation_cache: Dict[str, float] = {}
        self._rotation_history: deque = deque(maxlen=100)
        self._break_history: deque = deque(maxlen=100)
        self._reversion_history: deque = deque(maxlen=100)
        self._stats = {
            "scans": 0,
            "correlation_breaks": 0,
            "rotation_signals": 0,
            "reversion_signals": 0,
            "swarms_triggered": 0,
        }

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())
        logger.info("CorrelationRadar started (interval=%ds)", self._scan_interval)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("CorrelationRadar stopped")

    async def _scan_loop(self):
        await asyncio.sleep(60)  # Initial warmup
        while self._running:
            try:
                await self._full_scan()
                self._stats["scans"] += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("CorrelationRadar scan error: %s", e)
            await asyncio.sleep(self._scan_interval)

    async def _full_scan(self):
        """Run all correlation/rotation/reversion scans."""
        # Load data from DuckDB
        prices = await self._load_price_data()
        if prices is None or prices.empty:
            return

        indicators = await self._load_indicator_data()

        # 1. Correlation breaks
        breaks = self._detect_correlation_breaks(prices)
        for brk in breaks:
            self._break_history.append(brk)
            self._stats["correlation_breaks"] += 1
            await self._trigger_swarm_from_break(brk)

        # 2. Sector rotation
        rotations = self._detect_sector_rotation(prices)
        for rot in rotations:
            self._rotation_history.append(rot)
            self._stats["rotation_signals"] += 1
            await self._trigger_swarm_from_rotation(rot)

        # 3. Mean reversion
        reversions = self._detect_mean_reversion(prices, indicators)
        for rev in reversions:
            self._reversion_history.append(rev)
            self._stats["reversion_signals"] += 1
            await self._trigger_swarm_from_reversion(rev)

        # deque(maxlen=100) handles history trimming automatically

    # ──────────────────────────────────────────────────────────────────────
    # Data Loading
    # ──────────────────────────────────────────────────────────────────────
    async def _load_price_data(self) -> Optional[pd.DataFrame]:
        """Load price data for all tracked symbols from DuckDB."""
        try:
            def _sync():
                from app.data.duckdb_storage import duckdb_store
                conn = duckdb_store.get_thread_cursor()
                return conn.execute("""
                    SELECT symbol, date, close, volume
                    FROM daily_ohlcv
                    WHERE date >= CURRENT_DATE - INTERVAL '90 days'
                    ORDER BY symbol, date
                """).fetchdf()
            df = await asyncio.to_thread(_sync)
            if df.empty:
                return None
            return df
        except Exception as e:
            logger.debug("Price data load failed: %s", e)
            return None

    async def _load_indicator_data(self) -> Optional[pd.DataFrame]:
        """Load indicator data from DuckDB."""
        try:
            def _sync():
                from app.data.duckdb_storage import duckdb_store
                conn = duckdb_store.get_thread_cursor()
                return conn.execute("""
                    SELECT symbol, date, rsi_14, macd, bb_upper, bb_lower, bb_mid,
                           sma_20, sma_50, adx_14
                    FROM technical_indicators
                    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
                    ORDER BY symbol, date
                """).fetchdf()
            df = await asyncio.to_thread(_sync)
            return df if not df.empty else None
        except Exception as e:
            logger.debug("Indicator data load failed: %s", e)
            return None

    # ──────────────────────────────────────────────────────────────────────
    # Correlation Break Detection
    # ──────────────────────────────────────────────────────────────────────
    def _detect_correlation_breaks(self, prices: pd.DataFrame) -> List[CorrelationBreak]:
        """Detect when key pair correlations break from their normal range."""
        breaks = []

        # Pivot prices to wide format
        pivot = prices.pivot_table(index="date", columns="symbol", values="close")
        if pivot.shape[1] < 2:
            return breaks

        # Calculate returns
        returns = pivot.pct_change().dropna()
        if len(returns) < 20:
            return breaks

        for sym_a, sym_b, pair_type in KEY_PAIRS:
            if sym_a not in returns.columns or sym_b not in returns.columns:
                continue

            # Long-term correlation (60 days)
            long_corr = returns[sym_a].tail(60).corr(returns[sym_b].tail(60))
            # Short-term correlation (10 days)
            short_corr = returns[sym_a].tail(10).corr(returns[sym_b].tail(10))

            if np.isnan(long_corr) or np.isnan(short_corr):
                continue

            deviation = abs(short_corr - long_corr)
            cache_key = f"{sym_a}_{sym_b}"
            self._correlation_cache[cache_key] = short_corr

            # Significant deviation = correlation break
            if deviation > 0.4:
                interpretation, trade_idea, analyze = self._interpret_break(
                    sym_a, sym_b, pair_type, long_corr, short_corr
                )
                breaks.append(CorrelationBreak(
                    pair=(sym_a, sym_b),
                    pair_type=pair_type,
                    normal_corr=long_corr,
                    current_corr=short_corr,
                    deviation=deviation,
                    interpretation=interpretation,
                    trade_idea=trade_idea,
                    symbols_to_analyze=analyze,
                ))

        return breaks

    def _interpret_break(
        self, sym_a: str, sym_b: str, pair_type: str,
        normal_corr: float, current_corr: float,
    ) -> Tuple[str, str, List[str]]:
        """Interpret what a correlation break means and suggest trades."""
        interp_map = {
            "equity_breadth": (
                f"SPY-QQQ correlation broke ({normal_corr:.2f} -> {current_corr:.2f}). "
                "Market breadth diverging — watch for leadership rotation.",
                "Lagging index likely to catch up or leader to reverse",
                ["SPY", "QQQ", "IWM"],
            ),
            "risk_appetite": (
                f"SPY-IWM divergence ({normal_corr:.2f} -> {current_corr:.2f}). "
                "Small caps diverging from large — risk appetite shifting.",
                "If IWM lagging: risk-off rotation. If leading: risk-on broadening",
                ["IWM", "SPY", "XLF"],
            ),
            "stocks_vs_bonds": (
                f"SPY-TLT correlation shift ({normal_corr:.2f} -> {current_corr:.2f}). "
                "Stocks/bonds relationship changing — regime shift possible.",
                "Positive correlation = crisis mode. Negative = normal risk-on/off",
                ["SPY", "TLT", "GLD", "UVXY"],
            ),
            "growth_vs_value": (
                f"XLK-XLE rotation signal ({normal_corr:.2f} -> {current_corr:.2f}). "
                "Growth/value rotation underway.",
                "Buy the laggard, sell the leader for mean reversion",
                ["XLK", "XLE", "XLF", "QQQ"],
            ),
            "credit_risk": (
                f"SPY-HYG divergence ({normal_corr:.2f} -> {current_corr:.2f}). "
                "Credit markets diverging from equities — stress signal.",
                "Credit leads equities. HYG weakness = equities to follow",
                ["HYG", "SPY", "XLF", "TLT"],
            ),
        }
        default = (
            f"{sym_a}-{sym_b} correlation broke ({normal_corr:.2f} -> {current_corr:.2f})",
            f"Analyze {sym_a} and {sym_b} for divergence trade",
            [sym_a, sym_b],
        )
        return interp_map.get(pair_type, default)

    # ──────────────────────────────────────────────────────────────────────
    # Sector Rotation Detection
    # ──────────────────────────────────────────────────────────────────────
    def _detect_sector_rotation(self, prices: pd.DataFrame) -> List[RotationSignal]:
        """Detect money flowing between sectors."""
        rotations = []
        pivot = prices.pivot_table(index="date", columns="symbol", values="close")
        if pivot.shape[1] < 3:
            return rotations

        # Calculate sector returns over different windows
        sectors_available = {etf: name for etf, name in SECTOR_ETFS.items() if etf in pivot.columns}
        if len(sectors_available) < 3:
            return rotations

        # 1-day and 5-day returns
        returns_1d = pivot[list(sectors_available.keys())].pct_change(1).iloc[-1]
        returns_5d = pivot[list(sectors_available.keys())].pct_change(5).iloc[-1]

        # Find strongest rotations: big spread between winners and losers
        if returns_5d.isna().all():
            return rotations

        sorted_5d = returns_5d.dropna().sort_values()
        if len(sorted_5d) < 4:
            return rotations

        # Bottom 2 vs top 2 sectors
        losers = sorted_5d.head(2)
        winners = sorted_5d.tail(2)

        for loser_etf, loser_ret in losers.items():
            for winner_etf, winner_ret in winners.items():
                spread = winner_ret - loser_ret
                if spread > ROTATION_THRESHOLD:
                    # Check if this is a reversal setup (1d return opposite of 5d)
                    loser_1d = returns_1d.get(loser_etf, 0)
                    winner_1d = returns_1d.get(winner_etf, 0)

                    trade_ideas = []
                    # The loser today may be tomorrow's winner (mean reversion)
                    if loser_ret < -0.02:
                        trade_ideas.append({
                            "symbol": loser_etf,
                            "direction": "buy",
                            "rationale": f"{sectors_available[loser_etf]} oversold ({loser_ret:.1%} 5d), rotation reversal candidate",
                        })
                    # The winner may be extended
                    if winner_ret > 0.03:
                        trade_ideas.append({
                            "symbol": winner_etf,
                            "direction": "sell",
                            "rationale": f"{sectors_available[winner_etf]} extended ({winner_ret:.1%} 5d), profit-taking likely",
                        })

                    if trade_ideas:
                        strength = min(1.0, spread / 0.10)  # 10% spread = max strength
                        rotations.append(RotationSignal(
                            from_sector=sectors_available.get(loser_etf, loser_etf),
                            to_sector=sectors_available.get(winner_etf, winner_etf),
                            strength=strength,
                            from_return=loser_ret,
                            to_return=winner_ret,
                            spread=spread,
                            trade_ideas=trade_ideas,
                        ))

        return rotations[:5]  # Cap at 5 rotation signals

    # ──────────────────────────────────────────────────────────────────────
    # Mean Reversion Detection
    # ──────────────────────────────────────────────────────────────────────
    def _detect_mean_reversion(
        self, prices: pd.DataFrame, indicators: Optional[pd.DataFrame],
    ) -> List[MeanReversionSignal]:
        """Find symbols that are overextended and likely to snap back."""
        signals = []
        pivot = prices.pivot_table(index="date", columns="symbol", values="close")
        if pivot.shape[1] < 2:
            return signals

        returns = pivot.pct_change()

        for symbol in pivot.columns:
            col = returns[symbol].dropna()
            if len(col) < REVERSION_LOOKBACK:
                continue

            # Calculate z-score of recent return vs historical
            ret_5d = col.tail(5).sum()
            ret_mean = col.tail(60).mean() * 5  # 5-day mean return
            ret_std = col.tail(60).std() * np.sqrt(5)

            if ret_std == 0:
                continue

            zscore = (ret_5d - ret_mean) / ret_std

            # Get RSI and Bollinger position from indicators
            rsi = 50.0
            bb_pct = 0.5
            if indicators is not None and not indicators.empty:
                sym_ind = indicators[indicators["symbol"] == symbol]
                if not sym_ind.empty:
                    latest = sym_ind.iloc[-1]
                    rsi = float(latest.get("rsi_14", 50) or 50)
                    bb_upper = float(latest.get("bb_upper", 0) or 0)
                    bb_lower = float(latest.get("bb_lower", 0) or 0)
                    bb_mid = float(latest.get("bb_mid", 0) or 0)
                    last_close = float(pivot[symbol].iloc[-1])
                    if bb_upper > bb_lower:
                        bb_pct = (last_close - bb_lower) / (bb_upper - bb_lower)

            # Check for mean reversion setup
            if zscore < -REVERSION_ZSCORE_THRESHOLD and rsi < 35:
                # Oversold — bounce candidate
                prob = min(0.85, 0.4 + abs(zscore) * 0.1 + (35 - rsi) * 0.005)
                signals.append(MeanReversionSignal(
                    symbol=symbol,
                    direction="oversold",
                    zscore=zscore,
                    return_5d=ret_5d,
                    rsi=rsi,
                    bollinger_pct=bb_pct,
                    reversal_probability=prob,
                    trade_idea=f"BUY {symbol}: oversold (z={zscore:.1f}, RSI={rsi:.0f}), bounce likely",
                ))
            elif zscore > REVERSION_ZSCORE_THRESHOLD and rsi > 65:
                # Overbought — pullback candidate
                prob = min(0.85, 0.4 + abs(zscore) * 0.1 + (rsi - 65) * 0.005)
                signals.append(MeanReversionSignal(
                    symbol=symbol,
                    direction="overbought",
                    zscore=zscore,
                    return_5d=ret_5d,
                    rsi=rsi,
                    bollinger_pct=bb_pct,
                    reversal_probability=prob,
                    trade_idea=f"SELL {symbol}: overbought (z={zscore:.1f}, RSI={rsi:.0f}), pullback likely",
                ))

        # Sort by absolute z-score (most extreme first)
        signals.sort(key=lambda s: abs(s.zscore), reverse=True)
        return signals[:15]  # Top 15 most extreme

    # ──────────────────────────────────────────────────────────────────────
    # Swarm Triggering
    # ──────────────────────────────────────────────────────────────────────
    async def _trigger_swarm_from_break(self, brk: CorrelationBreak):
        self._stats["swarms_triggered"] += 1
        await self._publish_idea(
            symbols=brk.symbols_to_analyze,
            direction="unknown",
            reasoning=f"CORRELATION BREAK [{brk.pair_type}]: {brk.interpretation}. {brk.trade_idea}",
            priority=3,
            metadata={"signal_type": "correlation_break", "pair": list(brk.pair)},
        )

    async def _trigger_swarm_from_rotation(self, rot: RotationSignal):
        self._stats["swarms_triggered"] += 1
        for idea in rot.trade_ideas:
            direction = "bullish" if idea["direction"] == "buy" else "bearish"
            await self._publish_idea(
                symbols=[idea["symbol"]],
                direction=direction,
                reasoning=f"ROTATION: {rot.from_sector} -> {rot.to_sector} (spread={rot.spread:.1%}). {idea['rationale']}",
                priority=3,
                metadata={"signal_type": "sector_rotation"},
            )

    async def _trigger_swarm_from_reversion(self, rev: MeanReversionSignal):
        self._stats["swarms_triggered"] += 1
        direction = "bullish" if rev.direction == "oversold" else "bearish"
        await self._publish_idea(
            symbols=[rev.symbol],
            direction=direction,
            reasoning=f"MEAN REVERSION: {rev.trade_idea} (prob={rev.reversal_probability:.0%})",
            priority=3,
            metadata={
                "signal_type": "mean_reversion",
                "zscore": rev.zscore,
                "rsi": rev.rsi,
                "reversal_probability": rev.reversal_probability,
            },
        )

    async def _publish_idea(self, symbols, direction, reasoning, priority=3, metadata=None):
        if self._bus:
            await self._bus.publish("swarm.idea", {
                "source": "correlation_radar",
                "symbols": symbols,
                "direction": direction,
                "reasoning": reasoning,
                "priority": priority,
                "metadata": metadata or {},
            })

    # ──────────────────────────────────────────────────────────────────────
    # Status / API
    # ──────────────────────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "scan_interval": self._scan_interval,
            "stats": dict(self._stats),
            "correlation_cache": {k: round(v, 3) for k, v in self._correlation_cache.items()},
            "recent_breaks": [b.to_dict() for b in list(self._break_history)[-5:]],
            "recent_rotations": [r.to_dict() for r in list(self._rotation_history)[-5:]],
            "recent_reversions": [r.to_dict() for r in list(self._reversion_history)[-5:]],
        }

    def get_correlation_matrix(self) -> Dict[str, Any]:
        """Return the full correlation matrix for API consumers."""
        return {
            "pairs": dict(self._correlation_cache),
            "key_pairs": [
                {"pair": [a, b], "type": t, "correlation": self._correlation_cache.get(f"{a}_{b}")}
                for a, b, t in KEY_PAIRS
            ],
        }

    def get_rotation_signals(self, limit: int = 20) -> List[Dict]:
        return [r.to_dict() for r in list(self._rotation_history)[-limit:]]

    def get_reversion_signals(self, limit: int = 20) -> List[Dict]:
        return [r.to_dict() for r in list(self._reversion_history)[-limit:]]

    async def get_correlation_breaks(self, threshold: float = 0.75, limit: int = 20) -> List[Dict]:
        """Return recent correlation breaks from cached history (used by CorrelationBreakScout)."""
        results = []
        for brk in list(self._break_history)[-limit:]:
            d = brk.to_dict()
            if abs(d.get("correlation", 1.0)) < threshold or d.get("delta", 0) > (1 - threshold):
                results.append(d)
        return results

    async def get_sector_divergences(self, symbols: List[str] = None, limit: int = 20) -> List[Dict]:
        """Return recent sector rotation signals from cached history (used by SectorRotationScout)."""
        results = []
        for rot in list(self._rotation_history)[-limit:]:
            d = rot.to_dict()
            if symbols and d.get("symbol") not in symbols:
                continue
            results.append(d)
        return results


# Module-level singleton
_radar: Optional[CorrelationRadar] = None

def get_correlation_radar() -> CorrelationRadar:
    global _radar
    if _radar is None:
        _radar = CorrelationRadar()
    return _radar
