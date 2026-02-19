"""
Alerts API — alert rules persisted in SQLite.
GET /api/v1/alerts returns configured rules; PATCH /api/v1/alerts/{id} toggles enabled.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.database import db_service

router = APIRouter()

DEFAULT_RULES = [
    {"name": "Drawdown > 5%", "condition": "drawdown_gt_5", "enabled": True},
    {"name": "Signal score > 85", "condition": "signal_score_gt_85", "enabled": True},
    {"name": "Daily loss limit", "condition": "daily_loss_limit", "enabled": False},
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
