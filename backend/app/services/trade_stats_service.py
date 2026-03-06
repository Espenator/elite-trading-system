"""Trade Stats Service — real win/loss statistics from DuckDB.

Replaces hardcoded win_rate / avg_win / avg_loss in order_executor.py
with actual historical performance data from the trade_outcomes table.

Falls back to conservative priors when insufficient data exists,
then blends prior with observed data as trades accumulate (Bayesian).

Used by:
    - OrderExecutor._compute_kelly_size() for position sizing
    - WeightLearner for outcome-based weight updates
    - Council API for performance reporting
"""
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Conservative Bayesian priors (used when < min_trades)
PRIOR_WIN_RATE = 0.45
PRIOR_AVG_WIN_PCT = 0.025
PRIOR_AVG_LOSS_PCT = 0.018
PRIOR_TRADE_COUNT = 30  # Effective weight of the prior


class TradeStatsService:
    """Fetch and cache real trade statistics from DuckDB.

    Parameters
    ----------
    cache_ttl : int
        Seconds to cache stats before re-querying DuckDB.
    min_trades : int
        Minimum real trades before fully trusting observed data.
        Below this, we blend prior with observed.
    """

    def __init__(self, cache_ttl: int = 300, min_trades: int = 30):
        self.cache_ttl = cache_ttl
        self.min_trades = min_trades
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_time: Dict[str, float] = {}
        self._global_cache: Optional[Dict[str, Any]] = None
        self._global_cache_time: float = 0

    def get_stats(
        self, symbol: Optional[str] = None, regime: str = "NEUTRAL", side: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get trade statistics, optionally filtered by symbol and regime.

        Returns a dict with keys:
            win_rate, avg_win_pct, avg_loss_pct, trade_count,
            avg_r_multiple, sharpe_estimate, data_source

        Parameters
        ----------
        symbol : str or None
            If provided, get stats for this specific symbol.
            If None, get global portfolio stats.
        regime : str
            Current market regime for regime-specific stats.
        """
        cache_key = f"{symbol or 'GLOBAL'}_{regime}_{side or 'ALL'}"
        now = time.time()

        # Check cache
        if cache_key in self._cache:
            if now - self._cache_time.get(cache_key, 0) < self.cache_ttl:
                return self._cache[cache_key]

        # Query DuckDB
        stats = self._query_stats(symbol, regime, side)

        # Cache result
        self._cache[cache_key] = stats
        self._cache_time[cache_key] = now
        return stats

    def _query_stats(
        self, symbol: Optional[str], regime: str, side: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query trade_outcomes from DuckDB and compute statistics."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()

            # Ensure table exists
            tables = [
                r[0]
                for r in conn.execute(
                    "SELECT table_name FROM information_schema.tables"
                ).fetchall()
            ]
            if "trade_outcomes" not in tables:
                return self._prior_stats("no_table")

            # Build query with optional filters
            where_clauses = []
            params = []

            if symbol:
                where_clauses.append("symbol = ?")
                params.append(symbol.upper())

            if regime and regime != "NEUTRAL":
                where_clauses.append("regime = ?")
                params.append(regime.upper())

                        if side:
                where_clauses.append("side = ?")
                params.append(side.lower())

            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)

            query = f"""
                SELECT
                    COUNT(*) as trade_count,
                    COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins,
                    COUNT(CASE WHEN pnl <= 0 THEN 1 END) as losses,
                    AVG(CASE WHEN pnl > 0 THEN pnl_pct END) as avg_win_pct,
                    AVG(CASE WHEN pnl <= 0 THEN ABS(pnl_pct) END) as avg_loss_pct,
                    AVG(r_multiple) as avg_r_multiple,
                    STDDEV(pnl_pct) as pnl_std
                FROM trade_outcomes
                {where_sql}
            """

            row = conn.execute(query, params).fetchone()

            if not row or row[0] == 0:
                return self._prior_stats("no_data")

            trade_count = int(row[0])
            wins = int(row[1])
            losses = int(row[2])
            obs_win_rate = wins / trade_count if trade_count > 0 else 0.5
            obs_avg_win = float(row[3] or 0.025)
            obs_avg_loss = float(row[4] or 0.018)
            obs_avg_r = float(row[5] or 0.0)
            pnl_std = float(row[6] or 0.02)

            # Bayesian blend: weight prior vs observed based on sample size
            prior_weight = max(0, self.min_trades - trade_count)
            total_weight = trade_count + prior_weight

            if total_weight > 0:
                blended_win_rate = (
                    obs_win_rate * trade_count
                    + PRIOR_WIN_RATE * prior_weight
                ) / total_weight
                blended_avg_win = (
                    obs_avg_win * trade_count
                    + PRIOR_AVG_WIN_PCT * prior_weight
                ) / total_weight
                blended_avg_loss = (
                    obs_avg_loss * trade_count
                    + PRIOR_AVG_LOSS_PCT * prior_weight
                ) / total_weight
            else:
                blended_win_rate = PRIOR_WIN_RATE
                blended_avg_win = PRIOR_AVG_WIN_PCT
                blended_avg_loss = PRIOR_AVG_LOSS_PCT

            # Sharpe estimate (annualized)
            if pnl_std > 0:
                mean_return = (
                    blended_win_rate * blended_avg_win
                    - (1 - blended_win_rate) * blended_avg_loss
                )
                sharpe = (mean_return / pnl_std) * (252 ** 0.5)
            else:
                sharpe = 0.0

            return {
                "win_rate": round(blended_win_rate, 4),
                "avg_win_pct": round(blended_avg_win, 4),
                "avg_loss_pct": round(blended_avg_loss, 4),
                "trade_count": trade_count,
                "observed_win_rate": round(obs_win_rate, 4),
                "avg_r_multiple": round(obs_avg_r, 4),
                "sharpe_estimate": round(sharpe, 2),
                "prior_blend_pct": round(prior_weight / max(total_weight, 1), 2),
                "data_source": "duckdb",
            }

        except Exception as e:
            logger.warning("TradeStatsService query failed: %s", e)
            return self._prior_stats("error")

    def _prior_stats(self, reason: str) -> Dict[str, Any]:
        """Return conservative prior statistics when no data available."""
        return {
            "win_rate": PRIOR_WIN_RATE,
            "avg_win_pct": PRIOR_AVG_WIN_PCT,
            "avg_loss_pct": PRIOR_AVG_LOSS_PCT,
            "trade_count": 0,
            "observed_win_rate": 0.0,
            "avg_r_multiple": 0.0,
            "sharpe_estimate": 0.0,
            "prior_blend_pct": 1.0,
            "data_source": f"prior ({reason})",
        }

    def record_outcome(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        qty: int,
        regime: str = "NEUTRAL", side: Optional[str] = None,
        signal_score: float = 0.0,
        kelly_pct: float = 0.0,
    ) -> None:
        """Record a trade outcome to DuckDB for future stats."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()

            # Create table if needed
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_outcomes (
                    id INTEGER PRIMARY KEY,
                    symbol VARCHAR,
                    side VARCHAR,
                    entry_price DOUBLE,
                    exit_price DOUBLE,
                    qty INTEGER,
                    pnl DOUBLE,
                    pnl_pct DOUBLE,
                    r_multiple DOUBLE,
                    regime VARCHAR,
                    signal_score DOUBLE,
                    kelly_pct DOUBLE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            if side == "buy":
                pnl = (exit_price - entry_price) * qty
                pnl_pct = (exit_price / entry_price - 1) if entry_price > 0 else 0
            else:
                pnl = (entry_price - exit_price) * qty
                pnl_pct = (entry_price / exit_price - 1) if exit_price > 0 else 0

            # R-multiple: pnl relative to risk (approximated as 2% stop)
            risk = entry_price * 0.02 * qty
            r_multiple = pnl / risk if risk > 0 else 0

            conn.execute(
                """INSERT INTO trade_outcomes
                   (symbol, side, entry_price, exit_price, qty,
                    pnl, pnl_pct, r_multiple, regime, signal_score, kelly_pct)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    symbol.upper(), side, entry_price, exit_price, qty,
                    round(pnl, 2), round(pnl_pct, 6), round(r_multiple, 4),
                    regime, signal_score, kelly_pct,
                ],
            )

            # Invalidate cache
            self._cache.clear()
            self._cache_time.clear()

            # Trigger weight learning
            try:
                from app.council.weight_learner import get_weight_learner
                learner = get_weight_learner()
                outcome_dir = "win" if pnl > 0 else "loss"
                learner.update_from_outcome(
                    symbol=symbol,
                    outcome_direction=outcome_dir,
                    pnl=pnl,
                    r_multiple=r_multiple,
                )
            except Exception:
                pass

            logger.info(
                "Recorded trade outcome: %s %s %d @ $%.2f->$%.2f "
                "PnL=$%.2f (%.2f%%, R=%.2f)",
                side, symbol, qty, entry_price, exit_price,
                pnl, pnl_pct * 100, r_multiple,
            )

        except Exception as e:
            logger.warning("Failed to record trade outcome: %s", e)


# Module singleton
_stats_instance: Optional[TradeStatsService] = None


def get_trade_stats() -> TradeStatsService:
    """Get or create the global TradeStatsService singleton."""
    global _stats_instance
    if _stats_instance is None:
        _stats_instance = TradeStatsService()
    return _stats_instance
