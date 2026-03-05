#!/usr/bin/env python3
"""
Streaming Engine for OpenClaw v6.1 - Options Flow Agent Pipeline
Real-time event-driven trading engine with Pub/Sub Blackboard + Multi-Agent
sentiment pipeline.

Upgraded from v6.0 to add dynamic agent discovery for sentiment scanners:
- Auto-loads prediction_agent, retail_agent, derivatives_agent, and whale_flow.
- Registers dynamic topic enums.
"""

import os
import sys
import json
import time
import uuid
import math
import asyncio
import logging
import argparse
import threading
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum

try:
    from alpaca.data.live import StockDataStream
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    ALPACA_SDK_AVAILABLE = True
except ImportError:
    ALPACA_SDK_AVAILABLE = False

try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_FEED

try:
    from config import UNUSUALWHALES_API_KEY, UNUSUALWHALES_BASE_URL
except ImportError:
    UNUSUALWHALES_API_KEY = os.getenv("UNUSUALWHALES_API_KEY", "")
    UNUSUALWHALES_BASE_URL = "https://api.unusualwhales.com/api"

try:
    from config import MAX_DAILY_LOSS_PCT, DEFAULT_RISK_PCT
except ImportError:
    MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "2.0"))
    DEFAULT_RISK_PCT = float(os.getenv("DEFAULT_RISK_PCT", "1.5"))

try:
    from composite_scorer import CompositeScorer
except ImportError:
    CompositeScorer = None

try:
    from technical_checker import TechnicalChecker
except ImportError:
    TechnicalChecker = None

try:
    from regime import regime_detector
except ImportError:
    regime_detector = None

try:
    from macro_context import get_macro_snapshot
except ImportError:
    get_macro_snapshot = None

try:
    from memory_v3 import trade_memory

    HAS_MEMORY = True
except ImportError:
    trade_memory = None
    HAS_MEMORY = False

try:
    from position_sizer import PositionSizer

    HAS_SIZER = True
except ImportError:
    PositionSizer = None
    HAS_SIZER = False

try:
    # Import agent registry for auto-discovery
    from scanner import AGENT_REGISTRY
except ImportError:
    AGENT_REGISTRY = {}

logger = logging.getLogger(__name__)


# ========== PUB/SUB BLACKBOARD (Swarm Core) ==========


class Topic(str, Enum):
    """Typed message topics for the Blackboard pub/sub system."""

    ALPHA_SIGNALS = "alpha_signals"
    SCORED_SIGNALS = "scored_signals"
    EXECUTION_ORDERS = "execution_orders"
    TRADE_OUTCOMES = "trade_outcomes"
    REGIME_UPDATES = "regime_updates"
    AGENT_HEARTBEATS = "agent_heartbeats"
    WATCHLIST_UPDATES = "watchlist_updates"
    BAR_UPDATES = "bar_updates"
    # v6.0 Options Flow Pipeline topics
    FLOW_RAW = "flow_raw"
    FLOW_CONTEXTUALIZED = "flow_contextualized"
    FLOW_SENTIMENT = "flow_sentiment"
    FLOW_AUDITED = "flow_audited"
    # v6.1 Sentiment Agent topics
    RETAIL_SIGNALS = "retail_signals"
    PREDICTION_SIGNALS = "prediction_signals"
    DERIVATIVES_SIGNALS = "derivatives_signals"


@dataclass
class BlackboardMessage:
    """Typed message for Blackboard pub/sub transport."""

    topic: str
    payload: Dict
    source_agent: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: int = 5
    ttl_seconds: int = 300

    def is_expired(self) -> bool:
        created = datetime.fromisoformat(self.timestamp)
        return (datetime.now() - created).total_seconds() > self.ttl_seconds

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "BlackboardMessage":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Blackboard:
    """
    Central Pub/Sub message broker for the OpenClaw swarm.
    Lightweight asyncio-based implementation (no Redis dependency).
    Supports priority ordering, TTL expiry, message history, and
    pipeline-stage tracking for the options flow agent chain.
    """

    def __init__(self, history_size: int = 500):
        self._subscribers: Dict[str, Dict[str, asyncio.Queue]] = defaultdict(dict)
        self._history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=history_size)
        )
        self._stats: Dict[str, int] = defaultdict(int)
        self._agent_heartbeats: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        self._running = True
        self._pipeline_metrics: Dict[str, Dict] = defaultdict(
            lambda: {
                "processed": 0,
                "passed": 0,
                "rejected": 0,
                "avg_latency_ms": 0.0,
                "last_active": None,
            }
        )
        logger.info("[Blackboard] Initialized pub/sub broker v6.1")

    async def publish(self, message: BlackboardMessage) -> None:
        """Publish a message to a topic. All subscribers get a copy."""
        if not self._running:
            return
        topic = message.topic
        self._history[topic].append(message.to_dict())
        self._stats[f"published:{topic}"] += 1
        self._stats[f"from:{message.source_agent}"] += 1
        async with self._lock:
            subscribers = self._subscribers.get(topic, {})
            for agent_id, queue in subscribers.items():
                try:
                    await asyncio.wait_for(queue.put(message), timeout=1.0)
                except asyncio.TimeoutError:
                    logger.warning(f"[Blackboard] Queue full for {agent_id} on {topic}")
                except Exception as e:
                    logger.error(f"[Blackboard] Publish error to {agent_id}: {e}")
        logger.debug(
            f"[Blackboard] {message.source_agent} -> {topic} "
            f"({len(subscribers)} subscribers) id={message.message_id}"
        )

    async def subscribe(
        self, topic: str, agent_id: str, max_queue_size: int = 100
    ) -> asyncio.Queue:
        """Subscribe an agent to a topic. Returns an asyncio.Queue."""
        async with self._lock:
            if agent_id in self._subscribers.get(topic, {}):
                return self._subscribers[topic][agent_id]
            queue = asyncio.PriorityQueue(maxsize=max_queue_size)
            self._subscribers[topic][agent_id] = queue
            self._stats[f"subscribed:{topic}"] += 1
            logger.info(f"[Blackboard] {agent_id} subscribed to {topic}")
            return queue

    async def unsubscribe(self, topic: str, agent_id: str) -> None:
        """Remove an agent's subscription from a topic."""
        async with self._lock:
            if topic in self._subscribers and agent_id in self._subscribers[topic]:
                del self._subscribers[topic][agent_id]
                logger.info(f"[Blackboard] {agent_id} unsubscribed from {topic}")

    def get_history(self, topic: str, limit: int = 50) -> List[Dict]:
        """Get recent message history for a topic."""
        history = list(self._history.get(topic, []))
        return history[-limit:]

    def get_stats(self) -> Dict:
        """Get blackboard statistics including pipeline metrics."""
        return {
            "topics": {t: len(subs) for t, subs in self._subscribers.items()},
            "message_counts": dict(self._stats),
            "history_sizes": {t: len(h) for t, h in self._history.items()},
            "agent_heartbeats": {
                a: ts.isoformat() for a, ts in self._agent_heartbeats.items()
            },
            "pipeline_metrics": dict(self._pipeline_metrics),
        }

    def record_pipeline_step(
        self, agent_name: str, passed: bool, latency_ms: float = 0.0
    ):
        """Track pipeline throughput per agent stage."""
        m = self._pipeline_metrics[agent_name]
        m["processed"] += 1
        if passed:
            m["passed"] += 1
        else:
            m["rejected"] += 1
        n = m["processed"]
        m["avg_latency_ms"] = m["avg_latency_ms"] * ((n - 1) / n) + latency_ms / n
        m["last_active"] = datetime.now().isoformat()

    async def heartbeat(self, agent_id: str) -> None:
        """Record an agent heartbeat for health monitoring."""
        self._agent_heartbeats[agent_id] = datetime.now()
        await self.publish(
            BlackboardMessage(
                topic=Topic.AGENT_HEARTBEATS,
                payload={"agent_id": agent_id, "status": "alive"},
                source_agent=agent_id,
                priority=10,
                ttl_seconds=60,
            )
        )

    def get_stale_agents(self, timeout_seconds: int = 120) -> List[str]:
        """Get agents that haven't sent a heartbeat recently."""
        now = datetime.now()
        return [
            agent_id
            for agent_id, last_ts in self._agent_heartbeats.items()
            if (now - last_ts).total_seconds() > timeout_seconds
        ]

    async def shutdown(self) -> None:
        """Gracefully shut down the blackboard."""
        self._running = False
        logger.info("[Blackboard] Shutting down...")
        try:
            history_file = os.path.join(DATA_DIR, "blackboard_history.json")
            all_history = {t: list(h) for t, h in self._history.items()}
            with open(history_file, "w") as f:
                json.dump(all_history, f, indent=2, default=str)
            logger.info(f"[Blackboard] History saved to {history_file}")
        except Exception as e:
            logger.error(f"[Blackboard] Failed to save history: {e}")


