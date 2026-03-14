"""SymbolPrepService — async symbol data prep with bounded concurrency and circuit breaker.

Consumes symbol.prep.requested, runs data_ingestion (bars + indicators) off the hot path,
publishes symbol.prep.ready. Used by SwarmSpawner so ingestion is not inline in the request path.
"""
import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

PREP_TIMEOUT = float(os.getenv("SYMBOL_PREP_TIMEOUT", "45.0"))
MAX_CONCURRENT_PREPS = int(os.getenv("SYMBOL_PREP_MAX_CONCURRENT", "5"))
CIRCUIT_FAILURE_THRESHOLD = 5
CIRCUIT_RESET_SECS = 60
BACKOFF_BASE_SECS = 1.0
MAX_BACKOFF_SECS = 30.0


class SymbolPrepService:
    """Prepares symbol data (OHLCV + indicators) via async queue and circuit breaker."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._workers: List[asyncio.Task] = []
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_PREPS)
        self._failure_count = 0
        self._last_failure_ts: Optional[float] = None
        self._circuit_open = False
        self._pending: Dict[str, asyncio.Future] = {}  # request_id -> Future that receives ready payload

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self._bus:
            await self._bus.subscribe("symbol.prep.requested", self._on_request)
        for i in range(MAX_CONCURRENT_PREPS):
            self._workers.append(asyncio.create_task(self._worker(i)))
        logger.info(
            "SymbolPrepService started: max_concurrent=%s timeout=%s",
            MAX_CONCURRENT_PREPS, PREP_TIMEOUT,
        )

    async def stop(self) -> None:
        self._running = False
        for w in self._workers:
            w.cancel()
        for w in self._workers:
            try:
                await w
            except asyncio.CancelledError:
                pass
        self._workers.clear()
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()
        logger.info("SymbolPrepService stopped")

    def _circuit_ok(self) -> bool:
        if not self._circuit_open:
            return True
        if self._last_failure_ts and (time.time() - self._last_failure_ts) > CIRCUIT_RESET_SECS:
            self._circuit_open = False
            self._failure_count = 0
            return True
        return False

    def _record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_ts = time.time()
        if self._failure_count >= CIRCUIT_FAILURE_THRESHOLD:
            self._circuit_open = True
            logger.warning("SymbolPrepService circuit OPEN after %d failures", self._failure_count)

    async def _on_request(self, data: Dict[str, Any]) -> None:
        request_id = data.get("request_id", "")
        symbols = data.get("symbols", [])
        if isinstance(symbols, str):
            symbols = [symbols]
        if not request_id or not symbols:
            return
        try:
            self._queue.put_nowait({"request_id": request_id, "symbols": symbols[:25], "data": data})
        except asyncio.QueueFull:
            logger.warning("SymbolPrepService queue full, dropping request_id=%s", request_id)
            if self._bus:
                await self._bus.publish("symbol.prep.ready", {
                    "request_id": request_id,
                    "symbols_ready": [],
                    "errors": ["queue_full"],
                    "degraded": True,
                })

    async def _worker(self, worker_id: int) -> None:
        while self._running:
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            async with self._semaphore:
                await self._do_prep(item)
            self._queue.task_done()

    async def _do_prep(self, item: Dict[str, Any]) -> None:
        request_id = item["request_id"]
        symbols = item["symbols"]
        payload: Dict[str, Any] = {
            "request_id": request_id,
            "symbols_ready": [],
            "errors": [],
            "degraded": False,
        }
        if not self._circuit_ok():
            payload["errors"].append("circuit_open")
            payload["degraded"] = True
            if self._bus:
                await self._bus.publish("symbol.prep.ready", payload)
            return

        backoff = BACKOFF_BASE_SECS
        for sym in symbols:
            try:
                await self._ingest_one(sym)
                payload["symbols_ready"].append(sym)
            except Exception as e:
                payload["errors"].append(f"{sym}: {e}")
                self._record_failure()
                logger.debug("Prep failed for %s: %s", sym, e)
                # Backoff before next symbol
                await asyncio.sleep(min(backoff, MAX_BACKOFF_SECS))
                backoff = min(backoff * 2, MAX_BACKOFF_SECS)
        if self._bus:
            await self._bus.publish("symbol.prep.ready", payload)
        # Wake any waiter for this request_id
        fut = self._pending.pop(request_id, None)
        if fut and not fut.done():
            fut.set_result(payload)

    async def _ingest_one(self, symbol: str) -> None:
        from app.services.data_ingestion import data_ingestion
        await data_ingestion.ingest_daily_bars([symbol], days=60)
        await asyncio.to_thread(data_ingestion.compute_and_store_indicators, [symbol])

    async def request_prep_and_wait(
        self, request_id: str, symbols: List[str], timeout: float = None, bus=None
    ) -> Dict[str, Any]:
        """Request prep, then wait for symbol.prep.ready (registers future before publish so worker can complete it)."""
        t = timeout if timeout is not None else PREP_TIMEOUT
        symbols = symbols[:25] if symbols else []
        fut = asyncio.get_running_loop().create_future()
        self._pending[request_id] = fut
        bus = bus or self._bus
        try:
            if bus:
                await bus.publish("symbol.prep.requested", {"request_id": request_id, "symbols": symbols})
            return await asyncio.wait_for(asyncio.shield(fut), timeout=t)
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            return {
                "request_id": request_id,
                "symbols_ready": [],
                "errors": ["timeout"],
                "degraded": True,
            }
        except asyncio.CancelledError:
            self._pending.pop(request_id, None)
            raise

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "queue_depth": self._queue.qsize(),
            "circuit_open": self._circuit_open,
            "failure_count": self._failure_count,
            "pending_requests": len(self._pending),
        }


# Module-level singleton
_prep_service: Optional[SymbolPrepService] = None


def get_symbol_prep_service(message_bus=None) -> SymbolPrepService:
    global _prep_service
    if _prep_service is None:
        _prep_service = SymbolPrepService(message_bus)
    return _prep_service
