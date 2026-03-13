"""One-off script for Data Integrity Audit: query DuckDB and SQLite."""
import sqlite3
from pathlib import Path

def run_sqlite():
    backend = Path(__file__).resolve().parent.parent.parent / "backend"
    db_path = backend / "data" / "trading_orders.db"
    out = []
    if not db_path.exists():
        out.append(f"SQLite not found: {db_path}")
        return out
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    out.append("SQLite trading_orders.db tables: " + ", ".join(tables))
    for t in tables:
        try:
            n = conn.execute(f"SELECT count(*) FROM [{t}]").fetchone()[0]
            out.append(f"  {t}: count={n}")
        except Exception as ex:
            out.append(f"  {t}: error {ex}")
    conn.close()
    return out

def run_duckdb():
    import sys
    backend = Path(__file__).resolve().parent.parent.parent / "backend"
    sys.path.insert(0, str(backend))
    out = []
    try:
        from app.data.duckdb_storage import duckdb_store
        duckdb_store.get_thread_cursor()
        conn = duckdb_store._conn
        tables = [r[0] for r in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()]
        out.append("DuckDB analytics.duckdb tables: " + ", ".join(sorted(tables)))
        if "trade_outcomes" in tables:
            cols = [r[0] for r in conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name='trade_outcomes'").fetchall()]
            out.append("trade_outcomes columns: " + ", ".join(cols))
            row = conn.execute("SELECT count(*) FROM trade_outcomes").fetchone()
            out.append(f"trade_outcomes count: {row[0]}")
        if "daily_ohlcv" in tables:
            n = conn.execute("SELECT count(*) FROM daily_ohlcv").fetchone()[0]
            out.append(f"daily_ohlcv count: {n}")
    except Exception as e:
        out.append(f"DuckDB error: {e}")
    return out

if __name__ == "__main__":
    for line in run_sqlite():
        print(line)
    for line in run_duckdb():
        print(line)
