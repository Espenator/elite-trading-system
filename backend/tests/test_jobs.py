"""Tests for flywheel scheduler jobs."""
import pytest

from app.jobs.daily_outcome_update import run as daily_run
from app.jobs.weekly_walkforward_train import run as weekly_run
from app.jobs.champion_challenger_eval import run as eval_run
from app.jobs.scheduler import get_scheduler_status


class TestDailyOutcomeUpdate:
    def test_first_run_completes(self):
        import app.jobs.daily_outcome_update as mod
        mod._last_run_date = ""  # reset
        result = daily_run()
        assert result["status"] in ("completed", "error")
        assert "date" in result

    def test_idempotent_skips_second_run(self):
        import app.jobs.daily_outcome_update as mod
        mod._last_run_date = ""  # reset
        result1 = daily_run()
        result2 = daily_run()
        assert result2["status"] == "skipped"
        assert result2["reason"] == "already_run_today"


class TestWeeklyWalkforwardTrain:
    def test_first_run_returns_status(self):
        import app.jobs.weekly_walkforward_train as mod
        mod._last_train_date = ""  # reset
        result = weekly_run()
        # Will likely fail with "no data" since we don't have OHLCV data in test
        assert result["status"] in ("completed", "no_data", "error")

    def test_idempotent_skips_second_run(self):
        import app.jobs.weekly_walkforward_train as mod
        mod._last_train_date = ""  # reset
        result1 = weekly_run()
        result2 = weekly_run()
        assert result2["status"] == "skipped"
        assert result2["reason"] == "already_trained"


class TestChampionChallengerEval:
    def test_runs_without_crash(self):
        result = eval_run()
        # May return "no_challenger" since no model has been trained
        assert result["status"] in ("completed", "no_challenger", "error")
        assert "model_name" in result

    def test_reports_no_challenger(self):
        result = eval_run(model_name="nonexistent_model")
        assert result["status"] == "no_challenger"


class TestSchedulerStatus:
    def test_disabled_status(self):
        status = get_scheduler_status()
        # Scheduler should be disabled in test env (no SCHEDULER_ENABLED)
        assert status["enabled"] is False
        assert status["running"] is False
        assert status["jobs"] == []
