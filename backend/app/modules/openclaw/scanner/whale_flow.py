#!/usr/bin/env python3
"""
Whale Flow Module for OpenClaw v5.0 - Tier 1 Data Publisher

Monitors Unusual Whales API for large options flow.
Filters for high-conviction institutional trades that align with PAS v8 setups.

Swarm Integration:
  - Publishes WHALE_SIGNALS to the Blackboard for Tier 2 scoring
  - Async polling with configurable intervals
  - Rate limiting and retry logic for API resilience
  - Memory integration: tracks which flow signals led to profits
  - Robust imports with try/except fallbacks

Fixes from v2.1:
  - DTE now calculated from expiry date (was hardcoded 0)
  - OI ratio filter actually applied (was defined but never used)
  - Result caching with 10-min TTL to avoid hammering API
  - Safe sentiment aggregation (empty list guard)
  - get_whale_flow_for_ticker() helper used by composite_scorer
  - Standardized field names match daily_scanner expectations
"""

import asyncio
import os
import logging
import requests
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

# Robust imports with graceful fallbacks
try:
    from config import UNUSUALWHALES_API_KEY, UNUSUALWHALES_BASE_URL
except ImportError:
    UNUSUALWHALES_API_KEY = os.getenv('UNUSUALWHALES_API_KEY', '')
    UNUSUALWHALES_BASE_URL = os.getenv('UNUSUALWHALES_BASE_URL', 'https://api.unusualwhales.com/api')

try:
    from streaming_engine import get_blackboard, BlackboardMessage, Topic
except ImportError:
    get_blackboard = None
    BlackboardMessage = None
    Topic = None

try:
    from memory import trade_memory
except ImportError:
    trade_memory = None

try:
    import aiohttp
except ImportError:
    aiohttp = None

logger = logging.getLogger(__name__)

# --------------- SETTINGS ---------------
MIN_PREMIUM = int(os.getenv('MIN_PREMIUM', '100000'))       # Minimum $100K premium
MIN_OI_RATIO = float(os.getenv('MIN_OI_RATIO', '2.0'))     # Volume/OI ratio
MAX_DTE = int(os.getenv('MAX_DTE', '60'))                   # Max days to expiry
MIN_DTE = int(os.getenv('MIN_DTE', '7'))                    # Min DTE to filter 0DTE
POLL_INTERVAL = int(os.getenv('WHALE_POLL_INTERVAL', '120'))  # Seconds between polls
API_RATE_LIMIT_DELAY = float(os.getenv('API_RATE_LIMIT_DELAY', '1.0'))
MAX_RETRIES = int(os.getenv('API_MAX_RETRIES', '3'))

# Cache TTL in seconds (10 minutes)
_CACHE_TTL = 600


