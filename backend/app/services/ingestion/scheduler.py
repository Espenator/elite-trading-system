"""
Ingestion Scheduler

Schedules periodic ingestion tasks for each adapter based on their
optimal polling intervals.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.services.ingestion.registry import AdapterRegistry

logger = logging.getLogger(__name__)


class IngestionScheduler:
    """
    Scheduler for ingestion adapters with per-adapter intervals

    Each adapter can have its own schedule based on:
    - Data freshness requirements
    - API rate limits
    - Market hours (for market data)
    """

    # Default schedules for each adapter
    ADAPTER_SCHEDULES = {
        # Finviz: Once per day during market hours (screener data doesn't change frequently)
        "finviz": {
            "type": "cron",
            "hour": "9",
            "minute": "15",
            "timezone": "America/New_York"
        },
        # FRED: Once per day at 5:30 PM ET (after market close, economic data updates)
        "fred": {
            "type": "cron",
            "hour": "17",
            "minute": "30",
            "timezone": "America/New_York"
        },
        # Unusual Whales: Every 2 minutes during market hours (high-frequency options flow)
        "unusual_whales": {
            "type": "interval",
            "minutes": 2
        },
        # SEC EDGAR: Every 30 minutes (filings don't come frequently)
        "sec_edgar": {
            "type": "interval",
            "minutes": 30
        },
        # OpenClaw: Every 10 minutes (regime shifts and whale flow)
        "openclaw": {
            "type": "interval",
            "minutes": 10
        },
        # Alpaca Stream: Continuous (handled separately, not scheduled)
        # "alpaca_stream": runs continuously via start()
    }

    def __init__(self, adapter_registry: AdapterRegistry):
        """
        Initialize scheduler

        Args:
            adapter_registry: Registry containing all adapters
        """
        self.adapter_registry = adapter_registry
        self.scheduler = AsyncIOScheduler()
        self._running = False

    def _create_trigger(self, schedule_config: Dict[str, Any]):
        """Create APScheduler trigger from config"""
        schedule_type = schedule_config.get("type")

        if schedule_type == "interval":
            # Interval-based trigger (every N minutes/hours)
            return IntervalTrigger(
                minutes=schedule_config.get("minutes", 0),
                hours=schedule_config.get("hours", 0),
                seconds=schedule_config.get("seconds", 0)
            )
        elif schedule_type == "cron":
            # Cron-based trigger (specific times)
            return CronTrigger(
                hour=schedule_config.get("hour"),
                minute=schedule_config.get("minute"),
                second=schedule_config.get("second", "0"),
                day_of_week=schedule_config.get("day_of_week", "*"),
                timezone=schedule_config.get("timezone", "UTC")
            )
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

    async def _run_adapter_job(self, adapter_name: str):
        """Job function that runs adapter ingestion"""
        try:
            logger.info(f"[Scheduler] Running ingestion for {adapter_name}")
            result = await self.adapter_registry.run_adapter(adapter_name)

            if result.get("status") == "success":
                logger.info(
                    f"[Scheduler] {adapter_name} completed: "
                    f"{result.get('row_count', 0)} events"
                )
            else:
                logger.warning(
                    f"[Scheduler] {adapter_name} failed: "
                    f"{result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"[Scheduler] Error running {adapter_name}: {e}", exc_info=True)

    def schedule_adapter(self, adapter_name: str, schedule_config: Optional[Dict[str, Any]] = None):
        """
        Schedule a specific adapter

        Args:
            adapter_name: Name of adapter to schedule
            schedule_config: Optional custom schedule config (uses default if not provided)
        """
        # Use custom config or default
        config = schedule_config or self.ADAPTER_SCHEDULES.get(adapter_name)

        if not config:
            logger.warning(f"No schedule config for {adapter_name}, skipping")
            return

        # Create trigger
        trigger = self._create_trigger(config)

        # Add job to scheduler
        self.scheduler.add_job(
            self._run_adapter_job,
            trigger=trigger,
            args=[adapter_name],
            id=f"ingest_{adapter_name}",
            name=f"Ingestion: {adapter_name}",
            replace_existing=True,
            misfire_grace_time=300  # 5 minutes grace period
        )

        logger.info(f"Scheduled adapter: {adapter_name} with config {config}")

    def schedule_all_adapters(self):
        """Schedule all adapters based on their default schedules"""
        for adapter_name in self.ADAPTER_SCHEDULES.keys():
            self.schedule_adapter(adapter_name)

        logger.info(f"Scheduled {len(self.ADAPTER_SCHEDULES)} adapters")

    def start(self):
        """Start the scheduler"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self.scheduler.start()
        self._running = True
        logger.info("Ingestion scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if not self._running:
            return

        self.scheduler.shutdown(wait=False)
        self._running = False
        logger.info("Ingestion scheduler stopped")

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._running

    def get_scheduled_jobs(self) -> list:
        """Get list of scheduled jobs"""
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in self.scheduler.get_jobs()
        ]

    async def run_adapter_now(self, adapter_name: str):
        """Run an adapter immediately (outside of schedule)"""
        logger.info(f"[Scheduler] Running {adapter_name} immediately")
        await self._run_adapter_job(adapter_name)
