"""Notification system audit tests — Slack token expiry, deduplication, TradingView signature.

Covers:
- Slack: token expiry (401/invalid_auth) handled gracefully; no auto-refresh.
- Slack: no message deduplication for signals/verdicts (same symbol can flood within 5 min).
- TradingView webhook: secret validation when TRADINGVIEW_WEBHOOK_SECRET is set.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.slack_notification_service import (
    SlackNotificationService,
    CH_SIGNALS,
    get_slack_service,
)


# ─── Slack token expiry (graceful degradation) ─────────────────────────────

@pytest.mark.asyncio
async def test_slack_token_expiry_returns_false_does_not_raise(monkeypatch):
    """When Slack API returns invalid_auth (e.g. expired token), service returns False and does not raise."""
    monkeypatch.setattr("app.services.slack_notification_service.settings.SLACK_BOT_TOKEN", "xoxb-expired-token")

    async def _fake_post(*args, **kwargs):
        # Slack returns 200 with ok: false for auth errors
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"ok": False, "error": "invalid_auth"}
        return resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=_fake_post)
        mock_client_cls.return_value = mock_client

        svc = SlackNotificationService()
        result = await svc._post_message(CH_SIGNALS, "Test message")

    assert result is False


@pytest.mark.asyncio
async def test_slack_http_401_returns_false_does_not_raise(monkeypatch):
    """When Slack API returns HTTP 401, service handles it and returns False."""
    monkeypatch.setattr("app.services.slack_notification_service.settings.SLACK_BOT_TOKEN", "xoxb-token")

    async def _fake_post(*args, **kwargs):
        resp = MagicMock()
        resp.status_code = 401
        resp.json.return_value = {"ok": False, "error": "invalid_auth"}
        return resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=_fake_post)
        mock_client_cls.return_value = mock_client

        svc = SlackNotificationService()
        result = await svc._post_message(CH_SIGNALS, "Test")

    assert result is False


# ─── Message deduplication (same signal within 5 minutes) ───────────────────

@pytest.mark.asyncio
async def test_slack_no_deduplication_same_signal_sent_twice(monkeypatch):
    """Same symbol+direction sent twice (with >1s gap to avoid rate limit) results in two API calls — no deduplication."""
    monkeypatch.setattr("app.services.slack_notification_service.settings.SLACK_BOT_TOKEN", "xoxb-test")
    post_calls = []

    async def _capture_post(*args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"ok": True}
        post_calls.append((args, kwargs))
        return resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=_capture_post)
        mock_client_cls.return_value = mock_client

        # Reset module-level rate limit state so two sends can both go through (simulate >1s apart)
        import app.services.slack_notification_service as slack_mod
        slack_mod._last_send.clear()

        svc = SlackNotificationService()
        r1 = await svc.send_signal("AAPL", "LONG", score=80, kelly_pct=5.0)
        slack_mod._last_send[CH_SIGNALS] = 0  # allow next send (simulate >1s elapsed)
        r2 = await svc.send_signal("AAPL", "LONG", score=80, kelly_pct=5.0)

    assert r1 is True and r2 is True
    assert len(post_calls) == 2, "No deduplication: same signal sent twice produces two Slack API calls"


@pytest.mark.asyncio
async def test_slack_rate_limit_one_per_second_per_channel(monkeypatch):
    """Rate limit 1 msg/sec per channel: second send within 1s returns False."""
    monkeypatch.setattr("app.services.slack_notification_service.settings.SLACK_BOT_TOKEN", "xoxb-test")

    async def _ok_post(*args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"ok": True}
        return resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=_ok_post)
        mock_client_cls.return_value = mock_client

        import app.services.slack_notification_service as slack_mod
        slack_mod._last_send.clear()

        svc = SlackNotificationService()
        r1 = await svc._post_message(CH_SIGNALS, "First")
        r2 = await svc._post_message(CH_SIGNALS, "Second")  # within same second

    assert r1 is True
    assert r2 is False, "Second message within 1s should be rate-limited"
    assert mock_client.post.call_count == 1


# ─── TradingView webhook signature/secret validation ────────────────────────

@pytest.mark.asyncio
async def test_tradingview_webhook_signature_validation_missing_secret_returns_401(client, monkeypatch):
    """When TRADINGVIEW_WEBHOOK_SECRET is set, request with missing secret returns 401."""
    monkeypatch.setattr("app.core.config.settings.TRADINGVIEW_WEBHOOK_SECRET", "required_secret")
    body = {
        "symbol": "AAPL",
        "action": "BUY",
        "price": 100.0,
        "timeframe": "5m",
        "strategy": "Test",
        "timestamp": "2026-03-12T12:00:00Z",
        "mode": "council",
    }
    # No "secret" key
    r = await client.post("/api/v1/webhooks/tradingview", json=body)
    assert r.status_code == 401
    assert "secret" in r.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_tradingview_webhook_signature_validation_wrong_secret_returns_401(client, monkeypatch):
    """When TRADINGVIEW_WEBHOOK_SECRET is set, wrong secret in payload returns 401."""
    monkeypatch.setattr("app.core.config.settings.TRADINGVIEW_WEBHOOK_SECRET", "correct_secret")
    body = {
        "symbol": "AAPL",
        "action": "BUY",
        "price": 100.0,
        "secret": "wrong_secret",
        "timeframe": "5m",
        "strategy": "Test",
        "timestamp": "2026-03-12T12:00:00Z",
        "mode": "council",
    }
    r = await client.post("/api/v1/webhooks/tradingview", json=body)
    assert r.status_code == 401
    assert "secret" in r.json().get("detail", "").lower() or "invalid" in r.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_tradingview_webhook_no_secret_configured_accepts_without_secret(client, monkeypatch):
    """When TRADINGVIEW_WEBHOOK_SECRET is not set, payload without secret is accepted (validation skipped)."""
    monkeypatch.setattr("app.core.config.settings.TRADINGVIEW_WEBHOOK_SECRET", "")

    async def _stub_run_council(*args, **kwargs):
        from app.council.schemas import DecisionPacket, CognitiveMeta
        return DecisionPacket(
            symbol=kwargs.get("symbol", "AAPL"),
            timeframe="1d",
            timestamp="2026-03-12T12:00:00Z",
            votes=[],
            final_direction="buy",
            final_confidence=0.7,
            vetoed=False,
            veto_reasons=[],
            risk_limits={},
            execution_ready=False,
            council_reasoning="stub",
            council_decision_id="audit-id",
            cognitive=CognitiveMeta(),
        )

    with patch("app.council.runner.run_council", _stub_run_council):
        with patch("app.core.message_bus.get_message_bus"):
            with patch("app.websocket_manager.broadcast_ws", new_callable=AsyncMock):
                r = await client.post(
                    "/api/v1/webhooks/tradingview",
                    json={
                        "symbol": "AAPL",
                        "action": "BUY",
                        "price": 100.0,
                        "timeframe": "5m",
                        "mode": "council",
                    },
                )
    assert r.status_code == 200
