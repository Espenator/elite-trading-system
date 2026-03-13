"""Briefing API — morning briefing, position review, weekly review, TradingView, webhook.

GET  /api/v1/briefing/morning    — full morning briefing (optional ?notify=true & ?webhook=true)
GET  /api/v1/briefing/positions  — position review with attention flags
GET  /api/v1/briefing/weekly     — weekly review (start_date, end_date)
POST /api/v1/briefing/webhook/test — send test payload to TRADINGVIEW_WEBHOOK_URL
GET  /api/v1/briefing/status     — briefing config (webhook, Slack, last briefing, regime)
GET  /api/v1/briefing/tradingview — trade ideas for TradingView overlay
GET  /api/v1/briefing/watchlist-export — Pine paste + watchlist
POST /api/v1/briefing/push-webhook — push signals to webhook
"""

import logging
from datetime import date, timedelta
from typing import Any, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.security import require_auth
from app.services.briefing_service import generate_morning_briefing, get_briefing_service
from app.services.tradingview_bridge import get_tradingview_bridge

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Response models ────────────────────────────────────────────────────────
class WatchlistExportResponse(BaseModel):
    pine_paste: str
    watchlist_symbols: List[str]
    watchlist_text: str
    total: int


# ─── GET /morning ────────────────────────────────────────────────────────────
@router.get("/morning", dependencies=[Depends(require_auth)])
async def get_morning_briefing(
    regime: str = "GREEN",
    top_n: int = 5,
    notify: bool = Query(False, description="Send briefing to Slack"),
    webhook: bool = Query(False, description="Push trade ideas to TradingView webhook"),
):
    """Generate full morning briefing. Optionally notify Slack (?notify=true) and push webhook (?webhook=true)."""
    svc = get_briefing_service()
    result = await svc.generate_morning_briefing(
        as_of=date.today(),
        top_n=top_n,
        notify_slack=notify,
        push_webhook=webhook,
    )
    return result


# ─── GET /positions ──────────────────────────────────────────────────────────
@router.get("/positions", dependencies=[Depends(require_auth)])
async def get_briefing_positions():
    """Return enriched position list with R-multiple, days held, attention flags."""
    svc = get_briefing_service()
    return await svc.get_position_review()


# ─── GET /weekly ────────────────────────────────────────────────────────────
@router.get("/weekly", dependencies=[Depends(require_auth)])
async def get_briefing_weekly(
    start_date: date = Query(None, description="Start date (default: 7 days ago)"),
    end_date: date = Query(None, description="End date (default: today)"),
):
    """Weekly review: P&L, win rate, best/worst trades, agent Brier, regime summary."""
    svc = get_briefing_service()
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=7))
    return await svc.generate_weekly_review(start_date=start, end_date=end)


# ─── POST /webhook/test ──────────────────────────────────────────────────────
@router.post("/webhook/test", dependencies=[Depends(require_auth)])
async def post_briefing_webhook_test():
    """Send a test payload to TRADINGVIEW_WEBHOOK_URL. Returns delivery status."""
    bridge = get_tradingview_bridge()
    test_idea = {
        "symbol": "TEST",
        "direction": "buy",
        "entry_zone": [100.0, 100.2],
        "stop_loss": 98.0,
        "target_1": 104.0,
        "target_2": 106.0,
        "score": 70,
        "confidence": 0.75,
    }
    if hasattr(bridge, "push_signals"):
        result = await bridge.push_signals([test_idea])
    else:
        result = await bridge.push_signals_to_webhook([test_idea])
        result = {"sent": result.get("pushed_count", 0) > 0, "results": [], "timestamp": result.get("timestamp")}
    return result


