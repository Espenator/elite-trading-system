"""Data Source Health Aggregator — unified health view across all data sources.

Aggregates health from:
  - health_registry.py (subsystem states)
  - llm_health_monitor.py (LLM provider health)
  - ingestion/registry.py (adapter health)
  - off_hours_monitor.py (data freshness)
  - alpaca_service.py (market data + account)
  - Brain Service (gRPC)

Publishes alerts via SlackAlerter when sources go down or degrade.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")

# How often to run the aggregation loop
HEALTH_CHECK_INTERVAL = 60  # seconds


class DataSourceHealthAggregator:
    """Unified health monitoring for all data sources."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._last_check = 0.0
        self._health_cache: Dict[str, Dict] = {}
        self._incident_log: List[Dict] = []
        self._check_count = 0

    async def start(self):
        """Start the health aggregation loop."""
        self._running = True
        asyncio.create_task(self._health_check_loop())
        logger.info("DataSourceHealthAggregator started")

    async def stop(self):
        """Stop monitoring."""
        self._running = False
        logger.info("DataSourceHealthAggregator stopped")

    async def _health_check_loop(self):
        """Periodically aggregate health from all sources."""
        while self._running:
            try:
                await self._run_health_check()
            except Exception as e:
                logger.warning("Health check error: %s", e)
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

    async def _run_health_check(self):
        """Run a single health check cycle."""
        self._check_count += 1
        self._last_check = time.time()
        results = {}

        # 1. Health Registry (subsystem states)
        try:
            from app.services.health_registry import get_all_health
            registry = get_all_health()
            for name, info in registry.items():
                results[f"subsystem:{name}"] = {
                    "name": name,
                    "category": "subsystem",
                    "status": info.get("state", "unknown"),
                    "last_update": info.get("last_update", ""),
                    "details": info.get("detail", ""),
                }
        except Exception as e:
            logger.debug("Health registry check failed: %s", e)

        # 2. LLM Health Monitor
        try:
            from app.services.llm_health_monitor import get_llm_health_monitor
            llm_mon = get_llm_health_monitor()
            for provider, state in llm_mon.provider_states.items():
                status = "healthy"
                if state.circuit_open:
                    status = "unavailable"
                elif state.health_pct < 50:
                    status = "degraded"
                results[f"llm:{provider}"] = {
                    "name": provider,
                    "category": "llm_provider",
                    "status": status,
                    "health_pct": state.health_pct,
                    "consecutive_failures": state.consecutive_failures,
                    "circuit_open": state.circuit_open,
                }
        except Exception as e:
            logger.debug("LLM health check failed: %s", e)

        # 3. Adapter Registry
        try:
            from app.services.ingestion.registry import get_adapter_registry
            registry = get_adapter_registry()
            adapter_health = registry.health_check_all()
            for name, info in adapter_health.items():
                results[f"adapter:{name}"] = {
                    "name": name,
                    "category": "data_adapter",
                    "status": "healthy" if info.get("healthy") else "degraded",
                    "last_run": info.get("last_run", ""),
                    "last_error": info.get("last_error", ""),
                    "run_count": info.get("run_count", 0),
                }
        except Exception as e:
            logger.debug("Adapter registry check failed: %s", e)

        # 4. Alpaca Connection
        try:
            from app.services.alpaca_service import alpaca_service
            account = await alpaca_service.get_account()
            if account and account.get("equity"):
                results["broker:alpaca"] = {
                    "name": "Alpaca Markets",
                    "category": "broker",
                    "status": "healthy",
                    "equity": float(account.get("equity", 0)),
                    "buying_power": float(account.get("buying_power", 0)),
                    "account_status": account.get("status", "unknown"),
                }
            else:
                results["broker:alpaca"] = {
                    "name": "Alpaca Markets",
                    "category": "broker",
                    "status": "degraded",
                    "details": "No account data",
                }
        except Exception as e:
            results["broker:alpaca"] = {
                "name": "Alpaca Markets",
                "category": "broker",
                "status": "unavailable",
                "error": str(e),
            }

        # 5. Off-Hours Monitor
        try:
            from app.services.off_hours_monitor import get_off_hours_monitor
            ohm = get_off_hours_monitor()
            ohm_status = ohm.get_status()
            results["monitor:off_hours"] = {
                "name": "Off-Hours Monitor",
                "category": "monitor",
                "status": "healthy" if ohm_status.get("running") else "unavailable",
                "session": ohm_status.get("session"),
                "symbols_tracked": ohm_status.get("symbols_tracked", 0),
                "symbols_stale": ohm_status.get("symbols_stale", 0),
                "gaps_today": ohm_status.get("gaps_published", 0),
            }
        except Exception as e:
            logger.debug("Off-hours monitor check failed: %s", e)

        # 6. Brain Service (gRPC)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("http://localhost:50051/health")
                if resp.status_code == 200:
                    results["service:brain"] = {
                        "name": "Brain Service (gRPC)",
                        "category": "ai_service",
                        "status": "healthy",
                    }
                else:
                    results["service:brain"] = {
                        "name": "Brain Service (gRPC)",
                        "category": "ai_service",
                        "status": "degraded",
                        "details": f"HTTP {resp.status_code}",
                    }
        except Exception:
            results["service:brain"] = {
                "name": "Brain Service (gRPC)",
                "category": "ai_service",
                "status": "unavailable",
                "details": "Connection refused or timeout",
            }

        # Update cache
        self._health_cache = results

        # Check for incidents and alert
        await self._check_incidents(results)

        # Log summary periodically
        if self._check_count % 5 == 1:
            healthy = sum(1 for r in results.values() if r.get("status") == "healthy")
            degraded = sum(1 for r in results.values() if r.get("status") == "degraded")
            unavailable = sum(1 for r in results.values() if r.get("status") == "unavailable")
            logger.info(
                "Health check #%d: %d healthy, %d degraded, %d unavailable (of %d sources)",
                self._check_count, healthy, degraded, unavailable, len(results),
            )

    async def _check_incidents(self, results: Dict[str, Dict]):
        """Detect new incidents and send alerts."""
        for key, info in results.items():
            status = info.get("status", "unknown")
            if status in ("degraded", "unavailable"):
                # Check if this is a new incident
                incident_key = f"{key}:{status}"
                recent = any(
                    i.get("key") == incident_key
                    and time.time() - i.get("time", 0) < 300
                    for i in self._incident_log
                )
                if not recent:
                    self._incident_log.append({
                        "key": incident_key,
                        "source": info.get("name", key),
                        "status": status,
                        "time": time.time(),
                        "details": info.get("error") or info.get("details", ""),
                    })
                    # Keep only last 100 incidents
                    if len(self._incident_log) > 100:
                        self._incident_log = self._incident_log[-100:]

                    # Send Slack alert
                    try:
                        from app.services.slack_alerter import get_slack_alerter
                        alerter = get_slack_alerter()
                        await alerter.send_health_alert(
                            source_name=info.get("name", key),
                            status=status,
                            error=info.get("error") or info.get("details"),
                        )
                    except Exception:
                        pass

                    # Publish to message bus
                    if self._bus:
                        await self._bus.publish("alert.health", {
                            "source": key,
                            "name": info.get("name", key),
                            "status": status,
                            "details": info.get("error") or info.get("details", ""),
                            "timestamp": datetime.now(ET).isoformat(),
                        })

    def get_health(self) -> Dict[str, Any]:
        """Return current aggregated health status."""
        results = self._health_cache
        healthy = sum(1 for r in results.values() if r.get("status") == "healthy")
        degraded = sum(1 for r in results.values() if r.get("status") == "degraded")
        unavailable = sum(1 for r in results.values() if r.get("status") == "unavailable")
        total = len(results)

        # Compute overall status
        if unavailable > 0:
            overall = "critical" if unavailable >= 3 else "degraded"
        elif degraded > 0:
            overall = "degraded" if degraded >= 2 else "healthy"
        else:
            overall = "healthy"

        return {
            "overall_status": overall,
            "total_sources": total,
            "healthy": healthy,
            "degraded": degraded,
            "unavailable": unavailable,
            "health_pct": round(100 * healthy / max(total, 1), 1),
            "sources": results,
            "last_check": self._last_check,
            "check_count": self._check_count,
            "recent_incidents": self._incident_log[-10:],
        }

    def get_source_health(self, source_key: str) -> Optional[Dict]:
        """Get health for a specific source."""
        return self._health_cache.get(source_key)


# Module-level singleton
_aggregator: Optional[DataSourceHealthAggregator] = None


def get_health_aggregator(message_bus=None) -> DataSourceHealthAggregator:
    """Get or create the DataSourceHealthAggregator singleton."""
    global _aggregator
    if _aggregator is None:
        _aggregator = DataSourceHealthAggregator(message_bus=message_bus)
    return _aggregator
