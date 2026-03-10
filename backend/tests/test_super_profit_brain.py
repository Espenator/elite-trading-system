"""Behavioral tests for Super Profit Brain alignment: pipeline, degraded mode, learning integrity."""
import asyncio
import os
import sys

import pytest

# Ensure backend app is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── 1) Triage enforcement: covered in test_one_true_pipeline ─────────────────


def test_swarm_spawner_no_inline_ingestion():
    """SwarmSpawner must not import/call data_ingestion in its main flow."""
    import app.services.swarm_spawner as mod
    source = open(mod.__file__).read()
    # _run_swarm / _request_prep must not call data_ingestion directly
    assert "data_ingestion.ingest_daily_bars" not in source
    assert "data_ingestion.compute_and_store" not in source
    assert "symbol_prep" in source or "request_prep" in source


@pytest.mark.asyncio
async def test_symbol_prep_timeout_returns_degraded():
    """SymbolPrepService.request_prep_and_wait with timeout returns degraded payload."""
    from app.services.symbol_prep import SymbolPrepService

    svc = SymbolPrepService(message_bus=None)
    # Do not start workers; pass bus=None so no publish — wait will time out
    result = await svc.request_prep_and_wait("req-1", ["X"], timeout=0.02, bus=None)
    assert result.get("degraded") is True
    assert "timeout" in result.get("errors", [])


def test_ws_registry_has_channels_and_subscriber_counts():
    """GET /api/v1/ws/registry returns channel list and subscriber counts."""
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        r = client.get("/api/v1/ws/registry")
    assert r.status_code == 200
    data = r.json()
    assert "channels" in data
    assert "subscriber_counts" in data or "total_connections" in data


def test_daily_outcome_update_idempotent(monkeypatch):
    """daily_outcome_update skips when already run today (persisted state)."""
    from app.jobs import daily_outcome_update as mod
    from datetime import date

    today = date.today().isoformat()
    # Mock _get_state to return already-ran-today so run() skips without touching DuckDB
    monkeypatch.setattr(mod, "_get_state", lambda: {"last_run_date": today, "last_run_ts": 0, "last_result": None})
    result = mod.run()
    assert result.get("status") == "skipped"
    assert result.get("reason") == "already_run_today"


def test_council_registry_api_matches_runner():
    """Council API agent_count and agents come from registry; registry matches runner DAG."""
    from app.council.registry import get_agent_count, get_agents, get_dag_stages

    count = get_agent_count()
    agents = get_agents()
    stages = get_dag_stages()
    assert count >= 13
    assert "risk" in agents
    assert "strategy" in agents
    assert "arbiter" in agents
    flat = [a for stage in stages for a in stage]
    assert set(flat) >= {"risk", "strategy", "arbiter", "critic"}


def test_brain_degraded_endpoint():
    """GET /api/v1/brain/degraded returns degraded flag and reasons."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get("/api/v1/brain/degraded")
    assert r.status_code == 200
    data = r.json()
    assert "degraded" in data
    assert "reasons" in data


def test_outcome_tracker_timeout_censored(monkeypatch):
    """OutcomeTracker marks timeout as censored when policy is censor (default)."""
    from app.services.outcome_tracker import OutcomeTracker, TrackedPosition
    import time

    monkeypatch.setenv("SHADOW_TIMEOUT_POLICY", "censor")
    monkeypatch.delenv("OUTCOME_TIMEOUT_POLICY", raising=False)
    tracker = OutcomeTracker(message_bus=None)
    pos = TrackedPosition(
        order_id="t",
        symbol="X",
        side="buy",
        qty=1,
        entry_price=100.0,
        signal_score=50,
        kelly_pct=0.1,
        regime="",
        stop_loss=95,
        take_profit=110,
        is_shadow=True,
        opened_at=time.time() - 100000,
    )
    tracker._resolve_shadow_timeout(pos, time.time(), last_known_price=None)
    assert pos.is_censored is True
    assert pos.close_reason == "timeout_censored"


def test_weight_learner_ignores_censored():
    """WeightLearner.update_from_outcome returns unchanged weights when is_censored=True."""
    from app.council.weight_learner import get_weight_learner

    learner = get_weight_learner()
    before = dict(learner.get_weights())
    after = learner.update_from_outcome(
        symbol="TEST",
        outcome_direction="win",
        pnl=100.0,
        r_multiple=1.0,
        is_censored=True,
    )
    assert before == after


def test_price_cache_provides_prices():
    """PriceCacheService stores bar/quote and returns get_price."""
    from app.services.price_cache_service import PriceCacheService

    cache = PriceCacheService(message_bus=None)
    cache._prices["AAPL"] = 150.0
    cache._last_update_ts = 12345.0
    assert cache.get_price("AAPL") == 150.0
    assert cache.get_price("MSFT") is None
    assert cache.get_last_update_time() == 12345.0
    assert cache.get_prices(["AAPL", "MSFT"]) == {"AAPL": 150.0}
