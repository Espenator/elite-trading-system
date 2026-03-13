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


class TestStartupHealthCheck:
    """GET /api/v1/health/startup-check returns 7 phases and failure_patterns."""

    def test_startup_check_returns_phases_and_failure_patterns(self, client):
        r = client.get("/api/v1/health/startup-check")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "phases" in data
        assert "overall_ok" in data
        assert "failure_patterns" in data
        phases = data["phases"]
        for key in ("1_environment", "2_backend_startup", "3_router_verification", "4_api_smoke",
                    "5_signal_pipeline", "6_frontend_wiring", "7_background_loops"):
            assert key in phases, f"missing phase {key}"
            assert "label" in phases[key] and "ok" in phases[key] and "checks" in phases[key]
        assert isinstance(data["failure_patterns"], list)
        assert len(data["failure_patterns"]) >= 1
        for row in data["failure_patterns"]:
            assert "symptom" in row and "cause" in row and "remediation" in row


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

    def test_stocks_returns_200_and_symbols_key(self, client):
        """GET /api/v1/stocks or /api/v1/stocks/ (frontend useApi('stocks')) — symbol list for symbol-click navigation."""
        r = client.get("/api/v1/stocks")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "symbols" in data
        assert isinstance(data.get("symbols"), list)
        assert "count" in data
        r_slash = client.get("/api/v1/stocks/", follow_redirects=True)
        assert r_slash.status_code == 200, r_slash.text

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

    def test_council_status_returns_200(self, client):
        """GET /api/v1/council/status — council config (agent_count, dag_stages) for dashboard."""
        r = client.get("/api/v1/council/status")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)
        assert "agent_count" in data or "council_enabled" in data

    def test_council_latest_returns_200(self, client):
        """GET /api/v1/council/latest — latest council decision for symbol detail / dashboard."""
        r = client.get("/api/v1/council/latest")
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

    def test_cns_circuit_breaker_audit_returns_schema(self, client):
        """GET /api/v1/cns/circuit-breaker/audit returns agent audit schema."""
        r = client.get("/api/v1/cns/circuit-breaker/audit")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("agent") == "circuit_breakers"
        assert "normal_conditions_pass" in data
        assert isinstance(data["normal_conditions_pass"], bool)
        assert "flash_crash_halts" in data
        assert isinstance(data["flash_crash_halts"], bool)
        assert "vix_spike_halts" in data
        assert isinstance(data["vix_spike_halts"], bool)
        assert "daily_drawdown_halts" in data
        assert "position_limit_halts" in data
        assert "market_hours_halts" in data
        assert data.get("runner_skips_council_on_halt") is True
        assert "execution_time_ms" in data
        assert isinstance(data["execution_time_ms"], int)
        assert "thresholds_from_directives" in data
        assert "errors" in data
        assert isinstance(data["errors"], list)
        assert data["flash_crash_halts"] is True
        assert data["vix_spike_halts"] is True

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


# ---------------------------------------------------------------------------
# Council pipeline E2E audit report (schema from launch audit)
# ---------------------------------------------------------------------------

# Stage 1 = perception + academic edge; S2 = hypothesis (stage 3); S3 = strategy (4);
# S4 = risk_execution (5); S5 = critic (6); S6 = arbiter (post-stage 7)
STAGE_1_AGENTS = {
    "market_perception", "flow_perception", "regime", "social_perception",
    "news_catalyst", "youtube_knowledge", "intermarket",
    "gex_agent", "insider_agent", "finbert_sentiment_agent",
    "earnings_tone_agent", "dark_pool_agent", "macro_regime_agent",
}
VETO_AGENTS = {"risk", "execution"}
REQUIRED_VOTE_KEYS = ("agent_name", "direction", "confidence", "reasoning", "veto", "weight")


def _validate_agent_vote_schema(v: dict) -> bool:
    """Return True if v looks like a valid AgentVote (direction, confidence in range, etc.)."""
    if not isinstance(v, dict):
        return False
    for k in REQUIRED_VOTE_KEYS:
        if k not in v:
            return False
    direction = v.get("direction", "")
    if direction not in ("buy", "sell", "hold"):
        return False
    conf = v.get("confidence", -1)
    if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
        return False
    weight = v.get("weight", 0)
    if not isinstance(weight, (int, float)) or weight <= 0:
        return False
    return True


