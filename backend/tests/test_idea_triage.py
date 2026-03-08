"""Tests for idea_triage.py — E3 IdeaTriageService.

Covers: priority scoring, deduplication, adaptive thresholding, queue
behaviour, escalation, failure modes, and the get_status() snapshot.
No DuckDB, no external APIs, no LLM calls required.
"""
import asyncio
import time

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.idea_triage import (
    IdeaTriageService,
    TriageQueueItem,
    BASE_THRESHOLD,
    DEDUP_WINDOW_SECONDS,
    HIGH_RATE_THRESHOLD,
    LOW_RATE_THRESHOLD,
    MAX_THRESHOLD,
    MIN_THRESHOLD,
    THRESHOLD_STEP,
    get_idea_triage,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper factories
# ─────────────────────────────────────────────────────────────────────────────

def _idea(
    symbol: str = "AAPL",
    direction: str = "bullish",
    source: str = "turbo_scanner:technical_breakout",
    score: float = 0.75,
    priority: int = 7,
) -> dict:
    return {
        "source": source,
        "symbols": [symbol],
        "direction": direction,
        "reasoning": f"Test signal for {symbol}",
        "priority": priority,
        "metadata": {
            "signal_type": "technical_breakout",
            "score": score,
            "data": {},
        },
    }


def _triage(queue_size: int = 100) -> IdeaTriageService:
    """Return a fresh IdeaTriageService (no MessageBus)."""
    return IdeaTriageService(message_bus=None, queue_size=queue_size)


# ─────────────────────────────────────────────────────────────────────────────
# TriageQueueItem ordering
# ─────────────────────────────────────────────────────────────────────────────

class TestTriageQueueItem:
    def test_higher_score_is_less(self):
        a = TriageQueueItem(priority_score=90.0, seq=1, queued_at=0.0, queued_wall_time="2026-01-01T00:00:00+00:00", data={})
        b = TriageQueueItem(priority_score=50.0, seq=2, queued_at=0.0, queued_wall_time="2026-01-01T00:00:00+00:00", data={})
        assert a < b  # a has higher priority → sorts first

    def test_equal_score_earlier_seq_wins(self):
        a = TriageQueueItem(priority_score=70.0, seq=1, queued_at=0.0, queued_wall_time="2026-01-01T00:00:00+00:00", data={})
        b = TriageQueueItem(priority_score=70.0, seq=2, queued_at=0.0, queued_wall_time="2026-01-01T00:00:00+00:00", data={})
        assert a < b  # earlier insertion wins on tie


# ─────────────────────────────────────────────────────────────────────────────
# Priority scoring
# ─────────────────────────────────────────────────────────────────────────────

class TestComputePriority:
    def test_bullish_scores_higher_than_unknown(self):
        svc = _triage()
        score_bullish = svc._compute_priority(_idea(direction="bullish"))
        score_unknown = svc._compute_priority(_idea(direction="unknown"))
        assert score_bullish > score_unknown

    def test_higher_raw_score_raises_priority(self):
        svc = _triage()
        low = svc._compute_priority(_idea(score=0.1))
        high = svc._compute_priority(_idea(score=0.9))
        assert high > low

    def test_higher_priority_hint_raises_priority(self):
        svc = _triage()
        low = svc._compute_priority(_idea(priority=1))
        high = svc._compute_priority(_idea(priority=10))
        assert high > low

    def test_known_source_scores_higher_than_unknown(self):
        svc = _triage()
        known = svc._compute_priority(_idea(source="turbo_scanner:breakout"))
        unknown = svc._compute_priority(_idea(source="some_random_source"))
        assert known > unknown

    def test_score_clamped_to_0_100(self):
        svc = _triage()
        extreme = _idea(score=999.0, priority=99)
        assert 0.0 <= svc._compute_priority(extreme) <= 100.0

    def test_bearish_treated_same_as_bullish_for_direction_bonus(self):
        svc = _triage()
        bullish = svc._compute_priority(_idea(direction="bullish"))
        bearish = svc._compute_priority(_idea(direction="bearish"))
        assert bullish == bearish

    def test_score_normalised_from_0_1(self):
        svc = _triage()
        # score=0.75 → raw_score=75; score=75 → already 75 (>1 means no multiply)
        s1 = svc._compute_priority(_idea(score=0.75))
        s2 = svc._compute_priority(_idea(score=75.0))
        assert s1 == pytest.approx(s2, abs=0.01)

    def test_empty_metadata_does_not_raise(self):
        svc = _triage()
        data = {"source": "scout", "symbols": ["TSLA"], "direction": "bullish"}
        score = svc._compute_priority(data)
        assert 0.0 <= score <= 100.0

    def test_missing_symbols_handled(self):
        svc = _triage()
        data = {"source": "turbo_scanner", "direction": "bullish", "metadata": {"score": 0.8}}
        # Should not raise
        score = svc._compute_priority(data)
        assert score >= 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication
# ─────────────────────────────────────────────────────────────────────────────

class TestDedupKey:
    def test_same_symbol_direction_source_dedup(self):
        svc = _triage()
        k1 = svc._dedup_key(_idea("AAPL", "bullish", "turbo_scanner:tb"))
        k2 = svc._dedup_key(_idea("AAPL", "bullish", "turbo_scanner:vwap"))
        assert k1 == k2  # source prefix matches

    def test_different_direction_different_key(self):
        svc = _triage()
        k1 = svc._dedup_key(_idea("AAPL", "bullish", "turbo_scanner"))
        k2 = svc._dedup_key(_idea("AAPL", "bearish", "turbo_scanner"))
        assert k1 != k2

    def test_different_symbol_different_key(self):
        svc = _triage()
        k1 = svc._dedup_key(_idea("AAPL", "bullish", "turbo_scanner"))
        k2 = svc._dedup_key(_idea("TSLA", "bullish", "turbo_scanner"))
        assert k1 != k2

    def test_key_is_uppercased_symbol(self):
        svc = _triage()
        k = svc._dedup_key({"symbols": ["aapl"], "direction": "bullish", "source": "scout"})
        assert k.startswith("AAPL|")

    def test_missing_symbols_uses_unknown(self):
        svc = _triage()
        k = svc._dedup_key({"direction": "bullish", "source": "scout"})
        assert k.startswith("UNKNOWN|")


# ─────────────────────────────────────────────────────────────────────────────
# Dedup registry expiry
# ─────────────────────────────────────────────────────────────────────────────

class TestDedupRegistry:
    def test_fresh_entry_not_expired(self):
        svc = _triage()
        svc._dedup_registry["AAPL|bullish|turbo_scanner"] = time.monotonic()
        before = len(svc._dedup_registry)
        svc._expire_dedup_registry()
        assert len(svc._dedup_registry) == before   # entry still fresh

    def test_old_entry_evicted(self):
        svc = _triage()
        svc._dedup_registry["AAPL|bullish|turbo_scanner"] = (
            time.monotonic() - DEDUP_WINDOW_SECONDS - 1
        )
        svc._expire_dedup_registry()
        assert "AAPL|bullish|turbo_scanner" not in svc._dedup_registry


# ─────────────────────────────────────────────────────────────────────────────
# Adaptive threshold
# ─────────────────────────────────────────────────────────────────────────────

class TestAdaptiveThreshold:
    def test_high_rate_raises_threshold(self):
        svc = _triage()
        now = time.monotonic()
        # Simulate HIGH_RATE_THRESHOLD + 5 events in last 60 s
        for _ in range(int(HIGH_RATE_THRESHOLD + 5)):
            svc._recent_arrival_times.append(now)
        svc._adapt_threshold()
        assert svc._current_threshold > BASE_THRESHOLD

    def test_low_rate_lowers_threshold(self):
        svc = _triage()
        svc._current_threshold = BASE_THRESHOLD + THRESHOLD_STEP  # above base
        # Empty arrival buffer → rate = 0 (< LOW_RATE_THRESHOLD)
        svc._adapt_threshold()
        assert svc._current_threshold < BASE_THRESHOLD + THRESHOLD_STEP

    def test_threshold_never_exceeds_max(self):
        svc = _triage()
        svc._current_threshold = MAX_THRESHOLD
        now = time.monotonic()
        for _ in range(200):
            svc._recent_arrival_times.append(now)
        svc._adapt_threshold()
        assert svc._current_threshold == MAX_THRESHOLD

    def test_threshold_never_below_min(self):
        svc = _triage()
        svc._current_threshold = MIN_THRESHOLD
        # Empty buffer — low rate
        svc._adapt_threshold()
        assert svc._current_threshold == MIN_THRESHOLD

    def test_medium_rate_leaves_threshold_unchanged(self):
        svc = _triage()
        # Put rate between LOW and HIGH
        rate_in_middle = (LOW_RATE_THRESHOLD + HIGH_RATE_THRESHOLD) / 2
        now = time.monotonic()
        for _ in range(int(rate_in_middle)):
            svc._recent_arrival_times.append(now)
        before = svc._current_threshold
        svc._adapt_threshold()
        assert svc._current_threshold == before

    def test_idea_rate_counts_last_60s(self):
        svc = _triage()
        old = time.monotonic() - 90.0  # older than 60 s — not counted
        recent = time.monotonic() - 10.0
        svc._recent_arrival_times.extend([old] * 5)
        svc._recent_arrival_times.extend([recent] * 3)
        rate = svc._current_idea_rate()
        assert rate == 3.0

    def test_empty_arrival_buffer_returns_zero_rate(self):
        svc = _triage()
        assert svc._current_idea_rate() == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# _on_idea ingestion (async, no MessageBus)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
class TestOnIdea:
    async def test_new_idea_enters_queue(self):
        svc = _triage()
        await svc._on_idea(_idea())
        assert svc._queue.qsize() == 1

    async def test_dedup_suppresses_duplicate(self):
        svc = _triage()
        idea = _idea()
        await svc._on_idea(idea)
        await svc._on_idea(idea)   # identical — should be deduped
        assert svc._queue.qsize() == 1
        assert svc._stats["total_deduped"] == 1

    async def test_different_direction_not_deduped(self):
        svc = _triage()
        await svc._on_idea(_idea(direction="bullish"))
        await svc._on_idea(_idea(direction="bearish"))
        assert svc._queue.qsize() == 2

    async def test_stats_incremented(self):
        svc = _triage()
        await svc._on_idea(_idea())
        assert svc._stats["total_received"] == 1

    async def test_by_source_tracked(self):
        svc = _triage()
        await svc._on_idea(_idea(source="turbo_scanner:breakout"))
        assert svc._stats["by_source"]["turbo_scanner:breakout"] == 1

    async def test_queue_full_increments_dropped_counter(self):
        svc = _triage(queue_size=1)
        await svc._on_idea(_idea("AAPL"))
        await svc._on_idea(_idea("TSLA"))   # queue full after first
        assert svc._stats["total_dropped_queue_full"] == 1

    async def test_malformed_event_does_not_raise(self):
        svc = _triage()
        await svc._on_idea(None)   # type: ignore
        # Should not raise — errors are caught and logged
        assert svc._stats["errors"] == 1

    async def test_dedup_window_allows_requeue_after_expiry(self):
        svc = _triage()
        idea = _idea()
        await svc._on_idea(idea)
        # Manually expire the dedup entry
        key = svc._dedup_key(idea)
        svc._dedup_registry[key] = time.monotonic() - DEDUP_WINDOW_SECONDS - 1
        await svc._on_idea(idea)
        assert svc._queue.qsize() == 2  # re-queued after window expiry


# ─────────────────────────────────────────────────────────────────────────────
# Escalation and threshold filtering
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
class TestEscalation:
    async def test_high_score_idea_is_escalated(self):
        bus = MagicMock()
        bus.publish = AsyncMock()
        svc = IdeaTriageService(message_bus=bus, queue_size=100)
        svc._current_threshold = 30.0   # low threshold so score 90 passes
        idea = _idea(score=0.9, priority=9, direction="bullish")
        item = TriageQueueItem(
            priority_score=90.0, seq=1, queued_at=time.monotonic(),
            queued_wall_time="2026-01-01T00:00:00+00:00", data=idea
        )
        await svc._escalate(item)
        assert svc._stats["total_escalated"] == 1
        bus.publish.assert_awaited_once()
        call_args = bus.publish.call_args
        assert call_args[0][0] == "triage.escalated"

    async def test_escalated_payload_includes_triage_metadata(self):
        bus = MagicMock()
        bus.publish = AsyncMock()
        svc = IdeaTriageService(message_bus=bus)
        idea = _idea()
        item = TriageQueueItem(
            priority_score=75.0, seq=1, queued_at=time.monotonic(),
            queued_wall_time="2026-01-01T00:00:00+00:00", data=idea
        )
        await svc._escalate(item)
        published = bus.publish.call_args[0][1]
        assert "triage_score" in published
        assert "triage_threshold" in published
        assert "triage_queued_at" in published
        assert published["triage_score"] == 75.0

    async def test_below_threshold_emits_triage_dropped(self):
        bus = MagicMock()
        bus.publish = AsyncMock()
        svc = IdeaTriageService(message_bus=bus, queue_size=100)
        svc._current_threshold = 80.0   # high threshold
        idea = _idea(score=0.3)
        item = TriageQueueItem(
            priority_score=30.0, seq=1, queued_at=time.monotonic(),
            queued_wall_time="2026-01-01T00:00:00+00:00", data=idea
        )
        # Process one item manually
        svc._queue.put_nowait(item)
        svc._running = True
        process = asyncio.create_task(svc._process_loop())
        await asyncio.sleep(0.05)   # let worker drain the queue
        svc._running = False
        process.cancel()
        try:
            await process
        except asyncio.CancelledError:
            pass
        assert svc._stats["total_dropped_threshold"] == 1
        # triage.dropped should have been published
        topics_published = [c[0][0] for c in bus.publish.call_args_list]
        assert "triage.dropped" in topics_published

    async def test_stale_item_dropped(self):
        svc = _triage()
        idea = _idea()
        # Item queued 3 minutes ago — beyond STALE_WINDOW_SECONDS (2 min)
        item = TriageQueueItem(
            priority_score=80.0, seq=1,
            queued_at=time.monotonic() - 200.0,  # 200s ago > 120s stale window
            queued_wall_time="2026-01-01T00:00:00+00:00",
            data=idea,
        )
        svc._queue.put_nowait(item)
        svc._running = True
        process = asyncio.create_task(svc._process_loop())
        await asyncio.sleep(0.05)
        svc._running = False
        process.cancel()
        try:
            await process
        except asyncio.CancelledError:
            pass
        assert svc._stats["total_dropped_stale"] == 1
        assert svc._stats["total_escalated"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle: start / stop
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
class TestLifecycle:
    async def test_start_sets_running_flag(self):
        svc = _triage()
        await svc.start()
        assert svc._running is True
        await svc.stop()

    async def test_stop_clears_running_flag(self):
        svc = _triage()
        await svc.start()
        await svc.stop()
        assert svc._running is False

    async def test_double_start_is_idempotent(self):
        svc = _triage()
        await svc.start()
        worker_before = svc._worker_task
        await svc.start()   # second start — should no-op
        assert svc._worker_task is worker_before
        await svc.stop()

    async def test_start_subscribes_to_bus(self):
        bus = MagicMock()
        bus.subscribe = AsyncMock()
        bus.unsubscribe = AsyncMock()
        svc = IdeaTriageService(message_bus=bus)
        await svc.start()
        bus.subscribe.assert_awaited_once_with("swarm.idea", svc._on_idea)
        await svc.stop()

    async def test_stop_unsubscribes_from_bus(self):
        bus = MagicMock()
        bus.subscribe = AsyncMock()
        bus.unsubscribe = AsyncMock()
        svc = IdeaTriageService(message_bus=bus)
        await svc.start()
        await svc.stop()
        bus.unsubscribe.assert_awaited_once_with("swarm.idea", svc._on_idea)


# ─────────────────────────────────────────────────────────────────────────────
# get_status() observability
# ─────────────────────────────────────────────────────────────────────────────

class TestGetStatus:
    def test_status_keys_present(self):
        svc = _triage()
        status = svc.get_status()
        required_keys = {
            "running", "uptime_seconds", "base_threshold", "current_threshold",
            "dedup_window_seconds", "queue_depth", "queue_capacity",
            "total_received", "total_deduped", "total_dropped_threshold",
            "total_dropped_stale", "total_dropped_queue_full", "total_escalated",
            "escalation_rate", "current_idea_rate_per_min", "by_source",
            "by_direction", "errors",
        }
        assert required_keys.issubset(status.keys())

    def test_escalation_rate_zero_when_none_received(self):
        svc = _triage()
        assert svc.get_status()["escalation_rate"] == 0.0

    def test_escalation_rate_computed_correctly(self):
        svc = _triage()
        svc._stats["total_received"] = 10
        svc._stats["total_escalated"] = 4
        assert svc.get_status()["escalation_rate"] == pytest.approx(0.4)

    def test_queue_depth_reflects_queue_size(self):
        svc = _triage()
        idea = _idea()
        item = TriageQueueItem(priority_score=80.0, seq=1, queued_at=0.0, queued_wall_time="2026-01-01T00:00:00+00:00", data=idea)
        svc._queue.put_nowait(item)
        assert svc.get_status()["queue_depth"] == 1

    def test_current_threshold_in_status(self):
        svc = _triage()
        svc._current_threshold = 55.0
        assert svc.get_status()["current_threshold"] == 55.0

    def test_running_false_before_start(self):
        svc = _triage()
        assert svc.get_status()["running"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────

class TestSingleton:
    def test_get_idea_triage_returns_same_instance(self):
        import app.services.idea_triage as mod
        # Reset the singleton so the test is hermetic
        mod._idea_triage_instance = None
        a = get_idea_triage()
        b = get_idea_triage()
        assert a is b
        mod._idea_triage_instance = None   # clean up
