"""
Logs API — system activity logs (stub until logging pipeline is wired).
GET /api/v1/logs returns recent activity for Operator Console / debugging.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_logs(limit: int = 100):
    """Return recent system logs. Stub for now."""
    return {
        "logs": [
            {
                "ts": "2024-02-18T14:00:00Z",
                "level": "info",
                "message": "Signal batch completed",
                "source": "signals",
            },
            {
                "ts": "2024-02-18T13:58:00Z",
                "level": "info",
                "message": "Agent Market Data Agent started",
                "source": "agents",
            },
            {
                "ts": "2024-02-18T13:55:00Z",
                "level": "warning",
                "message": "Data source SEC EDGAR latency high",
                "source": "data-sources",
            },
        ][:limit],
    }
