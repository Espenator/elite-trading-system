"""FinBERT Social Sentiment Swarm Agent — continuous social media sentiment.

P1 Academic Edge Agent. Processes StockTwits, Twitter/X, and Reddit
through FinBERT for real-time sentiment analysis with volume anomaly
detection and contrarian filtering.

Academic basis: Bayesian-optimized FinBERT exceeds 70% F1 on return
prediction. Retail sentiment is a contrarian indicator at extremes
(>90% bullish → often precedes reversals).

Sub-agents:
- Firehose Collector: Ingests from StockTwits, Twitter/X, Reddit
- FinBERT Classifier: Batched sentiment classification every 60s
- Volume Anomaly Detector: 3σ mention volume spikes
- Contrarian Filter: Reduces confidence at crowd extremes

Council integration:
- regime_agent reads sentiment.crowd_extremes as contrarian signal
- strategy_agent reads sentiment.volume_anomalies for catalyst detection
"""
import logging
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "finbert_sentiment_agent"

# Volume anomaly threshold (standard deviations)
_VOLUME_ANOMALY_SIGMA = 3.0
# Crowd extreme thresholds
_EXTREME_BULLISH_PCT = 0.90
_EXTREME_BEARISH_PCT = 0.10
# Rolling history window
_ROLLING_WINDOW_HOURS = 168  # 7 days


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Aggregate social sentiment with FinBERT classification."""
    cfg = get_agent_thresholds()
    blackboard = context.get("blackboard")

    # Collect social media posts
    posts = await _collect_posts(symbol)
    if not posts:
        if blackboard:
            await blackboard.set("sentiment", "ticker_scores", {**blackboard.sentiment.get("ticker_scores", {}), symbol: 0.0})
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No social media data available for FinBERT analysis",
            weight=cfg.get("weight_finbert_sentiment_agent", 0.75),
            metadata={"data_available": False, "post_count": 0},
        )

    # Classify with FinBERT (or fallback)
    classified = await _classify_sentiment(posts)

    # Compute aggregate scores
    ticker_score, bullish_pct = _aggregate_scores(classified, symbol)

    # Volume anomaly detection
    volume_anomaly = _detect_volume_anomaly(symbol, len(posts))

    # Crowd extreme detection
    is_extreme, extreme_type = _detect_crowd_extreme(bullish_pct)

    # WSB momentum (Reddit-specific)
    wsb_score = _compute_wsb_momentum(classified)

    # Write to blackboard
    if blackboard:
        # Update ticker scores
        ticker_scores = {**blackboard.sentiment.get("ticker_scores", {}), symbol: ticker_score}
        await blackboard.set("sentiment", "ticker_scores", ticker_scores)

        # Update volume anomalies
        if volume_anomaly:
            volume_anomalies = blackboard.sentiment.get("volume_anomalies", [])
            if symbol not in volume_anomalies:
                await blackboard.set("sentiment", "volume_anomalies", volume_anomalies + [symbol])

        # Update crowd extremes
        if is_extreme:
            crowd_extremes = blackboard.sentiment.get("crowd_extremes", [])
            if symbol not in crowd_extremes:
                await blackboard.set("sentiment", "crowd_extremes", crowd_extremes + [symbol])

        # Update WSB momentum
        wsb_momentum = {**blackboard.sentiment.get("wsb_momentum", {}), symbol: wsb_score}
        await blackboard.set("sentiment", "wsb_momentum", wsb_momentum)

    # Determine vote with contrarian filter
    direction, confidence = _sentiment_to_vote(
        ticker_score, bullish_pct, is_extreme, extreme_type,
        volume_anomaly, cfg,
    )

    reasoning_parts = [
        f"FinBERT score={ticker_score:+.2f}",
        f"bullish%={bullish_pct:.0%}",
        f"posts={len(posts)}",
    ]
    if volume_anomaly:
        reasoning_parts.append("VOLUME SPIKE")
    if is_extreme:
        reasoning_parts.append(f"CROWD EXTREME ({extreme_type})")
    if wsb_score != 0:
        reasoning_parts.append(f"WSB={wsb_score:+.2f}")

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=", ".join(reasoning_parts),
        weight=cfg.get("weight_finbert_sentiment_agent", 0.75),
        metadata={
            "data_available": True,
            "post_count": len(posts),
            "ticker_score": ticker_score,
            "bullish_pct": bullish_pct,
            "volume_anomaly": volume_anomaly,
            "crowd_extreme": extreme_type if is_extreme else None,
            "wsb_momentum": wsb_score,
        },
    )


def _sentiment_to_vote(
    score: float, bullish_pct: float, is_extreme: bool,
    extreme_type: str, volume_anomaly: bool, cfg: Dict,
) -> Tuple[str, float]:
    """Convert sentiment to vote with contrarian filter at extremes."""
    base_confidence = 0.4

    if score > 0.3:
        direction = "buy"
        base_confidence = 0.5 + min(0.3, abs(score) * 0.5)
    elif score < -0.3:
        direction = "sell"
        base_confidence = 0.5 + min(0.3, abs(score) * 0.5)
    else:
        direction = "hold"
        base_confidence = 0.35

    # Volume anomaly + extreme sentiment = stronger signal
    if volume_anomaly and abs(score) > 0.3:
        base_confidence = min(0.85, base_confidence + 0.1)

    # CONTRARIAN FILTER: at crowd extremes, reduce confidence
    # Academic evidence: retail sentiment is contrarian at extremes
    if is_extreme:
        if extreme_type == "bullish" and direction == "buy":
            base_confidence *= 0.6  # Reduce buy confidence at extreme bullish
            logger.info("Contrarian filter: reducing buy confidence at extreme bullish for %s", "symbol")
        elif extreme_type == "bearish" and direction == "sell":
            base_confidence *= 0.6  # Reduce sell confidence at extreme bearish

    return direction, min(0.85, base_confidence)


async def _collect_posts(symbol: str) -> List[Dict[str, Any]]:
    """Collect social media posts from all sources."""
    all_posts: List[Dict] = []

    # StockTwits
    try:
        from app.services.stocktwits_service import get_symbol_messages
        st_posts = await get_symbol_messages(symbol, limit=50)
        for p in (st_posts or []):
            all_posts.append({"text": p.get("body", ""), "source": "stocktwits", **p})
    except Exception:
        pass

    # Reddit (PRAW) — r/wallstreetbets, r/stocks, r/options
    try:
        from app.services.reddit_service import search_ticker_mentions
        reddit_posts = await search_ticker_mentions(
            symbol, subreddits=["wallstreetbets", "stocks", "options"], limit=30,
        )
        for p in (reddit_posts or []):
            all_posts.append({"text": p.get("title", "") + " " + p.get("body", ""), "source": "reddit", **p})
    except Exception:
        pass

    # Twitter/X
    try:
        from app.services.twitter_service import search_cashtag
        tweets = await search_cashtag(symbol, limit=30)
        for t in (tweets or []):
            all_posts.append({"text": t.get("text", ""), "source": "twitter", **t})
    except Exception:
        pass

    # Fallback: existing social data from social_news_engine
    if not all_posts:
        try:
            from app.modules.social_news_engine.aggregators import aggregate_all
            items = aggregate_all([symbol], ["stockgeist", "newsapi"])
            for item in (items or []):
                all_posts.append({"text": item.get("text", ""), "source": item.get("source", "unknown")})
        except Exception:
            pass

    return all_posts


async def _classify_sentiment(posts: List[Dict]) -> List[Dict]:
    """Classify posts with FinBERT via brain_service or fallback."""
    # Try FinBERT via brain_service (GPU)
    try:
        from app.services.brain_client import get_brain_client
        brain = get_brain_client()
        texts = [p.get("text", "")[:512] for p in posts if p.get("text")]
        if texts:
            results = await brain.batch_sentiment(texts, model="finbert")
            for post, result in zip(posts, results):
                post["sentiment"] = result.get("label", "neutral")
                post["sentiment_score"] = result.get("score", 0.0)
            return posts
    except Exception:
        pass

    # Fallback: simple keyword sentiment
    for post in posts:
        text = post.get("text", "").lower()
        bullish_words = {"bull", "buy", "long", "moon", "rocket", "calls", "breakout", "green", "up"}
        bearish_words = {"bear", "sell", "short", "puts", "crash", "red", "down", "dump", "drill"}
        words = set(text.split())
        bull_count = len(words & bullish_words)
        bear_count = len(words & bearish_words)
        if bull_count > bear_count:
            post["sentiment"] = "bullish"
            post["sentiment_score"] = min(1.0, bull_count / max(1, bull_count + bear_count))
        elif bear_count > bull_count:
            post["sentiment"] = "bearish"
            post["sentiment_score"] = -min(1.0, bear_count / max(1, bull_count + bear_count))
        else:
            post["sentiment"] = "neutral"
            post["sentiment_score"] = 0.0

    return posts


def _aggregate_scores(posts: List[Dict], symbol: str) -> Tuple[float, float]:
    """Compute aggregate sentiment score and bullish percentage."""
    if not posts:
        return 0.0, 0.5

    scores = []
    bullish_count = 0
    total = 0

    for p in posts:
        score = p.get("sentiment_score", 0.0)
        sentiment = p.get("sentiment", "neutral")
        scores.append(score)
        total += 1
        if sentiment in ("bullish", "positive") or score > 0.2:
            bullish_count += 1

    avg_score = sum(scores) / max(1, len(scores))
    bullish_pct = bullish_count / max(1, total)

    return round(avg_score, 3), round(bullish_pct, 3)


# In-memory rolling mention volume (per-ticker)
_mention_history: Dict[str, List[int]] = defaultdict(list)


def _detect_volume_anomaly(symbol: str, current_count: int) -> bool:
    """Detect if current mention volume is >3σ above rolling average."""
    history = _mention_history[symbol]
    history.append(current_count)

    # Keep only last 168 data points (7 days at hourly)
    if len(history) > _ROLLING_WINDOW_HOURS:
        _mention_history[symbol] = history[-_ROLLING_WINDOW_HOURS:]
        history = _mention_history[symbol]

    if len(history) < 10:
        return False  # Not enough data

    mean = statistics.mean(history[:-1])
    stdev = statistics.stdev(history[:-1]) if len(history) > 2 else 1.0

    if stdev == 0:
        return current_count > mean * 3

    z_score = (current_count - mean) / stdev
    return z_score > _VOLUME_ANOMALY_SIGMA


def _detect_crowd_extreme(bullish_pct: float) -> Tuple[bool, str]:
    """Detect crowd extreme sentiment levels."""
    if bullish_pct >= _EXTREME_BULLISH_PCT:
        return True, "bullish"
    elif bullish_pct <= _EXTREME_BEARISH_PCT:
        return True, "bearish"
    return False, ""


def _compute_wsb_momentum(posts: List[Dict]) -> float:
    """Compute WallStreetBets-specific momentum score."""
    wsb_posts = [p for p in posts if p.get("source") == "reddit"
                 and "wallstreetbets" in str(p.get("subreddit", "")).lower()]
    if not wsb_posts:
        return 0.0

    scores = [p.get("sentiment_score", 0.0) for p in wsb_posts]
    return round(sum(scores) / max(1, len(scores)), 3)
