"""
OpenClaw Bridge Database Service
Raw sqlite3 — matches DatabaseService pattern in database.py
Tables: openclaw_ingests, openclaw_signals
DB:     backend/data/trading_orders.db  (same file as orders)
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "trading_orders.db"


class OpenClawDBService:
    """Persists OpenClaw bridge ingests + signals to SQLite."""

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()      # one conn per thread
        self._init_tables()

    # -- connection (thread-safe) ---------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(DB_PATH))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    # -- schema ---------------------------------------------------------------

    def _init_tables(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS openclaw_ingests (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id              TEXT    NOT NULL UNIQUE,
                received_at         TEXT    NOT NULL,
                timestamp           TEXT    NOT NULL,
                regime_state        TEXT,
                regime_confidence   REAL,
                regime_source       TEXT,
                universe_json       TEXT,
                signal_count        INTEGER NOT NULL DEFAULT 0,
                payload_hash        TEXT
            );

            CREATE TABLE IF NOT EXISTS openclaw_signals (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ingest_id       INTEGER NOT NULL
                                    REFERENCES openclaw_ingests(id)
                                    ON DELETE CASCADE,
                run_id          TEXT    NOT NULL,
                symbol          TEXT    NOT NULL,
                direction       TEXT    NOT NULL,
                score           REAL    NOT NULL,
                subscores_json  TEXT,
                entry           REAL,
                stop            REAL,
                target          REAL,
                timeframe       TEXT,
                reasons_json    TEXT,
                raw_json        TEXT,
                received_at     TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_oc_signals_symbol
                ON openclaw_signals(symbol);
            CREATE INDEX IF NOT EXISTS idx_oc_signals_run
                ON openclaw_signals(run_id);
            CREATE INDEX IF NOT EXISTS idx_oc_signals_received
                ON openclaw_signals(received_at DESC);
            CREATE INDEX IF NOT EXISTS idx_oc_ingests_received
                ON openclaw_ingests(received_at DESC);
        """)
        conn.commit()

    # -- writes ---------------------------------------------------------------

    def insert_ingest(
        self,
        *,
        run_id: str,
        timestamp: str,
        regime: Optional[Dict] = None,
        universe: Optional[Dict] = None,
        signal_count: int = 0,
        payload_hash: Optional[str] = None,
    ) -> int:
        """Insert an ingest header row. Returns the new row id."""
        now = datetime.utcnow().isoformat() + "Z"
        conn = self._conn()
        cur = conn.execute(
            """INSERT INTO openclaw_ingests
                (run_id, received_at, timestamp,
                 regime_state, regime_confidence, regime_source,
                 universe_json, signal_count, payload_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                now,
                timestamp,
                regime.get("state") if regime else None,
                regime.get("confidence") if regime else None,
                regime.get("source") if regime else None,
                json.dumps(universe) if universe else None,
                signal_count,
                payload_hash,
            ),
        )
        conn.commit()
        return cur.lastrowid

    def insert_signals(
        self, ingest_id: int, run_id: str, signals: List[Dict[str, Any]]
    ) -> int:
        """Bulk-insert signal rows for one ingest. Returns count."""
        now = datetime.utcnow().isoformat() + "Z"
        conn = self._conn()
        rows = [
            (
                ingest_id,
                run_id,
                s["symbol"],
                s["direction"],
                s["score"],
                json.dumps(s.get("subscores")) if s.get("subscores") else None,
                s.get("entry"),
                s.get("stop"),
                s.get("target"),
                s.get("timeframe"),
                json.dumps(s.get("reasons")) if s.get("reasons") else None,
                json.dumps(s.get("raw")) if s.get("raw") else None,
                now,
            )
            for s in signals
        ]
        conn.executemany(
            """INSERT INTO openclaw_signals
                (ingest_id, run_id, symbol, direction, score,
                 subscores_json, entry, stop, target, timeframe,
                 reasons_json, raw_json, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        return len(rows)

    # -- reads ----------------------------------------------------------------

    def get_latest_ingest(self) -> Optional[Dict]:
        """Return the most recent ingest header, or None."""
        row = self._conn().execute(
            "SELECT * FROM openclaw_ingests ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def get_signals_for_ingest(self, ingest_id: int) -> List[Dict]:
        """All signals belonging to a given ingest, score desc."""
        rows = self._conn().execute(
            """SELECT * FROM openclaw_signals
               WHERE ingest_id = ?
               ORDER BY score DESC""",
            (ingest_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_latest_signals(self, limit: int = 50) -> List[Dict]:
        """Most recent signals across all ingests, score desc."""
        rows = self._conn().execute(
            """SELECT s.*, i.regime_state, i.regime_confidence
               FROM openclaw_signals s
               JOIN openclaw_ingests i ON s.ingest_id = i.id
               ORDER BY s.received_at DESC, s.score DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_signals_by_symbol(self, symbol: str, limit: int = 20) -> List[Dict]:
        """Historical signals for one ticker."""
        rows = self._conn().execute(
            """SELECT s.*, i.regime_state, i.regime_confidence
               FROM openclaw_signals s
               JOIN openclaw_ingests i ON s.ingest_id = i.id
               WHERE s.symbol = ?
               ORDER BY s.received_at DESC
               LIMIT ?""",
            (symbol.upper(), limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_ingest_history(self, limit: int = 20) -> List[Dict]:
        """Recent ingest summaries (for health/debug dashboard)."""
        rows = self._conn().execute(
            """SELECT id, run_id, received_at, timestamp,
                      regime_state, regime_confidence,
                      signal_count
               FROM openclaw_ingests
               ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def count_signals(self, since: Optional[str] = None) -> int:
        """Total signal rows, optionally since a datetime string."""
        if since:
            row = self._conn().execute(
                "SELECT COUNT(*) FROM openclaw_signals WHERE received_at >= ?",
                (since,),
            ).fetchone()
        else:
            row = self._conn().execute(
                "SELECT COUNT(*) FROM openclaw_signals"
            ).fetchone()
        return row[0] if row else 0


# -- global instance (matches database.py pattern) ----------------------------

openclaw_db = OpenClawDBService()
