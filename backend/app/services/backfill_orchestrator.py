"""Backfill Orchestrator — D1 wrapper around DataIngestionService.

Gates TurboScanner until sufficient data exists (>= 50 rows per symbol
in daily_ohlcv). Tracks backfill status for the API dashboard.

Usage:
    from app.services.backfill_orchestrator import backfill_orchestrator
    status = await backfill_orchestrator.run()
    print(backfill_orchestrator.get_status())
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MIN_ROWS_PER_SYMBOL = 50  # TurboScanner gate threshold


class BackfillOrchestrator:
    """Coordinates startup backfill and gates TurboScanner readiness."""

    def __init__(self):
        self._status = "idle"  # idle | running | complete | failed
        self._started_at: Optional[float] = None
        self._completed_at: Optional[float] = None
        self._report: Dict[str, Any] = {}
        self._symbol_row_counts: Dict[str, int] = {}
        self._gated_symbols: List[str] = []  # Symbols below threshold
        self._ready_symbols: List[str] = []  # Symbols above threshold
        self._turbo_scanner_ready = False
        self._error: Optional[str] = None

    async def run(self, days: int = 252) -> Dict[str, Any]:
        """Run the full backfill orchestration.

        1. Trigger data_ingestion.run_startup_backfill()
        2. Check row counts per symbol in daily_ohlcv
        3. Gate TurboScanner if any symbol has < 50 rows

        Returns:
            Status report dict.
        """
        if self._status == "running":
            logger.warning("Backfill already running — skipping")
            return {"status": "already_running"}

        self._status = "running"
        self._started_at = time.time()
        self._error = None

        logger.info("=== BACKFILL ORCHESTRATOR: starting %d-day backfill ===", days)

        try:
            from app.services.data_ingestion import data_ingestion
            self._report = await data_ingestion.run_startup_backfill(days=days)

            # Check row counts per symbol
            await self._check_row_counts()

            # Gate TurboScanner
            self._evaluate_turbo_gate()

            self._status = "complete"
            self._completed_at = time.time()
            elapsed = self._completed_at - self._started_at

            logger.info(
                "=== BACKFILL ORCHESTRATOR COMPLETE: %.1fs, %d ready, %d gated, turbo=%s ===",
                elapsed, len(self._ready_symbols), len(self._gated_symbols),
                self._turbo_scanner_ready,
            )

            return self.get_status()

        except Exception as e:
            self._status = "failed"
            self._error = str(e)
            self._completed_at = time.time()
            logger.exception("Backfill orchestrator failed: %s", e)
            return self.get_status()

    async def _check_row_counts(self) -> None:
        """Query DuckDB for row counts per symbol in daily_ohlcv."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            df = await asyncio.to_thread(
                lambda: conn.execute(
                    "SELECT symbol, COUNT(*) as cnt FROM daily_ohlcv GROUP BY symbol"
                ).fetchdf()
            )

            self._symbol_row_counts = {}
            if not df.empty:
                for _, row in df.iterrows():
                    self._symbol_row_counts[row["symbol"]] = int(row["cnt"])
        except Exception as e:
            logger.warning("Row count check failed: %s", e)

    def _evaluate_turbo_gate(self) -> None:
        """Determine which symbols have enough data for TurboScanner."""
        self._ready_symbols = []
        self._gated_symbols = []

        for symbol, count in self._symbol_row_counts.items():
            if count >= MIN_ROWS_PER_SYMBOL:
                self._ready_symbols.append(symbol)
            else:
                self._gated_symbols.append(symbol)

        self._turbo_scanner_ready = (
            len(self._ready_symbols) > 0 and len(self._gated_symbols) == 0
        )

        if self._gated_symbols:
            logger.warning(
                "TurboScanner GATED: %d symbols have < %d rows: %s",
                len(self._gated_symbols), MIN_ROWS_PER_SYMBOL,
                self._gated_symbols[:10],
            )
        else:
            logger.info(
                "TurboScanner READY: all %d symbols have >= %d rows",
                len(self._ready_symbols), MIN_ROWS_PER_SYMBOL,
            )

    @property
    def is_turbo_ready(self) -> bool:
        """Whether TurboScanner has enough data to operate."""
        return self._turbo_scanner_ready

    def get_status(self) -> Dict[str, Any]:
        """Return backfill status for the API."""
        elapsed = None
        if self._started_at:
            end = self._completed_at or time.time()
            elapsed = round(end - self._started_at, 1)

        return {
            "status": self._status,
            "started_at": (
                datetime.fromtimestamp(self._started_at, tz=timezone.utc).isoformat()
                if self._started_at else None
            ),
            "completed_at": (
                datetime.fromtimestamp(self._completed_at, tz=timezone.utc).isoformat()
                if self._completed_at else None
            ),
            "elapsed_seconds": elapsed,
            "turbo_scanner_ready": self._turbo_scanner_ready,
            "ready_symbols": len(self._ready_symbols),
            "gated_symbols": len(self._gated_symbols),
            "gated_symbol_list": self._gated_symbols[:20],
            "min_rows_threshold": MIN_ROWS_PER_SYMBOL,
            "total_symbols_checked": len(self._symbol_row_counts),
            "error": self._error,
            "ingestion_report": self._report,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
backfill_orchestrator = BackfillOrchestrator()
