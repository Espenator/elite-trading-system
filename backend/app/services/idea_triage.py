"""IdeaTriageService — E3 of the Continuous Discovery Architecture (Issue #38).

Sits between ``swarm.idea`` publishers (E1/E2 scouts, TurboScanner) and
the HyperSwarm consumer, acting as a quality gate:

    swarm.idea  →  IdeaTriageService
                       │  ├─ dedup (5-min window)
                       │  ├─ priority score (0–100)
                       │  └─ adaptive threshold (BASE=40, MIN=20, MAX=80)
                       ├─ score ≥ threshold  → triage.escalated
                       └─ score < threshold  → triage.dropped

Scoring formula
───────────────
  base_score = 50
  + source_bonus      (insider=30, flow/congress=20, streaming/scout=10, other=0)
  + priority_bonus    (priority 1→20, 2→15, 3→10, 4→5, 5→0)
  - age_penalty       (−1 per second old, up to −20)
  - dup_penalty       (−15 if symbol seen <5 min ago)

Adaptive threshold
──────────────────
  BASE_THRESHOLD = 40    ← normal market
  When queue_depth >  200 → raise threshold (more selective)
  When queue_depth <   50 → lower threshold (more permissive)
  Clamped to [MIN_THRESHOLD=20, MAX_THRESHOLD=80]
"""
import asyncio
import hashlib
import logging
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TriageDropReason(str, Enum):
    """Explicit reason codes for triage drop (auditable, observable)."""
    BELOW_THRESHOLD = "below_threshold"
    DUPLICATE = "duplicate"
    COOLDOWN = "cooldown"
    OVERLOAD_SHED = "overload_shed"
    INVALID_PAYLOAD = "invalid_payload"
    STALE = "stale"
    INCOMPLETE = "incomplete"

# ─────────────────────────────────────────────────────────────────────────────
# Tunable constants
# ─────────────────────────────────────────────────────────────────────────────

BASE_THRESHOLD = 40
MIN_THRESHOLD = 20
MAX_THRESHOLD = 80

DEDUP_WINDOW_SECS = 300     # 5 minutes — same symbol+direction pair is duplicate
SYMBOL_COOLDOWN_SECS = 120  # Per-symbol cooldown between escalations
QUEUE_HIGH_WATER = 200      # Queue depth above this → raise threshold
QUEUE_LOW_WATER = 50        # Queue depth below this → lower threshold
THRESHOLD_ADJUST_STEP = 5   # How much to adjust per step
MAX_AGE_PENALTY = 20        # Maximum age penalty points
AGE_PENALTY_RATE = 1        # Points per second (capped at MAX_AGE_PENALTY)
DUP_PENALTY = 15            # Penalty for recently-seen symbol
MAX_QUEUE_SIZE = 5000       # Prevent unbounded memory usage (_recent_arrivals hard cap)
MAX_SEEN_SIZE = 10_000      # Prevent unbounded dedup dict under a symbol storm
OVERLOAD_SHED_QUEUE_DEPTH = 5000  # MessageBus queue depth above this -> shed load

SOURCE_BONUSES: Dict[str, int] = {
    "insider_scout": 30,
    "congress_scout": 20,
    "flow_hunter_scout": 20,
    "gamma_scout": 15,
    "macro_scout": 15,
    "news_scout": 10,
    "earnings_scout": 10,
    "short_squeeze_scout": 10,
    "correlation_break_scout": 10,
    "sector_rotation_scout": 10,
    "sentiment_scout": 5,
    "ipo_scout": 5,
}

PRIORITY_BONUSES: Dict[int, int] = {1: 20, 2: 15, 3: 10, 4: 5, 5: 0}

