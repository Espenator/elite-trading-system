"""
Performance API (DB-backed, no fake metrics)

This module computes performance metrics ONLY from real DB rows.
If no trade/execution data exists, endpoints return empty arrays and null metrics with a clear message.

DB: backend/data/trading_orders.db
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from fastapi import APIRouter

DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "trading_orders.db"

router = APIRouter()


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _list_tables(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return [r["name"] for r in rows] if rows else []


def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r[1] for r in rows] if rows else []


def _detect_trade_table(conn: sqlite3.Connection) -> Optional[Tuple[str, Dict[str, str]]]:
    """
    Try to find a table representing completed trades/executions with a realized PnL column.
    Returns (table_name, column_map).
    """
    candidates = _list_tables(conn)

    # Heuristics: prioritize obvious names
    preferred = [t for t in candidates if t.lower() in ("trades", "executions", "fills", "orders", "closed_trades")]
    fallback = [t for t in candidates if "trade" in t.lower() or "fill" in t.lower() or "exec" in t.lower()]
    scan = preferred + [t for t in fallback if t not in preferred] + [t for t in candidates if t not in preferred and t not in fallback]

    pnl_names = ["realized_pnl", "pnl", "profit", "realizedProfit", "net_pnl"]
    closed_time_names = ["closed_at", "exit_time", "filled_at", "completed_at", "timestamp", "updated_at"]
    symbol_names = ["symbol", "ticker"]
    side_names = ["side", "direction"]
    entry_names = ["entry", "entry_price", "avg_entry_price"]
    exit_names = ["exit", "exit_price", "avg_exit_price"]
    qty_names = ["qty", "quantity", "shares"]
    status_names = ["status", "state"]

    for table in scan:
        cols = _table_columns(conn, table)
        cols_l = {c.lower(): c for c in cols}

        pnl_col = next((cols_l.get(n.lower()) for n in pnl_names if n.lower() in cols_l), None)
        if not pnl_col:
            continue

        # Basic map with optional fields
        colmap: Dict[str, str] = {"pnl": pnl_col}
        for group, key in [
            (closed_time_names, "closed_at"),
            (symbol_names, "symbol"),
            (side_names, "side"),
            (entry_names, "entry"),
            (exit_names, "exit"),
            (qty_names, "qty"),
            (status_names, "status"),
        ]:
            found = next((cols_l.get(n.lower()) for n in group if n.lower() in cols_l), None)
            if found:
                colmap[key] = found

        return table, colmap

    return None


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


@router.get("")
def performance_root(limit_trades: int = 5000) -> Dict[str, Any]:
    """
    Dashboard-friendly combined performance: summary metrics + equity curve.
    GET /api/v1/performance returns this. Frontend expects portfolioValue, winRate, equityCurve, etc.
    """
    summary = performance_summary(limit_trades=limit_trades)
    equity_res = performance_equity(limit_trades=limit_trades)

    metrics = summary.get("metrics") or {}
    points = equity_res.get("points") or []
    # Chart expects { time, value }; use date or index
    equity_curve = [
        {"time": p.get("date") or str(p.get("index", i)), "value": p.get("equity", 0)}
        for i, p in enumerate(points)
    ]
    last_equity = points[-1]["equity"] if points else 0.0
    win_rate = metrics.get("winRate") if metrics.get("winRate") is not None else 0
    max_dd = metrics.get("maxDrawdown") if metrics.get("maxDrawdown") is not None else 0

    return {
        "hasData": summary.get("hasData", False),
        "message": summary.get("message", ""),
        "portfolioValue": last_equity,
        "totalValue": last_equity,
        "dailyPnL": None,
        "totalReturnPct": (metrics.get("netPnl") or 0) / max(abs(last_equity), 1) * 100 if last_equity else 0,
        "winRate": win_rate,
        "win_rate": win_rate,
        "sharpeRatio": 0,
        "sharpe": 0,
        "alpha": 0,
        "maxDrawdown": max_dd,
        "max_drawdown": max_dd,
        "equityCurve": equity_curve,
        "sectors": None,
        "lastUpdated": summary.get("lastUpdated"),
    }


def _iso_date_only(s: Any) -> Optional[str]:
    if s is None:
        return None
    st = str(s)
    # accept ISO strings or "YYYY-MM-DD ..."
    if len(st) >= 10:
        return st[:10]
    return None


@router.get("/health")
def performance_health() -> Dict[str, Any]:
    conn = _conn()
    try:
        tables = _list_tables(conn)
        detected = _detect_trade_table(conn)
        return {
            "dbPath": str(DB_PATH),
            "tables": tables,
            "tradeTableDetected": detected[0] if detected else None,
            "tradeTableColumns": detected[1] if detected else None,
        }
    finally:
        conn.close()


@router.get("/summary")
def performance_summary(limit_trades: int = 5000) -> Dict[str, Any]:
    """
    Returns realized performance metrics from the detected trade table.
    If no table/data exists, returns null metrics and a clear message.
    """
    conn = _conn()
    try:
        detected = _detect_trade_table(conn)
        if not detected:
            return {
                "hasData": False,
                "message": "No trade table with realized PnL found in DB yet.",
                "metrics": {
                    "totalTrades": 0,
                    "netPnl": None,
                    "winRate": None,
                    "avgWin": None,
                    "avgLoss": None,
                    "profitFactor": None,
                    "maxDrawdown": None,
                },
                "lastUpdated": None,
            }

        table, colmap = detected
        pnl_col = colmap["pnl"]
        closed_col = colmap.get("closed_at")

        query = f"SELECT {pnl_col} AS pnl" + (f", {closed_col} AS closed_at" if closed_col else "") + f" FROM {table}"
        rows = conn.execute(query).fetchmany(int(limit_trades))

        pnls: List[float] = []
        last_updated: Optional[str] = None

        for r in rows:
            p = _safe_float(r["pnl"])
            if p is None:
                continue
            pnls.append(p)
            if closed_col:
                d = r["closed_at"]
                if d:
                    last_updated = str(d)

        if not pnls:
            return {
                "hasData": False,
                "message": "Trade table exists, but no realized PnL rows found yet.",
                "metrics": {
                    "totalTrades": 0,
                    "netPnl": None,
                    "winRate": None,
                    "avgWin": None,
                    "avgLoss": None,
                    "profitFactor": None,
                    "maxDrawdown": None,
                },
                "lastUpdated": _iso_date_only(last_updated),
            }

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        net_pnl = float(sum(pnls))
        total = len(pnls)
        win_rate = float(len(wins) / total) if total > 0 else None
        avg_win = float(sum(wins) / len(wins)) if wins else None
        avg_loss = float(sum(losses) / len(losses)) if losses else None  # negative
        gross_win = float(sum(wins)) if wins else 0.0
        gross_loss = float(abs(sum(losses))) if losses else 0.0
        profit_factor = float(gross_win / gross_loss) if gross_loss > 0 else None

        # Max drawdown from cumulative equity curve (starting at 0)
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for p in pnls:
            equity += float(p)
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd

        return {
            "hasData": True,
            "message": "OK",
            "metrics": {
                "totalTrades": total,
                "netPnl": net_pnl,
                "winRate": win_rate,
                "avgWin": avg_win,
                "avgLoss": avg_loss,
                "profitFactor": profit_factor,
                "maxDrawdown": max_dd,
            },
            "lastUpdated": _iso_date_only(last_updated),
            "source": {"table": table, "pnlColumn": pnl_col},
        }
    finally:
        conn.close()


@router.get("/equity")
def performance_equity(limit_trades: int = 5000) -> Dict[str, Any]:
    """
    Equity curve computed from realized trade PnL in chronological order if possible.
    If no timestamp column is detected, it uses row order (truthfully noted).
    """
    conn = _conn()
    try:
        detected = _detect_trade_table(conn)
        if not detected:
            return {"hasData": False, "message": "No trade table detected.", "points": [], "note": None}

        table, colmap = detected
        pnl_col = colmap["pnl"]
        closed_col = colmap.get("closed_at")

        order_clause = ""
        note = None
        if closed_col:
            order_clause = f" ORDER BY {closed_col} ASC"
        else:
            note = "No timestamp column detected; equity curve uses table row order."

        rows = conn.execute(
            f"SELECT {pnl_col} AS pnl" + (f", {closed_col} AS closed_at" if closed_col else "") + f" FROM {table}{order_clause} LIMIT ?",
            (int(limit_trades),),
        ).fetchall()

        points: List[Dict[str, Any]] = []
        equity = 0.0

        for idx, r in enumerate(rows):
            p = _safe_float(r["pnl"])
            if p is None:
                continue
            equity += float(p)
            points.append(
                {
                    "index": idx,
                    "date": _iso_date_only(r["closed_at"]) if closed_col else None,
                    "pnl": float(p),
                    "equity": float(equity),
                }
            )

        if not points:
            return {"hasData": False, "message": "No realized PnL rows found.", "points": [], "note": note}

        return {"hasData": True, "message": "OK", "points": points, "note": note, "source": {"table": table}}
    finally:
        conn.close()


@router.get("/trades")
def performance_trades(limit: int = 200) -> Dict[str, Any]:
    """
    Recent trades (raw rows shaped into a stable response).
    Only returns fields that actually exist in the detected table.
    """
    conn = _conn()
    try:
        detected = _detect_trade_table(conn)
        if not detected:
            return {"hasData": False, "message": "No trade table detected.", "trades": []}

        table, colmap = detected

        cols = []
        for k in ["symbol", "side", "qty", "entry", "exit", "pnl", "closed_at", "status"]:
            if k in colmap:
                cols.append(f"{colmap[k]} AS {k}")

        if not cols:
            # should not happen because pnl exists, but keep safe
            cols = [f"{colmap['pnl']} AS pnl"]

        order_clause = ""
        if "closed_at" in colmap:
            order_clause = f" ORDER BY {colmap['closed_at']} DESC"

        rows = conn.execute(
            f"SELECT {', '.join(cols)} FROM {table}{order_clause} LIMIT ?",
            (int(limit),),
        ).fetchall()

        trades: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            # Normalize a bit
            if "symbol" in d and d["symbol"] is not None:
                d["symbol"] = str(d["symbol"]).upper()
            if "pnl" in d:
                d["pnl"] = _safe_float(d["pnl"])
            if "qty" in d:
                d["qty"] = _safe_float(d["qty"])
            if "entry" in d:
                d["entry"] = _safe_float(d["entry"])
            if "exit" in d:
                d["exit"] = _safe_float(d["exit"])
            if "closed_at" in d and d["closed_at"] is not None:
                d["closed_at"] = str(d["closed_at"])
            trades.append(d)

        if not trades:
            return {"hasData": False, "message": "Trade table exists but has no rows.", "trades": [], "source": {"table": table}}

        return {"hasData": True, "message": "OK", "trades": trades, "source": {"table": table}}
    finally:
        conn.close()


# -----------------------------------------------------------------
# Risk Metrics: computed from real trade data
# -----------------------------------------------------------------



@router.get("/risk-metrics")
def risk_metrics() -> Dict[str, Any]:
    """
    Compute portfolio risk metrics from actual trade history:
    - Sharpe ratio, Sortino ratio, Calmar ratio
    - Max drawdown (% and duration)
    - Win rate, profit factor, avg R-multiple
    - Kelly optimal fraction from realized stats
    """
    conn = _conn()
    try:
        detected = _detect_trade_table(conn)
        if not detected:
            return {"hasData": False, "message": "No trade table found"}
        table, colmap = detected

        pnl_col = colmap.get("pnl")
        if not pnl_col:
            return {"hasData": False, "message": "No PnL column found"}

        rows = conn.execute(
            f"SELECT {pnl_col} AS pnl FROM {table} WHERE {pnl_col} IS NOT NULL"
        ).fetchall()
        if not rows:
            return {"hasData": False, "message": "No trades with PnL"}

        pnls = [_safe_float(r["pnl"]) for r in rows]
        pnls = [p for p in pnls if p is not None]
        if not pnls:
            return {"hasData": False, "message": "No valid PnL values"}

        arr = np.array(pnls)
        wins = arr[arr > 0]
        losses = arr[arr < 0]

        win_rate = len(wins) / len(arr) if len(arr) > 0 else 0
        avg_win = float(np.mean(wins)) if len(wins) > 0 else 0
        avg_loss = float(np.mean(np.abs(losses))) if len(losses) > 0 else 0
        profit_factor = (
            float(np.sum(wins) / np.sum(np.abs(losses)))
            if len(losses) > 0 and np.sum(np.abs(losses)) > 0
            else float("inf") if len(wins) > 0
            else 0
        )

        # Sharpe (annualized, assuming daily)
        mean_r = float(np.mean(arr))
        std_r = float(np.std(arr))
        sharpe = (mean_r / std_r * np.sqrt(252)) if std_r > 0 else 0

        # Sortino (downside deviation)
        downside = arr[arr < 0]
        down_std = float(np.std(downside)) if len(downside) > 0 else 0
        sortino = (mean_r / down_std * np.sqrt(252)) if down_std > 0 else 0

        # Max drawdown
        cumulative = np.cumsum(arr)
        peak = np.maximum.accumulate(cumulative)
        drawdown = peak - cumulative
        max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0
        max_dd_pct = (max_dd / float(np.max(peak))) * 100 if np.max(peak) > 0 else 0

        # Calmar
        total_return = float(np.sum(arr))
        calmar = (total_return / max_dd) if max_dd > 0 else 0

        # Kelly from realized stats
        b = avg_win / avg_loss if avg_loss > 0 else 0
        kelly_edge = win_rate * b - (1 - win_rate) if b > 0 else 0
        kelly_fraction = kelly_edge / b if b > 0 and kelly_edge > 0 else 0

        return {
            "hasData": True,
            "total_trades": len(arr),
            "win_rate": round(win_rate, 4),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 3),
            "sharpe": round(float(sharpe), 3),
            "sortino": round(float(sortino), 3),
            "calmar": round(float(calmar), 3),
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_pct": round(float(max_dd_pct), 2),
            "total_pnl": round(total_return, 2),
            "mean_pnl": round(mean_r, 2),
            "kelly_edge": round(kelly_edge, 4),
            "kelly_optimal_fraction": round(kelly_fraction, 4),
            "kelly_half_fraction": round(kelly_fraction * 0.5, 4),
                    "risk_reward_ratio": round(avg_win / avg_loss, 2) if avg_loss > 0 else 0,
        "expectancy": round(win_rate * avg_win - (1 - win_rate) * avg_loss, 4),
        "trading_grade": "A" if sharpe > 2 else "B" if sharpe > 1 else "C" if sharpe > 0.5 else "D",
        }
    finally:
        conn.close()
