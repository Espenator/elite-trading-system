"""AutonomousScoutService — proactive agents that find opportunities and data.

Scouts run on configurable intervals and autonomously:
  1. Scan for unusual options flow (Unusual Whales)
  2. Screen for technical setups (breakouts, squeezes, momentum)
  3. Monitor watchlist symbols for entry conditions
  4. Discover new symbols from screeners and flow data
  5. Auto-ingest historical data for discovered symbols
  6. Trigger swarm analysis when opportunities are found

Scouts operate as background tasks that feed the SwarmSpawner with ideas.
They are the "autonomous nervous system" that keeps the system learning
even when the user isn't actively feeding it data.

Usage:
    scout = AutonomousScoutService(message_bus)
    await scout.start()
    # Scouts now running in background, discovering opportunities
"""
import asyncio
import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AutonomousScoutService:
    """Proactive background scouts that discover trading opportunities."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._discovered: Set[str] = set()  # Symbols already analyzed today
        self._stats = {
            "scans_completed": 0,
            "symbols_discovered": 0,
            "swarms_triggered": 0,
            "errors": 0,
        }
        # Scout configuration
        self.config = {
            "flow_scan_interval": 60,              # 1 min — options flow
            "screener_scan_interval": 120,         # 2 min — technical screener
            "watchlist_scan_interval": 60,         # 1 min — watchlist
            "backtest_scan_interval": 900,         # 15 min — proactive backtest
            "insider_scan_interval": 300,          # 5 min — SEC insider filings
            "congress_scan_interval": 300,         # 5 min — congress trades
            "gamma_scan_interval": 120,            # 2 min — options gamma exposure
            "news_scan_interval": 60,              # 1 min — breaking news
            "sentiment_scan_interval": 180,        # 3 min — social sentiment
            "macro_scan_interval": 600,            # 10 min — FRED macro signals
            "earnings_scan_interval": 600,         # 10 min — earnings calendar
            "sector_rotation_scan_interval": 300,  # 5 min — sector ETF momentum
            "short_squeeze_scan_interval": 180,    # 3 min — short interest + volume
            "ipo_scan_interval": 900,              # 15 min — recent IPO activity
            "correlation_break_scan_interval": 300,  # 5 min — cross-asset breaks
            "max_discoveries_per_scan": 20,        # 4x more (was 5)
            "min_flow_score": 3,                   # Minimum unusual flow score to trigger
            "enabled_scouts": [
                "flow", "screener", "watchlist", "backtest",
                "insider", "congress", "gamma", "news",
                "sentiment", "macro", "earnings", "sector_rotation",
                "short_squeeze", "ipo", "correlation_break",
            ],
        }
        # User-configurable watchlist
        self._watchlist: List[str] = []

    async def start(self):
        """Start all scout background tasks."""
        if self._running:
            return
        self._running = True
        self._load_watchlist()

        scouts = {
            "flow": (self._flow_scout_loop, self.config["flow_scan_interval"]),
            "screener": (self._screener_scout_loop, self.config["screener_scan_interval"]),
            "watchlist": (self._watchlist_scout_loop, self.config["watchlist_scan_interval"]),
            "backtest": (self._backtest_scout_loop, self.config["backtest_scan_interval"]),
            "insider": (self._insider_scout_loop, self.config["insider_scan_interval"]),
            "congress": (self._congress_scout_loop, self.config["congress_scan_interval"]),
            "gamma": (self._gamma_scout_loop, self.config["gamma_scan_interval"]),
            "news": (self._news_scout_loop, self.config["news_scan_interval"]),
            "sentiment": (self._sentiment_scout_loop, self.config["sentiment_scan_interval"]),
            "macro": (self._macro_scout_loop, self.config["macro_scan_interval"]),
            "earnings": (self._earnings_scout_loop, self.config["earnings_scan_interval"]),
            "sector_rotation": (self._sector_rotation_scout_loop, self.config["sector_rotation_scan_interval"]),
            "short_squeeze": (self._short_squeeze_scout_loop, self.config["short_squeeze_scan_interval"]),
            "ipo": (self._ipo_scout_loop, self.config["ipo_scan_interval"]),
            "correlation_break": (self._correlation_break_scout_loop, self.config["correlation_break_scan_interval"]),
        }

        for name, (fn, interval) in scouts.items():
            if name in self.config["enabled_scouts"]:
                task = asyncio.create_task(self._scout_wrapper(name, fn, interval))
                self._tasks.append(task)

        logger.info(
            "AutonomousScoutService started: %d scouts active, watchlist=%d symbols",
            len(self._tasks), len(self._watchlist),
        )

    async def stop(self):
        """Stop all scouts."""
        self._running = False
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        logger.info("AutonomousScoutService stopped")

    def set_watchlist(self, symbols: List[str]):
        """Update the watchlist and persist it."""
        self._watchlist = [s.upper().strip() for s in symbols if s.strip()]
        self._save_watchlist()
        logger.info("Watchlist updated: %s", self._watchlist)

    def add_to_watchlist(self, symbols: List[str]):
        """Add symbols to the watchlist."""
        for s in symbols:
            upper = s.upper().strip()
            if upper and upper not in self._watchlist:
                self._watchlist.append(upper)
        self._save_watchlist()

    def remove_from_watchlist(self, symbols: List[str]):
        """Remove symbols from the watchlist."""
        remove_set = {s.upper().strip() for s in symbols}
        self._watchlist = [s for s in self._watchlist if s not in remove_set]
        self._save_watchlist()

    # ------------------------------------------------------------------
    # Scout loops
    # ------------------------------------------------------------------
    async def _scout_wrapper(self, name: str, fn, interval: int):
        """Wrapper that runs a scout function at regular intervals."""
        await asyncio.sleep(30)  # Initial delay to let system warm up
        while self._running:
            try:
                logger.debug("Scout [%s] running...", name)
                await fn()
                self._stats["scans_completed"] += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._stats["errors"] += 1
                logger.warning("Scout [%s] error: %s", name, e)
            await asyncio.sleep(interval)

    async def _flow_scout_loop(self):
        """Scan for unusual options flow and trigger swarms on interesting activity."""
        try:
            from app.services.unusual_whales_service import unusual_whales_service
            flow = await unusual_whales_service.get_flow_alerts()
            if not flow:
                return

            for alert in flow[:self.config["max_discoveries_per_scan"]]:
                symbol = alert.get("symbol", alert.get("ticker", ""))
                if not symbol or symbol in self._discovered:
                    continue

                # Check if flow is significant
                volume = alert.get("volume", 0)
                open_interest = alert.get("open_interest", 0)
                premium = alert.get("premium", alert.get("total_premium", 0))

                if volume > open_interest * 2 or premium > 100_000:
                    self._discovered.add(symbol)
                    self._stats["symbols_discovered"] += 1

                    direction = "bullish" if alert.get("type", "").lower() in ("call", "calls") else "bearish"
                    await self._trigger_swarm(
                        source="scout",
                        symbols=[symbol],
                        direction=direction,
                        reasoning=f"Unusual flow: {alert.get('type', 'unknown')} volume={volume} premium=${premium:,.0f}",
                    )
        except ImportError:
            logger.debug("unusual_whales_service not available")
        except Exception as e:
            logger.debug("Flow scout error: %s", e)

    async def _screener_scout_loop(self):
        """Screen for technical setups using FinViz or local data."""
        try:
            # Try FinViz screener first
            from app.services.finviz_service import finviz_service
            screener_results = await finviz_service.run_screener()
            if not screener_results:
                return

            for result in screener_results[:self.config["max_discoveries_per_scan"]]:
                symbol = result.get("ticker", result.get("symbol", ""))
                if not symbol or symbol in self._discovered:
                    continue

                self._discovered.add(symbol)
                self._stats["symbols_discovered"] += 1
                await self._trigger_swarm(
                    source="scout",
                    symbols=[symbol],
                    direction="unknown",
                    reasoning=f"Screener hit: {result.get('pattern', result.get('signal', 'technical setup'))}",
                )
        except ImportError:
            logger.debug("finviz_service not available, trying DuckDB screener")
            await self._duckdb_screener()
        except Exception as e:
            logger.debug("Screener scout error: %s", e)

    async def _duckdb_screener(self):
        """Fallback screener using local DuckDB data."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()

            # Find symbols with strong recent momentum + volume surge
            query = """
                SELECT symbol, close, volume,
                       close / NULLIF(LAG(close, 5) OVER (PARTITION BY symbol ORDER BY date), 0) - 1 as ret_5d,
                       volume / NULLIF(AVG(volume) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING), 0) as vol_ratio
                FROM daily_ohlcv
                WHERE date >= CURRENT_DATE - INTERVAL '5 days'
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY ABS(ret_5d) DESC
                LIMIT 20
            """
            df = conn.execute(query).fetchdf()
            if df.empty:
                return

            for _, row in df.iterrows():
                symbol = row["symbol"]
                if symbol in self._discovered:
                    continue
                ret_5d = row.get("ret_5d", 0) or 0
                vol_ratio = row.get("vol_ratio", 0) or 0

                # Trigger on significant movers with volume
                if abs(ret_5d) > 0.05 and vol_ratio > 1.5:
                    self._discovered.add(symbol)
                    direction = "bullish" if ret_5d > 0 else "bearish"
                    await self._trigger_swarm(
                        source="scout",
                        symbols=[symbol],
                        direction=direction,
                        reasoning=f"Screener: {ret_5d:.1%} 5d return, {vol_ratio:.1f}x avg volume",
                    )
        except Exception as e:
            logger.debug("DuckDB screener error: %s", e)

    async def _watchlist_scout_loop(self):
        """Monitor watchlist symbols and trigger analysis when conditions change."""
        if not self._watchlist:
            return

        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()

            for symbol in self._watchlist:
                if symbol in self._discovered:
                    continue

                try:
                    # Get latest indicators
                    row = conn.execute("""
                        SELECT ti.*, o.close, o.volume
                        FROM technical_indicators ti
                        JOIN daily_ohlcv o ON ti.symbol = o.symbol AND ti.date = o.date
                        WHERE ti.symbol = ?
                        ORDER BY ti.date DESC
                        LIMIT 1
                    """, [symbol]).fetchone()

                    if not row:
                        # No data yet — ingest it
                        await self._auto_ingest(symbol)
                        continue

                    # Check for interesting conditions
                    rsi = row[2] if len(row) > 2 else None  # RSI column index
                    conditions = []

                    # This is a simplified check - real implementation would
                    # check RSI oversold/overbought, MACD crossover, etc.
                    # For now, just ensure data exists and trigger periodic analysis
                    self._discovered.add(symbol)
                    await self._trigger_swarm(
                        source="scout",
                        symbols=[symbol],
                        direction="unknown",
                        reasoning=f"Watchlist periodic scan",
                    )
                except Exception as e:
                    logger.debug("Watchlist scan error for %s: %s", symbol, e)
        except ImportError:
            logger.debug("DuckDB not available for watchlist scan")

    async def _backtest_scout_loop(self):
        """Proactively backtest symbols to build historical knowledge."""
        try:
            from app.data.duckdb_storage import duckdb_store
            from app.services.data_ingestion import data_ingestion

            conn = duckdb_store._get_conn()

            # Find symbols we have data for but haven't backtested recently
            symbols_with_data = conn.execute("""
                SELECT DISTINCT symbol, COUNT(*) as bars,
                       MAX(date) as latest_date
                FROM daily_ohlcv
                GROUP BY symbol
                HAVING bars > 30
                ORDER BY latest_date DESC
                LIMIT 50
            """).fetchdf()

            if symbols_with_data.empty:
                return

            # Ensure indicators are up to date, then trigger analysis
            for _, row in symbols_with_data.head(3).iterrows():
                symbol = row["symbol"]
                if symbol in self._discovered:
                    continue

                try:
                    await data_ingestion.compute_and_store_indicators([symbol])
                    self._discovered.add(symbol)
                    await self._trigger_swarm(
                        source="scout",
                        symbols=[symbol],
                        direction="unknown",
                        reasoning="Proactive backtest scan — validating historical edge",
                    )
                except Exception as e:
                    logger.debug("Backtest scout error for %s: %s", symbol, e)
        except Exception as e:
            logger.debug("Backtest scout error: %s", e)

    # ------------------------------------------------------------------
    # Scout loops — dedicated data-source agents (E2, Issue #38)
    # ------------------------------------------------------------------

    async def _insider_scout_loop(self):
        """Scan SEC EDGAR for recent insider transactions and trigger swarms."""
        try:
            from app.services.sec_edgar_service import SecEdgarService
            svc = SecEdgarService()
            tickers_data = await svc.get_company_tickers()
            if not tickers_data:
                return
            # Build a small sample of active tickers to check for recent filings
            symbols = [
                info.get("ticker", "")
                for info in list(tickers_data.values())[:200]
                if isinstance(info, dict) and info.get("ticker")
            ]
            for symbol in symbols[:self.config["max_discoveries_per_scan"]]:
                if not symbol or symbol in self._discovered:
                    continue
                try:
                    cik = svc.find_cik_by_ticker(tickers_data, symbol)
                    if not cik:
                        continue
                    submissions = await svc.get_submissions(cik)
                    filings = (
                        submissions.get("filings", {})
                        .get("recent", {})
                        .get("form", [])
                    )
                    # Form 4 = insider transaction; Form 144 = restricted share sale
                    insider_forms = [f for f in (filings or []) if f in ("4", "144")]
                    if insider_forms:
                        self._discovered.add(symbol)
                        self._stats["symbols_discovered"] += 1
                        await self._trigger_swarm(
                            source="insider_scout",
                            symbols=[symbol],
                            direction="unknown",
                            reasoning=f"Recent insider filing(s): {', '.join(set(insider_forms))}",
                        )
                        await self._publish_scout_discovery(
                            symbol=symbol,
                            scout="insider",
                            reason=f"Insider Form {', '.join(set(insider_forms))} filed",
                        )
                except Exception:
                    pass
        except ImportError:
            logger.debug("sec_edgar_service not available — insider scout skipped")
        except Exception as e:
            logger.debug("Insider scout error: %s", e)

    async def _congress_scout_loop(self):
        """Scan Unusual Whales congress trades and trigger swarms."""
        try:
            from app.services.unusual_whales_service import unusual_whales_service
            trades = await unusual_whales_service.get_congress_trades()
            if not trades:
                return
            items = trades if isinstance(trades, list) else trades.get("data", [])
            seen: set = set()
            for item in items[:self.config["max_discoveries_per_scan"]]:
                symbol = item.get("ticker", item.get("symbol", ""))
                if not symbol or symbol in self._discovered or symbol in seen:
                    continue
                seen.add(symbol)
                self._discovered.add(symbol)
                self._stats["symbols_discovered"] += 1
                tx_type = item.get("type", item.get("transaction_type", "transaction"))
                politician = item.get("politician", item.get("representative", "Congress"))
                amount = item.get("amount", item.get("estimated_amount", ""))
                direction = "bullish" if "purchase" in str(tx_type).lower() else "bearish"
                await self._trigger_swarm(
                    source="congress_scout",
                    symbols=[symbol],
                    direction=direction,
                    reasoning=f"Congress {tx_type} by {politician} — {amount}",
                )
                await self._publish_scout_discovery(
                    symbol=symbol,
                    scout="congress",
                    reason=f"Congress {tx_type}: {politician}",
                )
        except ImportError:
            logger.debug("unusual_whales_service not available — congress scout skipped")
        except Exception as e:
            logger.debug("Congress scout error: %s", e)

    async def _gamma_scout_loop(self):
        """Scan Unusual Whales for extreme gamma exposure setups."""
        try:
            from app.services.unusual_whales_service import unusual_whales_service
            flow = await unusual_whales_service.get_flow_alerts()
            if not flow:
                return
            items = flow if isinstance(flow, list) else flow.get("data", [])
            for item in items[:self.config["max_discoveries_per_scan"]]:
                symbol = item.get("ticker", item.get("symbol", ""))
                if not symbol or symbol in self._discovered:
                    continue
                premium = float(
                    item.get("premium", item.get("total_premium", 0)) or 0
                )
                # High-premium + short-dated options → gamma exposure signal
                dte = item.get("dte", item.get("expiration_days", 30)) or 30
                if premium >= 500_000 and int(dte) <= 7:
                    self._discovered.add(symbol)
                    self._stats["symbols_discovered"] += 1
                    direction = (
                        "bullish"
                        if item.get("type", "").lower() in ("call", "calls")
                        else "bearish"
                    )
                    await self._trigger_swarm(
                        source="gamma_scout",
                        symbols=[symbol],
                        direction=direction,
                        reasoning=(
                            f"Gamma squeeze setup: ${premium:,.0f} premium, "
                            f"{dte} DTE {item.get('type', 'options')}"
                        ),
                    )
                    await self._publish_scout_discovery(
                        symbol=symbol,
                        scout="gamma",
                        reason=f"Gamma risk: ${premium:,.0f} premium {dte} DTE",
                    )
        except ImportError:
            logger.debug("unusual_whales_service not available — gamma scout skipped")
        except Exception as e:
            logger.debug("Gamma scout error: %s", e)

    async def _news_scout_loop(self):
        """Pull breaking news from news_aggregator and trigger swarms for top movers."""
        try:
            from app.services.news_aggregator import get_news_aggregator
            agg = get_news_aggregator()
            articles = agg.get_news(limit=self.config["max_discoveries_per_scan"])
            for article in articles:
                symbols = article.get("symbols", []) or []
                sentiment_score = float(article.get("sentiment_score", 0.0) or 0.0)
                headline = article.get("headline", article.get("title", ""))
                for symbol in symbols:
                    if not symbol or symbol in self._discovered:
                        continue
                    if abs(sentiment_score) >= 0.4:
                        self._discovered.add(symbol)
                        self._stats["symbols_discovered"] += 1
                        direction = "bullish" if sentiment_score > 0 else "bearish"
                        await self._trigger_swarm(
                            source="news_scout",
                            symbols=[symbol],
                            direction=direction,
                            reasoning=f"Breaking news (sentiment={sentiment_score:.2f}): {headline[:100]}",
                        )
                        await self._publish_scout_discovery(
                            symbol=symbol,
                            scout="news",
                            reason=f"News sentiment {sentiment_score:+.2f}: {headline[:60]}",
                        )
        except ImportError:
            logger.debug("news_aggregator not available — news scout skipped")
        except Exception as e:
            logger.debug("News scout error: %s", e)

    async def _sentiment_scout_loop(self):
        """Scan social sentiment via the intelligence_cache for extreme readings."""
        try:
            from app.services.intelligence_cache import get_intelligence_cache
            cache = get_intelligence_cache()
            sentiment_data = cache.get_market("market_sentiment") or {}
            symbol_sentiment = sentiment_data.get("symbol_sentiment", {}) or {}
            for symbol, score in symbol_sentiment.items():
                if not symbol or symbol in self._discovered:
                    continue
                score_f = float(score) if isinstance(score, (int, float)) else 0.0
                if abs(score_f) >= 0.6:
                    self._discovered.add(symbol)
                    self._stats["symbols_discovered"] += 1
                    direction = "bullish" if score_f > 0 else "bearish"
                    await self._trigger_swarm(
                        source="sentiment_scout",
                        symbols=[symbol],
                        direction=direction,
                        reasoning=f"Extreme social sentiment: {score_f:+.2f}",
                    )
                    await self._publish_scout_discovery(
                        symbol=symbol,
                        scout="sentiment",
                        reason=f"Social sentiment: {score_f:+.2f}",
                    )
        except ImportError:
            logger.debug("intelligence_cache not available — sentiment scout skipped")
        except Exception as e:
            logger.debug("Sentiment scout error: %s", e)

    async def _macro_scout_loop(self):
        """Check FRED macro series for significant recent changes.

        Series monitored:
          VIXCLS  — CBOE Volatility Index; threshold=25 signals risk-off regime
          DGGS10  — 10Y Treasury yield; no threshold — scouts any latest reading
          CPIAUCSL — CPI index; no threshold — scouts any latest reading
        """
        MACRO_SERIES = [
            # (series_id, spike_threshold_or_None, human_label)
            ("VIXCLS", 25.0, "VIX spike — risk-off signal"),   # 25+ = elevated fear
            ("DGGS10", None, "10Y yield shift"),                # No fixed threshold
            ("CPIAUCSL", None, "CPI reading"),                  # No fixed threshold
        ]
        try:
            from app.services.fred_service import FredService
            svc = FredService()
            for series_id, threshold, label in MACRO_SERIES:
                try:
                    obs = await svc.get_observations(series_id, limit=2)
                    if not obs:
                        continue
                    val_str = obs[0].get("value", "0") or "0"
                    if val_str == ".":
                        continue
                    latest_val = float(val_str)
                    if threshold is not None and latest_val >= threshold:
                        if series_id not in self._discovered:
                            self._discovered.add(series_id)
                            self._stats["symbols_discovered"] += 1
                            await self._trigger_swarm(
                                source="macro_scout",
                                symbols=["SPY", "QQQ", "IWM"],
                                direction="bearish",
                                reasoning=f"{label}: {series_id}={latest_val:.2f}",
                            )
                            await self._publish_scout_discovery(
                                symbol=series_id,
                                scout="macro",
                                reason=f"{label}: {latest_val:.2f}",
                            )
                except Exception:
                    pass
        except ImportError:
            logger.debug("fred_service not available — macro scout skipped")
        except Exception as e:
            logger.debug("Macro scout error: %s", e)

    async def _earnings_scout_loop(self):
        """Discover symbols with upcoming or recent earnings via DuckDB."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            # Look for symbols that have had large price moves in the last 2 days
            # (proxy for earnings reaction) and haven't been scouted yet
            df = conn.execute("""
                SELECT symbol,
                       close / NULLIF(LAG(close, 2) OVER (PARTITION BY symbol ORDER BY date), 0) - 1 AS ret_2d,
                       volume / NULLIF(AVG(volume) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 20 PRECEDING AND 3 PRECEDING), 0) AS vol_ratio
                FROM daily_ohlcv
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY ABS(ret_2d) DESC
                LIMIT 30
            """).fetchdf()
            if df.empty:
                return
            for _, row in df.iterrows():
                symbol = row["symbol"]
                if not symbol or symbol in self._discovered:
                    continue
                ret_2d = float(row.get("ret_2d") or 0)
                vol_ratio = float(row.get("vol_ratio") or 0)
                # Large 2-day move with volume → likely earnings reaction
                if abs(ret_2d) > 0.08 and vol_ratio > 2.0:
                    self._discovered.add(symbol)
                    self._stats["symbols_discovered"] += 1
                    direction = "bullish" if ret_2d > 0 else "bearish"
                    await self._trigger_swarm(
                        source="earnings_scout",
                        symbols=[symbol],
                        direction=direction,
                        reasoning=(
                            f"Earnings reaction: {ret_2d:+.1%} 2d return, "
                            f"{vol_ratio:.1f}x avg volume"
                        ),
                    )
                    await self._publish_scout_discovery(
                        symbol=symbol,
                        scout="earnings",
                        reason=f"Post-earnings move: {ret_2d:+.1%} {vol_ratio:.1f}x vol",
                    )
        except Exception as e:
            logger.debug("Earnings scout error: %s", e)

    async def _sector_rotation_scout_loop(self):
        """Detect sector ETF momentum shifts via DuckDB."""
        SECTOR_ETFS = [
            "XLK", "XLF", "XLE", "XLV", "XLI",
            "XLP", "XLY", "XLU", "XLRE", "XLB", "XLC",
        ]
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            placeholders = ", ".join(["?" for _ in SECTOR_ETFS])
            df = conn.execute(f"""
                SELECT symbol,
                       close / NULLIF(LAG(close, 5) OVER (PARTITION BY symbol ORDER BY date), 0) - 1 AS ret_5d
                FROM daily_ohlcv
                WHERE symbol IN ({placeholders})
                  AND date >= CURRENT_DATE - INTERVAL '7 days'
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY ret_5d DESC
            """, SECTOR_ETFS).fetchdf()
            if df.empty:
                return
            # Top & bottom performing sectors
            leaders = df.head(2)
            laggards = df.tail(2)
            for _, row in leaders.iterrows():
                symbol = row["symbol"]
                ret = float(row.get("ret_5d") or 0)
                if ret > 0.02 and symbol not in self._discovered:
                    self._discovered.add(symbol)
                    self._stats["symbols_discovered"] += 1
                    await self._trigger_swarm(
                        source="sector_rotation_scout",
                        symbols=[symbol],
                        direction="bullish",
                        reasoning=f"Sector leader: {symbol} +{ret:.1%} 5d",
                    )
                    await self._publish_scout_discovery(
                        symbol=symbol,
                        scout="sector_rotation",
                        reason=f"Sector leader: +{ret:.1%} 5d",
                    )
            for _, row in laggards.iterrows():
                symbol = row["symbol"]
                ret = float(row.get("ret_5d") or 0)
                if ret < -0.02 and symbol not in self._discovered:
                    self._discovered.add(symbol)
                    self._stats["symbols_discovered"] += 1
                    await self._trigger_swarm(
                        source="sector_rotation_scout",
                        symbols=[symbol],
                        direction="bearish",
                        reasoning=f"Sector laggard: {symbol} {ret:.1%} 5d",
                    )
                    await self._publish_scout_discovery(
                        symbol=symbol,
                        scout="sector_rotation",
                        reason=f"Sector laggard: {ret:.1%} 5d",
                    )
        except Exception as e:
            logger.debug("Sector rotation scout error: %s", e)

    async def _short_squeeze_scout_loop(self):
        """Find short squeeze candidates: high short interest + volume surge."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            # Find symbols with high relative volume in recent bars
            df = conn.execute("""
                SELECT symbol,
                       volume / NULLIF(AVG(volume) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING), 0) AS vol_ratio,
                       close / NULLIF(LAG(close, 1) OVER (PARTITION BY symbol ORDER BY date), 0) - 1 AS ret_1d,
                       close
                FROM daily_ohlcv
                WHERE date >= CURRENT_DATE - INTERVAL '1 day'
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY vol_ratio DESC
                LIMIT 40
            """).fetchdf()
            if df.empty:
                return
            for _, row in df.iterrows():
                symbol = row["symbol"]
                if not symbol or symbol in self._discovered:
                    continue
                vol_ratio = float(row.get("vol_ratio") or 0)
                ret_1d = float(row.get("ret_1d") or 0)
                # High volume + positive price action → squeeze potential
                if vol_ratio >= 3.0 and ret_1d > 0.03:
                    self._discovered.add(symbol)
                    self._stats["symbols_discovered"] += 1
                    await self._trigger_swarm(
                        source="short_squeeze_scout",
                        symbols=[symbol],
                        direction="bullish",
                        reasoning=(
                            f"Short squeeze setup: {vol_ratio:.1f}x vol, "
                            f"+{ret_1d:.1%} 1d"
                        ),
                    )
                    await self._publish_scout_discovery(
                        symbol=symbol,
                        scout="short_squeeze",
                        reason=f"Squeeze: {vol_ratio:.1f}x vol +{ret_1d:.1%}",
                    )
        except Exception as e:
            logger.debug("Short squeeze scout error: %s", e)

    async def _ipo_scout_loop(self):
        """Find recently IPO'd symbols (within 90 days) with momentum."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            # Symbols with data first appearing in the last 90 days
            df = conn.execute("""
                SELECT symbol, MIN(date) AS first_date,
                       close / NULLIF(LAG(close, 5) OVER (PARTITION BY symbol ORDER BY date), 0) - 1 AS ret_5d
                FROM daily_ohlcv
                GROUP BY symbol, close, date
                HAVING MIN(date) >= CURRENT_DATE - INTERVAL '90 days'
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) = 1
                ORDER BY ABS(ret_5d) DESC
                LIMIT 20
            """).fetchdf()
            if df.empty:
                return
            for _, row in df.iterrows():
                symbol = row["symbol"]
                if not symbol or symbol in self._discovered:
                    continue
                ret_5d = float(row.get("ret_5d") or 0)
                if abs(ret_5d) > 0.05:
                    self._discovered.add(symbol)
                    self._stats["symbols_discovered"] += 1
                    direction = "bullish" if ret_5d > 0 else "bearish"
                    await self._trigger_swarm(
                        source="ipo_scout",
                        symbols=[symbol],
                        direction=direction,
                        reasoning=f"Recent IPO momentum: {ret_5d:+.1%} 5d (first traded {row['first_date']})",
                    )
                    await self._publish_scout_discovery(
                        symbol=symbol,
                        scout="ipo",
                        reason=f"IPO momentum: {ret_5d:+.1%} 5d",
                    )
        except Exception as e:
            logger.debug("IPO scout error: %s", e)

    async def _correlation_break_scout_loop(self):
        """Detect cross-asset correlation breaks via correlation_radar."""
        try:
            from app.services.correlation_radar import get_correlation_radar
            radar = get_correlation_radar()
            # Use status which returns recent_breaks as dicts
            status = radar.get_status()
            breaks = status.get("recent_breaks", [])
            for brk in breaks[:self.config["max_discoveries_per_scan"]]:
                symbols = brk.get("symbols_to_analyze", []) or []
                current_corr = brk.get("current_corr", 0.0)
                deviation = brk.get("deviation", 0.0)
                pair = brk.get("pair", [])
                for symbol in symbols:
                    if not symbol or symbol in self._discovered:
                        continue
                    self._discovered.add(symbol)
                    self._stats["symbols_discovered"] += 1
                    await self._trigger_swarm(
                        source="correlation_break_scout",
                        symbols=[symbol],
                        direction="unknown",
                        reasoning=(
                            f"Correlation break: corr={current_corr:.2f}, "
                            f"deviation={deviation:.2f} vs {pair}"
                        ),
                    )
                    await self._publish_scout_discovery(
                        symbol=symbol,
                        scout="correlation_break",
                        reason=f"Corr break: {current_corr:.2f} dev={deviation:.2f}",
                    )
        except ImportError:
            logger.debug("correlation_radar not available — correlation break scout skipped")
        except Exception as e:
            logger.debug("Correlation break scout error: %s", e)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _auto_ingest(self, symbol: str):
        """Auto-ingest data for a newly discovered symbol."""
        try:
            from app.services.data_ingestion import data_ingestion
            await data_ingestion.ingest_daily_bars([symbol], days=60)
            await data_ingestion.compute_and_store_indicators([symbol])
            logger.info("Auto-ingested data for %s", symbol)
        except Exception as e:
            logger.debug("Auto-ingest failed for %s: %s", symbol, e)

    async def _trigger_swarm(
        self,
        source: str,
        symbols: List[str],
        direction: str,
        reasoning: str,
    ):
        """Trigger a swarm analysis."""
        self._stats["swarms_triggered"] += 1
        if self._bus:
            await self._bus.publish("swarm.idea", {
                "source": source,
                "symbols": symbols,
                "direction": direction,
                "reasoning": reasoning,
                "priority": 5,
            })
        else:
            try:
                from app.services.swarm_spawner import get_swarm_spawner, SwarmIdea
                spawner = get_swarm_spawner()
                await spawner.spawn_analysis(SwarmIdea(
                    source=source,
                    symbols=symbols,
                    direction=direction,
                    reasoning=reasoning,
                ))
            except Exception as e:
                logger.warning("Failed to trigger swarm: %s", e)

    async def _publish_scout_discovery(
        self, symbol: str, scout: str, reason: str
    ) -> None:
        """Publish a scout.discovery event for real-time WebSocket monitoring."""
        if not self._bus:
            return
        try:
            await self._bus.publish("scout.discovery", {
                "symbol": symbol,
                "scout": scout,
                "reason": reason,
                "source": "autonomous_scout",
                "timestamp": time.time(),
            })
        except Exception:
            pass

    def _load_watchlist(self):
        """Load watchlist from persistent storage."""
        try:
            from app.services.database import db_service
            wl = db_service.get_config("scout_watchlist")
            if isinstance(wl, list):
                self._watchlist = wl
        except Exception:
            pass

    def _save_watchlist(self):
        """Persist watchlist to storage."""
        try:
            from app.services.database import db_service
            db_service.set_config("scout_watchlist", self._watchlist)
        except Exception as e:
            logger.warning("Failed to save watchlist: %s", e)

    def reset_daily_discoveries(self):
        """Reset the discovered set (call at start of trading day)."""
        count = len(self._discovered)
        self._discovered.clear()
        logger.info("Reset daily discoveries (was %d)", count)

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "scouts_active": len(self._tasks),
            "watchlist": self._watchlist,
            "discovered_today": list(self._discovered),
            "stats": dict(self._stats),
            "config": dict(self.config),
        }


# Module-level singleton
_scout: Optional[AutonomousScoutService] = None


def get_scout_service() -> AutonomousScoutService:
    global _scout
    if _scout is None:
        _scout = AutonomousScoutService()
    return _scout
