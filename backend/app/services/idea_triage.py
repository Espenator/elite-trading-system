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
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Tunable constants
# ─────────────────────────────────────────────────────────────────────────────

BASE_THRESHOLD = 40
MIN_THRESHOLD = 20
MAX_THRESHOLD = 80

DEDUP_WINDOW_SECS = 300     # 5 minutes — same symbol+direction pair is duplicate
QUEUE_HIGH_WATER = 200      # Queue depth above this → raise threshold
QUEUE_LOW_WATER = 50        # Queue depth below this → lower threshold
THRESHOLD_ADJUST_STEP = 5   # How much to adjust per step
MAX_AGE_PENALTY = 20        # Maximum age penalty points
AGE_PENALTY_RATE = 1        # Points per second (capped at MAX_AGE_PENALTY)
DUP_PENALTY = 15            # Penalty for recently-seen symbol
MAX_QUEUE_SIZE = 5000       # Prevent unbounded memory usage

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
    original: Dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

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
            "timestamp": self.timestamp,
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

        # Stats
        self._stats = {
            "total_received": 0,
            "total_escalated": 0,
            "total_dropped": 0,
            "total_duplicates": 0,
            "current_threshold": BASE_THRESHOLD,
            "queue_depth": 0,
        }

        # Sliding window for throughput-based threshold adaptation
        self._recent_arrivals: List[float] = []  # epoch timestamps
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
        # Guard against unbounded growth during event storms: keep at most
        # MAX_QUEUE_SIZE timestamps (the adaptive threshold only looks at the
        # last 60 s anyway, so older entries are pruned on the next call).
        if len(self._recent_arrivals) < MAX_QUEUE_SIZE:
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

        # Dedup check
        is_dup = await self._check_and_record(symbol, direction, now)
        if is_dup:
            self._stats["total_duplicates"] += 1

        # Score
        score = self._score_idea(source, priority, age_secs, is_dup)

        # Adaptive threshold
        threshold = self._adaptive_threshold()
        self._stats["current_threshold"] = threshold

        idea_id = _make_idea_id(data)
        result = TriageResult(
            idea_id=idea_id,
            symbol=symbol,
            source=source,
            direction=direction,
            score=score,
            threshold=threshold,
            escalated=(score >= threshold),
            age_secs=age_secs,
            is_duplicate=is_dup,
            original=data,
        )

        if result.escalated:
            self._stats["total_escalated"] += 1
            await self._publish_escalated(data, result)
        else:
            self._stats["total_dropped"] += 1
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
        # Keep only arrivals in the last 60 s for rate estimation
        self._recent_arrivals = [t for t in self._recent_arrivals if now - t < 60]
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
            await self._bus.publish("triage.escalated", payload)
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
            await self._bus.publish("triage.dropped", payload)
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
        return dict(self._stats)

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
