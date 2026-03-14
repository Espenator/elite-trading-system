"""Webhook receiver endpoints for TradingView alerts and external signals.

POST /api/v1/webhooks/tradingview — receives TradingView alert JSON, validates secret,
  routes to council (default) or direct_execution (testing), broadcasts via WebSocket.
POST /api/v1/webhooks/signal — receives generic external signal (MessageBus + Slack).

TradingView payload shape (see schemas.tradingview.TradingViewWebhookPayload):
  secret, symbol, action, timeframe, price, strategy, timestamp, order_type, qty, mode, meta.
"""

import logging
import secrets
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.security import require_auth
from app.schemas.tradingview import TradingViewWebhookPayload

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_tradingview_secret(payload_secret: Optional[str], configured_secret: str) -> None:
    """Validate webhook secret; raise HTTPException 401 if configured and mismatch."""
    if not configured_secret or not configured_secret.strip():
        logger.debug("TradingView webhook: no TRADINGVIEW_WEBHOOK_SECRET set, skipping validation")
        return
    if not payload_secret or not str(payload_secret).strip():
        raise HTTPException(status_code=401, detail="Missing webhook secret")
    if not secrets.compare_digest(str(payload_secret).strip(), configured_secret.strip()):
        logger.warning("TradingView webhook: secret mismatch (rejecting)")
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


def _build_signal_data(payload: TradingViewWebhookPayload) -> Dict[str, Any]:
    """Convert webhook payload to internal signal format for council/OrderExecutor."""
    symbol = payload.resolved_symbol()
    direction = payload.resolved_action()
    price = payload.resolved_price()
    timeframe = payload.resolved_timeframe()
    # Use a score that passes typical gate (e.g. 65); council still decides
    score = 70.0
    return {
        "symbol": symbol,
        "direction": direction,
        "score": score,
        "price": price,
        "close": price,
        "regime": "UNKNOWN",
        "source": "tradingview",
        "timestamp": payload.timestamp or "",
        "label": payload.strategy or "TradingView",
        "volume": payload.volume or 0,
        "timeframe": timeframe,
        "strategy": payload.strategy,
        "order_type": payload.order_type or "market",
        "qty": payload.qty,
        "meta": (payload.meta.model_dump() if hasattr(payload.meta, "model_dump") else dict(payload.meta)) if payload.meta else {},
    }


