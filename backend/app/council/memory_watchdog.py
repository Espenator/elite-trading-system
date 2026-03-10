"""Memory Watchdog — monitors layered_memory_agent health and memory usage.

Tracks memory size, staleness, query performance, and pattern quality to ensure
the layered memory system remains efficient and effective.

Integration: Called by self_awareness.py to monitor memory system health.
"""
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MemoryWatchdog:
    """Monitors layered_memory_agent performance and memory health.

    Tracks:
    - Memory store size (count of entries per layer)
    - Memory staleness (age of oldest/newest entries)
    - Query latency (time to recall from each layer)
    - Pattern quality (hit rate, signal strength)
    - Memory growth rate (entries added per hour)
    """

    def __init__(self):
        self._stats = {
            "short_term_size": 0,
            "mid_term_size": 0,
            "long_term_size": 0,
            "reflection_size": 0,
            "query_count": 0,
            "total_query_latency_ms": 0.0,
            "pattern_hits": 0,
            "pattern_misses": 0,
            "last_check": time.time(),
            "growth_history": defaultdict(list),  # layer -> [(timestamp, size)]
        }
        self._health_status = "healthy"
        self._last_warning: Optional[str] = None

    async def check_health(self) -> Dict[str, Any]:
        """Run health checks on the memory system.

        Returns:
            Dict with health status, metrics, and any warnings.
        """
        now = time.time()
        metrics = await self._collect_metrics()

        # Check for issues
        warnings = []

        # 1. Check memory size limits
        if metrics["short_term_size"] > 10000:
            warnings.append(f"Short-term memory too large: {metrics['short_term_size']} entries")
        if metrics["mid_term_size"] > 1000:
            warnings.append(f"Mid-term memory too large: {metrics['mid_term_size']} entries")

        # 2. Check staleness
        if metrics.get("oldest_short_term_age_hours", 0) > 120:  # 5 days
            warnings.append("Short-term memory contains stale entries")

        # 3. Check query performance
        avg_query_ms = metrics.get("avg_query_latency_ms", 0)
        if avg_query_ms > 100:
            warnings.append(f"Slow memory queries: {avg_query_ms:.1f}ms average")

        # 4. Check pattern quality
        pattern_hit_rate = metrics.get("pattern_hit_rate", 0)
        if pattern_hit_rate < 0.3 and metrics["query_count"] > 100:
            warnings.append(f"Low pattern hit rate: {pattern_hit_rate:.1%}")

        # 5. Check growth rate (unhealthy if growing too fast)
        growth_rate = metrics.get("growth_rate_per_hour", 0)
        if growth_rate > 500:
            warnings.append(f"Memory growing too fast: {growth_rate:.0f} entries/hour")

        # Update health status
        if warnings:
            self._health_status = "degraded" if len(warnings) <= 2 else "unhealthy"
            self._last_warning = "; ".join(warnings)
        else:
            self._health_status = "healthy"
            self._last_warning = None

        return {
            "health_status": self._health_status,
            "metrics": metrics,
            "warnings": warnings,
            "timestamp": now,
        }

    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current metrics from memory system."""
        metrics = {
            "short_term_size": self._stats["short_term_size"],
            "mid_term_size": self._stats["mid_term_size"],
            "long_term_size": self._stats["long_term_size"],
            "reflection_size": self._stats["reflection_size"],
            "query_count": self._stats["query_count"],
            "pattern_hit_rate": 0.0,
            "avg_query_latency_ms": 0.0,
            "growth_rate_per_hour": 0.0,
        }

        # Calculate derived metrics
        if self._stats["query_count"] > 0:
            metrics["avg_query_latency_ms"] = (
                self._stats["total_query_latency_ms"] / self._stats["query_count"]
            )

        total_pattern_checks = self._stats["pattern_hits"] + self._stats["pattern_misses"]
        if total_pattern_checks > 0:
            metrics["pattern_hit_rate"] = self._stats["pattern_hits"] / total_pattern_checks

        # Try to get actual memory sizes from layered_memory_agent
        try:
            from app.council.agents.layered_memory_agent import _memory_store

            metrics["short_term_size"] = sum(
                len(trades) for trades in _memory_store["short_term"].values()
            )
            metrics["mid_term_size"] = len(_memory_store["mid_term"])
            metrics["long_term_size"] = len(_memory_store["long_term"])
            metrics["reflection_size"] = len(_memory_store["reflection"])

            # Update internal stats
            self._stats["short_term_size"] = metrics["short_term_size"]
            self._stats["mid_term_size"] = metrics["mid_term_size"]
            self._stats["long_term_size"] = metrics["long_term_size"]
            self._stats["reflection_size"] = metrics["reflection_size"]

            # Calculate staleness
            oldest_age_hours = await self._get_oldest_entry_age(_memory_store)
            if oldest_age_hours is not None:
                metrics["oldest_short_term_age_hours"] = oldest_age_hours

        except Exception as e:
            logger.debug("Failed to collect memory metrics: %s", e)

        # Calculate growth rate
        now = time.time()
        total_size = sum([
            metrics["short_term_size"],
            metrics["mid_term_size"],
            metrics["long_term_size"],
        ])
        self._stats["growth_history"]["total"].append((now, total_size))

        # Keep only last hour of growth history
        cutoff = now - 3600
        self._stats["growth_history"]["total"] = [
            (t, s) for t, s in self._stats["growth_history"]["total"] if t > cutoff
        ]

        if len(self._stats["growth_history"]["total"]) >= 2:
            oldest = self._stats["growth_history"]["total"][0]
            newest = self._stats["growth_history"]["total"][-1]
            time_delta = newest[0] - oldest[0]
            size_delta = newest[1] - oldest[1]
            if time_delta > 0:
                metrics["growth_rate_per_hour"] = size_delta / (time_delta / 3600)

        return metrics

    async def _get_oldest_entry_age(self, memory_store: Dict) -> Optional[float]:
        """Get age in hours of oldest short-term entry."""
        try:
            oldest_timestamp = None
            for trades in memory_store["short_term"].values():
                for trade in trades:
                    ts = trade.get("timestamp")
                    if ts:
                        try:
                            if isinstance(ts, str):
                                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            elif isinstance(ts, float):
                                ts = datetime.fromtimestamp(ts, tz=timezone.utc)

                            if oldest_timestamp is None or ts < oldest_timestamp:
                                oldest_timestamp = ts
                        except Exception:
                            pass

            if oldest_timestamp:
                age_delta = datetime.now(timezone.utc) - oldest_timestamp
                return age_delta.total_seconds() / 3600

        except Exception as e:
            logger.debug("Failed to calculate oldest entry age: %s", e)

        return None

    def record_query(self, latency_ms: float, found_pattern: bool = False):
        """Record a memory query for performance tracking."""
        self._stats["query_count"] += 1
        self._stats["total_query_latency_ms"] += latency_ms

        if found_pattern:
            self._stats["pattern_hits"] += 1
        else:
            self._stats["pattern_misses"] += 1

    def get_status(self) -> Dict[str, Any]:
        """Get current watchdog status without running checks."""
        return {
            "health_status": self._health_status,
            "last_warning": self._last_warning,
            "query_count": self._stats["query_count"],
            "last_check": self._stats["last_check"],
        }

    async def suggest_cleanup(self) -> Dict[str, Any]:
        """Suggest cleanup actions if memory is unhealthy."""
        suggestions = []
        metrics = await self._collect_metrics()

        if metrics["short_term_size"] > 5000:
            suggestions.append({
                "action": "prune_short_term",
                "reason": f"Short-term has {metrics['short_term_size']} entries",
                "target_size": 2000,
            })

        if metrics.get("oldest_short_term_age_hours", 0) > 120:
            suggestions.append({
                "action": "decay_stale_entries",
                "reason": "Short-term contains entries older than 5 days",
                "decay_threshold_hours": 120,
            })

        if metrics.get("avg_query_latency_ms", 0) > 100:
            suggestions.append({
                "action": "optimize_indexes",
                "reason": f"Slow queries: {metrics['avg_query_latency_ms']:.1f}ms average",
            })

        return {
            "suggestions": suggestions,
            "metrics": metrics,
        }


# Singleton
_watchdog: Optional[MemoryWatchdog] = None


def get_memory_watchdog() -> MemoryWatchdog:
    """Get or create the singleton MemoryWatchdog."""
    global _watchdog
    if _watchdog is None:
        _watchdog = MemoryWatchdog()
    return _watchdog