# Module-level singleton
_blackboard: Optional[Blackboard] = None


def get_blackboard() -> Blackboard:
    """Get or create the global Blackboard singleton."""
    global _blackboard
    if _blackboard is None:
        _blackboard = Blackboard()
    return _blackboard


# ========== CONFIGURATION ==========

MAX_SUBSCRIPTIONS = 50
SCORE_PERSIST_INTERVAL = 60
RECONNECT_DELAY = 5
MAX_ERROR_COUNT = 3
SLACK_ALERT_THRESHOLD = 80
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
WATCHLIST_FILE = os.path.join(DATA_DIR, "daily_watchlist.json")
LIVE_SCORES_FILE = os.path.join(DATA_DIR, "live_scores.json")
SIGNAL_QUEUE_FILE = os.path.join(DATA_DIR, "signal_queue.json")
FLOW_PIPELINE_FILE = os.path.join(DATA_DIR, "flow_pipeline_history.json")

# Flow Monitor thresholds
FLOW_MIN_PREMIUM = 50_000
FLOW_MIN_OI_RATIO = 1.5
FLOW_SWEEP_ONLY = True
FLOW_POLL_INTERVAL = 15

# Risk Auditor constraints
MAX_POSITION_PCT = 5.0
MAX_CORRELATED_EXPOSURE = 15.0
MAX_SINGLE_DAY_TRADES = 8

TRIGGERS = {
    "pullback_entry": {
        "min_score": 75,
        "conditions": ["williams_r_cross_above_neg80", "near_vwap"],
        "description": "Score 75+ AND Williams %R crosses above -80 AND price near VWAP",
    },
    "breakout_entry": {
        "min_score": 80,
        "conditions": ["price_above_20bar_high", "volume_surge"],
        "description": "Score 80+ AND price > 20-bar high AND volume ratio > 1.5",
    },
    "mean_reversion": {
        "min_score": 70,
        "conditions": ["rsi_oversold", "williams_r_oversold", "above_sma200"],
        "description": "Score 70+ AND RSI < 30 AND Williams %R < -85 AND price > SMA200",
    },
    "flow_conviction": {
        "min_score": 70,
        "conditions": ["flow_audited_pass", "gex_aligned"],
        "description": "Score 70+ AND options flow pipeline approved AND GEX aligned",
    },
}


# ========== OPTIONS FLOW PIPELINE DATA STRUCTURES ==========


@dataclass
class FlowSignal:
    """Represents one institutional options flow event moving through the pipeline."""

    ticker: str
    option_type: str  # 'call' or 'put'
    strike: float
    expiry: str
    premium: float
    volume: int
    open_interest: int
    oi_ratio: float
    is_sweep: bool
    is_aggressive: bool
    sentiment: str  # 'bullish' or 'bearish'
    raw_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    pipeline_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    # Enriched by Contextualizer
    gex_value: Optional[float] = None
    gex_flip_strike: Optional[float] = None
    gex_alignment: Optional[str] = None  # 'aligned', 'neutral', 'opposed'
    iv_rank: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    # Enriched by Sentiment Agent
    market_tide: Optional[str] = None  # 'bullish', 'bearish', 'neutral'
    tide_score: Optional[float] = None
    sector_tide: Optional[str] = None
    sentiment_alignment: Optional[str] = None  # 'aligned', 'conflicting'
    # Enriched by Risk Auditor
    risk_verdict: Optional[str] = None  # 'APPROVED', 'REJECTED', 'REDUCED'
    risk_reason: Optional[str] = None
    suggested_size_pct: Optional[float] = None
    portfolio_heat: Optional[float] = None
    # Pipeline tracking
    stages_completed: List[str] = field(default_factory=list)
    stage_latencies_ms: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "FlowSignal":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


# ========== AGENT 1: FLOW MONITOR ==========


