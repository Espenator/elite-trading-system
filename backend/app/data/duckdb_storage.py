"""
DuckDB Analytics Storage — OHLCV, indicators, options flow, trade outcomes.

Separate from storage.py (SQLite for orders/config).
This is the ML/analytics database optimized for columnar scans.

Usage:
    from app.data.duckdb_storage import duckdb_store
    df = duckdb_store.get_training_window(["AAPL", "MSFT"], "2025-01-01", "2026-01-01")

Fixes Issue #25 — DuckDB query engine for feature pipeline.
"""

import asyncio
import logging
import threading
from datetime import date, datetime
from functools import partial
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
    """Analytics database for ML training and backtesting.

    AUDIT FIX (Task 5): Uses asyncio.Lock for async contexts and runs
    blocking DuckDB operations via asyncio.to_thread() to avoid blocking
    the FastAPI event loop. The threading.Lock is kept for sync callers
    (startup, tests) while async callers use the async-safe path.

    SINGLETON PATTERN: Uses lazy initialization to ensure only one instance
    exists and connections are created only when needed, not at import time.
    """

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, db_path: str = None):
        """Ensure only one instance of DuckDBStorage exists (singleton pattern).

        Args:
            db_path: Path to the DuckDB database file. Only used on first instantiation.
                    Subsequent calls with different paths will raise ValueError.

        Returns:
            The singleton instance of DuckDBStorage.

        Raises:
            ValueError: If db_path is provided and differs from the existing instance's path.
        """
        if cls._instance is None:
            with cls._instance_lock:
                # Double-check locking pattern
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        else:
            # If instance exists and db_path is explicitly provided, validate it matches
            if db_path is not None and hasattr(cls._instance, '_db_path'):
                requested_path = str(db_path)
                existing_path = cls._instance._db_path
                if requested_path != existing_path:
                    raise ValueError(
                        f"DuckDBStorage singleton already initialized with path '{existing_path}'. "
                        f"Cannot reinitialize with different path '{requested_path}'. "
                        f"Use the existing singleton instance instead."
                    )
        return cls._instance

    def __init__(self, db_path: str = None):
        """Initialize the DuckDBStorage instance.

        Only initializes once (singleton pattern). Subsequent calls are no-ops.

        Args:
            db_path: Path to the DuckDB database file. Only used on first initialization.
        """
        # Only initialize once (singleton pattern)
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._db_path = str(db_path or DUCKDB_PATH)
        self._conn = None
        self._lock = threading.RLock()  # Reentrant — upsert methods hold lock around _get_conn()
        # SF10 FIX: Create asyncio.Lock eagerly with thread-safe guard.
        # Lazy creation caused race where two coroutines could each create
        # a separate asyncio.Lock, defeating the purpose of the lock.
        self._async_lock = None
        self._async_lock_init = threading.Lock()
        self._schema_initialized = False
        self._initialized = True

    def _get_async_lock(self) -> asyncio.Lock:
        """Get or create the asyncio.Lock (thread-safe lazy init)."""
        if self._async_lock is None:
            with self._async_lock_init:
                if self._async_lock is None:
                    self._async_lock = asyncio.Lock()
        return self._async_lock

    def _get_conn(self):
        """Thread-safe connection (sync callers).

        Lazily creates the connection and initializes schema on first use.
        """
        with self._lock:
            if self._conn is None:
                duckdb = _get_duckdb()
                self._conn = duckdb.connect(self._db_path)
                self._conn.execute("SET enable_progress_bar = true")
                # Initialize schema on first connection
                if not self._schema_initialized:
                    self._init_schema_internal(self._conn)
                    self._schema_initialized = True
            return self._conn

    async def async_execute(self, query: str, params=None):
        """Execute a DuckDB query without blocking the event loop.

        Wraps the blocking DuckDB call in asyncio.to_thread() so it runs
        in the thread pool, preventing event loop stalls when 23+ services
        are all doing concurrent reads/writes.
        """
        def _run():
            conn = self._get_conn()
            with self._lock:
                if params:
                    return conn.execute(query, params).fetchall()
                return conn.execute(query).fetchall()
        return await asyncio.to_thread(_run)

    async def async_execute_df(self, query: str, params=None):
        """Execute a DuckDB query and return a DataFrame without blocking the event loop."""
        def _run():
            conn = self._get_conn()
            with self._lock:
                if params:
                    return conn.execute(query, params).fetchdf()
                return conn.execute(query).fetchdf()
        return await asyncio.to_thread(_run)

    async def async_insert(self, query: str, params=None):
        """Execute an INSERT/UPDATE without blocking the event loop."""
        def _run():
            conn = self._get_conn()
            with self._lock:
                if params:
                    conn.execute(query, params)
                else:
                    conn.execute(query)
        return await asyncio.to_thread(_run)

    def init_schema(self):
        """Explicitly initialize the database schema.

        Called from main.py on startup. Uses lazy initialization pattern,
        so calling this multiple times is safe (no-op after first call).
        """
        conn = self._get_conn()
        # Schema is initialized in _get_conn if not already done
        logger.info("DuckDB analytics schema ready at %s", self._db_path)

    def get_connection(self):
        """Get the DuckDB connection (public API).

        Returns the singleton connection instance. Prefer using the
        async_execute, async_execute_df, and async_insert methods for
        async contexts to avoid blocking the event loop.

        Returns:
            DuckDB connection object.
        """
        return self._get_conn()

    def get_thread_cursor(self):
        """Get a DuckDB cursor safe for use in thread-pool workers.

        DuckDB connections are NOT thread-safe. When running queries from
        asyncio.to_thread() or concurrent.futures thread pools, callers
        MUST use cursor() instead of the raw connection to avoid segfaults.

        The cursor is backed by the same connection but provides isolation.
        """
        conn = self._get_conn()
        return conn.cursor()

    def close(self):
        """Close the DuckDB connection.

        Called on shutdown. Safe to call multiple times.
        """
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                    logger.info("DuckDB connection closed")
                except Exception as e:
                    logger.warning("Error closing DuckDB connection: %s", e)
                finally:
                    self._conn = None
                    self._schema_initialized = False

    def _init_schema_internal(self, conn):
        """Create analytics tables if they don't exist.

        Args:
            conn: DuckDB connection to use for schema creation.
        """

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

        # Symbol/asset registry (DATABASE-DESIGN-REVIEW) — one row per symbol, drive backfill from here
        conn.execute("""
            CREATE TABLE IF NOT EXISTS symbol_registry (
                symbol VARCHAR NOT NULL PRIMARY KEY,
                asset_class VARCHAR DEFAULT 'us_equity',
                name VARCHAR,
                first_date DATE,
                last_date DATE,
                source VARCHAR DEFAULT 'alpaca',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        conn.execute("CREATE SEQUENCE IF NOT EXISTS trade_outcomes_seq START 1")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_outcomes (
                            id INTEGER PRIMARY KEY DEFAULT nextval('trade_outcomes_seq'),
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
                pipeline_version VARCHAR DEFAULT '1.0.0',
                schema_version VARCHAR DEFAULT '1.0',
                feature_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, ts, timeframe)
            )
        """)

        # Migrate existing features table: add columns that may be missing
        for col, typedef in [
            ("pipeline_version", "VARCHAR DEFAULT '1.0.0'"),
            ("schema_version", "VARCHAR DEFAULT '1.0'"),
            ("feature_count", "INTEGER DEFAULT 0"),
            ("feature_hash", "VARCHAR"),
            ("timeframe", "VARCHAR DEFAULT '1d'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE features ADD COLUMN {col} {typedef}")
            except Exception:
                pass  # Column already exists

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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS postmortems (
                id VARCHAR PRIMARY KEY,
                council_decision_id VARCHAR,
                symbol VARCHAR NOT NULL,
                direction VARCHAR,
                confidence DOUBLE,
                entry_price DOUBLE,
                exit_price DOUBLE,
                pnl DOUBLE,
                agent_votes VARCHAR,
                blackboard_snapshot VARCHAR,
                critic_analysis VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Ingestion events table for tracking adapter ingestion
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_events (
                event_id VARCHAR PRIMARY KEY,
                source VARCHAR NOT NULL,
                source_kind VARCHAR NOT NULL,
                topic VARCHAR,
                symbol VARCHAR,
                entity_id VARCHAR,
                occurred_at TIMESTAMP NOT NULL,
                ingested_at TIMESTAMP NOT NULL,
                sequence INTEGER,
                dedupe_key VARCHAR,
                schema_version VARCHAR DEFAULT '1.0',
                payload_json VARCHAR,
                trace_id VARCHAR
            )
        """)

        # Indexes for fast range scans
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON daily_ohlcv (date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol ON daily_ohlcv (symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol_registry_asset_class ON symbol_registry (asset_class)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ti_date ON technical_indicators (date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flow_date ON options_flow (date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_symbol ON trade_outcomes (symbol, entry_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_features_symbol_ts ON features (symbol, ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_features_pipeline_version ON features (pipeline_version)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_model_evals_model ON model_evals (model_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_postmortems_symbol ON postmortems (symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_postmortems_decision ON postmortems (council_decision_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_source ON ingestion_events (source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_topic ON ingestion_events (topic)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_symbol ON ingestion_events (symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_occurred_at ON ingestion_events (occurred_at)")

        # Job state for idempotent daily jobs (e.g. daily_outcome_update)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_state (
                job_name VARCHAR PRIMARY KEY,
                last_run_date VARCHAR NOT NULL,
                last_run_ts DOUBLE NOT NULL,
                last_result VARCHAR
            )
        """)

        # ── Phase 1: LLM Router telemetry ────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_calls (
                call_id VARCHAR PRIMARY KEY,
                ts TIMESTAMP NOT NULL,
                agent_name VARCHAR NOT NULL,
                stage INTEGER,
                provider VARCHAR NOT NULL,
                model VARCHAR,
                latency_ms DOUBLE,
                cost_usd DOUBLE DEFAULT 0,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                router_reason VARCHAR,
                council_decision_id VARCHAR,
                outcome_correct BOOLEAN
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS adaptive_routing (
                agent_name VARCHAR NOT NULL,
                provider VARCHAR NOT NULL,
                avg_accuracy DOUBLE DEFAULT 0.5,
                avg_latency_ms DOUBLE DEFAULT 0,
                total_cost DOUBLE DEFAULT 0,
                call_count INTEGER DEFAULT 0,
                PRIMARY KEY (agent_name, provider)
            )
        """)

        # ── Phase 2: Debate + Red Team logs ──────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS debate_logs (
                id VARCHAR PRIMARY KEY,
                council_decision_id VARCHAR NOT NULL,
                symbol VARCHAR NOT NULL,
                bull_arguments VARCHAR,
                bear_arguments VARCHAR,
                judge_summary VARCHAR,
                quality_score DOUBLE,
                winner VARCHAR,
                evidence_breadth DOUBLE,
                final_spread DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS red_team_logs (
                id VARCHAR PRIMARY KEY,
                council_decision_id VARCHAR NOT NULL,
                symbol VARCHAR NOT NULL,
                scenarios_json VARCHAR,
                worst_case_loss DOUBLE,
                scenarios_survived INTEGER,
                overall_recommendation VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── Phase 3: Cognitive 1000 — Knowledge system ───────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_memories (
                memory_id VARCHAR PRIMARY KEY,
                agent_name VARCHAR NOT NULL,
                trade_id VARCHAR,
                symbol VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                regime VARCHAR,
                market_context VARCHAR,
                agent_observation VARCHAR,
                agent_vote VARCHAR,
                confidence DOUBLE,
                embedding FLOAT[],
                outcome_r_multiple DOUBLE,
                was_correct BOOLEAN
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS heuristics (
                heuristic_id VARCHAR PRIMARY KEY,
                agent_name VARCHAR NOT NULL,
                regime VARCHAR,
                pattern_name VARCHAR NOT NULL,
                description TEXT,
                condition_vector FLOAT[],
                trigger_conditions VARCHAR,
                win_rate DOUBLE NOT NULL,
                avg_r_multiple DOUBLE,
                sample_size INTEGER NOT NULL,
                bayesian_confidence DOUBLE,
                decay_factor DOUBLE DEFAULT 1.0,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_edges (
                edge_id VARCHAR PRIMARY KEY,
                source_heuristic_id VARCHAR NOT NULL,
                target_heuristic_id VARCHAR NOT NULL,
                relationship VARCHAR NOT NULL,
                strength DOUBLE DEFAULT 0.5,
                co_occurrence_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes for new tables
        conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_calls_agent ON llm_calls (agent_name, ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_calls_decision ON llm_calls (council_decision_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_debate_decision ON debate_logs (council_decision_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_redteam_decision ON red_team_logs (council_decision_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_agent ON agent_memories (agent_name, symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_trade ON agent_memories (trade_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_heuristics_agent ON heuristics (agent_name, regime)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_edges_src ON knowledge_edges (source_heuristic_id)")

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
        with self._lock:
            conn = self._get_conn()
            conn.execute("CREATE OR REPLACE TEMP TABLE _staging AS SELECT * FROM daily_ohlcv LIMIT 0")
            conn.execute("INSERT INTO _staging SELECT * FROM df")
            conn.execute("""
                INSERT OR REPLACE INTO daily_ohlcv
                SELECT * FROM _staging
            """)
            self._update_symbol_registry_from_ohlcv_impl(conn, df)
        logger.info("Upserted %d OHLCV rows", len(df))
        return len(df)

    def upsert_indicators(self, df: pd.DataFrame) -> int:
        """Insert or update technical indicator data."""
        if df.empty:
            return 0
        with self._lock:
            conn = self._get_conn()
            conn.execute("INSERT OR REPLACE INTO technical_indicators SELECT * FROM df")
        logger.info("Upserted %d indicator rows", len(df))
        return len(df)

    def upsert_options_flow(self, df: pd.DataFrame) -> int:
        """Insert or update options flow data from Unusual Whales."""
        if df.empty:
            return 0
        with self._lock:
            conn = self._get_conn()
            conn.execute("INSERT OR REPLACE INTO options_flow SELECT * FROM df")
        logger.info("Upserted %d options flow rows", len(df))
        return len(df)

    def upsert_macro(self, df: pd.DataFrame) -> int:
        """Insert or update macro data from FRED."""
        if df.empty:
            return 0
        with self._lock:
            conn = self._get_conn()
            conn.execute("INSERT OR REPLACE INTO macro_data SELECT * FROM df")
        logger.info("Upserted %d macro rows", len(df))
        return len(df)

    def upsert_symbol_registry(
        self,
        symbol: str,
        asset_class: str = "us_equity",
        name: Optional[str] = None,
        first_date: Optional[date] = None,
        last_date: Optional[date] = None,
        source: str = "alpaca",
    ) -> None:
        """Insert or update one row in symbol_registry (DATABASE-DESIGN-REVIEW)."""
        with self._lock:
            conn = self._get_conn()
            conn.execute("""
                INSERT INTO symbol_registry (symbol, asset_class, name, first_date, last_date, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (symbol) DO UPDATE SET
                    asset_class = COALESCE(excluded.asset_class, symbol_registry.asset_class),
                    name = COALESCE(excluded.name, symbol_registry.name),
                    first_date = CASE
                        WHEN symbol_registry.first_date IS NULL THEN excluded.first_date
                        WHEN excluded.first_date IS NOT NULL AND excluded.first_date < symbol_registry.first_date THEN excluded.first_date
                        ELSE symbol_registry.first_date END,
                    last_date = CASE
                        WHEN symbol_registry.last_date IS NULL THEN excluded.last_date
                        WHEN excluded.last_date IS NOT NULL AND excluded.last_date > symbol_registry.last_date THEN excluded.last_date
                        ELSE symbol_registry.last_date END,
                    source = COALESCE(excluded.source, symbol_registry.source),
                    updated_at = CURRENT_TIMESTAMP
            """, [symbol.upper(), asset_class, name, first_date, last_date, source])

    def _update_symbol_registry_from_ohlcv_impl(self, conn, df: pd.DataFrame) -> int:
        """Update symbol_registry from OHLCV df. Caller must hold self._lock and pass conn."""
        if df.empty or "symbol" not in df.columns or "date" not in df.columns:
            return 0
        agg = df.groupby("symbol").agg({"date": ["min", "max"]}).reset_index()
        agg.columns = ["symbol", "first_date", "last_date"]
        for _, row in agg.iterrows():
            conn.execute("""
                INSERT INTO symbol_registry (symbol, asset_class, first_date, last_date, source, updated_at)
                VALUES (?, 'us_equity', ?, ?, 'alpaca', CURRENT_TIMESTAMP)
                ON CONFLICT (symbol) DO UPDATE SET
                    first_date = CASE WHEN symbol_registry.first_date IS NULL OR excluded.first_date < symbol_registry.first_date
                        THEN excluded.first_date ELSE symbol_registry.first_date END,
                    last_date = CASE WHEN symbol_registry.last_date IS NULL OR excluded.last_date > symbol_registry.last_date
                        THEN excluded.last_date ELSE symbol_registry.last_date END,
                    updated_at = CURRENT_TIMESTAMP
            """, [str(row["symbol"]).upper(), row["first_date"], row["last_date"]])
        return len(agg)

    def update_symbol_registry_from_ohlcv_df(self, df: pd.DataFrame) -> int:
        """Update symbol_registry first_date/last_date from an OHLCV DataFrame (symbol, date columns)."""
        if df.empty or "symbol" not in df.columns or "date" not in df.columns:
            return 0
        with self._lock:
            conn = self._get_conn()
            return self._update_symbol_registry_from_ohlcv_impl(conn, df)

    def insert_trade_outcome(self, trade: Dict) -> None:
        """Record a trade outcome for ML label generation."""
        with self._lock:
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
        placeholders = ",".join(["?" for _ in symbols])
        params = symbols + [start_date, end_date]

        with self._lock:
            conn = self._get_conn()

            query = f"""
                SELECT o.symbol, o.date, o.open, o.high, o.low, o.close, o.volume
                FROM daily_ohlcv o
                WHERE o.symbol IN ({placeholders})
                  AND o.date BETWEEN ? AND ?
                ORDER BY o.symbol, o.date
            """
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
        placeholders = ",".join(["?" for _ in symbols])
        # Sanitize lookback_days to prevent SQL injection
        lookback_days = max(1, min(int(lookback_days), 5000))

        with self._lock:
            conn = self._get_conn()

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
        with self._lock:
            conn = self._get_conn()
            return conn.execute("""
                SELECT * FROM trade_outcomes
                WHERE resolved = FALSE
                ORDER BY entry_date
            """).fetchdf()

    def get_symbol_count(self) -> int:
        """Count distinct symbols in OHLCV data."""
        with self._lock:
            conn = self._get_conn()
            result = conn.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv").fetchone()
        return result[0] if result else 0

    def get_date_range(self) -> Tuple[Optional[str], Optional[str]]:
        """Get min/max dates in OHLCV data."""
        with self._lock:
            conn = self._get_conn()
            result = conn.execute("SELECT MIN(date), MAX(date) FROM daily_ohlcv").fetchone()
        if result and result[0]:
            return str(result[0]), str(result[1])
        return None, None

    # ------------------------------------------------------------------
    # Postmortem methods (council post-trade analysis)
    # ------------------------------------------------------------------

    def insert_postmortem(self, postmortem: Dict) -> None:
        """Record a council postmortem after trade exit."""
        import json
        with self._lock:
            conn = self._get_conn()
            conn.execute("""
                INSERT INTO postmortems
                (id, council_decision_id, symbol, direction, confidence,
                 entry_price, exit_price, pnl, agent_votes,
                 blackboard_snapshot, critic_analysis, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [
                postmortem["id"],
                postmortem.get("council_decision_id", ""),
                postmortem["symbol"],
                postmortem.get("direction", ""),
                postmortem.get("confidence", 0.0),
                postmortem.get("entry_price", 0.0),
                postmortem.get("exit_price", 0.0),
                postmortem.get("pnl", 0.0),
                json.dumps(postmortem.get("agent_votes", []), default=str),
                json.dumps(postmortem.get("blackboard_snapshot", {}), default=str),
                postmortem.get("critic_analysis", ""),
            ])

    def get_postmortems(self, symbol: Optional[str] = None, limit: int = 50) -> pd.DataFrame:
        """Fetch postmortems, optionally filtered by symbol."""
        with self._lock:
            conn = self._get_conn()
            if symbol:
                return conn.execute(
                    "SELECT * FROM postmortems WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
                    [symbol, limit],
                ).fetchdf()
            return conn.execute(
                "SELECT * FROM postmortems ORDER BY created_at DESC LIMIT ?",
                [limit],
            ).fetchdf()

    def get_postmortem_count(self) -> int:
        """Count total postmortems."""
        with self._lock:
            conn = self._get_conn()
            result = conn.execute("SELECT COUNT(*) FROM postmortems").fetchone()
        return result[0] if result else 0

    def health_check(self) -> Dict:
        """Return storage health metrics."""
        with self._lock:
            conn = self._get_conn()
            tables = {
                "ohlcv_rows": "daily_ohlcv",
                "symbol_registry_rows": "symbol_registry",
                "indicator_rows": "technical_indicators",
                "flow_rows": "options_flow",
                "macro_rows": "macro_data",
                "trade_outcomes": "trade_outcomes",
                "feature_rows": "features",
                "model_eval_rows": "model_evals",
                "postmortem_rows": "postmortems",
            }
            counts = {}
            total = 0
            for key, table in tables.items():
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                counts[key] = count
                total += count
        return {
            "db_path": self._db_path,
            **counts,
            "total_tables": len(tables),
            "total_rows": total,
            "symbols": self.get_symbol_count(),
            "date_range": self.get_date_range(),
        }


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------
duckdb_store = DuckDBStorage()
