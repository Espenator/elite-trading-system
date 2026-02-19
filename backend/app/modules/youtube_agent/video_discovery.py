"""Discover YouTube video IDs to process: from API (channels) or static list."""

import logging
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_channel_ids() -> List[str]:
    """Parse YOUTUBE_CHANNEL_IDS (comma-separated)."""
    raw = (settings.YOUTUBE_CHANNEL_IDS or "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def get_static_video_ids() -> List[str]:
    """Parse YOUTUBE_VIDEO_IDS (comma-separated)."""
    raw = (settings.YOUTUBE_VIDEO_IDS or "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def fetch_recent_video_ids_from_channels(max_per_channel: int = 5) -> List[str]:
    """
    Use YouTube Data API v3 to list recent uploads from configured channels.
    Requires YOUTUBE_API_KEY and YOUTUBE_CHANNEL_IDS. Returns list of video IDs.
    """
    api_key = (settings.YOUTUBE_API_KEY or "").strip()
    channel_ids = get_channel_ids()
    if not api_key or not channel_ids:
        return []

    try:
        import httpx

        video_ids: List[str] = []
        for cid in channel_ids[:20]:
            # Get uploads playlist ID for channel
            resp = httpx.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "contentDetails", "id": cid, "key": api_key},
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items") or []
            if not items:
                continue
            uploads_playlist = (
                items[0].get("contentDetails", {}).get("uploadList", {}).get("uploads")
            )
            if not uploads_playlist:
                continue
            # Get recent videos from uploads playlist
            pl_resp = httpx.get(
                "https://www.googleapis.com/youtube/v3/playlistItems",
                params={
                    "part": "snippet",
                    "playlistId": uploads_playlist,
                    "maxResults": max_per_channel,
                    "key": api_key,
                },
                timeout=15.0,
            )
            pl_resp.raise_for_status()
            pl_data = pl_resp.json()
            for it in pl_data.get("items") or []:
                vid = (it.get("snippet") or {}).get("resourceId", {}).get("videoId")
                if vid:
                    video_ids.append(vid)
        return video_ids
    except Exception as e:
        logger.warning("YouTube Data API fetch failed: %s", e)
        return []


def fetch_video_ids_via_search(max_results: int = 15) -> List[str]:
    """
    Use YouTube Data API v3 search to find videos by query. Works with only YOUTUBE_API_KEY.
    Uses YOUTUBE_SEARCH_QUERY (default: financial/trading). Returns list of video IDs.
    """
    api_key = (settings.YOUTUBE_API_KEY or "").strip()
    if not api_key:
        return []
    query = (
        settings.YOUTUBE_SEARCH_QUERY or "stock market trading technical analysis"
    ).strip()
    if not query:
        return []
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
    Return next batch of video IDs to process. Order: static IDs, then channel uploads,
    then search by YOUTUBE_SEARCH_QUERY (so only YOUTUBE_API_KEY is enough). Excludes already_processed.
    """
    processed_set = set(already_processed or [])

    static = get_static_video_ids()
    candidates = [v for v in static if v not in processed_set]
    if candidates:
        return candidates

    from_channels = fetch_recent_video_ids_from_channels()
    candidates = [v for v in from_channels if v not in processed_set]
    if candidates:
        return candidates

    from_search = fetch_video_ids_via_search()
    return [v for v in from_search if v not in processed_set]
