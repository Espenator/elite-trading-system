"""APScheduler integration for flywheel jobs.

Schedules:
  - Daily 18:00 UTC: outcome update
  - Weekly Sunday 20:00 UTC: walk-forward training
  - Weekly Sunday 22:00 UTC: champion/challenger evaluation
  - Every 5 min (market hours): Finviz screener adapter
  - Every 15 min: FRED macro adapter
  - Every 2 min (market hours): Unusual Whales options flow adapter
  - Every 30 min: SEC EDGAR filings adapter
  - Every 10 min: OpenClaw signal adapter

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


def _run_adapter(adapter_name: str) -> None:
    """Generic APScheduler wrapper that runs an adapter's fetch cycle.

    Looks up the named adapter from the global AdapterRegistry, calls
    ``run_fetch()`` (which includes retry/backoff), then writes any events
    to DuckDB via the global IngestionEventSink.
    """
    from app.services.ingestion.registry import adapter_registry
    from app.services.ingestion.sink import ingestion_sink

    adapter = adapter_registry.get(adapter_name)
    if adapter is None:
        log.debug("Adapter '%s' not registered — skipping scheduled run", adapter_name)
        return

    async def _run():
        events = await adapter.run_fetch()
        if events:
            written = await ingestion_sink.store.write_ingestion_events_async(events)
            log.info(
                "Adapter '%s': %d events fetched, %d written to DuckDB",
                adapter_name, len(events), written,
            )

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_run())
        else:
            loop.run_until_complete(_run())
    except Exception as exc:
        log.exception("Adapter '%s' scheduler job failed: %s", adapter_name, exc)


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

    # ── Source adapter jobs ────────────────────────────────────────────

    # Finviz screener — every 5 minutes, Mon–Fri 09:30–16:00 ET (14:30–21:00 UTC)
    _scheduler.add_job(
        lambda: _run_adapter("finviz"),
        CronTrigger(
            minute="*/5",
            hour="14-20",
            day_of_week="mon-fri",
            timezone="UTC",
        ),
        id="adapter_finviz",
        name="Finviz Screener Adapter (5 min)",
        replace_existing=True,
    )

    # FRED macro — every 15 minutes (data updates a few times per day)
    _scheduler.add_job(
        lambda: _run_adapter("fred"),
        CronTrigger(minute="*/15", timezone="UTC"),
        id="adapter_fred",
        name="FRED Macro Adapter (15 min)",
        replace_existing=True,
    )

    # Unusual Whales options flow — every 2 minutes during market hours
    _scheduler.add_job(
        lambda: _run_adapter("unusual_whales"),
        CronTrigger(
            minute="*/2",
            hour="14-20",
            day_of_week="mon-fri",
            timezone="UTC",
        ),
        id="adapter_unusual_whales",
        name="Unusual Whales Flow Adapter (2 min)",
        replace_existing=True,
    )

    # SEC EDGAR filings — every 30 minutes
    _scheduler.add_job(
        lambda: _run_adapter("sec_edgar"),
        CronTrigger(minute="*/30", timezone="UTC"),
        id="adapter_sec_edgar",
        name="SEC EDGAR Filings Adapter (30 min)",
        replace_existing=True,
    )

    # OpenClaw signals — every 10 minutes
    _scheduler.add_job(
        lambda: _run_adapter("openclaw"),
        CronTrigger(minute="*/10", timezone="UTC"),
        id="adapter_openclaw",
        name="OpenClaw Signal Adapter (10 min)",
        replace_existing=True,
    )

    _scheduler.start()
    log.info("Flywheel scheduler started with 3 flywheel + 5 adapter jobs")

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
