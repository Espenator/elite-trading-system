"""DiscordSwarmBridge — monitors Discord channels and triggers swarm analysis.

Enhances the existing discord_listener.py by:
  1. Parsing trading signals from Discord messages (Unusual Whales, FOM, Maverick)
  2. Extracting symbols, direction, and trade parameters
  3. Triggering SwarmSpawner analysis for each meaningful signal
  4. Running as a background task within the main FastAPI process

This bridge connects Discord trading communities directly to the
agent swarm pipeline, so ideas from Discord channels you follow
automatically spawn analysis swarms.

Usage:
    bridge = DiscordSwarmBridge(message_bus)
    await bridge.start()  # Starts polling Discord channels
"""
import asyncio
import logging
import os
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set

import aiohttp

logger = logging.getLogger(__name__)

# Discord API config
DISCORD_API = "https://discord.com/api/v10"

# Channel configuration — same channels as discord_listener.py
# Users can add more channels via the API
DEFAULT_CHANNELS = {
    # Unusual Whales
    1186354600622694400: {"name": "UW-free-options-flow", "source": "unusual_whales", "type": "flow"},
    1187484002844680354: {"name": "UW-live-options-flow", "source": "unusual_whales", "type": "flow"},
    # Figuring Out Money (FOM)
    850211054549860352:  {"name": "FOM-trade-ideas", "source": "fom", "type": "trade_idea"},
    1097299537758003201: {"name": "FOM-daily-expected-moves", "source": "fom", "type": "analysis"},
    998705346882595840:  {"name": "FOM-zones", "source": "fom", "type": "levels"},
    1430213250645102602: {"name": "FOM-daily-ivol-alerts", "source": "fom", "type": "alert"},
    # Maverick Of Wall Street
    1051968098506379265: {"name": "Maverick-live-market-trading", "source": "maverick", "type": "trade_idea"},
}

# Ticker extraction pattern
_TICKER_RE = re.compile(r'(?<!\w)\$([A-Z]{1,5})(?!\w)')
_TICKER_RE_NO_DOLLAR = re.compile(r'\b([A-Z]{2,5})\b')

# Non-tickers to filter
_SKIP_WORDS = {
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "NEW",
    "NOW", "GET", "HIT", "RUN", "SET", "TOP", "WIN", "BIG", "MAY", "USD",
    "OTM", "ITM", "ATM", "EOD", "ATH", "ATL", "IMO", "LMAO", "ETF", "IPO",
    "CEO", "CFO", "SEC", "FDA", "GDP", "CPI", "FED", "NFT", "PUT", "CALL",
    "BUY", "SELL", "LONG", "SHORT", "FREE", "LIVE", "FLOW", "ALERT",
}


