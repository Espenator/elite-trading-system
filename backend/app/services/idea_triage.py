"""IdeaTriageService — E3 continuous triage layer for the Embodier discovery pipeline.

Sits between discovery scouts and the HyperSwarm evaluation layer.  Subscribes
to ``swarm.idea``, deduplicates within a rolling time window, computes a
priority score for each idea, applies an adaptive escalation threshold, and
re-publishes only the best ideas to ``triage.escalated`` for downstream
micro-swarm analysis.

Pipeline position::

    Scouts / TurboScanner / NewsAgg
        → MessageBus("swarm.idea")
            → IdeaTriageService           ← this module
                → MessageBus("triage.escalated")
                    → HyperSwarm
                        → SwarmSpawner (full 17-agent council)

Responsibilities (only):
    1. Receive raw ``swarm.idea`` events from all discovery sources.
    2. Deduplicate ideas within a rolling time window (default 5 min).
    3. Compute a numeric priority score from signal metadata.
    4. Maintain a bounded asyncio.PriorityQueue ordered by priority score.
    5. Apply an adaptive escalation threshold that rises when the idea rate
       is high and falls when the stream is quiet, keeping downstream load
       stable.
    6. Publish selected ideas to ``triage.escalated``, rejected ideas to
       ``triage.dropped`` (debug/metrics only).
    7. Track detailed metrics for observability.

Non-responsibilities:
    - No LLM calls (CPU-only, <1 ms per event).
    - No DuckDB reads or writes.
    - No trade decisions.
"""
import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration constants
# ═══════════════════════════════════════════════════════════════════════════════

TRIAGE_QUEUE_SIZE: int = 500          # Max items in the priority queue
DEDUP_WINDOW_SECONDS: float = 300.0   # 5-minute deduplication window
STALE_WINDOW_SECONDS: float = 120.0   # Drop queued items older than 2 min

# Adaptive threshold parameters
BASE_THRESHOLD: float = 40.0          # Default escalation threshold (0-100)
MIN_THRESHOLD: float = 20.0           # Floor — always escalate strong signals
MAX_THRESHOLD: float = 80.0           # Ceiling — cap during high-rate bursts
THRESHOLD_ADJUST_INTERVAL: float = 30.0   # Re-evaluate threshold every 30 s
HIGH_RATE_THRESHOLD: float = 30.0     # events/min → raise threshold
LOW_RATE_THRESHOLD: float = 5.0       # events/min → lower threshold
THRESHOLD_STEP: float = 5.0           # Raise/lower by this much each interval

# Priority scoring weights
SCORE_WEIGHT_RAW: float = 0.50        # Raw signal score contribution
SCORE_WEIGHT_PRIORITY_HINT: float = 0.20   # Explicit priority field (0-10)
SCORE_WEIGHT_DIRECTION: float = 0.10  # Direction clarity bonus
SCORE_WEIGHT_SOURCE: float = 0.20     # Source reputation bonus

# Source reputation bonuses (name fragment → 0-100 bonus points before weighting)
SOURCE_BONUSES: Dict[str, float] = {
    "turbo_scanner": 85.0,
    "discord": 75.0,
    "news_aggregator": 70.0,
    "autonomous_scout": 65.0,
    "geo_radar": 60.0,
    "correlation": 55.0,
    "pattern_library": 55.0,
}
DEFAULT_SOURCE_BONUS: float = 50.0


# ═══════════════════════════════════════════════════════════════════════════════
# Public data types
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TriageQueueItem:
    """A single item waiting in the triage priority queue."""

    priority_score: float        # 0-100; higher = process first
    seq: int                     # Monotonic insertion counter (tie-break)
    queued_at: float             # time.monotonic() insertion time (stale check)
    queued_wall_time: str        # ISO-8601 wall-clock time (observability only)
    data: Dict[str, Any]         # Original swarm.idea payload

    # PriorityQueue sorts ascending, so negate score for max-priority ordering.
    def __lt__(self, other: "TriageQueueItem") -> bool:
        if self.priority_score != other.priority_score:
            return self.priority_score > other.priority_score  # higher score = smaller rank
        return self.seq < other.seq  # earlier insertion wins on tie