class FlowMonitorAgent:
    """
    Agent 1 in the Options Flow Pipeline.
    Polls Unusual Whales /flow WebSocket/REST endpoint for real-time
    aggressive institutional sweeps. Filters by premium size, OI ratio,
    and sweep classification. Publishes qualifying flows to FLOW_RAW topic.
    """

    AGENT_ID = "flow_monitor"

    def __init__(self, blackboard: Blackboard):
        self.bb = blackboard
        self._seen_ids: deque = deque(maxlen=500)
        self._session: Optional[Any] = None
        self._last_poll = 0.0
        self._stats = {"polled": 0, "passed": 0, "filtered": 0}
        logger.info("[FlowMonitor] Initialized")

    def _qualifies(self, flow: Dict) -> bool:
        """Check if a raw flow event meets institutional sweep criteria."""
        premium = float(flow.get("total_premium", 0) or flow.get("premium", 0) or 0)
        if premium < FLOW_MIN_PREMIUM:
            return False
        oi = int(flow.get("open_interest", 1) or 1)
        vol = int(flow.get("volume", 0) or 0)
        if oi > 0 and vol / oi < FLOW_MIN_OI_RATIO:
            return False
        if FLOW_SWEEP_ONLY:
            is_sweep = (
                flow.get("is_sweep", False) or flow.get("type", "").lower() == "sweep"
            )
            if not is_sweep:
                return False
        return True

    def _parse_flow(self, raw: Dict) -> FlowSignal:
        """Parse raw API response into a FlowSignal."""
        ticker = (raw.get("underlying_symbol") or raw.get("ticker", "")).upper()
        otype = (raw.get("put_call") or raw.get("option_type", "call")).lower()
        strike = float(raw.get("strike_price", 0) or raw.get("strike", 0))
        expiry = raw.get("expires_date", "") or raw.get("expiry", "")
        premium = float(raw.get("total_premium", 0) or raw.get("premium", 0))
        volume = int(raw.get("volume", 0) or 0)
        oi = int(raw.get("open_interest", 0) or 0)
        oi_ratio = volume / oi if oi > 0 else 0.0
        is_sweep = bool(
            raw.get("is_sweep", False) or raw.get("type", "").lower() == "sweep"
        )
        bid = float(raw.get("bid", 0) or 0)
        ask = float(raw.get("ask", 0) or 0)
        trade_price = float(raw.get("price", 0) or 0)
        is_aggressive = trade_price >= ask * 0.95 if ask > 0 else False
        if otype == "call":
            sentiment = "bullish" if is_aggressive else "bearish"
        else:
            sentiment = "bearish" if is_aggressive else "bullish"
        return FlowSignal(
            ticker=ticker,
            option_type=otype,
            strike=strike,
            expiry=expiry,
            premium=premium,
            volume=volume,
            open_interest=oi,
            oi_ratio=round(oi_ratio, 2),
            is_sweep=is_sweep,
            is_aggressive=is_aggressive,
            sentiment=sentiment,
        )

    async def _fetch_flows(self) -> List[Dict]:
        """Fetch latest flow data from Unusual Whales API."""
        if not HAS_AIOHTTP or not UNUSUALWHALES_API_KEY:
            return []
        url = f"{UNUSUALWHALES_BASE_URL}/stock/flow"
        headers = {
            "Authorization": f"Bearer {UNUSUALWHALES_API_KEY}",
            "Accept": "application/json",
        }
        try:
            if self._session is None:
                self._session = aiohttp.ClientSession()
            async with self._session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", []) if isinstance(data, dict) else data
                else:
                    logger.warning(f"[FlowMonitor] API returned {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"[FlowMonitor] Fetch error: {e}")
            return []

    async def run(self):
        """Main polling loop. Publishes qualifying flows to FLOW_RAW."""
        logger.info("[FlowMonitor] Starting flow polling loop")
        while True:
            try:
                t0 = time.time()
                flows = await self._fetch_flows()
                self._stats["polled"] += 1
                for raw_flow in flows:
                    fid = (
                        raw_flow.get("id", "")
                        or str(hash(json.dumps(raw_flow, sort_keys=True, default=str)))[
                            :12
                        ]
                    )
                    if fid in self._seen_ids:
                        continue
                    self._seen_ids.append(fid)
                    if not self._qualifies(raw_flow):
                        self._stats["filtered"] += 1
                        continue
                    signal = self._parse_flow(raw_flow)
                    self._stats["passed"] += 1
                    latency = (time.time() - t0) * 1000
                    signal.stages_completed.append("flow_monitor")
                    signal.stage_latencies_ms["flow_monitor"] = round(latency, 1)
                    self.bb.record_pipeline_step(self.AGENT_ID, True, latency)
                    await self.bb.publish(
                        BlackboardMessage(
                            topic=Topic.FLOW_RAW,
                            payload=signal.to_dict(),
                            source_agent=self.AGENT_ID,
                            priority=2,
                            ttl_seconds=180,
                        )
                    )
                    logger.info(
                        f"[FlowMonitor] {signal.ticker} {signal.option_type.upper()} "
                        f"${signal.strike} exp={signal.expiry} "
                        f"prem=${signal.premium:,.0f} OI_ratio={signal.oi_ratio}"
                    )
                await self.bb.heartbeat(self.AGENT_ID)
                await asyncio.sleep(FLOW_POLL_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[FlowMonitor] Loop error: {e}")
                await asyncio.sleep(FLOW_POLL_INTERVAL)
        if self._session:
            await self._session.close()


# ========== AGENT 2: CONTEXTUALIZER ==========


class ContextualizerAgent:
    """
    Agent 2 in the Options Flow Pipeline.
    Subscribes to FLOW_RAW, enriches each FlowSignal with GEX (Gamma
    Exposure) data and greek context from the /greeks REST endpoint.
    Determines if the institutional flow aligns with or opposes the
    current Market Maker hedging regime. Publishes to FLOW_CONTEXTUALIZED.
    """

    AGENT_ID = "contextualizer"

    def __init__(self, blackboard: Blackboard):
        self.bb = blackboard
        self._session: Optional[Any] = None
        self._gex_cache: Dict[str, Tuple[Dict, float]] = {}
        self._cache_ttl = 120
        logger.info("[Contextualizer] Initialized")

    async def _fetch_greeks(self, ticker: str) -> Dict:
        """Fetch greeks/GEX data from Unusual Whales /greeks endpoint."""
        now = time.time()
        if ticker in self._gex_cache:
            cached, ts = self._gex_cache[ticker]
            if now - ts < self._cache_ttl:
                return cached
        if not HAS_AIOHTTP or not UNUSUALWHALES_API_KEY:
            return {}
        url = f"{UNUSUALWHALES_BASE_URL}/stock/{ticker}/greeks"
        headers = {
            "Authorization": f"Bearer {UNUSUALWHALES_API_KEY}",
            "Accept": "application/json",
        }
        try:
            if self._session is None:
                self._session = aiohttp.ClientSession()
            async with self._session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data.get("data", data) if isinstance(data, dict) else {}
                    self._gex_cache[ticker] = (result, now)
                    return result
                return {}
        except Exception as e:
            logger.error(f"[Contextualizer] Greeks fetch error for {ticker}: {e}")
            return {}

    def _compute_gex_alignment(self, signal: FlowSignal, greeks: Dict) -> FlowSignal:
        """Determine if the flow aligns with current GEX regime."""
        gex = float(greeks.get("gex", 0) or greeks.get("gamma_exposure", 0) or 0)
        flip = float(
            greeks.get("gex_flip_point", 0) or greeks.get("flip_strike", 0) or 0
        )
        iv_rank = float(
            greeks.get("iv_rank", 0) or greeks.get("implied_volatility_rank", 0) or 0
        )
        delta = float(greeks.get("delta", 0) or 0)
        gamma = float(greeks.get("gamma", 0) or 0)
        signal.gex_value = round(gex, 2)
        signal.gex_flip_strike = round(flip, 2) if flip else None
        signal.iv_rank = round(iv_rank, 1)
        signal.delta = round(delta, 4)
        signal.gamma = round(gamma, 4)
        if gex > 0:
            if signal.sentiment == "bullish":
                signal.gex_alignment = "aligned"
            else:
                signal.gex_alignment = "opposed"
        elif gex < 0:
            if signal.sentiment == "bearish":
                signal.gex_alignment = "aligned"
            else:
                signal.gex_alignment = "neutral"
        else:
            signal.gex_alignment = "neutral"
        return signal

    async def run(self):
        """Subscribe to FLOW_RAW, enrich, publish to FLOW_CONTEXTUALIZED."""
        queue = await self.bb.subscribe(Topic.FLOW_RAW, self.AGENT_ID)
        logger.info("[Contextualizer] Listening on flow_raw topic")
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=5.0)
                if isinstance(msg, BlackboardMessage) and not msg.is_expired():
                    t0 = time.time()
                    signal = FlowSignal.from_dict(msg.payload)
                    greeks = await self._fetch_greeks(signal.ticker)
                    signal = self._compute_gex_alignment(signal, greeks)
                    latency = (time.time() - t0) * 1000
                    signal.stages_completed.append("contextualizer")
                    signal.stage_latencies_ms["contextualizer"] = round(latency, 1)
                    passed = signal.gex_alignment != "opposed"
                    self.bb.record_pipeline_step(self.AGENT_ID, passed, latency)
                    if passed:
                        await self.bb.publish(
                            BlackboardMessage(
                                topic=Topic.FLOW_CONTEXTUALIZED,
                                payload=signal.to_dict(),
                                source_agent=self.AGENT_ID,
                                priority=2,
                                ttl_seconds=180,
                            )
                        )
                        logger.info(
                            f"[Contextualizer] {signal.ticker} GEX={signal.gex_value} "
                            f"align={signal.gex_alignment} IV_rank={signal.iv_rank}"
                        )
                    else:
                        logger.info(
                            f"[Contextualizer] FILTERED {signal.ticker}: "
                            f"GEX opposed (gex={signal.gex_value}, sentiment={signal.sentiment})"
                        )
            except asyncio.TimeoutError:
                await self.bb.heartbeat(self.AGENT_ID)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Contextualizer] Error: {e}")
                await asyncio.sleep(1)
        if self._session:
            await self._session.close()


# ========== AGENT 3: SENTIMENT AGENT ==========


