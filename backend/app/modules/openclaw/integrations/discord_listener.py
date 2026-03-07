"""Discord Listener for OpenClaw Trading Automation
Monitors Discord channels and forwards trading signals to Slack.
Modes:
 - continuous: Polls every 30s in a loop (local/server use)
 - batch: Polls once and exits (GitHub Actions / cron jobs)
Slack routing:
 UW channels  -> SLACK_WEBHOOK_UW (or fallback SLACK_WEBHOOK_URL) -> #oc-whale-flow
 FOM channels -> SLACK_WEBHOOK_FOM (or fallback SLACK_WEBHOOK_URL) -> #oc-signals-raw
 Maverick     -> SLACK_WEBHOOK_MAV (or fallback SLACK_WEBHOOK_URL) -> #oc-signals-raw
"""
import logging
import os
import sys
import json
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────────────────────────────────────
DISCORD_USER_TOKEN = os.getenv('DISCORD_USER_TOKEN', '')

if not DISCORD_USER_TOKEN:
    logger.error(
        "DISCORD_USER_TOKEN secret is not set! "
        "HOW TO GET YOUR TOKEN: "
        "1. Open Discord in your browser (discord.com) "
        "2. Press F12 to open DevTools "
        "3. Click the 'Network' tab "
        "4. Send any message in any channel "
        "5. Find a request to discord.com/api/ "
        "6. In the request headers, find 'Authorization' "
        "7. Copy that value (starts with your token). "
        "HOW TO ADD TO GITHUB: "
        "1. Go to: github.com/Espenator/openclaw/settings/secrets/actions/new "
        "2. Name: DISCORD_USER_TOKEN "
        "3. Value: paste your token "
        "4. Click 'Add secret'"
    )
    # Don't crash on import — just flag as disabled
    _DISCORD_ENABLED = False
else:
    _DISCORD_ENABLED = True

# Slack webhooks - per source routing, fallback to generic
SLACK_WEBHOOK_UW  = os.getenv('SLACK_WEBHOOK_UW',  os.getenv('SLACK_WEBHOOK_URL', ''))
SLACK_WEBHOOK_FOM = os.getenv('SLACK_WEBHOOK_FOM', os.getenv('SLACK_WEBHOOK_URL', ''))
SLACK_WEBHOOK_MAV = os.getenv('SLACK_WEBHOOK_MAV', os.getenv('SLACK_WEBHOOK_URL', ''))

RUN_MODE = os.getenv('RUN_MODE', 'continuous')  # 'batch' or 'continuous'
BATCH_LOOKBACK_MINS = int(os.getenv('BATCH_LOOKBACK_MINS', '20'))

# Channel IDs to monitor, with Slack webhook routing
MONITORED_CHANNELS = {
    # Unusual Whales
    1186354600622694400: ('UW-free-options-flow', 'uw'),
    1187484002844680354: ('UW-live-options-flow', 'uw'),
    # Figuring Out Money (FOM)
    850211054549860352:  ('FOM-trade-ideas', 'fom'),
    1097299537758003201: ('FOM-daily-expected-moves', 'fom'),
    998705356882595840:  ('FOM-zones', 'fom'),
    1430213250645102602: ('FOM-daily-ivol-alerts', 'fom'),
    # Maverick Of Wall Street
    1051968098506379265: ('Maverick-live-market-trading', 'mav'),
}

DISCORD_API = 'https://discord.com/api/v10'

WEBHOOK_MAP = {
    'uw':  SLACK_WEBHOOK_UW,
    'fom': SLACK_WEBHOOK_FOM,
    'mav': SLACK_WEBHOOK_MAV,
}

HEADERS = {
    'Authorization': DISCORD_USER_TOKEN,
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}


def snowflake_from_time(dt: datetime) -> int:
    """Convert datetime to Discord snowflake ID for message history lookup."""
    discord_epoch = 1420070400000
    ms = int(dt.timestamp() * 1000)
    return (ms - discord_epoch) << 22


