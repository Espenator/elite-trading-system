"""
Alerts API — alert rules persisted in SQLite.
GET /api/v1/alerts returns configured rules; PATCH /api/v1/alerts/{id} toggles enabled.
POST /api/v1/alerts/test-email sends a test email via Resend (requires RESEND_API_KEY).
"""

import logging
import ssl
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from app.services.database import db_service
from app.core.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"

router = APIRouter()

DEFAULT_RULES = [
    {"name": "Drawdown > 5%", "condition": "drawdown_gt_5", "enabled": True},
    {"name": "Signal score > 85", "condition": "signal_score_gt_85", "enabled": True},
    {"name": "Daily loss limit", "condition": "daily_loss_limit", "enabled": False},
    {"name": "Kelly edge > 0.15", "condition": "kelly_edge_gt_15", "enabled": True},
    {"name": "Position size > 8%", "condition": "kelly_pos_gt_8", "enabled": True},
    {"name": "Portfolio heat > 20%", "condition": "portfolio_heat_gt_20", "enabled": True},
    {"name": "Signal quality > 0.8", "condition": "signal_quality_gt_80", "enabled": False},
]


class AlertRule(BaseModel):
    name: str
    condition: str
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    enabled: bool | None = None


def _get_rules():
    db_service.ensure_alert_rules_seeded(DEFAULT_RULES)
    return db_service.get_alert_rules()


@router.get("")
async def get_alerts():
    """Return configured alert rules from DB."""
    return {"rules": _get_rules()}


@router.patch("/{rule_id}")
async def update_alert(rule_id: int, body: AlertRuleUpdate):
    """Toggle or update a rule (e.g. enabled) in DB."""
    if body.enabled is not None:
        rule = db_service.update_alert_rule_enabled(rule_id, body.enabled)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        return {"ok": True, "rule": rule}
    rule = next((r for r in _get_rules() if r["id"] == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"ok": True, "rule": rule}


async def _send_email_via_resend(to_email: str, subject: str, html: str) -> None:
    """Call Resend REST API with httpx. Uses default SSL context; avoids SDK SSL issues."""
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY.strip()}",
        "Content-Type": "application/json",
    }
    body = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(RESEND_API_URL, json=body, headers=headers)
        response.raise_for_status()


@router.post("/test-email")
async def test_email_alert():
    """Send a test email alert via Resend. Requires RESEND_API_KEY and RESEND_ALERT_TO_EMAIL in .env."""
    if not (settings.RESEND_API_KEY and settings.RESEND_API_KEY.strip()):
        raise HTTPException(
            status_code=503,
            detail="Email not configured. Set RESEND_API_KEY in .env",
        )
    to_email = (settings.RESEND_ALERT_TO_EMAIL or "").strip()
    if not to_email:
        raise HTTPException(
            status_code=400,
            detail="No recipient configured. Set RESEND_ALERT_TO_EMAIL in .env for test and risk alerts.",
        )
    try:
        await _send_email_via_resend(
            to_email=to_email,
            subject="[Embodier.ai] Test risk alert",
            html=(
                "<p>This is a test email from your Risk Intelligence alert system.</p>"
                "<p>If you received this, email alerts are configured correctly.</p>"
            ),
        )
        logger.info("Test email sent via Resend to %s", to_email)
        return {"ok": True, "message": "Test email alert sent"}
    except httpx.ConnectError as e:
        logger.exception("Resend connection failed")
        raise HTTPException(
            status_code=502,
            detail="Cannot reach Resend (network or firewall). Check VPN/proxy and outbound HTTPS to api.resend.com.",
        )
    except ssl.SSLError as e:
        logger.exception("Resend SSL error")
        raise HTTPException(
            status_code=502,
            detail="Secure connection to Resend failed. Update system CA certificates or check proxy.",
        )
    except httpx.HTTPStatusError as e:
        logger.exception("Resend API error")
        try:
            err_body = e.response.json()
            msg = err_body.get("message", str(err_body))
        except Exception:
            msg = e.response.text or str(e)
        raise HTTPException(status_code=502, detail=f"Resend API error: {msg}")
    except Exception as e:
        logger.exception("Resend send failed")
        raise HTTPException(status_code=502, detail=f"Failed to send email: {str(e)}")


@router.post("/test-sms")
async def test_sms_alert():
    """Send a test SMS alert. Stub: returns success; wire to SMS provider when configured."""
    # TODO: Integrate with SMS provider (e.g. Twilio) when configured
    return {"ok": True, "message": "Test SMS alert sent"}


# -----------------------------------------------------------------
# Kelly Alert Evaluation: check signals against alert thresholds
# -----------------------------------------------------------------

@router.post("/evaluate")
async def evaluate_alerts(signals: list[dict] = []):
    """Evaluate a list of signals against enabled alert rules.

    Returns triggered alerts for each signal that exceeds thresholds.
    Used by the scanner to generate real-time notifications.
    """
    rules = _get_rules()
    enabled_rules = [r for r in rules if r.get("enabled", False)]
    triggered = []

    for sig in signals:
        for rule in enabled_rules:
            cond = rule["condition"]
            fired = False
            if cond == "drawdown_gt_5":
                fired = sig.get("drawdown_pct", 0) > 5
            elif cond == "signal_score_gt_85":
                fired = sig.get("composite_score", 0) > 85
            elif cond == "daily_loss_limit":
                fired = sig.get("daily_loss_pct", 0) > 2
            elif cond == "kelly_edge_gt_15":
                fired = sig.get("kelly_edge", 0) > 0.15
            elif cond == "kelly_pos_gt_8":
                fired = sig.get("kelly_fraction", 0) > 0.08
            elif cond == "portfolio_heat_gt_20":
                fired = sig.get("portfolio_heat", 0) > 0.20
            elif cond == "signal_quality_gt_80":
                fired = sig.get("signal_quality", 0) > 0.80
            elif cond == "risk_score_lt_40":
                fired = sig.get("risk_score", 100) < 40
            elif cond == "drawdown_breached":
                fired = sig.get("drawdown_breached", False)
            elif cond == "trading_paused":
                fired = not sig.get("trading_allowed", True)
            elif cond == "profit_factor_lt_1":
                fired = sig.get("profit_factor", 999) < 1.0
            elif cond == "kelly_advantage_negative":
                fired = sig.get("kelly_advantage", 0) < 0
            if fired:
                triggered.append({
                    "symbol": sig.get("symbol", "?"),
                    "rule": rule["name"],
                    "condition": cond,
                    "value": sig.get(cond.split("_gt_")[0].replace("_", "."), "N/A"),
                                    "severity": "high" if "loss" in cond or "drawdown" in cond or "paused" in cond or "risk_score" in cond else "info",
                })

    return {
        "total_signals": len(signals),
        "total_triggered": len(triggered),
        "alerts": triggered,
    }
