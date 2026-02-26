#!/usr/bin/env python3
"""
agent_relative_weakness.py - Hunter-Killer Swarm: Weakness Scanner
OpenClaw Hierarchical Synthesis Architecture - Tier 3

Triggered ONLY when the Apex Synthesizer declares a Short_Only or
Distribution regime. Scans Finviz for stocks breaking below
their 50 SMA on high volume in high-beta sectors.

Publishes to: Topic.SCORED_SIGNALS
Subscribes to: Topic.REGIME_UPDATES
"""

import asyncio
import json
import logging
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Any

from streaming_engine import (
    Blackboard, BlackboardMessage, Topic, get_blackboard,
)

try:
    from finviz_scanner import scan_finviz
except ImportError:
    scan_finviz = None

try:
    from daily_scanner import get_daily_candidates
except ImportError:
    get_daily_candidates = None

logger = logging.getLogger(__name__)

# Sectors known for high beta / vulnerability in sell-offs
HIGH_BETA_SECTORS = {
    "Technology", "Consumer Cyclical", "Communication Services",
    "Consumer Discretionary", "Industrials",
}

# Trigger regimes: only these activate the scanner
SHORT_TRIGGER_REGIMES = {
    "Accelerating_Distribution", "Capitulation", "Bear_Confirmed",
}
SHORT_TRIGGER_BIASES = {"Short_Only"}

SCAN_COOLDOWN_SECONDS = 120  # Don't rescan more often than every 2 min
MAX_CANDIDATES = 20  # Max tickers to evaluate per scan