@dataclass
class TriageStats:
    """Point-in-time triage metrics snapshot."""

    running: bool
    uptime_seconds: float
    base_threshold: float
    current_threshold: float
    dedup_window_seconds: float
    queue_depth: int
    queue_capacity: int
    total_received: int
    total_deduped: int
    total_dropped_threshold: int
    total_dropped_stale: int
    total_dropped_queue_full: int
    total_escalated: int
    escalation_rate: float          # escalated / received (0-1)
    current_idea_rate_per_min: float
    by_source: Dict[str, int]
    by_direction: Dict[str, int]
    errors: int


# ═══════════════════════════════════════════════════════════════════════════════
# IdeaTriageService
# ═══════════════════════════════════════════════════════════════════════════════

class IdeaTriageService:
    """Continuous triage layer — prioritise, deduplicate, and escalate ideas.

    Usage::

        triage = IdeaTriageService(message_bus)
        await triage.start()
        # … runs in background …
        await triage.stop()
    """

    def __init__(self, message_bus=None, queue_size: int = TRIAGE_QUEUE_SIZE):
        self._bus = message_bus
        self._running: bool = False
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=queue_size)
        self._queue_size = queue_size
        self._worker_task: Optional[asyncio.Task] = None
        self._threshold_task: Optional[asyncio.Task] = None

        # Deduplication state: dedup_key → most-recent queued timestamp
        self._dedup_registry: Dict[str, float] = {}

        # Adaptive threshold state
        self._current_threshold: float = BASE_THRESHOLD
        # Ring buffer for rate estimation — each entry is the monotonic time of
        # a received event.  We keep up to 10 min worth of history.
        self._recent_arrival_times: deque = deque(maxlen=600)

        # Sequence counter for stable queue ordering on equal scores
        self._seq: int = 0

        # Timing
        self._started_at: float = 0.0

        # Metrics
        self._stats: Dict[str, Any] = {
            "total_received": 0,
            "total_deduped": 0,
            "total_dropped_threshold": 0,
            "total_dropped_stale": 0,
            "total_dropped_queue_full": 0,
            "total_escalated": 0,
            "errors": 0,
            "by_source": defaultdict(int),
            "by_direction": defaultdict(int),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Subscribe to ``swarm.idea`` and launch background workers."""
        if self._running:
            return
        self._running = True
        self._started_at = time.monotonic()

        if self._bus:
            await self._bus.subscribe("swarm.idea", self._on_idea)

        self._worker_task = asyncio.create_task(self._process_loop())
        self._threshold_task = asyncio.create_task(self._threshold_loop())

        logger.info(
            "IdeaTriageService started: queue_size=%d, base_threshold=%.1f, "
            "dedup_window=%ds",
            self._queue_size, self._current_threshold, int(DEDUP_WINDOW_SECONDS),
        )

    async def stop(self) -> None:
        """Unsubscribe and gracefully shut down worker tasks."""
        self._running = False

        if self._bus:
            await self._bus.unsubscribe("swarm.idea", self._on_idea)

        for task in (self._worker_task, self._threshold_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._worker_task = None
        self._threshold_task = None
        logger.info(
            "IdeaTriageService stopped: received=%d, escalated=%d, deduped=%d",
            self._stats["total_received"],
            self._stats["total_escalated"],
            self._stats["total_deduped"],
        )

    # ──────────────────────────────────────────────────────────────────────
    # Event ingestion
    # ──────────────────────────────────────────────────────────────────────

    async def _on_idea(self, data: Dict[str, Any]) -> None:
        """Handle a raw ``swarm.idea`` event arriving from the MessageBus."""
        try:
            self._stats["total_received"] += 1
            self._recent_arrival_times.append(time.monotonic())

            source = str(data.get("source", "unknown"))
            direction = str(data.get("direction", "unknown"))
            self._stats["by_source"][source] += 1
            self._stats["by_direction"][direction] += 1

            # Deduplication check
            key = self._dedup_key(data)
            now = time.monotonic()
            last_seen = self._dedup_registry.get(key, 0.0)
            if now - last_seen < DEDUP_WINDOW_SECONDS:
                self._stats["total_deduped"] += 1
                logger.debug("Triage dedup: %s (%.0fs ago)", key, now - last_seen)
                return

            # Update dedup registry
            self._dedup_registry[key] = now

            # Compute priority score
            priority_score = self._compute_priority(data)

            # Enqueue
            self._seq += 1
            item = TriageQueueItem(
                priority_score=priority_score,
                seq=self._seq,
                queued_at=now,
                queued_wall_time=datetime.now(timezone.utc).isoformat(),
                data=data,
            )
            try:
                self._queue.put_nowait(item)
            except asyncio.QueueFull:
                self._stats["total_dropped_queue_full"] += 1
                logger.debug(
                    "Triage queue full (%d/%d), dropping %s score=%.1f",
                    self._queue.qsize(), self._queue_size, key, priority_score,
                )
        except Exception as exc:
            self._stats["errors"] += 1
            logger.warning("IdeaTriageService._on_idea error: %s", exc)

    # ──────────────────────────────────────────────────────────────────────
    # Processing worker
    # ──────────────────────────────────────────────────────────────────────

    async def _process_loop(self) -> None:
        """Drain the priority queue and escalate ideas that pass the threshold."""
        while self._running:
            try:
                item: TriageQueueItem = await asyncio.wait_for(
                    self._queue.get(), timeout=2.0
                )
            except asyncio.TimeoutError:
                self._expire_dedup_registry()
                continue
            except asyncio.CancelledError:
                break

            try:
                age = time.monotonic() - item.queued_at
                if age > STALE_WINDOW_SECONDS:
                    self._stats["total_dropped_stale"] += 1
                    logger.debug(
                        "Triage dropped stale idea (age=%.0fs > %.0fs)",
                        age, STALE_WINDOW_SECONDS,
                    )
                elif item.priority_score >= self._current_threshold:
                    await self._escalate(item)
                else:
                    self._stats["total_dropped_threshold"] += 1
                    logger.debug(
                        "Triage suppressed idea score=%.1f < threshold=%.1f",
                        item.priority_score, self._current_threshold,
                    )
                    if self._bus:
                        await self._bus.publish("triage.dropped", {
                            "reason": "below_threshold",
                            "score": round(item.priority_score, 2),
                            "threshold": round(self._current_threshold, 2),
                            "source": item.data.get("source", "unknown"),
                            "symbols": item.data.get("symbols", []),
                            "direction": item.data.get("direction", "unknown"),
                            "dropped_at": datetime.now(timezone.utc).isoformat(),
                        })
            except Exception as exc:
                self._stats["errors"] += 1
                logger.warning("IdeaTriageService._process_loop error: %s", exc)
            finally:
                self._queue.task_done()

    async def _escalate(self, item: TriageQueueItem) -> None:
        """Publish a high-priority idea to ``triage.escalated``."""
        self._stats["total_escalated"] += 1
        enriched = {
            **item.data,
            "triage_score": round(item.priority_score, 2),
            "triage_threshold": round(self._current_threshold, 2),
            "triage_queued_at": item.queued_wall_time,
        }
        if self._bus:
            await self._bus.publish("triage.escalated", enriched)
        logger.debug(
            "Triage escalated: %s score=%.1f threshold=%.1f",
            item.data.get("symbols", []),
            item.priority_score,
            self._current_threshold,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Adaptive threshold management
    # ──────────────────────────────────────────────────────────────────────

    async def _threshold_loop(self) -> None:
        """Periodically re-evaluate and adjust the escalation threshold."""
        while self._running:
            try:
                await asyncio.sleep(THRESHOLD_ADJUST_INTERVAL)
                self._adapt_threshold()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._stats["errors"] += 1
                logger.warning("IdeaTriageService._threshold_loop error: %s", exc)

    def _adapt_threshold(self) -> None:
        """Raise threshold if input rate is high; lower if quiet."""
        rate = self._current_idea_rate()
        old = self._current_threshold
        if rate > HIGH_RATE_THRESHOLD:
            self._current_threshold = min(
                self._current_threshold + THRESHOLD_STEP, MAX_THRESHOLD
            )
        elif rate < LOW_RATE_THRESHOLD:
            self._current_threshold = max(
                self._current_threshold - THRESHOLD_STEP, MIN_THRESHOLD
            )
        if self._current_threshold != old:
            logger.info(
                "Triage threshold adjusted: %.1f → %.1f (rate=%.1f events/min)",
                old, self._current_threshold, rate,
            )

    def _current_idea_rate(self) -> float:
        """Return the observed idea arrival rate over the last 60 seconds."""
        if not self._recent_arrival_times:
            return 0.0
        now = time.monotonic()
        cutoff = now - 60.0
        count = sum(1 for t in self._recent_arrival_times if t >= cutoff)
        return float(count)   # events per minute

    # ──────────────────────────────────────────────────────────────────────
    # Priority scoring
    # ──────────────────────────────────────────────────────────────────────

    def _compute_priority(self, data: Dict[str, Any]) -> float:
        """Return a 0-100 priority score for a raw ``swarm.idea`` payload.

        Components:
          * Raw signal score from ``metadata.score`` (50% weight)
          * Explicit ``priority`` hint field 0-10 (20% weight)
          * Direction clarity — bullish/bearish > unknown (10% weight)
          * Source reputation (20% weight)
        """
        # 1. Raw score from metadata (normalise to 0-100)
        meta = data.get("metadata") or {}
        raw_score = float(meta.get("score", 0.5))
        if raw_score <= 1.0:
            raw_score = raw_score * 100.0   # convert 0-1 → 0-100
        raw_score = min(max(raw_score, 0.0), 100.0)

        # 2. Explicit priority hint (0-10 field)
        priority_hint = float(data.get("priority", 5))
        priority_hint = min(max(priority_hint, 0.0), 10.0) * 10.0  # → 0-100

        # 3. Direction clarity
        direction = str(data.get("direction", "unknown")).lower()
        direction_score = 100.0 if direction in ("bullish", "bearish") else 0.0

        # 4. Source reputation
        source = str(data.get("source", "")).lower()
        source_score = DEFAULT_SOURCE_BONUS
        for fragment, bonus in SOURCE_BONUSES.items():
            if fragment in source:
                source_score = bonus
                break

        score = (
            raw_score * SCORE_WEIGHT_RAW
            + priority_hint * SCORE_WEIGHT_PRIORITY_HINT
            + direction_score * SCORE_WEIGHT_DIRECTION
            + source_score * SCORE_WEIGHT_SOURCE
        )
        return min(max(score, 0.0), 100.0)

    # ──────────────────────────────────────────────────────────────────────
    # Deduplication helpers
    # ──────────────────────────────────────────────────────────────────────

    def _dedup_key(self, data: Dict[str, Any]) -> str:
        """Return a stable dedup key for a ``swarm.idea`` payload.

        Key format: ``{symbol}|{direction}|{source_prefix}``
        """
        symbols: List[str] = data.get("symbols") or []
        symbol = symbols[0].upper() if symbols else "UNKNOWN"
        direction = str(data.get("direction", "unknown")).lower()
        source = str(data.get("source", "unknown")).split(":")[0].lower()
        return f"{symbol}|{direction}|{source}"

    def _expire_dedup_registry(self) -> None:
        """Evict stale entries from the dedup registry to bound memory usage."""
        now = time.monotonic()
        expired = [
            k for k, ts in self._dedup_registry.items()
            if now - ts > DEDUP_WINDOW_SECONDS
        ]
        for k in expired:
            del self._dedup_registry[k]

    # ──────────────────────────────────────────────────────────────────────
    # Observability
    # ──────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return a health and metrics snapshot for the /agents/status endpoint."""
        total_received = self._stats["total_received"]
        total_escalated = self._stats["total_escalated"]
        escalation_rate = (
            round(total_escalated / total_received, 3)
            if total_received > 0
            else 0.0
        )
        uptime = time.monotonic() - self._started_at if self._running else 0.0
        return {
            "running": self._running,
            "uptime_seconds": round(uptime, 1),
            "base_threshold": BASE_THRESHOLD,
            "current_threshold": round(self._current_threshold, 2),
            "dedup_window_seconds": DEDUP_WINDOW_SECONDS,
            "queue_depth": self._queue.qsize(),
            "queue_capacity": self._queue_size,
            "total_received": total_received,
            "total_deduped": self._stats["total_deduped"],
            "total_dropped_threshold": self._stats["total_dropped_threshold"],
            "total_dropped_stale": self._stats["total_dropped_stale"],
            "total_dropped_queue_full": self._stats["total_dropped_queue_full"],
            "total_escalated": total_escalated,
            "escalation_rate": escalation_rate,
            "current_idea_rate_per_min": round(self._current_idea_rate(), 2),
            "by_source": dict(self._stats["by_source"]),
            "by_direction": dict(self._stats["by_direction"]),
            "errors": self._stats["errors"],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton accessor (matches convention used by other services)
# ═══════════════════════════════════════════════════════════════════════════════

_idea_triage_instance: Optional[IdeaTriageService] = None


def get_idea_triage() -> IdeaTriageService:
    """Return the process-wide IdeaTriageService singleton."""
    global _idea_triage_instance
    if _idea_triage_instance is None:
        _idea_triage_instance = IdeaTriageService()
    return _idea_triage_instance
