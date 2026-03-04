"""
YouTube Knowledge API stub — transcript ingestion / video intel.
GET /api/v1/youtube-knowledge returns a summary for Signal Intelligence page.
Full implementation can add transcript indexing and search later.
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", summary="YouTube knowledge summary")
@router.get("/", summary="YouTube knowledge summary with trailing slash")
async def get_youtube_knowledge():
    """Stub for Signal Intelligence page; avoids 404. Returns empty videos list until integration is built."""
    return {
        "videos": [],
        "status": "ok",
        "message": "YouTube Knowledge integration pending",
    }
