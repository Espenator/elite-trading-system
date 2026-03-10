"""Awareness Worker API: POST /enrich for batch SensoryEvent enrichment (PC2).

When running on PC2 (RTX/CUDA), this endpoint enriches events with tags, novelty score, embedding_ref.
PC1 uses awareness_worker.enrich_events() client or SensoryRouter _send_to_awareness_http; fails gracefully if PC2 down.
Stub implementation returns placeholder enrichment; replace with GPU/embedding pipeline on PC2.
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.core.security import require_auth
from pydantic import BaseModel

router = APIRouter(prefix="/awareness", tags=["awareness"])


class EnrichRequest(BaseModel):
    events: List[Dict[str, Any]] = []


@router.post("/enrich", dependencies=[Depends(require_auth)])
async def awareness_enrich(req: EnrichRequest) -> Dict[str, Any]:
    """Batch enrich sensory events (tags, novelty_score, embedding_ref). Stub when no GPU."""
    enriched: List[Dict[str, Any]] = []
    for evt in req.events or []:
        ev = dict(evt)
        # Stub: add placeholder enrichment; on PC2 replace with real embeddings/clustering
        ev.setdefault("embedding_ref", "stub")
        ev.setdefault("novelty_score", 0.5)
        tags = list(ev.get("tags") or [])
        if "awareness_stub" not in tags:
            tags.append("awareness_stub")
        ev["tags"] = tags
        enriched.append(ev)
    return {"enriched": enriched, "results": enriched, "count": len(enriched)}
