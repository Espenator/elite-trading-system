"""ExpectedMoveService — options-derived price levels for reversal detection.

Uses options data (implied volatility, expected moves) to calculate
key price levels where reversals are statistically likely. Inspired by
FOM (Figuring Out Money) expected move analysis.

Key Concepts:
  - Weekly Expected Move: The range the market is pricing via options
  - When price reaches the expected move boundary, it tends to reverse
  - Gamma exposure levels create "walls" that pin or repel price
  - Put/call walls define magnetic and repulsive zones

The system:
  1. Calculates expected moves from ATR and IV data
  2. Tracks where price is relative to expected move boundaries
  3. Triggers swarms when price approaches/reaches reversal zones
  4. Integrates Discord FOM data when available
"""
import asyncio
import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Symbols to calculate expected moves for
EXPECTED_MOVE_SYMBOLS = [
    "SPY", "QQQ", "IWM", "DIA",
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
    "XLK", "XLF", "XLE", "XLV",
    "GLD", "TLT", "USO",
]


@dataclass
class ExpectedMoveLevel:
    """Expected move levels for a symbol."""
    symbol: str
    current_price: float
    # Weekly expected move
    expected_move_pct: float      # e.g., 0.025 = 2.5%
    expected_move_dollars: float  # Dollar amount
    upper_boundary: float         # Price at upper EM
    lower_boundary: float         # Price at lower EM
    # Where are we relative to EM?
    pct_of_expected_move: float   # -1 to +1 (-1 = at lower, +1 = at upper)
    at_boundary: bool             # True if within 10% of a boundary
    reversal_zone: str            # "upper_reversal", "lower_reversal", "normal"
    # Confidence and signals
    reversal_probability: float
    trade_signal: str             # "buy", "sell", "none"
    reasoning: str
    # Data source
    source: str                   # "calculated", "fom_discord", "options_api"
    calculated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "current_price": round(self.current_price, 2),
            "expected_move_pct": round(self.expected_move_pct * 100, 2),
            "expected_move_dollars": round(self.expected_move_dollars, 2),
            "upper_boundary": round(self.upper_boundary, 2),
            "lower_boundary": round(self.lower_boundary, 2),
            "pct_of_expected_move": round(self.pct_of_expected_move, 3),
            "at_boundary": self.at_boundary,
            "reversal_zone": self.reversal_zone,
            "reversal_probability": round(self.reversal_probability, 2),
            "trade_signal": self.trade_signal,
            "reasoning": self.reasoning,
            "source": self.source,
            "calculated_at": self.calculated_at,
        }


