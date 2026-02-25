#!/usr/bin/env python3
"""
TradingView Session Cookie Refresh for OpenClaw

Validates existing TV_SESSION_ID cookies.
Login via API is DISABLED because TradingView blocks it with CAPTCHA
and the single-session limit on Premium disconnects the browser.

Session cookies must be updated manually in GitHub Secrets
when they expire (grab sessionid from browser DevTools).
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)


def refresh_session_cookies():
    """
    API login is disabled - TradingView blocks with CAPTCHA and
    single-session Premium accounts get disconnected.
    Returns None; existing TV_SESSION_ID from secrets is used as-is.
    """
    logger.info('TV session refresh: API login disabled (CAPTCHA + single-session limit)')
    logger.info('Using existing TV_SESSION_ID from secrets if available')
    existing = os.getenv('TV_SESSION_ID', '')
    if existing:
        logger.info(f'TV_SESSION_ID present: {existing[:8]}...')
    else:
        logger.warning('TV_SESSION_ID not set in secrets')
    return None


def ensure_session():
    """
    Ensure we have valid TradingView session cookies.
    Strategy:
      1. If TV_SESSION_ID is set, validate it
      2. If valid, return True
      3. If not set or invalid, log warning and return based on presence
      4. NO fresh login attempt (disabled)
    """
    existing_session = os.getenv('TV_SESSION_ID', '')

    if existing_session:
        if _validate_session(existing_session, os.getenv('TV_SESSION_ID_SIGN', '')):
            logger.info('Existing TradingView session is valid')
            return True
        else:
            logger.warning('TV_SESSION_ID present but validation failed (may be expired)')
            logger.info('Using unvalidated TV_SESSION_ID from secrets')
            return True  # Still try - might work for some endpoints

    logger.warning('No TV_SESSION_ID available - TV watchlist updates will be skipped')
    return False


def _validate_session(session_id, session_id_sign=''):
    """
    Validate a TradingView session by checking the user endpoint.
    Returns True if session is valid, False otherwise.
    """
    cookie = f'sessionid={session_id}'
    if session_id_sign:
        cookie += f'; sessionid_sign={session_id_sign}'

    headers = {
        'cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    try:
        resp = requests.get(
            'https://www.tradingview.com/accounts/signin/status/',
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get('username'):
                logger.info(f'Session valid for user: {data["username"]}')
                return True
        return False
    except Exception:
        return False
