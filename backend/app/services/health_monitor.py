"""Embodier Trader — Auto-Debug Health Monitor.

Continuously monitors all system components and provides:
- Service health status (backend, brain, Ollama, data sources)
- Auto-diagnostic reports when issues detected
- Self-healing actions (reconnect data sources, clear stale caches)
- API endpoint integration via /api/v1/health/deep

Designed for autonomous operation — if something breaks at 3 AM
during market hours, this module captures exactly what happened
and attempts to fix it.
"""
import asyncio
import logging
import os
import socket
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ComponentHealth:
    """Health status for a single component."""

    def __init__(self, name: str):
        self.name = name
        self.status = "unknown"
        self.last_check: Optional[datetime] = None
        self.last_ok: Optional[datetime] = None
        self.error_count = 0
        self.consecutive_failures = 0
        self.last_error = ""
        self.diagnostics: Dict[str, Any] = {}
        self.auto_heal_attempts = 0

    def mark_ok(self, diagnostics: Optional[Dict] = None):
        self.status = "healthy"
        self.last_check = datetime.now()
        self.last_ok = datetime.now()
        self.consecutive_failures = 0
        self.last_error = ""
        if diagnostics:
            self.diagnostics = diagnostics

    def mark_failed(self, error: str, diagnostics: Optional[Dict] = None):
        self.status = "unhealthy"
        self.last_check = datetime.now()
        self.error_count += 1
        self.consecutive_failures += 1
        self.last_error = error
        if diagnostics:
            self.diagnostics = diagnostics

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_ok": self.last_ok.isoformat() if self.last_ok else None,
            "error_count": self.error_count,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "diagnostics": self.diagnostics,
            "auto_heal_attempts": self.auto_heal_attempts,
        }


