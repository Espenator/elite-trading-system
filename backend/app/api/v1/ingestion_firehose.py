from __future__ import annotations

"""
Ingestion Firehose API.

Imported by `app.main` and mounted via `app.include_router(...)`.

Note: Full ingestion orchestration lives in later prompt pack agents. This
module intentionally stays lightweight so the backend can import and tests can
run without optional ingestion services.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])


@router.get("/firehose/health")
async def firehose_health():
    return {"status": "ok"}

