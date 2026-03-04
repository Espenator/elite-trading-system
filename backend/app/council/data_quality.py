"""Data Quality Monitor — detects stale, missing, or anomalous data feeds.

Production trading systems fail most often from bad data, not bad models.
This monitor tracks the health of all PNS (Peripheral Nervous System) data
sources and degrades gracefully when feeds go stale.

Monitored sources:
    - Alpaca market data (WebSocket + REST)
    - Unusual Whales options flow
    - FinViz screener
    - FRED macro data
    - SEC EDGAR filings
    - Feature pipeline output

Each source has:
    - Last successful fetch timestamp
    - Expected refresh interval
    - Quality score (0-100)
    - Staleness status (fresh/aging/stale/dead)

The HomeostasisMonitor reads data quality as a vital sign and can
degrade to DEFENSIVE mode if data sources go stale.

Usage:
    from app.council.data_quality import get_data_quality_monitor
    dqm = get_data_quality_monitor()
    dqm.record_fetch("alpaca_quotes", success=True)
    health = dqm.get_health()
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DataSourceConfig:
    """Configuration for a single data source."""
    name: str
    expected_interval_seconds: float  # How often we expect fresh data
    critical: bool = False  # If True, staleness triggers DEFENSIVE mode
    max_stale_seconds: float = 0  # After this, source is "dead" (0 = 3x interval)

    def __post_init__(self):
        if self.max_stale_seconds == 0:
            self.max_stale_seconds = self.expected_interval_seconds * 3


# Default data source configs
DEFAULT_SOURCES = [
    DataSourceConfig("alpaca_quotes", 60, critical=True),
    DataSourceConfig("alpaca_positions", 300, critical=True),
    DataSourceConfig("alpaca_account", 300, critical=True),
    DataSourceConfig("unusual_whales_flow", 900),  # 15 min
    DataSourceConfig("finviz_screener", 3600),  # 1 hour
    DataSourceConfig("fred_macro", 86400),  # Daily
    DataSourceConfig("feature_pipeline", 300, critical=True),  # 5 min
    DataSourceConfig("intelligence_cache", 120),  # 2 min
]


@dataclass
class SourceHealth:
    """Health state of a single data source."""
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    total_fetches: int = 0
    total_failures: int = 0
    last_error: str = ""
    last_record_count: int = 0


class DataQualityMonitor:
    """Monitors health and freshness of all data sources."""

    def __init__(self, sources: List[DataSourceConfig] = None):
        self._sources: Dict[str, DataSourceConfig] = {}
        self._health: Dict[str, SourceHealth] = {}

        for src in (sources or DEFAULT_SOURCES):
            self._sources[src.name] = src
            self._health[src.name] = SourceHealth()

    def register_source(self, config: DataSourceConfig):
        """Register a new data source to monitor."""
        self._sources[config.name] = config
        if config.name not in self._health:
            self._health[config.name] = SourceHealth()

    def record_fetch(
        self, source_name: str, success: bool = True,
        record_count: int = 0, error: str = "",
    ):
        """Record a data fetch attempt (success or failure)."""
        if source_name not in self._health:
            self._health[source_name] = SourceHealth()
            if source_name not in self._sources:
                self._sources[source_name] = DataSourceConfig(source_name, 300)

        h = self._health[source_name]
        h.total_fetches += 1

        if success:
            h.last_success = time.time()
            h.consecutive_failures = 0
            h.last_record_count = record_count
        else:
            h.last_failure = time.time()
            h.consecutive_failures += 1
            h.total_failures += 1
            h.last_error = error
            if h.consecutive_failures >= 3:
                logger.warning(
                    "Data source '%s' has %d consecutive failures: %s",
                    source_name, h.consecutive_failures, error,
                )

    def get_source_status(self, source_name: str) -> Dict[str, Any]:
        """Get detailed status for a single source."""
        config = self._sources.get(source_name)
        health = self._health.get(source_name)
        if not config or not health:
            return {"error": f"Unknown source: {source_name}"}

        now = time.time()
        age = now - health.last_success if health.last_success > 0 else float("inf")
        freshness = self._compute_freshness(age, config)
        quality_score = self._compute_quality(health, config)

        return {
            "name": source_name,
            "freshness": freshness,
            "age_seconds": round(age, 1) if age != float("inf") else None,
            "quality_score": quality_score,
            "critical": config.critical,
            "expected_interval": config.expected_interval_seconds,
            "consecutive_failures": health.consecutive_failures,
            "total_fetches": health.total_fetches,
            "error_rate": round(health.total_failures / max(health.total_fetches, 1), 3),
            "last_error": health.last_error if health.consecutive_failures > 0 else "",
            "last_record_count": health.last_record_count,
        }

    def get_health(self) -> Dict[str, Any]:
        """Get health summary across all sources."""
        sources = {}
        critical_stale = []
        overall_score = 0
        source_count = len(self._sources)

        for name in self._sources:
            status = self.get_source_status(name)
            sources[name] = status
            overall_score += status.get("quality_score", 0)

            if status.get("critical") and status.get("freshness") in ("stale", "dead"):
                critical_stale.append(name)

        avg_score = overall_score / max(source_count, 1)

        return {
            "overall_quality_score": round(avg_score, 1),
            "sources": sources,
            "critical_stale": critical_stale,
            "should_degrade": len(critical_stale) > 0,
            "degradation_reason": (
                f"Critical sources stale: {', '.join(critical_stale)}"
                if critical_stale else None
            ),
            "source_count": source_count,
        }

    def should_degrade(self) -> bool:
        """Quick check: should the system degrade to DEFENSIVE mode?"""
        for name, config in self._sources.items():
            if not config.critical:
                continue
            health = self._health.get(name)
            if not health or health.last_success == 0:
                continue  # Never fetched — not a degradation signal
            age = time.time() - health.last_success
            if age > config.max_stale_seconds:
                return True
        return False

    def get_quality_score(self) -> float:
        """Return aggregate quality score (0-100) for HomeostasisMonitor."""
        total = 0
        count = 0
        for name in self._sources:
            health = self._health.get(name)
            if health and health.total_fetches > 0:
                total += self._compute_quality(health, self._sources[name])
                count += 1
        return round(total / max(count, 1), 1)

    def _compute_freshness(self, age_seconds: float, config: DataSourceConfig) -> str:
        if age_seconds == float("inf"):
            return "unknown"
        if age_seconds <= config.expected_interval_seconds:
            return "fresh"
        if age_seconds <= config.expected_interval_seconds * 2:
            return "aging"
        if age_seconds <= config.max_stale_seconds:
            return "stale"
        return "dead"

    def _compute_quality(self, health: SourceHealth, config: DataSourceConfig) -> float:
        """Compute quality score 0-100 from health metrics."""
        if health.total_fetches == 0:
            return 50  # No data yet, neutral

        score = 100.0

        # Penalize for failures
        error_rate = health.total_failures / max(health.total_fetches, 1)
        score -= error_rate * 40  # Up to -40 for 100% error rate

        # Penalize for staleness
        if health.last_success > 0 and config.expected_interval_seconds > 0:
            age = time.time() - health.last_success
            staleness_ratio = age / config.expected_interval_seconds
            if staleness_ratio > 1:
                score -= min(30, (staleness_ratio - 1) * 10)

        # Penalize for consecutive failures
        score -= min(20, health.consecutive_failures * 5)

        return max(0, round(score, 1))


# Singleton
_monitor: Optional[DataQualityMonitor] = None


def get_data_quality_monitor() -> DataQualityMonitor:
    global _monitor
    if _monitor is None:
        _monitor = DataQualityMonitor()
    return _monitor
