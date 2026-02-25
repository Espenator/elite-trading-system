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
import os
import sys
import json
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta

# ── Configuration ───────────────────────────────────────────────────────────────────────────────
DISCORD_USER_TOKEN = os.getenv('DISCORD_USER_TOKEN', '')

if not DISCORD_USER_TOKEN:
    print('=' * 60)
    print('ERROR: DISCORD_USER_TOKEN secret is not set!')
    print('=' * 60)
    print()
    print('HOW TO GET YOUR TOKEN:')
    print('  1. Open Discord in your browser (discord.com)')
    print('  2. Press F12 to open DevTools')
    print('  3. Click the "Network" tab')
    print('  4. Send any message in any channel')
    print('  5. Find a request to discord.com/api/')
    print('  6. In the request headers, find "Authorization"')
    print('  7. Copy that value (starts with your token)')
    print()
    print('HOW TO ADD TO GITHUB:')
    print('  1. Go to: github.com/Espenator/openclaw/settings/secrets/actions/new')
    print('  2. Name: DISCORD_USER_TOKEN')
    print('  3. Value: paste your token')
    print('  4. Click "Add secret"')
    print()
    sys.exit(1)

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
                print(f'[ERROR] 401 Unauthorized on channel {channel_id} - token may be invalid or expired')
                return []
            elif resp.status == 403:
                print(f'[SKIP] 403 Forbidden on channel {channel_id} - no access')
                return []
            elif resp.status == 429:
                retry_after = (await resp.json()).get('retry_after', 5)
                print(f'[RATELIMIT] Waiting {retry_after}s...')
                await asyncio.sleep(float(retry_after))
                return []
            else:
                print(f'[ERROR] HTTP {resp.status} on channel {channel_id}')
                return []
    except Exception as e:
        print(f'[ERROR] Fetching channel {channel_id}: {e}')
        return []


async def send_to_slack(session: aiohttp.ClientSession, webhook_url: str, message: dict,
                        channel_name: str, source_type: str) -> bool:
    """Forward a Discord message to a Slack webhook."""
    if not webhook_url:
        print(f'[WARN] No Slack webhook configured for source type "{source_type}"')
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
                print(f'[SENT] {channel_name} | {username}: {full_text[:80]}...')
                return True
            else:
                print(f'[ERROR] Slack webhook returned {resp.status}')
                return False
    except Exception as e:
        print(f'[ERROR] Sending to Slack: {e}')
        return False


async def run_batch():
    """Batch mode: fetch all channels once and post new messages to Slack."""
    lookback = datetime.now(timezone.utc) - timedelta(minutes=BATCH_LOOKBACK_MINS)
    after_snowflake = snowflake_from_time(lookback)
    print(f'[BATCH] Looking back {BATCH_LOOKBACK_MINS} minutes from {lookback.strftime("%H:%M UTC")}')
    print(f'[BATCH] Monitoring {len(MONITORED_CHANNELS)} channels')

    total_sent = 0
    async with aiohttp.ClientSession() as session:
        for channel_id, (channel_name, source_type) in MONITORED_CHANNELS.items():
            messages = await fetch_messages(session, channel_id, after_snowflake)
            if messages:
                print(f'[{channel_name}] Found {len(messages)} new message(s)')
                # Discord returns newest first - reverse for chronological order
                for msg in reversed(messages):
                    webhook_url = WEBHOOK_MAP.get(source_type, '')
                    sent = await send_to_slack(session, webhook_url, msg, channel_name, source_type)
                    if sent:
                        total_sent += 1
                    await asyncio.sleep(0.3)  # Rate limit protection
            else:
                print(f'[{channel_name}] No new messages')
            await asyncio.sleep(0.5)  # Between channels

    print(f'[DONE] Sent {total_sent} messages to Slack')


async def run_continuous():
    """Continuous mode: poll every 30 seconds."""
    print('[CONTINUOUS] Starting Discord monitor loop (30s interval)')
    while True:
        await run_batch()
        print('[SLEEP] Waiting 30 seconds...')
        await asyncio.sleep(30)


if __name__ == '__main__':
    print(f'[START] OpenClaw Discord Listener | Mode: {RUN_MODE}')
    print(f'[CONFIG] Channels: {len(MONITORED_CHANNELS)} | Lookback: {BATCH_LOOKBACK_MINS}min')
    if RUN_MODE == 'batch':
        asyncio.run(run_batch())
    else:
        asyncio.run(run_continuous())
