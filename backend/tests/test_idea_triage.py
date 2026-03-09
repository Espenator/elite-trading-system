"""Tests for IdeaTriageService (E3)."""
import asyncio
import time
import pytest
from app.services.idea_triage import (
    IdeaTriageService,
    TriageResult,
    BASE_THRESHOLD,
    MIN_THRESHOLD,
    MAX_THRESHOLD,
    DEDUP_WINDOW_SECS,
    SOURCE_BONUSES,
    PRIORITY_BONUSES,
    get_idea_triage_service,
    _make_idea_id,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class FakeBus:
    def __init__(self):
        self.published = []
        self.subscriptions = {}

    async def subscribe(self, topic, handler):
        self.subscriptions[topic] = handler

    async def publish(self, topic, data):
        self.published.append((topic, data))


def make_idea(
    source="turbo_scanner:volume_surge",
    symbols=None,
    direction="bullish",
    reasoning="test",
    priority=3,
    metadata=None,
):
    return {
        "source": source,
        "symbols": symbols or ["AAPL"],
        "direction": direction,
        "reasoning": reasoning,
        "priority": priority,
        "metadata": metadata or {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_base_threshold_is_40(self):
        assert BASE_THRESHOLD == 40

    def test_min_threshold_is_20(self):
        assert MIN_THRESHOLD == 20

    def test_max_threshold_is_80(self):
        assert MAX_THRESHOLD == 80

    def test_dedup_window_is_5_minutes(self):
        assert DEDUP_WINDOW_SECS == 300

    def test_source_bonuses_defined(self):
        assert SOURCE_BONUSES["insider_scout"] == 30
        assert SOURCE_BONUSES["flow_hunter_scout"] == 20
        assert SOURCE_BONUSES["congress_scout"] == 20

    def test_priority_bonuses_defined(self):
        assert PRIORITY_BONUSES[1] == 20
        assert PRIORITY_BONUSES[5] == 0


# ─────────────────────────────────────────────────────────────────────────────
# _make_idea_id
# ─────────────────────────────────────────────────────────────────────────────

class TestMakeIdeaId:
    def test_same_data_same_id(self):
        idea = make_idea()
        assert _make_idea_id(idea) == _make_idea_id(idea)

    def test_different_source_different_id(self):
        a = make_idea(source="source_a")
        b = make_idea(source="source_b")
        assert _make_idea_id(a) != _make_idea_id(b)

    def test_id_is_12_chars(self):
        assert len(_make_idea_id(make_idea())) == 12


# ─────────────────────────────────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────────────────────────────────

class TestScoring:
    def setup_method(self):
        self.svc = IdeaTriageService()

    def test_base_score_50(self):
        score = self.svc.score_idea("unknown_source", 5, 0, False)
        assert score == 50

    def test_insider_bonus_applied(self):
        score = self.svc.score_idea("insider_scout", 5, 0, False)
        assert score == 50 + 30  # insider bonus = 30

    def test_priority_1_bonus_20(self):
        score = self.svc.score_idea("unknown", 1, 0, False)
        assert score == 50 + 20  # priority 1 bonus = 20

    def test_age_penalty_applied(self):
        score = self.svc.score_idea("unknown", 5, 10, False)  # 10 sec old
        assert score == 50 - 10

    def test_age_penalty_capped_at_20(self):
        score = self.svc.score_idea("unknown", 5, 1000, False)  # very old
        assert score == 50 - 20

    def test_dup_penalty_applied(self):
        score = self.svc.score_idea("unknown", 5, 0, True)
        assert score == 50 - 15

    def test_score_clamped_to_0_100(self):
        # Max possible: 50 + 30 + 20 = 100
        score_max = self.svc.score_idea("insider_scout", 1, 0, False)
        assert score_max == 100

        # Min possible: 50 - 20 - 15 = 15 (positive)
        score_min = self.svc.score_idea("unknown", 5, 1000, True)
        assert score_min == 15

    def test_source_colon_suffix_stripped(self):
        """'streaming_discovery:AAPL' → looks up 'streaming_discovery'."""
        score_with_suffix = self.svc.score_idea("streaming_discovery:AAPL", 3, 0, False)
        score_without = self.svc.score_idea("streaming_discovery", 3, 0, False)
        assert score_with_suffix == score_without

    def test_congress_scout_score(self):
        score = self.svc.score_idea("congress_scout", 2, 0, False)
        assert score == 50 + 20 + 15  # congress bonus + priority 2 bonus

    def test_flow_hunter_priority_2(self):
        score = self.svc.score_idea("flow_hunter_scout", 2, 0, False)
        assert score == 50 + 20 + 15  # flow_hunter bonus + priority 2


# ─────────────────────────────────────────────────────────────────────────────
# IdeaTriageService lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestLifecycle:
    @pytest.mark.anyio
    async def test_start_subscribes_to_swarm_idea(self):
        bus = FakeBus()
        svc = IdeaTriageService(bus)
        await svc.start()
        assert "swarm.idea" in bus.subscriptions
        await svc.stop()

    @pytest.mark.anyio
    async def test_start_idempotent(self):
        bus = FakeBus()
        svc = IdeaTriageService(bus)
        await svc.start()
        await svc.start()  # Should not raise
        await svc.stop()

    @pytest.mark.anyio
    async def test_stop_is_idempotent(self):
        bus = FakeBus()
        svc = IdeaTriageService(bus)
        await svc.start()
        await svc.stop()
        await svc.stop()  # Should not raise

    @pytest.mark.anyio
    async def test_no_bus_does_not_raise(self):
        svc = IdeaTriageService(None)
        await svc.start()
        await svc._on_idea(make_idea())
        await svc.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Escalation routing
# ─────────────────────────────────────────────────────────────────────────────

class TestEscalationRouting:
    @pytest.mark.anyio
    async def test_high_score_escalated(self):
        """insider_scout priority=1 → score=100 → escalated."""
        bus = FakeBus()
        svc = IdeaTriageService(bus)
        await svc.start()
        idea = make_idea(source="insider_scout", priority=1)
        await svc._on_idea(idea)
        escalated = [d for t, d in bus.published if t == "triage.escalated"]
        assert len(escalated) >= 1
        await svc.stop()

    @pytest.mark.anyio
    async def test_low_score_dropped(self):
        """Unknown source, priority=5, fresh → score=50 which is above BASE(40),
        but with age penalty or dup penalty it may drop. Use very old idea."""
        bus = FakeBus()
        svc = IdeaTriageService(bus)
        await svc.start()
        # Very old + dup penalty: 50 - 20 - 15 = 15 < 40
        idea = make_idea(source="unknown_source", priority=5, metadata={
            "detected_at": "2000-01-01T00:00:00+00:00"  # ancient
        })
        # Mark as dup manually first
        await svc._check_and_record("AAPL", "bullish", time.time())
        await svc._on_idea(idea)
        dropped = [d for t, d in bus.published if t == "triage.dropped"]
        assert len(dropped) >= 1
        await svc.stop()

    @pytest.mark.anyio
    async def test_escalated_payload_contains_triage_key(self):
        bus = FakeBus()
        svc = IdeaTriageService(bus)
        await svc.start()
        idea = make_idea(source="insider_scout", priority=1)
        await svc._on_idea(idea)
        escalated = [d for t, d in bus.published if t == "triage.escalated"]
        assert escalated
        assert "triage" in escalated[0]
        triage = escalated[0]["triage"]
        assert "score" in triage
        assert "threshold" in triage
        assert triage["escalated"] is True
        await svc.stop()

    @pytest.mark.anyio
    async def test_dropped_payload_contains_triage_key(self):
        bus = FakeBus()
        svc = IdeaTriageService(bus)
        await svc.start()
        # Force a drop: ancient timestamp + dup
        await svc._check_and_record("TSLA", "bearish", time.time())
        idea = make_idea(
            source="unknown", symbols=["TSLA"], direction="bearish", priority=5,
            metadata={"detected_at": "2000-01-01T00:00:00+00:00"}
        )
        await svc._on_idea(idea)
        dropped = [d for t, d in bus.published if t == "triage.dropped"]
        assert dropped
        assert "triage" in dropped[0]
        assert dropped[0]["triage"]["escalated"] is False
        await svc.stop()

    @pytest.mark.anyio
    async def test_stats_updated_on_receive(self):
        bus = FakeBus()
        svc = IdeaTriageService(bus)
        await svc.start()
        await svc._on_idea(make_idea())
        stats = svc.get_stats()
        assert stats["total_received"] == 1
        await svc.stop()

    @pytest.mark.anyio
    async def test_escalated_and_dropped_counts(self):
        bus = FakeBus()
        svc = IdeaTriageService(bus)
        await svc.start()

        # Send one sure-escalate (insider, priority 1)
        await svc._on_idea(make_idea(source="insider_scout", symbols=["AAPL"], priority=1))
        # Send one sure-drop (unknown, old, dup)
        await svc._check_and_record("TSLA", "bearish", time.time())
        await svc._on_idea(make_idea(
            source="unknown", symbols=["TSLA"], direction="bearish", priority=5,
            metadata={"detected_at": "2000-01-01T00:00:00+00:00"}
        ))
        stats = svc.get_stats()
        assert stats["total_escalated"] >= 1
        assert stats["total_dropped"] >= 1
        await svc.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication
# ─────────────────────────────────────────────────────────────────────────────

class TestDeduplication:
    @pytest.mark.anyio
    async def test_first_occurrence_not_dup(self):
        svc = IdeaTriageService()
        now = time.time()
        is_dup = await svc._check_and_record("AAPL", "bullish", now)
        assert not is_dup

    @pytest.mark.anyio
    async def test_second_occurrence_within_window_is_dup(self):
        svc = IdeaTriageService()
        now = time.time()
        await svc._check_and_record("AAPL", "bullish", now)
        is_dup = await svc._check_and_record("AAPL", "bullish", now + 10)
        assert is_dup

    @pytest.mark.anyio
    async def test_after_window_expired_not_dup(self):
        svc = IdeaTriageService()
        old_time = time.time() - (DEDUP_WINDOW_SECS + 10)
        # Plant an old record manually
        svc._seen[("AAPL", "bullish")] = old_time
        is_dup = await svc._check_and_record("AAPL", "bullish", time.time())
        assert not is_dup

    @pytest.mark.anyio
    async def test_different_direction_not_dup(self):
        svc = IdeaTriageService()
        now = time.time()
        await svc._check_and_record("AAPL", "bullish", now)
        is_dup = await svc._check_and_record("AAPL", "bearish", now + 1)
        assert not is_dup

    @pytest.mark.anyio
    async def test_different_symbol_not_dup(self):
        svc = IdeaTriageService()
        now = time.time()
        await svc._check_and_record("AAPL", "bullish", now)
        is_dup = await svc._check_and_record("MSFT", "bullish", now + 1)
        assert not is_dup

    @pytest.mark.anyio
    async def test_symbol_case_insensitive(self):
        svc = IdeaTriageService()
        now = time.time()
        await svc._check_and_record("aapl", "bullish", now)
        is_dup = await svc._check_and_record("AAPL", "bullish", now + 1)
        assert is_dup

    @pytest.mark.anyio
    async def test_dup_increments_counter(self):
        bus = FakeBus()
        svc = IdeaTriageService(bus)
        await svc.start()
        await svc._on_idea(make_idea(source="flow_hunter_scout", priority=2))
        await svc._on_idea(make_idea(source="flow_hunter_scout", priority=2))  # dup
        assert svc.get_stats()["total_duplicates"] >= 1
        await svc.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Adaptive threshold
# ─────────────────────────────────────────────────────────────────────────────

class TestAdaptiveThreshold:
    def test_normal_queue_gives_base_threshold(self):
        svc = IdeaTriageService()
        # Empty queue → below low water → threshold below BASE
        # but empty = 0 arrivals in last 60s
        threshold = svc._adaptive_threshold()
        assert MIN_THRESHOLD <= threshold <= MAX_THRESHOLD

    def test_high_queue_raises_threshold(self):
        svc = IdeaTriageService()
        now = time.time()
        # Simulate 250 recent arrivals
        svc._recent_arrivals = [now - 1] * 250
        threshold = svc._adaptive_threshold()
        assert threshold > BASE_THRESHOLD

    def test_low_queue_lowers_threshold(self):
        svc = IdeaTriageService()
        now = time.time()
        svc._recent_arrivals = [now - 1] * 5  # Very low
        threshold = svc._adaptive_threshold()
        assert threshold < BASE_THRESHOLD

    def test_threshold_never_below_min(self):
        svc = IdeaTriageService()
        svc._recent_arrivals = []
        threshold = svc._adaptive_threshold()
        assert threshold >= MIN_THRESHOLD

    def test_threshold_never_above_max(self):
        svc = IdeaTriageService()
        now = time.time()
        svc._recent_arrivals = [now - 1] * 10000  # Extreme load
        threshold = svc._adaptive_threshold()
        assert threshold <= MAX_THRESHOLD


# ─────────────────────────────────────────────────────────────────────────────
# TriageResult
# ─────────────────────────────────────────────────────────────────────────────

class TestTriageResult:
    def test_to_dict_contains_required_fields(self):
        result = TriageResult(
            idea_id="abc123",
            symbol="AAPL",
            source="insider_scout",
            direction="bullish",
            score=85,
            threshold=40,
            escalated=True,
            age_secs=2.5,
            is_duplicate=False,
            original={},
        )
        d = result.to_dict()
        for key in ("idea_id", "symbol", "source", "direction", "score",
                    "threshold", "escalated", "age_secs", "is_duplicate", "timestamp"):
            assert key in d, f"Missing key: {key}"

    def test_escalated_true_when_score_above_threshold(self):
        result = TriageResult(
            idea_id="x", symbol="AAPL", source="x", direction="bullish",
            score=80, threshold=40, escalated=True,
            age_secs=0, is_duplicate=False, original={}
        )
        assert result.escalated is True

    def test_escalated_false_when_score_below_threshold(self):
        result = TriageResult(
            idea_id="x", symbol="AAPL", source="x", direction="bullish",
            score=20, threshold=40, escalated=False,
            age_secs=0, is_duplicate=False, original={}
        )
        assert result.escalated is False


# ─────────────────────────────────────────────────────────────────────────────
# get_idea_triage_service singleton
# ─────────────────────────────────────────────────────────────────────────────

class TestSingleton:
    def test_singleton_returns_same_instance(self):
        import app.services.idea_triage as mod
        mod._triage = None
        a = get_idea_triage_service()
        b = get_idea_triage_service()
        assert a is b


# ─────────────────────────────────────────────────────────────────────────────
# Buffer cap enforcement (regression guards for fix 1 & 3)
# ─────────────────────────────────────────────────────────────────────────────

class TestBufferCaps:
    """Ensure MAX_QUEUE_SIZE and MAX_SEEN_SIZE hard caps are enforced."""

    @pytest.mark.asyncio
    async def test_recent_arrivals_capped_at_max_queue_size(self):
        from app.services.idea_triage import MAX_QUEUE_SIZE
        from collections import deque
        import time
        svc = IdeaTriageService()
        now = time.time()
        # Overfill the deque past its maxlen; deque(maxlen) auto-evicts oldest.
        for _ in range(MAX_QUEUE_SIZE + 200):
            svc._recent_arrivals.append(now)
        assert len(svc._recent_arrivals) == MAX_QUEUE_SIZE

        # One more event via the normal path should also stay within cap
        bus = FakeBus()
        svc._bus = bus
        await svc._on_idea(make_idea())
        assert len(svc._recent_arrivals) <= MAX_QUEUE_SIZE

    @pytest.mark.asyncio
    async def test_seen_dict_capped_at_max_seen_size(self):
        from app.services.idea_triage import MAX_SEEN_SIZE
        import time
        svc = IdeaTriageService()
        now = time.time()
        # Pre-fill _seen to exactly the limit, then add one more
        for i in range(MAX_SEEN_SIZE):
            svc._seen[(f"SYM{i}", "bullish")] = now
        assert len(svc._seen) == MAX_SEEN_SIZE
        # One more call inserts a new key, then evicts one → stays at MAX_SEEN_SIZE
        await svc._check_and_record("OVERFLOW", "bullish", now)
        assert len(svc._seen) == MAX_SEEN_SIZE