class HealthMonitor:
    """System-wide health monitor with auto-debug and self-healing."""

    def __init__(self):
        self.components: Dict[str, ComponentHealth] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._check_interval = 30  # seconds
        self._started_at: Optional[datetime] = None

        # Register all known components
        for name in [
            "backend_api",
            "database_sqlite",
            "database_duckdb",
            "alpaca_api",
            "alpaca_stream",
            "brain_service",
            "ollama",
            "message_bus",
            "council_engine",
            "signal_engine",
            "frontend",
            "websocket",
        ]:
            self.components[name] = ComponentHealth(name)

    async def start(self):
        """Start the background health monitoring loop."""
        if self._running:
            return
        self._running = True
        self._started_at = datetime.now()
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("HealthMonitor started — checking %d components", len(self.components))

    async def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("HealthMonitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        # Initial grace period
        await asyncio.sleep(10)

        while self._running:
            try:
                await self._run_all_checks()

                # Auto-heal if issues detected
                await self._auto_heal()

                # Log summary
                self._log_summary()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("HealthMonitor loop error: %s", e)

            await asyncio.sleep(self._check_interval)

    async def _run_all_checks(self):
        """Run all health checks concurrently."""
        checks = [
            self._check_database_sqlite(),
            self._check_database_duckdb(),
            self._check_alpaca(),
            self._check_brain_service(),
            self._check_ollama(),
            self._check_message_bus(),
            self._check_council(),
            self._check_signal_engine(),
            self._check_frontend(),
        ]
        await asyncio.gather(*checks, return_exceptions=True)

    # --- Individual health checks ---

    async def _check_database_sqlite(self):
        """Check SQLite database connectivity."""
        comp = self.components["database_sqlite"]
        try:
            from app.services.database import db_service
            # Quick read test
            orders = db_service.get_recent_orders(limit=1)
            comp.mark_ok({"order_count_sample": len(orders) if orders else 0})
        except Exception as e:
            comp.mark_failed(str(e))

    async def _check_database_duckdb(self):
        """Check DuckDB connectivity."""
        comp = self.components["database_duckdb"]
        try:
            from app.data.duckdb_storage import analytics_db
            if analytics_db:
                result = analytics_db.query("SELECT 1 as test")
                comp.mark_ok({"connected": True})
            else:
                comp.mark_failed("analytics_db not initialized")
        except Exception as e:
            comp.mark_failed(str(e))

    async def _check_alpaca(self):
        """Check Alpaca API connectivity."""
        comp = self.components["alpaca_api"]
        try:
            from app.services.alpaca_service import alpaca_service
            if alpaca_service:
                account = await asyncio.to_thread(
                    lambda: alpaca_service.get_account()
                )
                if account:
                    equity = getattr(account, "equity", "unknown")
                    status = getattr(account, "status", "unknown")
                    comp.mark_ok({
                        "equity": str(equity),
                        "account_status": str(status),
                    })
                else:
                    comp.mark_failed("get_account returned None")
            else:
                comp.mark_failed("alpaca_service not initialized")
        except Exception as e:
            comp.mark_failed(str(e))

    async def _check_brain_service(self):
        """Check Brain Service (gRPC) connectivity."""
        comp = self.components["brain_service"]
        brain_host = os.getenv("BRAIN_HOST", "localhost")
        brain_port = int(os.getenv("BRAIN_PORT", "50051"))

        if not os.getenv("BRAIN_ENABLED", "false").lower() in ("true", "1", "yes"):
            comp.mark_ok({"enabled": False, "note": "Brain disabled in config"})
            return

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((brain_host, brain_port))
            sock.close()
            if result == 0:
                comp.mark_ok({"host": brain_host, "port": brain_port})
            else:
                comp.mark_failed(
                    f"Cannot reach {brain_host}:{brain_port}",
                    {"host": brain_host, "port": brain_port},
                )
        except Exception as e:
            comp.mark_failed(str(e))

    async def _check_ollama(self):
        """Check Ollama LLM server."""
        comp = self.components["ollama"]
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        try:
            import urllib.request
            req = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    import json
                    data = json.loads(resp.read().decode())
                    models = [m.get("name", "?") for m in data.get("models", [])]
                    comp.mark_ok({"models": models[:5], "model_count": len(models)})
                else:
                    comp.mark_failed(f"HTTP {resp.status}")
        except Exception as e:
            comp.mark_failed(str(e), {"url": ollama_url})

    async def _check_message_bus(self):
        """Check MessageBus is operational."""
        comp = self.components["message_bus"]
        try:
            from app.core.message_bus import bus
            if bus:
                stats = {
                    "topic_count": len(bus._topics) if hasattr(bus, "_topics") else 0,
                    "subscriber_count": sum(
                        len(subs) for subs in bus._topics.values()
                    ) if hasattr(bus, "_topics") else 0,
                }
                comp.mark_ok(stats)
            else:
                comp.mark_failed("MessageBus not initialized")
        except Exception as e:
            comp.mark_failed(str(e))

    async def _check_council(self):
        """Check Council engine readiness."""
        comp = self.components["council_engine"]
        try:
            from app.council.runner import council_runner
            if council_runner:
                agent_count = getattr(council_runner, "agent_count", None)
                comp.mark_ok({"agents_loaded": agent_count or "unknown"})
            else:
                comp.mark_failed("council_runner not initialized")
        except ImportError:
            comp.mark_failed("council.runner not importable")
        except Exception as e:
            comp.mark_failed(str(e))

    async def _check_signal_engine(self):
        """Check Signal Engine status."""
        comp = self.components["signal_engine"]
        try:
            from app.services.signal_engine import signal_engine
            if signal_engine:
                comp.mark_ok({"initialized": True})
            else:
                comp.mark_failed("signal_engine not initialized")
        except ImportError:
            comp.mark_failed("signal_engine not importable")
        except Exception as e:
            comp.mark_failed(str(e))

    async def _check_frontend(self):
        """Check if frontend dev server is reachable."""
        comp = self.components["frontend"]
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:5173", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    comp.mark_ok()
                else:
                    comp.mark_failed(f"HTTP {resp.status}")
        except Exception as e:
            comp.mark_failed(str(e))

    # --- Auto-healing ---

    async def _auto_heal(self):
        """Attempt automatic fixes for known failure patterns."""
        for name, comp in self.components.items():
            if comp.consecutive_failures < 3:
                continue  # only heal after 3 consecutive failures

            if name == "message_bus" and comp.consecutive_failures == 3:
                logger.warning("[AUTO-HEAL] Attempting MessageBus reconnect...")
                comp.auto_heal_attempts += 1
                try:
                    from app.core.message_bus import bus
                    if hasattr(bus, "reconnect"):
                        await bus.reconnect()
                        logger.info("[AUTO-HEAL] MessageBus reconnected")
                except Exception as e:
                    logger.error("[AUTO-HEAL] MessageBus reconnect failed: %s", e)

            if name == "database_duckdb" and comp.consecutive_failures == 3:
                logger.warning("[AUTO-HEAL] Attempting DuckDB reconnect...")
                comp.auto_heal_attempts += 1
                try:
                    from app.data.duckdb_storage import analytics_db
                    if hasattr(analytics_db, "reconnect"):
                        analytics_db.reconnect()
                        logger.info("[AUTO-HEAL] DuckDB reconnected")
                except Exception as e:
                    logger.error("[AUTO-HEAL] DuckDB reconnect failed: %s", e)

    # --- Reporting ---

    def _log_summary(self):
        """Log compact health summary."""
        healthy = sum(1 for c in self.components.values() if c.status == "healthy")
        total = len(self.components)
        unhealthy = [c.name for c in self.components.values() if c.status == "unhealthy"]

        if unhealthy:
            logger.warning(
                "HEALTH: %d/%d healthy — UNHEALTHY: %s",
                healthy, total, ", ".join(unhealthy),
            )
        else:
            logger.info("HEALTH: %d/%d healthy — all systems nominal", healthy, total)

    def get_full_report(self) -> dict:
        """Get comprehensive health report for API response."""
        healthy_count = sum(1 for c in self.components.values() if c.status == "healthy")
        total = len(self.components)

        return {
            "overall": "healthy" if healthy_count == total else (
                "degraded" if healthy_count > total // 2 else "critical"
            ),
            "healthy_count": healthy_count,
            "total_components": total,
            "uptime_seconds": (
                (datetime.now() - self._started_at).total_seconds()
                if self._started_at else 0
            ),
            "timestamp": datetime.now().isoformat(),
            "components": {
                name: comp.to_dict() for name, comp in self.components.items()
            },
        }


# Module-level singleton
health_monitor = HealthMonitor()
