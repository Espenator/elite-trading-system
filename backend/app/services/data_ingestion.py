"""Data Ingestion Service — Pulls from all external APIs and persists to DuckDB.

This is the write-side orchestrator that feeds the analytics database.
market_data_agent.py calls this during each tick to persist data.

Data flow:
    Alpaca Market Data API -> daily_ohlcv
    ta library calculations -> technical_indicators
    Unusual Whales API     -> options_flow
    FRED API               -> macro_data
    Order fills            -> trade_outcomes

Phase D1 enhancements (March 11 2026):
  - Startup backfill: 252 days for all tracked symbols on boot
  - Daily scheduler: incremental backfill at 4:30 AM ET
  - Weekly full refresh: technical indicators at midnight Sunday
  - Rate-limited: uses AsyncRateLimiter for Alpaca (200/min)
  - Batched symbol fetching: 50 symbols per Alpaca multi-bar request

Usage:
    from app.services.data_ingestion import data_ingestion
    await data_ingestion.ingest_daily_bars(["AAPL", "MSFT"], days=252)
    await data_ingestion.ingest_all(["AAPL", "MSFT"])
    await data_ingestion.run_startup_backfill()

Fixes Issue #25 Task 4.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)

# Alpaca Market Data API (separate from trading API)
_alpaca_data = getattr(settings, "ALPACA_DATA_URL", "https://data.alpaca.markets").rstrip("/")
ALPACA_DATA_BASE_URL = _alpaca_data if _alpaca_data.endswith("/v2") else _alpaca_data + "/v2"

# FRED series IDs for macro features
FRED_SERIES = {
    "vix_close": "VIXCLS",
    "dxy_close": "DTWEXBGS",
    "us10y_yield": "DGS10",
    "fed_funds_rate": "DFF",
}


class DataIngestionService:
    """Orchestrates data collection from all sources into DuckDB."""

    def __init__(self):
        self._store = None

    @property
    def store(self):
        if self._store is None:
            from app.data.duckdb_storage import duckdb_store
            self._store = duckdb_store
        return self._store

    # ------------------------------------------------------------------
    # Alpaca OHLCV bars (Market Data API, not Trading API)
    # ------------------------------------------------------------------

    async def ingest_daily_bars(
        self,
        symbols: List[str],
        days: int = 252,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """Fetch daily OHLCV bars from Alpaca Market Data API and persist to DuckDB.

        Uses the /v2/stocks/bars endpoint (separate from trading API).
        No yfinance. Alpaca provides free historical bars for US equities.

        Args:
            symbols: List of ticker symbols
            days: Number of calendar days of history to fetch
            end_date: End date (YYYY-MM-DD), defaults to today

        Returns:
            Dict with counts per symbol
        """
        import httpx

        api_key = settings.ALPACA_API_KEY
        secret_key = settings.ALPACA_SECRET_KEY
        if not api_key or not secret_key:
            logger.warning("Alpaca API keys not configured, skipping OHLCV ingestion")
            return {"error": "API keys not configured"}

        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "accept": "application/json",
        }

        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
        start_dt = end_dt - timedelta(days=days)
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59Z")

        results = {}
        all_rows = []

        from app.core.rate_limiter import get_rate_limiter
        limiter = get_rate_limiter("alpaca")

        # Batch symbols into groups of 50 for multi-bar endpoint
        batch_size = 50
        for batch_start in range(0, len(symbols), batch_size):
            batch = symbols[batch_start:batch_start + batch_size]

            try:
                async with limiter:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        # Use multi-symbol bars endpoint for efficiency
                        page_token = None
                        batch_rows = []
                        max_pages = 100
                        page_count = 0

                        while page_count < max_pages:
                            page_count += 1
                            params = {
                                "symbols": ",".join(batch),
                                "start": start_str,
                                "end": end_str,
                                "timeframe": "1Day",
                                "limit": "10000",
                                "adjustment": "split",
                                "feed": "sip",
                            }
                            if page_token:
                                params["page_token"] = page_token

                            resp = await client.get(
                                f"{ALPACA_DATA_BASE_URL}/stocks/bars",
                                headers=headers,
                                params=params,
                            )

                            if resp.status_code != 200:
                                logger.warning(
                                    "Alpaca multi-bars batch: HTTP %s", resp.status_code
                                )
                                break

                            data = resp.json()
                            bars_map = data.get("bars") or {}

                            for symbol, bars in bars_map.items():
                                for bar in bars:
                                    batch_rows.append({
                                        "symbol": symbol,
                                        "date": bar["t"][:10],
                                        "open": bar["o"],
                                        "high": bar["h"],
                                        "low": bar["l"],
                                        "close": bar["c"],
                                        "volume": bar["v"],
                                        "source": "alpaca",
                                    })

                            page_token = data.get("next_page_token")
                            if not page_token:
                                break

                        all_rows.extend(batch_rows)
                        # Count per symbol
                        for row in batch_rows:
                            s = row["symbol"]
                            results[s] = results.get(s, 0) + 1
                        logger.info(
                            "Alpaca multi-bars batch (%d symbols): %d rows",
                            len(batch), len(batch_rows),
                        )

                # Yield to event loop between batches so HTTP handlers can run
                await asyncio.sleep(0.1)

            except Exception as exc:
                logger.error("Alpaca multi-bars batch failed: %s", exc)
                for s in batch:
                    results.setdefault(s, 0)

        if all_rows:
            df = pd.DataFrame(all_rows)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            await asyncio.to_thread(self.store.upsert_ohlcv, df)
            logger.info("Persisted %d total OHLCV rows to DuckDB", len(df))

        results["total_rows"] = len(all_rows)
        return results

    # ------------------------------------------------------------------
    # Technical indicators (computed from OHLCV in DuckDB)
    # ------------------------------------------------------------------

    def compute_and_store_indicators(
        self,
        symbols: List[str] = None,
        lookback_days: int = 300,
    ) -> int:
        """Compute technical indicators from OHLCV data and store in DuckDB.

        Calculates: RSI, MACD, SMAs, EMAs, ATR, Bollinger Bands, ADX, Williams %R.
        Reads from daily_ohlcv, writes to technical_indicators.

        Returns:
            Number of indicator rows stored.
        """
        conn = self.store._get_conn()

        if symbols:
            placeholders = ",".join(["?" for _ in symbols])
            query = f"""
                SELECT symbol, date, open, high, low, close, volume
                FROM daily_ohlcv
                WHERE symbol IN ({placeholders})
                  AND date >= CURRENT_DATE - INTERVAL '{lookback_days}' DAY
                ORDER BY symbol, date
            """
            df = conn.execute(query, symbols).fetchdf()
        else:
            df = conn.execute(f"""
                SELECT symbol, date, open, high, low, close, volume
                FROM daily_ohlcv
                WHERE date >= CURRENT_DATE - INTERVAL '{lookback_days}' DAY
                ORDER BY symbol, date
            """).fetchdf()

        if df.empty:
            logger.warning("No OHLCV data for indicator computation")
            return 0

        results = []
        for symbol, group in df.groupby("symbol"):
            g = group.sort_values("date").copy()
            close = g["close"]
            high = g["high"]
            low = g["low"]

            row = pd.DataFrame()
            row["symbol"] = g["symbol"]
            row["date"] = g["date"]

            # RSI 14
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / (loss + 1e-10)
            row["rsi_14"] = 100 - 100 / (1 + rs)

            # MACD
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            row["macd"] = ema12 - ema26
            row["macd_signal"] = row["macd"].ewm(span=9).mean()
            row["macd_hist"] = row["macd"] - row["macd_signal"]

            # SMAs
            row["sma_20"] = close.rolling(20).mean()
            row["sma_50"] = close.rolling(50).mean()
            row["sma_200"] = close.rolling(200).mean()

            # EMAs
            row["ema_9"] = close.ewm(span=9).mean()
            row["ema_21"] = close.ewm(span=21).mean()

            # ATR
            prev_close = close.shift(1)
            tr = pd.concat([
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ], axis=1).max(axis=1)
            row["atr_14"] = tr.rolling(14).mean()
            row["atr_21"] = tr.rolling(21).mean()

            # Bollinger Bands
            row["bb_middle"] = close.rolling(20).mean()
            bb_std = close.rolling(20).std()
            row["bb_upper"] = row["bb_middle"] + 2 * bb_std
            row["bb_lower"] = row["bb_middle"] - 2 * bb_std

            # ADX 14 (simplified)
            plus_dm = high.diff().clip(lower=0)
            minus_dm = (-low.diff()).clip(lower=0)
            atr14 = row["atr_14"]
            plus_di = 100 * (plus_dm.rolling(14).mean() / (atr14 + 1e-10))
            minus_di = 100 * (minus_dm.rolling(14).mean() / (atr14 + 1e-10))
            dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
            row["adx_14"] = dx.rolling(14).mean()

            # Williams %R
            highest_14 = high.rolling(14).max()
            lowest_14 = low.rolling(14).min()
            row["williams_r"] = -100 * (highest_14 - close) / (highest_14 - lowest_14 + 1e-10)

            results.append(row)

        if results:
            indicators_df = pd.concat(results, ignore_index=True)
            indicators_df = indicators_df.dropna(subset=["rsi_14"])
            self.store.upsert_indicators(indicators_df)
            logger.info("Computed and stored %d indicator rows", len(indicators_df))
            return len(indicators_df)

        return 0

    # ------------------------------------------------------------------
    # Unusual Whales options flow
    # ------------------------------------------------------------------

    async def ingest_options_flow(self) -> int:
        """Fetch options flow from Unusual Whales and persist to DuckDB.

        Transforms raw flow alerts into the structured options_flow schema.

        Returns:
            Number of flow rows stored.
        """
        try:
            from app.services.unusual_whales_service import UnusualWhalesService
            svc = UnusualWhalesService()
            data = await svc.get_flow_alerts()
        except Exception as exc:
            logger.warning("Unusual Whales ingestion skipped: %s", exc)
            return 0

        if not data:
            return 0

        alerts = data if isinstance(data, list) else data.get("data", data.get("items", []))
        if not alerts:
            return 0

        rows = []
        for alert in alerts:
            symbol = (alert.get("ticker") or alert.get("symbol") or "").upper()
            if not symbol:
                continue

            alert_date = (
                alert.get("date")
                or alert.get("traded_at", "")[:10]
                or date.today().isoformat()
            )

            is_call = (alert.get("option_type") or alert.get("type") or "").upper() == "CALL"
            volume = int(alert.get("volume") or alert.get("size") or 0)
            premium = float(alert.get("premium") or alert.get("total_premium") or 0)

            rows.append({
                "symbol": symbol,
                "date": alert_date,
                "call_volume": volume if is_call else 0,
                "put_volume": 0 if is_call else volume,
                "net_premium": premium if is_call else -premium,
                "pcr_volume": 0.0,
                "dark_pool_volume": int(alert.get("dark_pool_volume") or 0),
                "total_premium": abs(premium),
                "source": "unusual_whales",
            })

        if rows:
            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"]).dt.date

            # Aggregate by symbol+date (multiple alerts per day)
            agg_df = df.groupby(["symbol", "date"]).agg({
                "call_volume": "sum",
                "put_volume": "sum",
                "net_premium": "sum",
                "dark_pool_volume": "sum",
                "total_premium": "sum",
            }).reset_index()
            agg_df["pcr_volume"] = agg_df["put_volume"] / (agg_df["call_volume"] + 1)
            agg_df["source"] = "unusual_whales"

            await asyncio.to_thread(self.store.upsert_options_flow, agg_df)
            logger.info("Persisted %d options flow rows to DuckDB", len(agg_df))
            return len(agg_df)

        return 0

    # ------------------------------------------------------------------
    # FRED macro data
    # ------------------------------------------------------------------

    async def ingest_macro_data(self, days: int = 252) -> int:
        """Fetch macro series from FRED and persist to DuckDB.

        Pulls: VIX, DXY, US10Y, Fed Funds Rate.
        Also fetches SPY/QQQ close from Alpaca for regime features.

        Returns:
            Number of macro rows stored.
        """
        try:
            from app.services.fred_service import FredService
            svc = FredService()
        except Exception as exc:
            logger.warning("FRED ingestion skipped: %s", exc)
            return 0

        # Collect FRED series
        series_data = {}
        for col_name, series_id in FRED_SERIES.items():
            try:
                obs = await svc.get_observations(series_id, limit=days, sort_order="asc")
                for ob in obs:
                    d = ob.get("date")
                    v = ob.get("value")
                    if d and v and v != ".":
                        if d not in series_data:
                            series_data[d] = {}
                        series_data[d][col_name] = float(v)
            except Exception as exc:
                logger.warning("FRED series %s failed: %s", series_id, exc)

        if not series_data:
            logger.warning("No FRED data retrieved")
            return 0

        # Build DataFrame
        rows = []
        for d, values in series_data.items():
            row = {"date": d}
            row.update(values)
            rows.append(row)

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"]).dt.date

        # Fill missing columns with NaN
        for col in ["vix_close", "dxy_close", "us10y_yield", "fed_funds_rate",
                     "spy_close", "qqq_close", "breadth_ratio"]:
            if col not in df.columns:
                df[col] = np.nan

        # Try to get SPY/QQQ close from DuckDB (already ingested via Alpaca)
        def _merge_etf(df_in):
            conn = self.store._get_conn()
            for etf in ["SPY", "QQQ"]:
                etf_df = conn.execute(f"""
                    SELECT date, close as {etf.lower()}_close
                    FROM daily_ohlcv
                    WHERE symbol = '{etf}'
                    ORDER BY date
                """).fetchdf()
                if not etf_df.empty:
                    etf_df["date"] = pd.to_datetime(etf_df["date"]).dt.date
                    df_in = df_in.merge(etf_df, on="date", how="left", suffixes=("", "_ohlcv"))
                    ohlcv_col = f"{etf.lower()}_close_ohlcv"
                    if ohlcv_col in df_in.columns:
                        df_in[f"{etf.lower()}_close"] = df_in[f"{etf.lower()}_close"].fillna(df_in[ohlcv_col])
                        df_in = df_in.drop(columns=[ohlcv_col])
            return df_in

        try:
            df = await asyncio.to_thread(_merge_etf, df)
        except Exception as exc:
            logger.debug("SPY/QQQ merge from DuckDB failed: %s", exc)

        # Ensure column order matches macro_data schema
        macro_cols = ["date", "vix_close", "dxy_close", "us10y_yield",
                      "fed_funds_rate", "spy_close", "qqq_close", "breadth_ratio"]
        for col in macro_cols:
            if col not in df.columns:
                df[col] = np.nan
        df = df[macro_cols]

        await asyncio.to_thread(self.store.upsert_macro, df)
        logger.info("Persisted %d macro rows to DuckDB", len(df))
        return len(df)

    # ------------------------------------------------------------------
    # Trade outcome ingestion (from Alpaca fills)
    # ------------------------------------------------------------------

    async def ingest_trade_outcomes(self) -> int:
        """Pull filled orders from Alpaca and record as trade outcomes.

        Matches buy fills to subsequent sell fills per symbol to compute PnL.

        Returns:
            Number of outcomes recorded.
        """
        try:
            from app.services.alpaca_service import alpaca_service
            fills = await alpaca_service.get_activities(activity_types="FILL", limit=100)
        except Exception as exc:
            logger.warning("Trade outcome ingestion skipped: %s", exc)
            return 0

        if not fills:
            return 0

        # Group fills by symbol, pair buy->sell
        from collections import defaultdict
        buys = defaultdict(list)
        sells = defaultdict(list)

        for fill in fills:
            symbol = (fill.get("symbol") or "").upper()
            side = (fill.get("side") or "").lower()
            if not symbol:
                continue
            entry = {
                "symbol": symbol,
                "date": (fill.get("transaction_time") or "")[:10],
                "price": float(fill.get("price") or 0),
                "qty": float(fill.get("qty") or 0),  # fractional shares (e.g. crypto) supported
            }
            if side == "buy":
                buys[symbol].append(entry)
            elif side in ("sell", "sell_short"):
                sells[symbol].append(entry)

        def _match_and_insert(buys_d, sells_d):
            """Match buy→sell fills and insert outcomes (sync, runs in thread)."""
            cnt = 0
            for sym in buys_d:
                for buy in buys_d[sym]:
                    matching = [
                        s for s in sells_d.get(sym, [])
                        if s["date"] >= buy["date"]
                    ]
                    if matching:
                        sell = matching[0]
                        pnl = (sell["price"] - buy["price"]) * buy["qty"]
                        pct_return = (sell["price"] - buy["price"]) / (buy["price"] + 1e-10)
                        self.store.insert_trade_outcome({
                            "symbol": sym,
                            "direction": "LONG",
                            "entry_date": buy["date"],
                            "exit_date": sell["date"],
                            "entry_price": buy["price"],
                            "exit_price": sell["price"],
                            "shares": int(round(buy["qty"])),
                            "pnl": pnl,
                            "r_multiple": pct_return,
                            "outcome": "WIN" if pnl > 0 else "LOSS",
                            "resolved": True,
                            "resolved_at": datetime.utcnow().isoformat(),
                        })
                        cnt += 1
                        sells_d[sym].remove(sell)
            return cnt

        count = await asyncio.to_thread(_match_and_insert, buys, sells)

        if count:
            logger.info("Recorded %d trade outcomes to DuckDB", count)
        return count

    # ------------------------------------------------------------------
    # Full ingestion cycle
    # ------------------------------------------------------------------

    async def ingest_all(
        self,
        symbols: List[str],
        days: int = 252,
    ) -> Dict[str, Any]:
        """Run complete data ingestion cycle.

        1. Fetch OHLCV bars from Alpaca
        2. Compute technical indicators
        3. Fetch options flow from Unusual Whales
        4. Fetch macro data from FRED
        5. Record trade outcomes from Alpaca fills

        This should be called:
        - On initial setup (days=252 for full backfill)
        - Daily before market open (days=5 for incremental)
        - After each market_data_agent tick (days=1 for latest)
        """
        report = {"timestamp": datetime.utcnow().isoformat()}

        logger.info("Starting full ingestion for %d symbols, %d days", len(symbols), days)

        # 1. OHLCV
        report["ohlcv"] = await self.ingest_daily_bars(symbols, days=days)

        # 2. Indicators (computed from freshly ingested OHLCV)
        report["indicators"] = await asyncio.to_thread(self.compute_and_store_indicators, symbols)

        # 3. Options flow
        report["options_flow"] = await self.ingest_options_flow()

        # 4. Macro
        report["macro"] = await self.ingest_macro_data(days=days)

        # 5. Trade outcomes
        report["trade_outcomes"] = await self.ingest_trade_outcomes()

        # Health check (sync DuckDB call → run in thread)
        report["duckdb_health"] = await asyncio.to_thread(self.store.health_check)

        logger.info("Full ingestion complete: %s", report)
        return report


    # ------------------------------------------------------------------
    # D1: Startup backfill orchestrator
    # ------------------------------------------------------------------

    async def run_startup_backfill(self, days: int = 252) -> Dict[str, Any]:
        """Run gap-only backfill on startup for priority symbols.

        Called from main.py lifespan. Runs in background so API server
        is responsive immediately.

        Optimizations vs naive 252-day × full-universe approach:
        1. Caps symbols to 50 max (core + positions + recent council)
        2. Queries DuckDB for latest date per symbol — only fetches the gap
        3. Skips symbols already up-to-date (latest >= yesterday)
        """
        logger.info("=== STARTUP BACKFILL: gap-only, priority symbols ===")
        start = datetime.now(timezone.utc)

        # Get tracked symbols, capped to avoid event loop saturation
        all_symbols = self._get_tracked_symbols()
        if not all_symbols:
            logger.warning("No tracked symbols found — skipping startup backfill")
            return {"skipped": True, "reason": "no_symbols"}

        # Priority cap: core ETFs first, then limit to 50 max
        _CORE = {"SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "NVDA", "TSLA",
                 "GOOGL", "AMZN", "META", "TLT", "GLD"}
        core = [s for s in all_symbols if s in _CORE]
        rest = [s for s in all_symbols if s not in _CORE]
        _MAX_STARTUP_SYMBOLS = 50
        symbols = core + rest[:_MAX_STARTUP_SYMBOLS - len(core)]

        # Query DuckDB for latest date per symbol to compute gap
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        gap_days = days  # default if no existing data
        try:
            conn = self.store._get_conn()
            placeholders = ",".join(["?" for _ in symbols])
            rows = conn.execute(
                f"SELECT symbol, MAX(date) as latest FROM daily_ohlcv "
                f"WHERE symbol IN ({placeholders}) GROUP BY symbol",
                symbols,
            ).fetchall()
            latest_map = {r[0]: r[1] for r in rows}

            # Filter out symbols already up-to-date
            need_backfill = []
            for s in symbols:
                latest = latest_map.get(s)
                if latest is None:
                    need_backfill.append(s)
                else:
                    # Convert to date if needed
                    if hasattr(latest, 'date'):
                        latest = latest.date()
                    if latest < yesterday:
                        need_backfill.append(s)

            if latest_map:
                # Use the largest gap across all symbols that need updating
                min_latest = min(
                    (v.date() if hasattr(v, 'date') else v
                     for v in latest_map.values()),
                    default=None,
                )
                if min_latest:
                    gap_days = (datetime.now(timezone.utc).date() - min_latest).days + 1
                    gap_days = max(gap_days, 5)  # at least 5 days

            skipped = len(symbols) - len(need_backfill)
            if skipped:
                logger.info(
                    "Startup backfill: %d symbols up-to-date, %d need data (gap=%d days)",
                    skipped, len(need_backfill), gap_days,
                )
            symbols = need_backfill
        except Exception as e:
            logger.warning("Gap detection failed, falling back to full backfill: %s", e)

        if not symbols:
            logger.info("=== STARTUP BACKFILL: all symbols up-to-date, nothing to do ===")
            return {"skipped": True, "reason": "up_to_date", "symbol_count": 0}

        logger.info("Backfilling %d symbols (%d days gap)...", len(symbols), gap_days)

        report = await self.ingest_all(symbols, days=gap_days)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        report["elapsed_seconds"] = round(elapsed, 1)
        report["symbol_count"] = len(symbols)

        logger.info(
            "=== STARTUP BACKFILL COMPLETE: %d symbols, %.1fs ===",
            len(symbols), elapsed,
        )
        return report

    async def run_daily_incremental(self) -> Dict[str, Any]:
        """Daily incremental backfill — fetch last 5 trading days.

        Scheduled at 4:30 AM ET to catch any gaps from the previous session.
        """
        logger.info("=== DAILY INCREMENTAL BACKFILL ===")
        symbols = self._get_tracked_symbols()
        if not symbols:
            return {"skipped": True}

        report = await self.ingest_all(symbols, days=7)  # 7 calendar days ~= 5 trading days
        logger.info("Daily incremental complete: %d symbols", len(symbols))
        return report

    async def run_weekly_indicator_refresh(self) -> int:
        """Weekly full indicator recompute — runs at midnight Sunday.

        Recomputes all technical indicators from stored OHLCV data.
        """
        logger.info("=== WEEKLY INDICATOR REFRESH ===")
        symbols = self._get_tracked_symbols()
        count = await asyncio.to_thread(
            self.compute_and_store_indicators, symbols, lookback_days=400
        )
        logger.info("Weekly indicator refresh: %d rows computed", count)
        return count

    def _get_tracked_symbols(self) -> List[str]:
        """Get the current list of tracked symbols from the symbol universe."""
        try:
            from app.modules.symbol_universe import get_tracked_symbols
            symbols = get_tracked_symbols()
            if symbols:
                return symbols
        except Exception:
            pass

        # Fallback: read from DuckDB
        try:
            conn = self.store._get_conn()
            df = conn.execute(
                "SELECT DISTINCT symbol FROM daily_ohlcv ORDER BY symbol"
            ).fetchdf()
            if not df.empty:
                return df["symbol"].tolist()
        except Exception:
            pass

        # Last resort: core symbols
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
            "SPY", "QQQ", "IWM", "DIA", "TLT", "GLD", "VIX",
        ]

    # ------------------------------------------------------------------
    # D1: Background scheduler loop
    # ------------------------------------------------------------------

    async def scheduler_loop(self) -> None:
        """Background loop that runs daily/weekly ingestion tasks.

        Schedule:
          - Daily at 4:30 AM ET: incremental backfill (7 calendar days)
          - Weekly at midnight Sunday: full indicator refresh (400 days)

        This runs forever and should be launched as a background task
        from main.py's lifespan.
        """
        import calendar

        logger.info("DataIngestion scheduler started")
        last_daily_date = None
        last_weekly_date = None

        while True:
            await asyncio.sleep(60)  # Check every minute
            try:
                # Use ET (UTC-5 / UTC-4 depending on DST)
                # Approximate: use UTC-5 (EST) for simplicity
                now_utc = datetime.now(timezone.utc)
                now_et = now_utc - timedelta(hours=5)
                today = now_et.date()
                hour = now_et.hour
                minute = now_et.minute
                weekday = now_et.weekday()  # 0=Monday, 6=Sunday

                # Daily at 4:30 AM ET (weekdays only)
                if (
                    hour == 4 and 30 <= minute < 31
                    and weekday < 5  # Mon-Fri
                    and last_daily_date != today
                ):
                    last_daily_date = today
                    logger.info("Scheduler: triggering daily incremental backfill")
                    try:
                        await self.run_daily_incremental()
                    except Exception:
                        logger.exception("Scheduler: daily backfill failed")

                # Weekly at midnight Sunday (weekday=6, hour=0)
                if (
                    weekday == 6 and hour == 0 and 0 <= minute < 1
                    and last_weekly_date != today
                ):
                    last_weekly_date = today
                    logger.info("Scheduler: triggering weekly indicator refresh")
                    try:
                        await self.run_weekly_indicator_refresh()
                    except Exception:
                        logger.exception("Scheduler: weekly refresh failed")

            except asyncio.CancelledError:
                logger.info("DataIngestion scheduler cancelled")
                return
            except Exception:
                logger.exception("DataIngestion scheduler error")


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------
data_ingestion = DataIngestionService()
