"""Shadow Trading Tracker — tracks shadow P&L alongside real performance.

Before any evolved strategy goes live, it should run in shadow mode —
generating signals but not executing. This tracker records shadow trades
and computes hypothetical P&L so you can compare before committing capital.

Integrates with:
    - OrderExecutor shadow mode (existing)
    - Council decisions (tracks what council WOULD have done)
    - Execution simulator (realistic slippage on shadow trades)

Usage:
    from app.council.shadow_tracker import get_shadow_tracker
    tracker = get_shadow_tracker()
    tracker.record_shadow_trade(decision, simulated_fill)
    comparison = tracker.get_comparison()
"""
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_SHADOW_TRADES = 1000


class ShadowTracker:
    """Track shadow (paper) trades and compare to live performance."""

    def __init__(self):
        self._shadow_trades: List[Dict[str, Any]] = []
        self._live_trades: List[Dict[str, Any]] = []
        self._shadow_equity_curve: List[Dict[str, float]] = []
        self._live_equity_curve: List[Dict[str, float]] = []
        self._shadow_pnl = 0.0
        self._live_pnl = 0.0

    def record_shadow_trade(
        self,
        symbol: str,
        direction: str,
        confidence: float,
        entry_price: float,
        simulated_fill_price: float,
        qty: int,
        council_decision_id: str = "",
        metadata: Dict[str, Any] = None,
    ):
        """Record a shadow (paper) trade from the council decision."""
        trade = {
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence,
            "entry_price": entry_price,
            "fill_price": simulated_fill_price,
            "qty": qty,
            "slippage_cost": abs(simulated_fill_price - entry_price) * qty,
            "council_decision_id": council_decision_id,
            "timestamp": time.time(),
            "status": "open",
            "exit_price": None,
            "pnl": None,
            "metadata": metadata or {},
        }
        self._shadow_trades.append(trade)
        if len(self._shadow_trades) > MAX_SHADOW_TRADES:
            self._shadow_trades = self._shadow_trades[-MAX_SHADOW_TRADES:]
        logger.info("Shadow trade recorded: %s %s %s @ $%.2f", direction, qty, symbol, simulated_fill_price)

    def close_shadow_trade(self, symbol: str, exit_price: float):
        """Close the most recent open shadow trade for a symbol."""
        for trade in reversed(self._shadow_trades):
            if trade["symbol"] == symbol and trade["status"] == "open":
                trade["exit_price"] = exit_price
                trade["status"] = "closed"
                if trade["direction"] == "buy":
                    trade["pnl"] = (exit_price - trade["fill_price"]) * trade["qty"]
                else:
                    trade["pnl"] = (trade["fill_price"] - exit_price) * trade["qty"]
                self._shadow_pnl += trade["pnl"]
                self._shadow_equity_curve.append({
                    "timestamp": time.time(),
                    "cumulative_pnl": self._shadow_pnl,
                })
                return trade
        return None

    def record_live_trade(
        self, symbol: str, direction: str, pnl: float,
        entry_price: float = 0, exit_price: float = 0,
    ):
        """Record a real live trade for comparison."""
        self._live_trades.append({
            "symbol": symbol,
            "direction": direction,
            "pnl": pnl,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "timestamp": time.time(),
        })
        self._live_pnl += pnl
        self._live_equity_curve.append({
            "timestamp": time.time(),
            "cumulative_pnl": self._live_pnl,
        })
        if len(self._live_trades) > MAX_SHADOW_TRADES:
            self._live_trades = self._live_trades[-MAX_SHADOW_TRADES:]

    def get_comparison(self) -> Dict[str, Any]:
        """Compare shadow vs live performance metrics."""
        shadow_closed = [t for t in self._shadow_trades if t["status"] == "closed"]
        shadow_wins = sum(1 for t in shadow_closed if (t.get("pnl") or 0) > 0)
        live_wins = sum(1 for t in self._live_trades if t.get("pnl", 0) > 0)

        return {
            "shadow": {
                "total_trades": len(shadow_closed),
                "open_trades": sum(1 for t in self._shadow_trades if t["status"] == "open"),
                "cumulative_pnl": round(self._shadow_pnl, 2),
                "win_rate": round(shadow_wins / max(len(shadow_closed), 1), 3),
                "avg_pnl": round(self._shadow_pnl / max(len(shadow_closed), 1), 2),
                "total_slippage": round(
                    sum(t.get("slippage_cost", 0) for t in shadow_closed), 2
                ),
            },
            "live": {
                "total_trades": len(self._live_trades),
                "cumulative_pnl": round(self._live_pnl, 2),
                "win_rate": round(live_wins / max(len(self._live_trades), 1), 3),
                "avg_pnl": round(self._live_pnl / max(len(self._live_trades), 1), 2),
            },
            "comparison": self._compute_comparison(shadow_closed),
        }

    def _compute_comparison(self, shadow_closed: List[Dict]) -> Dict[str, Any]:
        """Compute comparison metrics between shadow and live."""
        shadow_count = len(shadow_closed)
        live_count = len(self._live_trades)

        if shadow_count == 0 and live_count == 0:
            return {"status": "no_data", "recommendation": "Run more trades in both modes"}

        pnl_diff = self._shadow_pnl - self._live_pnl

        if shadow_count >= 20 and live_count >= 20:
            shadow_wr = sum(1 for t in shadow_closed if (t.get("pnl") or 0) > 0) / shadow_count
            live_wr = sum(1 for t in self._live_trades if t.get("pnl", 0) > 0) / live_count
            wr_diff = shadow_wr - live_wr

            if self._shadow_pnl > self._live_pnl * 1.2 and shadow_wr > live_wr:
                recommendation = "Shadow outperforming live — consider activating shadow strategy"
            elif self._live_pnl > self._shadow_pnl * 1.2:
                recommendation = "Live outperforming shadow — current strategy is better"
            else:
                recommendation = "Performance similar — more data needed for clear signal"
        else:
            wr_diff = 0
            recommendation = f"Need more trades (shadow={shadow_count}, live={live_count}, target=20 each)"

        return {
            "pnl_difference": round(pnl_diff, 2),
            "shadow_leading": self._shadow_pnl > self._live_pnl,
            "recommendation": recommendation,
            "sufficient_data": shadow_count >= 20 and live_count >= 20,
        }

    def get_shadow_equity_curve(self) -> List[Dict[str, float]]:
        return self._shadow_equity_curve[-200:]

    def get_live_equity_curve(self) -> List[Dict[str, float]]:
        return self._live_equity_curve[-200:]

    def get_recent_shadow_trades(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._shadow_trades[-limit:]

    def get_status(self) -> Dict[str, Any]:
        return {
            "shadow_trade_count": len(self._shadow_trades),
            "shadow_pnl": round(self._shadow_pnl, 2),
            "live_trade_count": len(self._live_trades),
            "live_pnl": round(self._live_pnl, 2),
            "open_shadow_positions": sum(1 for t in self._shadow_trades if t["status"] == "open"),
        }


# Singleton
_tracker: Optional[ShadowTracker] = None


def get_shadow_tracker() -> ShadowTracker:
    global _tracker
    if _tracker is None:
        _tracker = ShadowTracker()
    return _tracker
