"""APScheduler integration for flywheel jobs.

Schedules:
  - Daily 18:00 UTC: outcome update
  - Weekly Sunday 20:00 UTC: walk-forward training
  - Weekly Sunday 22:00 UTC: champion/challenger evaluation
  - Daily 09:30 UTC (4:30 AM ET): incremental data backfill (D1)
  - Daily 05:00 UTC (midnight ET): overnight FRED/SEC refresh (D5)

Only starts when SCHEDULER_ENABLED=true.

Market Hours Guard:
  GPU training jobs (XGBoost CUDA) are blocked during 09:30-16:00 ET
  to protect VRAM for gemma3:12b live inference on PC2.

24/5 Session Support:
  is_trading_session() — True for any active session (Sun 8 PM - Fri 8 PM ET)
  get_cycle_interval() — session-specific cycle interval in seconds
"""
import asyncio
import logging
from datetime import datetime, time as dt_time
from typing import Optional

log = logging.getLogger(__name__)


def is_market_hours() -> bool:
    """Return True if US equity market is open (09:30-16:00 ET).

    Used to block GPU training jobs that would starve VRAM
    needed for gemma3:12b live inference on PC2.
    Note: This is the VRAM protection guard — NOT the trading session check.
    For 24/5 trading session awareness, use is_trading_session() instead.
    """
    try:
        import pytz
        et = datetime.now(pytz.timezone("America/New_York")).time()
    except ImportError:
        from datetime import timezone, timedelta
        et_offset = timezone(timedelta(hours=-5))  # EST approximation
        et = datetime.now(et_offset).time()
    return dt_time(9, 30) <= et <= dt_time(16, 0)


def is_trading_session() -> bool:
    """Return True if we're in any active 24/5 trading session.

    Active sessions (Sun 8 PM ET through Fri 8 PM ET):
      OVERNIGHT, PRE_MARKET, REGULAR, AFTER_HOURS

    Inactive:
      WEEKEND (Sat 8 PM - Sun 8 PM ET)

    Used by the scanning/trading pipeline to decide whether to
    process signals and submit orders.
    """
    from app.services.data_swarm.session_clock import get_session_clock, TradingSession
    session = get_session_clock().get_current_session()
    return session != TradingSession.WEEKEND


# Session-specific cycle intervals (seconds)
_SESSION_CYCLE_INTERVALS = {
    "regular": 15 * 60,       # 15 min — full liquidity, tight cycles
    "pre_market": 30 * 60,    # 30 min — thinner liquidity
    "after_hours": 30 * 60,   # 30 min — thinner liquidity
    "overnight": 60 * 60,     # 60 min — minimal liquidity, conserve resources
    "weekend": 0,             # No trading
}


def get_cycle_interval() -> int:
    """Return the appropriate scan/trading cycle interval for current session.

    Returns:
        Interval in seconds. 0 means no trading (weekend).
        - REGULAR:     900s  (15 min)
        - PRE_MARKET:  1800s (30 min)
        - AFTER_HOURS: 1800s (30 min)
        - OVERNIGHT:   3600s (60 min)
        - WEEKEND:     0     (inactive)
    """
    from app.services.data_swarm.session_clock import get_session_clock
    session = get_session_clock().get_current_session()
    return _SESSION_CYCLE_INTERVALS.get(session.value, 900)

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
    """Wrapper for APScheduler (sync).

    Blocks during market hours (09:30-16:00 ET) to protect
    VRAM for gemma3:12b live inference on PC2.
    Pins to E-cores for background training on hybrid CPUs.
    """
    if is_market_hours():
        log.info(
            "Market hours -- skipping GPU training to protect VRAM for gemma3:12b"
        )
        return
    # Pin training to E-cores (background) on Intel hybrid CPUs
    try:
        from app.core.hardware_profile import apply_affinity
        apply_affinity("e_cores")
    except Exception:
        pass
    from app.jobs.weekly_walkforward_train import run
    try:
        result = run()
        log.info("Scheduled weekly_walkforward_train: %s", result.get("status"))
    except Exception as e:
        log.exception("Scheduled weekly_walkforward_train failed: %s", e)


