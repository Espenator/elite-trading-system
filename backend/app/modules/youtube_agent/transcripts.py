"""Fetch YouTube video transcripts via youtube-transcript-api (no API key)."""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def fetch_transcript(
    video_id: str,
    languages: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Fetch transcript for a YouTube video. Returns full text or None if unavailable.
    Uses youtube-transcript-api (no API key). Pass video ID only (e.g. from watch?v=ID).
    """
    if not (video_id or "").strip():
        return None
    video_id = video_id.strip()
    languages = languages or ["en"]
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        fetched = YouTubeTranscriptApi().fetch(video_id, languages=languages)
        if not fetched:
            return None
        parts = [snippet.text for snippet in fetched]
        return " ".join(parts) if parts else None
    except Exception as e:
        logger.warning("YouTube transcript fetch failed for %s: %s", video_id, e)
        return None
