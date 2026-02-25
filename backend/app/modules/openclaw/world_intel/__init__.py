"""World Intelligence Sensorium — OpenClaw Agent Swarm System 1.

Multi-source intelligence gathering pipeline that feeds the
Blackboard pub/sub system with pre-processed alpha signals.

Components:
    - WorldIntelSensorium: Main orchestrator
    - NewsAggregator: Financial news via NewsAPI + RSS
    - XScanner: X/Twitter social signal scanner
    - YouTubeIntel: Video transcript extraction via yt-dlp + Whisper
    - CatalystTracker: Event calendar correlation engine
    - LLMThemeExtractor: Theme synthesis from raw intel
"""

from world_intel.sensorium import (
    WorldIntelSensorium,
    NewsAggregator,
    XScanner,
    YouTubeIntel,
    CatalystTracker,
    LLMThemeExtractor,
)

__all__ = [
    "WorldIntelSensorium",
    "NewsAggregator",
    "XScanner",
    "YouTubeIntel",
    "CatalystTracker",
    "LLMThemeExtractor",
]
