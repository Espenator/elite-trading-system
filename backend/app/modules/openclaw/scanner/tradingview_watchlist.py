#!/usr/bin/env python3
"""
TradingView Watchlist Manager for OpenClaw
Uses TradingView's internal API to manage watchlist symbols.
Automatically refreshes session cookies via tv_session_refresh.
"""
import os
import logging
import requests
from datetime import date

logger = logging.getLogger(__name__)

TV_BASE_URL = 'https://www.tradingview.com'


class TVWatchlistManager:
    """Manages TradingView watchlist via internal API."""

    def __init__(self):
        self.session_id = os.getenv('TV_SESSION_ID', '')
        self.session_id_sign = os.getenv('TV_SESSION_ID_SIGN', '')
        self.watchlist_id = os.getenv('TV_WATCHLIST_ID', '')
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'origin': TV_BASE_URL,
            'x-requested-with': 'XMLHttpRequest',
        }
        self._setup_cookies()

    def _setup_cookies(self):
        """Set up cookie header from current env vars."""
        self.session_id = os.getenv('TV_SESSION_ID', '')
        self.session_id_sign = os.getenv('TV_SESSION_ID_SIGN', '')
        if self.session_id:
            cookie = f'sessionid={self.session_id}'
            if self.session_id_sign:
                cookie += f'; sessionid_sign={self.session_id_sign}'
            self.headers['cookie'] = cookie

    def _ensure_session(self):
        """Try to refresh session if needed before API calls."""
        try:
            from tv_session_refresh import ensure_session
            if ensure_session():
                self._setup_cookies()
                return True
        except ImportError:
            logger.debug('tv_session_refresh not available')
        except Exception as e:
            logger.warning(f'Session refresh error: {e}')
        return bool(self.session_id)

    def is_configured(self):
        """Check if TV credentials are set."""
        return bool(self.session_id and self.watchlist_id)

    def get_watchlist(self):
        """Get current symbols in the watchlist."""
        if not self.is_configured():
            self._ensure_session()
        if not self.is_configured():
            logger.warning('TradingView not configured - missing TV_SESSION_ID or TV_WATCHLIST_ID')
            return []
        url = f'{TV_BASE_URL}/api/v1/symbols_list/custom/{self.watchlist_id}'
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            symbols = data.get('symbols', [])
            logger.info(f'TV watchlist {self.watchlist_id}: {len(symbols)} symbols')
            return symbols
        except Exception as e:
            logger.error(f'Failed to get TV watchlist: {e}')
            return []

    def replace_watchlist(self, symbols):
        """Replace entire watchlist with new symbols."""
        if not self.is_configured():
            self._ensure_session()
        if not self.is_configured():
            logger.warning('TradingView not configured - skipping watchlist update')
            return False
        url = f'{TV_BASE_URL}/api/v1/symbols_list/custom/{self.watchlist_id}/replace/?unsafe=true'
        try:
            resp = requests.post(url, json=symbols, headers=self.headers, timeout=15)
            resp.raise_for_status()
            logger.info(f'TV watchlist replaced: {len(symbols)} symbols')
            return True
        except Exception as e:
            logger.error(f'Failed to replace TV watchlist: {e}')
            return False

    def append_to_watchlist(self, symbols):
        """Append symbols to existing watchlist."""
        if not self.is_configured():
            self._ensure_session()
        if not self.is_configured():
            logger.warning('TradingView not configured - skipping watchlist append')
            return False
        url = f'{TV_BASE_URL}/api/v1/symbols_list/custom/{self.watchlist_id}/append/'
        try:
            resp = requests.post(url, json=symbols, headers=self.headers, timeout=15)
            resp.raise_for_status()
            logger.info(f'TV watchlist appended: {len(symbols)} symbols')
            return True
        except Exception as e:
            logger.error(f'Failed to append to TV watchlist: {e}')
            return False

    def update_daily_watchlist(self, watchlist_items):
        """
        Update the TradingView watchlist with daily scan results.
                Organizes by composite score tier: SLAM(80+) > HIGH(65+) > TRADEABLE(55+) > WATCH(40+).
        Falls back to source tier if no scores available.
        """
        if not self.is_configured():
            self._ensure_session()
        if not self.is_configured():
            logger.info('TradingView not configured - skipping daily watchlist update')
            return False

        today = date.today().strftime('%b %d')
        symbols = []

        # Check if composite scores are available
        has_scores = any(
            w.get('composite_score', 0) > 0 for w in watchlist_items
        )

        if has_scores:
            # Score-based sections (v3.0)
            slams = [
                w['ticker'] for w in watchlist_items
                if w.get('composite_score', 0) >= 80
            ]
            highs = [
                w['ticker'] for w in watchlist_items
                if 65 <= w.get('composite_score', 0) < 80
            ]
            trades = [
                w['ticker'] for w in watchlist_items
                if 55 <= w.get('composite_score', 0) < 65
            ]
            watch = [
                w['ticker'] for w in watchlist_items
                if 40 <= w.get('composite_score', 0) < 55
            ]

            if slams:
                symbols.append(f'###SLAM TRADES {today}')
                symbols.extend([f'NYSE:{t}' if ':' not in t else t for t in slams])
            if highs:
                symbols.append(f'###HIGH CONVICTION {today}')
                symbols.extend([f'NYSE:{t}' if ':' not in t else t for t in highs])
            if trades:
                symbols.append(f'###TRADEABLE {today}')
                symbols.extend([f'NYSE:{t}' if ':' not in t else t for t in trades])
            if watch:
                symbols.append(f'###WATCHLIST {today}')
                symbols.extend([f'NYSE:{t}' if ':' not in t else t for t in watch])
        else:
            # Fallback: source tier sections
            tier1 = [w['ticker'] for w in watchlist_items if w.get('tier') == 1]
            tier2 = [w['ticker'] for w in watchlist_items if w.get('tier') == 2]
            tier3 = [w['ticker'] for w in watchlist_items if w.get('tier') == 3]

            if tier1:
                symbols.append(f'###T1 CONFLUENCE {today}')
                symbols.extend([f'NYSE:{t}' if ':' not in t else t for t in tier1])
            if tier2:
                symbols.append(f'###T2 FINVIZ {today}')
                symbols.extend([f'NYSE:{t}' if ':' not in t else t for t in tier2])
            if tier3:
                symbols.append(f'###T3 WHALE {today}')
                symbols.extend([f'NYSE:{t}' if ':' not in t else t for t in tier3])

        if not symbols:
            logger.warning('No symbols to update in TV watchlist')
            return False

        success = self.replace_watchlist(symbols)
        if success:
            logger.info(
                f'TV daily watchlist updated: {len(symbols)} items '
                f'({"scored" if has_scores else "tier-based"})'
            )
        return success


# Module-level instance for convenience
tv_watchlist = TVWatchlistManager()
