"""Triage API — operator visibility into the E3 attention gate."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def triage_status():
    """Return triage counters, drop reasons, and recent audit trail."""
    from app.services.idea_triage import get_idea_triage_service

    triage = get_idea_triage_service()
    return triage.get_stats()

