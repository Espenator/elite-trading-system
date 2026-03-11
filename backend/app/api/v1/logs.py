"""
Logs API — real system activity logs from Python logging ring buffer.
GET /api/v1/logs returns recent activity for Operator Console / debugging.
"""

from fastapi import APIRouter

from app.core.logging_config import get_ring_buffer

router = APIRouter()


@router.get("")
async def get_logs(limit: int = 100):
    """Return recent system logs from in-memory ring buffer.

    Used by Operator Console.
    Fields: ts, level, message, source, agent, type (for filter).
    """
    ring = get_ring_buffer()
    logs = ring.get_recent(limit=limit)
    return {"logs": logs}
