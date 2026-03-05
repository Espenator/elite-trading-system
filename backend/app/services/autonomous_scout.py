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
            "flow_scan_interval": 60,        # 1 min (was 5 min) — 5x faster
            "screener_scan_interval": 120,   # 2 min (was 15 min) — 7x faster
            "watchlist_scan_interval": 60,   # 1 min (was 10 min) — 10x faster
            "backtest_scan_interval": 900,   # 15 min (was 1 hr) — 4x faster
            "max_discoveries_per_scan": 20,  # 4x more (was 5)
            "min_flow_score": 3,             # Minimum unusual flow score to trigger
            "enabled_scouts": ["flow", "screener", "watchlist", "backtest"],
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
