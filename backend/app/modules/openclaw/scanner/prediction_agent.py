"""Prediction Agent for OpenClaw.

Integrates with Polymarket and Kalshi to capture wisdom-of-crowds sentiment.
Normalizes contract odds to [-1, 1], triggers on >10% probability shifts, and
feeds into trade_memory for accuracy backtesting.
"""
import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

async def fetch_prediction_markets() -> List[Dict[str, Any]]:
    """Mock fetch from Polymarket/Kalshi."""
    # In a real implementation, this would call actual APIs.
    # For now, simulate some probability shifts on major indices or tickers.
    return [
        {"ticker": "SPY", "market": "Will SPY close above 520 this week?", "odds": 0.65, "previous_odds": 0.52},
        {"ticker": "QQQ", "market": "Will QQQ reach new ATH?", "odds": 0.45, "previous_odds": 0.40},
        {"ticker": "BTC", "market": "Will BTC break 70k?", "odds": 0.85, "previous_odds": 0.70},
    ]

def normalize_odds(odds: float) -> float:
    """Normalize odds (0.0 to 1.0) into sentiment score [-1.0, 1.0]."""
    return (odds - 0.5) * 2.0

class PredictionScanner:
    """Class-based Prediction Agent to be auto-discovered by scanner registry."""
    
    def __init__(self, blackboard=None):
        self.bb = blackboard
        self._previous_odds = {}
        
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
                            "timestamp": datetime.utcnow().isoformat()
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

async def async_prediction_agent_publisher(blackboard=None):
    """Entry point for auto-discovery."""
    scanner = PredictionScanner(blackboard)
    await scanner.run()
