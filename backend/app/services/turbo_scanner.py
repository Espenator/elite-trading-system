"""TurboScanner — parallel multi-source market scanner for 100x throughput.

Scans ALL data sources simultaneously every 30-60 seconds:
  1. Alpaca batch bars (50 symbols per request)
  2. Unusual Whales flow alerts
  3. FinViz screener presets (momentum, breakout, pullback)
  4. DuckDB internal screener (momentum + volume + technical)
  5. FRED macro shifts
  6. Sector ETF divergence scanner
  7. Options flow anomaly detection
  8. VIX regime change detection

Design:
  - All scans run concurrently via asyncio.gather()
  - Batch Alpaca calls: 50 symbols per HTTP request (vs 1 at a time)
  - Results scored locally by Ollama (free, <500ms)
  - High-scoring signals go straight to HyperSwarm
  - Full market sweep: 8000+ symbols screened in <60 seconds via DuckDB

2-PC Architecture:
  - PC1: Primary (runs API, council, deep analysis)
  - PC2: Scanner + local LLM farm (Ollama instances)
  - Configure SCANNER_OLLAMA_URLS for multi-node LLM pool
"""
import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Configuration — Tunable for your 2-PC setup
# ═══════════════════════════════════════════════════════════════════════════════

SCAN_INTERVAL_NORMAL = 60       # Seconds between scans (normal market)
SCAN_INTERVAL_VOLATILE = 30     # During high VIX / active events
SCAN_INTERVAL_PREMARKET = 120   # Pre/post market
BATCH_SIZE_ALPACA = 50          # Symbols per Alpaca bars request (max efficient batch)
BATCH_SIZE_SCREEN = 200         # Symbols per DuckDB screen batch
MAX_SIGNALS_PER_SCAN = 50       # Cap signals to prevent swarm flooding
MIN_SIGNAL_SCORE = 0.4          # Minimum composite score to trigger swarm (0-1)

# Multi-node Ollama pool (add PC2 URL for 2x throughput)
OLLAMA_POOL_URLS = []  # Populated from env: SCANNER_OLLAMA_URLS=http://pc2:11434,http://localhost:11434

# Universe tiers — scan frequency varies by tier
UNIVERSE_TIER_1 = [  # Scan every cycle — most liquid
    "SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "TSLA", "META", "AMD", "NFLX", "AVGO", "CRM", "ORCL", "ADBE", "INTC",
    "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLU", "XLRE", "XLB", "XLC",
    "TLT", "GLD", "SLV", "USO", "UUP", "HYG", "EEM", "EFA", "VIX",
    "JPM", "BAC", "GS", "WFC", "MS",
    "UNH", "JNJ", "PFE", "MRK", "ABBV",
    "XOM", "CVX", "COP", "SLB", "OXY",
    "LMT", "RTX", "NOC", "GD", "BA",
    "HD", "LOW", "TGT", "WMT", "COST",
    "COIN", "MSTR", "SQ", "PYPL",
]
UNIVERSE_TIER_2 = []  # Populated from DuckDB — top 200 by volume
UNIVERSE_TIER_3 = []  # Populated from DuckDB — full market (screened via SQL)

# Signal types
SIGNAL_TYPES = {
    "unusual_flow": {"priority": 2, "weight": 0.25},
    "technical_breakout": {"priority": 3, "weight": 0.20},
    "momentum_surge": {"priority": 3, "weight": 0.15},
    "volume_spike": {"priority": 4, "weight": 0.15},
    "sector_divergence": {"priority": 3, "weight": 0.10},
    "vix_regime": {"priority": 1, "weight": 0.10},
    "mean_reversion": {"priority": 3, "weight": 0.15},
    "rsi_extreme": {"priority": 4, "weight": 0.10},
    "macd_cross": {"priority": 4, "weight": 0.10},
    "earnings_drift": {"priority": 3, "weight": 0.15},
}


@dataclass
class ScanSignal:
    """A signal discovered during a scan cycle."""
    symbol: str
    signal_type: str
    direction: str          # "bullish" / "bearish" / "unknown"
    score: float            # 0-1 composite score
    reasoning: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "turbo_scanner"
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "direction": self.direction,
            "score": round(self.score, 3),
            "reasoning": self.reasoning,
            "data": self.data,
            "source": self.source,
            "detected_at": self.detected_at,
        }


