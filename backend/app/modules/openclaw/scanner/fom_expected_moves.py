#!/usr/bin/env python3
"""
FOM Expected Moves - Discord Scraper & TradingView Formatter
Scrapes the FOM #daily-expected-moves Discord channel,
parses the expected move levels, and outputs the paste-ready
string for the TradingView FOM Expected Move Levels indicator.

Pipeline:
  1. Fetch latest messages from FOM #daily-expected-moves via Discord API
  2. Parse the TV-formatted code block (TICKER,1sig Up,1sig Dn,2sig Up,2sig Dn;)
  3. Post formatted string to Slack #oc-trade-desk for easy copy-paste
  4. Optionally extract individual ticker levels for programmatic use

Format expected by TradingView indicator:
  TICKER,1σ Up,1σ Dn,2σ Up,2σ Dn;
  Example: SPY,688.38,677.32,693.91,671.79;
"""
import os
import re
import json
import logging
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta, date

logger = logging.getLogger(__name__)

# Discord config
DISCORD_USER_TOKEN = os.getenv('DISCORD_USER_TOKEN', '')
DISCORD_API = 'https://discord.com/api/v10'
FOM_DEM_CHANNEL_ID = 1097299537758003201

# Slack config
SLACK_WEBHOOK_FOM = os.getenv('SLACK_WEBHOOK_FOM', os.getenv('SLACK_WEBHOOK_URL', ''))

HEADERS = {
    'Authorization': DISCORD_USER_TOKEN,
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}


# ── Ticker mapping: futures symbols in Discord -> TradingView symbols ────
FUTURES_MAP = {
    '/ESH26': 'ES1!', '/ESH2026': 'ES1!',
    '/NQH26': 'NQ1!', '/NQH2026': 'NQ1!',
    '/RTYH26': 'RTY1!', '/RTYH2026': 'RTY1!',
    '/GCJ26': 'GC1!', '/GCJ2026': 'GC1!',
    '/CLJ26': 'CL1!', '/CLJ2026': 'CL1!',
    '/BTCG26': 'BTC1!', '/BTCG2026': 'BTC1!',
    '/ZNH26': 'ZN1!', '/ZNH2026': 'ZN1!',
    '/ZBH26': 'ZB1!', '/ZBH2026': 'ZB1!',
}


def snowflake_from_time(dt: datetime) -> int:
    """Convert datetime to Discord snowflake ID."""
    discord_epoch = 1420070400000
    ms = int(dt.timestamp() * 1000)
    return (ms - discord_epoch) << 22


def parse_tv_code_block(text: str) -> dict:
    """
    Parse the TV-formatted code block from Discord message.
    Looks for lines matching: TICKER,num,num,num,num;
    Returns dict of {ticker: {upper_1sig, lower_1sig, upper_2sig, lower_2sig}}
    """
    levels = {}
    # Match lines like: SPX,6897.94,6788.50,6952.66,6733.78;
    # or SPY,688.38,677.32,693.91,671.79;
    pattern = re.compile(
        r'^\s*([A-Z/][A-Z0-9/]*)\s*,\s*'
        r'([\d.]+)\s*,\s*'
        r'([\d.]+)\s*,\s*'
        r'([\d.]+)\s*,\s*'
        r'([\d.]+)\s*;?\s*$',
        re.MULTILINE
    )
    for match in pattern.finditer(text):
        ticker = match.group(1).strip()
        upper_1sig = float(match.group(2))
        lower_1sig = float(match.group(3))
        upper_2sig = float(match.group(4))
        lower_2sig = float(match.group(5))
        levels[ticker] = {
            'ticker': ticker,
            'upper_1sig': upper_1sig,
            'lower_1sig': lower_1sig,
            'upper_2sig': upper_2sig,
            'lower_2sig': lower_2sig,
        }
    return levels


def format_for_tradingview(levels: dict) -> str:
    """
    Format parsed levels into the TradingView indicator paste string.
    Output: TICKER,1sig Up,1sig Dn,2sig Up,2sig Dn;\n per ticker
    """
    lines = []
    for ticker, data in levels.items():
        # Map futures symbols if needed
        tv_ticker = FUTURES_MAP.get(ticker, ticker)
        line = (
            f"{tv_ticker},"
            f"{data['upper_1sig']:.2f},"
            f"{data['lower_1sig']:.2f},"
            f"{data['upper_2sig']:.2f},"
            f"{data['lower_2sig']:.2f};"
        )
        lines.append(line)
    return '\n'.join(lines)


def format_slack_message(tv_string: str, em_date: str, level_count: int) -> str:
    """Build a rich Slack message with the paste-ready TV data."""
    msg = (
        f":chart_with_upwards_trend: *FOM Daily Expected Moves - {em_date}*\n\n"
        f"*{level_count} symbols parsed* | Ready to paste into TradingView indicator\n\n"
        f"```\n{tv_string}\n```\n\n"
        f":point_right: Copy the block above and paste into "
        f"_FOM Expected Move Levels_ indicator settings > *Paste DEM Levels*"
    )
    return msg


