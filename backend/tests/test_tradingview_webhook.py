"""Tests for TradingView webhook: schema, secret validation, council routing, execution handoff."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.schemas.tradingview import TradingViewWebhookPayload, TradingViewAlertMeta


def _stub_decision_packet(symbol="AAPL", final_direction="buy", execution_ready=True):
    from app.council.schemas import DecisionPacket, CognitiveMeta
    return DecisionPacket(
        symbol=symbol,
        timeframe="1d",
        timestamp="2026-03-12T20:55:00Z",
        votes=[],
        final_direction=final_direction,
        final_confidence=0.7,
        vetoed=False,
        veto_reasons=[],
        risk_limits={},
        execution_ready=execution_ready,
        council_reasoning="stub",
        council_decision_id="test-id",
        cognitive=CognitiveMeta(),
    )


# ─── Schema validation ─────────────────────────────────────────────────────

def test_tradingview_payload_resolved_symbol():
    """Schema resolves symbol from symbol or ticker."""
    p = TradingViewWebhookPayload(symbol="AAPL")
    assert p.resolved_symbol() == "AAPL"
    p = TradingViewWebhookPayload(ticker="MSFT")
    assert p.resolved_symbol() == "MSFT"
    p = TradingViewWebhookPayload(symbol="  tsla  ")
    assert p.resolved_symbol() == "TSLA"
    p = TradingViewWebhookPayload()
    assert p.resolved_symbol() == ""


def test_tradingview_payload_resolved_action():
    """Schema normalizes action to buy/sell/hold."""
    assert TradingViewWebhookPayload(action="BUY").resolved_action() == "buy"
    assert TradingViewWebhookPayload(action="LONG").resolved_action() == "buy"
    assert TradingViewWebhookPayload(action="SELL").resolved_action() == "sell"
    assert TradingViewWebhookPayload(action="SHORT").resolved_action() == "sell"
    assert TradingViewWebhookPayload(side="buy").resolved_action() == "buy"
    assert TradingViewWebhookPayload(action="").resolved_action() == "hold"


def test_tradingview_payload_resolved_price():
    """Schema resolves price from price or close."""
    assert TradingViewWebhookPayload(price=100.5).resolved_price() == 100.5
    assert TradingViewWebhookPayload(close=99.0).resolved_price() == 99.0
    assert TradingViewWebhookPayload().resolved_price() == 0.0


def test_tradingview_payload_resolved_mode():
    """Schema resolves mode to council or direct_execution."""
    assert TradingViewWebhookPayload(mode="council").resolved_mode() == "council"
    assert TradingViewWebhookPayload(mode="direct_execution").resolved_mode() == "direct_execution"
    assert TradingViewWebhookPayload(mode="invalid").resolved_mode() == "council"
    assert TradingViewWebhookPayload().resolved_mode() == "council"


def test_tradingview_payload_meta_optional():
    """Payload accepts optional meta dict."""
    p = TradingViewWebhookPayload(symbol="AAPL", meta=TradingViewAlertMeta(exchange="NASDAQ"))
    assert p.meta is not None
    assert p.meta.exchange == "NASDAQ"


# ─── Webhook endpoint (integration) ─────────────────────────────────────────

@pytest.fixture
def valid_tradingview_body():
    return {
        "symbol": "AAPL",
        "action": "BUY",
        "timeframe": "5m",
        "price": 212.34,
        "strategy": "EMA Cross",
        "timestamp": "2026-03-12T20:55:00Z",
        "order_type": "market",
        "qty": 1,
        "mode": "council",
        "meta": {"exchange": "NASDAQ", "alert_name": "TV Momentum Long"},
    }


@pytest.mark.asyncio
async def test_tradingview_webhook_success_council_mode(client, valid_tradingview_body, monkeypatch):
    """POST /webhooks/tradingview with valid payload returns 200 and routes through council."""
    publish_called = []

    async def _stub_run_council(symbol, timeframe="1d", features=None, context=None):
        return _stub_decision_packet(symbol=symbol, final_direction="buy", execution_ready=True)

    monkeypatch.setattr("app.council.runner.run_council", _stub_run_council)

    async def _capture_publish(topic, data):
        publish_called.append((topic, data))

    with patch("app.core.message_bus.get_message_bus") as mbus:
        bus = MagicMock()
        bus.publish = AsyncMock(side_effect=_capture_publish)
        mbus.return_value = bus
        with patch("app.websocket_manager.broadcast_ws", new_callable=AsyncMock):
            r = await client.post("/api/v1/webhooks/tradingview", json=valid_tradingview_body)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["symbol"] == "AAPL"
    assert data["action"] == "buy"
    assert data["mode"] == "council"
    assert data["final_direction"] == "buy"
    assert data["execution_ready"] is True
    assert any(t == "council.verdict" for t, _ in publish_called)


@pytest.mark.asyncio
async def test_tradingview_webhook_invalid_secret_returns_401(client, valid_tradingview_body, monkeypatch):
    """When TRADINGVIEW_WEBHOOK_SECRET is set, wrong secret returns 401."""
    monkeypatch.setattr("app.core.config.settings.TRADINGVIEW_WEBHOOK_SECRET", "expected_secret")
    body = {**valid_tradingview_body, "secret": "wrong_secret"}
    r = await client.post("/api/v1/webhooks/tradingview", json=body)
    assert r.status_code == 401
    assert "secret" in r.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_tradingview_webhook_valid_secret_accepts(client, valid_tradingview_body, monkeypatch):
    """When TRADINGVIEW_WEBHOOK_SECRET is set, matching secret is accepted."""
    monkeypatch.setattr("app.core.config.settings.TRADINGVIEW_WEBHOOK_SECRET", "my_webhook_secret")
    body = {**valid_tradingview_body, "secret": "my_webhook_secret"}
    async def _stub_run_council(*args, **kwargs):
        return _stub_decision_packet(
            symbol=kwargs.get("symbol", "AAPL"),
            final_direction="hold",
            execution_ready=False,
        )
    monkeypatch.setattr("app.council.runner.run_council", _stub_run_council)
    with patch("app.core.message_bus.get_message_bus"):
        with patch("app.websocket_manager.broadcast_ws", new_callable=AsyncMock):
            r = await client.post("/api/v1/webhooks/tradingview", json=body)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_tradingview_webhook_missing_symbol_returns_422(client):
    """Payload without symbol or ticker returns 422."""
    r = await client.post("/api/v1/webhooks/tradingview", json={"action": "BUY", "price": 100})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_tradingview_webhook_invalid_json_returns_422(client):
    """Invalid JSON body returns 422."""
    r = await client.post(
        "/api/v1/webhooks/tradingview",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_tradingview_webhook_direct_execution_paper_only(client, valid_tradingview_body, monkeypatch):
    """direct_execution mode submits via Alpaca only when TRADING_MODE=paper."""
    monkeypatch.setattr("app.core.config.settings.TRADING_MODE", "paper")
    body = {**valid_tradingview_body, "mode": "direct_execution", "action": "BUY"}
    created = {"id": "order-123", "symbol": "AAPL", "side": "buy", "qty": "1"}
    with patch("app.services.alpaca_service.alpaca_service") as mock_svc:
        mock_svc.create_order = AsyncMock(return_value=created)
        r = await client.post("/api/v1/webhooks/tradingview", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "direct_execution"
    assert data.get("order_id") == "order-123"


@pytest.mark.asyncio
async def test_tradingview_webhook_direct_execution_rejected_when_not_paper(client, valid_tradingview_body, monkeypatch):
    """direct_execution is rejected with 403 when TRADING_MODE is not paper."""
    monkeypatch.setattr("app.core.config.settings.TRADING_MODE", "live")
    body = {**valid_tradingview_body, "mode": "direct_execution", "action": "BUY"}
    r = await client.post("/api/v1/webhooks/tradingview", json=body)
    assert r.status_code == 403
    assert "direct_execution" in r.json().get("detail", "")


@pytest.mark.asyncio
async def test_tradingview_webhook_backward_compat_minimal_payload(client, monkeypatch):
    """Minimal payload (ticker, action, price only) is accepted and routed to council."""
    async def _stub_run_council(symbol, timeframe="1d", features=None, context=None):
        return _stub_decision_packet(symbol=symbol, final_direction="buy", execution_ready=True)
    monkeypatch.setattr("app.council.runner.run_council", _stub_run_council)
    with patch("app.core.message_bus.get_message_bus"):
        with patch("app.websocket_manager.broadcast_ws", new_callable=AsyncMock):
            r = await client.post(
                "/api/v1/webhooks/tradingview",
                json={"ticker": "MSFT", "action": "buy", "price": 350.0},
            )
    assert r.status_code == 200
    assert r.json()["symbol"] == "MSFT"