class SentimentAgent:
    """
    Agent 3 in the Options Flow Pipeline.
    Subscribes to FLOW_CONTEXTUALIZED, enriches with market-wide
    sentiment data from the /market-tide REST endpoint.
    Determines if the flow's directional bias aligns with the
    broader market tide. Publishes to FLOW_SENTIMENT.
    """

    AGENT_ID = "sentiment_agent"

    def __init__(self, blackboard: Blackboard):
        self.bb = blackboard
        self._session: Optional[Any] = None
        self._tide_cache: Tuple[Optional[Dict], float] = (None, 0.0)
        self._sector_cache: Dict[str, Tuple[Dict, float]] = {}
        self._cache_ttl = 60
        logger.info("[SentimentAgent] Initialized")

    async def _fetch_market_tide(self) -> Dict:
        """Fetch market-wide sentiment from UW /market-tide."""
        now = time.time()
        cached, ts = self._tide_cache
        if cached and now - ts < self._cache_ttl:
            return cached
        if not HAS_AIOHTTP or not UNUSUALWHALES_API_KEY:
            return {}
        url = f"{UNUSUALWHALES_BASE_URL}/market/market-tide"
        headers = {
            "Authorization": f"Bearer {UNUSUALWHALES_API_KEY}",
            "Accept": "application/json",
        }
        try:
            if self._session is None:
                self._session = aiohttp.ClientSession()
            async with self._session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data.get("data", data) if isinstance(data, dict) else {}
                    self._tide_cache = (result, now)
                    return result
                return {}
        except Exception as e:
            logger.error(f"[SentimentAgent] Market tide fetch error: {e}")
            return {}

    def _evaluate_sentiment(self, signal: FlowSignal, tide: Dict) -> FlowSignal:
        """Compare flow sentiment with market tide."""
        call_prem = float(tide.get("net_call_premium", 0) or 0)
        put_prem = float(tide.get("net_put_premium", 0) or 0)
        net = call_prem - put_prem
        if net > 0:
            signal.market_tide = "bullish"
        elif net < 0:
            signal.market_tide = "bearish"
        else:
            signal.market_tide = "neutral"
        total = abs(call_prem) + abs(put_prem)
        signal.tide_score = round(net / total * 100, 1) if total > 0 else 0.0
        if signal.sentiment == signal.market_tide:
            signal.sentiment_alignment = "aligned"
        elif signal.market_tide == "neutral":
            signal.sentiment_alignment = "aligned"
        else:
            signal.sentiment_alignment = "conflicting"
        return signal

    async def run(self):
        """Subscribe to FLOW_CONTEXTUALIZED, enrich, publish to FLOW_SENTIMENT."""
        queue = await self.bb.subscribe(Topic.FLOW_CONTEXTUALIZED, self.AGENT_ID)
        logger.info("[SentimentAgent] Listening on flow_contextualized topic")
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=5.0)
                if isinstance(msg, BlackboardMessage) and not msg.is_expired():
                    t0 = time.time()
                    signal = FlowSignal.from_dict(msg.payload)
                    tide = await self._fetch_market_tide()
                    signal = self._evaluate_sentiment(signal, tide)
                    latency = (time.time() - t0) * 1000
                    signal.stages_completed.append("sentiment_agent")
                    signal.stage_latencies_ms["sentiment_agent"] = round(latency, 1)
                    passed = signal.sentiment_alignment == "aligned"
                    self.bb.record_pipeline_step(self.AGENT_ID, passed, latency)
                    await self.bb.publish(
                        BlackboardMessage(
                            topic=Topic.FLOW_SENTIMENT,
                            payload=signal.to_dict(),
                            source_agent=self.AGENT_ID,
                            priority=2,
                            ttl_seconds=180,
                        )
                    )
                    log_level = "info" if passed else "warning"
                    getattr(logger, log_level)(
                        f"[SentimentAgent] {signal.ticker} tide={signal.market_tide} "
                        f"score={signal.tide_score} align={signal.sentiment_alignment}"
                    )
            except asyncio.TimeoutError:
                await self.bb.heartbeat(self.AGENT_ID)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SentimentAgent] Error: {e}")
                await asyncio.sleep(1)
        if self._session:
            await self._session.close()


# ========== AGENT 4: RISK AUDITOR ==========


class RiskAuditorAgent:
    """
    Agent 4 in the Options Flow Pipeline.
    Subscribes to FLOW_SENTIMENT, applies portfolio-level risk
    constraints before allowing a flow signal to reach execution.
    Checks: position sizing, sector correlation limits, daily trade
    count, blacklist status, and current P&L drawdown.
    Publishes final go/no-go to FLOW_AUDITED.
    """

    AGENT_ID = "risk_auditor"

    def __init__(self, blackboard: Blackboard):
        self.bb = blackboard
        self._trades_today: List[str] = []
        self._sector_exposure: Dict[str, float] = defaultdict(float)
        self._daily_pnl: float = 0.0
        self._last_reset_date: str = ""
        logger.info("[RiskAuditor] Initialized")

    def _reset_daily_if_needed(self):
        """Reset daily counters at midnight."""
        today = date.today().isoformat()
        if self._last_reset_date != today:
            self._trades_today = []
            self._daily_pnl = 0.0
            self._sector_exposure = defaultdict(float)
            self._last_reset_date = today

    def _check_blacklist(self, ticker: str) -> Optional[str]:
        """Check if ticker is blacklisted in memory_v3."""
        if HAS_MEMORY and trade_memory:
            if trade_memory.is_blacklisted(ticker):
                return f"{ticker} is blacklisted (consecutive losses)"
        return None

    def _check_daily_limit(self) -> Optional[str]:
        """Check if daily trade count exceeded."""
        if len(self._trades_today) >= MAX_SINGLE_DAY_TRADES:
            return f"Daily trade limit reached ({MAX_SINGLE_DAY_TRADES})"
        return None

    def _check_drawdown(self) -> Optional[str]:
        """Check if daily P&L drawdown exceeded."""
        if self._daily_pnl <= -MAX_DAILY_LOSS_PCT:
            return f"Daily loss limit hit ({self._daily_pnl:.1f}% vs max {MAX_DAILY_LOSS_PCT}%)"
        return None

    def _compute_position_size(self, signal: FlowSignal) -> float:
        """Compute suggested position size as portfolio percentage."""
        base_pct = DEFAULT_RISK_PCT
        if (
            signal.gex_alignment == "aligned"
            and signal.sentiment_alignment == "aligned"
        ):
            size = base_pct * 1.2
        elif signal.sentiment_alignment == "conflicting":
            size = base_pct * 0.6
        else:
            size = base_pct
        size = min(size, MAX_POSITION_PCT)
        if signal.iv_rank and signal.iv_rank > 70:
            size *= 0.8
        return round(size, 2)

    def _audit(self, signal: FlowSignal) -> FlowSignal:
        """Run all risk checks on the signal."""
        self._reset_daily_if_needed()
        reasons = []
        bl = self._check_blacklist(signal.ticker)
        if bl:
            reasons.append(bl)
        dl = self._check_daily_limit()
        if dl:
            reasons.append(dl)
        dd = self._check_drawdown()
        if dd:
            reasons.append(dd)
        if reasons:
            signal.risk_verdict = "REJECTED"
            signal.risk_reason = "; ".join(reasons)
            signal.suggested_size_pct = 0.0
        else:
            size = self._compute_position_size(signal)
            signal.suggested_size_pct = size
            signal.portfolio_heat = round(sum(self._sector_exposure.values()) + size, 2)
            if signal.sentiment_alignment == "conflicting":
                signal.risk_verdict = "REDUCED"
                signal.risk_reason = "Sentiment misaligned - reduced size"
            else:
                signal.risk_verdict = "APPROVED"
                signal.risk_reason = "All checks passed"
            self._trades_today.append(signal.ticker)
        return signal

    async def run(self):
        """Subscribe to FLOW_SENTIMENT, audit, publish to FLOW_AUDITED."""
        queue = await self.bb.subscribe(Topic.FLOW_SENTIMENT, self.AGENT_ID)
        logger.info("[RiskAuditor] Listening on flow_sentiment topic")
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=5.0)
                if isinstance(msg, BlackboardMessage) and not msg.is_expired():
                    t0 = time.time()
                    signal = FlowSignal.from_dict(msg.payload)
                    signal = self._audit(signal)
                    latency = (time.time() - t0) * 1000
                    signal.stages_completed.append("risk_auditor")
                    signal.stage_latencies_ms["risk_auditor"] = round(latency, 1)
                    passed = signal.risk_verdict in ("APPROVED", "REDUCED")
                    self.bb.record_pipeline_step(self.AGENT_ID, passed, latency)
                    await self.bb.publish(
                        BlackboardMessage(
                            topic=Topic.FLOW_AUDITED,
                            payload=signal.to_dict(),
                            source_agent=self.AGENT_ID,
                            priority=1,
                            ttl_seconds=300,
                        )
                    )
                    if passed:
                        await self.bb.publish(
                            BlackboardMessage(
                                topic=Topic.ALPHA_SIGNALS,
                                payload={
                                    "ticker": signal.ticker,
                                    "signal_type": "flow_pipeline",
                                    "sentiment": signal.sentiment,
                                    "gex_alignment": signal.gex_alignment,
                                    "market_tide": signal.market_tide,
                                    "risk_verdict": signal.risk_verdict,
                                    "suggested_size_pct": signal.suggested_size_pct,
                                    "premium": signal.premium,
                                    "pipeline_id": signal.pipeline_id,
                                },
                                source_agent=self.AGENT_ID,
                                priority=1,
                                ttl_seconds=300,
                            )
                        )
                        self._persist_flow(signal)
                    icon = "PASS" if passed else "REJECT"
                    logger.info(
                        f"[RiskAuditor] [{icon}] {signal.ticker} "
                        f"verdict={signal.risk_verdict} size={signal.suggested_size_pct}% "
                        f"reason={signal.risk_reason}"
                    )
            except asyncio.TimeoutError:
                await self.bb.heartbeat(self.AGENT_ID)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[RiskAuditor] Error: {e}")
                await asyncio.sleep(1)

    def _persist_flow(self, signal: FlowSignal):
        """Save approved flow signals to disk for review."""
        try:
            history = []
            if os.path.exists(FLOW_PIPELINE_FILE):
                with open(FLOW_PIPELINE_FILE, "r") as f:
                    history = json.load(f)
            history.append(signal.to_dict())
            history = history[-200:]
            with open(FLOW_PIPELINE_FILE, "w") as f:
                json.dump(history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"[RiskAuditor] Persist error: {e}")


