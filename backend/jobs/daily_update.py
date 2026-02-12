"""
Daily data update: fetch Alpaca daily bars, build features and labels, upsert into DuckDB.
Run after market close (e.g. via cron or Task Scheduler).
Research doc: Phase 1 – Data & simple strategy.
"""
import sys
from pathlib import Path

# Ensure backend app is on path
BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from datetime import datetime, timedelta

# Default watchlist; later load from config or universe table
DEFAULT_WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "SPY"]


def run_daily_update(watchlist=None):
    watchlist = watchlist or DEFAULT_WATCHLIST
    from app.data.alpaca_data import get_daily_bars
    from app.data.features import build_features
    from app.data.labels import build_labels
    from app.data.storage import get_conn, init_schema

    today = datetime.utcnow().date()
    start = today - timedelta(days=365 * 5)
    end = today

    bars = get_daily_bars(watchlist, start, end)
    if bars.empty:
        print("No bars fetched (check Alpaca keys and data API access).")
        return
    feats = build_features(bars)
    labeled = build_labels(feats)
    # Select columns that match daily_features schema
    cols = ["symbol", "date", "close", "return_1d", "return_5d", "ma_10", "ma_20", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel", "fwd_ret_5d", "y_direction"]
    for c in cols:
        if c not in labeled.columns:
            labeled[c] = None
    df = labeled[cols].dropna(subset=["symbol", "date", "close"], how="all")
    if df.empty:
        print("No labeled rows to write.")
        return
    conn = get_conn()
    init_schema(conn)
    try:
        min_d, max_d = df["date"].min(), df["date"].max()
        conn.execute("DELETE FROM daily_features WHERE date >= ? AND date <= ?", [min_d, max_d])
        conn.register("_daily_df", df)
        conn.execute("INSERT INTO daily_features SELECT * FROM _daily_df")
    except Exception as e:
        print("Write failed:", e)
    finally:
        conn.close()
    print("Daily update done. Rows:", len(df))


if __name__ == "__main__":
    run_daily_update()
