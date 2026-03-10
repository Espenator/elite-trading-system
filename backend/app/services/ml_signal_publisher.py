"""ML Signal Publisher — feeds Stage-4 ML signals into the brain (signal.generated / swarm.idea).

Periodically reads stage4 signals from config store or DuckDB and publishes
them to the MessageBus so CouncilGate and the decision loop consume them
as first-class inputs (not dashboard-only).

Provenance: source=ml_api_stage4, confidence=prob/100, score 0-100.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SEC = 60
SOURCE = "ml_api_stage4"


class MLSignalPublisher:
    """Publish stage4 ML inferences to signal.generated and swarm.idea."""

    def __init__(self, message_bus=None, interval_sec: float = DEFAULT_INTERVAL_SEC):
        self._bus = message_bus
        self._interval_sec = interval_sec
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_publish_count = 0
        self._last_run_ts: float = 0.0

    async def start(self) -> None:
        if self._running or not self._bus:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("MLSignalPublisher started (interval=%.0fs, source=%s)", self._interval_sec, SOURCE)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("MLSignalPublisher stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._fetch_and_publish()
            except Exception as e:
                logger.debug("MLSignalPublisher tick error: %s", e)
            await asyncio.sleep(self._interval_sec)

    def _fetch_stage4_signals(self) -> List[Dict[str, Any]]:
        """Fetch stage4 signals from config store or DuckDB."""
        # 1) Config store (same source as GET /api/v1/ml-brain/signals/staged)
        try:
            from app.services.database import db_service
            data = db_service.get_config("ml_brain_staged_signals")
            if isinstance(data, list) and data:
                return data
        except Exception:
            pass

        # 2) DuckDB fallback if table exists
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            try:
                rows = conn.execute("""
                    SELECT symbol, direction, win_probability, created_at
                    FROM scanner_signals
                    WHERE stage = 4 AND win_probability >= 70
                    ORDER BY win_probability DESC
                    LIMIT 20
                """).fetchall()
                if rows:
                    return [
                        {
                            "symbol": r[0],
                            "dir": r[1],
                            "prob": float(r[2]) if r[2] is not None else 70.0,
                            "timestamp": r[3],
                        }
                        for r in rows
                    ]
            except Exception:
                pass
        except Exception:
            pass

        return []

    async def _fetch_and_publish(self) -> None:
        signals = self._fetch_stage4_signals()
        self._last_run_ts = time.time()
        count = 0
        for s in signals:
            symbol = (s.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            prob = float(s.get("prob") or s.get("win_probability") or 70.0)
            prob = max(0.0, min(100.0, prob))
            direction = (s.get("dir") or s.get("direction") or "buy").lower()
            if direction not in ("buy", "sell"):
                direction = "buy"

            # signal.generated: score 0-100, confidence 0-1
            payload = {
                "symbol": symbol,
                "score": round(prob, 1),
                "confidence": round(prob / 100.0, 4),
                "source": SOURCE,
                "priority": min(10, int(prob / 10)),
                "direction": direction,
                "regime": (s.get("regime") or "UNKNOWN"),
                "timestamp": time.time(),
            }
            if self._bus:
                await self._bus.publish("signal.generated", payload)
                count += 1

            # swarm.idea (optional) for triage/context
            idea = {
                "source": SOURCE,
                "symbols": [symbol],
                "direction": direction,
                "priority": payload["priority"],
                "reasoning": f"Stage4 ML win_prob={prob:.1f}%",
                "confidence": payload["confidence"],
            }
            if self._bus:
                await self._bus.publish("swarm.idea", idea)
        self._last_publish_count = count
        if count:
            logger.debug("MLSignalPublisher published %d stage4 signals", count)

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "source": SOURCE,
            "interval_sec": self._interval_sec,
            "last_publish_count": self._last_publish_count,
            "last_run_ts": self._last_run_ts,
        }


_publisher: MLSignalPublisher | None = None


def get_ml_signal_publisher(message_bus=None) -> MLSignalPublisher:
    global _publisher
    if _publisher is None:
        _publisher = MLSignalPublisher(message_bus=message_bus)
    return _publisher
