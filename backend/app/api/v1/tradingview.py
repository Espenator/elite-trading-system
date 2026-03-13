"""TradingView API — push signals, config, Pine Script indicator.

POST /api/v1/tradingview/push-signals — push trade ideas to webhook (auth required)
GET  /api/v1/tradingview/config      — webhook configured, last push, stats (auth required)
GET  /api/v1/tradingview/pine-script  — Embodier Signal Overlay Pine Script (public, text/plain)
"""

import logging
from typing import Any, List

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import PlainTextResponse

from app.core.security import require_auth
from app.services.tradingview_bridge import get_tradingview_bridge

logger = logging.getLogger(__name__)
router = APIRouter()

PINE_SCRIPT = r'''//@version=5
indicator("Embodier Signals", overlay=true, max_labels_count=10)

// === INPUTS ===
direction  = input.string("none", "Direction", options=["long", "short", "none"], group="Signal")
entryPrice = input.float(0.0, "Entry Price", group="Signal")
stopLoss   = input.float(0.0, "Stop Loss", group="Signal")
target1    = input.float(0.0, "Target 1 (2R)", group="Signal")
target2    = input.float(0.0, "Target 2 (3R)", group="Signal")
showLabels = input.bool(true, "Show Labels", group="Display")

// === COLORS ===
entryColor = color.new(color.blue, 20)
stopColor  = color.new(color.red, 20)
t1Color    = color.new(color.green, 20)
t2Color    = color.new(color.lime, 30)

// === PLOT LEVELS ===
isActive = direction != "none" and entryPrice > 0

plot(isActive ? entryPrice : na, "Entry", color=entryColor, linewidth=2, style=plot.style_linebr)
plot(isActive ? stopLoss : na, "Stop", color=stopColor, linewidth=2, style=plot.style_linebr)
plot(isActive ? target1 : na, "T1 (2R)", color=t1Color, linewidth=1, style=plot.style_linebr)
plot(isActive ? target2 : na, "T2 (3R)", color=t2Color, linewidth=1, style=plot.style_linebr)

// === FILL ZONES ===
entryLine = plot(isActive ? entryPrice : na, display=display.none)
stopLine  = plot(isActive ? stopLoss : na, display=display.none)
t1Line    = plot(isActive ? target1 : na, display=display.none)

fill(entryLine, stopLine, color=color.new(color.red, 90), title="Risk Zone")
fill(entryLine, t1Line, color=color.new(color.green, 90), title="Reward Zone")

// === LABELS ===
if isActive and showLabels and barstate.islast
    riskPerShare = math.abs(entryPrice - stopLoss)
    rewardRatio = riskPerShare > 0 ? math.abs(target1 - entryPrice) / riskPerShare : 0

    label.new(bar_index + 2, entryPrice, "ENTRY " + str.tostring(entryPrice, "#.##"),
              color=entryColor, textcolor=color.white, size=size.small)
    label.new(bar_index + 2, stopLoss, "STOP " + str.tostring(stopLoss, "#.##"),
              color=stopColor, textcolor=color.white, size=size.small)
    label.new(bar_index + 2, target1, "T1 " + str.tostring(target1, "#.##") + " (" + str.tostring(rewardRatio, "#.#") + "R)",
              color=t1Color, textcolor=color.white, size=size.small)
    label.new(bar_index + 2, target2, "T2 " + str.tostring(target2, "#.##"),
              color=t2Color, textcolor=color.white, size=size.small)

// === ALERTS ===
longEntryZone  = direction == "long" and close <= entryPrice * 1.003 and close >= entryPrice * 0.997
shortEntryZone = direction == "short" and close >= entryPrice * 0.997 and close <= entryPrice * 1.003
stopHit        = (direction == "long" and low <= stopLoss) or (direction == "short" and high >= stopLoss)
t1Hit          = (direction == "long" and high >= target1) or (direction == "short" and low <= target1)

alertcondition(longEntryZone, "Long Entry Zone", "EMBODIER: Price in LONG entry zone for {{ticker}}")
alertcondition(shortEntryZone, "Short Entry Zone", "EMBODIER: Price in SHORT entry zone for {{ticker}}")
alertcondition(stopHit, "Stop Loss Hit", "EMBODIER: STOP HIT on {{ticker}}")
alertcondition(t1Hit, "Target 1 Hit", "EMBODIER: TARGET 1 HIT on {{ticker}} — consider trailing stop")
'''


@router.post("/push-signals", dependencies=[Depends(require_auth)])
async def post_tradingview_push_signals(
    signals: List[dict] = Body(default=None),
    execute: bool = Query(False, description="If true, also send to TradersPost for real Alpaca execution"),
):
    """Push trade ideas to webhooks. execute=false: monitoring only (webhook.site). execute=true: also TradersPost."""
    bridge = get_tradingview_bridge()
    if not signals:
        from app.services.briefing_service import get_briefing_service
        svc = get_briefing_service()
        briefing = await svc.generate_morning_briefing(top_n=5)
        signals = briefing.get("trade_ideas", [])
    result = await bridge.push_signals(signals, execute=execute)
    # Normalize for backward compatibility
    if "results" not in result and "monitor_results" in result:
        result = {**result, "results": result.get("monitor_results", [])}
    return result


@router.get("/config", dependencies=[Depends(require_auth)])
async def get_tradingview_config():
    """Return webhook_url configured (bool), last push timestamp, delivery stats."""
    bridge = get_tradingview_bridge()
    return {
        "webhook_configured": bridge.is_configured(),
        "last_push_timestamp": getattr(bridge, "_last_push_time", None),
        "monitor_url_configured": bool(getattr(bridge, "webhook_url", "") or getattr(bridge, "_url", "")),
        "traderspost_configured": bool(getattr(bridge, "traderspost_url", "")),
    }


@router.get("/pine-script", response_class=PlainTextResponse)
async def get_tradingview_pine_script():
    """Return Embodier Signal Overlay Pine Script as text/plain (no auth)."""
    return PlainTextResponse(content=PINE_SCRIPT, media_type="text/plain")
