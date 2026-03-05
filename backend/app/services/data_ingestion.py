"""Data Ingestion Service — Pulls from all external APIs and persists to DuckDB.

This is the write-side orchestrator that feeds the analytics database.
market_data_agent.py calls this during each tick to persist data.

Data flow:
    Alpaca Market Data API -> daily_ohlcv
    ta library calculations -> technical_indicators
    Unusual Whales API     -> options_flow
    FRED API               -> macro_data
    Order fills            -> trade_outcomes

Usage:
    from app.services.data_ingestion import data_ingestion
    await data_ingestion.ingest_daily_bars(["AAPL", "MSFT"], days=252)
    await data_ingestion.ingest_all(["AAPL", "MSFT"])

Fixes Issue #25 Task 4.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)

# Alpaca Market Data API (separate from trading API)
ALPACA_DATA_BASE_URL = "https://data.alpaca.markets/v2"

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

        async with httpx.AsyncClient(timeout=30.0) as client:
            for symbol in symbols:
                try:
                    page_token = None
                    symbol_rows = []

                    while True:
                        params = {
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
                            f"{ALPACA_DATA_BASE_URL}/stocks/{symbol}/bars",
                            headers=headers,
                            params=params,
                        )

                        if resp.status_code != 200:
                            logger.warning(
                                "Alpaca bars %s: HTTP %s", symbol, resp.status_code
                            )
                            break

                        data = resp.json()
                        bars = data.get("bars") or []

                        for bar in bars:
                            symbol_rows.append({
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

                    all_rows.extend(symbol_rows)
                    results[symbol] = len(symbol_rows)
                    logger.info("Alpaca bars %s: %d days fetched", symbol, len(symbol_rows))

                except Exception as exc:
                    logger.error("Alpaca bars %s failed: %s", symbol, exc)
                    results[symbol] = 0

        if all_rows:
            df = pd.DataFrame(all_rows)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            self.store.upsert_ohlcv(df)
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

            self.store.upsert_options_flow(agg_df)
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
        try:
            for etf in ["SPY", "QQQ"]:
                etf_df = self.store.query(f"""
                    SELECT date, close as {etf.lower()}_close
                    FROM daily_ohlcv
                    WHERE symbol = ?
                    ORDER BY date
                """, [etf]).fetchdf()
                if not etf_df.empty:
                    etf_df["date"] = pd.to_datetime(etf_df["date"]).dt.date
                    df = df.merge(etf_df, on="date", how="left", suffixes=("", "_ohlcv"))
                    ohlcv_col = f"{etf.lower()}_close_ohlcv"
                    if ohlcv_col in df.columns:
                        df[f"{etf.lower()}_close"] = df[f"{etf.lower()}_close"].fillna(df[ohlcv_col])
                        df = df.drop(columns=[ohlcv_col])
        except Exception as exc:
            logger.debug("SPY/QQQ merge from DuckDB failed: %s", exc)

        # Ensure column order matches macro_data schema
        macro_cols = ["date", "vix_close", "dxy_close", "us10y_yield",
                      "fed_funds_rate", "spy_close", "qqq_close", "breadth_ratio"]
        for col in macro_cols:
            if col not in df.columns:
                df[col] = np.nan
        df = df[macro_cols]

        self.store.upsert_macro(df)
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

        count = 0
        for symbol in buys:
            for buy in buys[symbol]:
                matching_sells = [
                    s for s in sells.get(symbol, [])
                    if s["date"] >= buy["date"]
                ]
                if matching_sells:
                    sell = matching_sells[0]
                    pnl = (sell["price"] - buy["price"]) * buy["qty"]
                    r_mult = (sell["price"] - buy["price"]) / (buy["price"] + 1e-10)

                    self.store.insert_trade_outcome({
                        "symbol": symbol,
                        "direction": "LONG",
                        "entry_date": buy["date"],
                        "exit_date": sell["date"],
                        "entry_price": buy["price"],
                        "exit_price": sell["price"],
                        "shares": int(round(buy["qty"])),  # DB column is INTEGER; fractional rounded
                        "pnl": pnl,
                        "r_multiple": r_mult,
                        "outcome": "WIN" if pnl > 0 else "LOSS",
                        "resolved": True,
                        "resolved_at": datetime.utcnow().isoformat(),
                    })
                    count += 1
                    sells[symbol].remove(sell)

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
        report["indicators"] = self.compute_and_store_indicators(symbols)

        # 3. Options flow
        report["options_flow"] = await self.ingest_options_flow()

        # 4. Macro
        report["macro"] = await self.ingest_macro_data(days=days)

        # 5. Trade outcomes
        report["trade_outcomes"] = await self.ingest_trade_outcomes()

        # Health check
        report["duckdb_health"] = self.store.health_check()

        logger.info("Full ingestion complete: %s", report)
        return report


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------
data_ingestion = DataIngestionService()
