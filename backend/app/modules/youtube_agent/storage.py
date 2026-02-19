"""Persist YouTube knowledge and processing state for ML feed and flywheel."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.modules.youtube_agent.config import KNOWLEDGE_MAX_ENTRIES


def get_processed_ids() -> List[str]:
    from app.services.database import db_service
    return list(db_service.get_config("youtube_processed_ids") or [])


def mark_processed(video_id: str) -> None:
    from app.services.database import db_service
    ids = get_processed_ids()
    if video_id not in ids:
        ids.append(video_id)
    db_service.set_config("youtube_processed_ids", ids[-2000:])  # cap queue size


def append_knowledge(entry: Dict[str, Any]) -> None:
    from app.services.database import db_service
    entries = db_service.get_config("youtube_knowledge") or []
    entry["fetched_at"] = datetime.now(timezone.utc).isoformat()
    entries.insert(0, entry)
    db_service.set_config("youtube_knowledge", entries[:KNOWLEDGE_MAX_ENTRIES])


def get_knowledge(limit: int = 100) -> List[Dict[str, Any]]:
    from app.services.database import db_service
    entries = db_service.get_config("youtube_knowledge") or []
    return entries[:limit]


def set_status(last_run: str = None, error: str = None) -> None:
    from app.services.database import db_service
    status = db_service.get_config("youtube_agent_status") or {}
    if last_run is not None:
        status["last_run"] = last_run
    if error is not None:
        status["error"] = error
    db_service.set_config("youtube_agent_status", status)
