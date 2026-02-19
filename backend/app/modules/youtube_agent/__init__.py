"""
YouTube Knowledge Agent — ingest transcripts from financial YouTube videos,
extract trading ideas and technical analysis concepts, feed into ML feature engineering.
24/7 self-learning flywheel.
"""

import logging
from datetime import datetime, timezone
from typing import List, Tuple

from app.modules.symbol_universe import get_tracked_symbols
from app.modules.youtube_agent.config import (
    MAX_VIDEOS_PER_TICK,
    TRANSCRIPT_LANGUAGES,
)
from app.modules.youtube_agent.transcripts import fetch_transcript
from app.modules.youtube_agent.extractor import (
    extract_ideas_and_concepts,
    extract_symbols_from_text,
)
from app.modules.youtube_agent.video_discovery import get_video_ids_to_process
from app.modules.youtube_agent.storage import (
    get_processed_ids,
    mark_processed,
    append_knowledge,
    set_status,
)

logger = logging.getLogger(__name__)

AGENT_NAME = "YouTube Knowledge Agent"


def get_status() -> dict:
    """Return engine status (last_run, error, knowledge_count, processed_count)."""
    from app.services.database import db_service

    stored = db_service.get_config("youtube_agent_status") or {}
    knowledge = db_service.get_config("youtube_knowledge") or []
    processed = db_service.get_config("youtube_processed_ids") or []
    return {
        "status": "running",
        "last_run": stored.get("last_run"),
        "error": stored.get("error"),
        "knowledge_entries": len(knowledge),
        "processed_video_count": len(processed),
    }


def run_tick(
    *,
    max_videos_per_tick: int = MAX_VIDEOS_PER_TICK,
) -> List[Tuple[str, str]]:
    """
    Run one YouTube Knowledge Agent tick: discover videos, fetch transcripts,
    extract ideas/concepts/symbols, append to knowledge store for ML feed.
    Returns list of (message, level) for activity log.
    """
    entries: List[Tuple[str, str]] = []
    set_status(error=None)

    processed = get_processed_ids()
    to_process = get_video_ids_to_process(processed)[:max_videos_per_tick]
    if not to_process:
        entries.append(
            (
                "No new videos to process (set YOUTUBE_API_KEY; optional: YOUTUBE_CHANNEL_IDS or YOUTUBE_VIDEO_IDS)",
                "info",
            )
        )
        set_status(last_run=datetime.now(timezone.utc).isoformat())
        return entries

    symbols = get_tracked_symbols()
    for video_id in to_process:
        try:
            text = fetch_transcript(video_id, languages=TRANSCRIPT_LANGUAGES)
            if not text:
                entries.append((f"No transcript for video {video_id}", "warning"))
                mark_processed(video_id)
                continue
            extracted = extract_ideas_and_concepts(text)
            syms = extract_symbols_from_text(text, symbols) if symbols else []
            ideas = extracted.get("ideas") or []
            concepts = extracted.get("concepts") or []
            title_placeholder = f"Video {video_id}"
            entry = {
                "video_id": video_id,
                "title": title_placeholder,
                "ideas": ideas,
                "concepts": concepts,
                "symbols": syms[:20],
                "snippet": (text[:500] + "...") if len(text) > 500 else text,
            }
            append_knowledge(entry)
            mark_processed(video_id)
            n_ideas = len(ideas) + len(concepts)
            msg = f"Extracted {n_ideas} ideas/concepts from '{title_placeholder}'"
            if syms:
                msg += f" (symbols: {', '.join(syms[:5])})"
            entries.append((msg, "success"))
        except Exception as e:
            logger.exception("YouTube process failed for %s", video_id)
            entries.append((f"Failed {video_id}: {str(e)[:60]}", "warning"))
            set_status(error=str(e)[:120])

    set_status(last_run=datetime.now(timezone.utc).isoformat())
    if not entries:
        entries.append(("Tick completed; no new transcripts", "info"))
    return entries
