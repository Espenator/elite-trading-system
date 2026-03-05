"""
DuckDB Analytics Storage — OHLCV, indicators, options flow, trade outcomes.

Separate from storage.py (SQLite for orders/config).
This is the ML/analytics database optimized for columnar scans.

Usage:
    from app.data.duckdb_storage import duckdb_store
    df = duckdb_store.get_training_window(["AAPL", "MSFT"], "2025-01-01", "2026-01-01")

Fixes Issue #25 — DuckDB query engine for feature pipeline.
"""

import logging
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DuckDB connection management
# ---------------------------------------------------------------------------
DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DUCKDB_PATH = DB_DIR / "analytics.duckdb"

_lock = threading.Lock()


def _get_duckdb():
    """Import duckdb with graceful fallback."""
    try:
        import duckdb
        return duckdb
    except ImportError:
        logger.error("duckdb not installed. Run: pip install duckdb")
        raise


class DuckDBStorage:
    """Analytics database for ML training and backtesting."""

    def __init__(self, db_path: str = None):
        self._db_path = str(db_path or DUCKDB_PATH)
        self._conn = None
        self._init_schema()

    def _get_conn(self):
        """Thread-safe connection with WAL mode."""
        if self._conn is None:
            with _lock:
                if self._conn is None:
                    duckdb = _get_duckdb()
                    self._conn = duckdb.connect(self._db_path)
                    self._conn.execute("PRAGMA enable_progress_bar")
        return self._conn

    def query(self, sql: str, params=None):
        """Execute a read-only query and return the result.

        Args:
            sql: SQL query string.
            params: Optional list of parameters for parameterized queries.

        Returns:
            DuckDB query result (use .fetchone(), .fetchall(), .fetchdf()).
        """
        conn = self._get_conn()
        if params:
            return conn.execute(sql, params)
        return conn.execute(sql)

    def _init_schema(self):
        """Create analytics tables if they don't exist."""
        conn = self._get_conn()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_ohlcv (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                source VARCHAR DEFAULT 'alpaca',
                PRIMARY KEY (symbol, date)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS technical_indicators (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                rsi_14 DOUBLE,
                macd DOUBLE,
                macd_signal DOUBLE,
                macd_hist DOUBLE,
                sma_20 DOUBLE,
                sma_50 DOUBLE,
                sma_200 DOUBLE,
                ema_9 DOUBLE,
                ema_21 DOUBLE,
                atr_14 DOUBLE,
                atr_21 DOUBLE,
                bb_upper DOUBLE,
                bb_lower DOUBLE,
                bb_middle DOUBLE,
                adx_14 DOUBLE,
                williams_r DOUBLE,
                PRIMARY KEY (symbol, date)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS options_flow (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                call_volume BIGINT,
                put_volume BIGINT,
                net_premium DOUBLE,
                pcr_volume DOUBLE,
                dark_pool_volume BIGINT,
                total_premium DOUBLE,
                source VARCHAR DEFAULT 'unusual_whales',
                PRIMARY KEY (symbol, date)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS macro_data (
                date DATE NOT NULL PRIMARY KEY,
                vix_close DOUBLE,
                dxy_close DOUBLE,
                us10y_yield DOUBLE,
                fed_funds_rate DOUBLE,
                spy_close DOUBLE,
                qqq_close DOUBLE,
                breadth_ratio DOUBLE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_outcomes (
                id INTEGER PRIMARY KEY,
                symbol VARCHAR NOT NULL,
                direction VARCHAR NOT NULL,
                entry_date DATE NOT NULL,
                exit_date DATE,
                entry_price DOUBLE NOT NULL,
                exit_price DOUBLE,
                shares INTEGER,
                pnl DOUBLE,
                r_multiple DOUBLE,
                outcome VARCHAR,
                stop_price DOUBLE,
                target_price DOUBLE,
                signal_score DOUBLE,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS ml_features_cache (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                feature_json VARCHAR,
                pipeline_version VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, date, pipeline_version)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS features (
                symbol VARCHAR NOT NULL,
                ts TIMESTAMP NOT NULL,
                timeframe VARCHAR NOT NULL DEFAULT '1d',
                feature_json VARCHAR,
                feature_hash VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, ts, timeframe)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS model_evals (
                eval_id VARCHAR PRIMARY KEY,
                model_id VARCHAR NOT NULL,
                "window" VARCHAR NOT NULL,
                sharpe DOUBLE,
                profit_factor DOUBLE,
                win_rate DOUBLE,
                max_dd DOUBLE,
                passed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes for fast range scans
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON daily_ohlcv (date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol ON daily_ohlcv (symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ti_date ON technical_indicators (date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flow_date ON options_flow (date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_symbol ON trade_outcomes (symbol, entry_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_features_symbol_ts ON features (symbol, ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_model_evals_model ON model_evals (model_id)")

        logger.info("DuckDB analytics schema initialized at %s", self._db_path)

    # ------------------------------------------------------------------
    # WRITE methods (called by data ingestion services)
    # ------------------------------------------------------------------

    def upsert_ohlcv(self, df: pd.DataFrame) -> int:
        """Insert or update OHLCV data.

        Args:
            df: Must have columns: symbol, date, open, high, low, close, volume

        Returns:
            Number of rows upserted.
        """
        if df.empty:
            return 0
        conn = self._get_conn()
        conn.execute("CREATE OR REPLACE TEMP TABLE _staging AS SELECT * FROM daily_ohlcv LIMIT 0")
        conn.execute("INSERT INTO _staging SELECT * FROM df")
        conn.execute("""
            INSERT OR REPLACE INTO daily_ohlcv
            SELECT * FROM _staging
        """)
        logger.info("Upserted %d OHLCV rows", len(df))
        return len(df)

    def upsert_indicators(self, df: pd.DataFrame) -> int:
        """Insert or update technical indicator data."""
        if df.empty:
            return 0
        conn = self._get_conn()
        conn.execute("INSERT OR REPLACE INTO technical_indicators SELECT * FROM df")
        logger.info("Upserted %d indicator rows", len(df))
        return len(df)

    def upsert_options_flow(self, df: pd.DataFrame) -> int:
        """Insert or update options flow data from Unusual Whales."""
        if df.empty:
            return 0
        conn = self._get_conn()
        conn.execute("INSERT OR REPLACE INTO options_flow SELECT * FROM df")
        logger.info("Upserted %d options flow rows", len(df))
        return len(df)

    def upsert_macro(self, df: pd.DataFrame) -> int:
        """Insert or update macro data from FRED."""
        if df.empty:
            return 0
        conn = self._get_conn()
        conn.execute("INSERT OR REPLACE INTO macro_data SELECT * FROM df")
        logger.info("Upserted %d macro rows", len(df))
        return len(df)

    def insert_trade_outcome(self, trade: Dict) -> None:
        """Record a trade outcome for ML label generation."""
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO trade_outcomes
            (symbol, direction, entry_date, exit_date, entry_price, exit_price,
             shares, pnl, r_multiple, outcome, stop_price, target_price,
             signal_score, resolved, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            trade["symbol"], trade["direction"],
            trade["entry_date"], trade.get("exit_date"),
            trade["entry_price"], trade.get("exit_price"),
            trade.get("shares", 0), trade.get("pnl", 0.0),
            trade.get("r_multiple", 0.0), trade.get("outcome", "PENDING"),
            trade.get("stop_price"), trade.get("target_price"),
            trade.get("signal_score", 0.0),
            trade.get("resolved", False), trade.get("resolved_at")
        ])

    # ------------------------------------------------------------------
    # READ methods (called by feature pipeline and training)
    # ------------------------------------------------------------------

    def get_training_window(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        include_indicators: bool = True,
        include_flow: bool = True,
        include_macro: bool = True,
    ) -> pd.DataFrame:
        """Fetch joined OHLCV + indicators + flow + macro for training.

        This is the primary method called by FeaturePipeline.

        Args:
            symbols: List of tickers
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            include_indicators: Join technical indicators
            include_flow: Join options flow data
            include_macro: Join macro data

        Returns:
            DataFrame with columns ready for FeaturePipeline.generate()
        """
        conn = self._get_conn()
        placeholders = ",".join(["?" for _ in symbols])

        query = f"""
            SELECT o.symbol, o.date, o.open, o.high, o.low, o.close, o.volume
            FROM daily_ohlcv o
            WHERE o.symbol IN ({placeholders})
              AND o.date BETWEEN ? AND ?
            ORDER BY o.symbol, o.date
        """
        params = symbols + [start_date, end_date]
        df = conn.execute(query, params).fetchdf()

        if df.empty:
            logger.warning("No OHLCV data for %s between %s and %s", symbols, start_date, end_date)
            return df

        if include_indicators:
            ti = conn.execute(f"""
                SELECT * FROM technical_indicators
                WHERE symbol IN ({placeholders})
                  AND date BETWEEN ? AND ?
            """, params).fetchdf()
            if not ti.empty:
                df = df.merge(ti, on=["symbol", "date"], how="left")

        if include_flow:
            flow = conn.execute(f"""
                SELECT * FROM options_flow
                WHERE symbol IN ({placeholders})
                  AND date BETWEEN ? AND ?
            """, params).fetchdf()
            if not flow.empty:
                df = df.merge(flow, on=["symbol", "date"], how="left")

        if include_macro:
            macro = conn.execute("""
                SELECT * FROM macro_data
                WHERE date BETWEEN ? AND ?
            """, [start_date, end_date]).fetchdf()
            if not macro.empty:
                df = df.merge(macro, on="date", how="left")

        logger.info(
            "Training window: %d rows, %d symbols, %d columns, %s to %s",
            len(df), df["symbol"].nunique(), len(df.columns), start_date, end_date
        )
        return df

    def get_inference_snapshot(
        self,
        symbols: List[str],
        lookback_days: int = 250,
    ) -> pd.DataFrame:
        """Fetch latest N days of data for real-time inference.

        Identical schema to get_training_window but uses relative date range.
        """
        conn = self._get_conn()
        placeholders = ",".join(["?" for _ in symbols])

        df = conn.execute(f"""
            SELECT o.symbol, o.date, o.open, o.high, o.low, o.close, o.volume
            FROM daily_ohlcv o
            WHERE o.symbol IN ({placeholders})
              AND o.date >= CURRENT_DATE - INTERVAL '{lookback_days}' DAY
            ORDER BY o.symbol, o.date
        """, symbols).fetchdf()

        # Join indicators
        if not df.empty:
            ti = conn.execute(f"""
                SELECT * FROM technical_indicators
                WHERE symbol IN ({placeholders})
                  AND date >= CURRENT_DATE - INTERVAL '{lookback_days}' DAY
            """, symbols).fetchdf()
            if not ti.empty:
                df = df.merge(ti, on=["symbol", "date"], how="left")

            flow = conn.execute(f"""
                SELECT * FROM options_flow
                WHERE symbol IN ({placeholders})
                  AND date >= CURRENT_DATE - INTERVAL '{lookback_days}' DAY
            """, symbols).fetchdf()
            if not flow.empty:
                df = df.merge(flow, on=["symbol", "date"], how="left")

            macro = conn.execute(f"""
                SELECT * FROM macro_data
                WHERE date >= CURRENT_DATE - INTERVAL '{lookback_days}' DAY
            """).fetchdf()
            if not macro.empty:
                df = df.merge(macro, on="date", how="left")

        return df

    def get_unresolved_trades(self) -> pd.DataFrame:
        """Fetch trades that need outcome resolution."""
        conn = self._get_conn()
        return conn.execute("""
            SELECT * FROM trade_outcomes
            WHERE resolved = FALSE
            ORDER BY entry_date
        """).fetchdf()

    def get_symbol_count(self) -> int:
        """Count distinct symbols in OHLCV data."""
        conn = self._get_conn()
        result = conn.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv").fetchone()
        return result[0] if result else 0

    def get_date_range(self) -> Tuple[Optional[str], Optional[str]]:
        """Get min/max dates in OHLCV data."""
        conn = self._get_conn()
        result = conn.execute("SELECT MIN(date), MAX(date) FROM daily_ohlcv").fetchone()
        if result and result[0]:
            return str(result[0]), str(result[1])
        return None, None

    def get_connection(self):
        """Public accessor for the DuckDB connection.

        Use this instead of accessing _get_conn() directly from outside
        this module.
        """
        return self._get_conn()

    def health_check(self) -> Dict:
        """Return storage health metrics."""
        conn = self._get_conn()
        ohlcv = conn.execute("SELECT COUNT(*) FROM daily_ohlcv").fetchone()[0]
        indicators = conn.execute("SELECT COUNT(*) FROM technical_indicators").fetchone()[0]
        flow = conn.execute("SELECT COUNT(*) FROM options_flow").fetchone()[0]
        macro = conn.execute("SELECT COUNT(*) FROM macro_data").fetchone()[0]
        outcomes = conn.execute("SELECT COUNT(*) FROM trade_outcomes").fetchone()[0]
        features = conn.execute("SELECT COUNT(*) FROM features").fetchone()[0]
        evals = conn.execute("SELECT COUNT(*) FROM model_evals").fetchone()[0]
        total_rows = ohlcv + indicators + flow + macro + outcomes + features + evals
        return {
            "db_path": self._db_path,
            "total_tables": 7,
            "total_rows": total_rows,
            "ohlcv_rows": ohlcv,
            "indicator_rows": indicators,
            "flow_rows": flow,
            "macro_rows": macro,
            "trade_outcomes": outcomes,
            "feature_rows": features,
            "model_eval_rows": evals,
            "symbols": self.get_symbol_count(),
            "date_range": self.get_date_range(),
        }


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------
duckdb_store = DuckDBStorage()