# Max age (seconds) for an idea to be considered non-stale
MAX_IDEA_AGE_SECS = 600  # 10 minutes


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TriageResult:
    idea_id: str
    symbol: str
    source: str
    direction: str
    score: int
    threshold: int
    escalated: bool
    age_secs: float
    is_duplicate: bool
    drop_reason: Optional[str]  # TriageDropReason.value or None
    original: Dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    confidence: float = 1.0  # 0–1 quality/confidence for downstream

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idea_id": self.idea_id,
            "symbol": self.symbol,
            "source": self.source,
            "direction": self.direction,
            "score": self.score,
            "threshold": self.threshold,
            "escalated": self.escalated,
            "age_secs": round(self.age_secs, 1),
            "is_duplicate": self.is_duplicate,
            "drop_reason": self.drop_reason,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class IdeaTriageService:
    """Scores and routes incoming ``swarm.idea`` events.

    High-quality ideas are escalated to ``triage.escalated`` where
    HyperSwarm picks them up.  Low-quality ideas go to ``triage.dropped``
    for optional audit.
    """

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False

        # Dedup state: (symbol, direction) → last-seen epoch
        self._seen: Dict[Tuple[str, str], float] = {}
        self._seen_lock = asyncio.Lock()

        # Per-symbol escalation cooldown: symbol -> last escalated epoch
        self._symbol_last_escalated: Dict[str, float] = {}

        # Stats
        self._stats = {
            "total_received": 0,
            "total_escalated": 0,
            "total_dropped": 0,
            "total_duplicates": 0,
            "dropped_by_reason": defaultdict(int),
            "current_threshold": BASE_THRESHOLD,
            "queue_depth": 0,
        }

        # Sliding window for throughput-based threshold adaptation.
        # Bounded deque (maxlen=MAX_QUEUE_SIZE) gives automatic O(1) eviction
        # of the oldest timestamp whenever the window is full — no manual trim needed.
        self._recent_arrivals: Deque[float] = deque(maxlen=MAX_QUEUE_SIZE)
        self._recent_dropped: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._recent_escalated: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ──────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self._bus:
            await self._bus.subscribe("swarm.idea", self._on_idea)
        self._heartbeat_task = asyncio.create_task(self._maintenance_loop())
        logger.info(
            "IdeaTriageService started: base_threshold=%d, dedup_window=%ds",
            BASE_THRESHOLD, DEDUP_WINDOW_SECS,
        )

    async def stop(self) -> None:
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("IdeaTriageService stopped")

    # ──────────────────────────────────────────────────────────────────────
    # Core handler
    # ──────────────────────────────────────────────────────────────────────

    async def _on_idea(self, data: Dict[str, Any]) -> None:
        self._stats["total_received"] += 1
        now = time.time()
        # deque(maxlen=MAX_QUEUE_SIZE) automatically drops the oldest entry when
        # full, so no manual trim is needed — the cap is always enforced.
        self._recent_arrivals.append(now)

        # Extract primary symbol
        symbols = data.get("symbols", [])
        if isinstance(symbols, str):
            symbols = [symbols]
        symbol = symbols[0] if symbols else ""
        source = data.get("source", "unknown")
        direction = data.get("direction", "neutral")
        priority = int(data.get("priority", 5))
        metadata = data.get("metadata", {})

        # Watchdog: shed load when the nervous system is saturated.
        try:
            if self._bus and getattr(self._bus, "_queue", None) is not None:
                depth = int(self._bus.get_metrics().get("queue_depth", 0))
                threshold = int(os.getenv("TRIAGE_OVERLOAD_QUEUE_DEPTH", str(OVERLOAD_SHED_QUEUE_DEPTH)))
                if depth >= threshold:
                    result = TriageResult(
                        idea_id=_make_idea_id(data),
                        symbol=symbol,
                        source=source,
                        direction=direction,
                        score=0,
                        threshold=self._adaptive_threshold(),
                        escalated=False,
                        age_secs=0.0,
                        is_duplicate=False,
                        drop_reason=TriageDropReason.OVERLOAD_SHED.value,
                        original=data,
                    )
                    self._stats["total_dropped"] += 1
                    self._stats["dropped_by_reason"][TriageDropReason.OVERLOAD_SHED.value] += 1
                    await self._publish_dropped(data, result)
                    return
        except Exception:
            pass

        if not symbol:
            result = TriageResult(
                idea_id=_make_idea_id(data),
                symbol="",
                source=source,
                direction=direction,
                score=0,
                threshold=self._adaptive_threshold(),
                escalated=False,
                age_secs=0.0,
                is_duplicate=False,
                drop_reason=TriageDropReason.INVALID_PAYLOAD.value,
                original=data,
            )
            self._stats["total_dropped"] += 1
            self._stats["dropped_by_reason"][TriageDropReason.INVALID_PAYLOAD.value] += 1
            await self._publish_dropped(data, result)
            return

        # Extract event age (if publisher embedded a timestamp)
        event_ts = (
            metadata.get("detected_at") or
            metadata.get("discovered_at") or
            data.get("timestamp")
        )
        age_secs = 0.0
        if event_ts:
            try:
                ts = datetime.fromisoformat(event_ts.replace("Z", "+00:00"))
                age_secs = now - ts.timestamp()
            except Exception:
                pass

        # Reject stale ideas (explicit degraded path)
        if age_secs > MAX_IDEA_AGE_SECS:
            result = TriageResult(
                idea_id=_make_idea_id(data),
                symbol=symbol,
                source=source,
                direction=direction,
                score=0,
                threshold=self._adaptive_threshold(),
                escalated=False,
                age_secs=age_secs,
                is_duplicate=False,
                drop_reason=TriageDropReason.STALE.value,
                original=data,
            )
            self._stats["total_dropped"] += 1
            self._stats["dropped_by_reason"][TriageDropReason.STALE.value] += 1
            logger.info(
                "Triage dropped stale idea symbol=%s age_secs=%.0f trace_id=%s",
                symbol, age_secs, (data.get("_event_meta") or {}).get("trace_id"),
            )
            await self._publish_dropped(data, result)
            return

        # Dedup check
        is_dup = await self._check_and_record(symbol, direction, now)
        if is_dup:
            self._stats["total_duplicates"] += 1

        # Per-symbol cooldown: avoid flooding downstream analysis on the same ticker.
        cooldown_hit = False
        last_escalated = self._symbol_last_escalated.get(symbol.upper(), 0.0)
        if (now - last_escalated) < SYMBOL_COOLDOWN_SECS:
            cooldown_hit = True

        # Score
        score = self._score_idea(source, priority, age_secs, is_dup)

        # Adaptive threshold
        threshold = self._adaptive_threshold()
        self._stats["current_threshold"] = threshold

        idea_id = _make_idea_id(data)
        drop_reason: Optional[str] = None
        escalated = False
        if cooldown_hit:
            drop_reason = TriageDropReason.COOLDOWN.value
        elif is_dup:
            drop_reason = TriageDropReason.DUPLICATE.value
        elif score < threshold:
            drop_reason = TriageDropReason.BELOW_THRESHOLD.value
        else:
            escalated = True

        result = TriageResult(
            idea_id=idea_id,
            symbol=symbol,
            source=source,
            direction=direction,
            score=score,
            threshold=threshold,
            escalated=escalated,
            age_secs=age_secs,
            is_duplicate=is_dup,
            drop_reason=drop_reason,
            original=data,
        )

        if result.escalated:
            self._stats["total_escalated"] += 1
            self._symbol_last_escalated[symbol.upper()] = now
            await self._publish_escalated(data, result)
        else:
            self._stats["total_dropped"] += 1
            if result.drop_reason:
                self._stats["dropped_by_reason"][result.drop_reason] += 1
            await self._publish_dropped(data, result)

    # ──────────────────────────────────────────────────────────────────────
    # Scoring
    # ──────────────────────────────────────────────────────────────────────

    def _score_idea(self, source: str, priority: int, age_secs: float, is_dup: bool) -> int:
        score = 50

        # Source bonus — strip colon-suffixes like "streaming_discovery:AAPL"
        source_key = source.split(":")[0]
        score += SOURCE_BONUSES.get(source_key, 0)

        # Priority bonus
        score += PRIORITY_BONUSES.get(priority, 0)

        # Age penalty
        age_penalty = min(int(age_secs * AGE_PENALTY_RATE), MAX_AGE_PENALTY)
        score -= age_penalty

        # Duplicate penalty
        if is_dup:
            score -= DUP_PENALTY

        return max(0, min(100, score))

    def _adaptive_threshold(self) -> int:
        """Adjust threshold based on recent arrival rate."""
        now = time.time()
        # Keep only arrivals in the last 60 s for rate estimation.
        # Re-create as a new deque (same maxlen) so old entries are pruned
        # while preserving the bounded-size guarantee.
        self._recent_arrivals = deque(
            (t for t in self._recent_arrivals if now - t < 60),
            maxlen=MAX_QUEUE_SIZE,
        )
        depth = len(self._recent_arrivals)
        self._stats["queue_depth"] = depth

        threshold = BASE_THRESHOLD
        if depth > QUEUE_HIGH_WATER:
            steps = min((depth - QUEUE_HIGH_WATER) // 50 + 1, 8)
            threshold = BASE_THRESHOLD + steps * THRESHOLD_ADJUST_STEP
        elif depth < QUEUE_LOW_WATER:
            steps = min((QUEUE_LOW_WATER - depth) // 10 + 1, 4)
            threshold = BASE_THRESHOLD - steps * THRESHOLD_ADJUST_STEP

        return max(MIN_THRESHOLD, min(MAX_THRESHOLD, threshold))

    # ──────────────────────────────────────────────────────────────────────
    # Dedup
    # ──────────────────────────────────────────────────────────────────────

    async def _check_and_record(self, symbol: str, direction: str, now: float) -> bool:
        """Return True if this (symbol, direction) pair was seen recently."""
        if not symbol:
            return False
        key = (symbol.upper(), direction)
        async with self._seen_lock:
            last = self._seen.get(key, 0.0)
            is_dup = (now - last) < DEDUP_WINDOW_SECS
            self._seen[key] = now
            # Hard cap: evict the first-inserted (oldest by insertion-order) entry
            # when the dict exceeds MAX_SEEN_SIZE.  Python 3.7+ dicts maintain
            # insertion order, and updates to existing keys don't move them, so
            # next(iter(_seen)) is always the entry inserted longest ago.  The
            # maintenance loop does bulk expiry every 60 s; this cap guards
            # against a symbol-storm in between those cycles.
            if len(self._seen) > MAX_SEEN_SIZE:
                oldest_key = next(iter(self._seen))
                del self._seen[oldest_key]
        return is_dup

    # ──────────────────────────────────────────────────────────────────────
    # Publishing
    # ──────────────────────────────────────────────────────────────────────

    async def _publish_escalated(
        self, original: Dict[str, Any], result: TriageResult
    ) -> None:
        if not self._bus:
            return
        try:
            payload = dict(original)
            payload["triage"] = result.to_dict()
            trace_id = (original.get("_event_meta") or {}).get("trace_id")
            try:
                from app.events.contracts import publish_event, TOPIC_TRIAGE_ESCALATED
                ok = await publish_event(
                    self._bus,
                    TOPIC_TRIAGE_ESCALATED,
                    payload,
                    producer="idea_triage",
                    pipeline_stage="triage",
                    trace_id=trace_id,
                )
                if not ok:
                    await self._bus.publish("triage.escalated", payload)
            except Exception:
                await self._bus.publish("triage.escalated", payload)
            self._recent_escalated.append(
                {"triage": result.to_dict(), "original": {"symbol": result.symbol, "source": result.source}}
            )
            logger.debug(
                "Escalated: symbol=%s source=%s score=%d threshold=%d",
                result.symbol, result.source, result.score, result.threshold,
            )
        except Exception as exc:
            logger.warning("Triage escalate publish failed: %s", exc)

    async def _publish_dropped(
        self, original: Dict[str, Any], result: TriageResult
    ) -> None:
        if not self._bus:
            return
        try:
            payload = dict(original)
            payload["triage"] = result.to_dict()
            trace_id = (original.get("_event_meta") or {}).get("trace_id")
            try:
                from app.events.contracts import publish_event, TOPIC_TRIAGE_DROPPED
                ok = await publish_event(
                    self._bus,
                    TOPIC_TRIAGE_DROPPED,
                    payload,
                    producer="idea_triage",
                    pipeline_stage="triage",
                    trace_id=trace_id,
                )
                if not ok:
                    await self._bus.publish("triage.dropped", payload)
            except Exception:
                await self._bus.publish("triage.dropped", payload)
            self._recent_dropped.append(
                {"triage": result.to_dict(), "original": {"symbol": result.symbol, "source": result.source}}
            )
        except Exception as exc:
            logger.debug("Triage drop publish failed: %s", exc)

    # ──────────────────────────────────────────────────────────────────────
    # Maintenance
    # ──────────────────────────────────────────────────────────────────────

    async def _maintenance_loop(self) -> None:
        """Periodically expire old dedup entries and publish health."""
        while self._running:
            await asyncio.sleep(60)
            if not self._running:
                break
            now = time.time()
            async with self._seen_lock:
                expired = [k for k, t in self._seen.items() if now - t > DEDUP_WINDOW_SECS]
                for k in expired:
                    del self._seen[k]
            if self._bus:
                try:
                    await self._bus.publish("scout.heartbeat", {
                        "source": "idea_triage_service",
                        "status": "healthy",
                        "stats": dict(self._stats),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as exc:
                    logger.debug("Triage heartbeat failed: %s", exc)

    # ──────────────────────────────────────────────────────────────────────
    # Public helpers
    # ──────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        # Ensure defaultdict is JSONable for APIs.
        stats = dict(self._stats)
        if "dropped_by_reason" in stats and isinstance(stats["dropped_by_reason"], dict):
            stats["dropped_by_reason"] = dict(stats["dropped_by_reason"])
        stats["symbol_cooldown_seconds"] = SYMBOL_COOLDOWN_SECS
        stats["dedup_window_seconds"] = DEDUP_WINDOW_SECS
        stats["recent_dropped"] = list(self._recent_dropped)[-25:]
        stats["recent_escalated"] = list(self._recent_escalated)[-25:]
        return stats

    def score_idea(
        self, source: str, priority: int, age_secs: float = 0, is_dup: bool = False
    ) -> int:
        """Compute the triage score for an idea given its attributes (0–100).

        Useful for external callers, API endpoints, and unit tests that need
        to understand how a given idea would be scored without routing it through
        the full pipeline.
        """
        return self._score_idea(source, priority, age_secs, is_dup)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_idea_id(data: Dict[str, Any]) -> str:
    """Stable idea ID derived from content hash."""
    symbols = data.get("symbols", [])
    source = data.get("source", "")
    direction = data.get("direction", "")
    raw = f"{source}:{symbols}:{direction}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


_triage: Optional[IdeaTriageService] = None


def get_idea_triage_service(message_bus=None) -> IdeaTriageService:
    global _triage
    if _triage is None:
        _triage = IdeaTriageService(message_bus)
    return _triage