class RelativeWeaknessAgent:
    """
    Hunter-Killer sub-swarm agent: scans for the weakest stocks
    when the Apex Synthesizer declares a bearish regime.
    """

    AGENT_ID = "relative_weakness"

    def __init__(self, blackboard: Blackboard):
        self.bb = blackboard
        self._last_scan: float = 0.0
        self._active_regime: Dict[str, Any] = {}
        self._weak_stocks: List[Dict] = []
        self._stats = {
            "scans_run": 0,
            "candidates_found": 0,
            "regime_triggers": 0,
        }
        logger.info("[RelativeWeakness] Initialized - Hunter-Killer scanner ready")

    # ----------------------------------------------------------
    # Regime Gate
    # ----------------------------------------------------------

    def _should_activate(self, regime: Dict) -> bool:
        """Only activate on bearish regime declarations."""
        mr = regime.get("Market_Regime", "")
        db = regime.get("Directional_Bias", "")
        cv = regime.get("Conviction", 0)
        is_short_regime = mr in SHORT_TRIGGER_REGIMES
        is_short_bias = db in SHORT_TRIGGER_BIASES
        has_conviction = cv >= 60
        return (is_short_regime or is_short_bias) and has_conviction

    # ----------------------------------------------------------
    # Finviz Scanning
    # ----------------------------------------------------------

    async def _scan_for_weakness(self) -> List[Dict]:
        """
        Scan for stocks breaking below 50 SMA on high volume.
        Uses finviz_scanner as primary, daily_scanner as fallback.
        """
        candidates = []

        # Strategy 1: Use existing finviz_scanner module
        if scan_finviz:
            try:
                raw = scan_finviz(
                    filters={
                        "SMA50": "Price below SMA50",
                        "Change": "Down",
                        "Volume": "Over 1M",
                        "AverageVolume": "Over 500K",
                    },
                    sort="-change",
                    limit=MAX_CANDIDATES,
                )
                if isinstance(raw, list):
                    for stock in raw:
                        ticker = stock.get("ticker", stock.get("Ticker", ""))
                        if ticker:
                            candidates.append({
                                "ticker": ticker.upper(),
                                "price": float(stock.get("price", stock.get("Price", 0))),
                                "change_pct": float(stock.get("change", stock.get("Change", "0").replace("%", "")) or 0),
                                "volume": int(stock.get("volume", stock.get("Volume", 0)) or 0),
                                "sector": stock.get("sector", stock.get("Sector", "")),
                                "sma50": float(stock.get("sma50", stock.get("SMA50", 0)) or 0),
                                "source": "finviz",
                            })
            except Exception as e:
                logger.error(f"[RelativeWeakness] Finviz scan error: {e}")

        # Strategy 2: Fallback to daily_scanner candidates
        if not candidates and get_daily_candidates:
            try:
                daily = get_daily_candidates() or []
                for stock in daily[:MAX_CANDIDATES]:
                    ticker = stock.get("ticker", "")
                    if ticker:
                        candidates.append({
                            "ticker": ticker.upper(),
                            "price": float(stock.get("price", 0)),
                            "change_pct": float(stock.get("price_change_5d", 0)),
                            "volume": int(stock.get("volume", 0) or 0),
                            "sector": stock.get("sector", ""),
                            "sma50": float(stock.get("sma_50", 0) or 0),
                            "source": "daily_scanner",
                        })
            except Exception as e:
                logger.error(f"[RelativeWeakness] Daily scanner error: {e}")

        return candidates

    def _score_weakness(self, candidates: List[Dict]) -> List[Dict]:
        """
        Score each candidate on relative weakness.
        Higher score = weaker stock = better short candidate.
        """
        scored = []
        for c in candidates:
            score = 0.0

            # Factor 1: Price below 50 SMA (distance matters)
            price = c.get("price", 0)
            sma50 = c.get("sma50", 0)
            if price > 0 and sma50 > 0 and price < sma50:
                pct_below = ((sma50 - price) / sma50) * 100
                score += min(pct_below * 5, 30)  # Max 30 pts

            # Factor 2: Magnitude of daily decline
            change = abs(c.get("change_pct", 0))
            score += min(change * 3, 25)  # Max 25 pts

            # Factor 3: High-beta sector bonus
            sector = c.get("sector", "")
            if sector in HIGH_BETA_SECTORS:
                score += 15

            # Factor 4: Volume surge (relative to normal)
            vol = c.get("volume", 0)
            if vol > 2_000_000:
                score += 15
            elif vol > 1_000_000:
                score += 10
            elif vol > 500_000:
                score += 5

            # Factor 5: Already weak (multi-day decline)
            change5d = c.get("change_pct", 0)
            if change5d < -5:
                score += 15

            scored.append({
                **c,
                "weakness_score": round(score, 1),
                "scored_at": datetime.now().isoformat(),
            })

        # Sort by weakness score descending
        scored.sort(key=lambda x: x["weakness_score"], reverse=True)
        return scored

    # ----------------------------------------------------------
    # Publication
    # ----------------------------------------------------------

    async def _publish_weak_stocks(self, weak_stocks: List[Dict]) -> None:
        """Publish the top weakness candidates to the Blackboard."""
        top5 = weak_stocks[:5]
        self._weak_stocks = top5
        payload = {
            "signal_type": "relative_weakness_scan",
            "regime": self._active_regime,
            "candidates": top5,
            "scan_timestamp": datetime.now().isoformat(),
            "total_scanned": len(weak_stocks),
        }

        await self.bb.publish(BlackboardMessage(
            topic=Topic.SCORED_SIGNALS,
            payload=payload,
            source_agent=self.AGENT_ID,
            priority=2,
            ttl_seconds=300,
        ))

        tickers = [s["ticker"] for s in top5]
        logger.info(
            f"[RelativeWeakness] Published {len(top5)} weak stocks: "
            f"{', '.join(tickers)}"
        )

    # ----------------------------------------------------------
    # Main Event Loop
    # ----------------------------------------------------------

    async def run(self) -> None:
        """Listen for regime updates; scan when bearish regime declared."""
        regime_q = await self.bb.subscribe(
            Topic.REGIME_UPDATES, self.AGENT_ID
        )
        logger.info(
            "[RelativeWeakness] Subscribed to regime_updates. "
            "Waiting for Short_Only trigger..."
        )

        while True:
            try:
                msg = await asyncio.wait_for(regime_q.get(), timeout=10.0)
                if not isinstance(msg, BlackboardMessage) or msg.is_expired():
                    continue

                regime = msg.payload
                self._active_regime = regime
                if not self._should_activate(regime):
                    continue

                # Cooldown check
                now = time.time()
                if now - self._last_scan < SCAN_COOLDOWN_SECONDS:
                    continue

                self._stats["regime_triggers"] += 1
                logger.info(
                    f"[RelativeWeakness] ACTIVATED by regime "
                    f"{regime.get('Market_Regime')} | "
                    f"Bias={regime.get('Directional_Bias')} | "
                    f"Conviction={regime.get('Conviction')}"
                )

                # Run the scan
                candidates = await self._scan_for_weakness()
                if candidates:
                    scored = self._score_weakness(candidates)
                    self._stats["candidates_found"] += len(scored)
                    self._stats["scans_run"] += 1
                    await self._publish_weak_stocks(scored)
                else:
                    logger.warning("[RelativeWeakness] No candidates found")

                self._last_scan = now

            except asyncio.TimeoutError:
                await self.bb.heartbeat(self.AGENT_ID)
            except asyncio.CancelledError:
                logger.info("[RelativeWeakness] Shutting down")
                break
            except Exception as e:
                logger.error(f"[RelativeWeakness] Loop error: {e}")
                await asyncio.sleep(5)

    def get_status(self) -> Dict:
        return {
            "agent_id": self.AGENT_ID,
            "active_regime": self._active_regime,
            "weak_stocks": self._weak_stocks,
            "stats": dict(self._stats),
        }