class DiscordSwarmBridge:
    """Monitors Discord channels and spawns analysis swarms from signals."""

    def __init__(self, message_bus=None, on_signal=None, publish_to_bus=True):
        self._bus = message_bus
        self._on_signal_callback = on_signal
        self._publish_to_bus = publish_to_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._token = os.getenv("DISCORD_USER_TOKEN", "")
        self._channels = dict(DEFAULT_CHANNELS)
        self._seen_message_ids: Set[str] = set()
        self._poll_interval = int(os.getenv("DISCORD_POLL_INTERVAL", "60"))
        self._lookback_mins = int(os.getenv("DISCORD_LOOKBACK_MINS", "10"))
        self._stats = {
            "polls": 0,
            "messages_processed": 0,
            "swarms_triggered": 0,
            "errors": 0,
        }
        # User-added channels
        self._load_custom_channels()

    async def start(self):
        """Start the Discord polling loop."""
        if not self._token:
            logger.info("DiscordSwarmBridge: no DISCORD_USER_TOKEN set, skipping")
            return
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(
            "DiscordSwarmBridge started: %d channels, %ds interval",
            len(self._channels), self._poll_interval,
        )

    async def stop(self):
        """Stop the polling loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("DiscordSwarmBridge stopped")

    def add_channel(self, channel_id: int, name: str, source: str = "custom", msg_type: str = "trade_idea"):
        """Add a Discord channel to monitor."""
        self._channels[channel_id] = {"name": name, "source": source, "type": msg_type}
        self._save_custom_channels()
        logger.info("Added Discord channel: %s (%d)", name, channel_id)

    def remove_channel(self, channel_id: int):
        """Remove a Discord channel from monitoring."""
        self._channels.pop(channel_id, None)
        self._save_custom_channels()

    def list_channels(self) -> List[Dict[str, Any]]:
        """List all monitored channels."""
        return [
            {"id": cid, **info}
            for cid, info in self._channels.items()
        ]

    # ------------------------------------------------------------------
    # Polling loop
    # ------------------------------------------------------------------
    async def _poll_loop(self):
        """Main polling loop."""
        await asyncio.sleep(15)  # Initial delay
        while self._running:
            try:
                await self._poll_all_channels()
                self._stats["polls"] += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._stats["errors"] += 1
                logger.warning("Discord poll error: %s", e)
            await asyncio.sleep(self._poll_interval)

    async def _poll_all_channels(self):
        """Poll all monitored channels for new messages."""
        lookback = datetime.now(timezone.utc) - timedelta(minutes=self._lookback_mins)
        after_snowflake = self._snowflake_from_time(lookback)

        headers = {
            "Authorization": self._token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }

        async with aiohttp.ClientSession() as session:
            for channel_id, channel_info in self._channels.items():
                try:
                    messages = await self._fetch_messages(
                        session, headers, channel_id, after_snowflake
                    )
                    for msg in messages:
                        msg_id = str(msg.get("id", ""))
                        if msg_id in self._seen_message_ids:
                            continue
                        self._seen_message_ids.add(msg_id)

                        # Process and potentially trigger swarm
                        await self._process_message(msg, channel_info)
                        self._stats["messages_processed"] += 1

                    # Trim seen messages to prevent memory growth
                    if len(self._seen_message_ids) > 5000:
                        self._seen_message_ids = set(list(self._seen_message_ids)[-2000:])

                except Exception as e:
                    logger.debug("Error polling channel %s: %s", channel_info["name"], e)

                await asyncio.sleep(0.5)  # Rate limit protection

    async def _fetch_messages(
        self, session: aiohttp.ClientSession, headers: dict,
        channel_id: int, after_snowflake: int,
    ) -> List[dict]:
        """Fetch messages from a Discord channel."""
        url = f"{DISCORD_API}/channels/{channel_id}/messages"
        params = {"after": str(after_snowflake), "limit": 20}
        try:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 429:
                    retry = (await resp.json()).get("retry_after", 5)
                    await asyncio.sleep(float(retry))
                elif resp.status in (401, 403):
                    logger.debug("Access denied to channel %d (status=%d)", channel_id, resp.status)
                return []
        except Exception as e:
            logger.debug("Fetch error for channel %d: %s", channel_id, e)
            return []

    # ------------------------------------------------------------------
    # Message processing
    # ------------------------------------------------------------------
    async def _process_message(self, msg: dict, channel_info: dict):
        """Parse a Discord message and trigger swarm if it contains trading signals."""
        content = msg.get("content", "")

        # Also extract text from embeds
        for embed in msg.get("embeds", []):
            if embed.get("title"):
                content += f" {embed['title']}"
            if embed.get("description"):
                content += f" {embed['description']}"
            for field in embed.get("fields", []):
                content += f" {field.get('name', '')} {field.get('value', '')}"

        if not content.strip():
            return

        # Extract symbols
        symbols = self._extract_symbols(content)
        if not symbols:
            return  # No actionable tickers found

        # Detect direction
        direction = self._detect_direction(content, channel_info)

        # Build reasoning
        author = msg.get("author", {})
        username = author.get("global_name") or author.get("username", "Unknown")
        reasoning = (
            f"Discord [{channel_info['name']}] by {username}: "
            f"{content[:300]}"
        )

        # Trigger swarm
        await self._trigger_swarm(
            symbols=symbols[:3],  # Cap at 3 symbols per message
            direction=direction,
            reasoning=reasoning,
            raw_content=content[:2000],
            channel=channel_info["name"],
            source_type=channel_info["source"],
        )

    def _extract_symbols(self, text: str) -> List[str]:
        """Extract ticker symbols from Discord message text."""
        # First try $TICKER pattern (most reliable)
        dollar_tickers = _TICKER_RE.findall(text)

        # Then try plain uppercase words if no dollar tickers found
        if not dollar_tickers:
            words = _TICKER_RE_NO_DOLLAR.findall(text)
            dollar_tickers = [w for w in words if w not in _SKIP_WORDS and len(w) <= 5]

        # Deduplicate and filter
        seen = set()
        result = []
        for t in dollar_tickers:
            upper = t.upper()
            if upper not in seen and upper not in _SKIP_WORDS:
                seen.add(upper)
                result.append(upper)
        return result[:5]

    def _detect_direction(self, text: str, channel_info: dict) -> str:
        """Detect trading direction from message content."""
        lower = text.lower()

        bull_score = 0
        bear_score = 0

        bull_words = ["bullish", "calls", "long", "buy", "breakout", "moon", "ripping", "squeeze"]
        bear_words = ["bearish", "puts", "short", "sell", "breakdown", "crash", "dumping", "fade"]

        for w in bull_words:
            if w in lower:
                bull_score += 1
        for w in bear_words:
            if w in lower:
                bear_score += 1

        # Channel-specific biases
        if channel_info["type"] == "flow":
            if "call" in lower and "sweep" in lower:
                bull_score += 2
            elif "put" in lower and "sweep" in lower:
                bear_score += 2

        if bull_score > bear_score:
            return "bullish"
        elif bear_score > bull_score:
            return "bearish"
        return "unknown"

    async def _trigger_swarm(
        self,
        symbols: List[str],
        direction: str,
        reasoning: str,
        raw_content: str,
        channel: str,
        source_type: str,
    ):
        """Trigger a swarm analysis from a Discord signal."""
        self._stats["swarms_triggered"] += 1

        payload = {
            "source": "discord",
            "symbols": symbols,
            "direction": direction,
            "reasoning": reasoning,
            "raw_content": raw_content,
            "metadata": {
                "channel": channel,
                "source_type": source_type,
            },
            "priority": 4,
        }

        # Route through callback if set (DiscordChannelAgent mode)
        if self._on_signal_callback:
            try:
                await self._on_signal_callback(payload)
            except Exception as e:
                logger.warning("Discord on_signal callback failed: %s", e)
            if not self._publish_to_bus:
                return

        if self._bus:
            await self._bus.publish("swarm.idea", payload)
        else:
            try:
                from app.services.swarm_spawner import get_swarm_spawner, SwarmIdea
                spawner = get_swarm_spawner()
                await spawner.spawn_analysis(SwarmIdea(
                    source="discord",
                    symbols=symbols,
                    direction=direction,
                    reasoning=reasoning,
                    raw_content=raw_content,
                    metadata={"channel": channel, "source_type": source_type},
                    priority=4,
                ))
            except Exception as e:
                logger.warning("Failed to trigger swarm from Discord: %s", e)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load_custom_channels(self):
        """Load user-added channels from storage."""
        try:
            from app.services.database import db_service
            custom = db_service.get_config("discord_custom_channels")
            if isinstance(custom, dict):
                for cid_str, info in custom.items():
                    self._channels[int(cid_str)] = info
        except Exception:
            pass

    def _save_custom_channels(self):
        """Save user-added channels (only non-default ones)."""
        try:
            from app.services.database import db_service
            custom = {}
            for cid, info in self._channels.items():
                if cid not in DEFAULT_CHANNELS:
                    custom[str(cid)] = info
            db_service.set_config("discord_custom_channels", custom)
        except Exception as e:
            logger.warning("Failed to save custom channels: %s", e)

    @staticmethod
    def _snowflake_from_time(dt: datetime) -> int:
        """Convert datetime to Discord snowflake ID."""
        discord_epoch = 1420070400000
        ms = int(dt.timestamp() * 1000)
        return (ms - discord_epoch) << 22

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "token_configured": bool(self._token),
            "channels": len(self._channels),
            "channel_list": self.list_channels(),
            "poll_interval": self._poll_interval,
            "stats": dict(self._stats),
        }


# Module-level singleton
_bridge: Optional[DiscordSwarmBridge] = None


def get_discord_bridge() -> DiscordSwarmBridge:
    global _bridge
    if _bridge is None:
        _bridge = DiscordSwarmBridge()
    return _bridge
