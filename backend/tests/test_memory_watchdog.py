"""Tests for memory_watchdog.py — layered_memory_agent health monitoring.

Tests the MemoryWatchdog class that monitors memory size, staleness, query
performance, and pattern quality.
"""
import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.council.memory_watchdog import MemoryWatchdog, get_memory_watchdog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def watchdog():
    """Create a fresh MemoryWatchdog instance."""
    return MemoryWatchdog()


@pytest.fixture
def mock_memory_store():
    """Mock layered_memory_agent memory store."""
    now = datetime.now(timezone.utc)
    return {
        "short_term": {
            "AAPL": [
                {"timestamp": now - timedelta(hours=2), "outcome": "win"},
                {"timestamp": now - timedelta(hours=4), "outcome": "loss"},
            ],
            "MSFT": [
                {"timestamp": now - timedelta(hours=1), "outcome": "win"},
            ],
        },
        "mid_term": {
            "tech": {"pattern": "bullish", "confidence": 0.7},
            "finance": {"pattern": "bearish", "confidence": 0.6},
        },
        "long_term": {
            "bull": {"transitions": 15, "avg_duration_days": 45},
        },
        "reflection": {
            "overall_win_rate": 0.58,
            "total_trades": 250,
        },
    }


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------

class TestMemoryWatchdogInit:
    def test_initial_state(self, watchdog):
        """Test watchdog initializes with correct default state."""
        status = watchdog.get_status()
        assert status["health_status"] == "healthy"
        assert status["last_warning"] is None
        assert status["query_count"] == 0

    def test_singleton_pattern(self):
        """Test get_memory_watchdog returns singleton."""
        w1 = get_memory_watchdog()
        w2 = get_memory_watchdog()
        assert w1 is w2


# ---------------------------------------------------------------------------
# Query Recording Tests
# ---------------------------------------------------------------------------

class TestQueryRecording:
    def test_record_query_with_pattern(self, watchdog):
        """Test recording a query that found a pattern."""
        watchdog.record_query(latency_ms=15.5, found_pattern=True)

        status = watchdog.get_status()
        assert status["query_count"] == 1
        assert watchdog._stats["pattern_hits"] == 1
        assert watchdog._stats["pattern_misses"] == 0
        assert watchdog._stats["total_query_latency_ms"] == 15.5

    def test_record_query_without_pattern(self, watchdog):
        """Test recording a query that didn't find a pattern."""
        watchdog.record_query(latency_ms=8.2, found_pattern=False)

        status = watchdog.get_status()
        assert status["query_count"] == 1
        assert watchdog._stats["pattern_hits"] == 0
        assert watchdog._stats["pattern_misses"] == 1

    def test_multiple_queries(self, watchdog):
        """Test recording multiple queries."""
        watchdog.record_query(10.0, found_pattern=True)
        watchdog.record_query(20.0, found_pattern=False)
        watchdog.record_query(30.0, found_pattern=True)

        assert watchdog._stats["query_count"] == 3
        assert watchdog._stats["pattern_hits"] == 2
        assert watchdog._stats["pattern_misses"] == 1
        assert watchdog._stats["total_query_latency_ms"] == 60.0


# ---------------------------------------------------------------------------
# Metrics Collection Tests
# ---------------------------------------------------------------------------

class TestMetricsCollection:
    @pytest.mark.anyio
    async def test_collect_metrics_with_memory_store(self, watchdog, mock_memory_store):
        """Test collecting metrics from actual memory store."""
        with patch(
            "app.council.memory_watchdog._memory_store",
            new=mock_memory_store,
        ):
            metrics = await watchdog._collect_metrics()

        assert metrics["short_term_size"] == 3  # 2 AAPL + 1 MSFT
        assert metrics["mid_term_size"] == 2   # tech + finance
        assert metrics["long_term_size"] == 1  # bull
        assert metrics["reflection_size"] == 1

    @pytest.mark.anyio
    async def test_collect_metrics_calculates_hit_rate(self, watchdog):
        """Test pattern hit rate calculation."""
        watchdog._stats["pattern_hits"] = 7
        watchdog._stats["pattern_misses"] = 3

        metrics = await watchdog._collect_metrics()
        assert metrics["pattern_hit_rate"] == 0.7  # 7 / (7+3)

    @pytest.mark.anyio
    async def test_collect_metrics_calculates_avg_latency(self, watchdog):
        """Test average query latency calculation."""
        watchdog._stats["query_count"] = 10
        watchdog._stats["total_query_latency_ms"] = 150.0

        metrics = await watchdog._collect_metrics()
        assert metrics["avg_query_latency_ms"] == 15.0  # 150 / 10

    @pytest.mark.anyio
    async def test_collect_metrics_growth_rate(self, watchdog):
        """Test growth rate calculation."""
        now = time.time()
        # Simulate growth over 1 hour
        watchdog._stats["growth_history"]["total"] = [
            (now - 3600, 100),  # 1 hour ago: 100 entries
            (now, 600),         # now: 600 entries
        ]

        watchdog._stats["short_term_size"] = 400
        watchdog._stats["mid_term_size"] = 150
        watchdog._stats["long_term_size"] = 50

        metrics = await watchdog._collect_metrics()
        # Growth rate = 500 entries per hour
        assert metrics["growth_rate_per_hour"] == 500.0

    @pytest.mark.anyio
    async def test_collect_metrics_handles_import_error(self, watchdog):
        """Test graceful handling when memory_store import fails."""
        with patch(
            "app.council.memory_watchdog._memory_store",
            side_effect=ImportError("Module not found"),
        ):
            metrics = await watchdog._collect_metrics()

        # Should return default metrics without crashing
        assert "short_term_size" in metrics
        assert "mid_term_size" in metrics