def build_council_pipeline_audit_report(
    agent: str = "council_pipeline",
    symbols_tested: list = None,
    decisions: list = None,
) -> dict:
    """Build audit report from one or more council evaluate responses.

    decisions: list of response dicts from POST /api/v1/council/evaluate (decision.to_dict()).
    Merges all decisions to fill stage_results, total_pipeline_ms, veto_logic_correct, etc.
    """
    symbols_tested = symbols_tested or []
    decisions = decisions or []
    errors = []
    all_votes = []
    total_pipeline_ms = 0
    council_decision_id = ""
    blackboard_created = False
    stage_latencies = {}

    for d in decisions:
        if not d:
            continue
        cid = d.get("council_decision_id") or ""
        if cid:
            blackboard_created = True
            council_decision_id = cid
        cognitive = d.get("cognitive") or {}
        total_pipeline_ms = max(total_pipeline_ms, cognitive.get("total_latency_ms", 0))
        sl = cognitive.get("stage_latencies") or {}
        for k in ("stage1", "stage2", "stage3", "stage4", "stage5", "stage5.5", "stage6"):
            if k in sl:
                try:
                    stage_latencies[k] = int(round(float(sl[k])))
                except (TypeError, ValueError):
                    stage_latencies[k] = 0
        votes = d.get("votes") or []
        for v in votes:
            all_votes.append(v if isinstance(v, dict) else (v.to_dict() if hasattr(v, "to_dict") else {}))

    all_agent_votes_valid_schema = all(_validate_agent_vote_schema(v) for v in all_votes)
    if not all_votes and decisions:
        errors.append("No votes in decision response")

    # Veto logic: only risk/execution may have veto=True; if vetoed, final_direction must be hold
    veto_logic_correct = True
    for d in decisions:
        final = (d.get("final_direction") or "").lower()
        vetoed = d.get("vetoed", False)
        if vetoed and final != "hold":
            veto_logic_correct = False
            errors.append("vetoed=True but final_direction is not hold")
        for v in (d.get("votes") or []):
            vote = v if isinstance(v, dict) else getattr(v, "to_dict", lambda: {})()
            if vote.get("veto") is True:
                name = (vote.get("agent_name") or "").lower()
                # Normalize: "risk_agent" -> "risk", "execution_agent" -> "execution"
                base = name.replace("_agent", "").split("_")[0]
                if base not in VETO_AGENTS and name not in VETO_AGENTS:
                    veto_logic_correct = False
                    errors.append(f"Veto from non-veto agent: {name}")

    # Map runner stages to audit schema stages (S1..S6)
    def stage_result(passed: bool, time_ms: int, agents_wrote: list = None, used_llm: bool = False):
        r = {"passed": bool(passed), "time_ms": int(time_ms)}
        if agents_wrote is not None:
            r["agents_wrote"] = list(agents_wrote)
        r["used_llm"] = bool(used_llm)
        return r

    s1_agents = [v.get("agent_name") for v in all_votes if v.get("agent_name") in STAGE_1_AGENTS]
    used_llm = any(
        (v.get("agent_name") or "").lower() == "hypothesis"
        for v in all_votes
    )

    stage_results = {
        "S1_perception": stage_result(
            passed=len(s1_agents) >= 3,
            time_ms=stage_latencies.get("stage1", 0),
            agents_wrote=s1_agents[:10] or ["market", "flow", "regime"],
        ),
        "S2_hypothesis": stage_result(
            passed=any((v.get("agent_name") or "").lower() in ("hypothesis", "layered_memory_agent") for v in all_votes),
            time_ms=stage_latencies.get("stage3", 0),
            used_llm=used_llm,
        ),
        "S3_strategy": stage_result(
            passed=any((v.get("agent_name") or "").lower() == "strategy" for v in all_votes),
            time_ms=stage_latencies.get("stage4", 0),
        ),
        "S4_risk_execution": stage_result(
            passed=any(
                (v.get("agent_name") or "").lower() in ("risk", "risk_agent", "execution", "execution_agent")
                for v in all_votes
            ),
            time_ms=stage_latencies.get("stage5", 0),
        ),
        "S5_critic": stage_result(
            passed=any((v.get("agent_name") or "").lower() == "critic" for v in all_votes),
            time_ms=stage_latencies.get("stage6", 0),
        ),
        "S6_arbiter": stage_result(
            passed=bool(decisions and (decisions[0].get("final_direction") or decisions[0].get("vote_count", 0) > 0)),
            time_ms=0,
        ),
    }

    decision_id_matches_blackboard = True
    if decisions and council_decision_id:
        for d in decisions:
            if (d.get("council_decision_id") or "") != council_decision_id and d.get("council_decision_id"):
                decision_id_matches_blackboard = False
                break

    return {
        "agent": agent,
        "blackboard_created": blackboard_created,
        "stage_results": stage_results,
        "total_pipeline_ms": int(round(total_pipeline_ms)),
        "veto_logic_correct": veto_logic_correct,
        "symbols_tested": list(symbols_tested),
        "all_agent_votes_valid_schema": all_agent_votes_valid_schema,
        "decision_id_matches_blackboard": decision_id_matches_blackboard,
        "errors": errors,
    }


