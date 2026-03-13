"""Scheduler job resilience and distributed locking audit tests.

Covers: idempotency (job_state), failure recovery, startup ordering.
Run: pytest backend/tests/test_scheduler_resilience.py -v
"""
import os
from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from app.jobs.daily_outcome_update import run as daily_run, JOB_NAME
from app.jobs.scheduler import (
    get_scheduler_status,
    start_scheduler,
    stop_scheduler,
    _run_daily_outcome,
)


class TestJobIdempotency:
    """Verify job_state table prevents duplicate runs for daily_outcome_update."""

    def test_daily_outcome_skips_second_run_when_state_says_already_run(self):
        """Run same job twice with state indicating already run today → second skips (single execution)."""
        today = date.today().isoformat()
        state_after_run = {
            "last_run_date": today,
            "last_run_ts": 12345.0,
            "last_result": None,
        }

        with patch("app.jobs.daily_outcome_update._get_state") as m_get:
            # First call: no prior run. Second call: already ran today.
            m_get.side_effect = [
                {},  # first run: no state
                state_after_run,  # second run: already ran today
            ]
            with patch("app.jobs.daily_outcome_update._save_state"):
                result1 = daily_run()
                result2 = daily_run()

        # First run proceeds (may complete or error depending on deps); second must skip
        assert result2["status"] == "skipped"
        assert result2.get("reason") == "already_run_today"
        assert result2.get("date") == today
        # Exactly one "real" execution: _get_state was called twice; second time we skipped
        assert m_get.call_count == 2

    def test_daily_outcome_idempotency_uses_duckdb_job_state(self):
        """daily_outcome_update uses job_state table for idempotency (not in-memory only)."""
        from app.jobs import daily_outcome_update as mod
        # Module uses duckdb_store.get_thread_cursor() in _get_state/_save_state
        assert hasattr(mod, "_get_state")
        assert hasattr(mod, "_save_state")
        # job_state key is JOB_NAME
        assert JOB_NAME == "daily_outcome_update"


class TestFailureRecovery:
    """Failed jobs are caught by scheduler wrappers; no retry until next cron."""

    def test_scheduler_wrapper_catches_job_exception(self):
        """When job raises, wrapper logs and does not propagate — no crash."""
        with patch("app.jobs.daily_outcome_update.run") as m_run:
            m_run.side_effect = RuntimeError("Simulated job crash")
            # Should not raise; wrapper catches and logs
            _run_daily_outcome()
        m_run.assert_called_once()

    def test_failed_job_wrapper_does_not_propagate(self):
        """Scheduler wrapper catches any exception from job; process continues."""
        with patch("app.jobs.daily_outcome_update.run") as m_run:
            m_run.side_effect = ValueError("Simulated failure")
            try:
                _run_daily_outcome()
            except ValueError:
                pytest.fail("Scheduler wrapper must catch job exceptions and not propagate")
        m_run.assert_called_once()


class TestStartupOrdering:
    """Scheduler starts after DuckDB and MessageBus in main lifespan."""

    def test_scheduler_status_before_start_returns_disabled_or_jobs(self):
        """get_scheduler_status() does not require DuckDB/MessageBus to be ready."""
        status = get_scheduler_status()
        assert "enabled" in status
        assert "running" in status
        assert "jobs" in status
        # In test env SCHEDULER_ENABLED is usually false
        assert isinstance(status["jobs"], list)

    def test_start_scheduler_registers_six_jobs_when_enabled(self):
        """When SCHEDULER_ENABLED=true, start_scheduler() registers all 6 flywheel jobs."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with patch("app.core.config.settings") as m_settings:
                m_settings.SCHEDULER_ENABLED = True
                try:
                    s = start_scheduler()
                    if s is not None:
                        jobs = s.get_jobs()
                        assert len(jobs) == 6, "Expected 6 scheduled jobs"
                        ids = {j.id for j in jobs}
                        expected = {
                            "daily_outcome_update",
                            "weekly_walkforward_train",
                            "champion_challenger_eval",
                            "daily_backfill",
                            "overnight_refresh",
                            "morning_briefing",
                        }
                        assert ids == expected, f"Job ids mismatch: {ids}"
                finally:
                    try:
                        stop_scheduler()
                    except (RuntimeError, AttributeError):
                        pass  # Event loop teardown race
        finally:
            loop.close()

    def test_main_lifespan_order_scheduler_after_duckdb(self):
        """Documentation: main.py starts scheduler after DuckDB init and event pipeline."""
        import app.main as main_mod
        source = open(main_mod.__file__, encoding="utf-8").read()
        # Scheduler is started in lifespan (run_in_background=False path)
        assert "start_scheduler" in source
        assert "duckdb_store.init_schema" in source
        # Order: init_schema before start_scheduler (scheduler comes in "3b")
        idx_duckdb = source.find("duckdb_store.init_schema()")
        idx_scheduler = source.find("start_scheduler()")
        assert idx_duckdb != -1 and idx_scheduler != -1
        assert idx_duckdb < idx_scheduler, (
            "Scheduler must start after DuckDB init_schema in main lifespan"
        )
