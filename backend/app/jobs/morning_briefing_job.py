"""Morning briefing scheduled job — 9 AM ET weekdays.

Calls BriefingService.generate_morning_briefing() then TradingViewBridge.push_signals_to_webhook().
Logs result and sends Slack confirmation to #trade-alerts.
"""

import asyncio
import logging
from datetime import date

from app.services.briefing_service import generate_morning_briefing
from app.services.tradingview_bridge import get_tradingview_bridge

log = logging.getLogger(__name__)


def run_morning_briefing() -> dict:
    """Run morning briefing (sync wrapper for APScheduler): generate ideas and push to webhook.

    Returns dict with status, ideas_count, push_result, error (if any).
    """
    try:
        result = asyncio.run(_run_async())
        return result
    except Exception as e:
        log.exception("Morning briefing job failed: %s", e)
        return {"status": "error", "error": str(e), "ideas_count": 0, "push_result": {}}


async def _run_async() -> dict:
    """Generate briefing and push to TradingView webhook; send Slack confirmation."""
    briefing_result = await generate_morning_briefing(as_of=date.today(), top_n=5, regime="GREEN")
    ideas = briefing_result.get("ideas", [])
    ideas_count = len(ideas)

    push_result = {}
    bridge = get_tradingview_bridge()
    if bridge.is_configured() and ideas:
        push_result = await bridge.push_signals_to_webhook(ideas)
        log.info(
            "Morning briefing: %d ideas, webhook pushed %d, failed %d",
            ideas_count,
            push_result.get("pushed_count", 0),
            push_result.get("failed_count", 0),
        )
    else:
        log.info("Morning briefing: %d ideas (webhook not configured or no ideas)", ideas_count)

    # Slack confirmation
    try:
        from app.services.slack_notification_service import slack_service
        summary = f"Morning briefing: {ideas_count} ideas"
        if ideas:
            symbols = ", ".join((i.get("ticker") or i.get("symbol") or "?") for i in ideas[:5])
            summary += f" — {symbols}"
        if push_result:
            summary += f" | Pushed to TradingView: {push_result.get('pushed_count', 0)}"
        await slack_service.send_alert(summary, level="INFO")
    except Exception as e:
        log.warning("Slack confirmation failed: %s", e)

    return {
        "status": "ok",
        "ideas_count": ideas_count,
        "briefing": briefing_result,
        "push_result": push_result,
    }
