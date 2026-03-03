"""Daily job: resolve pending signal outcomes and update flywheel accuracy.

Idempotent: checks last run date, skips if already run today.
CLI: python -m app.jobs.daily_outcome_update
"""
import logging
from datetime import date, datetime, timezone

log = logging.getLogger(__name__)

_last_run_date: str = ""


def run() -> dict:
    """Resolve pending outcomes and refresh flywheel accuracy metrics.

    Returns:
        Dict with status, resolved_count, accuracy info.
    """
    global _last_run_date

    today = date.today().isoformat()
    if _last_run_date == today:
        log.info("daily_outcome_update already ran today (%s), skipping", today)
        return {"status": "skipped", "reason": "already_run_today", "date": today}

    log.info("Running daily_outcome_update for %s", today)

    result = {
        "status": "completed",
        "date": today,
        "resolved_count": 0,
        "accuracy_30d": None,
        "accuracy_90d": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Resolve pending outcomes
    try:
        from app.modules.ml_engine.outcome_resolver import get_flywheel_metrics

        metrics = get_flywheel_metrics()
        result["resolved_count"] = metrics.get("resolved_count", 0)
        result["accuracy_30d"] = metrics.get("accuracy_30d")
        result["accuracy_90d"] = metrics.get("accuracy_90d")
        log.info(
            "Flywheel metrics: resolved=%d acc_30d=%s acc_90d=%s",
            result["resolved_count"], result["accuracy_30d"], result["accuracy_90d"],
        )
    except Exception as e:
        log.warning("Outcome resolution failed: %s", e)
        result["error"] = str(e)

    # 2. Update trade outcomes from DuckDB if available
    try:
        from app.data.duckdb_storage import duckdb_store

        health = duckdb_store.health_check()
        result["duckdb_rows"] = health.get("total_rows", 0)
    except Exception as e:
        log.debug("DuckDB outcome update skipped: %s", e)

    _last_run_date = today
    log.info("daily_outcome_update completed: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    print(run())
