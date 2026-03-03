"""SQLite database logger for OpenClaw.
Drop-in replacement for sheets_logger.py.
Logs all signals, trades, veto/confirms, and daily journals to local SQLite.
"""
import sqlite3
import os
import logging
from datetime import datetime
from pathlib import Path
from config import BASE_DIR

logger = logging.getLogger(__name__)

# Database path — store in data/ alongside other OpenClaw data
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = os.getenv("OPENCLAW_DB_PATH", str(DB_DIR / "openclaw_trades.db"))


class DBLogger:
    """SQLite trade logger — API-compatible replacement for SheetsLogger."""

    def __init__(self):
        self.db_path = DB_PATH
        self.connected = False
        self._connect()

    def _connect(self):
        """Initialize database and create tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # ── trades table (was "Trade Log" sheet) ──
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    action TEXT,
                    qty REAL,
                    entry REAL,
                    stop REAL,
                    target REAL,
                    status TEXT,
                    fill_price REAL,
                    pnl REAL,
                    pnl_pct REAL,
                    velez_score REAL,
                    regime TEXT,
                    source_channel TEXT,
                    order_id TEXT,
                    notes TEXT
                )
            """)

            # ── signals table (was "Signals" sheet) ──
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    action TEXT,
                    entry REAL,
                    stop REAL,
                    target REAL,
                    velez_score REAL,
                    quality TEXT,
                    source_channel TEXT,
                    source_user TEXT,
                    raw_text TEXT,
                    decision TEXT,
                    decision_time TEXT
                )
            """)

            # ── journal table (was "Daily Journal" sheet) ──
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    regime TEXT,
                    vix REAL,
                    trades_taken INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    gross_pnl REAL DEFAULT 0,
                    net_pnl REAL DEFAULT 0,
                    win_rate TEXT,
                    best_trade TEXT,
                    worst_trade TEXT,
                    notes TEXT
                )
            """)

            # ── audit_trail table (was "Audit Trail" sheet) ──
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    user TEXT DEFAULT 'system',
                    details TEXT,
                    channel TEXT
                )
            """)

            # ── indexes for common queries ──
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_timestamp
                ON trades(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_ticker
                ON trades(ticker)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_timestamp
                ON signals(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_ticker
                ON signals(ticker)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_date
                ON journal(date)
            """)

            conn.commit()
            conn.close()
            self.connected = True
            logger.info(f"Database logger connected: {self.db_path}")

        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            logger.warning("Trades will still execute but won't be logged to DB.")

    def _get_conn(self):
        """Get a new connection (sqlite3 connections are not thread-safe)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ──────────────────────────────────────────────
    # WRITE methods (match SheetsLogger API exactly)
    # ──────────────────────────────────────────────

    def log_signal(self, signal):
        """Log a parsed signal to the signals table."""
        if not self.connected:
            return
        try:
            conn = self._get_conn()
            conn.execute(
                """INSERT INTO signals
                   (timestamp, ticker, action, entry, stop, target,
                    velez_score, quality, source_channel, source_user,
                    raw_text, decision, decision_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    signal.get("timestamp", datetime.now().isoformat()),
                    signal.get("ticker", ""),
                    signal.get("action", ""),
                    signal.get("entry", None),
                    signal.get("stop", None),
                    signal.get("target", None),
                    signal.get("velez_score", None),
                    signal.get("quality", ""),
                    signal.get("source_channel", ""),
                    signal.get("source_user", ""),
                    (signal.get("raw_text", "") or "")[:500],
                    None,  # decision — filled on confirm/veto
                    None,  # decision_time
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log signal: {e}")

    def log_trade(self, trade):
        """Log an executed trade to the trades table."""
        if not self.connected:
            return
        try:
            conn = self._get_conn()
            conn.execute(
                """INSERT INTO trades
                   (timestamp, ticker, action, qty, entry, stop, target,
                    status, fill_price, pnl, pnl_pct, velez_score,
                    regime, source_channel, order_id, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trade.get("timestamp", datetime.now().isoformat()),
                    trade.get("ticker", ""),
                    trade.get("action", ""),
                    trade.get("qty", None),
                    trade.get("entry", None),
                    trade.get("stop", None),
                    trade.get("target", None),
                    trade.get("status", ""),
                    trade.get("fill_price", None),
                    trade.get("pnl", None),
                    trade.get("pnl_pct", None),
                    trade.get("velez_score", None),
                    trade.get("regime", ""),
                    trade.get("source_channel", ""),
                    trade.get("order_id", ""),
                    trade.get("notes", ""),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")

    def log_decision(self, signal_ticker, decision, timestamp=None):
        """Update the most recent signal row for a ticker with user decision."""
        if not self.connected:
            return
        try:
            conn = self._get_conn()
            # Find the most recent signal for this ticker
            row = conn.execute(
                "SELECT id FROM signals WHERE ticker = ? ORDER BY id DESC LIMIT 1",
                (signal_ticker,),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE signals SET decision = ?, decision_time = ? WHERE id = ?",
                    (decision, timestamp or datetime.now().isoformat(), row["id"]),
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")

    def log_audit(self, action, user="system", details="", channel=""):
        """Log an audit trail entry."""
        if not self.connected:
            return
        try:
            conn = self._get_conn()
            conn.execute(
                """INSERT INTO audit_trail (timestamp, action, user, details, channel)
                   VALUES (?, ?, ?, ?, ?)""",
                (datetime.now().isoformat(), action, user, details, channel),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

    def log_daily_journal(self, journal_data):
        """Log daily trading journal entry (upsert by date)."""
        if not self.connected:
            return
        try:
            conn = self._get_conn()
            date_val = journal_data.get("date", datetime.now().strftime("%Y-%m-%d"))
            conn.execute(
                """INSERT INTO journal
                   (date, regime, vix, trades_taken, wins, losses,
                    gross_pnl, net_pnl, win_rate, best_trade, worst_trade, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(date) DO UPDATE SET
                    regime=excluded.regime, vix=excluded.vix,
                    trades_taken=excluded.trades_taken, wins=excluded.wins,
                    losses=excluded.losses, gross_pnl=excluded.gross_pnl,
                    net_pnl=excluded.net_pnl, win_rate=excluded.win_rate,
                    best_trade=excluded.best_trade, worst_trade=excluded.worst_trade,
                    notes=excluded.notes""",
                (
                    date_val,
                    journal_data.get("regime", ""),
                    journal_data.get("vix", None),
                    journal_data.get("trades_taken", 0),
                    journal_data.get("wins", 0),
                    journal_data.get("losses", 0),
                    journal_data.get("gross_pnl", 0),
                    journal_data.get("net_pnl", 0),
                    journal_data.get("win_rate", ""),
                    journal_data.get("best_trade", ""),
                    journal_data.get("worst_trade", ""),
                    journal_data.get("notes", ""),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log journal: {e}")

    # ──────────────────────────────────────────────
    # READ methods (match SheetsLogger API exactly)
    # ──────────────────────────────────────────────

    def get_todays_trades(self):
        """Get all trades from today."""
        if not self.connected:
            return []
        try:
            conn = self._get_conn()
            today = datetime.now().strftime("%Y-%m-%d")
            rows = conn.execute(
                "SELECT * FROM trades WHERE timestamp LIKE ? ORDER BY id",
                (f"{today}%",),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_performance_summary(self, days=30):
        """Get performance summary for filled trades."""
        if not self.connected:
            return {}
        try:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = 'FILLED'"
            ).fetchall()
            conn.close()

            if not rows:
                return {"total_trades": 0}

            trades = [dict(r) for r in rows]
            wins = [t for t in trades if (t.get("pnl") or 0) > 0]
            losses = [t for t in trades if (t.get("pnl") or 0) < 0]
            total_pnl = sum(t.get("pnl") or 0 for t in trades)

            return {
                "total_trades": len(trades),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": (
                    f"{len(wins)/len(trades)*100:.1f}%"
                    if trades
                    else "0%"
                ),
                "total_pnl": round(total_pnl, 2),
                "avg_pnl": (
                    round(total_pnl / len(trades), 2)
                    if trades
                    else 0
                ),
            }
        except Exception:
            return {"error": "Could not retrieve performance data"}

    # ──────────────────────────────────────────────
    # EXTRA query helpers (not in SheetsLogger)
    # ──────────────────────────────────────────────

    def get_signals_by_ticker(self, ticker, limit=50):
        """Get recent signals for a specific ticker."""
        if not self.connected:
            return []
        try:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM signals WHERE ticker = ? ORDER BY id DESC LIMIT ?",
                (ticker, limit),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_journal_range(self, start_date, end_date):
        """Get journal entries for a date range."""
        if not self.connected:
            return []
        try:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM journal WHERE date BETWEEN ? AND ? ORDER BY date",
                (start_date, end_date),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_recent_audit(self, limit=100):
        """Get recent audit trail entries."""
        if not self.connected:
            return []
        try:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM audit_trail ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []


# ── Singleton (same pattern as sheets_logger.py) ──
db_logger = DBLogger()
