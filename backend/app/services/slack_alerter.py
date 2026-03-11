"""Slack Alerter — webhook-based notifications for trading system health.

Sends alerts to Slack when data sources fail, LLM providers degrade,
or critical thresholds are breached.

Configuration:
  SLACK_WEBHOOK_URL: Slack incoming webhook URL
  SLACK_ALERT_CHANNEL: Override channel (optional)
  SLACK_ALERT_THROTTLE_SEC: Min seconds between identical alerts (default: 300)
"""

import asyncio
import hashlib
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Severity levels
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

# Slack webhook colors by severity
_SEVERITY_COLORS = {
    SEVERITY_INFO: "#36a64f",       # Green
    SEVERITY_WARNING: "#ff9900",    # Orange
    SEVERITY_CRITICAL: "#ff0000",   # Red
}

_SEVERITY_EMOJI = {
    SEVERITY_INFO: "large_blue_circle",
    SEVERITY_WARNING: "warning",
    SEVERITY_CRITICAL: "rotating_light",
}


class SlackAlerter:
    """Sends throttled alerts to Slack via incoming webhook."""

    def __init__(self):
        self._webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        self._channel = os.getenv("SLACK_ALERT_CHANNEL", "")
        self._throttle_sec = int(os.getenv("SLACK_ALERT_THROTTLE_SEC", "300"))
        self._enabled = bool(self._webhook_url)

        # Throttle state: alert_hash -> last_sent_timestamp
        self._sent_alerts: Dict[str, float] = {}
        self._alerts_sent = 0
        self._alerts_throttled = 0

        if self._enabled:
            logger.info("SlackAlerter enabled (throttle=%ds)", self._throttle_sec)
        else:
            logger.info("SlackAlerter disabled (no SLACK_WEBHOOK_URL)")

    async def send(
        self,
        title: str,
        message: str,
        severity: str = SEVERITY_WARNING,
        source: str = "system",
        fields: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Send an alert to Slack.

        Returns True if sent, False if throttled or disabled.
        """
        if not self._enabled:
            logger.debug("Slack alert suppressed (disabled): %s", title)
            return False

        # Throttle check
        alert_hash = hashlib.md5(f"{title}:{source}".encode()).hexdigest()
        now = time.time()
        last_sent = self._sent_alerts.get(alert_hash, 0)
        if now - last_sent < self._throttle_sec:
            self._alerts_throttled += 1
            return False

        # Build Slack message
        color = _SEVERITY_COLORS.get(severity, "#808080")
        emoji = _SEVERITY_EMOJI.get(severity, "bell")

        attachment_fields = []
        if fields:
            for k, v in fields.items():
                attachment_fields.append({
                    "title": k,
                    "value": str(v),
                    "short": True,
                })

        payload = {
            "text": f":{emoji}: *{title}*",
            "attachments": [
                {
                    "color": color,
                    "text": message,
                    "fields": attachment_fields,
                    "footer": f"Embodier Trader | {source}",
                    "ts": int(now),
                }
            ],
        }
        if self._channel:
            payload["channel"] = self._channel

        # Send via httpx
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._webhook_url, json=payload)
                if resp.status_code == 200:
                    self._sent_alerts[alert_hash] = now
                    self._alerts_sent += 1
                    logger.info("Slack alert sent: %s [%s]", title, severity)
                    return True
                else:
                    logger.warning(
                        "Slack webhook failed: %d %s", resp.status_code, resp.text
                    )
                    return False
        except Exception as e:
            logger.warning("Slack alert failed: %s", e)
            return False

    async def send_health_alert(
        self,
        source_name: str,
        status: str,
        error: Optional[str] = None,
    ) -> bool:
        """Convenience method for data source health alerts."""
        severity = SEVERITY_CRITICAL if status == "unavailable" else SEVERITY_WARNING
        return await self.send(
            title=f"Data Source: {source_name} is {status}",
            message=error or f"{source_name} health check failed",
            severity=severity,
            source="health_monitor",
            fields={
                "Source": source_name,
                "Status": status,
            },
        )

    def get_status(self) -> Dict[str, Any]:
        """Return alerter status."""
        return {
            "enabled": self._enabled,
            "alerts_sent": self._alerts_sent,
            "alerts_throttled": self._alerts_throttled,
            "throttle_sec": self._throttle_sec,
            "has_webhook": bool(self._webhook_url),
        }

    def _prune_stale_throttles(self):
        """Clean up old throttle entries."""
        now = time.time()
        self._sent_alerts = {
            k: v for k, v in self._sent_alerts.items()
            if now - v < self._throttle_sec * 2
        }


# Module-level singleton
_alerter: Optional[SlackAlerter] = None


def get_slack_alerter() -> SlackAlerter:
    """Get or create the SlackAlerter singleton."""
    global _alerter
    if _alerter is None:
        _alerter = SlackAlerter()
    return _alerter
