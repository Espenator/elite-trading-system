#!/usr/bin/env python3
"""
Multi-Timeframe Alignment for OpenClaw
Scores Weekly/Daily/4H/1H structure alignment.

Timeframes analyzed:
  - Weekly: Overall trend direction
  - Daily: Primary trend confirmation
  - 4-Hour: Intermediate structure
  - 1-Hour: Entry timing

Alignment score (0-5) feeds into CompositeScorer Trend pillar.
Full alignment across all timeframes = highest conviction.
"""
import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
_data_url = os.getenv('ALPACA_DATA_URL', 'https://data.alpaca.markets').rstrip('/')
ALPACA_DATA_URL = _data_url if _data_url.endswith('/v2') else _data_url + '/v2'
ALPACA_FEED = os.getenv('ALPACA_FEED', 'sip')

# Timeframe configs: (alpaca_timeframe, bars_needed, weight)
TIMEFRAMES = {
    'weekly': ('1Week', 52, 2.0),
    'daily': ('1Day', 200, 1.5),
    '4hour': ('4Hour', 100, 1.0),
    '1hour': ('1Hour', 100, 0.5),
}


class MTFAlignment:
    """Multi-Timeframe Alignment Analyzer."""

    def __init__(self, api_key=None, secret_key=None):
        self.api_key = api_key or ALPACA_API_KEY
        self.secret_key = secret_key or ALPACA_SECRET_KEY
        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.secret_key,
        }

    def get_bars(self, ticker: str, timeframe: str, limit: int) -> List[Dict]:
        """Fetch OHLCV bars from Alpaca for a specific timeframe."""
        url = f"{ALPACA_DATA_URL}/stocks/{ticker}/bars"
        params = {
            'timeframe': timeframe,
            'limit': limit,
            'adjustment': 'split',
                'feed': ALPACA_FEED,
                  'start': (datetime.now() - timedelta(days=int(limit * 1.6))).strftime('%Y-%m-%d'),
        }
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json().get('bars') or []
        except Exception as e:
            logger.error(f"MTF bars failed for {ticker} ({timeframe}): {e}")
            return []

    def analyze(self, ticker: str) -> Dict:
        """
        Analyze multi-timeframe alignment for a ticker.

        Returns:
            Dict with alignment_score (0-5), per-timeframe analysis,
            and overall direction.
        """
        result = {
            'ticker': ticker,
            'alignment_score': 0,
            'direction': 'NEUTRAL',
            'timeframes': {},
        }

        bullish_count = 0
        bearish_count = 0
        total_weight = 0
        weighted_score = 0

        for tf_name, (alpaca_tf, bars_needed, weight) in TIMEFRAMES.items():
            bars = self.get_bars(ticker, alpaca_tf, bars_needed)
            if not bars or len(bars) < 20:
                result['timeframes'][tf_name] = {'status': 'NO_DATA'}
                continue

            tf_analysis = self._analyze_timeframe(bars)
            result['timeframes'][tf_name] = tf_analysis

            if tf_analysis['trend'] == 'BULLISH':
                bullish_count += 1
                weighted_score += weight
            elif tf_analysis['trend'] == 'BEARISH':
                bearish_count += 1
                weighted_score -= weight

            total_weight += weight

        # Calculate alignment score (0-5)
        if total_weight > 0:
            # Normalize to 0-5 scale
            raw = (weighted_score / total_weight + 1) * 2.5
            result['alignment_score'] = max(0, min(5, round(raw, 1)))

        # Overall direction
        if bullish_count >= 3:
            result['direction'] = 'STRONG_BULLISH'
        elif bullish_count >= 2:
            result['direction'] = 'BULLISH'
        elif bearish_count >= 3:
            result['direction'] = 'STRONG_BEARISH'
        elif bearish_count >= 2:
            result['direction'] = 'BEARISH'
        else:
            result['direction'] = 'MIXED'

        logger.info(f"MTF {ticker}: score={result['alignment_score']} "
                    f"dir={result['direction']} "
                    f"bull={bullish_count} bear={bearish_count}")
        return result

    def _analyze_timeframe(self, bars: List[Dict]) -> Dict:
        """Analyze a single timeframe's trend structure."""
        closes = [b['c'] for b in bars]
        highs = [b['h'] for b in bars]
        lows = [b['l'] for b in bars]

        price = closes[-1]
        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else 0
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else 0

        # Determine trend
        above_20 = price > sma_20 if sma_20 else False
        above_50 = price > sma_50 if sma_50 else False
        sma_order = sma_20 > sma_50 if (sma_20 and sma_50) else False

        # Higher highs / higher lows check (last 10 bars)
        recent = min(10, len(bars))
        hh = highs[-1] > max(highs[-recent:-1]) if recent > 1 else False
        hl = min(lows[-5:]) > min(lows[-recent:-5]) if recent > 5 else False

        bullish_signals = sum([above_20, above_50, sma_order, hh, hl])

        if bullish_signals >= 4:
            trend = 'BULLISH'
        elif bullish_signals >= 2:
            trend = 'NEUTRAL'
        else:
            trend = 'BEARISH'

        return {
            'trend': trend,
            'price': price,
            'sma_20': round(sma_20, 2),
            'sma_50': round(sma_50, 2),
            'above_20': above_20,
            'above_50': above_50,
            'sma_order': sma_order,
            'bullish_signals': bullish_signals,
        }

    def check_tickers(self, tickers: List[str]) -> Dict[str, Dict]:
        """Batch MTF analysis for multiple tickers."""
        results = {}
        for ticker in tickers:
            try:
                results[ticker] = self.analyze(ticker)
            except Exception as e:
                logger.error(f"MTF failed for {ticker}: {e}")
                results[ticker] = {'alignment_score': 0, 'direction': 'ERROR'}
        return results


# ========== MODULE-LEVEL CONVENIENCE ==========

mtf_analyzer = MTFAlignment()


def get_mtf_alignment(ticker: str) -> Dict:
    """Get MTF alignment for a single ticker."""
    return mtf_analyzer.analyze(ticker)


def batch_mtf_alignment(tickers: List[str]) -> Dict[str, Dict]:
    """Get MTF alignment for multiple tickers."""
    return mtf_analyzer.check_tickers(tickers)