class WhaleFlowScanner:
    """
    Tier 1 Data Publisher: Scans Unusual Whales API for large options flow.
    Filters for bullish sweeps, block trades, and unusual activity.
    Caches results for 10 minutes to avoid redundant API calls.

    Swarm role: Publishes WHALE_SIGNALS to Blackboard for Tier 2 scoring.
    """

    def __init__(self, blackboard=None):
        self.api_key = UNUSUALWHALES_API_KEY or os.getenv('UNUSUALWHALES_API_KEY', '')
        self.base_url = 'https://api.unusualwhales.com/api'
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
        })
        # Cache: (timestamp, data)
        self._flow_cache: Optional[tuple] = None
        self._ticker_cache: Dict[str, tuple] = {}
        # Swarm integration
        self._blackboard = blackboard
        self._published_signals: set = set()  # Track published to avoid duplicates
        self._last_api_call: float = 0.0  # Rate limiting
        # Stats
        self._total_scans: int = 0
        self._total_signals_published: int = 0

    def _cache_valid(self, cache_entry) -> bool:
        """Return True if cache entry is still within TTL."""
        if cache_entry is None:
            return False
        ts, _ = cache_entry
        return (datetime.now() - ts).total_seconds() < _CACHE_TTL

    def _rate_limit(self) -> None:
        """Enforce API rate limiting between calls."""
        elapsed = time.time() - self._last_api_call
        if elapsed < API_RATE_LIMIT_DELAY:
            time.sleep(API_RATE_LIMIT_DELAY - elapsed)
        self._last_api_call = time.time()

    def _calc_dte(self, expiry_str: str) -> int:
        """
        Calculate days to expiry from expiry string.
        Handles formats: 'YYYY-MM-DD', 'MM/DD/YYYY', 'YYMMDD', 'YYYYMMDD'.
        Returns 0 on parse failure.
        """
        if not expiry_str:
            return 0
        today = date.today()
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%y%m%d', '%Y%m%d'):
            try:
                exp = datetime.strptime(str(expiry_str), fmt).date()
                return max(0, (exp - today).days)
            except ValueError:
                continue
        return 0

    def get_flow(self, limit: int = 50, use_cache: bool = True) -> List[Dict]:
        """
        Get recent options flow alerts from Unusual Whales.
        Uses /option-trades/flow-alerts endpoint.
        Returns list of flow entries filtered by our criteria.
        Caches results for _CACHE_TTL seconds.
        Includes retry logic for API resilience.
        """
        if not self.api_key:
            logger.warning("No Unusual Whales API key configured")
            return []

        # Return cached result if still valid
        if use_cache and self._cache_valid(self._flow_cache):
            _, cached_flows = self._flow_cache
            logger.debug(f"Whale flow: returning {len(cached_flows)} cached entries")
            return cached_flows

        for attempt in range(MAX_RETRIES):
            try:
                self._rate_limit()
                url = f"{self.base_url}/option-trades/flow-alerts"
                params = {
                    'limit': min(limit, 200),
                    'min_premium': MIN_PREMIUM,
                    'min_dte': MIN_DTE,
                    'max_dte': MAX_DTE,
                    'issue_types[]': 'Common Stock',
                }
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                flows = data.get('data', [])

                # Map API fields to our format and apply OI ratio filter
                filtered = self._filter_flows(flows)
                logger.info(f"Whale flow: {len(flows)} raw -> {len(filtered)} filtered")

                # Store in cache
                self._flow_cache = (datetime.now(), filtered)
                self._total_scans += 1
                return filtered

            except requests.RequestException as e:
                logger.warning(f"Unusual Whales API attempt {attempt + 1}/{MAX_RETRIES}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Unusual Whales API failed after {MAX_RETRIES} attempts")
        return []

    def get_flow_by_ticker(self, ticker: str) -> List[Dict]:
        """
        Get options flow for a specific ticker.
        Uses /stock/{ticker}/flow-recent endpoint.
        Caches per-ticker results for _CACHE_TTL seconds.
        """
        if not self.api_key:
            return []

        # Return cached if valid
        if self._cache_valid(self._ticker_cache.get(ticker)):
            _, cached = self._ticker_cache[ticker]
            return cached

        for attempt in range(MAX_RETRIES):
            try:
                self._rate_limit()
                url = f"{self.base_url}/stock/{ticker}/flow-recent"
                params = {'min_premium': MIN_PREMIUM}
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                flows = self._filter_flows(data.get('data', []))
                self._ticker_cache[ticker] = (datetime.now(), flows)
                return flows
            except requests.RequestException as e:
                logger.warning(f"Flow lookup for {ticker} attempt {attempt + 1}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
        return []

    def get_whale_flow_for_ticker(self, ticker: str) -> Dict:
        """
        Convenience method for composite_scorer integration.
        Returns a summary dict for a single ticker:
        {
            'has_whale_flow': bool,
            'total_premium': float,
            'flow_count': int,
            'dominant_sentiment': str,
            'has_sweep': bool,
            'has_block': bool,
        }
        """
        # First try the broad flow cache (already fetched)
        ticker_flows = []
        if self._cache_valid(self._flow_cache):
            _, cached = self._flow_cache
            ticker_flows = [f for f in cached if f.get('ticker') == ticker]

        # Fall back to per-ticker endpoint if not in broad scan
        if not ticker_flows:
            ticker_flows = self.get_flow_by_ticker(ticker)

        if not ticker_flows:
            return {
                'has_whale_flow': False,
                'total_premium': 0.0,
                'flow_count': 0,
                'dominant_sentiment': 'neutral',
                'has_sweep': False,
                'has_block': False,
            }

        total_prem = sum(f.get('premium', 0) for f in ticker_flows)
        sentiments = [f.get('sentiment', 'neutral') for f in ticker_flows]
        dominant = max(set(sentiments), key=sentiments.count) if sentiments else 'neutral'
        has_sweep = any(f.get('trade_type') == 'sweep' for f in ticker_flows)
        has_block = any(f.get('trade_type') == 'block' for f in ticker_flows)

        return {
            'has_whale_flow': True,
            'total_premium': total_prem,
            'flow_count': len(ticker_flows),
            'dominant_sentiment': dominant,
            'has_sweep': has_sweep,
            'has_block': has_block,
        }

    def _filter_flows(self, flows: List[Dict]) -> List[Dict]:
        """
        Filter and normalize flow alerts.
        FIXED: applies OI ratio filter and calculates real DTE.
        """
        filtered = []
        for flow in flows:
            try:
                premium = float(flow.get('total_premium', 0))
                ticker = flow.get('ticker', '')
                option_type = flow.get('type', '').lower()
                strike = flow.get('strike', '')
                expiry = flow.get('expiry', '')
                has_sweep = flow.get('has_sweep', False)
                has_floor = flow.get('has_floor', False)
                volume = int(flow.get('volume', 0) or 0)
                oi = int(flow.get('open_interest', 0) or 0)
                total_ask = float(flow.get('total_ask_side_prem', 0) or 0)
                total_bid = float(flow.get('total_bid_side_prem', 0) or 0)

                # Apply premium threshold
                if premium < MIN_PREMIUM:
                    continue

                # Apply OI ratio filter (FIXED: was declared but never used)
                if oi > 0 and (volume / oi) < MIN_OI_RATIO:
                    continue

                # Calculate real DTE (FIXED: was hardcoded 0)
                dte = self._calc_dte(str(expiry))

                # DTE range guard (belt-and-suspenders)
                if expiry and (dte < MIN_DTE or dte > MAX_DTE):
                    continue

                # Determine sentiment from ask/bid side premium
                if total_ask > total_bid:
                    sentiment = 'bullish' if option_type == 'call' else 'bearish'
                else:
                    sentiment = 'bearish' if option_type == 'call' else 'bullish'

                # Determine trade type
                if has_sweep:
                    trade_type = 'sweep'
                elif has_floor:
                    trade_type = 'floor'
                else:
                    trade_type = 'block'

                filtered.append({
                    'ticker': ticker,
                    'option_type': option_type,
                    'strike': strike,
                    'expiry': expiry,
                    'dte': dte,
                    'premium': premium,
                    'sentiment': sentiment,
                    'trade_type': trade_type,
                    'volume': volume,
                    'open_interest': oi,
                    'oi_ratio': round(volume / oi, 2) if oi > 0 else 0.0,
                    'scan_date': date.today().isoformat(),
                    'source': 'unusual_whales',
                })
            except (ValueError, KeyError, TypeError) as e:
                logger.debug(f"Skipping flow entry: {e}")
                continue
        return filtered

    def get_whale_tickers(self, limit: int = 20) -> List[Dict]:
        """
        Get unique tickers from whale flow sorted by total premium.
        Returns list of dicts matching daily_scanner expectations.
        FIXED: guards against empty sentiment list.
        """
        flows = self.get_flow(limit=100)
        ticker_counts: Dict[str, Dict] = {}

        for f in flows:
            t = f['ticker']
            if t not in ticker_counts:
                ticker_counts[t] = {'count': 0, 'total_premium': 0.0, 'sentiment': []}
            ticker_counts[t]['count'] += 1
            ticker_counts[t]['total_premium'] += f['premium']
            ticker_counts[t]['sentiment'].append(f['sentiment'])

        sorted_tickers = sorted(
            ticker_counts.items(),
            key=lambda x: x[1]['total_premium'],
            reverse=True
        )

        result = []
        for t, data in sorted_tickers[:limit]:
            sentiments = data['sentiment']
            # FIXED: guard against empty list
            dominant = max(set(sentiments), key=sentiments.count) if sentiments else 'neutral'
            result.append({
                'ticker': t,
                'flow_count': data['count'],
                'total_premium': data['total_premium'],
                'dominant_sentiment': dominant,
            })
        return result

    def format_flow_summary(self, flows: List[Dict], limit: int = 10) -> str:
        """
        Format whale flow as a Slack-friendly message.
        """
        if not flows:
            return "No whale flow data available."

        today = date.today().strftime('%b %d')
        lines = [f"*Whale Flow Summary - {today}*"]
        lines.append(f"Filtered: {len(flows)} high-conviction trades\n")

        for f in flows[:limit]:
            emoji = ':whale:' if f['premium'] >= 500_000 else ':dolphin:'
            call_put = f['option_type'].upper()
            dte_str = f"{f['dte']}d" if f.get('dte') else ''
            lines.append(
                f"{emoji} *{f['ticker']}* {f['strike']} {call_put} "
                f"exp {f['expiry']} {dte_str} | ${f['premium']:,.0f} "
                f"| {f['sentiment']} {f['trade_type']}"
            )
        return '\n'.join(lines)

    def invalidate_cache(self):
        """Force-clear the flow cache (useful for testing or forced refresh)."""
        self._flow_cache = None
        self._ticker_cache.clear()
        logger.info("Whale flow cache cleared")

    # --------------- BLACKBOARD PUBLISHING ---------------

    def publish_whale_signals(self, flows: List[Dict] = None) -> int:
        """
        Publish filtered whale flow signals to the Blackboard.
        Returns count of new signals published.
        Deduplicates against previously published signals.
        """
        if not self._blackboard or not BlackboardMessage or not Topic:
            return 0

        if flows is None:
            flows = self.get_flow()

        published = 0
        for flow in flows:
            # Create unique signal ID to prevent duplicates
            sig_id = f"{flow['ticker']}_{flow['expiry']}_{flow['strike']}_{flow['trade_type']}"
            if sig_id in self._published_signals:
                continue

            try:
                msg = BlackboardMessage(
                    topic=Topic.WHALE_SIGNALS,
                    payload={
                        'ticker': flow['ticker'],
                        'option_type': flow['option_type'],
                        'strike': flow['strike'],
                        'expiry': flow['expiry'],
                        'dte': flow['dte'],
                        'premium': flow['premium'],
                        'sentiment': flow['sentiment'],
                        'trade_type': flow['trade_type'],
                        'volume': flow['volume'],
                        'open_interest': flow['open_interest'],
                        'oi_ratio': flow['oi_ratio'],
                        'scan_date': flow['scan_date'],
                    },
                    source='whale_flow',
                )
                self._blackboard.publish(msg)
                self._published_signals.add(sig_id)
                published += 1
            except Exception as e:
                logger.warning(f"[WhaleFlow] Failed to publish signal for {flow['ticker']}: {e}")

        if published > 0:
            self._total_signals_published += published
            logger.info(f"[WhaleFlow] Published {published} new whale signals to Blackboard")

        return published

    def get_stats(self) -> Dict:
        """Return scanner statistics for monitoring."""
        return {
            'total_scans': self._total_scans,
            'total_signals_published': self._total_signals_published,
            'unique_signals_tracked': len(self._published_signals),
            'cache_valid': self._cache_valid(self._flow_cache),
        }


# Singleton used by daily_scanner and other modules (backward compatible)
whale_flow_scanner = WhaleFlowScanner()


# --------------- ASYNC POLLING LOOP ---------------

async def async_whale_flow_publisher(blackboard=None, poll_interval: int = None) -> None:
    """
    Tier 1 async publisher loop.
    Polls Unusual Whales API at regular intervals and publishes
    filtered whale signals to the Blackboard.
    """
    interval = poll_interval or POLL_INTERVAL
    bb = blackboard

    if not bb and get_blackboard:
        try:
            bb = get_blackboard()
        except Exception as e:
            logger.error(f"[WhaleFlow] Failed to get Blackboard: {e}")

    scanner = WhaleFlowScanner(blackboard=bb)
    logger.info(f"[WhaleFlow] Tier 1 publisher starting (poll every {interval}s)")
    logger.info(f"[WhaleFlow] Filters: premium>=${MIN_PREMIUM:,} OI ratio>={MIN_OI_RATIO} DTE={MIN_DTE}-{MAX_DTE}")

    while True:
        try:
            # Fetch and filter flow
            flows = scanner.get_flow(use_cache=False)

            if flows:
                # Publish to Blackboard
                published = scanner.publish_whale_signals(flows)

                # Log to memory for learning flywheel
                if trade_memory and flows:
                    for flow in flows[:5]:  # Top 5 by premium
                        try:
                            trade_memory.record_signal(
                                flow['ticker'],
                                'whale_flow',
                                'whale_flow',
                                score=flow.get('premium', 0) / 10000,  # Normalize
                                regime=flow.get('sentiment', 'neutral'),
                            )
                        except Exception as e:
                            logger.debug(f"[WhaleFlow] Memory record failed: {e}")

                stats = scanner.get_stats()
                logger.info(
                    f"[WhaleFlow] Scan complete: {len(flows)} signals, "
                    f"{published} published, {stats['total_scans']} total scans"
                )
            else:
                logger.debug("[WhaleFlow] No whale flow signals this cycle")

        except Exception as e:
            logger.error(f"[WhaleFlow] Publisher cycle error: {e}")

        await asyncio.sleep(interval)


async def run(mode: str = "publisher") -> None:
    """
    Main async entry point for the Tier 1 whale flow agent.

    Modes:
        publisher: Poll API and publish to Blackboard (default)
        standalone: Run without Blackboard (legacy mode)
    """
    logger.info(f"[WhaleFlow] Starting Tier 1 Data Publisher (mode={mode})")

    if mode == "publisher":
        await async_whale_flow_publisher()
    else:
        logger.info("[WhaleFlow] Standalone mode - use whale_flow_scanner singleton directly")
        while True:
            await asyncio.sleep(60)


# --------------- CLI ENTRY POINT ---------------

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='OpenClaw Tier 1 Whale Flow Publisher'
    )
    parser.add_argument(
        '--mode',
        choices=['publisher', 'standalone'],
        default='publisher',
        help='Run mode: publisher (poll + publish to Blackboard) or standalone',
    )
    parser.add_argument(
        '--scan',
        action='store_true',
        help='Run a single scan and print results',
    )
    parser.add_argument(
        '--ticker',
        type=str,
        default=None,
        help='Get whale flow for a specific ticker',
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    )

    if args.scan:
        scanner = WhaleFlowScanner()
        flows = scanner.get_flow(use_cache=False)
        print(scanner.format_flow_summary(flows))
        print(f"\nTotal: {len(flows)} filtered flow alerts")
    elif args.ticker:
        scanner = WhaleFlowScanner()
        summary = scanner.get_whale_flow_for_ticker(args.ticker.upper())
        print(f"Whale flow for {args.ticker.upper()}: {summary}")
    else:
        try:
            asyncio.run(run(mode=args.mode))
        except KeyboardInterrupt:
            logger.info("[WhaleFlow] Shutting down gracefully...")
        except Exception as e:
            logger.error(f"[WhaleFlow] Fatal error: {e}")
            raise
