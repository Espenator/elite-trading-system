"""
Alerts API — alert rules and notifications (stub until alerting is wired).
GET /api/v1/alerts returns configured rules; PATCH /api/v1/alerts/{id} toggles enabled.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# In-memory store so toggles persist for the session
_rules = [
    {"id": 1, "name": "Drawdown > 5%", "condition": "drawdown_gt_5", "enabled": True},
    {
        "id": 2,
        "name": "Signal score > 85",
        "condition": "signal_score_gt_85",
        "enabled": True,
    },
    {
        "id": 3,
        "name": "Daily loss limit",
        "condition": "daily_loss_limit",
        "enabled": False,
    },
]


class AlertRule(BaseModel):
    name: str
    condition: str
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    enabled: bool | None = None


@router.get("")
async def get_alerts():
    """Return configured alert rules."""
    return {"rules": _rules}


@router.patch("/{rule_id}")
async def update_alert(rule_id: int, body: AlertRuleUpdate):
    """Toggle or update a rule (e.g. enabled)."""
    rule = next((r for r in _rules if r["id"] == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    if body.enabled is not None:
        rule["enabled"] = body.enabled
    return {"ok": True, "rule": rule}