# ─── GET /status ────────────────────────────────────────────────────────────
@router.get("/status", dependencies=[Depends(require_auth)])
async def get_briefing_status():
    """Briefing service config: webhook configured?, Slack configured?, last briefing, regime."""
    svc = get_briefing_service()
    bridge = get_tradingview_bridge()
    slack_ok = False
    try:
        from app.services.slack_notification_service import get_slack_service
        slack_ok = get_slack_service()._is_configured()
    except Exception:
        pass
    regime_state = "unknown"
    try:
        from app.council.regime.bayesian_regime import get_bayesian_regime
        regime_state = get_bayesian_regime().to_dict().get("dominant_regime", "unknown")
    except Exception:
        pass
    return {
        "webhook_configured": bridge.is_configured(),
        "slack_configured": slack_ok,
        "last_briefing_time": getattr(svc, "_last_briefing_time", None),
        "regime_state": regime_state,
    }


# ─── GET /tradingview ────────────────────────────────────────────────────────
@router.get("/tradingview")
async def get_briefing_tradingview(regime: str = "GREEN", top_n: int = 5):
    """Return trade ideas formatted for TradingView (same as morning, keyed for overlay)."""
    result = await generate_morning_briefing(as_of=date.today(), top_n=top_n, regime=regime)
    return {"as_of": result.get("as_of"), "regime": result.get("regime"), "ideas": result.get("ideas", [])}


# ─── GET /watchlist-export ───────────────────────────────────────────────────
def _ideas_to_pine_paste(ideas: List[dict]) -> str:
    """Format ideas as Symbol:action:entry:stop:t1:t2:score[, ...] for Pine Script paste."""
    parts = []
    for idea in ideas:
        ticker = (idea.get("ticker") or idea.get("symbol") or "").upper()
        action = (idea.get("action") or "buy").lower()
        entry = idea.get("entry") or idea.get("price") or 0
        stop = idea.get("stop") or 0
        t1 = idea.get("target1") or 0
        t2 = idea.get("target2") or 0
        score = idea.get("confidence") or idea.get("score") or 0
        regime = idea.get("regime") or ""
        parts.append(f"{ticker}:{action}:{entry}:{stop}:{t1}:{t2}:{score}:{regime}")
    return ",".join(parts)


@router.get("/watchlist-export", response_model=WatchlistExportResponse)
async def get_watchlist_export(regime: str = "GREEN", top_n: int = 10):
    """Return today's trade ideas in Pine Script paste format and watchlist import format."""
    result = await generate_morning_briefing(as_of=date.today(), top_n=top_n, regime=regime)
    ideas = result.get("ideas", [])
    pine_paste = _ideas_to_pine_paste(ideas)
    symbols = list({(idea.get("ticker") or idea.get("symbol") or "").upper() for idea in ideas if (idea.get("ticker") or idea.get("symbol"))})
    watchlist_text = "\n".join(symbols)
    return WatchlistExportResponse(
        pine_paste=pine_paste,
        watchlist_symbols=symbols,
        watchlist_text=watchlist_text,
        total=len(symbols),
    )


# ─── POST /push-webhook ─────────────────────────────────────────────────────
@router.post("/push-webhook", dependencies=[Depends(require_auth)])
async def post_push_webhook(regime: str = "GREEN", top_n: int = 5):
    """Push current top trade ideas to TRADINGVIEW_WEBHOOK_URL."""
    result = await generate_morning_briefing(as_of=date.today(), top_n=top_n, regime=regime)
    ideas = result.get("ideas", [])
    bridge = get_tradingview_bridge()
    push_result = await bridge.push_signals_to_webhook(ideas)
    return {"briefing": result, "push": push_result}


# Optional: POST body to push custom payload (for webhook testing)
class PushWebhookBody(BaseModel):
    ideas: List[dict]


@router.post("/push-webhook/body", dependencies=[Depends(require_auth)])
async def post_push_webhook_body(body: PushWebhookBody):
    """Push provided ideas to TRADINGVIEW_WEBHOOK_URL (for testing)."""
    bridge = get_tradingview_bridge()
    push_result = await bridge.push_signals_to_webhook(body.ideas)
    return push_result
