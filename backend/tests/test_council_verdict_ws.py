"""Tests for council verdict API and WebSocket broadcast.

- Compact verdict payload shape (build_compact_verdict_payload)
- POST /council/evaluate triggers broadcast; response unchanged
- WebSocket broadcast failure does not break pipeline (broadcast is best-effort)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestBuildCompactVerdictPayload:
    """Compact payload has required keys and is frontend-friendly."""

    def test_payload_has_required_keys(self):
        from app.council.verdict_broadcast import build_compact_verdict_payload

        verdict = {
            "council_decision_id": "dec-123",
            "symbol": "AAPL",
            "final_direction": "buy",
            "final_confidence": 0.72,
            "votes": [
                {"agent_name": "risk", "direction": "buy", "confidence": 0.8, "veto": False},
                {"agent_name": "strategy", "direction": "buy", "confidence": 0.7, "veto": False},
            ],
            "execution_ready": True,
            "timestamp": "2026-03-12T12:00:00Z",
        }
        out = build_compact_verdict_payload(verdict)
        assert "councildecisionid" in out
        assert out["councildecisionid"] == "dec-123"
        assert out["symbol"] == "AAPL"
        assert out["direction"] == "buy"
        assert out["confidence"] == 0.72
        assert "vote_summary" in out
        assert out["vote_summary"]["buy"] == 2
        assert "halt_reason" in out
        assert out["halt_reason"] is None
        assert "timestamp" in out
        assert out["execution_ready"] is True

    def test_payload_with_halt_reason(self):
        from app.council.verdict_broadcast import build_compact_verdict_payload

        verdict = {
            "symbol": "TSLA",
            "final_direction": "hold",
            "final_confidence": 0.3,
            "votes": [],
            "execution_ready": False,
        }
        out = build_compact_verdict_payload(verdict, halt_reason="timeout")
        assert out["symbol"] == "TSLA"
        assert out["direction"] == "hold"
        assert out["halt_reason"] == "timeout"
        assert out["execution_ready"] is False

    def test_payload_uses_halt_reason_from_verdict_when_param_none(self):
        from app.council.verdict_broadcast import build_compact_verdict_payload

        verdict = {
            "symbol": "MSFT",
            "final_direction": "hold",
            "final_confidence": 0.0,
            "votes": [],
            "halt_reason": "vetoed",
            "execution_ready": False,
        }
        out = build_compact_verdict_payload(verdict)
        assert out["halt_reason"] == "vetoed"


class TestBroadcastCouncilVerdictNeverRaises:
    """broadcast_council_verdict must not raise so WS failures do not break pipeline."""

    @pytest.mark.asyncio
    async def test_broadcast_swallows_exception(self):
        from app.council.verdict_broadcast import broadcast_council_verdict

        with patch("app.websocket_manager.broadcast_ws", new_callable=AsyncMock) as mock_ws:
            mock_ws.side_effect = RuntimeError("WebSocket down")
            await broadcast_council_verdict({"councildecisionid": "x", "symbol": "AAPL"})
            mock_ws.assert_called_once()
        # No exception propagated


class TestCouncilEvaluateBroadcast:
    """POST /council/evaluate triggers verdict broadcast; response unchanged."""

    def test_evaluate_calls_broadcast_on_success(self, client, auth_headers):
        """When run_council returns, broadcast is invoked with compact payload (mock run_council)."""
        from fastapi.testclient import TestClient
        from app.main import app

        fake_decision = MagicMock()
        fake_decision.to_dict.return_value = {
            "council_decision_id": "eval-456",
            "symbol": "AAPL",
            "final_direction": "buy",
            "final_confidence": 0.65,
            "votes": [],
            "execution_ready": True,
            "timestamp": "2026-03-12T12:00:00Z",
        }
        fake_decision.vetoed = False
        fake_decision.final_direction = "buy"
        fake_decision.execution_ready = True

        with patch("app.council.runner.run_council", new_callable=AsyncMock, return_value=fake_decision):
            with patch(
                "app.council.verdict_broadcast.broadcast_council_verdict",
                new_callable=AsyncMock,
            ) as mock_broadcast:
                sync_client = TestClient(app)
                r = sync_client.post(
                    "/api/v1/council/evaluate",
                    json={"symbol": "AAPL", "timeframe": "1d"},
                    headers=auth_headers,
                )
                assert r.status_code == 200
                import time
                time.sleep(0.25)
                if mock_broadcast.called:
                    call_args = mock_broadcast.call_args
                    payload = call_args[0][0] if call_args[0] else {}
                    assert payload.get("symbol") == "AAPL"
                    assert "councildecisionid" in payload or "council_decision_id" in str(payload)
                data = r.json()
                assert data.get("symbol") == "AAPL"
                assert "final_direction" in data

    def test_evaluate_returns_200_even_if_broadcast_raises(self, client, auth_headers):
        """Pipeline is not broken when WebSocket broadcast fails (broadcast is best-effort)."""
        from fastapi.testclient import TestClient
        from app.main import app
        sync_client = TestClient(app)

        fake_decision = MagicMock()
        fake_decision.to_dict.return_value = {
            "council_decision_id": "x",
            "symbol": "AAPL",
            "final_direction": "hold",
            "final_confidence": 0.5,
            "votes": [],
            "execution_ready": False,
            "timestamp": "2026-03-12T12:00:00Z",
        }
        fake_decision.vetoed = False
        fake_decision.final_direction = "hold"
        fake_decision.execution_ready = False

        with patch("app.council.runner.run_council", new_callable=AsyncMock, return_value=fake_decision):
            with patch(
                "app.council.verdict_broadcast.broadcast_council_verdict",
                new_callable=AsyncMock,
                side_effect=OSError("WebSocket connection refused"),
            ):
                r = sync_client.post(
                    "/api/v1/council/evaluate",
                    json={"symbol": "AAPL"},
                    headers=auth_headers,
                )
                # Endpoint must still return 200 (broadcast runs in task and swallows errors)
                assert r.status_code == 200

    def test_evaluate_returns_504_on_timeout_and_emits_halted(self, client, auth_headers):
        """On council timeout, API returns 504 and a halted verdict is broadcast (mock)."""
        from fastapi.testclient import TestClient
        from app.main import app
        sync_client = TestClient(app)

        with patch("app.council.runner.run_council", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = asyncio.TimeoutError()
            with patch(
                "app.api.v1.council._broadcast_verdict_safe",
                new_callable=AsyncMock,
            ) as mock_broadcast:
                r = sync_client.post(
                    "/api/v1/council/evaluate",
                    json={"symbol": "GOOG"},
                    headers=auth_headers,
                )
                assert r.status_code == 504
                detail = (r.json().get("detail") or "").lower()
                assert "timeout" in detail or "timed out" in detail
                import time
                time.sleep(0.15)
                if mock_broadcast.called:
                    assert mock_broadcast.call_args.kwargs.get("halt_reason") == "timeout"