# ---------------------------------------------------------------------------
# Health Check Tests
# ---------------------------------------------------------------------------

class TestHealthChecks:
    @pytest.mark.anyio
    async def test_healthy_state(self, watchdog, mock_memory_store):
        """Test health check when everything is healthy."""
        with patch(
            "app.council.memory_watchdog._memory_store",
            new=mock_memory_store,
        ):
            health = await watchdog.check_health()

        assert health["health_status"] == "healthy"
        assert len(health["warnings"]) == 0

    @pytest.mark.anyio
    async def test_short_term_memory_too_large(self, watchdog):
        """Test warning when short-term memory exceeds threshold."""
        large_store = {
            "short_term": {f"SYM{i}": [{"ts": time.time()}] for i in range(10001)},
            "mid_term": {},
            "long_term": {},
            "reflection": {},
        }

        with patch(
            "app.council.memory_watchdog._memory_store",
            new=large_store,
        ):
            health = await watchdog.check_health()

        assert health["health_status"] in ["degraded", "unhealthy"]
        assert any("too large" in w for w in health["warnings"])

    @pytest.mark.anyio
    async def test_slow_queries_warning(self, watchdog):
        """Test warning when queries are too slow."""
        # Record slow queries
        for _ in range(10):
            watchdog.record_query(150.0, found_pattern=True)  # 150ms each

        health = await watchdog.check_health()

        assert health["health_status"] in ["degraded", "unhealthy"]
        assert any("Slow memory queries" in w for w in health["warnings"])

    @pytest.mark.anyio
    async def test_low_pattern_hit_rate_warning(self, watchdog):
        """Test warning when pattern hit rate is too low."""
        # Record many misses
        for _ in range(150):
            watchdog.record_query(10.0, found_pattern=False)
        for _ in range(50):
            watchdog.record_query(10.0, found_pattern=True)

        health = await watchdog.check_health()

        assert health["health_status"] in ["degraded", "unhealthy"]
        assert any("Low pattern hit rate" in w for w in health["warnings"])

    @pytest.mark.anyio
    async def test_fast_growth_rate_warning(self, watchdog):
        """Test warning when memory is growing too fast."""
        now = time.time()
        # Simulate very fast growth (1000 entries in 1 hour)
        watchdog._stats["growth_history"]["total"] = [
            (now - 3600, 0),
            (now, 1000),
        ]
        watchdog._stats["short_term_size"] = 1000

        health = await watchdog.check_health()

        assert health["health_status"] in ["degraded", "unhealthy"]
        assert any("growing too fast" in w for w in health["warnings"])

    @pytest.mark.anyio
    async def test_stale_entries_warning(self, watchdog):
        """Test warning when entries are too old."""
        # Mock very old entries
        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        stale_store = {
            "short_term": {
                "AAPL": [{"timestamp": old_time}],
            },
            "mid_term": {},
            "long_term": {},
            "reflection": {},
        }

        with patch(
            "app.council.memory_watchdog._memory_store",
            new=stale_store,
        ):
            health = await watchdog.check_health()

        assert health["health_status"] in ["degraded", "unhealthy"]
        assert any("stale" in w for w in health["warnings"])

    @pytest.mark.anyio
    async def test_multiple_warnings_degrade_health(self, watchdog):
        """Test that multiple warnings make status unhealthy."""
        # Trigger multiple issues
        for _ in range(200):
            watchdog.record_query(150.0, found_pattern=False)

        large_stale_store = {
            "short_term": {f"SYM{i}": [{"timestamp": datetime.now(timezone.utc) - timedelta(days=10)}] for i in range(11000)},
            "mid_term": {},
            "long_term": {},
            "reflection": {},
        }

        with patch(
            "app.council.memory_watchdog._memory_store",
            new=large_stale_store,
        ):
            health = await watchdog.check_health()

        assert health["health_status"] == "unhealthy"
        assert len(health["warnings"]) >= 3