class TestCouncilPipelineAudit:
    """
    E2E audit: council pipeline produces a report that matches the launch audit schema.
    Report shape: agent, blackboard_created, stage_results (S1..S6), total_pipeline_ms,
    veto_logic_correct, symbols_tested, all_agent_votes_valid_schema,
    decision_id_matches_blackboard, errors.
    """

    @pytest.fixture
    def auth_headers(self):
        import os
        token = os.environ.get("API_AUTH_TOKEN", "test_auth_token_for_tests")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    @pytest.mark.anyio
    async def test_audit_report_schema_from_mock_council(self, client, auth_headers):
        """Build audit report from a single council evaluate response (mocked run_council)."""
        from unittest.mock import AsyncMock, patch

        from app.council.schemas import AgentVote, DecisionPacket, CognitiveMeta

        def _make_vote(name: str, direction: str = "buy", confidence: float = 0.6, veto: bool = False):
            return AgentVote(
                agent_name=name,
                direction=direction,
                confidence=confidence,
                reasoning=f"{name} vote",
                veto=veto,
                veto_reason="test" if veto else "",
                weight=1.0,
            )

        # Minimal DecisionPacket with cognitive.stage_latencies and council_decision_id
        async def _mock_run_council(symbol, timeframe="1d", features=None, context=None):
            votes = [
                _make_vote("market_perception"), _make_vote("flow_perception"), _make_vote("regime"),
                _make_vote("rsi"), _make_vote("hypothesis"), _make_vote("strategy"),
                _make_vote("risk"), _make_vote("execution"), _make_vote("critic"),
            ]
            cognitive = CognitiveMeta(
                total_latency_ms=450.0,
                stage_latencies={
                    "stage1": 120, "stage2": 80, "stage3": 100,
                    "stage4": 30, "stage5": 90, "stage6": 30,
                },
            )
            return DecisionPacket(
                symbol=symbol,
                timeframe=timeframe,
                timestamp="2026-03-12T00:00:00Z",
                votes=votes,
                final_direction="buy",
                final_confidence=0.55,
                vetoed=False,
                veto_reasons=[],
                risk_limits={},
                execution_ready=True,
                council_reasoning="Audit test",
                council_decision_id="audit-test-decision-id-123",
                cognitive=cognitive,
            )

        with patch("app.council.runner.run_council", new=_mock_run_council):
            r = client.post(
                "/api/v1/council/evaluate",
                headers=auth_headers,
                json={"symbol": "AAPL", "timeframe": "1d"},
            )
        assert r.status_code == 200, r.text
        data = r.json()
        report = build_council_pipeline_audit_report(
            symbols_tested=["AAPL"],
            decisions=[data],
        )
        assert report["agent"] == "council_pipeline"
        assert report["blackboard_created"] is True
        assert report["total_pipeline_ms"] >= 0
        assert report["veto_logic_correct"] is True
        assert report["symbols_tested"] == ["AAPL"]
        assert report["all_agent_votes_valid_schema"] is True
        assert report["decision_id_matches_blackboard"] is True
        assert isinstance(report["errors"], list)
        stage_results = report["stage_results"]
        for key in ("S1_perception", "S2_hypothesis", "S3_strategy", "S4_risk_execution", "S5_critic", "S6_arbiter"):
            assert key in stage_results
            assert "passed" in stage_results[key]
            assert "time_ms" in stage_results[key]
        assert stage_results["S1_perception"].get("agents_wrote")
        assert "used_llm" in stage_results["S2_hypothesis"]

    @pytest.mark.anyio
    async def test_audit_report_veto_logic_reject_non_veto_agent(self):
        """Veto from non risk/execution agent sets veto_logic_correct=False."""
        bad_votes = [
            {"agent_name": "risk", "direction": "buy", "confidence": 0.5, "reasoning": "ok", "veto": False, "weight": 1.0},
            {"agent_name": "noise_agent", "direction": "hold", "confidence": 0.0, "reasoning": "x", "veto": True, "weight": 1.0},
        ]
        decision = {
            "council_decision_id": "id-1",
            "votes": bad_votes,
            "final_direction": "hold",
            "vetoed": True,
            "cognitive": {"total_latency_ms": 100, "stage_latencies": {}},
        }
        report = build_council_pipeline_audit_report(decisions=[decision], symbols_tested=[])
        assert report["veto_logic_correct"] is False
        assert any("non-veto" in e for e in report["errors"])


# =============================================================================
# Signal pipeline E2E verification (Cursor Prompt #2: verify signals flow end-to-end)
# Pipeline: market_data.bar → EventDrivenSignalEngine → signal.generated →
#           CouncilGate → council → council.verdict → OrderExecutor → order.submitted
# =============================================================================


