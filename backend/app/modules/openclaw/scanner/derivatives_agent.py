#!/usr/bin/env python3
"""
Derivatives Agent for OpenClaw
Monitors CBOE Put/Call Ratio and Short Interest as proxies for institutional fear/greed.
Controls: Alerts on >1.2 put-heavy PCR, >10% float shorted.
"""
import asyncio
import os
import logging
import time
from typing import Dict, List, Optional

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    from app.modules.openclaw.streaming_engine import get_blackboard, BlackboardMessage, Topic
except ImportError:
    get_blackboard = None; BlackboardMessage = None; Topic = None

logger = logging.getLogger(__name__)

# --- CONTROLS ---
MIN_PCR_THRESHOLD = float(os.getenv('MIN_PCR_THRESHOLD', '1.2'))
MIN_SHORT_INTEREST = float(os.getenv('MIN_SHORT_INTEREST', '0.10')) # 10%
POLL_INTERVAL = int(os.getenv('DERIVATIVES_POLL_INTERVAL', '900')) # 15 mins

class DerivativesScanner:
    def __init__(self, blackboard=None):
        self._blackboard = blackboard
        
    def fetch_cboe_pcr(self) -> Optional[float]:
        """
        Polls ^PCR (CBOE Put/Call Ratio) via yfinance.
        """
        if not yf:
            return None
        try:
            pcr = yf.Ticker("^PCR")
            hist = pcr.history(period="1d")
            if not hist.empty:
                return hist['Close'].iloc[-1]
        except Exception as e:
            logger.error(f"Failed to fetch CBOE PCR: {e}")
        return None

    def scan_derivatives(self) -> List[Dict]:
        signals = []
        pcr_value = self.fetch_cboe_pcr()
        if pcr_value and pcr_value >= MIN_PCR_THRESHOLD:
            signals.append({
                'indicator': 'CBOE_PCR',
                'value': pcr_value,
                'sentiment': 'fear',
                'threshold_crossed': MIN_PCR_THRESHOLD
            })
            
        # Stub for Short Interest polling (Alpha Vantage / Finnhub)
        # if short_interest > MIN_SHORT_INTEREST: ...
        
        return signals

async def async_derivatives_publisher(blackboard=None):
    bb = blackboard or (get_blackboard() if get_blackboard else None)
    scanner = DerivativesScanner(bb)
    logger.info(f"[DerivativesAgent] Starting polling every {POLL_INTERVAL}s")
    
    while True:
        signals = scanner.scan_derivatives()
        for sig in signals:
            logger.warning(f"[DerivativesAgent] Derivative Alert: {sig['indicator']} at {sig['value']}")
            if bb and Topic:
                topic_enum = getattr(Topic, 'DERIVATIVES_SIGNALS', 'derivatives_signals')
                msg = BlackboardMessage(
                    topic=topic_enum,
                    payload=sig,
                    source='derivatives_agent'
                )
                bb.publish(msg)
                
        await asyncio.sleep(POLL_INTERVAL)