async def fetch_latest_em_messages(session: aiohttp.ClientSession,
                                    lookback_hours: int = 24) -> list:
    """Fetch recent messages from the FOM daily-expected-moves channel."""
    lookback = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    after_snowflake = snowflake_from_time(lookback)
    url = f"{DISCORD_API}/channels/{FOM_DEM_CHANNEL_ID}/messages"
    params = {'after': str(after_snowflake), 'limit': 10}
    try:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            if resp.status == 200:
                messages = await resp.json()
                logger.info(f"Fetched {len(messages)} messages from FOM DEM channel")
                return messages
            else:
                logger.error(f"Discord API returned {resp.status}")
                return []
    except Exception as e:
        logger.error(f"Error fetching FOM DEM messages: {e}")
        return []


async def fetch_attachment_text(session: aiohttp.ClientSession, url: str) -> str:
    """Download and return the text content of a Discord attachment."""
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                logger.warning(f"Failed to download attachment: HTTP {resp.status}")
                return ''
    except Exception as e:
        logger.error(f"Error downloading attachment: {e}")
        return ''


async def get_daily_expected_moves(lookback_hours: int = 24) -> dict:
    """
    Main function: fetch FOM DEM data from Discord, parse, return structured data.
    Returns: {
        'date': '2026-02-18',
        'levels': {ticker: {upper_1sig, lower_1sig, upper_2sig, lower_2sig}},
        'tv_string': 'paste-ready string for TradingView',
        'raw_text': 'original message text',
    }
    """
    if not DISCORD_USER_TOKEN:
        logger.error("DISCORD_USER_TOKEN not set - cannot fetch FOM DEM data")
        return {}

    async with aiohttp.ClientSession() as session:
        messages = await fetch_latest_em_messages(session, lookback_hours)

        if not messages:
            logger.warning("No FOM DEM messages found")
            return {}

        # Search messages for TV-formatted data
        # FOM posts: (1) image table, (2) TOS code block, (3) TV code block, (4) attachments
        all_levels = {}
        em_date = ''
        raw_text = ''

        for msg in reversed(messages):  # oldest first
            content = msg.get('content', '')

            # Try to detect date from message
            date_match = re.search(r'Daily EMs for (\d+/\d+)', content)
            if date_match:
                em_date = date_match.group(1)

            # Parse TV-formatted lines directly from message content
            levels = parse_tv_code_block(content)
            if levels:
                all_levels.update(levels)
                raw_text = content
                logger.info(f"Parsed {len(levels)} levels from message content")

            # Also check attachments for TV_FOM_DEM_Data files
            for attachment in msg.get('attachments', []):
                filename = attachment.get('filename', '')
                if 'TV_FOM_DEM' in filename and filename.endswith('.txt'):
                    att_url = attachment.get('url', '')
                    if att_url:
                        att_text = await fetch_attachment_text(session, att_url)
                        if att_text:
                            att_levels = parse_tv_code_block(att_text)
                            if att_levels:
                                all_levels.update(att_levels)
                                raw_text = att_text
                                logger.info(
                                    f"Parsed {len(att_levels)} levels from "
                                    f"attachment {filename}"
                                )

        if not all_levels:
            logger.warning("No expected move levels found in FOM DEM messages")
            return {}

        # Determine date
        if not em_date:
            em_date = date.today().strftime('%m/%d')

        tv_string = format_for_tradingview(all_levels)

        return {
            'date': em_date,
            'levels': all_levels,
            'tv_string': tv_string,
            'raw_text': raw_text,
            'count': len(all_levels),
        }


async def post_em_to_slack(em_data: dict) -> bool:
    """Post the formatted EM data to Slack."""
    if not SLACK_WEBHOOK_FOM:
        logger.warning("No SLACK_WEBHOOK_FOM configured")
        return False

    if not em_data or not em_data.get('tv_string'):
        logger.warning("No EM data to post")
        return False

    slack_msg = format_slack_message(
        em_data['tv_string'],
        em_data['date'],
        em_data['count'],
    )

    async with aiohttp.ClientSession() as session:
        payload = {
            'text': slack_msg,
            'username': 'OpenClaw - FOM Expected Moves',
            'icon_emoji': ':chart_with_upwards_trend:',
        }
        try:
            async with session.post(SLACK_WEBHOOK_FOM, json=payload) as resp:
                if resp.status == 200:
                    logger.info(f"Posted FOM DEM to Slack ({em_data['count']} symbols)")
                    return True
                else:
                    logger.error(f"Slack webhook returned {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Error posting to Slack: {e}")
            return False


def get_ticker_levels(em_data: dict, ticker: str) -> dict:
    """Get expected move levels for a specific ticker."""
    if not em_data or not em_data.get('levels'):
        return {}
    # Check direct match
    levels = em_data['levels']
    if ticker in levels:
        return levels[ticker]
    # Check futures map (reverse lookup)
    for discord_sym, tv_sym in FUTURES_MAP.items():
        if tv_sym == ticker and discord_sym in levels:
            return levels[discord_sym]
    return {}



# ── Per-ticker expected move query (Task 8e) ────────────────────────────