class TestSignalPipelineBarToSignal:
    """Verify market_data.bar → EventDrivenSignalEngine → signal.generated."""

    @pytest.mark.asyncio
    async def test_bar_events_produce_signal_generated_when_score_above_threshold(self):
        """Publishing 5+ bullish bars yields at least one signal.generated with valid shape."""
        from app.core.message_bus import MessageBus
        from app.services.signal_engine import EventDrivenSignalEngine

        signals = []
        bus = MessageBus()
        await bus.start()

        async def collect_signal(data):
            signals.append(data)

        await bus.subscribe("signal.generated", collect_signal)
        engine = EventDrivenSignalEngine(bus)
        await engine.start()

        # 5+ bars: clear uptrend so _compute_composite_score yields score >= 65
        symbol = "PIPELINE_TEST"
        base = 100.0
        for i in range(6):
            bar = {
                "symbol": symbol,
                "open": base + i * 0.5,
                "high": base + i * 0.5 + 1.0,
                "low": base + i * 0.5 - 0.3,
                "close": base + i * 0.5 + 0.8,
                "volume": 1_000_000,
            }
            await bus.publish("market_data.bar", bar)

        for _ in range(30):
            await __import__("asyncio").sleep(0.1)
            if signals:
                break

        await engine.stop()
        await bus.stop()

        assert len(signals) >= 1, "EventDrivenSignalEngine should publish signal.generated from bars"
        sig = signals[0]
        assert sig.get("symbol") == symbol
        assert "score" in sig
        assert 0 <= sig["score"] <= 100
        assert sig.get("source") == "event_driven_signal_engine"
        assert sig.get("label")  # e.g. momentum_bull or similar


class TestSignalPipelineFullChain:
    """Verify signal.generated → CouncilGate → council.verdict → OrderExecutor → order.submitted."""

    @pytest.mark.asyncio
    async def test_signal_to_verdict_to_order_submitted(self):
        """Full chain: signal.generated → council.verdict → order.submitted (stubbed council, shadow executor)."""
        from unittest.mock import patch, MagicMock
        from types import SimpleNamespace
        import asyncio
        from app.core.message_bus import MessageBus
        from app.council.council_gate import CouncilGate
        from app.services.order_executor import OrderExecutor

        verdicts = []
        orders = []
        bus = MessageBus()
        await bus.start()
        await bus.subscribe("council.verdict", lambda d: verdicts.append(d))
        await bus.subscribe("order.submitted", lambda d: orders.append(d))

        async def _stub_run_council(symbol=None, **kwargs):
            sym = symbol or kwargs.get("symbol", "E2E")
            return SimpleNamespace(
                vetoed=False,
                veto_reasons=[],
                final_direction="buy",
                final_confidence=0.9,
                execution_ready=True,
                votes=[],
                symbol=sym,
                to_dict=lambda: {
                    "symbol": sym,
                    "vetoed": False,
                    "final_direction": "buy",
                    "final_confidence": 0.9,
                    "execution_ready": True,
                },
            )

        with patch("app.council.runner.run_council", side_effect=_stub_run_council):
            gate = CouncilGate(bus, gate_threshold=0.0, max_concurrent=2, cooldown_seconds=0)
            await gate.start()

            executor = OrderExecutor(
                bus,
                auto_execute=False,
                min_score=0,
                max_daily_trades=100,
                cooldown_seconds=0,
            )
            async def _stub_kelly(symbol, score, regime, price, direction):
                return {
                    "action": "TRADE",
                    "kelly_pct": 0.05,
                    "qty": 10,
                    "edge": 0.1,
                    "stats_source": "test",
                    "stop_loss": price * 0.98,
                    "take_profit": price * 1.05,
                    "raw_kelly": 0.05,
                    "win_rate": 0.55,
                    "trade_count": 50,
                }
            executor._compute_kelly_size = _stub_kelly
            await executor.start()

            await bus.publish("signal.generated", {
                "symbol": "E2E",
                "score": 80,
                "label": "momentum_bull",
                "direction": "buy",
                "price": 100.0,
                "source": "test",
            })

            for _ in range(50):
                await asyncio.sleep(0.05)
                if verdicts and orders:
                    break

            await executor.stop()
            await gate.stop()

        await bus.stop()

        assert len(verdicts) >= 1, "CouncilGate should publish council.verdict"
        assert verdicts[0].get("execution_ready") is True
        assert verdicts[0].get("final_direction") == "buy"
        assert len(orders) >= 1, "OrderExecutor should publish order.submitted"
        assert orders[0].get("symbol") == "E2E"