class ExpectedMoveService:
    """Calculates and monitors expected move levels for reversal trading."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._levels: Dict[str, ExpectedMoveLevel] = {}
        self._fom_levels: Dict[str, Dict] = {}  # FOM Discord override levels
        self._scan_interval = 300  # 5 min
        self._stats = {
            "scans": 0,
            "reversals_detected": 0,
            "swarms_triggered": 0,
        }

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())
        logger.info("ExpectedMoveService started (%d symbols)", len(EXPECTED_MOVE_SYMBOLS))

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def set_fom_levels(self, symbol: str, upper: float, lower: float, source: str = "fom_discord"):
        """Set expected move levels from FOM Discord or user input.

        This overrides the calculated levels with real options-derived data.
        """
        self._fom_levels[symbol.upper()] = {
            "upper": upper,
            "lower": lower,
            "source": source,
            "set_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("FOM levels set for %s: upper=%.2f, lower=%.2f", symbol, upper, lower)

    async def _scan_loop(self):
        await asyncio.sleep(45)
        while self._running:
            try:
                await self._calculate_all_levels()
                await self._check_reversal_zones()
                self._stats["scans"] += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("ExpectedMoveService error: %s", e)
            await asyncio.sleep(self._scan_interval)

    async def _calculate_all_levels(self):
        """Calculate expected move levels for all tracked symbols."""
        try:
            levels = await asyncio.to_thread(self._calculate_all_levels_sync)
            self._levels.update(levels)
        except Exception as e:
            logger.debug("EM scan error: %s", e)

    def _calculate_all_levels_sync(self):
        """Sync helper — runs in thread pool."""
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        results = {}

        for symbol in EXPECTED_MOVE_SYMBOLS:
            try:
                df = conn.execute("""
                    SELECT date, close, high, low, volume
                    FROM daily_ohlcv
                    WHERE symbol = ? AND date >= CURRENT_DATE - INTERVAL '30 days'
                    ORDER BY date
                """, [symbol]).fetchdf()

                if df.empty or len(df) < 10:
                    continue

                current_price = float(df["close"].iloc[-1])
                closes = df["close"].values.astype(float)

                atr_df = conn.execute("""
                    SELECT atr_14
                    FROM technical_indicators
                    WHERE symbol = ? AND atr_14 IS NOT NULL
                    ORDER BY date DESC
                    LIMIT 1
                """, [symbol]).fetchdf()

                atr = float(atr_df["atr_14"].iloc[0]) if not atr_df.empty else None

                level = self._calculate_expected_move(symbol, current_price, closes, atr)
                if level:
                    results[symbol] = level
            except Exception as e:
                logger.debug("EM calculation error for %s: %s", symbol, e)

        return results

    def _calculate_expected_move(
        self,
        symbol: str,
        current_price: float,
        closes: np.ndarray,
        atr: Optional[float],
    ) -> Optional[ExpectedMoveLevel]:
        """Calculate the weekly expected move for a symbol."""
        if current_price <= 0:
            return None

        # Check for FOM override levels
        fom = self._fom_levels.get(symbol)
        if fom:
            upper = fom["upper"]
            lower = fom["lower"]
            em_dollars = (upper - lower) / 2
            em_pct = em_dollars / current_price
            source = fom["source"]
        else:
            # Calculate from historical volatility + ATR
            returns = np.diff(closes) / closes[:-1]
            if len(returns) < 5:
                return None

            # Annualized volatility
            daily_vol = np.std(returns)
            # Weekly expected move ≈ daily_vol * sqrt(5) * price
            weekly_vol = daily_vol * math.sqrt(5)
            em_pct = weekly_vol
            em_dollars = em_pct * current_price

            # If ATR is available, blend it (ATR captures gaps better)
            if atr and atr > 0:
                atr_weekly = atr * math.sqrt(5)
                atr_pct = atr_weekly / current_price
                # Blend: 60% volatility, 40% ATR
                em_pct = em_pct * 0.6 + atr_pct * 0.4
                em_dollars = em_pct * current_price

            # Calculate Friday close for weekly reference
            upper = current_price + em_dollars
            lower = current_price - em_dollars
            source = "calculated"

        # Where is price relative to EM boundaries?
        if em_dollars > 0:
            midpoint = (upper + lower) / 2
            pct_of_em = (current_price - midpoint) / em_dollars
        else:
            pct_of_em = 0.0

        # Reversal zone detection
        boundary_threshold = 0.85  # Within 85% of expected move
        at_boundary = abs(pct_of_em) > boundary_threshold
        reversal_zone = "normal"
        trade_signal = "none"
        reversal_prob = 0.0
        reasoning = f"Price at {pct_of_em:.0%} of expected move range"

        if pct_of_em > boundary_threshold:
            reversal_zone = "upper_reversal"
            reversal_prob = min(0.80, 0.5 + (abs(pct_of_em) - boundary_threshold) * 2)
            trade_signal = "sell"
            reasoning = (
                f"{symbol} at upper expected move boundary "
                f"(${current_price:.2f} vs EM upper ${upper:.2f}). "
                f"High probability reversal zone ({reversal_prob:.0%})."
            )
        elif pct_of_em < -boundary_threshold:
            reversal_zone = "lower_reversal"
            reversal_prob = min(0.80, 0.5 + (abs(pct_of_em) - boundary_threshold) * 2)
            trade_signal = "buy"
            reasoning = (
                f"{symbol} at lower expected move boundary "
                f"(${current_price:.2f} vs EM lower ${lower:.2f}). "
                f"High probability reversal zone ({reversal_prob:.0%})."
            )

        return ExpectedMoveLevel(
            symbol=symbol,
            current_price=current_price,
            expected_move_pct=em_pct,
            expected_move_dollars=em_dollars,
            upper_boundary=upper,
            lower_boundary=lower,
            pct_of_expected_move=pct_of_em,
            at_boundary=at_boundary,
            reversal_zone=reversal_zone,
            reversal_probability=reversal_prob,
            trade_signal=trade_signal,
            reasoning=reasoning,
            source=source,
        )

    async def _check_reversal_zones(self):
        """Trigger swarms for symbols at expected move boundaries."""
        for symbol, level in self._levels.items():
            if level.at_boundary and level.trade_signal != "none":
                self._stats["reversals_detected"] += 1
                direction = "bullish" if level.trade_signal == "buy" else "bearish"

                await self._trigger_swarm(
                    symbols=[symbol],
                    direction=direction,
                    reasoning=(
                        f"EXPECTED MOVE REVERSAL: {level.reasoning} "
                        f"(source={level.source})"
                    ),
                    priority=2,
                    metadata={
                        "signal_type": "expected_move",
                        "reversal_zone": level.reversal_zone,
                        "pct_of_em": level.pct_of_expected_move,
                        "reversal_probability": level.reversal_probability,
                        "upper_boundary": level.upper_boundary,
                        "lower_boundary": level.lower_boundary,
                    },
                )

    async def _trigger_swarm(self, symbols, direction, reasoning, priority=2, metadata=None):
        self._stats["swarms_triggered"] += 1
        if self._bus:
            await self._bus.publish("swarm.idea", {
                "source": "expected_move",
                "symbols": symbols,
                "direction": direction,
                "reasoning": reasoning,
                "priority": priority,
                "metadata": metadata or {},
            })

    # ──────────────────────────────────────────────────────────────────────
    # Status / API
    # ──────────────────────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "symbols_tracked": len(EXPECTED_MOVE_SYMBOLS),
            "levels_calculated": len(self._levels),
            "fom_overrides": len(self._fom_levels),
            "stats": dict(self._stats),
        }

    def get_levels(self, symbol: str = None) -> List[Dict]:
        if symbol:
            level = self._levels.get(symbol.upper())
            return [level.to_dict()] if level else []
        return [l.to_dict() for l in self._levels.values()]

    def get_reversal_zones(self) -> List[Dict]:
        """Get only symbols currently at reversal zones."""
        return [l.to_dict() for l in self._levels.values() if l.at_boundary]


# Module-level singleton
_service: Optional[ExpectedMoveService] = None

def get_expected_move_service() -> ExpectedMoveService:
    global _service
    if _service is None:
        _service = ExpectedMoveService()
    return _service
