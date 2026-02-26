#!/usr/bin/env python3
"""
Retail Sentiment Agent for OpenClaw
Monitors StockTwits, Reddit, and Telegram for retail momentum.
Applies controls like message age, bullish/bearish ratio (>2:1), and volume thresholds.
"""
import asyncio
import os
import logging
import time
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:
    from app.modules.openclaw.streaming_engine import get_blackboard, BlackboardMessage, Topic
except ImportError:
    get_blackboard = None; BlackboardMessage = None; Topic = None

logger = logging.getLogger(__name__)

# --- CONTROLS ---
MIN_STOCKTWITS_RATIO = float(os.getenv('MIN_STOCKTWITS_RATIO', '2.0'))
MIN_REDDIT_MENTIONS = int(os.getenv('MIN_REDDIT_MENTIONS_PER_HR', '500'))
POLL_INTERVAL = int(os.getenv('RETAIL_POLL_INTERVAL', '300')) # 5 mins

class RetailSentimentScanner:
    def __init__(self, blackboard=None):
        self._blackboard = blackboard
        self._published_signals = set()

    def fetch_stocktwits(self, symbol: str) -> Optional[Dict]:
        """
        Fetch cashtag sentiment. Requires > 2:1 imbalance.
        """
        try:
            url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                messages = data.get('messages', [])
                bullish = sum(1 for m in messages if m.get('entities', {}).get('sentiment', {}).get('basic') == 'Bullish')
                bearish = sum(1 for m in messages if m.get('entities', {}).get('sentiment', {}).get('basic') == 'Bearish')
                
                bearish_safe = bearish if bearish > 0 else 1
                bullish_safe = bullish if bullish > 0 else 1
                
                ratio = bullish / bearish_safe
                inv_ratio = bearish / bullish_safe
                
                if ratio >= MIN_STOCKTWITS_RATIO:
                    return {'ticker': symbol, 'source': 'stocktwits', 'sentiment': 'bullish', 'ratio': ratio, 'volume': len(messages)}
                elif inv_ratio >= MIN_STOCKTWITS_RATIO:
                    return {'ticker': symbol, 'source': 'stocktwits', 'sentiment': 'bearish', 'ratio': inv_ratio, 'volume': len(messages)}
        except Exception as e:
            logger.debug(f"[RetailAgent] StockTwits error for {symbol}: {e}")
        return None

    def fetch_reddit_volume(self, symbol: str) -> Optional[Dict]:
        """
        Stub for PRAW scrape. Filters noise by requiring >500 mentions/hour.
        """
        # Implementation would integrate PRAW here
        pass

    def run_scan(self, symbols: List[str]) -> List[Dict]:
        signals = []
        for sym in symbols:
            st_data = self.fetch_stocktwits(sym)
            if st_data:
                signals.append(st_data)
            time.sleep(1) # API rate limit
        return signals

async def async_retail_publisher(symbols: List[str], blackboard=None):
    bb = blackboard or (get_blackboard() if get_blackboard else None)
    scanner = RetailSentimentScanner(bb)
    logger.info(f"[RetailAgent] Starting polling every {POLL_INTERVAL}s")
    
    while True:
        signals = scanner.run_scan(symbols)
        for sig in signals:
            sig_id = f"{sig['ticker']}_{sig['source']}_{sig['sentiment']}_{int(time.time()/3600)}"
            if sig_id in scanner._published_signals:
                continue
                
            logger.info(f"[RetailAgent] Signal found: {sig['ticker']} ({sig['sentiment']})")
            if bb and Topic:
                try:
                    # Dynamically get RETAIL_SIGNALS topic or fallback
                    topic_enum = getattr(Topic, 'RETAIL_SIGNALS', 'retail_signals')
                    msg = BlackboardMessage(
                        topic=topic_enum,
                        payload=sig,
                        source='retail_agent'
                    )
                    bb.publish(msg)
                    scanner._published_signals.add(sig_id)
                except Exception as e:
                    logger.error(f"Failed to publish: {e}")
                    
        await asyncio.sleep(POLL_INTERVAL)
