"""APScheduler integration for flywheel jobs.

24/7 Session-aware schedule (ET):
  AFTERHOURS (4–8 PM ET): daily_outcome, weight learner batch
  OVERNIGHT (8 PM–4 AM ET): drift check, regime forecast, model validation
  PREMARKET (4–9:30 AM ET): news/EDGAR/congressional scan, morning briefing
  WEEKEND: walk-forward, champion/challenger, weekly performance

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
    """Return True always — 24/7 mode active.

    All sessions are active for both intelligence and order execution.
    Weekend orders submitted to Alpaca queue until Monday market open.
    """
    return True


def is_intelligence_active() -> bool:
    """Return True always — intelligence never sleeps.

    Signal generation, scanning, news analysis, sentiment, scouts,
    and council deliberation run 24/7 including weekends.
    Only order execution is gated by is_trading_session().
    """
    return True


# Session-specific cycle intervals (seconds)
_SESSION_CYCLE_INTERVALS = {
    "regular": 15 * 60,       # 15 min — full liquidity, tight cycles
    "pre_market": 30 * 60,    # 30 min — thinner liquidity
    "after_hours": 30 * 60,   # 30 min — thinner liquidity
    "overnight": 60 * 60,     # 60 min — minimal liquidity, conserve resources
    "weekend": 120 * 60,      # 2 hours — intelligence cycles (no execution)
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


def _run_world_awareness_scan():
    """Part 6: Continuous World Awareness — Perplexity Sonar Pro every 15 min.

    Fires 5 parallel intelligence scans and publishes world.awareness_snapshot
    to MessageBus so macro_regime_agent and hypothesis_agent have live context.
    """
    import asyncio

    async def _scan():
        try:
            from app.services.perplexity_intelligence import get_perplexity_intel
            from app.core.message_bus import get_message_bus
            intel = get_perplexity_intel()
            results = await asyncio.gather(
                intel.scan_fed_macro(),
                intel.scan_sector_rotation(),
                intel.get_fear_greed_context(),
                intel.scan_breaking_news("SPY"),
                intel.get_institutional_flow("QQQ"),
                return_exceptions=True,
            )
            bus = get_message_bus()
            if bus._running:
                snapshot = {
                    "fed_macro": results[0] if not isinstance(results[0], Exception) else None,
                    "sector_rotation": results[1] if not isinstance(results[1], Exception) else None,
                    "fear_greed": results[2] if not isinstance(results[2], Exception) else None,
                    "spy_news": results[3] if not isinstance(results[3], Exception) else None,
                    "qqq_flow": results[4] if not isinstance(results[4], Exception) else None,
                }
                await bus.publish("world.awareness_snapshot", snapshot)
            log.info("World awareness scan: %d/5 succeeded",
                     sum(1 for r in results if not isinstance(r, Exception)))
        except Exception as e:
            log.warning("World awareness scan failed: %s", e)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_scan())
        else:
            asyncio.run(_scan())
    except Exception as e:
        log.exception("World awareness scheduler error: %s", e)


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

    # NOTE: SCHEDULER_ENABLED must be set to true in .env for the weekly
    # walk-forward training job to run. The bootstrap in _maybe_bootstrap_ml_model()
    # bypasses this gate to ensure initial training always happens.
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

    # AFTERHOURS: Daily at 4:30 PM ET — outcome resolution, weight learner batch
    # Mon-Fri only: outcomes resolve against live market closes
    _scheduler.add_job(
        _run_daily_outcome,
        CronTrigger(hour=16, minute=30, day_of_week="mon-fri", timezone="America/New_York"),
        id="daily_outcome_update",
        name="Daily Outcome Update (AFTERHOURS)",
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
    # 7 days: weekend backfill catches up on any missed data
    _scheduler.add_job(
        _run_daily_backfill,
        CronTrigger(hour=9, minute=30, timezone="UTC"),
        id="daily_backfill",
        name="Daily Incremental Backfill",
        replace_existing=True,
    )

    # OVERNIGHT: Daily at 10:00 PM ET — FRED/SEC refresh, drift check
    # 7 days: macro data and SEC filings can drop anytime
    _scheduler.add_job(
        _run_overnight_refresh,
        CronTrigger(hour=22, minute=0, timezone="America/New_York"),
        id="overnight_refresh",
        name="Overnight FRED/SEC Refresh",
        replace_existing=True,
    )

    # 9 AM ET daily — morning briefing + TradingView webhook push
    # 7 days: weekend briefings prep for Monday open
    _scheduler.add_job(
        _run_morning_briefing,
        CronTrigger(hour=9, minute=0, timezone="America/New_York"),
        id="morning_briefing",
        name="Morning Briefing (9 AM ET)",
        replace_existing=True,
    )

    # Hourly — retroactive signal resolution to bootstrap flywheel
    # 7 days: historical analysis doesn't need live market
    _scheduler.add_job(
        _run_historical_signal_resolution,
        CronTrigger(minute=30, timezone="UTC"),
        id="historical_signal_resolution",
        name="Historical Signal Resolution (hourly)",
        replace_existing=True,
    )

    # Part 6: Continuous World Awareness — Perplexity scan every 15 minutes
    # 7 days: world events don't stop on weekends
    from apscheduler.triggers.interval import IntervalTrigger
    _scheduler.add_job(
        _run_world_awareness_scan,
        IntervalTrigger(minutes=15),
        id="world_awareness_scan",
        name="World Awareness Scan (Perplexity, 15min)",
        replace_existing=True,
    )

    _scheduler.start()
    log.info("Flywheel scheduler started with %d jobs", len(_scheduler.get_jobs()))

    return _scheduler


async def _maybe_bootstrap_ml_model():
    """On startup, check if ML model exists. If not, trigger initial training.

    Called as a background task from main.py lifespan. Waits 5 minutes
    to let data ingestion populate DuckDB before training.
    """
    import os
    model_path = os.path.join(
        os.path.dirname(__file__), "..", "modules", "ml_engine", "artifacts", "xgboost_best.json"
    )
    if os.path.exists(model_path):
        log.info("ML model found at %s — skipping bootstrap", model_path)
        return

    log.info("No ML model found — scheduling bootstrap training in 5 minutes")
    # Delay to let data ingestion populate DuckDB first
    await asyncio.sleep(300)
    try:
        from app.modules.ml_engine.xgboost_trainer import train_xgboost_v2
        # Train on top liquid symbols
        symbols = [
            "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "AMZN", "GOOGL", "META",
            "JPM", "BAC", "XOM", "CVX", "UNH", "JNJ", "V", "MA", "PG", "HD",
        ]
        result = await asyncio.to_thread(train_xgboost_v2, symbols)
        log.info("ML bootstrap training complete: %s", result)
    except Exception as e:
        log.warning("ML bootstrap training failed (will retry on next weekly schedule): %s", e)


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