def _run_weekly_eval():
    """Wrapper for APScheduler (sync).

    Blocks during market hours to avoid GPU contention.
    """
    if is_market_hours():
        log.info(
            "Market hours -- skipping champion_challenger_eval to protect VRAM"
        )
        return
    from app.jobs.champion_challenger_eval import run
    try:
        result = run()
        log.info("Scheduled champion_challenger_eval: %s", result.get("status"))
    except Exception as e:
        log.exception("Scheduled champion_challenger_eval failed: %s", e)


def _run_daily_backfill():
    """D1: Daily incremental backfill at 4:30 AM ET (09:30 UTC)."""
    import asyncio
    from app.services.data_ingestion import data_ingestion
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(data_ingestion.run_daily_incremental())
        else:
            asyncio.run(data_ingestion.run_daily_incremental())
        log.info("Scheduled daily_backfill triggered")
    except Exception as e:
        log.exception("Scheduled daily_backfill failed: %s", e)


def _run_overnight_refresh():
    """D5: Overnight FRED macro + SEC refresh at midnight ET (05:00 UTC)."""
    import asyncio
    from app.services.data_ingestion import data_ingestion
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(data_ingestion.ingest_macro_data(days=30))
        else:
            asyncio.run(data_ingestion.ingest_macro_data(days=30))
        log.info("Scheduled overnight_refresh triggered")
    except Exception as e:
        log.exception("Scheduled overnight_refresh failed: %s", e)


def _run_morning_briefing():
    """9 AM ET weekdays: generate morning briefing and push to TradingView webhook."""
    from app.jobs.morning_briefing_job import run_morning_briefing
    try:
        result = run_morning_briefing()
        log.info("Scheduled morning_briefing: %s", result.get("status"))
    except Exception as e:
        log.exception("Scheduled morning_briefing failed: %s", e)


def _run_historical_signal_resolution():
    """Hourly: resolve past turbo_scanner signals against current prices to feed the flywheel."""
    import asyncio
    from app.services.outcome_tracker import resolve_historical_signals
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(resolve_historical_signals())
        else:
            asyncio.run(resolve_historical_signals())
        log.info("Scheduled historical_signal_resolution triggered")
    except Exception as e:
        log.exception("Scheduled historical_signal_resolution failed: %s", e)


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

    try:
        event_loop = asyncio.get_event_loop()
    except RuntimeError:
        # Python 3.13+: no current loop in main thread by default.
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)

    _scheduler = AsyncIOScheduler(event_loop=event_loop)

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

    # D1: Daily at 09:30 UTC (4:30 AM ET) — incremental data backfill
    _scheduler.add_job(
        _run_daily_backfill,
        CronTrigger(hour=9, minute=30, timezone="UTC", day_of_week="mon-fri"),
        id="daily_backfill",
        name="Daily Incremental Backfill",
        replace_existing=True,
    )

    # D5: Daily at 05:00 UTC (midnight ET) — overnight FRED/SEC refresh
    _scheduler.add_job(
        _run_overnight_refresh,
        CronTrigger(hour=5, minute=0, timezone="UTC", day_of_week="mon-fri"),
        id="overnight_refresh",
        name="Overnight FRED/SEC Refresh",
        replace_existing=True,
    )

    # 9 AM ET weekdays — morning briefing + TradingView webhook push
    _scheduler.add_job(
        _run_morning_briefing,
        CronTrigger(hour=9, minute=0, day_of_week="mon-fri", timezone="America/New_York"),
        id="morning_briefing",
        name="Morning Briefing (9 AM ET)",
        replace_existing=True,
    )

    # Hourly weekdays — retroactive signal resolution to bootstrap flywheel
    _scheduler.add_job(
        _run_historical_signal_resolution,
        CronTrigger(minute=30, day_of_week="mon-fri", timezone="UTC"),
        id="historical_signal_resolution",
        name="Historical Signal Resolution (hourly)",
        replace_existing=True,
    )

    _scheduler.start()
    log.info("Flywheel scheduler started with %d jobs", len(_scheduler.get_jobs()))

    return _scheduler


def stop_scheduler():
    """Gracefully stop the scheduler."""
    global _scheduler
    if _scheduler is not None:
        try:
            if getattr(_scheduler, "running", False):
                _scheduler.shutdown(wait=False)
                log.info("Flywheel scheduler stopped")
        except Exception as e:
            # Best effort in tests and shutdown races.
            log.debug("Scheduler shutdown skipped: %s", e)
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
