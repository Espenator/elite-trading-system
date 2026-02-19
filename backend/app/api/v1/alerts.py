"""
Alerts API — alert rules and notifications (stub until alerting is wired).
GET /api/v1/alerts returns configured rules; POST to create/update (stub).
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class AlertRule(BaseModel):
    name: str
    condition: str
    enabled: bool = True


@router.get("")
async def get_alerts():
    """Return configured alert rules. Stub for now."""
    return {
        "rules": [
            {
                "id": 1,
                "name": "Drawdown > 5%",
                "condition": "drawdown_gt_5",
                "enabled": True,
            },
            {
                "id": 2,
                "name": "Signal score > 85",
                "condition": "signal_score_gt_85",
                "enabled": True,
            },
        ],
    }


@router.post("")
async def create_alert(rule: AlertRule):
    """Create or update an alert rule. Stub for now."""
    return {"ok": True, "rule": rule.model_dump()}
