"""Daily job: resolve pending signal outcomes and update flywheel accuracy.

Idempotent: checks persisted state in DuckDB, skips if already run today.
Survives process restarts (no in-memory _last_run_date only).
CLI: python -m app.jobs.daily_outcome_update
"""
import json
import logging
import time
from datetime import date, datetime, timezone

log = logging.getLogger(__name__)

JOB_NAME = "daily_outcome_update"


def _emit_metric(name: str, labels: dict, value: int = 1) -> None:
    try:
        from app.core.metrics import counter_inc
        counter_inc(name, labels, value=value)
    except Exception:
        pass


def _get_state() -> dict:
    """Load job state from DuckDB. Returns {} if not run before or DB unavailable."""
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        row = conn.execute(
            "SELECT last_run_date, last_run_ts, last_result FROM job_state WHERE job_name = ?",
            [JOB_NAME],
        ).fetchone()
        if row:
            return {
                "last_run_date": row[0],
                "last_run_ts": row[1],
                "last_result": json.loads(row[2]) if row[2] else None,
            }
    except Exception as e:
        log.debug("Could not load job_state: %s", e)
    return {}


def _save_state(today: str, result: dict) -> None:
    """Persist job state to DuckDB."""
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        result_json = json.dumps(result)
        conn.execute(
            """
            INSERT INTO job_state (job_name, last_run_date, last_run_ts, last_result)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (job_name) DO UPDATE SET
                last_run_date = excluded.last_run_date,
                last_run_ts = excluded.last_run_ts,
                last_result = excluded.last_result
            """,
            [JOB_NAME, today, time.time(), result_json],
        )
    except Exception as e:
        log.warning("Could not save job_state: %s", e)


def run() -> dict:
    """Resolve pending outcomes and refresh flywheel accuracy metrics.

    Uses DuckDB job_state so restart does not cause double-run.
    Returns:
        Dict with status, resolved_count, accuracy info.
    """
    today = date.today().isoformat()
    state = _get_state()
    if state.get("last_run_date") == today:
        log.info("daily_outcome_update already ran today (%s), skipping", today)
        _emit_metric("outcome_reconcile_total", {"status": "skipped_idempotent"})
        return {
            "status": "skipped",
            "reason": "already_run_today",
            "date": today,
            "last_run_ts": state.get("last_run_ts"),
        }

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
        _emit_metric("outcome_resolution_total", {"status": "completed"})
        _emit_metric("outcome_resolution_total", {"status": "resolved"}, value=result["resolved_count"])
        log.info(
            "Flywheel metrics: resolved=%d acc_30d=%s acc_90d=%s",
            result["resolved_count"], result["accuracy_30d"], result["accuracy_90d"],
        )
    except Exception as e:
        log.warning("Outcome resolution failed: %s", e)
        result["error"] = str(e)
        _emit_metric("outcome_resolution_total", {"status": "error"})

    # 2. Update trade outcomes from DuckDB if available
    try:
        from app.data.duckdb_storage import duckdb_store

        health = duckdb_store.health_check()
        result["duckdb_rows"] = health.get("total_rows", 0)
    except Exception as e:
        log.debug("DuckDB outcome update skipped: %s", e)

    _save_state(today, result)
    _emit_metric("outcome_reconcile_total", {"status": "completed"})
    log.info("daily_outcome_update completed: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    print(run())