async def fetch_messages(session: aiohttp.ClientSession, channel_id: int, after_snowflake: int) -> list:
    """Fetch messages from a Discord channel after a given snowflake ID."""
    url = f"{DISCORD_API}/channels/{channel_id}/messages"
    params = {'after': str(after_snowflake), 'limit': 50}
    try:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            elif resp.status == 401:
                logger.error('401 Unauthorized on channel %s - token may be invalid or expired', channel_id)
                return []
            elif resp.status == 403:
                logger.warning('403 Forbidden on channel %s - no access', channel_id)
                return []
            elif resp.status == 429:
                retry_after = (await resp.json()).get('retry_after', 5)
                logger.warning('Rate limited, waiting %ss...', retry_after)
                await asyncio.sleep(float(retry_after))
                return []
            else:
                logger.error('HTTP %s on channel %s', resp.status, channel_id)
                return []
    except Exception as e:
        logger.error('Fetching channel %s: %s', channel_id, e)
        return []


async def send_to_slack(session: aiohttp.ClientSession, webhook_url: str, message: dict,
                        channel_name: str, source_type: str) -> bool:
    """Forward a Discord message to a Slack webhook."""
    if not webhook_url:
        logger.warning('No Slack webhook configured for source type "%s"', source_type)
        return False

    author = message.get('author', {})
    username = author.get('global_name') or author.get('username', 'Unknown')
    content = message.get('content', '')
    timestamp = message.get('timestamp', '')

    # Build embeds text
    embed_texts = []
    for embed in message.get('embeds', []):
        parts = []
        if embed.get('title'):
            parts.append(f"*{embed['title']}*")
        if embed.get('description'):
            parts.append(embed['description'])
        for field in embed.get('fields', []):
            parts.append(f"*{field.get('name', '')}*: {field.get('value', '')}")
        embed_texts.append('\n'.join(parts))

    full_text = content
    if embed_texts:
        full_text = (content + '\n' + '\n---\n'.join(embed_texts)).strip()

    if not full_text.strip():
        return False  # Skip empty messages

    slack_payload = {
        'text': f'*[{channel_name}]* {username}: {full_text[:2000]}',
        'username': f'Discord - {channel_name}',
        'icon_emoji': ':speech_balloon:',
    }
    try:
        async with session.post(webhook_url, json=slack_payload) as resp:
            if resp.status == 200:
                logger.info('[SENT] %s | %s: %s...', channel_name, username, full_text[:80])
                return True
            else:
                logger.error('Slack webhook returned %s', resp.status)
                return False
    except Exception as e:
        logger.error('Sending to Slack: %s', e)
        return False


async def run_batch():
    """Batch mode: fetch all channels once and post new messages to Slack."""
    lookback = datetime.now(timezone.utc) - timedelta(minutes=BATCH_LOOKBACK_MINS)
    after_snowflake = snowflake_from_time(lookback)
    logger.info('[BATCH] Looking back %d minutes from %s', BATCH_LOOKBACK_MINS, lookback.strftime("%H:%M UTC"))
    logger.info('[BATCH] Monitoring %d channels', len(MONITORED_CHANNELS))

    total_sent = 0
    async with aiohttp.ClientSession() as session:
        for channel_id, (channel_name, source_type) in MONITORED_CHANNELS.items():
            messages = await fetch_messages(session, channel_id, after_snowflake)
            if messages:
                logger.info('[%s] Found %d new message(s)', channel_name, len(messages))
                # Discord returns newest first - reverse for chronological order
                for msg in reversed(messages):
                    webhook_url = WEBHOOK_MAP.get(source_type, '')
                    sent = await send_to_slack(session, webhook_url, msg, channel_name, source_type)
                    if sent:
                        total_sent += 1
                    await asyncio.sleep(0.3)  # Rate limit protection
            else:
                logger.info('[%s] No new messages', channel_name)
            await asyncio.sleep(0.5)  # Between channels

    logger.info('[DONE] Sent %d messages to Slack', total_sent)


async def run_continuous():
    """Continuous mode: poll every 30 seconds."""
    logger.info('[CONTINUOUS] Starting Discord monitor loop (30s interval)')
    while True:
        await run_batch()
        logger.info('[SLEEP] Waiting 30 seconds...')
        await asyncio.sleep(30)


if __name__ == '__main__':
    print(f'[START] OpenClaw Discord Listener | Mode: {RUN_MODE}')
    print(f'[CONFIG] Channels: {len(MONITORED_CHANNELS)} | Lookback: {BATCH_LOOKBACK_MINS}min')
    if RUN_MODE == 'batch':
        asyncio.run(run_batch())
    else:
        asyncio.run(run_continuous())