@router.post("/tradingview")
async def receive_tradingview_alert(request: Request):
    """Receive TradingView alert webhook: validate secret, route to council or direct execution."""
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("TradingView webhook: invalid JSON body: %s", e)
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    try:
        payload = TradingViewWebhookPayload.model_validate(body)
    except Exception as e:
        logger.warning("TradingView webhook: schema validation failed: %s", e)
        raise HTTPException(status_code=422, detail="Invalid payload schema")

    symbol = payload.resolved_symbol()
    if not symbol:
        raise HTTPException(status_code=422, detail="Missing symbol or ticker")

    # Secret validation (from config only)
    from app.core.config import settings
    configured_secret = getattr(settings, "TRADINGVIEW_WEBHOOK_SECRET", "") or ""
    _validate_tradingview_secret(payload.secret, configured_secret)

    direction = payload.resolved_action()
    price = payload.resolved_price()
    mode = payload.resolved_mode()
    signal_data = _build_signal_data(payload)

    logger.info(
        "TradingView alert: %s %s @ %.2f (mode=%s)",
        direction, symbol, price, mode,
    )

    # Broadcast received signal to WebSocket clients
    try:
        from app.websocket_manager import broadcast_ws
        await broadcast_ws("signal", {
            "type": "tradingview_received",
            "symbol": symbol,
            "direction": direction,
            "price": price,
            "timeframe": payload.resolved_timeframe(),
            "strategy": payload.strategy or "",
            "timestamp": payload.timestamp,
            "mode": mode,
        })
    except Exception as e:
        logger.debug("WebSocket broadcast (signal) failed: %s", e)

    if mode == "direct_execution":
        # Testing only: bypass council, submit via Alpaca service (paper-only when enforced)
        from app.core.config import settings as s
        if getattr(s, "TRADING_MODE", "paper").lower() != "paper":
            logger.warning("TradingView direct_execution rejected: TRADING_MODE is not paper")
            raise HTTPException(
                status_code=403,
                detail="direct_execution allowed only when TRADING_MODE=paper",
            )
        qty = payload.qty or 1
        if direction == "hold":
            return {"ok": True, "symbol": symbol, "action": direction, "skipped": "hold"}
        try:
            from app.services.alpaca_service import alpaca_service
            order_type = (payload.order_type or "market").strip().lower()
            result = await alpaca_service.create_order(
                symbol=symbol,
                qty=str(qty),
                side=direction,
                type=order_type if order_type in ("market", "limit") else "market",
            )
            if result:
                try:
                    from app.websocket_manager import broadcast_ws
                    await broadcast_ws("order", {
                        "type": "order_update",
                        "order": {"id": result.get("id"), "symbol": symbol, "side": direction, "qty": qty},
                    })
                except Exception:
                    pass
            return {
                "ok": True,
                "symbol": symbol,
                "action": direction,
                "price": price,
                "mode": "direct_execution",
                "order_id": result.get("id") if result else None,
            }
        except Exception as e:
            logger.exception("TradingView direct_execution failed: %s", e)
            raise HTTPException(status_code=500, detail="Order submission failed")

    # Default: route through council
    try:
        from app.council.runner import run_council
        from app.core.message_bus import get_message_bus
        from app.websocket_manager import broadcast_ws
    except ImportError as e:
        logger.exception("TradingView council flow import failed: %s", e)
        raise HTTPException(status_code=503, detail="Council unavailable")

    context = {
        "signal_score": signal_data["score"],
        "signal_label": signal_data.get("label", ""),
        "signal_regime": signal_data.get("regime", "UNKNOWN"),
        "signal_price": price,
        "signal_volume": signal_data.get("volume", 0),
        "signal_timestamp": signal_data.get("timestamp", ""),
        "source": "tradingview",
    }

    try:
        decision = await run_council(
            symbol=symbol,
            timeframe=payload.resolved_timeframe(),
            context=context,
        )
    except Exception as e:
        logger.exception("TradingView council run failed for %s: %s", symbol, e)
        raise HTTPException(status_code=503, detail="Council evaluation failed")

    verdict_data = decision.to_dict()
    verdict_data["signal_data"] = signal_data
    verdict_data["price"] = price
    verdict_data["sizing_deferred_to_executor"] = True

    # Publish verdict so OrderExecutor can execute if BUY/SELL and gates pass
    try:
        bus = get_message_bus()
        await bus.publish("council.verdict", verdict_data)
    except Exception as e:
        logger.warning("MessageBus publish council.verdict failed: %s", e)

    # Broadcast verdict to WebSocket
    try:
        await broadcast_ws("council", {"type": "council_verdict", "verdict": verdict_data})
    except Exception as e:
        logger.debug("WebSocket broadcast (council) failed: %s", e)

    return {
        "ok": True,
        "symbol": symbol,
        "action": direction,
        "price": price,
        "mode": "council",
        "final_direction": decision.final_direction,
        "final_confidence": decision.final_confidence,
        "vetoed": decision.vetoed,
        "execution_ready": decision.execution_ready,
    }


class ExternalSignal(BaseModel):
    """Generic external signal payload."""

    symbol: str
    direction: str = "LONG"
    score: int = 50
    source: str = "external"
    message: Optional[str] = None


@router.post("/signal", dependencies=[Depends(require_auth)])
async def receive_external_signal(signal: ExternalSignal):
    """Receive a generic external signal and publish to MessageBus."""
    logger.info(
        "External signal: %s %s (score=%d)",
        signal.direction, signal.symbol, signal.score,
    )

    try:
        from app.core.message_bus import get_message_bus
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
