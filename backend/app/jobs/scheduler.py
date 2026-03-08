"""APScheduler integration for flywheel jobs and data ingestion adapters.

Schedules:
  - Daily 18:00 UTC: outcome update
  - Weekly Sunday 20:00 UTC: walk-forward training
  - Weekly Sunday 22:00 UTC: champion/challenger evaluation
  - Every 5 minutes: Finviz screener ingestion
  - Every 15 minutes: FRED economic data ingestion
  - Every 2 minutes: Unusual Whales flow/insider/congress trades
  - Every 30 minutes: SEC Edgar filings ingestion
  - Every 10 minutes: OpenClaw signals ingestion

Only starts when SCHEDULER_ENABLED=true.
"""
import asyncio
import logging
from typing import Optional

log = logging.getLogger(__name__)

_scheduler = None


def _run_daily_outcome():
    """Wrapper for APScheduler (sync)."""
    from app.jobs.daily_outcome_update import run
    try:
        result = run()
        log.info("Scheduled daily_outcome_update: %s", result.get("status"))
    except Exception as e:
        log.exception("Scheduled daily_outcome_update failed: %s", e)


def _run_weekly_train():
    """Wrapper for APScheduler (sync)."""
    from app.jobs.weekly_walkforward_train import run
    try:
        result = run()
        log.info("Scheduled weekly_walkforward_train: %s", result.get("status"))
    except Exception as e:
        log.exception("Scheduled weekly_walkforward_train failed: %s", e)


def _run_weekly_eval():
    """Wrapper for APScheduler (sync)."""
    from app.jobs.champion_challenger_eval import run
    try:
        result = run()
        log.info("Scheduled champion_challenger_eval: %s", result.get("status"))
    except Exception as e:
        log.exception("Scheduled champion_challenger_eval failed: %s", e)


def _run_adapter(adapter_id: str):
    """Wrapper for running an adapter (async -> sync)."""
    from app.services.ingestion import get_adapter_registry

    try:
        registry = get_adapter_registry()

        # Run adapter in async context
        async def _run():
            return await registry.run_adapter(adapter_id)

        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        count = loop.run_until_complete(_run())
        log.info(f"Scheduled {adapter_id} adapter: ingested {count} events")
    except Exception as e:
        log.exception(f"Scheduled {adapter_id} adapter failed: %s", e)


def start_scheduler() -> Optional[object]:
    """Start the APScheduler with flywheel jobs.

    Returns:
        The scheduler instance, or None if disabled/unavailable.
    """
    global _scheduler
    from app.core.config import settings

    if not settings.SCHEDULER_ENABLED:
        log.info("Scheduler disabled (SCHEDULER_ENABLED=false in config)")
        return None

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        log.warning("apscheduler not installed — scheduler disabled")
        return None

    _scheduler = AsyncIOScheduler()

    # Daily at 18:00 UTC — outcome resolution
    _scheduler.add_job(
        _run_daily_outcome,
        CronTrigger(hour=18, minute=0, timezone="UTC"),
        id="daily_outcome_update",
        name="Daily Outcome Update",
        replace_existing=True,
    )

    # Weekly Sunday 20:00 UTC — walk-forward training
    _scheduler.add_job(
        _run_weekly_train,
        CronTrigger(day_of_week="sun", hour=20, minute=0, timezone="UTC"),
        id="weekly_walkforward_train",
        name="Weekly Walk-Forward Training",
        replace_existing=True,
    )

    # Weekly Sunday 22:00 UTC — champion/challenger evaluation
    _scheduler.add_job(
        _run_weekly_eval,
        CronTrigger(day_of_week="sun", hour=22, minute=0, timezone="UTC"),
        id="champion_challenger_eval",
        name="Champion/Challenger Evaluation",
        replace_existing=True,
    )

    # Data ingestion adapter jobs
    # Finviz: Every 5 minutes during market hours (9:00-16:30 ET / 14:00-21:30 UTC Mon-Fri)
    _scheduler.add_job(
        lambda: _run_adapter("finviz"),
        CronTrigger(minute="*/5", hour="14-21", day_of_week="mon-fri", timezone="UTC"),
        id="adapter_finviz",
        name="Finviz Screener Ingestion",
        replace_existing=True,
    )

    # FRED: Every 15 minutes (economic data updates infrequently)
    _scheduler.add_job(
        lambda: _run_adapter("fred"),
        CronTrigger(minute="*/15", timezone="UTC"),
        id="adapter_fred",
        name="FRED Economic Data Ingestion",
        replace_existing=True,
    )

    # Unusual Whales: Every 2 minutes during market hours (high-frequency options flow)
    _scheduler.add_job(
        lambda: _run_adapter("unusual_whales"),
        CronTrigger(minute="*/2", hour="14-21", day_of_week="mon-fri", timezone="UTC"),
        id="adapter_unusual_whales",
        name="Unusual Whales Flow Ingestion",
        replace_existing=True,
    )

    # SEC Edgar: Every 30 minutes (filings are not real-time)
    _scheduler.add_job(
        lambda: _run_adapter("sec_edgar"),
        CronTrigger(minute="*/30", timezone="UTC"),
        id="adapter_sec_edgar",
        name="SEC Edgar Filings Ingestion",
        replace_existing=True,
    )

    # OpenClaw: Every 10 minutes (regime and signal updates)
    _scheduler.add_job(
        lambda: _run_adapter("openclaw"),
        CronTrigger(minute="*/10", timezone="UTC"),
        id="adapter_openclaw",
        name="OpenClaw Signals Ingestion",
        replace_existing=True,
    )

    _scheduler.start()
    log.info("Scheduler started with 8 jobs (3 flywheel + 5 adapters)")

    return _scheduler


def stop_scheduler():
    """Gracefully stop the scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        log.info("Flywheel scheduler stopped")
        _scheduler = None


def get_scheduler_status() -> dict:
    """Return scheduler status for API/dashboard."""
    if _scheduler is None:
        return {"enabled": False, "running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })

    return {
        "enabled": True,
        "running": _scheduler.running,
        "jobs": jobs,
    }