# Cache for FOM data to avoid repeated Discord API calls
_fom_cache = {'data': None, 'timestamp': None}
_FOM_CACHE_TTL_HOURS = int(os.getenv('FOM_CACHE_HOURS', '6'))


def get_expected_move(ticker: str) -> dict:
    """
    Get expected move data for a specific ticker.
    Queries cached FOM data from last Discord scrape.
    Returns {'em_pct': float, 'em_dollars': float, 'last_updated': str}
    Fallback: calculate from ATR if ticker not found in FOM data.
    """
    global _fom_cache

    # Check cache freshness
    now = datetime.now(timezone.utc)
    cache_stale = True
    if _fom_cache['timestamp'] and _fom_cache['data']:
        age_hours = (now - _fom_cache['timestamp']).total_seconds() / 3600
        cache_stale = age_hours > _FOM_CACHE_TTL_HOURS

    # Refresh cache if stale
    if cache_stale:
        try:
            em_data = asyncio.run(get_daily_expected_moves(lookback_hours=48))
            if em_data and em_data.get('levels'):
                _fom_cache['data'] = em_data
                _fom_cache['timestamp'] = now
                logger.info(f"[FOM] Cache refreshed: {em_data.get('count', 0)} symbols")
        except Exception as e:
            logger.warning(f"[FOM] Cache refresh failed: {e}")

    # Also try loading from persisted file (written by daily_scanner bridge)
    if not _fom_cache['data'] or not _fom_cache['data'].get('levels'):
        try:
            cache_path = 'data/fom_cache.json'
            if os.path.exists(cache_path):
                with open(cache_path) as f:
                    cached = json.load(f)
                if cached.get('levels'):
                    _fom_cache['data'] = cached
                    _fom_cache['timestamp'] = now
                    logger.info(f"[FOM] Loaded from file cache: {len(cached['levels'])} symbols")
        except Exception as e:
            logger.debug(f"[FOM] File cache load failed: {e}")

    em_data = _fom_cache.get('data')
    if not em_data or not em_data.get('levels'):
        return {'em_pct': 0, 'em_dollars': 0, 'last_updated': '', 'source': 'none'}

    levels = em_data['levels']
    ticker_upper = ticker.upper()

    # Direct lookup
    entry = levels.get(ticker_upper)

    # Try common ETF/index mappings
    if not entry:
        aliases = {
            'SPY': ['SPX', 'ES1!'], 'QQQ': ['NDX', 'NQ1!'],
            'IWM': ['RUT', 'RTY1!'], 'SPX': ['SPY'],
            'NDX': ['QQQ'], 'RUT': ['IWM'],
        }
        for alias in aliases.get(ticker_upper, []):
            entry = levels.get(alias)
            if entry:
                break

    if not entry:
        return {'em_pct': 0, 'em_dollars': 0, 'last_updated': em_data.get('date', ''), 'source': 'not_found'}

    # Calculate EM percentage from 1-sigma levels
    upper_1 = entry.get('upper_1sig', 0)
    lower_1 = entry.get('lower_1sig', 0)
    if upper_1 and lower_1:
        midpoint = (upper_1 + lower_1) / 2.0
        em_dollars = (upper_1 - lower_1) / 2.0
        em_pct = (em_dollars / midpoint * 100) if midpoint > 0 else 0
    else:
        em_pct = 0
        em_dollars = 0

    return {
        'em_pct': round(em_pct, 2),
        'em_dollars': round(em_dollars, 2),
        'upper_1sig': upper_1,
        'lower_1sig': lower_1,
        'upper_2sig': entry.get('upper_2sig', 0),
        'lower_2sig': entry.get('lower_2sig', 0),
        'last_updated': em_data.get('date', ''),
        'source': 'fom_discord',
    }

# ── Synchronous wrappers for use in daily_scanner.py ─────────────────────

def run_fom_em_scrape(lookback_hours: int = 24) -> dict:
    """Synchronous wrapper to fetch and parse FOM expected moves."""
    return asyncio.run(get_daily_expected_moves(lookback_hours))


def run_fom_em_post(em_data: dict) -> bool:
    """Synchronous wrapper to post EM data to Slack."""
    return asyncio.run(post_em_to_slack(em_data))


# ── CLI entry point ──────────────────────────────────────────────────────

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("[FOM-EM] Fetching daily expected moves from Discord...")

    em_data = run_fom_em_scrape(lookback_hours=48)

    if em_data and em_data.get('tv_string'):
        print(f"\n[FOM-EM] Date: {em_data['date']}")
        print(f"[FOM-EM] Symbols: {em_data['count']}")
        print(f"\n{'='*60}")
        print("PASTE INTO TRADINGVIEW INDICATOR:")
        print(f"{'='*60}")
        print(em_data['tv_string'])
        print(f"{'='*60}\n")

        # Post to Slack if webhook is configured
        if SLACK_WEBHOOK_FOM:
            print("[FOM-EM] Posting to Slack...")
            success = run_fom_em_post(em_data)
            print(f"[FOM-EM] Slack post: {'OK' if success else 'FAILED'}")
        else:
            print("[FOM-EM] No SLACK_WEBHOOK_FOM set - skipping Slack post")
    else:
        print("[FOM-EM] No expected move data found")
