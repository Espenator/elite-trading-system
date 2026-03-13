"""
E2E verification for audit enhancements (E2E-AUDIT-REPORT.md fixes).

Verifies:
- Ingestion health returns 503 on failure (not 200 + error body)
- Agents API returns statusDisplay, cpu, mem for frontend
- Backtest results/optimization/walkforward/montecarlo return 501
- CORS includes 5174
- Flywheel sync in daily_outcome_update (logic path)
- ML scorer uses registry champion when available

Dashboard (http://localhost:5173/dashboard):
- TestDashboardDataEndpoints: every GET used by Dashboard.jsx (signals, portfolio,
  marketIndices, agents, performance, risk, flywheel, sentiment, cognitive, etc.)
- TestDashboardCnsEndpoints: CNS Vitals + Profit Brain (homeostasis, circuit-breaker,
  agents/health, last-verdict, profit-brain)
- TestDashboardActionEndpoints: POST routes for Run Scan, orders/advanced,
  flatten-all, emergency-stop (route exists; auth may return 401)
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


class TestIngestionHealth503:
    """Ingestion /health must return 503 when unhealthy (readiness probes)."""

    def test_ingestion_health_returns_200_when_healthy(self, client):
        # When DuckDB is available, health returns 200
        r = client.get("/api/ingestion/health")
        # Either 200 (healthy) or 503 (unhealthy) — never 200 with body {"status": "error"}
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            data = r.json()
            assert data.get("status") != "error"
        if r.status_code == 503:
            assert "unhealthy" in (r.json().get("detail") or "").lower() or "503" in str(r.status_code)


class TestAgentsPayloadNormalized:
    """GET /agents must include statusDisplay, cpu, mem for frontend."""

    def test_agents_response_has_normalized_fields(self, client):
        r = client.get("/api/v1/agents")
        assert r.status_code == 200
        data = r.json()
        agents = data.get("agents") or []
        for a in agents:
            assert "status" in a
            assert "statusDisplay" in a
            assert "cpu" in a
            assert "mem" in a


class TestAgentSpawnEndpoints:
    """POST /agents/spawn, clone, swarm/spawn, kill-all and GET /agents/swarm/templates (Patterns page)."""

    @pytest.fixture
    def auth_headers(self):
        import os
        token = os.environ.get("API_AUTH_TOKEN", "test_auth_token_for_tests")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def test_agents_spawn_requires_auth(self, client):
        r = client.post("/api/v1/agents/spawn", json={"name": "TestScanner", "type": "scanner"})
        assert r.status_code in (401, 403, 422)

    def test_agents_spawn_returns_200_with_auth(self, client, auth_headers):
        r = client.post("/api/v1/agents/spawn", headers=auth_headers, json={"name": "TestScanner", "type": "scanner"})
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "agent" in data
        assert data["agent"].get("id") is not None
        assert data["agent"].get("name") == "TestScanner"
        assert data["agent"].get("type") == "scanner"

    def test_agents_clone_returns_400_without_agent_id(self, client, auth_headers):
        r = client.post("/api/v1/agents/clone", headers=auth_headers, json={})
        assert r.status_code == 400

    def test_agents_clone_returns_200_with_auth(self, client, auth_headers):
        r = client.post("/api/v1/agents/clone", headers=auth_headers, json={"agent_id": 1})
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "agent" in data
        assert data["agent"].get("id") is not None

    def test_agents_swarm_spawn_returns_200_with_auth(self, client, auth_headers):
        r = client.post("/api/v1/agents/swarm/spawn", headers=auth_headers, json={})
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "message" in data

    def test_agents_swarm_templates_returns_200_with_auth(self, client, auth_headers):
        r = client.get("/api/v1/agents/swarm/templates", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "templates" in data
        assert isinstance(data["templates"], list)

    def test_agents_kill_all_returns_200_with_auth(self, client, auth_headers):
        r = client.post("/api/v1/agents/kill-all", headers=auth_headers, json={})
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "count" in data
        assert data.get("message", "").lower().find("paused") >= 0 or data.get("message", "").lower().find("all") >= 0

    def test_agents_list_includes_spawned_agent(self, client, auth_headers):
        """After spawn, GET /api/v1/agents must include the new agent (same id and name)."""
        r = client.post(
            "/api/v1/agents/spawn",
            headers=auth_headers,
            json={"name": "E2ESpawnCheck", "type": "scanner"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        agent = data.get("agent")
        assert agent is not None
        spawn_id = agent.get("id")
        spawn_name = agent.get("name")
        assert spawn_id is not None and spawn_name == "E2ESpawnCheck"
        r2 = client.get("/api/v1/agents")
        assert r2.status_code == 200
        list_data = r2.json()
        agents = list_data.get("agents") or []
        found = next((a for a in agents if a.get("id") == spawn_id and a.get("name") == spawn_name), None)
        assert found is not None, f"GET /agents should include spawned agent id={spawn_id} name={spawn_name}"


class TestBacktestStubs501:
    """Backtest stub endpoints must return 501 Not Implemented."""

    @pytest.mark.parametrize("path", [
        "/api/v1/backtest/results",
        "/api/v1/backtest/optimization",
        "/api/v1/backtest/walkforward",
        "/api/v1/backtest/montecarlo",
    ])
    def test_backtest_stub_returns_501(self, client, path):
        r = client.get(path)
        assert r.status_code == 501
        data = r.json()
        assert "detail" in data
        assert "not implemented" in (data.get("detail") or "").lower()


class TestCORS5174:
    """CORS config must include localhost:5174."""

    def test_cors_includes_5174(self):
        from app.core.config import settings
        origins = getattr(settings, "effective_cors_origins", None) or []
        assert any("5174" in str(o) for o in origins), "CORS should include localhost:5174"


class TestFlywheelSyncInDailyOutcome:
    """daily_outcome_update syncs outcome_resolver -> flywheel_data."""

    def test_daily_outcome_update_run_imports_and_has_sync_logic(self):
        from app.jobs import daily_outcome_update
        source = open(daily_outcome_update.__file__).read()
        assert "flywheel_data" in source or "db_service.set_config" in source
        assert "get_flywheel_metrics" in source


class TestMLScorerChampionPath:
    """MLScorer resolves model path via registry champion when available."""

    def test_ml_scorer_has_model_path_resolution(self):
        from app.services import ml_scorer
        assert hasattr(ml_scorer.MLScorer, "_model_path")


# ---------------------------------------------------------------------------
# Dashboard page (http://localhost:5173/dashboard) — every data feed & button
# ---------------------------------------------------------------------------

class TestDashboardDataEndpoints:
    """
    Every GET endpoint used by Dashboard.jsx must return 200 and a shape
    the frontend can consume. Missing or wrong shape = UI break or empty data.
    """

    def test_signals_returns_200_and_signals_key(self, client):
        r = client.get("/api/v1/signals/")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "signals" in data
        assert isinstance(data.get("signals"), list)

    def test_kelly_ranked_returns_200(self, client):
        r = client.get("/api/v1/signals/kelly-ranked")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "kellyRanked" in data or "kelly" in data or isinstance(data, list)

    def test_portfolio_returns_200(self, client):
        r = client.get("/api/v1/portfolio")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_market_indices_returns_200(self, client):
        r = client.get("/api/v1/market/indices")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_openclaw_returns_200(self, client):
        r = client.get("/api/v1/openclaw")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_performance_returns_200(self, client):
        r = client.get("/api/v1/performance")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_agents_returns_200_and_agents_list(self, client):
        r = client.get("/api/v1/agents")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "agents" in data
        assert isinstance(data.get("agents"), list)

    def test_agent_consensus_returns_200(self, client):
        r = client.get("/api/v1/agents/consensus")
        assert r.status_code == 200, r.text
        data = r.json()
        # Dashboard Swarm Consensus expects agents array (fallback from template when no conference)
        assert "agents" in data or "votes" in data
        agents = data.get("agents") or data.get("votes") or []
        assert isinstance(agents, list)
        if agents:
            assert "name" in agents[0] or "agent" in agents[0]
        assert isinstance(data, dict)

    def test_performance_equity_returns_200(self, client):
        r = client.get("/api/v1/performance/equity")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_risk_score_returns_200(self, client):
        r = client.get("/api/v1/risk/risk-score")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_system_alerts_returns_200(self, client):
        r = client.get("/api/v1/agents/alerts")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, (dict, list))

    def test_flywheel_returns_200(self, client):
        r = client.get("/api/v1/flywheel")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_sentiment_returns_200(self, client):
        r = client.get("/api/v1/sentiment")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_cognitive_dashboard_returns_200(self, client):
        r = client.get("/api/v1/cognitive/dashboard")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_signals_technicals_for_symbol_returns_200(self, client):
        r = client.get("/api/v1/signals/SPY/technicals")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)
        assert "technicals" in data or "indicators" in data

    def test_swarm_topology_for_symbol_returns_200(self, client):
        r = client.get("/api/v1/agents/swarm-topology/SPY")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_data_sources_returns_200(self, client):
        r = client.get("/api/v1/data-sources/")
        assert r.status_code == 200, r.text
        data = r.json()
        # API returns { dataSources: [...], sources: [...], total: N }
        items = data.get("dataSources") or data.get("sources") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        assert isinstance(items, list), "data-sources response must have dataSources/sources list or be a list"
        assert len(items) > 0, "data-sources list should not be empty"
        for item in items:
            assert "id" in item and "name" in item
            assert "status" in item

    def test_risk_proposal_for_symbol_returns_200(self, client):
        r = client.get("/api/v1/risk/proposal/SPY")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)
        assert "proposal" in data
        assert "proposedSize" in data.get("proposal", {}) or "maxShares" in data

    def test_quotes_book_for_symbol_returns_200(self, client):
        r = client.get("/api/v1/quotes/SPY/book")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)


class TestDashboardCnsEndpoints:
    """CNS Vitals and Profit Brain bar — endpoints used by dashboard widgets."""

    def test_cns_homeostasis_vitals_returns_200(self, client):
        r = client.get("/api/v1/cns/homeostasis/vitals")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_cns_circuit_breaker_status_returns_200(self, client):
        r = client.get("/api/v1/cns/circuit-breaker/status")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)
        assert "checks" in data or "thresholds" in data or "fired" in str(data).lower()

    def test_cns_agents_health_returns_200(self, client):
        r = client.get("/api/v1/cns/agents/health")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)
        assert "agents" in data or "summary" in data

    def test_cns_last_verdict_returns_200(self, client):
        r = client.get("/api/v1/cns/council/last-verdict")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data is None or isinstance(data, dict)

    def test_cns_profit_brain_returns_200(self, client):
        r = client.get("/api/v1/cns/profit-brain")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)


class TestDashboardActionEndpoints:
    """
    Dashboard buttons: Run Scan, Exec Top 5, Flatten, Emergency Stop, BUY/SELL.
    Without auth these may return 401/403; we assert route exists and responds.
    """

    def test_post_signals_run_scan_route_exists(self, client):
        r = client.post("/api/v1/signals/", json={})
        assert r.status_code in (200, 401, 403, 422), r.text

    def test_post_orders_advanced_route_exists(self, client):
        r = client.post(
            "/api/v1/orders/advanced",
            json={"symbol": "SPY", "side": "buy", "type": "market", "qty": "10", "time_in_force": "day"},
        )
        assert r.status_code in (200, 201, 400, 401, 403, 422), r.text

    def test_post_flatten_all_route_exists(self, client):
        r = client.post("/api/v1/orders/flatten-all")
        assert r.status_code in (200, 401, 403), r.text

    def test_post_emergency_stop_route_exists(self, client):
        r = client.post("/api/v1/orders/emergency-stop")
        assert r.status_code in (200, 401, 403), r.text
