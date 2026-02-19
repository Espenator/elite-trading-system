"""
Flywheel API — ML accuracy and outcome feedback (stub until flywheel pipeline is wired).
GET /api/v1/flywheel returns metrics for Dashboard/ML insights.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_flywheel():
    """Return flywheel metrics: accuracy over time, outcome resolution stats. Stub for now."""
    return {
        "accuracy30d": 0.68,
        "accuracy90d": 0.65,
        "resolvedSignals": 1240,
        "pendingResolution": 42,
        "history": [
            {"date": "2024-01", "accuracy": 0.62},
            {"date": "2024-02", "accuracy": 0.65},
            {"date": "2024-03", "accuracy": 0.68},
        ],
    }
