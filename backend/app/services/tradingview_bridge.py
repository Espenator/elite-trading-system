"""TradingView webhook bridge — push Embodier trade ideas to webhooks.

Supports two destinations (both fire if configured):
- TRADINGVIEW_WEBHOOK_URL: monitoring/testing (e.g. webhook.site)
- TRADERSPOST_WEBHOOK_URL: TradersPost for Alpaca execution (only when execute=True)

Used by morning briefing job and POST /api/v1/tradingview/push-signals.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
TIMEOUT = 10.0


def _signal_to_payload(idea: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a briefing trade idea to TradingView webhook payload."""
    action = (idea.get("action") or "buy").lower()
    if action == "long":
        action = "buy"
    elif action == "short":
        action = "sell"
    return {
        "ticker": (idea.get("ticker") or idea.get("symbol") or "").upper(),
        "action": action,
        "price": round(float(idea.get("price") or idea.get("entry") or 0), 2),
        "stop": round(float(idea.get("stop") or idea.get("stop_loss") or 0), 2),
        "target1": round(float(idea.get("target1") or idea.get("target_1") or 0), 2),
        "target2": round(float(idea.get("target2") or idea.get("target_2") or 0), 2),
        "message": idea.get("message") or "",
    }


class TradingViewBridge:
    """Pushes Embodier Trader signals to external webhooks.

    Supports two destinations (both fire if configured):
    - TRADINGVIEW_WEBHOOK_URL: webhook.site for testing / monitoring
    - TRADERSPOST_WEBHOOK_URL: TradersPost for actual Alpaca execution
    """

    _instance = None
    _last_push_time: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.webhook_url = (
            getattr(settings, "TRADINGVIEW_WEBHOOK_URL", None)
            or os.getenv("TRADINGVIEW_WEBHOOK_URL", "")
            or ""
        ).strip()
        self.traderspost_url = (
            getattr(settings, "TRADERSPOST_WEBHOOK_URL", None)
            or os.getenv("TRADERSPOST_WEBHOOK_URL", "")
            or ""
        ).strip()
        self.enabled = bool(self.webhook_url) or bool(self.traderspost_url)
        self.timeout = TIMEOUT
        # Backward compatibility
        self._url = self.webhook_url

    def is_configured(self) -> bool:
        return self.enabled

    def _format_payload(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Format for monitoring webhook (webhook.site) — full detail."""
        direction = (idea.get("direction") or idea.get("action") or "buy").lower()
        if direction == "long":
            direction = "buy"
        elif direction == "short":
            direction = "sell"
        entry_zone = idea.get("entry_zone") or []
        price = entry_zone[0] if entry_zone else float(idea.get("price") or idea.get("entry") or 0)
        return {
            "ticker": (idea.get("symbol") or idea.get("ticker") or "").upper(),
            "action": direction,
            "price": round(price, 2),
            "stop_loss": round(float(idea.get("stop_loss") or idea.get("stop") or 0), 2),
            "take_profit": round(float(idea.get("target_1") or idea.get("target1") or 0), 2),
            "take_profit_2": round(float(idea.get("target_2") or idea.get("target2") or 0), 2),
            "position_size_pct": round(float(idea.get("position_size_pct") or 0), 2),
            "order_type": "limit",
            "confidence": round(float(idea.get("confidence") or 0), 2),
            "score": int(idea.get("score") or 0),
            "regime": idea.get("regime", "unknown"),
            "council_decision_id": idea.get("council_decision_id", ""),
            "source": "embodier_trader",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Embodier: {} {} | Score {} | Conf {:.0%}".format(
                (idea.get("direction") or "buy").upper(),
                (idea.get("symbol") or idea.get("ticker") or "").upper(),
                idea.get("score", 0),
                float(idea.get("confidence", 0)),
            ),
        }

    def _format_traderspost_payload(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Format for TradersPost — matches their expected webhook schema."""
        direction = (idea.get("direction") or idea.get("action") or "buy").lower()
        if direction == "long":
            direction = "buy"
        elif direction == "short":
            direction = "sell"
        entry_zone = idea.get("entry_zone") or []
        price = entry_zone[0] if entry_zone else float(idea.get("price") or idea.get("entry") or 0)
        return {
            "ticker": (idea.get("symbol") or idea.get("ticker") or "").upper(),
            "action": direction,
            "sentiment": "bullish" if direction == "buy" else "bearish",
            "price": round(price, 2),
            "time": datetime.now(timezone.utc).isoformat(),
        }

    async def push_signals(
        self,
        trade_ideas: List[Dict[str, Any]],
        execute: bool = False,
    ) -> Dict[str, Any]:
        """Send trade ideas to configured webhook URLs.

        Args:
            trade_ideas: List of signal dicts from briefing service.
            execute: If True, ALSO send to TradersPost for real Alpaca execution.
                     If False, only send to monitoring webhook (webhook.site).
                     Safety gate — never auto-execute without explicit flag.

        Returns:
            Delivery status with monitor_results and execution_results.
        """
        if not self.enabled:
            logger.info("No webhook URLs configured")
            return {
                "sent": False,
                "reason": "no_webhook_urls_configured",
                "monitor_results": [],
                "execution_results": [],
                "executed": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        monitor_results: List[Dict[str, Any]] = []
        execution_results: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for idea in trade_ideas:
                if self.webhook_url:
                    payload = self._format_payload(idea)
                    try:
                        resp = await client.post(self.webhook_url, json=payload)
                        monitor_results.append({
                            "symbol": idea.get("symbol", payload.get("ticker", "")),
                            "status": resp.status_code,
                            "success": 200 <= resp.status_code < 300,
                        })
                    except httpx.RequestError as e:
                        logger.error("Monitor webhook failed for %s: %s", idea.get("symbol"), e)
                        monitor_results.append({
                            "symbol": idea.get("symbol", ""),
                            "success": False,
                            "error": str(e),
                        })

                if execute and self.traderspost_url:
                    tp_payload = self._format_traderspost_payload(idea)
                    try:
                        resp = await client.post(self.traderspost_url, json=tp_payload)
                        execution_results.append({
                            "symbol": idea.get("symbol", tp_payload.get("ticker", "")),
                            "status": resp.status_code,
                            "success": 200 <= resp.status_code < 300,
                        })
                    except httpx.RequestError as e:
                        logger.error("TradersPost execution failed for %s: %s", idea.get("symbol"), e)
                        execution_results.append({
                            "symbol": idea.get("symbol", ""),
                            "success": False,
                            "error": str(e),
                        })

        self._last_push_time = datetime.now(timezone.utc).isoformat()
        return {
            "sent": True,
            "monitor_results": monitor_results,
            "execution_results": execution_results,
            "executed": execute,
            "timestamp": self._last_push_time,
        }

    async def push_signals_to_webhook(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """POST each signal to TRADINGVIEW_WEBHOOK_URL (legacy). execute=False."""
        if not self.webhook_url:
            logger.debug("TradingView webhook URL not set, skipping push")
            return {"pushed_count": 0, "failed_count": len(signals), "errors": ["TRADINGVIEW_WEBHOOK_URL not set"]}

        pushed = 0
        errors: List[str] = []

        for idea in signals:
            payload = _signal_to_payload(idea)
            if not payload.get("ticker"):
                errors.append("skip: missing ticker")
                continue
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    r = await client.post(self.webhook_url, json=payload)
                    if r.is_success:
                        pushed += 1
                    else:
                        errors.append(f"{payload.get('ticker')}: HTTP {r.status_code}")
            except Exception as e:
                errors.append(f"{payload.get('ticker')}: {e!s}")

        failed = len(signals) - pushed
        if errors:
            logger.warning("TradingView push: %d ok, %d failed: %s", pushed, failed, errors[:5])
        return {"pushed_count": pushed, "failed_count": failed, "errors": errors}


def get_tradingview_bridge() -> TradingViewBridge:
    """Return the TradingViewBridge singleton."""
    return TradingViewBridge()
