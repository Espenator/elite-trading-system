#!/usr/bin/env python3
"""
Prediction Market Agent for OpenClaw
Monitors Polymarket and Kalshi for forward-looking macro and earnings sentiment.
Controls: Triggers on >10% probability shifts.
"""
import asyncio
import os
import logging
import time
from datetime import datetime
from typing import Dict, List

try:
    from app.modules.openclaw.streaming.streaming_engine import get_blackboard, BlackboardMessage, Topic
except ImportError:
    get_blackboard = None; BlackboardMessage = None; Topic = None

logger = logging.getLogger(__name__)

# --- CONTROLS ---
MIN_PROBABILITY_SHIFT = float(os.getenv('MIN_PROBABILITY_SHIFT', '0.10')) # 10%
POLL_INTERVAL = int(os.getenv('PREDICTION_POLL_INTERVAL', '600')) # 10 mins


async def fetch_prediction_markets() -> List[Dict]:
    """Fetch from Polymarket / Kalshi APIs. Returns list of market dicts."""
    # TODO: wire real Polymarket Gamma API
    return []


def normalize_odds(odds: float) -> float:
    """Normalize probability odds to a [-1, 1] sentiment scale."""
    return round((odds - 0.5) * 2, 4)


class PredictionMarketScanner:
    def __init__(self, blackboard=None):
        self._blackboard = blackboard
        self._probability_cache = {} # Track shifts
        
    def fetch_polymarket_contracts(self) -> List[Dict]:
        """
        Polls Polymarket Gamma API for contract odds.
        Normalized to [-1, 1] scale matching sentiment.py
        """
        # Stub for Polymarket API integration
        # Typical return: [{'id': '...', 'title': '...', 'probability': 0.65, 'side': 'bullish'}]
        return []

    async def run(self):
        """Main loop for the prediction agent."""
        logger.info("[PredictionAgent] Started prediction market scanning.")
        while True:
            try:
                markets = await fetch_prediction_markets()
                for m in markets:
                    ticker = m["ticker"]
                    odds = m["odds"]
                    prev_odds = m.get("previous_odds", self._previous_odds.get(ticker, odds))

                    self._previous_odds[ticker] = odds

                    shift = odds - prev_odds
                    if abs(shift) >= 0.10: # >10% probability shift
                        sentiment_score = normalize_odds(odds)

                        # Generate payload matching alpha signal standard
                        payload = {
                            "ticker": ticker,
                            "signal_type": "prediction_market",
                            "sentiment": "bullish" if sentiment_score > 0 else "bearish",
                            "score": sentiment_score,
                            "shift": shift,
                            "market_question": m["market"],
                            "timestamp": datetime.utcnow().isoformat(),
                            # Kelly-informed confidence from prediction odds
                            "kelly_edge": round(abs(shift) * odds, 4),
                            "confidence": round(min(1.0, odds * (1 + abs(shift))), 3),
                            "prob_up": round(odds if shift > 0 else 1 - odds, 3),
                            "risk_adjusted_score": round(sentiment_score * min(1.0, odds), 3),
                            "position_recommendation": "FULL" if odds > 0.7 and abs(shift) > 0.15 else "HALF" if odds > 0.55 else "SKIP",
                            "expected_value": round(abs(shift) * odds - abs(shift) * (1 - odds), 4),
                        }

                        # Feed into trade memory for accuracy backtesting (mock or direct via topic)
                        logger.info(f"[PredictionAgent] >10% shift detected on {ticker}: {shift*100:.1f}%")

                        if self.bb:
                            from app.modules.openclaw.streaming.streaming_engine import BlackboardMessage, Topic
                            await self.bb.publish(BlackboardMessage(
                                topic=Topic.PREDICTION_SIGNALS,
                                payload=payload,
                                source_agent="prediction_agent"
                            ))

                            # Also feed into trade outcomes / memory for backtesting
                            await self.bb.publish(BlackboardMessage(
                                topic=Topic.TRADE_OUTCOMES,
                                payload={
                                    "type": "prediction_log",
                                    "ticker": ticker,
                                    "odds": odds,
                                    "sentiment": sentiment_score,
                                    "timestamp": payload["timestamp"]
                                },
                                source_agent="prediction_agent"
                            ))

                await asyncio.sleep(60) # Poll every 60 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PredictionAgent] Error: {e}")
                await asyncio.sleep(60)

    def detect_shifts(self, contracts: List[Dict]) -> List[Dict]:
        signals = []
        for contract in contracts:
            cid = contract['id']
            current_prob = contract['probability']
            if cid in self._probability_cache:
                old_prob = self._probability_cache[cid]
                shift = current_prob - old_prob
                if abs(shift) >= MIN_PROBABILITY_SHIFT:
                    signals.append({
                        'event': contract['title'],
                        'shift': shift,
                        'current_probability': current_prob,
                        'sentiment_normalized': (current_prob - 0.5) * 2 # maps [0,1] to [-1,1]
                    })
            self._probability_cache[cid] = current_prob
        return signals

async def async_prediction_publisher(blackboard=None):
    bb = blackboard or (get_blackboard() if get_blackboard else None)
    scanner = PredictionMarketScanner(bb)
    logger.info(f"[PredictionAgent] Starting polling every {POLL_INTERVAL}s")
    
    while True:
        contracts = scanner.fetch_polymarket_contracts()
        signals = scanner.detect_shifts(contracts)
        
        for sig in signals:
            logger.info(f"[PredictionAgent] 10%+ Shift Detected: {sig['event']}")
            if bb and Topic:
                topic_enum = getattr(Topic, 'PREDICTION_SIGNALS', 'prediction_signals')
                msg = BlackboardMessage(
                    topic=topic_enum,
                    payload=sig,
                    source='prediction_agent'
                )
                bb.publish(msg)
                
        await asyncio.sleep(POLL_INTERVAL)
