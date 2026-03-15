"""MarketWideSweep — batch scan entire US equity market for setups.

Instead of scanning 50-100 symbols, this service uses Alpaca's multi-symbol
batch endpoint to pull bars for ALL tracked symbols, then runs SQL-based
screens across the full universe in DuckDB (milliseconds for 8000+ symbols).

Workflow:
    1. Full universe ingest (batch Alpaca bars — 50 symbols per request)
    2. Compute indicators for all symbols in one pass
    3. Run 10+ SQL-based screens across entire universe
    4. Score results and emit to HyperSwarm for triage
    5. Run every 4 hours (full sweep) + incremental every 30 min

Screens:
    - Momentum leaders (5d, 20d, 60d returns by percentile)
    - Volume anomalies (>2x, >3x, >5x average volume)
    - RSI extremes (< 20 or > 80)
    - Bollinger squeeze (bandwidth at 6-month low → breakout imminent)
    - SMA golden/death crosses
    - Sector strength ranking (relative to SPY)
    - Earnings drift (post-earnings momentum continuation)
    - New highs/lows (52-week)
    - Institutional accumulation (volume + price up pattern)
    - Mean reversion candidates (z-score > 2.5)
"""
import asyncio
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

FULL_SWEEP_INTERVAL = int(os.getenv("MARKET_SWEEP_FULL_INTERVAL", "3600"))       # env default 1h (was 4h)
INCREMENTAL_INTERVAL = int(os.getenv("MARKET_SWEEP_INCR_INTERVAL", "300"))      # env default 5min (was 30min)
BATCH_SIZE = 50                   # Symbols per Alpaca batch request
MAX_UNIVERSE_SIZE = 8000          # Maximum symbols to track
INGEST_DAYS = 5                   # Days of data per incremental ingest
FULL_INGEST_DAYS = 60             # Days per full backfill
MAX_CONCURRENT_BATCHES = int(os.getenv("MARKET_SWEEP_CONCURRENCY", "20"))       # env default 20 (was 10)
BATCH_SIZE_SCREEN = int(os.getenv("MARKET_SWEEP_SCREEN_BATCH", "500"))          # screening batch (was 200)


@dataclass
class SweepResult:
    """Result of a market-wide sweep."""
    screen_name: str
    symbols: List[Dict[str, Any]]
    total_universe: int
    hits: int
    scan_time_ms: float
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screen_name": self.screen_name,
            "symbols": self.symbols[:50],  # Top 50 per screen
            "total_universe": self.total_universe,
            "hits": self.hits,
            "scan_time_ms": round(self.scan_time_ms, 1),
            "created_at": self.created_at,
        }


