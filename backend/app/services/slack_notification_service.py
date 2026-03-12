"""Slack notification service — sends alerts to Embodier Trader workspace.

Supports two bots:
  1. OpenClaw (A0AF9HSCQ6S) — multi-agent swarm notifications
  2. TradingView Alerts (A0AFQ89RVEV) — inbound TradingView webhook alerts

Tokens are short-lived (12h) and must be refreshed via Slack API console.
If SLACK_BOT_TOKEN is missing, all methods degrade gracefully (no-op).

Channel mapping (Embodier Trader workspace):
  #trade-alerts      — signals, council verdicts, trading decisions
  #oc-trade-desk     — order executions, fills, position updates
  #embodier-trader   — system alerts, health, circuit breakers

Usage:
    from app.services.slack_notification_service import slack_service
    await slack_service.send_signal("AAPL", "BUY", score=87)
    await slack_service.send_alert("Circuit breaker triggered", level="RED")
"""

import logging
import time
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SLACK_API = "https://slack.com/api"

# ── Channel constants (mapped to existing Embodier Trader workspace) ──
CH_SIGNALS = "#trade-alerts"        # signals + council verdicts
CH_EXECUTIONS = "#oc-trade-desk"    # order executions + fills
CH_SYSTEM = "#embodier-trader"      # system alerts + health

# Rate limit: max 1 message per second per channel
_last_send: Dict[str, float] = {}
_RATE_LIMIT_SEC = 1.0


class SlackNotificationService:
    """Sends structured notifications to Slack channels."""

    def __init__(self):
        self._token = settings.SLACK_BOT_TOKEN or ""
        self._default_channel = CH_SIGNALS

    def _is_configured(self) -> bool:
        return bool(self._token)

    async def _post_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[list] = None,
    ) -> bool:
        """Send a message to a Slack channel. Returns True on success."""
        if not self._is_configured():
            logger.debug("Slack not configured (no SLACK_BOT_TOKEN)")
            return False

        # Rate limit per channel
        now = time.monotonic()
        last = _last_send.get(channel, 0)
        if (now - last) < _RATE_LIMIT_SEC:
            logger.debug("Slack rate limited for %s", channel)
            return False
        _last_send[channel] = now

        payload: Dict[str, Any] = {
            "channel": channel,
            "text": text,
        }
        if blocks:
            payload["blocks"] = blocks

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{SLACK_API}/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            data = resp.json()
            if not data.get("ok"):
                logger.warning("Slack API error: %s", data.get("error", "unknown"))
                return False
            return True
        except Exception as e:
            logger.warning("Slack send failed: %s", e)
            return False

    async def send_signal(
        self,
        symbol: str,
        direction: str,
        score: int = 0,
        kelly_pct: float = 0,
        channel: Optional[str] = None,
    ) -> bool:
        """Send a trading signal notification to #trade-alerts."""
        ch = channel or CH_SIGNALS
        emoji = ":chart_with_upwards_trend:" if direction == "LONG" else ":chart_with_downwards_trend:"
        text = f"{emoji} *{symbol}* — {direction} | Score: {score} | Kelly: {kelly_pct:.1f}%"
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            }
        ]
        return await self._post_message(ch, text, blocks)

    async def send_alert(
        self,
        message: str,
        level: str = "INFO",
        channel: Optional[str] = None,
    ) -> bool:
        """Send a system alert to #embodier-trader."""
        ch = channel or CH_SYSTEM
        emoji_map = {"RED": ":red_circle:", "AMBER": ":large_orange_circle:", "INFO": ":information_source:"}
        emoji = emoji_map.get(level.upper(), ":information_source:")
        text = f"{emoji} [{level.upper()}] {message}"
        return await self._post_message(ch, text)

    async def send_trade_execution(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        channel: Optional[str] = None,
    ) -> bool:
        """Send a trade execution confirmation to #oc-trade-desk."""
        ch = channel or CH_EXECUTIONS
        emoji = ":white_check_mark:" if side.lower() == "buy" else ":x:"
        text = f"{emoji} Executed: {side.upper()} {qty}x *{symbol}* @ ${price:.2f}"
        return await self._post_message(ch, text)

    async def send_council_verdict(
        self,
        symbol: str,
        verdict: str,
        confidence: float,
        channel: Optional[str] = None,
    ) -> bool:
        """Send a council verdict notification to #trade-alerts."""
        ch = channel or CH_SIGNALS
        text = f":scales: Council: *{symbol}* → {verdict} ({confidence:.0f}% confidence)"
        return await self._post_message(ch, text)


# Singleton
slack_service = SlackNotificationService()


def get_slack_service() -> SlackNotificationService:
    """Return the module-level singleton (used by main.py, message_bus.py)."""
    return slack_service


async def send_slack_message(
    text: str,
    channel: str = CH_SYSTEM,
) -> bool:
    """Convenience function for quick one-liner alerts.

    Used by order_executor._slack_alert() and alpaca_stream_service._slack_alert().
    """
    return await slack_service._post_message(channel, text)
