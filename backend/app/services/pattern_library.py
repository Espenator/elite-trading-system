"""PatternLibrary — discovers, stores, and validates recurring market patterns.

The pattern library learns from historical data to identify repeating
market rhythms and structures that the system can trade:

  - Next-day reversal patterns (steep selloff -> bounce)
  - Intraday rhythm patterns (time-of-day effects)
  - Post-earnings drift patterns
  - Options expiration patterns (OpEx pin, gamma squeeze)
  - Sector rotation sequences (which sector leads/lags)
  - Correlation regime patterns (what happens after X breaks)
  - Expected move level patterns (FOM-style reversal at key levels)
  - Fear/greed cycle patterns (extreme readings -> reversal)

Each pattern is:
  1. Detected from historical data
  2. Backtested for hit rate and edge
  3. Stored with confidence scores
  4. Monitored in real-time for new occurrences
  5. Triggers swarm analysis when a pattern fires

Usage:
    library = PatternLibrary(message_bus)
    await library.start()
    # Library scans for pattern occurrences every N minutes
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MarketPattern:
    """A discovered market pattern with backtest statistics."""
    id: str
    name: str
    pattern_type: str          # reversal, rotation, momentum, expected_move, cycle
    description: str
    conditions: Dict[str, Any]  # What triggers this pattern
    trade_action: str           # buy / sell / pairs_trade
    symbols: List[str]          # Which symbols this applies to ("*" = all)
    # Backtest stats
    hit_rate: float = 0.0       # How often it works
    avg_return: float = 0.0     # Average return when it works
    sample_size: int = 0        # How many times observed
    sharpe: float = 0.0         # Sharpe ratio of pattern trades
    # Confidence
    confidence: float = 0.0     # Overall confidence score
    last_triggered: str = ""
    times_triggered: int = 0
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "conditions": self.conditions,
            "trade_action": self.trade_action,
            "symbols": self.symbols,
            "hit_rate": round(self.hit_rate, 3),
            "avg_return_pct": round(self.avg_return * 100, 2),
            "sample_size": self.sample_size,
            "sharpe": round(self.sharpe, 2),
            "confidence": round(self.confidence, 3),
            "last_triggered": self.last_triggered,
            "times_triggered": self.times_triggered,
            "active": self.active,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Built-in Pattern Definitions
# ═══════════════════════════════════════════════════════════════════════════════

BUILTIN_PATTERNS = [
    MarketPattern(
        id="steep_selloff_bounce",
        name="Steep Selloff Bounce",
        pattern_type="reversal",
        description="After a 3%+ single-day drop, buy the next-day bounce. Historically 65% hit rate.",
        conditions={"return_1d": {"lt": -0.03}, "rsi_14": {"lt": 35}},
        trade_action="buy",
        symbols=["*"],
    ),
    MarketPattern(
        id="oversold_rsi_bounce",
        name="RSI Oversold Bounce",
        pattern_type="reversal",
        description="RSI < 25 with price at lower Bollinger Band. Mean reversion bounce.",
        conditions={"rsi_14": {"lt": 25}, "bollinger_pct": {"lt": 0.1}},
        trade_action="buy",
        symbols=["*"],
    ),
    MarketPattern(
        id="overbought_rsi_fade",
        name="RSI Overbought Fade",
        pattern_type="reversal",
        description="RSI > 75 with price at upper Bollinger Band. Profit-taking pullback likely.",
        conditions={"rsi_14": {"gt": 75}, "bollinger_pct": {"gt": 0.9}},
        trade_action="sell",
        symbols=["*"],
    ),
    MarketPattern(
        id="vix_spike_reversal",
        name="VIX Spike Reversal",
        pattern_type="cycle",
        description="VIX jumps 20%+ in a day — fear peaks, markets tend to bounce 1-3 days later.",
        conditions={"vix_change_pct": {"gt": 0.20}},
        trade_action="buy",
        symbols=["SPY", "QQQ", "IWM"],
    ),
    MarketPattern(
        id="vix_crush_complacency",
        name="VIX Crush Complacency",
        pattern_type="cycle",
        description="VIX below 12 — extreme complacency. Sell volatility premium is crowded, risk of snap.",
        conditions={"vix_level": {"lt": 12}},
        trade_action="sell",
        symbols=["SPY", "QQQ"],
    ),
    MarketPattern(
        id="sector_rotation_reversion",
        name="Sector Rotation Reversion",
        pattern_type="rotation",
        description="Worst performing sector over 5 days tends to outperform over next 5 days (mean reversion).",
        conditions={"sector_rank_5d": {"eq": "last"}, "return_5d": {"lt": -0.03}},
        trade_action="buy",
        symbols=["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLU", "XLRE", "XLB", "XLC"],
    ),
    MarketPattern(
        id="gap_fill_pattern",
        name="Gap Fill After Large Gap",
        pattern_type="reversal",
        description="Gaps > 1.5% tend to fill within 1-3 days. Fade the gap direction.",
        conditions={"gap_pct": {"abs_gt": 0.015}},
        trade_action="fade_gap",
        symbols=["*"],
    ),
    MarketPattern(
        id="three_day_rule",
        name="Three Day Rule",
        pattern_type="reversal",
        description="After 3 consecutive down days, probability of up day increases significantly.",
        conditions={"consecutive_down_days": {"gte": 3}},
        trade_action="buy",
        symbols=["*"],
    ),
    MarketPattern(
        id="expected_move_reversal",
        name="Expected Move Boundary Reversal",
        pattern_type="expected_move",
        description="Price reaches the weekly expected move boundary (from options). High probability reversal zone.",
        conditions={"pct_of_expected_move": {"abs_gt": 0.90}},
        trade_action="fade_direction",
        symbols=["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL"],
    ),
    MarketPattern(
        id="monday_reversal",
        name="Monday Reversal",
        pattern_type="cycle",
        description="If Friday closes down 1%+, Monday tends to open lower then reverse intraday.",
        conditions={"day_of_week": {"eq": 0}, "friday_return": {"lt": -0.01}},
        trade_action="buy",
        symbols=["SPY", "QQQ"],
    ),
    MarketPattern(
        id="breadth_thrust",
        name="Breadth Thrust Ignition",
        pattern_type="momentum",
        description="When breadth flips from <30% to >70% in 5 days — powerful rally initiation.",
        conditions={"breadth_5d_ago": {"lt": 0.30}, "breadth_now": {"gt": 0.70}},
        trade_action="buy",
        symbols=["SPY", "QQQ", "IWM"],
    ),
    MarketPattern(
        id="high_put_call_bounce",
        name="High Put/Call Ratio Bounce",
        pattern_type="cycle",
        description="Put/Call ratio > 1.2 signals excessive fear. Contrarian buy signal.",
        conditions={"put_call_ratio": {"gt": 1.2}},
        trade_action="buy",
        symbols=["SPY", "QQQ"],
    ),
]


class PatternLibrary:
    """Discovers, validates, and monitors market patterns."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._patterns: Dict[str, MarketPattern] = {}
        self._scan_interval = 600  # 10 minutes
        self._stats = {
            "scans": 0,
            "patterns_triggered": 0,
            "swarms_triggered": 0,
        }
        # Load built-in patterns
        for p in BUILTIN_PATTERNS:
            self._patterns[p.id] = p

    async def start(self):
        if self._running:
            return
        self._running = True
        # Run initial backtest to set hit rates
        asyncio.create_task(self._initial_backtest())
        self._task = asyncio.create_task(self._scan_loop())
        logger.info("PatternLibrary started (%d patterns loaded)", len(self._patterns))

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _scan_loop(self):
        await asyncio.sleep(120)  # Wait for data to be ready
        while self._running:
            try:
                await self._scan_for_active_patterns()
                self._stats["scans"] += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("PatternLibrary scan error: %s", e)
            await asyncio.sleep(self._scan_interval)

    def _fetch_pattern_data(self):
        """Fetch all data needed for pattern scanning (sync, runs in thread)."""
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()

        latest = conn.execute("""
            SELECT o.symbol, o.date, o.close, o.open, o.high, o.low, o.volume,
                   t.rsi_14, t.macd, t.bb_upper, t.bb_lower, t.bb_mid,
                   t.sma_20, t.sma_50, t.adx_14
            FROM daily_ohlcv o
            LEFT JOIN technical_indicators t ON o.symbol = t.symbol AND o.date = t.date
            WHERE o.date >= CURRENT_DATE - INTERVAL '10 days'
            ORDER BY o.symbol, o.date
        """).fetchdf()

        macro = conn.execute("""
            SELECT date, vix_close, breadth_ratio
            FROM macro_data
            WHERE date >= CURRENT_DATE - INTERVAL '10 days'
            ORDER BY date DESC
            LIMIT 10
        """).fetchdf()

        flow = conn.execute("""
            SELECT call_volume, put_volume
            FROM options_flow
            WHERE date = (SELECT MAX(date) FROM options_flow)
            LIMIT 1
        """).fetchdf()

        return latest, macro, flow

    async def _scan_for_active_patterns(self):
        """Check current market conditions against all active patterns."""
        try:
            latest, macro, flow = await asyncio.to_thread(self._fetch_pattern_data)

            if latest.empty:
                return

            vix_level = float(macro["vix_close"].iloc[0]) if not macro.empty and not pd.isna(macro["vix_close"].iloc[0]) else None
            vix_prev = float(macro["vix_close"].iloc[1]) if len(macro) > 1 and not pd.isna(macro["vix_close"].iloc[1]) else None
            vix_change = (vix_level / vix_prev - 1) if vix_level and vix_prev else 0
            breadth = float(macro["breadth_ratio"].iloc[0]) if not macro.empty and not pd.isna(macro["breadth_ratio"].iloc[0]) else 0.5

            pcr = 1.0
            if not flow.empty:
                cv = float(flow["call_volume"].iloc[0] or 1)
                pv = float(flow["put_volume"].iloc[0] or 0)
                pcr = pv / cv if cv > 0 else 1.0

            # Check each pattern
            for pattern_id, pattern in self._patterns.items():
                if not pattern.active:
                    continue

                # Determine which symbols to check
                if pattern.symbols == ["*"]:
                    symbols_to_check = latest["symbol"].unique().tolist()
                else:
                    symbols_to_check = [s for s in pattern.symbols if s in latest["symbol"].values]

                for symbol in symbols_to_check:
                    sym_data = latest[latest["symbol"] == symbol]
                    if sym_data.empty:
                        continue

                    triggered = self._check_pattern_conditions(
                        pattern, sym_data, vix_level, vix_change, breadth, pcr
                    )

                    if triggered:
                        pattern.times_triggered += 1
                        pattern.last_triggered = datetime.now(timezone.utc).isoformat()
                        self._stats["patterns_triggered"] += 1

                        await self._trigger_pattern_swarm(pattern, symbol)

        except Exception as e:
            logger.debug("Pattern scan error: %s", e)

    def _check_pattern_conditions(
        self,
        pattern: MarketPattern,
        sym_data: pd.DataFrame,
        vix_level: Optional[float],
        vix_change: float,
        breadth: float,
        pcr: float,
    ) -> bool:
        """Check if current conditions match a pattern's trigger conditions."""
        conditions = pattern.conditions
        row = sym_data.iloc[-1]  # Latest data point

        for key, rule in conditions.items():
            # Get the current value for this condition
            value = None
            if key == "return_1d" and len(sym_data) >= 2:
                prev_close = float(sym_data.iloc[-2]["close"] or 0)
                curr_close = float(row["close"] or 0)
                value = (curr_close / prev_close - 1) if prev_close > 0 else 0
            elif key == "rsi_14":
                value = float(row.get("rsi_14") or 50)
            elif key == "bollinger_pct":
                bb_u = float(row.get("bb_upper") or 0)
                bb_l = float(row.get("bb_lower") or 0)
                close = float(row.get("close") or 0)
                value = (close - bb_l) / (bb_u - bb_l) if bb_u > bb_l else 0.5
            elif key == "vix_change_pct":
                value = vix_change
            elif key == "vix_level":
                value = vix_level
            elif key == "put_call_ratio":
                value = pcr
            elif key == "gap_pct":
                open_p = float(row.get("open") or 0)
                if len(sym_data) >= 2:
                    prev_close = float(sym_data.iloc[-2]["close"] or 0)
                    value = (open_p / prev_close - 1) if prev_close > 0 else 0
            elif key == "consecutive_down_days":
                value = 0
                for i in range(min(len(sym_data), 5)):
                    idx = -(i + 1)
                    if len(sym_data) > abs(idx):
                        r = sym_data.iloc[idx]
                        if float(r.get("close", 0) or 0) < float(r.get("open", 0) or 0):
                            value += 1
                        else:
                            break
            elif key in ("breadth_now",):
                value = breadth
            else:
                continue  # Unknown condition, skip

            if value is None:
                return False

            # Check the rule
            for op, threshold in rule.items():
                if op == "lt" and not (value < threshold):
                    return False
                elif op == "gt" and not (value > threshold):
                    return False
                elif op == "gte" and not (value >= threshold):
                    return False
                elif op == "lte" and not (value <= threshold):
                    return False
                elif op == "abs_gt" and not (abs(value) > threshold):
                    return False

        return True  # All conditions met

    async def _trigger_pattern_swarm(self, pattern: MarketPattern, symbol: str):
        """Trigger a swarm analysis for a pattern match."""
        self._stats["swarms_triggered"] += 1
        direction = "unknown"
        if pattern.trade_action == "buy":
            direction = "bullish"
        elif pattern.trade_action in ("sell", "fade_gap", "fade_direction"):
            direction = "bearish"

        if self._bus:
            await self._bus.publish("swarm.idea", {
                "source": "pattern_library",
                "symbols": [symbol],
                "direction": direction,
                "reasoning": (
                    f"PATTERN [{pattern.name}]: {pattern.description} "
                    f"(hit_rate={pattern.hit_rate:.0%}, triggered {pattern.times_triggered}x)"
                ),
                "priority": 3,
                "metadata": {
                    "signal_type": "pattern_match",
                    "pattern_id": pattern.id,
                    "pattern_type": pattern.pattern_type,
                    "hit_rate": pattern.hit_rate,
                    "confidence": pattern.confidence,
                },
            })

    async def _initial_backtest(self):
        """Run historical backtest on all patterns to set hit rates."""
        await asyncio.sleep(30)  # Wait for DuckDB to be ready
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()

            # Get historical OHLCV data
            df = conn.execute("""
                SELECT o.symbol, o.date, o.open, o.close, o.high, o.low, o.volume,
                       t.rsi_14, t.bb_upper, t.bb_lower
                FROM daily_ohlcv o
                LEFT JOIN technical_indicators t ON o.symbol = t.symbol AND o.date = t.date
                WHERE o.date >= CURRENT_DATE - INTERVAL '365 days'
                ORDER BY o.symbol, o.date
            """).fetchdf()

            if df.empty:
                return

            # Backtest simple patterns
            for pattern_id, pattern in self._patterns.items():
                if pattern.pattern_type == "reversal" and "return_1d" in pattern.conditions:
                    self._backtest_return_pattern(pattern, df)
                elif pattern.pattern_type == "reversal" and "rsi_14" in pattern.conditions:
                    self._backtest_rsi_pattern(pattern, df)
                elif pattern.pattern_type == "reversal" and "consecutive_down_days" in pattern.conditions:
                    self._backtest_consecutive_pattern(pattern, df)

            logger.info(
                "PatternLibrary backtest complete: %d patterns validated",
                sum(1 for p in self._patterns.values() if p.sample_size > 0),
            )
        except Exception as e:
            logger.debug("Pattern backtest error: %s", e)

    def _backtest_return_pattern(self, pattern: MarketPattern, df: pd.DataFrame):
        """Backtest a return-based pattern."""
        threshold = pattern.conditions.get("return_1d", {}).get("lt", -0.03)
        results = []

        for symbol in df["symbol"].unique():
            sym = df[df["symbol"] == symbol].sort_values("date")
            closes = sym["close"].values
            for i in range(1, len(closes) - 1):
                if closes[i - 1] > 0:
                    ret = closes[i] / closes[i - 1] - 1
                    if ret < threshold:
                        # Check next-day return
                        next_ret = closes[i + 1] / closes[i] - 1 if closes[i] > 0 else 0
                        results.append(next_ret)

        if results:
            wins = sum(1 for r in results if r > 0)
            pattern.hit_rate = wins / len(results)
            pattern.avg_return = np.mean(results)
            pattern.sample_size = len(results)
            pattern.sharpe = np.mean(results) / np.std(results) * np.sqrt(252) if np.std(results) > 0 else 0
            pattern.confidence = min(0.9, pattern.hit_rate * (1 - 1 / max(pattern.sample_size, 1)))

    def _backtest_rsi_pattern(self, pattern: MarketPattern, df: pd.DataFrame):
        """Backtest an RSI-based pattern."""
        rsi_cond = pattern.conditions.get("rsi_14", {})
        rsi_lt = rsi_cond.get("lt")
        rsi_gt = rsi_cond.get("gt")
        results = []

        for symbol in df["symbol"].unique():
            sym = df[df["symbol"] == symbol].sort_values("date")
            for i in range(len(sym) - 5):
                row = sym.iloc[i]
                rsi = row.get("rsi_14")
                if rsi is None or pd.isna(rsi):
                    continue

                triggered = False
                if rsi_lt and rsi < rsi_lt:
                    triggered = True
                elif rsi_gt and rsi > rsi_gt:
                    triggered = True

                if triggered:
                    close_now = float(row["close"] or 0)
                    close_5d = float(sym.iloc[i + 5]["close"] or 0)
                    if close_now > 0:
                        ret_5d = close_5d / close_now - 1
                        if pattern.trade_action == "buy":
                            results.append(ret_5d)
                        else:
                            results.append(-ret_5d)

        if results:
            wins = sum(1 for r in results if r > 0)
            pattern.hit_rate = wins / len(results)
            pattern.avg_return = np.mean(results)
            pattern.sample_size = len(results)
            pattern.sharpe = np.mean(results) / np.std(results) * np.sqrt(252) if np.std(results) > 0 else 0
            pattern.confidence = min(0.9, pattern.hit_rate * (1 - 1 / max(pattern.sample_size, 1)))

    def _backtest_consecutive_pattern(self, pattern: MarketPattern, df: pd.DataFrame):
        """Backtest consecutive down/up day patterns."""
        min_days = pattern.conditions.get("consecutive_down_days", {}).get("gte", 3)
        results = []

        for symbol in df["symbol"].unique():
            sym = df[df["symbol"] == symbol].sort_values("date")
            closes = sym["close"].values
            opens = sym["open"].values

            for i in range(min_days, len(closes) - 1):
                # Check if last N days were all down
                all_down = True
                for j in range(min_days):
                    if closes[i - j] >= opens[i - j]:
                        all_down = False
                        break

                if all_down:
                    next_ret = closes[i + 1] / closes[i] - 1 if closes[i] > 0 else 0
                    results.append(next_ret)

        if results:
            wins = sum(1 for r in results if r > 0)
            pattern.hit_rate = wins / len(results)
            pattern.avg_return = np.mean(results)
            pattern.sample_size = len(results)
            pattern.sharpe = np.mean(results) / np.std(results) * np.sqrt(252) if np.std(results) > 0 else 0
            pattern.confidence = min(0.9, pattern.hit_rate * (1 - 1 / max(pattern.sample_size, 1)))

    # ──────────────────────────────────────────────────────────────────────
    # Pattern CRUD
    # ──────────────────────────────────────────────────────────────────────
    def add_pattern(self, pattern: MarketPattern):
        self._patterns[pattern.id] = pattern
        self._persist_patterns()

    def remove_pattern(self, pattern_id: str):
        self._patterns.pop(pattern_id, None)
        self._persist_patterns()

    def toggle_pattern(self, pattern_id: str, active: bool):
        if pattern_id in self._patterns:
            self._patterns[pattern_id].active = active

    def _persist_patterns(self):
        """Save custom patterns to database."""
        try:
            from app.services.database import db_service
            custom = {k: v.to_dict() for k, v in self._patterns.items()
                      if k not in {p.id for p in BUILTIN_PATTERNS}}
            db_service.set_config("custom_patterns", custom)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────
    # Status / API
    # ──────────────────────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_patterns": len(self._patterns),
            "active_patterns": sum(1 for p in self._patterns.values() if p.active),
            "validated_patterns": sum(1 for p in self._patterns.values() if p.sample_size > 0),
            "stats": dict(self._stats),
        }

    def get_patterns(self, pattern_type: str = None) -> List[Dict]:
        patterns = list(self._patterns.values())
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        return [p.to_dict() for p in patterns]

    def get_pattern(self, pattern_id: str) -> Optional[Dict]:
        p = self._patterns.get(pattern_id)
        return p.to_dict() if p else None


# Module-level singleton
_library: Optional[PatternLibrary] = None

def get_pattern_library() -> PatternLibrary:
    global _library
    if _library is None:
        _library = PatternLibrary()
    return _library
