"""Memory Architecture — DuckDB DDL for episodic, semantic, and prediction memory.

Tables:
  - episodic_memory: Individual trade/decision episodes with embeddings
  - semantic_patterns: Learned market patterns (abstracted from episodes)
  - prediction_history: Council prediction tracking for Free Energy learning

Usage:
    from app.data.memory_schemas import init_memory_schemas
    init_memory_schemas()
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def init_memory_schemas(conn=None) -> None:
    """Create memory tables in DuckDB if they don't exist.

    Parameters
    ----------
    conn : DuckDB connection, optional
        If None, uses the global duckdb_store connection.
    """
    if conn is None:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_connection()

    # Episodic Memory — records individual decision episodes
    conn.execute("""
        CREATE TABLE IF NOT EXISTS episodic_memory (
            episode_id VARCHAR PRIMARY KEY,
            symbol VARCHAR NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            timeframe VARCHAR DEFAULT '1d',

            -- Context snapshot
            regime VARCHAR,
            signal_score DOUBLE,
            price DOUBLE,
            volume BIGINT,

            -- Council decision
            direction VARCHAR,
            confidence DOUBLE,
            votes_json VARCHAR,
            vetoed BOOLEAN DEFAULT FALSE,

            -- Outcome (filled after trade resolves)
            outcome VARCHAR,
            pnl DOUBLE,
            r_multiple DOUBLE,
            resolved_at TIMESTAMP,

            -- Embedding for similarity search (768-dim vector)
            embedding DOUBLE[768],

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Semantic Patterns — abstracted patterns learned from episodes
    conn.execute("""
        CREATE TABLE IF NOT EXISTS semantic_patterns (
            pattern_id VARCHAR PRIMARY KEY,
            pattern_type VARCHAR NOT NULL,
            description VARCHAR,

            -- Pattern features
            regime VARCHAR,
            direction VARCHAR,
            avg_confidence DOUBLE,
            occurrence_count INTEGER DEFAULT 1,
            win_rate DOUBLE,
            avg_r_multiple DOUBLE,

            -- Embedding for pattern matching
            embedding DOUBLE[768],

            -- Metadata
            last_seen TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Prediction History — tracks predictions for Free Energy Principle learning
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prediction_history (
            prediction_id VARCHAR PRIMARY KEY,
            symbol VARCHAR NOT NULL,
            timestamp TIMESTAMP NOT NULL,

            -- What was predicted
            predicted_direction VARCHAR NOT NULL,
            predicted_confidence DOUBLE NOT NULL,

            -- Per-agent predictions
            agent_predictions_json VARCHAR,

            -- Actual outcome (filled on resolution)
            actual_direction VARCHAR,
            actual_pnl DOUBLE,
            prediction_error DOUBLE,

            -- Free Energy metrics
            surprise DOUBLE,
            free_energy DOUBLE,

            -- Resolution
            resolved BOOLEAN DEFAULT FALSE,
            resolved_at TIMESTAMP,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes for memory queries
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_episodic_symbol_ts "
        "ON episodic_memory (symbol, timestamp)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_episodic_regime "
        "ON episodic_memory (regime)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_semantic_type "
        "ON semantic_patterns (pattern_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_predictions_symbol "
        "ON prediction_history (symbol, timestamp)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_predictions_unresolved "
        "ON prediction_history (resolved, symbol)"
    )

    logger.info("Memory schemas initialized (episodic_memory, semantic_patterns, prediction_history)")
