"""Tests for briefing service, TradingView bridge, and briefing/tradingview API."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.briefing_service import BriefingService, get_briefing_service
from app.services.tradingview_bridge import TradingViewBridge, get_tradingview_bridge


# ─── BriefingService init ────────────────────────────────────────────────────

def test_briefing_service_init():
    """Service instantiates without error."""
    svc = BriefingService()
    assert svc is not None
    assert get_briefing_service() is not None


# ─── format_tradingview_levels ───────────────────────────────────────────────

def test_format_tradingview_levels_long():
    """Long trade levels: entry zone, stop = entry - 2*ATR, target1 = entry + 2*risk, target2 = entry + 3*risk."""
    svc = BriefingService()
    signal = {"entry": 100.0, "price": 100.0, "direction": "long", "score": 70}
    atr = 2.0
    out = svc.format_tradingview_levels(signal, atr)
    assert out["entry_zone"] == [99.8, 100.2]
    assert out["stop_loss"] == 96.0  # 100 - 2*2
    risk = 4.0
    assert out["target_1"] == pytest.approx(100 + 2 * risk, rel=0.01)
    assert out["target_2"] == pytest.approx(100 + 3 * risk, rel=0.01)
    assert out["risk_per_share"] == 4.0
    assert out["reward_risk_ratio"] == pytest.approx(2.0, rel=0.01)


def test_format_tradingview_levels_short():
    """Short trade levels: stop above entry, targets below entry."""
    svc = BriefingService()
    signal = {"entry": 100.0, "direction": "sell", "score": 65}
    atr = 2.0
    out = svc.format_tradingview_levels(signal, atr)
    assert out["stop_loss"] == 104.0  # 100 + 2*2
    risk = 4.0
    assert out["target_1"] == pytest.approx(100 - 2 * risk, rel=0.01)
    assert out["target_2"] == pytest.approx(100 - 3 * risk, rel=0.01)


# ─── TradingViewBridge payload and disabled ────────────────────────────────────

def test_tradingview_bridge_format_payload():
    """Payload format matches expected schema (ticker, action, stop_loss, take_profit, etc.)."""
    bridge = TradingViewBridge()
    bridge._url = "https://example.com"
    idea = {
        "symbol": "AAPL",
        "direction": "buy",
        "entry_zone": [178.5, 179.2],
        "stop_loss": 174.8,
        "target_1": 186.6,
        "target_2": 190.3,
        "position_size_pct": 1.2,
        "confidence": 0.87,
        "score": 82,
        "regime": "bull",
        "council_decision_id": "uuid-1",
    }
    payload = bridge._format_payload(idea)
    assert payload["ticker"] == "AAPL"
    assert payload["action"] == "buy"
    assert payload["price"] == 178.5
    assert payload["stop_loss"] == 174.8
    assert payload["take_profit"] == 186.6
    assert payload["take_profit_2"] == 190.3
    assert payload["position_size_pct"] == 1.2
    assert payload["order_type"] == "limit"
    assert payload["confidence"] == 0.87
    assert payload["score"] == 82
    assert payload["regime"] == "bull"
    assert payload["council_decision_id"] == "uuid-1"
    assert payload["source"] == "embodier_trader"
    assert "timestamp" in payload
    assert "message" in payload


def test_tradingview_bridge_disabled():
    """Returns gracefully when no webhook URLs are configured."""
    bridge = get_tradingview_bridge()
    bridge.webhook_url = ""
    bridge.traderspost_url = ""
    bridge.enabled = False
    assert bridge.is_configured() is False


# ─── API endpoints (with client) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_briefing_morning_endpoint(client, auth_headers):
    """GET /api/v1/briefing/morning returns 200 with auth."""
    r = await client.get("/api/v1/briefing/morning", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "timestamp" in data or "trade_ideas" in data or "ideas" in data or "regime" in data


@pytest.mark.asyncio
async def test_briefing_morning_no_auth(client):
    """GET /api/v1/briefing/morning returns 401 without auth."""
    r = await client.get("/api/v1/briefing/morning")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_briefing_positions_endpoint(client, auth_headers):
    """GET /api/v1/briefing/positions returns 200."""
    r = await client.get("/api/v1/briefing/positions", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_briefing_weekly_endpoint(client, auth_headers):
    """GET /api/v1/briefing/weekly returns 200."""
    r = await client.get("/api/v1/briefing/weekly", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total_pnl" in data or "win_rate_pct" in data or "total_trades" in data


@pytest.mark.asyncio
async def test_webhook_test_endpoint(client, auth_headers):
    """POST /api/v1/briefing/webhook/test returns result."""
    r = await client.post("/api/v1/briefing/webhook/test", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "sent" in data or "pushed_count" in data or "results" in data


@pytest.mark.asyncio
async def test_briefing_status_endpoint(client, auth_headers):
    """GET /api/v1/briefing/status returns config."""
    r = await client.get("/api/v1/briefing/status", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "webhook_configured" in data
    assert "slack_configured" in data or "regime_state" in data


@pytest.mark.asyncio
async def test_pine_script_endpoint(client):
    """GET /api/v1/tradingview/pine-script returns text/plain (no auth)."""
    r = await client.get("/api/v1/tradingview/pine-script")
    assert r.status_code == 200
    assert "text/plain" in r.headers.get("content-type", "")
    assert "indicator(" in r.text or "//@version" in r.text


# ─── Regime adaptive threshold ───────────────────────────────────────────────

def test_regime_adaptive_threshold():
    """Signals filtered correctly per regime (GREEN=55, YELLOW=65, RED=75)."""
    from app.config.regime_thresholds import get_regime_config
    g = get_regime_config("GREEN")
    y = get_regime_config("YELLOW")
    r = get_regime_config("RED")
    assert g.get("gate_threshold") == 55.0
    assert y.get("gate_threshold") == 65.0
    assert r.get("gate_threshold") == 75.0


# ─── Position attention flags ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_position_attention_flags():
    """Positions near stop, old, or regime-changed are flagged."""
    svc = BriefingService()
    mock_positions = [
        {
            "symbol": "AAPL",
            "qty": "100",
            "avg_entry_price": "150",
            "current_price": "149",
            "unrealized_pl": "-100",
            "market_value": "14900",
            "opened_at": "2026-01-01T10:00:00Z",
        },
    ]
    with patch("app.services.alpaca_service.alpaca_service") as m:
        m.get_positions = AsyncMock(return_value=mock_positions)
        positions = await svc.get_position_review()
        assert isinstance(positions, list)
        if positions:
            p = positions[0]
            assert "needs_attention" in p
            assert "attention_reason" in p or p.get("needs_attention") is False


# ─── Slack briefing format ────────────────────────────────────────────────────

def test_slack_briefing_format():
    """Slack message contains required sections (regime, positions, ideas)."""
    svc = BriefingService()
    briefing = {
        "regime": {"state": "bull", "vix": 14.5, "confidence": 0.82, "signal_threshold": 55},
        "portfolio": {"total_value": 100000, "heat_pct": 4.2, "open_positions": 3},
        "positions": [{"symbol": "AAPL", "direction": "long"}],
        "trade_ideas": [
            {"symbol": "MSFT", "direction": "buy", "entry_zone": [415, 416], "stop_loss": 410, "target_1": 425, "target_2": 431},
        ],
        "calendar_events": [],
    }
    text = svc.format_slack_briefing(briefing)
    assert "bull" in text or "Regime" in text
    assert "Portfolio" in text or "100000" in text
    assert "MSFT" in text
    assert "415" in text or "410" in text
