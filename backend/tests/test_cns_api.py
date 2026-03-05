"""Tests for CNS (Central Nervous System) API endpoints."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestCnsHomeostasis:
    @pytest.mark.asyncio
    async def test_homeostasis_vitals(self):
        from app.api.v1.cns import homeostasis_vitals

        mock_monitor = MagicMock()
        mock_monitor.check_vitals = AsyncMock(return_value={"risk_score": 60})
        mock_monitor.get_mode.return_value = "NORMAL"
        mock_monitor.get_position_scale.return_value = 1.0
        mock_monitor.get_directive_regime.return_value = "unknown"
        mock_monitor._last_check = 1234567890

        with patch("app.council.homeostasis.get_homeostasis", return_value=mock_monitor):
            result = await homeostasis_vitals()
            assert result["mode"] == "NORMAL"
            assert result["position_scale"] == 1.0
            assert result["vitals"]["risk_score"] == 60

    @pytest.mark.asyncio
    async def test_homeostasis_vitals_fallback(self):
        """Should return defaults if homeostasis is unavailable."""
        from app.api.v1.cns import homeostasis_vitals

        with patch.dict("sys.modules", {"app.council.homeostasis": None}):
            result = await homeostasis_vitals()
            assert result["mode"] == "NORMAL"
            assert result["position_scale"] == 1.0


class TestCnsCircuitBreaker:
    @pytest.mark.asyncio
    async def test_circuit_breaker_status(self):
        from app.api.v1.cns import circuit_breaker_status

        with patch("app.council.reflexes.circuit_breaker._get_thresholds", return_value={
            "cb_vix_spike_threshold": 35.0,
            "cb_daily_drawdown_limit": 0.03,
        }):
            result = await circuit_breaker_status()
            assert result["armed"] is True
            assert len(result["checks"]) == 5


class TestCnsAgentsHealth:
    @pytest.mark.asyncio
    async def test_agents_health(self):
        from app.api.v1.cns import agents_health

        mock_sa = MagicMock()
        mock_sa.get_status.return_value = {
            "agent_a": {"skip": False, "streak": {"status": "ACTIVE"}},
            "agent_b": {"skip": True, "streak": {"status": "HIBERNATION"}},
        }

        with patch("app.council.self_awareness.get_self_awareness", return_value=mock_sa):
            result = await agents_health()
            assert result["summary"]["total_agents"] == 2
            assert result["summary"]["hibernated"] == 1


class TestCnsBlackboard:
    @pytest.mark.asyncio
    async def test_blackboard_no_data(self):
        from app.api.v1.cns import blackboard_current

        with patch("app.api.v1.council._latest_decision", None):
            result = await blackboard_current()
            assert result["available"] is False

    @pytest.mark.asyncio
    async def test_blackboard_with_data(self):
        from app.api.v1.cns import blackboard_current

        with patch("app.api.v1.council._latest_decision", {
            "council_decision_id": "abc-123",
            "symbol": "AAPL",
            "final_direction": "buy",
            "final_confidence": 0.85,
            "votes": [],
            "vetoed": False,
            "timestamp": "2025-01-01",
        }):
            result = await blackboard_current()
            assert result["available"] is True
            assert result["symbol"] == "AAPL"
            assert result["direction"] == "buy"


class TestCnsDirectives:
    @pytest.mark.asyncio
    async def test_list_directives(self):
        from app.api.v1.cns import list_directives

        mock_loader = MagicMock()
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_file = MagicMock()
        mock_file.name = "global.md"
        mock_file.read_text.return_value = "# Global"
        mock_dir.glob.return_value = [mock_file]
        mock_loader._dir = mock_dir

        with patch("app.council.directives.loader.directive_loader", mock_loader):
            result = await list_directives()
            assert len(result["directives"]) == 1
            assert result["directives"][0]["filename"] == "global.md"


class TestCnsPostmortems:
    @pytest.mark.asyncio
    async def test_list_postmortems(self):
        from app.api.v1.cns import list_postmortems

        with patch("app.data.duckdb_storage.duckdb_store") as mock_db:
            mock_db.get_postmortems.return_value = [
                {"council_decision_id": "abc", "symbol": "AAPL"}
            ]
            result = await list_postmortems()
            assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_postmortem_attribution(self):
        from app.api.v1.cns import postmortem_attribution

        with patch("app.data.duckdb_storage.duckdb_store") as mock_db:
            mock_db.get_postmortems.return_value = [
                {
                    "agent_votes": [
                        {"agent_name": "risk", "direction": "buy", "confidence": 0.8},
                        {"agent_name": "strategy", "direction": "buy", "confidence": 0.6},
                    ]
                }
            ]
            result = await postmortem_attribution()
            assert "risk" in result["attribution"]
            assert result["attribution"]["risk"]["total_votes"] == 1
            assert result["attribution"]["risk"]["avg_confidence"] == 0.8


class TestCnsLastVerdict:
    @pytest.mark.asyncio
    async def test_last_verdict(self):
        from app.api.v1.cns import council_last_verdict

        mock_h = MagicMock()
        mock_h.get_mode.return_value = "NORMAL"
        mock_h.get_position_scale.return_value = 1.0

        with patch("app.api.v1.council._latest_decision", {"symbol": "AAPL", "final_direction": "buy"}):
            with patch("app.council.homeostasis.get_homeostasis", return_value=mock_h):
                result = await council_last_verdict()
                assert result["verdict"]["symbol"] == "AAPL"
                assert result["homeostasis_mode"] == "NORMAL"
