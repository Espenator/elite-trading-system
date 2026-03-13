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

    # 1. Resolve pending outcomes and sync to flywheel_data (dashboard KPIs)
    try:
        from app.modules.ml_engine.outcome_resolver import get_flywheel_metrics
        from app.services.database import db_service

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
        # Sync outcome_resolver metrics into flywheel_data so ML Brain dashboard stays current
        try:
            stored = db_service.get_config("flywheel_data") or {}
            history = list(stored.get("history") or [])
            acc_30 = result["accuracy_30d"]
            acc_90 = result["accuracy_90d"]
            entry = {
                "date": today,
                "accuracy": round(float(acc_30 or acc_90 or 0), 4),
            }
            history.append(entry)
            if len(history) > 365:
                history = history[-365:]
            updated = {
                **stored,
                "accuracy30d": float(acc_30) if acc_30 is not None else stored.get("accuracy30d", 0.0),
                "accuracy90d": float(acc_90) if acc_90 is not None else stored.get("accuracy90d", 0.0),
                "resolvedSignals": result["resolved_count"],
                "pendingResolution": stored.get("pendingResolution", 0),
                "history": history,
            }
            db_service.set_config("flywheel_data", updated)
            log.debug("Synced flywheel_data from outcome_resolver")
        except Exception as sync_err:
            log.warning("Flywheel data sync failed: %s", sync_err)
    except Exception as e:
        log.warning("Outcome resolution failed: %s", e)
        result["error"] = str(e)
        _emit_metric("outcome_resolution_total", {"status": "error"})

    # 2. Scan DuckDB trade_outcomes for resolved trades not yet in outcome_resolver
    duckdb_synced = 0
    try:
        from app.data.duckdb_storage import duckdb_store
        from app.modules.ml_engine.outcome_resolver import record_outcome, _get_store

        conn = duckdb_store.get_thread_cursor()
        rows = conn.execute("""
            SELECT symbol, direction, entry_date, exit_date, pnl, signal_score
            FROM trade_outcomes
            WHERE exit_date IS NOT NULL AND pnl IS NOT NULL
            ORDER BY exit_date DESC
            LIMIT 500
        """).fetchall()

        if rows:
            # Build set of already-resolved (symbol, signal_date) pairs to avoid duplicates
            store = _get_store()
            existing = {
                (r.get("symbol", ""), r.get("signal_date", ""))
                for r in (store.get("resolved") or [])
            }

            for row in rows:
                symbol, direction, entry_date, exit_date, pnl, signal_score = row
                sig_date = str(entry_date)
                if (symbol, sig_date) in existing:
                    continue
                # outcome: 1 if profitable, 0 if not
                outcome = 1 if (pnl or 0) > 0 else 0
                # prediction: 1 if signal was bullish (buy), 0 if bearish (sell)
                prediction = 1 if direction == "buy" else 0
                record_outcome(
                    symbol=symbol,
                    signal_date=sig_date,
                    outcome=outcome,
                    prediction=prediction,
                    resolved_at=str(exit_date) if exit_date else None,
                )
                duckdb_synced += 1

            if duckdb_synced > 0:
                log.info("Synced %d trade_outcomes from DuckDB to outcome_resolver", duckdb_synced)
                # Re-fetch metrics after syncing new outcomes
                from app.modules.ml_engine.outcome_resolver import get_flywheel_metrics as _refresh
                refreshed = _refresh()
                result["resolved_count"] = refreshed.get("resolved_count", result["resolved_count"])
                result["accuracy_30d"] = refreshed.get("accuracy_30d") or result.get("accuracy_30d")
                result["accuracy_90d"] = refreshed.get("accuracy_90d") or result.get("accuracy_90d")

        result["duckdb_synced"] = duckdb_synced
        health = duckdb_store.health_check()
        result["duckdb_rows"] = health.get("total_rows", 0)
    except Exception as e:
        log.debug("DuckDB outcome sync skipped: %s", e)
        result["duckdb_synced"] = 0

    # 3. Re-sync flywheel_data after DuckDB scan (in case new outcomes were added)
    if duckdb_synced > 0:
        try:
            from app.services.database import db_service

            stored = db_service.get_config("flywheel_data") or {}
            history = list(stored.get("history") or [])
            acc_30 = result.get("accuracy_30d")
            acc_90 = result.get("accuracy_90d")
            entry = {
                "date": today,
                "accuracy": round(float(acc_30 or acc_90 or 0), 4),
            }
            # Replace today's entry if already appended in step 1
            history = [h for h in history if h.get("date") != today]
            history.append(entry)
            if len(history) > 365:
                history = history[-365:]
            updated = {
                **stored,
                "accuracy30d": float(acc_30) if acc_30 is not None else stored.get("accuracy30d", 0.0),
                "accuracy90d": float(acc_90) if acc_90 is not None else stored.get("accuracy90d", 0.0),
                "resolvedSignals": result["resolved_count"],
                "pendingResolution": stored.get("pendingResolution", 0),
                "history": history,
            }
            db_service.set_config("flywheel_data", updated)
            log.info("Re-synced flywheel_data after DuckDB scan (%d new outcomes)", duckdb_synced)
        except Exception as sync_err:
            log.warning("Post-DuckDB flywheel_data sync failed: %s", sync_err)

    _save_state(today, result)
    _emit_metric("outcome_reconcile_total", {"status": "completed"})
    log.info("daily_outcome_update completed: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    print(run())
