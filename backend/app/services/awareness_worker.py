"""PC2 Awareness Worker client: batch SensoryEvent enrichment (tags, novelty, embedding).

PC1 calls POST /awareness/enrich on PC2 (RTX/CUDA). Client fails gracefully when
AWARENESS_WORKER_URL is unset or PC2 is down.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

AWARENESS_WORKER_URL = os.getenv("AWARENESS_WORKER_URL", "").strip()
DEFAULT_TIMEOUT = 30.0


async def enrich_events(events: List[Dict[str, Any]], timeout: float = DEFAULT_TIMEOUT) -> Optional[List[Dict[str, Any]]]:
    """POST batch of sensory events to PC2; return enriched list (tags, novelty_score, embedding_ref) or None if down."""
    url = AWARENESS_WORKER_URL
    if not url:
        logger.debug("AWARENESS_WORKER_URL not set — skipping enrichment")
        return None
    if not url.endswith("/"):
        url = url.rstrip("/")
    endpoint = f"{url}/awareness/enrich"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(endpoint, json={"events": events})
            r.raise_for_status()
            data = r.json()
        return data.get("enriched") or data.get("results") or []
    except Exception as e:
        logger.debug("Awareness worker enrichment failed (graceful): %s", e)
        return None


def is_awareness_worker_configured() -> bool:
    return bool(AWARENESS_WORKER_URL)
