"""

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
        use_kelly: bool = False,
        kelly_fraction: float = 0.5,  # Half-Kelly default
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

            # Kelly-aware position sizing
            if use_kelly:
                score = float(sig.get("score", 50))
                prob = min(0.95, max(0.3, 0.4 + (score / 100) * 0.5))
                avg_w = risk * 2.0  # Assume 2R target
                avg_l = risk
                b = avg_w / max(avg_l, 0.001)
                edge = prob * b - (1 - prob)
                kelly_pct = max(0, (edge / b) * kelly_fraction)
                position_value = equity * min(kelly_pct, 0.10)  # Cap 10%
                shares = max(1, int(position_value / max(entry_price, 0.01)))
            else:
                shares = shares_per_trade
            pnl_dollars = pnl_r * risk * shares
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
                    "shares": shares,
                    "kelly_sized": use_kelly,
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
        total_return_pct = (equity - initial_equity) / initial_equity
        # Calmar = percentage return / |maxDD| (both in percentage terms)
        calmar = float(total_return_pct / abs(maxdd)) if maxdd != 0 else 0.0

        # Enhanced metrics for profitability
        neg_returns = returns[returns < 0]
        sortino = (
            float(returns.mean() / neg_returns.std() * np.sqrt(252))
            if len(neg_returns) > 0 and neg_returns.std() > 0
            else 0.0
        )
        profit_factor = (
            float(returns[returns > 0].sum() / abs(returns[returns < 0].sum()))
            if len(neg_returns) > 0 and abs(returns[returns < 0].sum()) > 0
            else float('inf')
        )
        kelly_trades = [t for t in trades if t.get("kelly_sized")]
        kelly_efficiency = len(kelly_trades) / len(trades) if trades else 0
        avg_kelly_pnl = sum(t["pnl_dollars"] for t in kelly_trades) / len(kelly_trades) if kelly_trades else 0
        avg_non_kelly_pnl = (
            sum(t["pnl_dollars"] for t in trades if not t.get("kelly_sized")) /
            max(1, len(trades) - len(kelly_trades))
        ) if len(trades) > len(kelly_trades) else 0

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
            "sortino": round(sortino, 4),
            "profit_factor": round(profit_factor, 4) if profit_factor != float('inf') else "inf",
            "kelly_efficiency": round(kelly_efficiency, 4),
            "avg_kelly_pnl": round(avg_kelly_pnl, 2),
            "avg_non_kelly_pnl": round(avg_non_kelly_pnl, 2),
            "kelly_advantage": round(avg_kelly_pnl - avg_non_kelly_pnl, 2),
        }

    def _get_price(self, symbol: str, timestamp: str) -> Optional[float]:
        """Look up price from daily_ohlcv in the orders DB, fall back to OHLCV table."""
        conn = self._conn()
        try:
            # Try to get close price from daily_ohlcv on or before the timestamp date
            row = conn.execute(
                """SELECT close FROM daily_ohlcv
                   WHERE symbol = ? AND date <= date(?)
                   ORDER BY date DESC LIMIT 1""",
                [symbol.upper(), timestamp],
            ).fetchone()
            if row and row[0]:
                return float(row[0])
            # Fallback: try openclaw_signals entry price for the same symbol/time
            row = conn.execute(
                """SELECT entry FROM openclaw_signals
                   WHERE symbol = ? AND entry IS NOT NULL
                   ORDER BY ABS(julianday(received_at) - julianday(?)) LIMIT 1""",
                [symbol.upper(), timestamp],
            ).fetchone()
            if row and row[0]:
                return float(row[0])
            return None
        finally:
            conn.close()

    def monte_carlo_simulation(
        self,
        trades: list,
        num_simulations: int = 1000,
        initial_equity: float = 100000,
    ) -> Dict:
        """Run Monte Carlo simulation on trade results to estimate risk/reward distribution.
        Shuffles trade order to see range of possible equity curves."""
        import random
        if not trades or len(trades) < 5:
            return {"error": "Need at least 5 trades for Monte Carlo"}

        pnl_list = [t.get("pnl_dollars", t.get("pnl_pct", 0)) for t in trades]
        final_equities = []
        max_drawdowns = []
        sharpe_ratios = []

        for _ in range(num_simulations):
            shuffled = pnl_list.copy()
            random.shuffle(shuffled)
            equity = initial_equity
            peak = equity
            max_dd = 0.0
            returns = []
            for pnl in shuffled:
                equity += pnl
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)
                returns.append(pnl / max(1, equity - pnl))
            final_equities.append(equity)
            max_drawdowns.append(max_dd)
            if returns:
                avg_r = sum(returns) / len(returns)
                std_r = (sum((r - avg_r)**2 for r in returns) / len(returns)) ** 0.5
                sharpe_ratios.append(avg_r / std_r * (252**0.5) if std_r > 0 else 0)

        final_equities.sort()
        max_drawdowns.sort()
        n = len(final_equities)

        return {
            "simulations": num_simulations,
            "trades_count": len(trades),
            "equity_median": round(final_equities[n // 2], 2),
            "equity_p5": round(final_equities[int(n * 0.05)], 2),
            "equity_p25": round(final_equities[int(n * 0.25)], 2),
            "equity_p75": round(final_equities[int(n * 0.75)], 2),
            "equity_p95": round(final_equities[int(n * 0.95)], 2),
            "equity_worst": round(final_equities[0], 2),
            "equity_best": round(final_equities[-1], 2),
            "drawdown_median": round(max_drawdowns[n // 2], 4),
            "drawdown_p95": round(max_drawdowns[int(n * 0.95)], 4),
            "drawdown_worst": round(max_drawdowns[-1], 4),
            "sharpe_median": round(sharpe_ratios[n // 2], 4) if sharpe_ratios else 0,
            "risk_of_ruin": round(sum(1 for e in final_equities if e < initial_equity * 0.5) / n, 4),
            "probability_profit": round(sum(1 for e in final_equities if e > initial_equity) / n, 4),
        }


# -- global instance (matches openclaw_db.py pattern) ----------------------
backtest_engine = BacktestEngine()