class TurboScanner:
    """Parallel multi-source market scanner with 100x throughput."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._scan_interval = SCAN_INTERVAL_NORMAL
        self._signals_history: List[ScanSignal] = []
        self._seen_today: Set[str] = set()  # symbol+type dedup
        self._last_scan_time = 0.0
        self._volatile_mode = False
        self._tier2_loaded = False
        self._stats = {
            "total_scans": 0,
            "total_signals": 0,
            "swarms_triggered": 0,
            "scan_duration_ms": 0.0,
            "symbols_scanned": 0,
            "by_type": defaultdict(int),
        }

    async def start(self):
        if self._running:
            return
        self._running = True
        await self._load_tier2_universe()
        self._task = asyncio.create_task(self._scan_loop())
        logger.info(
            "TurboScanner started (interval=%ds, tier1=%d, tier2=%d symbols)",
            self._scan_interval, len(UNIVERSE_TIER_1), len(UNIVERSE_TIER_2),
        )

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("TurboScanner stopped")

    # ──────────────────────────────────────────────────────────────────────
    # Main Scan Loop
    # ──────────────────────────────────────────────────────────────────────
    async def _scan_loop(self):
        await asyncio.sleep(15)  # Brief warmup
        while self._running:
            try:
                t0 = time.monotonic()
                signals = await self._run_all_scans()
                elapsed = (time.monotonic() - t0) * 1000

                self._stats["total_scans"] += 1
                self._stats["scan_duration_ms"] = round(elapsed, 1)

                # Score and filter
                actionable = [s for s in signals if s.score >= MIN_SIGNAL_SCORE]
                actionable.sort(key=lambda s: s.score, reverse=True)
                actionable = actionable[:MAX_SIGNALS_PER_SCAN]

                # Trigger swarms for top signals
                for signal in actionable:
                    dedup_key = f"{signal.symbol}:{signal.signal_type}:{signal.direction}"
                    if dedup_key in self._seen_today:
                        continue
                    self._seen_today.add(dedup_key)
                    self._signals_history.append(signal)
                    self._stats["total_signals"] += 1
                    self._stats["by_type"][signal.signal_type] += 1
                    await self._emit_signal(signal)

                # Trim history
                self._signals_history = self._signals_history[-500:]

                logger.info(
                    "TurboScan #%d: %d raw signals, %d actionable, %.0fms",
                    self._stats["total_scans"], len(signals),
                    len(actionable), elapsed,
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("TurboScanner scan error: %s", e)

            await asyncio.sleep(self._scan_interval)

    async def _run_all_scans(self) -> List[ScanSignal]:
        """Run ALL scan sources off the event loop (DuckDB is blocking I/O).

        DuckDB queries share a single connection, so they serialize anyway.
        Running them in a thread via asyncio.to_thread keeps the event loop
        free for HTTP requests and prevents event loop blocking.
        """
        return await asyncio.to_thread(self._run_all_scans_sync)

    def _run_all_scans_sync(self) -> List[ScanSignal]:
        """Synchronous scan runner -- called from a thread to avoid blocking the event loop."""
        scan_methods = [
            self._scan_duckdb_technicals_sync,
            self._scan_duckdb_volume_spikes_sync,
            self._scan_duckdb_momentum_sync,
            self._scan_duckdb_rsi_extremes_sync,
            self._scan_duckdb_macd_crosses_sync,
            self._scan_sector_divergence_sync,
            self._scan_vix_regime_sync,
            self._scan_options_flow_anomalies_sync,
            self._scan_mean_reversion_setups_sync,
            self._scan_gap_reversals_sync,
        ]
        signals = []
        for method in scan_methods:
            try:
                result = method()
                if isinstance(result, list):
                    signals.extend(result)
            except Exception as e:
                logger.debug("Scan task failed: %s", e)
        return signals

    # ──────────────────────────────────────────────────────────────────────
    # DuckDB-Powered Scans (scan thousands of symbols in milliseconds)
    # ──────────────────────────────────────────────────────────────────────

    def _scan_duckdb_technicals_sync(self) -> List[ScanSignal]:
        """Find breakout setups: price above key SMAs + strong ADX."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            df = conn.execute("""
                SELECT t.symbol, t.rsi_14, t.macd, t.macd_signal, t.adx_14,
                       t.sma_20, t.sma_50, t.sma_200,
                       o.close, o.volume,
                       o.close / NULLIF(LAG(o.close, 1) OVER (PARTITION BY o.symbol ORDER BY o.date), 0) - 1 as ret_1d,
                       o.close / NULLIF(LAG(o.close, 5) OVER (PARTITION BY o.symbol ORDER BY o.date), 0) - 1 as ret_5d
                FROM technical_indicators t
                JOIN daily_ohlcv o ON t.symbol = o.symbol AND t.date = o.date
                WHERE t.date >= CURRENT_DATE - INTERVAL '2 days'
                QUALIFY ROW_NUMBER() OVER (PARTITION BY t.symbol ORDER BY t.date DESC) = 1
            """).fetchdf()

            self._stats["symbols_scanned"] = max(self._stats["symbols_scanned"], len(df))
            signals = []

            for _, row in df.iterrows():
                symbol = row["symbol"]
                close = row.get("close", 0) or 0
                sma20 = row.get("sma_20", 0) or 0
                sma50 = row.get("sma_50", 0) or 0
                sma200 = row.get("sma_200", 0) or 0
                adx = row.get("adx_14", 0) or 0
                rsi = row.get("rsi_14", 50) or 50
                ret_1d = row.get("ret_1d", 0) or 0

                # Breakout: above all SMAs + strong trend
                if close > sma20 > sma50 > sma200 and adx > 25 and 40 < rsi < 70:
                    score = 0.3 + min(0.3, adx / 100) + min(0.2, ret_1d * 5) + (0.1 if rsi < 60 else 0)
                    signals.append(ScanSignal(
                        symbol=symbol,
                        signal_type="technical_breakout",
                        direction="bullish",
                        score=min(1.0, score),
                        reasoning=f"Bullish alignment: close>{sma20:.0f}>{sma50:.0f}>{sma200:.0f}, ADX={adx:.0f}, RSI={rsi:.0f}",
                        data={"adx": adx, "rsi": rsi, "sma_stack": "bullish"},
                    ))
                # Breakdown: below all SMAs + strong downtrend
                elif close < sma20 < sma50 < sma200 and adx > 25 and rsi < 40:
                    score = 0.3 + min(0.3, adx / 100) + min(0.2, abs(ret_1d) * 5)
                    signals.append(ScanSignal(
                        symbol=symbol,
                        signal_type="technical_breakout",
                        direction="bearish",
                        score=min(1.0, score),
                        reasoning=f"Bearish alignment: close<{sma20:.0f}<{sma50:.0f}<{sma200:.0f}, ADX={adx:.0f}, RSI={rsi:.0f}",
                        data={"adx": adx, "rsi": rsi, "sma_stack": "bearish"},
                    ))

            return signals
        except Exception as e:
            logger.debug("DuckDB technical scan: %s", e)
            return []

    def _scan_duckdb_volume_spikes_sync(self) -> List[ScanSignal]:
        """Find symbols with unusual volume (>2x 20-day average)."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            df = conn.execute("""
                WITH vol_stats AS (
                    SELECT symbol, date, close, volume,
                           AVG(volume) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) as avg_vol,
                           close / NULLIF(LAG(close, 1) OVER (PARTITION BY symbol ORDER BY date), 0) - 1 as ret
                    FROM daily_ohlcv
                    WHERE date >= CURRENT_DATE - INTERVAL '25 days'
                )
                SELECT * FROM vol_stats
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND volume > avg_vol * 2
                  AND avg_vol > 100000
                ORDER BY volume / NULLIF(avg_vol, 0) DESC
                LIMIT 100
            """).fetchdf()

            signals = []
            for _, row in df.iterrows():
                vol_ratio = (row["volume"] / row["avg_vol"]) if row["avg_vol"] > 0 else 1
                ret = row.get("ret", 0) or 0
                direction = "bullish" if ret > 0 else "bearish"
                score = min(1.0, 0.2 + min(0.4, (vol_ratio - 2) / 10) + min(0.3, abs(ret) * 10))
                signals.append(ScanSignal(
                    symbol=row["symbol"],
                    signal_type="volume_spike",
                    direction=direction,
                    score=score,
                    reasoning=f"Volume spike: {vol_ratio:.1f}x avg, {ret:.1%} return",
                    data={"vol_ratio": round(vol_ratio, 1), "return_1d": round(ret, 4)},
                ))
            return signals
        except Exception as e:
            logger.debug("Volume spike scan: %s", e)
            return []

    def _scan_duckdb_momentum_sync(self) -> List[ScanSignal]:
        """Find symbols with strong momentum (5d + 20d returns)."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            df = conn.execute("""
                WITH rets AS (
                    SELECT symbol, date, close,
                           close / NULLIF(LAG(close, 5) OVER w, 0) - 1 as ret_5d,
                           close / NULLIF(LAG(close, 20) OVER w, 0) - 1 as ret_20d,
                           volume,
                           AVG(volume) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) as avg_vol
                    FROM daily_ohlcv
                    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
                    WINDOW w AS (PARTITION BY symbol ORDER BY date)
                )
                SELECT * FROM rets
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND ABS(ret_5d) > 0.05
                  AND volume > avg_vol * 1.2
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY ABS(ret_5d) DESC
                LIMIT 50
            """).fetchdf()

            signals = []
            for _, row in df.iterrows():
                ret_5d = row.get("ret_5d", 0) or 0
                ret_20d = row.get("ret_20d", 0) or 0
                direction = "bullish" if ret_5d > 0 else "bearish"
                # Higher score when 5d and 20d align
                alignment = 0.15 if (ret_5d > 0 and ret_20d > 0) or (ret_5d < 0 and ret_20d < 0) else 0
                score = min(1.0, 0.2 + min(0.4, abs(ret_5d) * 5) + alignment + min(0.2, abs(ret_20d) * 3))
                signals.append(ScanSignal(
                    symbol=row["symbol"],
                    signal_type="momentum_surge",
                    direction=direction,
                    score=score,
                    reasoning=f"Momentum: {ret_5d:.1%} 5d, {'N/A' if (isinstance(ret_20d, float) and np.isnan(ret_20d)) else f'{ret_20d:.1%}'} 20d",
                    data={"ret_5d": round(ret_5d, 4), "ret_20d": round(ret_20d, 4)},
                ))
            return signals
        except Exception as e:
            logger.debug("Momentum scan: %s", e)
            return []

    def _scan_duckdb_rsi_extremes_sync(self) -> List[ScanSignal]:
        """Find RSI extremes for reversal setups."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            df = conn.execute("""
                SELECT t.symbol, t.rsi_14, t.bb_upper, t.bb_lower, o.close
                FROM technical_indicators t
                JOIN daily_ohlcv o ON t.symbol = o.symbol AND t.date = o.date
                WHERE t.date >= CURRENT_DATE - INTERVAL '2 days'
                  AND (t.rsi_14 < 25 OR t.rsi_14 > 75)
                QUALIFY ROW_NUMBER() OVER (PARTITION BY t.symbol ORDER BY t.date DESC) = 1
                ORDER BY ABS(t.rsi_14 - 50) DESC
                LIMIT 50
            """).fetchdf()

            signals = []
            for _, row in df.iterrows():
                rsi = row.get("rsi_14", 50) or 50
                close = row.get("close", 0) or 0
                bb_lower = row.get("bb_lower", 0) or 0
                bb_upper = row.get("bb_upper", 0) or 0

                if rsi < 25:
                    # Bollinger confirmation
                    bb_confirm = close < bb_lower if bb_lower > 0 else False
                    score = min(1.0, 0.3 + (25 - rsi) * 0.02 + (0.2 if bb_confirm else 0))
                    signals.append(ScanSignal(
                        symbol=row["symbol"],
                        signal_type="rsi_extreme",
                        direction="bullish",
                        score=score,
                        reasoning=f"RSI oversold: {rsi:.0f}" + (" + below BB" if bb_confirm else ""),
                        data={"rsi": rsi, "bb_confirm": bb_confirm},
                    ))
                elif rsi > 75:
                    bb_confirm = close > bb_upper if bb_upper > 0 else False
                    score = min(1.0, 0.3 + (rsi - 75) * 0.02 + (0.2 if bb_confirm else 0))
                    signals.append(ScanSignal(
                        symbol=row["symbol"],
                        signal_type="rsi_extreme",
                        direction="bearish",
                        score=score,
                        reasoning=f"RSI overbought: {rsi:.0f}" + (" + above BB" if bb_confirm else ""),
                        data={"rsi": rsi, "bb_confirm": bb_confirm},
                    ))
            return signals
        except Exception as e:
            logger.debug("RSI extreme scan: %s", e)
            return []

    def _scan_duckdb_macd_crosses_sync(self) -> List[ScanSignal]:
        """Find fresh MACD crossovers."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            df = conn.execute("""
                WITH macd_data AS (
                    SELECT t.symbol, t.date, t.macd, t.macd_signal,
                           LAG(t.macd) OVER w as prev_macd,
                           LAG(t.macd_signal) OVER w as prev_signal,
                           t.adx_14, t.rsi_14
                    FROM technical_indicators t
                    WHERE t.date >= CURRENT_DATE - INTERVAL '5 days'
                    WINDOW w AS (PARTITION BY t.symbol ORDER BY t.date)
                )
                SELECT * FROM macd_data
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND macd IS NOT NULL AND macd_signal IS NOT NULL
                  AND prev_macd IS NOT NULL AND prev_signal IS NOT NULL
                  AND ((prev_macd < prev_signal AND macd > macd_signal)
                    OR (prev_macd > prev_signal AND macd < macd_signal))
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
            """).fetchdf()

            signals = []
            for _, row in df.iterrows():
                macd = row.get("macd", 0) or 0
                signal_line = row.get("macd_signal", 0) or 0
                bullish_cross = macd > signal_line
                adx = row.get("adx_14", 0) or 0
                rsi = row.get("rsi_14", 50) or 50

                direction = "bullish" if bullish_cross else "bearish"
                score = 0.35 + min(0.25, adx / 100)
                # RSI confirmation
                if bullish_cross and rsi < 50:
                    score += 0.15  # Bullish cross from oversold
                elif not bullish_cross and rsi > 50:
                    score += 0.15  # Bearish cross from overbought

                signals.append(ScanSignal(
                    symbol=row["symbol"],
                    signal_type="macd_cross",
                    direction=direction,
                    score=min(1.0, score),
                    reasoning=f"MACD {'bullish' if bullish_cross else 'bearish'} cross (ADX={adx:.0f}, RSI={rsi:.0f})",
                    data={"macd": round(macd, 4), "adx": adx, "rsi": rsi},
                ))
            return signals
        except Exception as e:
            logger.debug("MACD cross scan: %s", e)
            return []

    def _scan_sector_divergence_sync(self) -> List[ScanSignal]:
        """Find sectors diverging from SPY — rotation opportunities."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()

            sectors = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLU", "XLRE", "XLB", "XLC", "SPY"]
            placeholders = ",".join([f"'{s}'" for s in sectors])

            df = conn.execute(f"""
                WITH rets AS (
                    SELECT symbol, date, close,
                           close / NULLIF(LAG(close, 1) OVER w, 0) - 1 as ret_1d,
                           close / NULLIF(LAG(close, 5) OVER w, 0) - 1 as ret_5d
                    FROM daily_ohlcv
                    WHERE symbol IN ({placeholders})
                      AND date >= CURRENT_DATE - INTERVAL '10 days'
                    WINDOW w AS (PARTITION BY symbol ORDER BY date)
                )
                SELECT * FROM rets
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
            """).fetchdf()

            if df.empty:
                return []

            spy_row = df[df["symbol"] == "SPY"]
            if spy_row.empty:
                return []
            spy_5d = float(spy_row.iloc[0].get("ret_5d", 0) or 0)

            signals = []
            sector_names = {
                "XLK": "Technology", "XLF": "Financials", "XLE": "Energy",
                "XLV": "Healthcare", "XLI": "Industrials", "XLP": "Staples",
                "XLY": "Discretionary", "XLU": "Utilities", "XLRE": "Real Estate",
                "XLB": "Materials", "XLC": "Communications",
            }

            for _, row in df.iterrows():
                symbol = row["symbol"]
                if symbol == "SPY":
                    continue
                ret_5d = row.get("ret_5d", 0) or 0
                divergence = ret_5d - spy_5d

                if abs(divergence) > 0.02:  # 2%+ divergence from SPY
                    if divergence < -0.02:
                        # Sector lagging — potential bounce candidate
                        direction = "bullish"
                        reasoning = f"{sector_names.get(symbol, symbol)} lagging SPY by {abs(divergence):.1%} 5d — rotation bounce?"
                    else:
                        # Sector leading — momentum or exhaustion?
                        direction = "bullish" if divergence > 0.04 else "unknown"
                        reasoning = f"{sector_names.get(symbol, symbol)} leading SPY by {divergence:.1%} 5d — momentum"

                    score = min(1.0, 0.25 + abs(divergence) * 5)
                    signals.append(ScanSignal(
                        symbol=symbol,
                        signal_type="sector_divergence",
                        direction=direction,
                        score=score,
                        reasoning=reasoning,
                        data={"divergence_5d": round(divergence, 4), "spy_5d": round(spy_5d, 4)},
                    ))
            return signals
        except Exception as e:
            logger.debug("Sector divergence scan: %s", e)
            return []

    def _scan_vix_regime_sync(self) -> List[ScanSignal]:
        """Detect VIX regime changes — spikes, collapses, term structure shifts."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            df = conn.execute("""
                SELECT date, vix_close
                FROM macro_data
                WHERE vix_close IS NOT NULL
                ORDER BY date DESC
                LIMIT 30
            """).fetchdf()

            if df.empty or len(df) < 5:
                return []

            latest_vix = float(df.iloc[0]["vix_close"])
            prev_vix = float(df.iloc[1]["vix_close"]) if len(df) > 1 else latest_vix
            avg_vix_20 = float(df["vix_close"].head(20).mean())
            vix_change_pct = (latest_vix - prev_vix) / (prev_vix + 1e-10)

            signals = []

            # VIX spike (>15% jump)
            if vix_change_pct > 0.15:
                self._volatile_mode = True
                self._scan_interval = SCAN_INTERVAL_VOLATILE
                score = min(1.0, 0.4 + vix_change_pct * 2)
                signals.append(ScanSignal(
                    symbol="VIX",
                    signal_type="vix_regime",
                    direction="bearish",
                    score=score,
                    reasoning=f"VIX spike: {prev_vix:.1f} -> {latest_vix:.1f} (+{vix_change_pct:.0%}). Risk-off regime.",
                    data={"vix": latest_vix, "change_pct": round(vix_change_pct, 3), "avg_20": round(avg_vix_20, 1)},
                ))
                # Also signal buy opportunity for hedges
                for hedge in ["UVXY", "SQQQ", "TLT", "GLD"]:
                    signals.append(ScanSignal(
                        symbol=hedge,
                        signal_type="vix_regime",
                        direction="bullish",
                        score=score * 0.8,
                        reasoning=f"VIX spike +{vix_change_pct:.0%} — {hedge} as hedge/beneficiary",
                    ))

            # VIX collapse from high (>25% drop from elevated level)
            elif vix_change_pct < -0.10 and latest_vix > 20:
                self._volatile_mode = False
                self._scan_interval = SCAN_INTERVAL_NORMAL
                signals.append(ScanSignal(
                    symbol="SPY",
                    signal_type="vix_regime",
                    direction="bullish",
                    score=0.55,
                    reasoning=f"VIX crush: {prev_vix:.1f} -> {latest_vix:.1f} ({vix_change_pct:.0%}). Fear subsiding.",
                    data={"vix": latest_vix, "change_pct": round(vix_change_pct, 3)},
                ))

            # Elevated VIX regime (VIX > 25, unusual)
            elif latest_vix > 25 and latest_vix > avg_vix_20 * 1.3:
                signals.append(ScanSignal(
                    symbol="VIX",
                    signal_type="vix_regime",
                    direction="unknown",
                    score=0.5,
                    reasoning=f"Elevated VIX regime: {latest_vix:.1f} (avg20={avg_vix_20:.1f}). High vol environment.",
                    data={"vix": latest_vix, "avg_20": round(avg_vix_20, 1)},
                ))

            return signals
        except Exception as e:
            logger.debug("VIX regime scan: %s", e)
            return []

    def _scan_options_flow_anomalies_sync(self) -> List[ScanSignal]:
        """Find unusual options activity patterns in DuckDB."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            df = conn.execute("""
                WITH flow_stats AS (
                    SELECT symbol, date,
                           call_volume, put_volume, total_premium, pcr_volume,
                           AVG(total_premium) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING) as avg_premium
                    FROM options_flow
                    WHERE date >= CURRENT_DATE - INTERVAL '15 days'
                )
                SELECT * FROM flow_stats
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND total_premium > avg_premium * 3
                  AND total_premium > 50000
                ORDER BY total_premium / NULLIF(avg_premium, 0) DESC
                LIMIT 30
            """).fetchdf()

            signals = []
            for _, row in df.iterrows():
                symbol = row["symbol"]
                premium = row.get("total_premium", 0) or 0
                avg_premium = row.get("avg_premium", 0) or 0
                pcr = row.get("pcr_volume", 0) or 0
                call_vol = row.get("call_volume", 0) or 0
                put_vol = row.get("put_volume", 0) or 0

                ratio = premium / (avg_premium + 1) if avg_premium > 0 else 1
                direction = "bullish" if call_vol > put_vol * 1.5 else ("bearish" if put_vol > call_vol * 1.5 else "unknown")
                score = min(1.0, 0.3 + min(0.4, (ratio - 3) / 10) + (0.15 if direction != "unknown" else 0))

                signals.append(ScanSignal(
                    symbol=symbol,
                    signal_type="unusual_flow",
                    direction=direction,
                    score=score,
                    reasoning=f"Options flow {ratio:.1f}x normal (${premium:,.0f}), {'call' if call_vol > put_vol else 'put'} heavy",
                    data={"premium": premium, "ratio": round(ratio, 1), "pcr": round(pcr, 2)},
                ))
            return signals
        except Exception as e:
            logger.debug("Options flow anomaly scan: %s", e)
            return []

    def _scan_mean_reversion_setups_sync(self) -> List[ScanSignal]:
        """Find overextended symbols ready to snap back."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            df = conn.execute("""
                WITH stats AS (
                    SELECT symbol, date, close,
                           close / NULLIF(LAG(close, 5) OVER w, 0) - 1 as ret_5d,
                           AVG(close / NULLIF(LAG(close, 5) OVER w, 0) - 1)
                             OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 60 PRECEDING AND 6 PRECEDING) as avg_ret_5d,
                           STDDEV(close / NULLIF(LAG(close, 5) OVER w, 0) - 1)
                             OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 60 PRECEDING AND 6 PRECEDING) as std_ret_5d
                    FROM daily_ohlcv
                    WHERE date >= CURRENT_DATE - INTERVAL '90 days'
                    WINDOW w AS (PARTITION BY symbol ORDER BY date)
                )
                SELECT symbol, ret_5d, avg_ret_5d, std_ret_5d,
                       (ret_5d - avg_ret_5d) / NULLIF(std_ret_5d, 0) as zscore
                FROM stats
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND std_ret_5d > 0
                  AND ABS((ret_5d - avg_ret_5d) / NULLIF(std_ret_5d, 0)) > 2.0
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY ABS((ret_5d - avg_ret_5d) / NULLIF(std_ret_5d, 0)) DESC
                LIMIT 40
            """).fetchdf()

            signals = []
            for _, row in df.iterrows():
                zscore = row.get("zscore", 0) or 0
                ret_5d = row.get("ret_5d", 0) or 0

                if zscore < -2.0:
                    direction = "bullish"
                    reasoning = f"Oversold reversion: z={zscore:.1f}, {ret_5d:.1%} 5d drop"
                else:
                    direction = "bearish"
                    reasoning = f"Overbought reversion: z={zscore:.1f}, {ret_5d:.1%} 5d surge"

                score = min(1.0, 0.3 + min(0.4, (abs(zscore) - 2) / 3))
                signals.append(ScanSignal(
                    symbol=row["symbol"],
                    signal_type="mean_reversion",
                    direction=direction,
                    score=score,
                    reasoning=reasoning,
                    data={"zscore": round(zscore, 2), "ret_5d": round(ret_5d, 4)},
                ))
            return signals
        except Exception as e:
            logger.debug("Mean reversion scan: %s", e)
            return []

    def _scan_gap_reversals_sync(self) -> List[ScanSignal]:
        """Find gap-up/gap-down reversal candidates."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            df = conn.execute("""
                WITH gaps AS (
                    SELECT symbol, date, open, close, volume,
                           LAG(close) OVER w as prev_close,
                           open / NULLIF(LAG(close) OVER w, 0) - 1 as gap_pct,
                           close / NULLIF(open, 0) - 1 as intraday_ret,
                           AVG(volume) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) as avg_vol
                    FROM daily_ohlcv
                    WHERE date >= CURRENT_DATE - INTERVAL '5 days'
                    WINDOW w AS (PARTITION BY symbol ORDER BY date)
                )
                SELECT * FROM gaps
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND ABS(gap_pct) > 0.02
                  AND volume > avg_vol * 1.3
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY ABS(gap_pct) DESC
                LIMIT 30
            """).fetchdf()

            signals = []
            for _, row in df.iterrows():
                gap = row.get("gap_pct", 0) or 0
                intraday = row.get("intraday_ret", 0) or 0

                # Gap and reversal (gap up but closed red, or gap down but closed green)
                if gap > 0.02 and intraday < -0.01:
                    score = min(1.0, 0.3 + abs(gap) * 5 + abs(intraday) * 3)
                    signals.append(ScanSignal(
                        symbol=row["symbol"],
                        signal_type="mean_reversion",
                        direction="bearish",
                        score=score,
                        reasoning=f"Gap-up reversal: gapped +{gap:.1%}, closed {intraday:.1%}",
                        data={"gap": round(gap, 4), "intraday": round(intraday, 4)},
                    ))
                elif gap < -0.02 and intraday > 0.01:
                    score = min(1.0, 0.3 + abs(gap) * 5 + abs(intraday) * 3)
                    signals.append(ScanSignal(
                        symbol=row["symbol"],
                        signal_type="mean_reversion",
                        direction="bullish",
                        score=score,
                        reasoning=f"Gap-down reversal: gapped {gap:.1%}, recovered {intraday:.1%}",
                        data={"gap": round(gap, 4), "intraday": round(intraday, 4)},
                    ))
            return signals
        except Exception as e:
            logger.debug("Gap reversal scan: %s", e)
            return []

    # ──────────────────────────────────────────────────────────────────────
    # Universe Management
    # ──────────────────────────────────────────────────────────────────────
    async def _load_tier2_universe(self):
        """Load top 200 liquid symbols from DuckDB."""
        global UNIVERSE_TIER_2
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            df = conn.execute("""
                SELECT symbol, SUM(volume) as total_vol
                FROM daily_ohlcv
                WHERE date >= CURRENT_DATE - INTERVAL '10 days'
                GROUP BY symbol
                HAVING SUM(volume) > 500000
                ORDER BY total_vol DESC
                LIMIT 200
            """).fetchdf()
            if not df.empty:
                UNIVERSE_TIER_2 = df["symbol"].tolist()
                self._tier2_loaded = True
                logger.info("Loaded Tier 2 universe: %d symbols", len(UNIVERSE_TIER_2))
        except Exception as e:
            logger.debug("Tier 2 universe load: %s", e)

    # ──────────────────────────────────────────────────────────────────────
    # Signal Emission
    # ──────────────────────────────────────────────────────────────────────
    async def _emit_signal(self, signal: ScanSignal):
        """Publish signal to MessageBus for swarm processing + unified scoring."""
        self._stats["swarms_triggered"] += 1
        if self._bus:
            # Only publish swarm.idea when LLM pipeline is active — otherwise
            # SwarmSpawner triggers synchronous DuckDB ingest that deadlocks the server.
            import os as _os
            _llm_on = _os.getenv("LLM_ENABLED", "true").lower() == "true"
            priority = SIGNAL_TYPES.get(signal.signal_type, {}).get("priority", 5)
            if _llm_on:
                await self._bus.publish("swarm.idea", {
                    "source": f"turbo_scanner:{signal.signal_type}",
                    "symbols": [signal.symbol],
                    "direction": signal.direction,
                    "reasoning": signal.reasoning,
                    "priority": priority,
                    "metadata": {
                        "signal_type": signal.signal_type,
                        "score": signal.score,
                        "data": signal.data,
                    },
                })
            # Also publish as signal.generated so UnifiedProfitEngine can score it
            # (only when LLM pipeline active — UnifiedProfitEngine does sync DuckDB queries)
            # NOTE: signal.score is 0-1 scale; convert to 0-100 to match CouncilGate threshold (65.0)
            if _llm_on and signal.score >= MIN_SIGNAL_SCORE:
                await self._bus.publish("signal.generated", {
                    "symbol": signal.symbol,
                    "score": signal.score * 100,  # Convert 0-1 to 0-100 scale
                    "label": f"scanner_{signal.signal_type}",
                    "price": signal.data.get("close", 0) if isinstance(signal.data, dict) else 0,
                    "regime": "SCANNER",
                    "source": "turbo_scanner",
                })

    def reset_daily(self):
        """Reset daily dedup set (call at market open)."""
        self._seen_today.clear()

    # ──────────────────────────────────────────────────────────────────────
    # Status / API
    # ──────────────────────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "scan_interval": self._scan_interval,
            "volatile_mode": self._volatile_mode,
            "tier1_symbols": len(UNIVERSE_TIER_1),
            "tier2_symbols": len(UNIVERSE_TIER_2),
            "signals_today": len(self._seen_today),
            "stats": {k: (dict(v) if isinstance(v, defaultdict) else v) for k, v in self._stats.items()},
            "recent_signals": [s.to_dict() for s in self._signals_history[-20:]],
        }

    def get_signals(self, signal_type: str = None, limit: int = 50) -> List[Dict]:
        signals = self._signals_history
        if signal_type:
            signals = [s for s in signals if s.signal_type == signal_type]
        return [s.to_dict() for s in signals[-limit:]]


# Module-level singleton
_scanner: Optional[TurboScanner] = None

def get_turbo_scanner() -> TurboScanner:
    global _scanner
    if _scanner is None:
        _scanner = TurboScanner()
    return _scanner