# ========== ROLLING INDICATORS (preserved from v5.0) ==========


class RollingIndicators:
    """Maintains rolling window of bars and computes fast indicators."""

    def __init__(self, window: int = 60):
        self.window = window
        self.closes = deque(maxlen=window)
        self.highs = deque(maxlen=window)
        self.lows = deque(maxlen=window)
        self.volumes = deque(maxlen=window)
        self.opens = deque(maxlen=window)
        self.timestamps = deque(maxlen=window)
        self._prev_williams_r = None

    def add_bar(self, bar: Dict):
        self.closes.append(float(bar.get("close", 0)))
        self.highs.append(float(bar.get("high", 0)))
        self.lows.append(float(bar.get("low", 0)))
        self.volumes.append(float(bar.get("volume", 0)))
        self.opens.append(float(bar.get("open", 0)))
        self.timestamps.append(bar.get("timestamp", datetime.now().isoformat()))

    @property
    def bar_count(self) -> int:
        return len(self.closes)

    def compute_rsi(self, period: int = 14) -> Optional[float]:
        if len(self.closes) < period + 1:
            return None
        closes = list(self.closes)
        deltas = [closes[i] - closes[i - 1] for i in range(-period, 0)]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        avg_gain = sum(gains) / period if gains else 0.0001
        avg_loss = sum(losses) / period if losses else 0.0001
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        return 100 - (100 / (1 + rs))

    def compute_williams_r(self, period: int = 14) -> Optional[float]:
        if len(self.closes) < period:
            return None
        highs = list(self.highs)[-period:]
        lows = list(self.lows)[-period:]
        highest, lowest = max(highs), min(lows)
        if highest == lowest:
            return -50.0
        return ((highest - self.closes[-1]) / (highest - lowest)) * -100

    def compute_vwap(self) -> Optional[float]:
        if len(self.closes) < 2:
            return None
        tp = [(h + l + c) / 3 for h, l, c in zip(self.highs, self.lows, self.closes)]
        cum_vol = sum(self.volumes)
        if cum_vol == 0:
            return None
        return sum(t * v for t, v in zip(tp, self.volumes)) / cum_vol

    def compute_volume_ratio(self, period: int = 20) -> Optional[float]:
        if len(self.volumes) < period:
            return None
        avg = sum(list(self.volumes)[-period:]) / period
        return self.volumes[-1] / avg if avg > 0 else None

    def compute_sma(self, period: int = 20) -> Optional[float]:
        if len(self.closes) < period:
            return None
        return sum(list(self.closes)[-period:]) / period

    def compute_atr(self, period: int = 14) -> Optional[float]:
        if len(self.closes) < period + 1:
            return None
        trs, closes, highs, lows = (
            [],
            list(self.closes),
            list(self.highs),
            list(self.lows),
        )
        for i in range(-period, 0):
            trs.append(
                max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1]),
                )
            )
        return sum(trs) / period

    def get_20bar_high(self) -> Optional[float]:
        if len(self.highs) < 20:
            return None
        return max(list(self.highs)[-20:])

    def williams_r_crossed_above(self, threshold: float = -80) -> bool:
        current = self.compute_williams_r()
        if current is None or self._prev_williams_r is None:
            return False
        return self._prev_williams_r <= threshold < current

    def compute_all(self) -> Dict:
        rsi = self.compute_rsi()
        wr = self.compute_williams_r()
        vwap = self.compute_vwap()
        vol_ratio = self.compute_volume_ratio()
        sma_20 = self.compute_sma(20)
        sma_200 = self.compute_sma(200) if len(self.closes) >= 200 else None
        atr = self.compute_atr()
        bar_high_20 = self.get_20bar_high()
        wr_crossed = self.williams_r_crossed_above(-80)
        self._prev_williams_r = wr
        price = self.closes[-1] if self.closes else 0
        vwap_dist = (
            abs(price - vwap) / atr if vwap and atr and atr > 0 and price else None
        )
        return {
            "price": price,
            "rsi": rsi,
            "williams_r": wr,
            "vwap": vwap,
            "vwap_distance_atr": vwap_dist,
            "volume_ratio": vol_ratio,
            "sma_20": sma_20,
            "sma_200": sma_200,
            "atr": atr,
            "bar_high_20": bar_high_20,
            "williams_r_crossed_above_neg80": wr_crossed,
            "bar_count": self.bar_count,
            "last_update": datetime.now().isoformat(),
        }


# ========== STREAMING ENGINE v6.1 ==========


