"""Discover YouTube video IDs to process using only YOUTUBE_API_KEY (search API)."""

import logging
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


def fetch_video_ids_via_search(max_results: int = 15) -> List[str]:
    """
    Use YouTube Data API v3 search to find videos by query. Only YOUTUBE_API_KEY required.
    Uses YOUTUBE_SEARCH_QUERY (default: financial/trading). Returns list of video IDs.
    """
    api_key = (settings.YOUTUBE_API_KEY or "").strip()
    if not api_key:
        return []
    query = (
        settings.YOUTUBE_SEARCH_QUERY or "stock market trading technical analysis"
    ).strip()
    if not query:
        query = "stock market trading technical analysis"
    try:
        import httpx

        resp = httpx.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "id",
                "type": "video",
                "q": query,
                "maxResults": min(max_results, 50),
                "key": api_key,
                "order": "date",
                "relevanceLanguage": "en",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        video_ids = []
        for it in data.get("items") or []:
            vid = (it.get("id") or {}).get("videoId")
            if vid:
                video_ids.append(vid)
        return video_ids
    except Exception as e:
        logger.warning("YouTube search API failed: %s", e)
        return []


def get_video_ids_to_process(already_processed: List[str]) -> List[str]:
    """
    Return next batch of video IDs to process. Uses only YOUTUBE_API_KEY + search.
    Excludes already_processed.
    """
    processed_set = set(already_processed or [])
    from_search = fetch_video_ids_via_search()
    return [v for v in from_search if v not in processed_set]
