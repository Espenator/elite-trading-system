"""SwarmSpawner — spawns analysis swarms from ideas, signals, and data feeds.

When an idea arrives (from Discord, YouTube, user input, or autonomous scouts),
the SwarmSpawner creates a targeted analysis swarm: a group of agents that
evaluate the idea, backtest it, and produce an actionable recommendation.

Architecture:
    Idea Source (Discord/YouTube/User/Scout)
        -> SwarmSpawner.spawn_analysis()
            -> Data ingestion (fetch OHLCV + indicators)
            -> Council evaluation (relevant agents only)
            -> Backtest validation (if historical data available)
            -> Result published to MessageBus + stored in DB

Usage:
    spawner = SwarmSpawner(message_bus)
    await spawner.start()
    await spawner.spawn_analysis(SwarmIdea(
        source="discord",
        symbols=["AAPL"],
        direction="bullish",
        reasoning="Unusual call buying 5x normal volume",
    ))
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IdeaSource(str, Enum):
    DISCORD = "discord"
    YOUTUBE = "youtube"
    USER = "user"
    SCOUT = "scout"
    NEWS = "news"
    URL = "url"


class SwarmStatus(str, Enum):
    QUEUED = "queued"
    INGESTING = "ingesting_data"
    ANALYZING = "analyzing"
    BACKTESTING = "backtesting"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class SwarmIdea:
    """An idea that triggers a swarm analysis."""
    source: str
    symbols: List[str]
    direction: str = "unknown"          # bullish/bearish/unknown
    reasoning: str = ""
    raw_content: str = ""               # Original message/transcript text
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5                   # 1=highest, 10=lowest
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SwarmResult:
    """Result of a swarm analysis."""
    idea_id: str
    symbols: List[str]
    source: str
    status: SwarmStatus
    council_verdict: Optional[Dict[str, Any]] = None
    backtest_result: Optional[Dict[str, Any]] = None
    data_quality: Optional[Dict[str, Any]] = None
    recommendation: str = "no_action"   # buy/sell/watch/no_action
    confidence: float = 0.0
    reasoning: str = ""
    duration_ms: float = 0.0
    created_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idea_id": self.idea_id,
            "symbols": self.symbols,
            "source": self.source,
            "status": self.status.value,
            "council_verdict": self.council_verdict,
            "backtest_result": self.backtest_result,
            "data_quality": self.data_quality,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class SwarmSpawner:
    """Spawns targeted analysis swarms from ideas."""

    MAX_CONCURRENT_SWARMS = 20   # Scaled 4x (was 5) — local LLMs are free
    MAX_HISTORY = 1000           # Scaled 5x (was 200)

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=2000)  # Scaled 20x (was 100)
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._active_swarms: Dict[str, SwarmStatus] = {}
        self._results: List[SwarmResult] = []
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_SWARMS)
        self._stats = {
            "total_spawned": 0,
            "total_completed": 0,
            "total_failed": 0,
            "by_source": {},
        }

    async def start(self):
        """Start the swarm worker pool."""
        if self._running:
            return
        self._running = True
        # Subscribe to triage-escalated ideas only (E3 quality gate).
        # Previously subscribed to raw swarm.idea which caused full 17-agent council
        # to run on every unfiltered idea.  Now only ideas that have passed
        # IdeaTriageService's scoring threshold (≥40 by default) reach here.
        # swarm.prescreened is no longer subscribed: SwarmSpawner now receives all
        # triage-passed ideas directly via triage.escalated, so HyperSwarm
        # prescreened output is handled by the HyperSwarm→council path separately.
        if self._bus:
            await self._bus.subscribe("triage.escalated", self._on_idea_event)
        # Start worker tasks
        for i in range(self.MAX_CONCURRENT_SWARMS):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)
        logger.info("SwarmSpawner started with %d workers", self.MAX_CONCURRENT_SWARMS)

    async def stop(self):
        """Graceful shutdown."""
        self._running = False
        for w in self._workers:
            w.cancel()
        for w in self._workers:
            try:
                await w
            except asyncio.CancelledError:
                pass
        self._workers.clear()
        logger.info("SwarmSpawner stopped")

    async def spawn_analysis(self, idea: SwarmIdea) -> str:
        """Queue an idea for swarm analysis. Returns the idea ID."""
        try:
            self._queue.put_nowait(idea)
            self._active_swarms[idea.id] = SwarmStatus.QUEUED
            self._stats["total_spawned"] += 1
            src = idea.source
            self._stats["by_source"][src] = self._stats["by_source"].get(src, 0) + 1
            logger.info(
                "Swarm queued: id=%s source=%s symbols=%s direction=%s",
                idea.id, idea.source, idea.symbols, idea.direction,
            )
            # Also publish event
            if self._bus:
                await self._bus.publish("swarm.spawned", {
                    "idea_id": idea.id,
                    "source": idea.source,
                    "symbols": idea.symbols,
                    "direction": idea.direction,
                })
            return idea.id
        except asyncio.QueueFull:
            logger.warning("Swarm queue full — dropping idea %s", idea.id)
            return ""

    async def _worker(self, worker_id: int):
        """Worker loop that processes ideas from the queue."""
        while self._running:
            try:
                idea = await asyncio.wait_for(self._queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            async with self._semaphore:
                result = await self._run_swarm(idea, worker_id)
                self._results.append(result)
                # Trim history
                if len(self._results) > self.MAX_HISTORY:
                    self._results = self._results[-self.MAX_HISTORY:]
                self._queue.task_done()

    async def _run_swarm(self, idea: SwarmIdea, worker_id: int) -> SwarmResult:
        """Execute a full swarm analysis for one idea."""
        start = time.monotonic()
        result = SwarmResult(
            idea_id=idea.id,
            symbols=idea.symbols,
            source=idea.source,
            status=SwarmStatus.INGESTING,
            created_at=idea.created_at,
        )

        try:
            # Phase 1: Data Ingestion — ensure we have fresh data for the symbols
            self._active_swarms[idea.id] = SwarmStatus.INGESTING
            data_quality = await self._ingest_data(idea.symbols)
            result.data_quality = data_quality

            # Phase 2: Council Analysis — run relevant agents
            self._active_swarms[idea.id] = SwarmStatus.ANALYZING
            verdict = await self._run_council(idea)
            result.council_verdict = verdict

            # Phase 3: Backtest Validation — if we have historical signals
            self._active_swarms[idea.id] = SwarmStatus.BACKTESTING
            bt_result = await self._run_backtest(idea)
            result.backtest_result = bt_result

            # Phase 4: Synthesize recommendation
            result.recommendation, result.confidence, result.reasoning = (
                self._synthesize(idea, verdict, bt_result)
            )
            result.status = SwarmStatus.COMPLETE
            self._stats["total_completed"] += 1

        except Exception as e:
            logger.exception("Swarm %s failed: %s", idea.id, e)
            result.status = SwarmStatus.FAILED
            result.reasoning = f"Swarm analysis failed: {e}"
            self._stats["total_failed"] += 1

        elapsed = (time.monotonic() - start) * 1000
        result.duration_ms = round(elapsed, 1)
        result.completed_at = datetime.now(timezone.utc).isoformat()
        self._active_swarms[idea.id] = result.status

        # Publish result
        if self._bus:
            await self._bus.publish("swarm.result", result.to_dict())

        logger.info(
            "Swarm %s complete: recommendation=%s confidence=%.2f duration=%.0fms",
            idea.id, result.recommendation, result.confidence, elapsed,
        )
        return result

    async def _ingest_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Ensure we have recent OHLCV + indicators for the symbols."""
        quality = {"symbols_requested": len(symbols), "symbols_ready": 0, "errors": []}
        try:
            from app.services.data_ingestion import data_ingestion
            for sym in symbols[:25]:  # Cap at 25 symbols per swarm (was 10)
                try:
                    await data_ingestion.ingest_daily_bars([sym], days=60)
                    await data_ingestion.compute_and_store_indicators([sym])
                    quality["symbols_ready"] += 1
                except Exception as e:
                    quality["errors"].append(f"{sym}: {e}")
                    logger.debug("Ingest failed for %s: %s", sym, e)
        except ImportError:
            quality["errors"].append("data_ingestion module not available")
        return quality

    async def _run_council(self, idea: SwarmIdea) -> Optional[Dict[str, Any]]:
        """Run the council evaluation for the primary symbol."""
        if not idea.symbols:
            return None
        symbol = idea.symbols[0]
        try:
            from app.council.runner import run_council
            decision = await run_council(
                symbol=symbol,
                timeframe="1d",
                context={"swarm_idea": {
                    "source": idea.source,
                    "direction": idea.direction,
                    "reasoning": idea.reasoning,
                    "raw_content": idea.raw_content,
                }},
            )
            if hasattr(decision, "to_dict"):
                return decision.to_dict()
            return decision
        except Exception as e:
            logger.warning("Council evaluation failed for %s: %s", symbol, e)
            return {"error": str(e), "symbol": symbol}

    async def _run_backtest(self, idea: SwarmIdea) -> Optional[Dict[str, Any]]:
        """Run a quick backtest for the symbol if historical data exists."""
        if not idea.symbols:
            return None
        symbol = idea.symbols[0]
        try:
            from app.services.backtest_engine import backtest_engine
            from datetime import date, timedelta
            end = date.today().isoformat()
            start = (date.today() - timedelta(days=90)).isoformat()
            result = backtest_engine.run_backtest(
                symbol=symbol,
                start_date=start,
                end_date=end,
                strategy="composite",
            )
            # Strip large trade details for swarm result
            if isinstance(result, dict):
                result.pop("trades_detail", None)
            return result
        except Exception as e:
            logger.debug("Backtest skipped for %s: %s", symbol, e)
            return {"skipped": True, "reason": str(e)}

    def _synthesize(
        self,
        idea: SwarmIdea,
        verdict: Optional[Dict],
        backtest: Optional[Dict],
    ) -> tuple:
        """Combine council verdict + backtest into a recommendation."""
        recommendation = "no_action"
        confidence = 0.0
        reasons = []

        # Council verdict
        if verdict and not verdict.get("error"):
            council_dir = verdict.get("final_direction", "hold")
            council_conf = verdict.get("final_confidence", 0)
            vetoed = verdict.get("vetoed", False)
            if vetoed:
                reasons.append("Council VETOED this trade")
                return "no_action", 0.0, "; ".join(reasons)
            if council_dir in ("buy", "sell"):
                recommendation = council_dir
                confidence = council_conf
                reasons.append(f"Council says {council_dir} with {council_conf:.0%} confidence")
            else:
                reasons.append(f"Council says hold ({council_conf:.0%})")

        # Backtest validation
        if backtest and not backtest.get("error") and not backtest.get("skipped"):
            sharpe = backtest.get("sharpe", 0)
            winrate = backtest.get("winrate", 0)
            trades = backtest.get("trades", 0)
            if trades >= 5:
                if sharpe > 1.0 and winrate > 0.5:
                    confidence = min(1.0, confidence + 0.15)
                    reasons.append(f"Backtest supports: Sharpe={sharpe:.2f}, WR={winrate:.0%}")
                elif sharpe < 0:
                    confidence = max(0.0, confidence - 0.2)
                    reasons.append(f"Backtest warns: Sharpe={sharpe:.2f}")
            else:
                reasons.append(f"Backtest: insufficient history ({trades} trades)")

        # Idea direction alignment
        if idea.direction in ("bullish", "buy") and recommendation == "buy":
            confidence = min(1.0, confidence + 0.05)
            reasons.append("Idea direction aligns with council")
        elif idea.direction in ("bearish", "sell") and recommendation == "sell":
            confidence = min(1.0, confidence + 0.05)
            reasons.append("Idea direction aligns with council")

        if confidence < 0.3:
            recommendation = "watch"

        return recommendation, round(confidence, 3), "; ".join(reasons) if reasons else "Insufficient data"

    # --- Event handler ---
    async def _on_idea_event(self, data: Dict[str, Any]):
        """Handle swarm.idea events from the MessageBus."""
        idea = SwarmIdea(
            source=data.get("source", "unknown"),
            symbols=data.get("symbols", []),
            direction=data.get("direction", "unknown"),
            reasoning=data.get("reasoning", ""),
            raw_content=data.get("raw_content", ""),
            metadata=data.get("metadata", {}),
            priority=data.get("priority", 5),
        )
        await self.spawn_analysis(idea)

    # --- Status ---
    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "queue_depth": self._queue.qsize(),
            "active_swarms": dict(self._active_swarms),
            "stats": self._stats,
            "recent_results": [r.to_dict() for r in self._results[-10:]],
        }

    def get_result(self, idea_id: str) -> Optional[Dict[str, Any]]:
        for r in reversed(self._results):
            if r.idea_id == idea_id:
                return r.to_dict()
        return None

    def get_results(self, limit: int = 20, source: str = None) -> List[Dict[str, Any]]:
        results = self._results
        if source:
            results = [r for r in results if r.source == source]
        return [r.to_dict() for r in results[-limit:]]


# Module-level singleton
_spawner: Optional[SwarmSpawner] = None


def get_swarm_spawner() -> SwarmSpawner:
    global _spawner
    if _spawner is None:
        _spawner = SwarmSpawner()
    return _spawner
