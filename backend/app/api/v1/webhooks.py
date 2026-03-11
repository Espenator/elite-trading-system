"""Webhook receiver endpoints for TradingView alerts and external signals.

POST /api/v1/webhooks/tradingview — receives TradingView alert JSON
POST /api/v1/webhooks/signal — receives generic external signal

TradingView alerts send JSON like:
  {"ticker": "AAPL", "action": "buy", "price": 150.50, "message": "..."}

These get published to the MessageBus as 'signal.external' events
and forwarded to Slack via the notification service.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class TradingViewAlert(BaseModel):
    ticker: Optional[str] = None
    symbol: Optional[str] = None
    action: Optional[str] = None
    side: Optional[str] = None
    price: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    message: Optional[str] = None
    exchange: Optional[str] = None
    timeframe: Optional[str] = None


class ExternalSignal(BaseModel):
    symbol: str
    direction: str = "LONG"
    score: int = 50
    source: str = "external"
    message: Optional[str] = None


@router.post("/tradingview")
async def receive_tradingview_alert(alert: TradingViewAlert):
    """Receive a TradingView alert webhook and publish to MessageBus."""
    symbol = (alert.ticker or alert.symbol or "").upper()
    action = (alert.action or alert.side or "").upper()
    price = alert.price or alert.close or 0

    logger.info("TradingView alert: %s %s @ %.2f", action, symbol, price)

    # Publish to MessageBus
    try:
        from app.services.message_bus import get_message_bus
        bus = get_message_bus()
        await bus.publish("signal.external", {
            "source": "tradingview",
            "symbol": symbol,
            "action": action,
            "price": price,
            "message": alert.message or "",
        })
    except Exception as e:
        logger.debug("MessageBus publish failed: %s", e)

    # Forward to Slack
    try:
        from app.services.slack_notification_service import slack_service
        direction = "LONG" if action in ("BUY", "LONG") else "SHORT"
        await slack_service.send_signal(
            symbol=symbol,
            direction=direction,
            score=0,
            channel="#tradingview-alerts",
        )
    except Exception as e:
        logger.debug("Slack forward failed: %s", e)

    return {"ok": True, "symbol": symbol, "action": action, "price": price}


@router.post("/signal")
async def receive_external_signal(signal: ExternalSignal):
    """Receive a generic external signal and publish to MessageBus."""
    logger.info("External signal: %s %s (score=%d)", signal.direction, signal.symbol, signal.score)

    try:
        from app.services.message_bus import get_message_bus
        bus = get_message_bus()
        await bus.publish("signal.external", {
            "source": signal.source,
            "symbol": signal.symbol.upper(),
            "direction": signal.direction,
            "score": signal.score,
            "message": signal.message or "",
        })
    except Exception as e:
        logger.debug("MessageBus publish failed: %s", e)

    return {"ok": True, "symbol": signal.symbol.upper(), "direction": signal.direction}
