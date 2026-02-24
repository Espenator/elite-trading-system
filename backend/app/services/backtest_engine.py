"""Backtest Engine - Simulate OpenClaw scoring on historical data.

Uses sqlite3 data (openclaw_signals historical), Alpaca for fills.
Metrics: PnL, Sharpe, Winrate, MaxDD, Calmar.
DB:      backend/data/trading_orders.db  (same file as orders)
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

import numpy as np
import pandas as pd

DB_PATH = Path(__file__).parent.parent.parent / "data" / "trading_orders.db"


class BacktestEngine:
    """Run historical backtests on OpenClaw signal data."""

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    def run_backtest(
        self,
        symbol: Optional[str],
        start_date: str,
        end_date: str,
        strategy: str = "composite",
        initial_equity: float = 100_000.0,
        shares_per_trade: int = 100,
    ) -> Dict[str, Any]:
        """Full backtest: fetch historical signals/prices, simulate trades."""
        conn = self._conn()
        try:
            if symbol:
                signals = pd.read_sql_query(
                    """SELECT * FROM openclaw_signals
                       WHERE symbol = ? AND received_at BETWEEN ? AND ?
                       ORDER BY received_at""",
                    conn,
                    params=[symbol.upper(), start_date, end_date],
                )
            else:
                signals = pd.read_sql_query(
                    """SELECT * FROM openclaw_signals
                       WHERE received_at BETWEEN ? AND ?
                       ORDER BY received_at""",
                    conn,
                    params=[start_date, end_date],
                )
        finally:
            conn.close()

        if signals.empty:
            return {"error": "No signals found for the given parameters"}

        trades: List[Dict[str, Any]] = []
        equity = initial_equity

        for _, sig in signals.iterrows():
            entry_price = sig.get("entry") or self._get_price(
                sig["symbol"], sig["received_at"]
            )
            stop_price = sig.get("stop")
            target_price = sig.get("target")

            if not entry_price or not stop_price or not target_price:
                continue

            direction = 1 if sig["direction"] == "LONG" else -1
            risk = abs(entry_price - stop_price)
            if risk == 0:
                continue

            # R-multiple PnL simulation
            if direction > 0:
                pnl_r = (target_price - entry_price) / risk
            else:
                pnl_r = (entry_price - target_price) / risk

            pnl_dollars = pnl_r * risk * shares_per_trade
            equity += pnl_dollars

            trades.append(
                {
                    "symbol": sig["symbol"],
                    "direction": sig["direction"],
                    "entry": float(entry_price),
                    "stop": float(stop_price),
                    "target": float(target_price),
                    "pnl_r": round(float(pnl_r), 3),
                    "pnl_dollars": round(float(pnl_dollars), 2),
                    "equity": round(float(equity), 2),
                    "score": float(sig.get("score", 0)),
                    "received_at": str(sig["received_at"]),
                }
            )

        if not trades:
            return {"error": "No valid trades (missing entry/stop/target)"}

        df_trades = pd.DataFrame(trades)
        returns = df_trades["pnl_r"]

        # Metrics
        sharpe = (
            float(returns.mean() / returns.std() * np.sqrt(252))
            if returns.std() > 0
            else 0.0
        )
        winrate = float((returns > 0).mean())
        maxdd = float(
            (df_trades["equity"] / df_trades["equity"].cummax() - 1).min()
        )
        avg_r = float(returns.mean())
        total_pnl = float(df_trades["pnl_dollars"].sum())
        calmar = float(abs(total_pnl / maxdd)) if maxdd != 0 else 0.0

        return {
            "symbol": symbol or "ALL",
            "strategy": strategy,
            "period": f"{start_date} to {end_date}",
            "trades": len(trades),
            "winrate": round(winrate, 4),
            "sharpe": round(sharpe, 4),
            "maxdd": round(maxdd, 4),
            "calmar": round(calmar, 4),
            "avg_r": round(avg_r, 3),
            "total_pnl": round(total_pnl, 2),
            "initial_equity": initial_equity,
            "final_equity": round(equity, 2),
            "trades_detail": trades,
        }

    def _get_price(self, symbol: str, timestamp: str) -> Optional[float]:
        """Stub: query pricedata table or Alpaca historical."""
        # TODO: implement Alpaca historical bar lookup
        return None


# -- global instance (matches openclaw_db.py pattern) ----------------------
backtest_engine = BacktestEngine()