class StreamingEngine:
    """
    Real-time event-driven trading engine v6.1.
    Hosts the Blackboard message broker + multi-agent sentiment/flow pipeline.
    Manages WebSocket bar connections, scoring, triggers, and dynamic agent discovery.
    """

    def __init__(self, blackboard: Optional[Blackboard] = None):
        self.watchlist: Dict[str, Dict] = {}
        self.indicators: Dict[str, RollingIndicators] = {}
        self.live_scores: Dict[str, Dict] = {}
        self.signal_queue: asyncio.Queue = asyncio.Queue()
        self.error_counts: Dict[str, int] = {}
        self.running = False
        self.stream = None
        self._last_persist = time.time()
        self._regime_data = {}
        self._macro_data = {}
        self._scorer = None
        self.blackboard = blackboard or get_blackboard()

        # Core flow pipeline agents
        self._flow_monitor = FlowMonitorAgent(self.blackboard)
        self._contextualizer = ContextualizerAgent(self.blackboard)
        self._sentiment_agent = SentimentAgent(self.blackboard)
        self._risk_auditor = RiskAuditorAgent(self.blackboard)

        # Dynamic Scanner Agents
        self._scanner_tasks = []

        self._flow_approved: Dict[str, Dict] = {}
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_file = os.path.join(
            LOGS_DIR, f"streaming_engine_{date.today().isoformat()}.log"
        )
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(fh)
        logger.setLevel(logging.INFO)

    def load_watchlist(self) -> List[str]:
        if not os.path.exists(WATCHLIST_FILE):
            logger.warning(f"No watchlist file at {WATCHLIST_FILE}")
            return []
        try:
            with open(WATCHLIST_FILE, "r") as f:
                data = json.load(f)
            tickers = []
            if isinstance(data, list):
                for item in data:
                    ticker = item.get("ticker", "")
                    if ticker:
                        self.watchlist[ticker] = item
                        tickers.append(ticker)
            elif isinstance(data, dict):
                for item in data.get("watchlist", []):
                    ticker = item.get("ticker", "")
                    if ticker:
                        self.watchlist[ticker] = item
                        tickers.append(ticker)
            tickers = tickers[:MAX_SUBSCRIPTIONS]
            logger.info(f"Loaded {len(tickers)} tickers from watchlist")
            return tickers
        except Exception as e:
            logger.error(f"Failed to load watchlist: {e}")
            return []

    def add_ticker(self, ticker: str, metadata: Optional[Dict] = None):
        if len(self.watchlist) >= MAX_SUBSCRIPTIONS:
            return False
        ticker = ticker.upper().strip()
        if ticker in self.watchlist:
            return True
        self.watchlist[ticker] = metadata or {"ticker": ticker, "source": "manual"}
        self.indicators[ticker] = RollingIndicators()
        logger.info(f"Added {ticker} to streaming watchlist")
        return True

    def remove_ticker(self, ticker: str):
        ticker = ticker.upper().strip()
        self.watchlist.pop(ticker, None)
        self.indicators.pop(ticker, None)
        self.live_scores.pop(ticker, None)
        self.error_counts.pop(ticker, None)

    def _init_scorer(self):
        if not CompositeScorer:
            logger.warning("CompositeScorer not available")
            return
        try:
            if regime_detector:
                rs = regime_detector.get_regime_summary()
                self._regime_data = rs if isinstance(rs, dict) else {"regime": str(rs)}
            else:
                self._regime_data = {"regime": "GREEN"}
            if get_macro_snapshot:
                self._macro_data = get_macro_snapshot() or {}
            else:
                self._macro_data = {}
            self._scorer = CompositeScorer(
                regime_data=self._regime_data, macro_data=self._macro_data
            )
            logger.info(
                f"Scorer initialized: regime={self._regime_data.get('regime', 'UNKNOWN')}"
            )
        except Exception as e:
            logger.error(f"Failed to init scorer: {e}")
            self._scorer = None

    def _score_ticker(self, ticker: str, indicators: Dict) -> Optional[Dict]:
        if not self._scorer:
            return None
        try:
            tech = {
                "ticker": ticker,
                "price": indicators.get("price", 0),
                "rsi": indicators.get("rsi"),
                "williams_r": indicators.get("williams_r"),
                "vwap": indicators.get("vwap"),
                "volume_ratio": indicators.get("volume_ratio"),
                "sma_20": indicators.get("sma_20"),
                "sma_200": indicators.get("sma_200"),
                "atr": indicators.get("atr"),
                "adx": self.watchlist.get(ticker, {}).get("adx"),
                "macd_hist": self.watchlist.get(ticker, {}).get("macd_hist"),
                "ema_50": self.watchlist.get(ticker, {}).get("ema_50"),
                "price_change_5d": self.watchlist.get(ticker, {}).get(
                    "price_change_5d"
                ),
                "sector": self.watchlist.get(ticker, {}).get("sector", ""),
                "earnings_safe": True,
            }
            bd = self._scorer.score_candidate(tech)
            return {
                "ticker": ticker,
                "score": bd.total,
                "tier": bd.tier,
                "regime_score": bd.regime_score,
                "trend_score": bd.trend_score,
                "pullback_score": bd.pullback_score,
                "momentum_score": bd.momentum_score,
                "pattern_score": bd.pattern_score,
                "last_update": datetime.now().isoformat(),
                "pillars": {
                    "regime": bd.regime_score,
                    "trend": bd.trend_score,
                    "pullback": bd.pullback_score,
                    "momentum": bd.momentum_score,
                    "pattern": bd.pattern_score,
                },
            }
        except Exception as e:
            logger.error(f"Scoring failed for {ticker}: {e}")
            return None

    def _check_triggers(
        self, ticker: str, indicators: Dict, score_data: Dict
    ) -> Optional[Dict]:
        score = score_data.get("score", 0)
        for tname, tcfg in TRIGGERS.items():
            if score < tcfg["min_score"]:
                continue
            ok = True
            for cond in tcfg["conditions"]:
                if cond == "williams_r_cross_above_neg80":
                    ok = ok and indicators.get("williams_r_crossed_above_neg80", False)
                elif cond == "near_vwap":
                    vd = indicators.get("vwap_distance_atr")
                    ok = ok and (vd is not None and vd <= 0.5)
                elif cond == "price_above_20bar_high":
                    ok = ok and (
                        indicators.get("price", 0)
                        > (indicators.get("bar_high_20") or 0)
                    )
                elif cond == "volume_surge":
                    ok = ok and ((indicators.get("volume_ratio") or 0) >= 1.5)
                elif cond == "rsi_oversold":
                    ok = ok and ((indicators.get("rsi") or 100) < 30)
                elif cond == "williams_r_oversold":
                    ok = ok and ((indicators.get("williams_r") or 0) < -85)
                elif cond == "above_sma200":
                    ok = ok and (
                        indicators.get("price", 0)
                        > (indicators.get("sma_200") or float("inf"))
                    )
                elif cond == "flow_audited_pass":
                    ok = ok and (ticker in self._flow_approved)
                elif cond == "gex_aligned":
                    fa = self._flow_approved.get(ticker, {})
                    ok = ok and (fa.get("gex_alignment") in ("aligned", "neutral"))
            if ok:
                atr = indicators.get("atr", 0)
                entry = indicators.get("price", 0)
                sl = entry - (1.5 * atr) if atr else entry * 0.98
                tp = entry + (3.0 * atr) if atr else entry * 1.04
                signal = {
                    "event": "SIGNAL_READY",
                    "ticker": ticker,
                    "trigger": tname,
                    "score": score,
                    "tier": score_data.get("tier", ""),
                    "entry_price": round(entry, 2),
                    "stop_loss": round(sl, 2),
                    "take_profit": round(tp, 2),
                    "atr": round(atr, 4) if atr else 0,
                    "regime": self._regime_data.get("regime", "GREEN"),
                    "indicators": {
                        "rsi": indicators.get("rsi"),
                        "williams_r": indicators.get("williams_r"),
                        "volume_ratio": indicators.get("volume_ratio"),
                    },
                    "flow_data": self._flow_approved.get(ticker),
                    "timestamp": datetime.now().isoformat(),
                }
                logger.info(
                    f"SIGNAL_READY: {ticker} | {tname} | Score: {score:.1f} | Entry: ${entry:.2f}"
                )
                return signal
        return None

    async def _handle_bar(self, bar):
        """Process incoming bar from WebSocket and publish to Blackboard."""
        try:
            ticker = bar.symbol if hasattr(bar, "symbol") else str(bar.get("S", ""))
            if not ticker or ticker not in self.watchlist:
                return
            if ticker not in self.indicators:
                self.indicators[ticker] = RollingIndicators()
            bar_data = {
                "open": getattr(bar, "open", 0),
                "high": getattr(bar, "high", 0),
                "low": getattr(bar, "low", 0),
                "close": getattr(bar, "close", 0),
                "volume": getattr(bar, "volume", 0),
                "timestamp": (
                    getattr(bar, "timestamp", datetime.now()).isoformat()
                    if hasattr(getattr(bar, "timestamp", None), "isoformat")
                    else datetime.now().isoformat()
                ),
            }
            self.indicators[ticker].add_bar(bar_data)
            fast = self.indicators[ticker].compute_all()
            await self.blackboard.publish(
                BlackboardMessage(
                    topic=Topic.BAR_UPDATES,
                    payload={"ticker": ticker, "bar": bar_data, "indicators": fast},
                    source_agent="streaming_engine",
                    priority=3,
                    ttl_seconds=120,
                )
            )
            score_data = self._score_ticker(ticker, fast)
            if score_data:
                self.live_scores[ticker] = score_data
                signal = self._check_triggers(ticker, fast, score_data)
                if signal:
                    await self.signal_queue.put(signal)
                    self._save_signal(signal)
                    await self.blackboard.publish(
                        BlackboardMessage(
                            topic=Topic.SCORED_SIGNALS,
                            payload=signal,
                            source_agent="streaming_engine",
                            priority=1,
                            ttl_seconds=300,
                        )
                    )
                    if score_data["score"] >= SLACK_ALERT_THRESHOLD:
                        await self.blackboard.publish(
                            BlackboardMessage(
                                topic=Topic.EXECUTION_ORDERS,
                                payload=signal,
                                source_agent="streaming_engine",
                                priority=1,
                                ttl_seconds=300,
                            )
                        )
                        self._post_slack_alert(signal)
            now = time.time()
            if now - self._last_persist >= SCORE_PERSIST_INTERVAL:
                self._persist_state()
                self._last_persist = now
            self.error_counts[ticker] = 0
        except Exception as e:
            ts = getattr(bar, "symbol", "UNKNOWN")
            self.error_counts[ts] = self.error_counts.get(ts, 0) + 1
            logger.error(f"Bar handler error for {ts}: {e}")
            if self.error_counts.get(ts, 0) >= MAX_ERROR_COUNT:
                self.remove_ticker(ts)

    async def _consume_alpha_signals(self):
        """Consume alpha_signals from Tier 1 agents + flow pipeline via Blackboard."""
        queue = await self.blackboard.subscribe(Topic.ALPHA_SIGNALS, "streaming_engine")
        logger.info("[StreamingEngine] Listening for Tier 1 alpha signals...")
        while self.running:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=2.0)
                if isinstance(msg, BlackboardMessage) and not msg.is_expired():
                    payload = msg.payload
                    ticker = payload.get("ticker", "")
                    source = msg.source_agent
                    logger.info(
                        f"[StreamingEngine] Alpha signal from {source}: {ticker}"
                    )
                    if ticker and ticker not in self.watchlist:
                        self.add_ticker(
                            ticker,
                            {
                                "ticker": ticker,
                                "source": source,
                                "alpha_signal": payload,
                            },
                        )
                    if (
                        source == "risk_auditor"
                        and payload.get("signal_type") == "flow_pipeline"
                    ):
                        self._flow_approved[ticker] = payload
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[StreamingEngine] Alpha consumer error: {e}")
                await asyncio.sleep(1)

    async def _heartbeat_loop(self):
        while self.running:
            try:
                await self.blackboard.heartbeat("streaming_engine")
                stale = self.blackboard.get_stale_agents()
                if stale:
                    logger.warning(f"[StreamingEngine] Stale agents: {stale}")
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            await asyncio.sleep(30)

    def _persist_state(self):
        try:
            with open(LIVE_SCORES_FILE, "w") as f:
                json.dump(self.live_scores, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to persist state: {e}")

    def _save_signal(self, signal: Dict):
        try:
            signals = []
            if os.path.exists(SIGNAL_QUEUE_FILE):
                with open(SIGNAL_QUEUE_FILE, "r") as f:
                    signals = json.load(f)
            signals.append(signal)
            signals = signals[-100:]
            with open(SIGNAL_QUEUE_FILE, "w") as f:
                json.dump(signals, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save signal: {e}")

    def _post_slack_alert(self, signal: Dict):
        try:
            from slack_sdk import WebClient
            from config import SLACK_BOT_TOKEN, OC_TRADE_DESK_CHANNEL

            if not SLACK_BOT_TOKEN:
                return
            client = WebClient(token=SLACK_BOT_TOKEN)
            flow_info = ""
            if signal.get("flow_data"):
                fd = signal["flow_data"]
                flow_info = f" | Flow: {fd.get('sentiment','?')} GEX={fd.get('gex_alignment','?')}"
            msg = (
                f":rocket: *{signal['ticker']}* score {signal['score']:.1f} | "
                f"{signal['trigger']} trigger | "
                f"Entry: ${signal['entry_price']} | Stop: ${signal['stop_loss']} | "
                f"Target: ${signal['take_profit']}{flow_info}"
            )
            client.chat_postMessage(
                channel=OC_TRADE_DESK_CHANNEL, text=msg, mrkdwn=True
            )
        except Exception as e:
            logger.debug(f"Slack alert failed: {e}")

    def _load_persisted_state(self):
        if os.path.exists(LIVE_SCORES_FILE):
            try:
                with open(LIVE_SCORES_FILE, "r") as f:
                    self.live_scores = json.load(f)
                logger.info(f"Reloaded {len(self.live_scores)} scores from disk")
            except Exception as e:
                logger.warning(f"Could not reload state: {e}")

    def _launch_registered_agents(self, tickers: List[str]):
        """Dynamically launch all agents found in the scanner registry."""
        for name, agent_func in AGENT_REGISTRY.items():
            logger.info(f"Auto-launching registered agent: {name}")
            try:
                # Prediction agent does not take tickers list
                if "prediction" in name or "derivatives" in name:
                    task = asyncio.create_task(agent_func(blackboard=self.blackboard))
                else:
                    task = asyncio.create_task(
                        agent_func(symbols=tickers, blackboard=self.blackboard)
                    )
                self._scanner_tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to launch agent {name}: {e}")

    async def run(self):
        """
        Main streaming engine loop v6.1.
        Launches WebSocket + alpha consumer + heartbeat + 4-agent flow pipeline
        + auto-discovered sentiment agents.
        """
        if not ALPACA_SDK_AVAILABLE:
            logger.error("alpaca-py SDK not installed")
            return
        if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
            logger.error("ALPACA_API_KEY and ALPACA_SECRET_KEY required")
            return
        tickers = self.load_watchlist()
        if not tickers:
            logger.warning("No tickers in watchlist. Run daily_scanner first.")
            return
        for ticker in tickers:
            self.indicators[ticker] = RollingIndicators()
        self._init_scorer()
        self._load_persisted_state()
        self.running = True
        logger.info(f"Starting streaming engine v6.1 with {len(tickers)} tickers")
        logger.info("OpenClaw Streaming Engine v6.1 - Multi-Agent Sentiment Pipeline")
        logger.info(
            "Blackboard: %d topic subscriptions", len(self.blackboard._subscribers)
        )
        logger.info("Tickers: %d", len(tickers))
        logger.info("=" * 60)

        # Launch Core Pipeline Tasks
        alpha_task = asyncio.create_task(self._consume_alpha_signals())
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        flow_monitor_task = asyncio.create_task(self._flow_monitor.run())
        contextualizer_task = asyncio.create_task(self._contextualizer.run())
        sentiment_task = asyncio.create_task(self._sentiment_agent.run())
        risk_auditor_task = asyncio.create_task(self._risk_auditor.run())

        # Launch Dynamic Scanner Agents (Retail, Prediction, Derivatives, Whale Flow)
        self._launch_registered_agents(tickers)

        while self.running:
            try:
                self.stream = StockDataStream(
                    ALPACA_API_KEY, ALPACA_SECRET_KEY, feed=ALPACA_FEED
                )
                self.stream.subscribe_bars(
                    self._handle_bar, *list(self.watchlist.keys())
                )
                logger.info("WebSocket connected, streaming bars...")
                self.stream.run()
            except KeyboardInterrupt:
                logger.info("Streaming engine stopped by user")
                self.running = False
                break
            except ValueError as e:
                err_msg = str(e).lower()
                if "connection limit exceeded" in err_msg or "auth failed" in err_msg:
                    logger.warning(
                        "Alpaca data stream: %s. Only one WebSocket per account is allowed. "
                        "Close the FastAPI app (or set DISABLE_ALPACA_DATA_STREAM=1) or other apps using the same API key. "
                        "Retrying in 60s.",
                        e,
                    )
                    if self.running:
                        await asyncio.sleep(60)
                else:
                    raise
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if self.running:
                    await asyncio.sleep(RECONNECT_DELAY)

        # Cleanup
        for task in [
            alpha_task,
            heartbeat_task,
            flow_monitor_task,
            contextualizer_task,
            sentiment_task,
            risk_auditor_task,
        ] + self._scanner_tasks:
            task.cancel()
        self._persist_state()
        await self.blackboard.shutdown()
        logger.info("Streaming engine v6.1 shutdown complete")

    def show_watchlist(self):
        tickers = self.load_watchlist()
        if not tickers:
            logger.info("No tickers in watchlist.")
            return
        logger.info("Streaming Watchlist (%d tickers):", len(tickers))
        logger.info("=" * 50)
        for i, ticker in enumerate(tickers, 1):
            meta = self.watchlist.get(ticker, {})
            source = meta.get("source", "?")
            score = meta.get("composite_score", 0)
            flow = "FLOW" if ticker in self._flow_approved else ""
            logger.info(
                "  %2d. %-8s | source: %-12s | score: %s %s",
                i,
                ticker,
                source,
                score,
                flow,
            )

    def show_scores(self):
        if os.path.exists(LIVE_SCORES_FILE):
            try:
                with open(LIVE_SCORES_FILE, "r") as f:
                    scores = json.load(f)
            except Exception:
                scores = {}
        else:
            scores = self.live_scores
        if not scores:
            logger.info("No live scores available.")
            return
        logger.info("Live Scores (%d tickers):", len(scores))
        logger.info("=" * 85)
        logger.info(
            "  %-8s %6s %-16s %4s %4s %4s %4s %4s %5s %s",
            "Ticker",
            "Score",
            "Tier",
            "R",
            "T",
            "P",
            "M",
            "Pat",
            "Flow",
            "Updated",
        )
        logger.info("-" * 85)
        for ticker, data in sorted(
            scores.items(), key=lambda x: x[1].get("score", 0), reverse=True
        ):
            flow_tag = "YES" if ticker in self._flow_approved else ""
            logger.info(
                "  %-8s %6.1f %-16s %4.0f %4.0f %4.0f %4.0f %4.0f %5s %s",
                ticker,
                data.get("score", 0),
                data.get("tier", "?"),
                data.get("regime_score", 0),
                data.get("trend_score", 0),
                data.get("pullback_score", 0),
                data.get("momentum_score", 0),
                data.get("pattern_score", 0),
                flow_tag,
                data.get("last_update", "?")[-8:],
            )

    def show_blackboard_status(self):
        stats = self.blackboard.get_stats()
        logger.info("Blackboard Status (v6.1):")
        logger.info("=" * 60)
        logger.info("Topics & Subscribers:")
        for topic, count in stats.get("topics", {}).items():
            logger.info("  %-30s %s subscriber(s)", topic, count)
        logger.info("Message Counts:")
        for key, count in sorted(stats.get("message_counts", {}).items()):
            logger.info("  %-35s %s", key, count)
        logger.info("Agent Heartbeats:")
        for agent, ts in stats.get("agent_heartbeats", {}).items():
            logger.info("  %-25s last seen: %s", agent, ts)
        stale = self.blackboard.get_stale_agents()
        if stale:
            logger.warning("STALE AGENTS: %s", ", ".join(stale))

    def show_flow_status(self):
        """Display options flow pipeline status and metrics."""
        stats = self.blackboard.get_stats()
        pm = stats.get("pipeline_metrics", {})
        logger.info("Options Flow Agent Pipeline Status:")
        logger.info("=" * 70)
        agents = [
            ("flow_monitor", "Flow Monitor", "WebSocket /flow"),
            ("contextualizer", "Contextualizer", "REST /greeks"),
            ("sentiment_agent", "Sentiment Agent", "REST /market-tide"),
            ("risk_auditor", "Risk Auditor", "Internal Logic"),
        ]
        logger.info(
            "  %-20s %-20s %10s %8s %9s %8s",
            "Agent",
            "Input",
            "Processed",
            "Passed",
            "Rejected",
            "Avg ms",
        )
        logger.info("-" * 70)
        for aid, name, inp in agents:
            m = pm.get(aid, {})
            logger.info(
                "  %-20s %-20s %10d %8d %9d %8.1f",
                name,
                inp,
                m.get("processed", 0),
                m.get("passed", 0),
                m.get("rejected", 0),
                m.get("avg_latency_ms", 0),
            )
        total_in = pm.get("flow_monitor", {}).get("passed", 0)
        total_out = pm.get("risk_auditor", {}).get("passed", 0)
        pass_rate = (total_out / total_in * 100) if total_in > 0 else 0
        logger.info(
            "  Pipeline pass-through: %d/%d (%.1f%%)", total_out, total_in, pass_rate
        )
        if self._flow_approved:
            logger.info(
                "  Active flow-approved tickers: %s",
                ", ".join(self._flow_approved.keys()),
            )

    def show_flow_history(self):
        """Display recent flow pipeline signals."""
        if not os.path.exists(FLOW_PIPELINE_FILE):
            logger.info("No flow pipeline history.")
            return
        try:
            with open(FLOW_PIPELINE_FILE, "r") as f:
                history = json.load(f)
        except Exception:
            logger.error("Could not read flow history.")
            return
        logger.info("Recent Flow Pipeline Signals (%d total):", len(history))
        logger.info("=" * 90)
        for sig in history[-15:]:
            verdict = sig.get("risk_verdict", "?")
            icon = "OK" if verdict in ("APPROVED", "REDUCED") else "NO"
            total_lat = sum(sig.get("stage_latencies_ms", {}).values())
            logger.info(
                "  [%s] %-6s %-5s $%-8s prem=$%10.0f GEX=%-8s tide=%-8s verdict=%-9s size=%s%% (%.0fms)",
                icon,
                sig.get("ticker", "?"),
                sig.get("option_type", "?").upper(),
                sig.get("strike", 0),
                sig.get("premium", 0),
                sig.get("gex_alignment", "?"),
                sig.get("market_tide", "?"),
                verdict,
                sig.get("suggested_size_pct", 0),
                total_lat,
            )


# ========== MODULE-LEVEL FUNCTIONS ==========


def get_streaming_engine() -> StreamingEngine:
    if not hasattr(get_streaming_engine, "_instance"):
        get_streaming_engine._instance = StreamingEngine()
    return get_streaming_engine._instance


def export_watchlist(watchlist: List[Dict]):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(watchlist, f, indent=2, default=str)
        logger.info(f"Exported {len(watchlist)} tickers to {WATCHLIST_FILE}")
    except Exception as e:
        logger.error(f"Failed to export watchlist: {e}")


# ========== CLI ENTRY POINT ==========


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw Streaming Engine v6.1 - Multi-Agent Sentiment Pipeline"
    )
    parser.add_argument("--start", action="store_true", help="Start streaming daemon")
    parser.add_argument(
        "--watchlist", action="store_true", help="Show current subscriptions"
    )
    parser.add_argument("--scores", action="store_true", help="Print live scores table")
    parser.add_argument(
        "--blackboard", action="store_true", help="Show blackboard status"
    )
    parser.add_argument(
        "--flow-status", action="store_true", help="Show flow pipeline status"
    )
    parser.add_argument(
        "--flow-history", action="store_true", help="Show recent flow signals"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    engine = StreamingEngine()

    if args.watchlist:
        engine.show_watchlist()
    elif args.scores:
        engine.show_scores()
    elif args.blackboard:
        engine.show_blackboard_status()
    elif args.flow_status:
        engine.show_flow_status()
    elif args.flow_history:
        engine.show_flow_history()
    elif args.start:
        print("OpenClaw Streaming Engine v6.1 - Multi-Agent Sentiment Pipeline")
        print("Real-time event-driven trading with Multi-Agent Swarm")
        print("=" * 60)
        asyncio.run(engine.run())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