# ---------------------------------------------------------------------------
# Cleanup Suggestions Tests
# ---------------------------------------------------------------------------

class TestCleanupSuggestions:
    @pytest.mark.anyio
    async def test_suggest_prune_when_large(self, watchdog):
        """Test cleanup suggestions when memory is large."""
        large_store = {
            "short_term": {f"SYM{i}": [{"ts": time.time()}] for i in range(6000)},
            "mid_term": {},
            "long_term": {},
            "reflection": {},
        }

        with patch(
            "app.council.memory_watchdog._memory_store",
            new=large_store,
        ):
            suggestions = await watchdog.suggest_cleanup()

        assert len(suggestions["suggestions"]) > 0
        prune_suggestion = next(
            (s for s in suggestions["suggestions"] if s["action"] == "prune_short_term"),
            None,
        )
        assert prune_suggestion is not None
        assert prune_suggestion["target_size"] == 2000

    @pytest.mark.anyio
    async def test_suggest_decay_when_stale(self, watchdog):
        """Test cleanup suggestions when entries are stale."""
        old_time = datetime.now(timezone.utc) - timedelta(days=7)
        stale_store = {
            "short_term": {
                "AAPL": [{"timestamp": old_time}],
            },
            "mid_term": {},
            "long_term": {},
            "reflection": {},
        }

        with patch(
            "app.council.memory_watchdog._memory_store",
            new=stale_store,
        ):
            suggestions = await watchdog.suggest_cleanup()

        decay_suggestion = next(
            (s for s in suggestions["suggestions"] if s["action"] == "decay_stale_entries"),
            None,
        )
        assert decay_suggestion is not None

    @pytest.mark.anyio
    async def test_suggest_optimize_when_slow(self, watchdog):
        """Test cleanup suggestions when queries are slow."""
        for _ in range(20):
            watchdog.record_query(150.0, found_pattern=True)

        suggestions = await watchdog.suggest_cleanup()

        optimize_suggestion = next(
            (s for s in suggestions["suggestions"] if s["action"] == "optimize_indexes"),
            None,
        )
        assert optimize_suggestion is not None

    @pytest.mark.anyio
    async def test_no_suggestions_when_healthy(self, watchdog, mock_memory_store):
        """Test no cleanup suggestions when memory is healthy."""
        with patch(
            "app.council.memory_watchdog._memory_store",
            new=mock_memory_store,
        ):
            suggestions = await watchdog.suggest_cleanup()

        assert len(suggestions["suggestions"]) == 0


# ---------------------------------------------------------------------------
# Oldest Entry Age Tests
# ---------------------------------------------------------------------------

class TestOldestEntryAge:
    @pytest.mark.anyio
    async def test_calculate_oldest_entry_age(self, watchdog):
        """Test calculation of oldest entry age."""
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=72)  # 3 days ago

        store = {
            "short_term": {
                "AAPL": [
                    {"timestamp": now - timedelta(hours=1)},
                    {"timestamp": old_time},  # Oldest
                    {"timestamp": now - timedelta(hours=24)},
                ],
            },
            "mid_term": {},
            "long_term": {},
            "reflection": {},
        }

        age_hours = await watchdog._get_oldest_entry_age(store)

        assert age_hours is not None
        assert abs(age_hours - 72.0) < 1.0  # Should be ~72 hours

    @pytest.mark.anyio
    async def test_oldest_entry_age_with_timestamp_float(self, watchdog):
        """Test oldest entry age with Unix timestamp (float)."""
        now = time.time()
        old_time = now - (48 * 3600)  # 48 hours ago

        store = {
            "short_term": {
                "MSFT": [
                    {"timestamp": now},
                    {"timestamp": old_time},
                ],
            },
            "mid_term": {},
            "long_term": {},
            "reflection": {},
        }

        age_hours = await watchdog._get_oldest_entry_age(store)

        assert age_hours is not None
        assert abs(age_hours - 48.0) < 1.0

    @pytest.mark.anyio
    async def test_oldest_entry_age_with_no_entries(self, watchdog):
        """Test oldest entry age when there are no entries."""
        store = {
            "short_term": {},
            "mid_term": {},
            "long_term": {},
            "reflection": {},
        }

        age_hours = await watchdog._get_oldest_entry_age(store)

        assert age_hours is None
