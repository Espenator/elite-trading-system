"""PositionManager — automated exit management for open positions.

Monitors open positions and applies intelligent exit rules:
  - Trailing stops (ATR-based, adapts to volatility)
  - Time-based exits (close stale positions)
  - Profit target scaling (partial exits at milestones)
  - Regime-based exits (tighten stops in deteriorating regimes)

Subscribes to market_data.bar for real-time price updates. Works with both
real Alpaca positions and shadow (paper) positions.

Architecture:
    market_data.bar event
        → PositionManager._on_bar()
            → update trailing stop for symbol
            → check exit conditions
            → if exit triggered: close via Alpaca or shadow close
            → publish position.closed event
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ManagedPosition:
    """A position with active exit management."""
    symbol: str
    side: str  # buy or sell
    entry_price: float
    qty: int
    order_id: str
    is_shadow: bool
    opened_at: float
    # Exit management
    initial_stop: float = 0.0
    trailing_stop: float = 0.0
    take_profit: float = 0.0
    highest_price: float = 0.0  # For trailing stop (long)
    lowest_price: float = 0.0   # For trailing stop (short)
    atr: float = 0.0
    # Partial exit tracking
    partial_exits: int = 0
    remaining_qty: int = 0

    def __post_init__(self):
        self.remaining_qty = self.qty
        self.highest_price = self.entry_price
        self.lowest_price = self.entry_price


class PositionManager:
    """Manages exits for open positions with trailing stops and time rules."""

    # Trailing stop: 2x ATR from high watermark
    ATR_TRAIL_MULT = 2.0
    # Time exit: close positions held > 5 days
    MAX_HOLD_SECONDS = 5 * 24 * 3600
    # Partial profit: take 50% at 2R, let rest ride
    PARTIAL_EXIT_R = 2.0
    PARTIAL_EXIT_PCT = 0.5
    # Regime tightening
    REGIME_STOP_MULT = {"GREEN": 1.0, "YELLOW": 0.75, "RED": 0.5}

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._positions: Dict[str, ManagedPosition] = {}  # symbol -> position
        self._regime = "UNKNOWN"
        self._stats = {
            "exits_trailing": 0,
            "exits_time": 0,
            "exits_target": 0,
            "exits_regime": 0,
            "partial_exits": 0,
            "total_managed": 0,
        }

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self._bus:
            await self._bus.subscribe("market_data.bar", self._on_bar)
            await self._bus.subscribe("order.submitted", self._on_order)
            await self._bus.subscribe("order.filled", self._on_fill)
        logger.info("PositionManager started — trailing stops + time exits active")

    async def stop(self) -> None:
        self._running = False
        if self._bus:
            await self._bus.unsubscribe("market_data.bar", self._on_bar)
        logger.info("PositionManager stopped — %d exits managed", sum(
            v for k, v in self._stats.items() if k.startswith("exits_")))

    async def _on_order(self, data: Dict[str, Any]) -> None:
        """Track new positions from order submissions."""
        symbol = data.get("symbol", "")
        if not symbol or symbol in self._positions:
            return

        entry_price = data.get("price", 0)
        if not entry_price:
            return

        stop_loss = data.get("stop_loss", 0) or 0
        take_profit = data.get("take_profit", 0) or 0
        is_shadow = data.get("source", "").endswith("_shadow")

        # Estimate ATR as 2% of price (will be updated with real data)
        atr = entry_price * 0.02

        pos = ManagedPosition(
            symbol=symbol,
            side=data.get("side", "buy"),
            entry_price=entry_price,
            qty=data.get("qty", 0),
            order_id=data.get("order_id", ""),
            is_shadow=is_shadow,
            opened_at=data.get("timestamp", time.time()),
            initial_stop=stop_loss,
            trailing_stop=stop_loss if stop_loss else entry_price - atr * self.ATR_TRAIL_MULT,
            take_profit=take_profit,
            atr=atr,
        )
        self._positions[symbol] = pos
        self._stats["total_managed"] += 1
        logger.debug("Managing position: %s %s @ $%.2f (trail=$%.2f)",
                      symbol, pos.side, entry_price, pos.trailing_stop)

    async def _on_fill(self, data: Dict[str, Any]) -> None:
        """Update entry price on fill."""
        symbol = data.get("symbol", "")
        fill_price = data.get("fill_price", 0)
        if symbol in self._positions and fill_price > 0:
            pos = self._positions[symbol]
            pos.entry_price = fill_price
            pos.highest_price = fill_price
            pos.lowest_price = fill_price
            # Recalculate trailing stop from actual fill
            if pos.side == "buy":
                pos.trailing_stop = fill_price - pos.atr * self.ATR_TRAIL_MULT
            else:
                pos.trailing_stop = fill_price + pos.atr * self.ATR_TRAIL_MULT

    async def _on_bar(self, data: Dict[str, Any]) -> None:
        """Process price update and check exit conditions."""
        symbol = data.get("symbol", "")
        if symbol not in self._positions:
            return

        pos = self._positions[symbol]
        current_price = float(data.get("close", 0))
        if current_price <= 0:
            return

        high = float(data.get("high", current_price))
        low = float(data.get("low", current_price))
        now = time.time()

        # Update ATR estimate from bar data
        bar_range = high - low
        if bar_range > 0:
            pos.atr = pos.atr * 0.9 + bar_range * 0.1  # EMA smoothing

        exit_reason = None
        exit_price = current_price

        if pos.side == "buy":
            # Update high watermark
            if high > pos.highest_price:
                pos.highest_price = high
                # Trail the stop up
                regime_mult = self.REGIME_STOP_MULT.get(self._regime, 1.0)
                new_trail = high - pos.atr * self.ATR_TRAIL_MULT * regime_mult
                if new_trail > pos.trailing_stop:
                    pos.trailing_stop = new_trail

            # Check trailing stop
            if low <= pos.trailing_stop:
                exit_reason = "trailing_stop"
                exit_price = pos.trailing_stop
                self._stats["exits_trailing"] += 1

            # Check take profit
            elif pos.take_profit and high >= pos.take_profit:
                exit_reason = "take_profit"
                exit_price = pos.take_profit
                self._stats["exits_target"] += 1

        else:  # short
            if low < pos.lowest_price:
                pos.lowest_price = low
                regime_mult = self.REGIME_STOP_MULT.get(self._regime, 1.0)
                new_trail = low + pos.atr * self.ATR_TRAIL_MULT * regime_mult
                if new_trail < pos.trailing_stop:
                    pos.trailing_stop = new_trail

            if high >= pos.trailing_stop:
                exit_reason = "trailing_stop"
                exit_price = pos.trailing_stop
                self._stats["exits_trailing"] += 1

            elif pos.take_profit and low <= pos.take_profit:
                exit_reason = "take_profit"
                exit_price = pos.take_profit
                self._stats["exits_target"] += 1

        # Time-based exit
        if not exit_reason and (now - pos.opened_at) > self.MAX_HOLD_SECONDS:
            exit_reason = "time_exit"
            exit_price = current_price
            self._stats["exits_time"] += 1

        # Partial exit at 2R (if not already done)
        if not exit_reason and pos.partial_exits == 0:
            risk = abs(pos.entry_price - pos.initial_stop) if pos.initial_stop else pos.atr * self.ATR_TRAIL_MULT
            if risk > 0:
                if pos.side == "buy":
                    current_r = (current_price - pos.entry_price) / risk
                else:
                    current_r = (pos.entry_price - current_price) / risk
                if current_r >= self.PARTIAL_EXIT_R:
                    await self._partial_exit(pos, current_price)

        if exit_reason:
            await self._close_position(pos, exit_price, exit_reason)

    async def _partial_exit(self, pos: ManagedPosition, price: float) -> None:
        """Take partial profits at milestone."""
        exit_qty = max(1, int(pos.remaining_qty * self.PARTIAL_EXIT_PCT))
        pos.remaining_qty -= exit_qty
        pos.partial_exits += 1
        self._stats["partial_exits"] += 1

        # Move stop to breakeven after partial
        pos.trailing_stop = max(pos.trailing_stop, pos.entry_price)

        logger.info(
            "Partial exit: %s sold %d/%d @ $%.2f (stop moved to breakeven $%.2f)",
            pos.symbol, exit_qty, pos.qty, price, pos.entry_price,
        )

        if self._bus:
            await self._bus.publish("position.partial_exit", {
                "symbol": pos.symbol,
                "qty_exited": exit_qty,
                "qty_remaining": pos.remaining_qty,
                "exit_price": price,
                "entry_price": pos.entry_price,
                "is_shadow": pos.is_shadow,
            })

        # Execute real partial exit if not shadow
        if not pos.is_shadow:
            await self._execute_close(pos.symbol, exit_qty, "sell" if pos.side == "buy" else "buy")

    async def _close_position(self, pos: ManagedPosition, price: float, reason: str) -> None:
        """Close position and publish event."""
        pnl = (price - pos.entry_price) * pos.remaining_qty if pos.side == "buy" else \
              (pos.entry_price - price) * pos.remaining_qty

        logger.info(
            "Position CLOSED: %s %s @ $%.2f → $%.2f PnL=$%.2f reason=%s",
            pos.symbol, pos.side, pos.entry_price, price, pnl, reason,
        )

        if self._bus:
            await self._bus.publish("position.closed", {
                "symbol": pos.symbol,
                "side": pos.side,
                "entry_price": pos.entry_price,
                "exit_price": price,
                "qty": pos.remaining_qty,
                "pnl": round(pnl, 2),
                "reason": reason,
                "hold_time_s": time.time() - pos.opened_at,
                "is_shadow": pos.is_shadow,
                "order_id": pos.order_id,
            })

        # Execute real close if not shadow
        if not pos.is_shadow:
            close_side = "sell" if pos.side == "buy" else "buy"
            await self._execute_close(pos.symbol, pos.remaining_qty, close_side)

        # Remove from managed positions
        self._positions.pop(pos.symbol, None)

    async def _execute_close(self, symbol: str, qty: int, side: str) -> None:
        """Submit close order to Alpaca."""
        try:
            from app.services.alpaca_service import alpaca_service
            await alpaca_service.create_order(
                symbol=symbol,
                qty=str(qty),
                side=side,
                type="market",
                time_in_force="day",
            )
        except Exception as e:
            logger.error("Failed to close %s: %s", symbol, e)

    def update_regime(self, regime: str) -> None:
        """Update market regime for stop tightening."""
        if regime != self._regime:
            logger.info("PositionManager regime: %s → %s", self._regime, regime)
            self._regime = regime

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "managed_positions": len(self._positions),
            "regime": self._regime,
            "stats": self._stats,
            "positions": {
                sym: {
                    "entry": p.entry_price,
                    "trailing_stop": round(p.trailing_stop, 2),
                    "highest": p.highest_price,
                    "atr": round(p.atr, 2),
                    "hold_time_min": round((time.time() - p.opened_at) / 60, 1),
                    "partial_exits": p.partial_exits,
                    "remaining_qty": p.remaining_qty,
                }
                for sym, p in self._positions.items()
            },
        }


# Module-level singleton
_manager: Optional[PositionManager] = None


def get_position_manager() -> PositionManager:
    global _manager
    if _manager is None:
        _manager = PositionManager()
    return _manager