class MarketWideSweep:
    """Full market scanner using batch Alpaca + DuckDB SQL screens."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._universe: List[str] = []
        self._last_full_sweep = 0.0
        self._sweep_results: Dict[str, SweepResult] = {}
        self._stats = {
            "full_sweeps": 0,
            "incremental_sweeps": 0,
            "total_symbols_ingested": 0,
            "total_screen_hits": 0,
            "universe_size": 0,
            "last_sweep_duration_ms": 0.0,
        }

    async def _duckdb_query(self, query: str) -> pd.DataFrame:
        """Run a synchronous DuckDB query off the event loop via to_thread."""
        def _sync():
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store.get_thread_cursor()
            return conn.execute(query).fetchdf()
        return await asyncio.to_thread(_sync)

    async def start(self):
        if self._running:
            return
        self._running = True
        await self._build_universe()
        self._tasks.append(asyncio.create_task(self._full_sweep_loop()))
        self._tasks.append(asyncio.create_task(self._incremental_loop()))
        logger.info("MarketWideSweep started (universe=%d symbols)", len(self._universe))

    async def stop(self):
        self._running = False
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        logger.info("MarketWideSweep stopped")

    # ──────────────────────────────────────────────────────────────────────
    # Universe Building
    # ──────────────────────────────────────────────────────────────────────
    async def _build_universe(self):
        """Build the full symbol universe from Alpaca assets API."""
        try:
            from app.core.config import settings
            import httpx

            api_key = settings.ALPACA_API_KEY
            secret_key = settings.ALPACA_SECRET_KEY
            base_url = getattr(settings, "ALPACA_BASE_URL", "https://api.alpaca.markets")

            if not api_key or not secret_key:
                logger.warning("Alpaca keys not configured, using DuckDB universe")
                await self._build_universe_from_duckdb()
                return

            headers = {
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": secret_key,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{base_url}/v2/assets",
                    headers=headers,
                    params={
                        "status": "active",
                        "asset_class": "us_equity",
                    },
                )
                if resp.status_code == 200:
                    assets = resp.json()
                    # Filter to tradeable, non-OTC equities
                    self._universe = [
                        a["symbol"] for a in assets
                        if a.get("tradable") and a.get("exchange") in ("NYSE", "NASDAQ", "ARCA", "BATS", "AMEX")
                        and not a.get("symbol", "").endswith("W")  # Skip warrants
                        and "." not in a.get("symbol", "")  # Skip preferred/class shares
                    ][:MAX_UNIVERSE_SIZE]
                    self._stats["universe_size"] = len(self._universe)
                    logger.info("Built universe: %d tradeable US equities", len(self._universe))
                else:
                    logger.warning("Alpaca assets API returned %d", resp.status_code)
                    await self._build_universe_from_duckdb()
        except Exception as e:
            logger.warning("Universe build failed: %s, using DuckDB", e)
            await self._build_universe_from_duckdb()

    async def _build_universe_from_duckdb(self):
        """Fallback: build universe from symbols already in DuckDB."""
        try:
            df = await self._duckdb_query("""
                SELECT DISTINCT symbol
                FROM daily_ohlcv
                WHERE date >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY symbol
            """)
            if not df.empty:
                self._universe = df["symbol"].tolist()
                self._stats["universe_size"] = len(self._universe)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────
    # Batch Ingestion (50 symbols per request, 10 concurrent)
    # ──────────────────────────────────────────────────────────────────────
    async def _batch_ingest(self, symbols: List[str], days: int = 5):
        """Ingest OHLCV bars in parallel batches of 50."""
        from app.core.config import settings
        import httpx

        api_key = settings.ALPACA_API_KEY
        secret_key = settings.ALPACA_SECRET_KEY
        if not api_key or not secret_key:
            return

        _alpaca_data = getattr(settings, "ALPACA_DATA_URL", "https://data.alpaca.markets").rstrip("/")
        base_url = _alpaca_data if _alpaca_data.endswith("/v2") else _alpaca_data + "/v2"

        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
        }

        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59Z")

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)

        async def fetch_batch(batch: List[str]) -> List[dict]:
            async with semaphore:
                try:
                    symbols_param = ",".join(batch)
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        resp = await client.get(
                            f"{base_url}/stocks/bars",
                            headers=headers,
                            params={
                                "symbols": symbols_param,
                                "start": start_str,
                                "end": end_str,
                                "timeframe": "1Day",
                                "limit": "10000",
                                "adjustment": "split",
                                "feed": "sip",
                            },
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            bars = data.get("bars", {})
                            rows = []
                            for sym, sym_bars in bars.items():
                                for bar in sym_bars:
                                    rows.append({
                                        "symbol": sym,
                                        "date": bar["t"][:10],
                                        "open": bar["o"],
                                        "high": bar["h"],
                                        "low": bar["l"],
                                        "close": bar["c"],
                                        "volume": bar["v"],
                                        "source": "alpaca_batch",
                                    })
                            return rows
                except Exception as e:
                    logger.debug("Batch ingest failed for %d symbols: %s", len(batch), e)
                return []

        # Split into batches of BATCH_SIZE
        batches = [symbols[i:i + BATCH_SIZE] for i in range(0, len(symbols), BATCH_SIZE)]

        # Run all batches concurrently (limited by semaphore)
        results = await asyncio.gather(*[fetch_batch(b) for b in batches], return_exceptions=True)

        all_rows = []
        for result in results:
            if isinstance(result, list):
                all_rows.extend(result)

        if all_rows:
            from app.data.duckdb_storage import duckdb_store
            df = pd.DataFrame(all_rows)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            await asyncio.to_thread(duckdb_store.upsert_ohlcv, df)
            self._stats["total_symbols_ingested"] += len(set(df["symbol"]))
            logger.info("Batch ingested %d bars for %d symbols", len(df), len(set(df["symbol"])))

    # ──────────────────────────────────────────────────────────────────────
    # SQL-Based Screens (run across entire universe in DuckDB)
    # ──────────────────────────────────────────────────────────────────────
    async def _run_all_screens(self) -> Dict[str, SweepResult]:
        """Run all SQL screens against the full DuckDB universe."""
        screens = {
            "momentum_leaders": self._screen_momentum_leaders,
            "volume_anomalies": self._screen_volume_anomalies,
            "rsi_extremes": self._screen_rsi_extremes,
            "bollinger_squeeze": self._screen_bollinger_squeeze,
            "sma_crosses": self._screen_sma_crosses,
            "new_highs_lows": self._screen_new_highs_lows,
            "mean_reversion": self._screen_mean_reversion,
            "institutional_accumulation": self._screen_accumulation,
            "sector_strength": self._screen_sector_strength,
            "consecutive_moves": self._screen_consecutive_moves,
        }

        results = {}
        for name, fn in screens.items():
            try:
                t0 = time.monotonic()
                result = await fn()
                elapsed = (time.monotonic() - t0) * 1000
                if result:
                    sweep = SweepResult(
                        screen_name=name,
                        symbols=result,
                        total_universe=self._stats["universe_size"],
                        hits=len(result),
                        scan_time_ms=elapsed,
                    )
                    results[name] = sweep
                    self._stats["total_screen_hits"] += len(result)
            except Exception as e:
                logger.debug("Screen %s failed: %s", name, e)

        return results

    async def _screen_momentum_leaders(self) -> List[Dict]:
        try:
            df = await self._duckdb_query("""
                WITH rets AS (
                    SELECT symbol, date, close, volume,
                           close / NULLIF(FIRST_VALUE(close) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 5 PRECEDING AND 5 PRECEDING), 0) - 1 as ret_5d,
                           close / NULLIF(FIRST_VALUE(close) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 20 PRECEDING AND 20 PRECEDING), 0) - 1 as ret_20d
                    FROM daily_ohlcv
                    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
                )
                SELECT symbol, ret_5d, ret_20d FROM rets
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND ret_5d > 0.03 AND ret_20d > 0.05
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY ret_5d + ret_20d DESC
                LIMIT 50
            """)
            return [{"symbol": r["symbol"], "ret_5d": round(r["ret_5d"], 4), "ret_20d": round(r["ret_20d"], 4)} for _, r in df.iterrows()]
        except Exception:
            return []

    async def _screen_volume_anomalies(self) -> List[Dict]:
        try:
            df = await self._duckdb_query("""
                WITH vol AS (
                    SELECT symbol, date, volume,
                           AVG(volume) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) as avg_vol
                    FROM daily_ohlcv
                    WHERE date >= CURRENT_DATE - INTERVAL '25 days'
                )
                SELECT symbol, volume, avg_vol, volume / NULLIF(avg_vol, 0) as ratio
                FROM vol
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND volume > avg_vol * 3
                  AND avg_vol > 200000
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY ratio DESC
                LIMIT 50
            """)
            return [{"symbol": r["symbol"], "vol_ratio": round(r["ratio"], 1)} for _, r in df.iterrows()]
        except Exception:
            return []

    async def _screen_rsi_extremes(self) -> List[Dict]:
        try:
            df = await self._duckdb_query("""
                SELECT symbol, rsi_14
                FROM technical_indicators
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND (rsi_14 < 20 OR rsi_14 > 80)
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY ABS(rsi_14 - 50) DESC
                LIMIT 50
            """)
            return [{"symbol": r["symbol"], "rsi": round(r["rsi_14"], 1)} for _, r in df.iterrows()]
        except Exception:
            return []

    async def _screen_bollinger_squeeze(self) -> List[Dict]:
        """Find symbols where Bollinger bandwidth is at multi-week low (breakout imminent)."""
        try:
            df = await self._duckdb_query("""
                WITH bb AS (
                    SELECT symbol, date,
                           (bb_upper - bb_lower) / NULLIF(bb_middle, 0) as bandwidth,
                           MIN((bb_upper - bb_lower) / NULLIF(bb_middle, 0))
                             OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) as min_bw
                    FROM technical_indicators
                    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
                      AND bb_upper IS NOT NULL AND bb_lower IS NOT NULL AND bb_middle IS NOT NULL
                )
                SELECT symbol, bandwidth, min_bw
                FROM bb
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND bandwidth <= min_bw * 1.05
                  AND bandwidth > 0
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY bandwidth ASC
                LIMIT 30
            """)
            return [{"symbol": r["symbol"], "bandwidth": round(r["bandwidth"], 4)} for _, r in df.iterrows()]
        except Exception:
            return []

    async def _screen_sma_crosses(self) -> List[Dict]:
        """Find recent golden/death crosses (SMA50 crossing SMA200)."""
        try:
            df = await self._duckdb_query("""
                WITH crosses AS (
                    SELECT symbol, date, sma_50, sma_200,
                           LAG(sma_50) OVER w as prev_50,
                           LAG(sma_200) OVER w as prev_200
                    FROM technical_indicators
                    WHERE date >= CURRENT_DATE - INTERVAL '5 days'
                      AND sma_50 IS NOT NULL AND sma_200 IS NOT NULL
                    WINDOW w AS (PARTITION BY symbol ORDER BY date)
                )
                SELECT symbol, sma_50, sma_200,
                       CASE WHEN prev_50 < prev_200 AND sma_50 > sma_200 THEN 'golden_cross'
                            WHEN prev_50 > prev_200 AND sma_50 < sma_200 THEN 'death_cross'
                       END as cross_type
                FROM crosses
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND ((prev_50 < prev_200 AND sma_50 > sma_200)
                    OR (prev_50 > prev_200 AND sma_50 < sma_200))
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
            """)
            return [{"symbol": r["symbol"], "cross_type": r["cross_type"]} for _, r in df.iterrows()]
        except Exception:
            return []

    async def _screen_new_highs_lows(self) -> List[Dict]:
        """Find symbols at 52-week highs or lows."""
        try:
            df = await self._duckdb_query("""
                WITH extremes AS (
                    SELECT symbol, date, close,
                           MAX(high) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 252 PRECEDING AND 1 PRECEDING) as high_52w,
                           MIN(low) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 252 PRECEDING AND 1 PRECEDING) as low_52w
                    FROM daily_ohlcv
                    WHERE date >= CURRENT_DATE - INTERVAL '260 days'
                )
                SELECT symbol, close, high_52w, low_52w,
                       CASE WHEN close >= high_52w * 0.98 THEN 'near_52w_high'
                            WHEN close <= low_52w * 1.02 THEN 'near_52w_low'
                       END as extreme_type
                FROM extremes
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND (close >= high_52w * 0.98 OR close <= low_52w * 1.02)
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY CASE WHEN close >= high_52w * 0.98 THEN close / NULLIF(high_52w, 0)
                              ELSE low_52w / NULLIF(close, 0) END DESC
                LIMIT 50
            """).fetchdf()
            return [{"symbol": r["symbol"], "type": r["extreme_type"], "close": round(r["close"], 2)} for _, r in df.iterrows()]
        except Exception:
            return []

    async def _screen_mean_reversion(self) -> List[Dict]:
        try:
            df = await self._duckdb_query("""
                WITH stats AS (
                    SELECT symbol, date, close,
                           close / NULLIF(LAG(close, 5) OVER w, 0) - 1 as ret_5d,
                           AVG(close / NULLIF(LAG(close, 5) OVER w, 0) - 1) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 60 PRECEDING AND 6 PRECEDING) as avg_ret,
                           STDDEV(close / NULLIF(LAG(close, 5) OVER w, 0) - 1) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 60 PRECEDING AND 6 PRECEDING) as std_ret
                    FROM daily_ohlcv
                    WHERE date >= CURRENT_DATE - INTERVAL '90 days'
                    WINDOW w AS (PARTITION BY symbol ORDER BY date)
                )
                SELECT symbol, ret_5d, (ret_5d - avg_ret) / NULLIF(std_ret, 0) as zscore
                FROM stats
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                  AND ABS((ret_5d - avg_ret) / NULLIF(std_ret, 0)) > 2.5
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY ABS((ret_5d - avg_ret) / NULLIF(std_ret, 0)) DESC
                LIMIT 40
            """).fetchdf()
            return [{"symbol": r["symbol"], "zscore": round(r["zscore"], 2), "ret_5d": round(r["ret_5d"], 4)} for _, r in df.iterrows()]
        except Exception:
            return []

    async def _screen_accumulation(self) -> List[Dict]:
        """Detect institutional accumulation: price up + volume up for 3+ days."""
        try:
            df = await self._duckdb_query("""
                WITH daily AS (
                    SELECT symbol, date, close, volume,
                           close > LAG(close) OVER w as price_up,
                           volume > LAG(volume) OVER w as vol_up
                    FROM daily_ohlcv
                    WHERE date >= CURRENT_DATE - INTERVAL '10 days'
                    WINDOW w AS (PARTITION BY symbol ORDER BY date)
                )
                SELECT symbol,
                       SUM(CASE WHEN price_up AND vol_up THEN 1 ELSE 0 END) as accum_days
                FROM daily
                WHERE date >= CURRENT_DATE - INTERVAL '5 days'
                GROUP BY symbol
                HAVING accum_days >= 3
                ORDER BY accum_days DESC
                LIMIT 30
            """).fetchdf()
            return [{"symbol": r["symbol"], "accum_days": int(r["accum_days"])} for _, r in df.iterrows()]
        except Exception:
            return []

    async def _screen_sector_strength(self) -> List[Dict]:
        """Rank sectors by relative strength vs SPY."""
        try:
            sectors = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLU", "XLRE", "XLB", "XLC"]
            placeholders = ",".join([f"'{s}'" for s in sectors + ["SPY"]])
            df = await self._duckdb_query(f"""
                WITH rets AS (
                    SELECT symbol,
                           close / NULLIF(FIRST_VALUE(close) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 5 PRECEDING AND 5 PRECEDING), 0) - 1 as ret_5d
                    FROM daily_ohlcv
                    WHERE symbol IN ({placeholders})
                      AND date >= CURRENT_DATE - INTERVAL '10 days'
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                )
                SELECT symbol, ret_5d
                FROM rets
                ORDER BY ret_5d DESC
            """).fetchdf()
            return [{"symbol": r["symbol"], "ret_5d": round(r["ret_5d"], 4)} for _, r in df.iterrows()]
        except Exception:
            return []

    async def _screen_consecutive_moves(self) -> List[Dict]:
        """Find symbols with 3+ consecutive up or down days."""
        try:
            df = await self._duckdb_query("""
                WITH daily AS (
                    SELECT symbol, date, close,
                           CASE WHEN close > LAG(close) OVER w THEN 1 ELSE -1 END as direction
                    FROM daily_ohlcv
                    WHERE date >= CURRENT_DATE - INTERVAL '10 days'
                    WINDOW w AS (PARTITION BY symbol ORDER BY date)
                )
                SELECT symbol,
                       SUM(CASE WHEN direction = 1 THEN 1 ELSE 0 END) as up_days,
                       SUM(CASE WHEN direction = -1 THEN 1 ELSE 0 END) as down_days
                FROM daily
                WHERE date >= CURRENT_DATE - INTERVAL '5 days'
                GROUP BY symbol
                HAVING up_days >= 4 OR down_days >= 4
                ORDER BY GREATEST(up_days, down_days) DESC
                LIMIT 30
            """).fetchdf()
            return [{"symbol": r["symbol"], "up_days": int(r["up_days"]), "down_days": int(r["down_days"])} for _, r in df.iterrows()]
        except Exception:
            return []

    # ──────────────────────────────────────────────────────────────────────
    # Sweep Loops
    # ──────────────────────────────────────────────────────────────────────
    async def _full_sweep_loop(self):
        """Full market sweep every 4 hours."""
        await asyncio.sleep(120)  # Let system warm up
        while self._running:
            try:
                t0 = time.monotonic()
                logger.info("Starting full market sweep (%d symbols)...", len(self._universe))

                # Phase 1: Batch ingest for full universe
                if self._universe:
                    await self._batch_ingest(self._universe, days=FULL_INGEST_DAYS)

                # Phase 2: Compute indicators (off event loop)
                try:
                    from app.services.data_ingestion import data_ingestion
                    await asyncio.to_thread(data_ingestion.compute_and_store_indicators)
                except Exception as e:
                    logger.debug("Indicator computation: %s", e)

                # Phase 3: Run all screens
                results = await self._run_all_screens()
                self._sweep_results = results

                elapsed = (time.monotonic() - t0) * 1000
                self._stats["full_sweeps"] += 1
                self._stats["last_sweep_duration_ms"] = elapsed

                # Phase 4: Emit top findings to swarm
                await self._emit_sweep_results(results)

                total_hits = sum(r.hits for r in results.values())
                logger.info(
                    "Full sweep complete: %d screens, %d hits, %.1fs",
                    len(results), total_hits, elapsed / 1000,
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Full sweep error: %s", e)

            await asyncio.sleep(FULL_SWEEP_INTERVAL)

    async def _incremental_loop(self):
        """Incremental scan every 30 minutes."""
        await asyncio.sleep(300)  # Let full sweep run first
        while self._running:
            try:
                # Only run screens (skip ingestion for speed)
                results = await self._run_all_screens()
                self._sweep_results.update(results)
                self._stats["incremental_sweeps"] += 1
                await self._emit_sweep_results(results)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Incremental sweep error: %s", e)

            await asyncio.sleep(INCREMENTAL_INTERVAL)

    async def _emit_sweep_results(self, results: Dict[str, SweepResult]):
        """Emit top sweep findings to swarm for analysis."""
        if not self._bus:
            return

        for screen_name, sweep in results.items():
            for sym_data in sweep.symbols[:10]:  # Top 10 per screen
                symbol = sym_data.get("symbol", "")
                if not symbol:
                    continue

                # Determine direction from screen type
                direction = "unknown"
                if screen_name in ("momentum_leaders", "institutional_accumulation"):
                    direction = "bullish"
                elif screen_name in ("rsi_extremes",):
                    rsi = sym_data.get("rsi", 50)
                    direction = "bullish" if rsi < 30 else "bearish"
                elif screen_name in ("new_highs_lows",):
                    direction = "bullish" if sym_data.get("type") == "near_52w_high" else "bearish"

                await self._bus.publish("swarm.idea", {
                    "source": f"market_sweep:{screen_name}",
                    "symbols": [symbol],
                    "direction": direction,
                    "reasoning": f"[Sweep:{screen_name}] {sym_data}",
                    "priority": 4,
                    "metadata": {"screen": screen_name, "data": sym_data},
                })
                # Also publish as signal.generated for unified scoring
                await self._bus.publish("signal.generated", {
                    "symbol": symbol,
                    "score": 65.0,  # Sweep hit = moderate signal
                    "label": f"sweep_{screen_name}",
                    "price": sym_data.get("close", 0),
                    "regime": "SWEEP",
                    "source": "market_wide_sweep",
                })

    # ──────────────────────────────────────────────────────────────────────
    # Status / API
    # ──────────────────────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "universe_size": len(self._universe),
            "stats": dict(self._stats),
            "screens": {
                name: result.to_dict() for name, result in self._sweep_results.items()
            },
        }

    def get_screen(self, screen_name: str) -> Optional[Dict]:
        result = self._sweep_results.get(screen_name)
        return result.to_dict() if result else None

    def get_all_screens(self) -> Dict[str, Any]:
        return {name: r.to_dict() for name, r in self._sweep_results.items()}


# Module-level singleton
_sweep: Optional[MarketWideSweep] = None

def get_market_sweep() -> MarketWideSweep:
    global _sweep
    if _sweep is None:
        _sweep = MarketWideSweep()
    return _sweep
