"""SEC Form 4 Insider Filing Agent — insider transaction tracking and scoring.

P0 Academic Edge Agent. Tracks insider purchases by corporate officers as
one of the most persistent alpha signals in academic finance.

Academic basis: Microcap insider purchases show 3.5% mean 30-day CAR,
rising to 6.3% for filings coinciding with positive momentum. Distance
from 52-week high contributes ~36% of predictive power.

Sub-agents:
- Filing Ingestion: Polls SEC EDGAR XBRL feed for Form 4 filings
- Cluster Detection: Identifies multi-insider purchases within 7-day window
- Context Enrichment: Cross-references with earnings, analyst downgrades, short interest
- Signal Scoring: Composite score weighting purchase size, role, cluster status

Council integration: Runs as S1 perception agent in parallel with market_perception.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "insider_agent"

# Rolling window for cluster detection
_CLUSTER_WINDOW_DAYS = 7
_CLUSTER_MIN_INSIDERS = 2

# Insider role weights (CEO/CFO weighted higher per academic evidence)
_ROLE_WEIGHTS = {
    "ceo": 1.5,
    "chief executive officer": 1.5,
    "cfo": 1.4,
    "chief financial officer": 1.4,
    "president": 1.3,
    "coo": 1.2,
    "director": 1.0,
    "10% owner": 0.9,
    "vp": 0.8,
    "officer": 0.8,
}


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Analyze insider filing activity for the given symbol."""
    cfg = get_agent_thresholds()
    f = features.get("features", features)
    blackboard = context.get("blackboard")

    # Fetch recent Form 4 filings
    filings = await _fetch_insider_filings(symbol)
    if not filings:
        if blackboard:
            blackboard.insider["latest_filings"] = []
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No recent insider filings found",
            weight=cfg.get("weight_insider_agent", 0.85),
            metadata={"data_available": False, "filing_count": 0},
        )

    # Filter to purchases only (most predictive)
    purchases = [f for f in filings if _is_purchase(f)]

    # Cluster detection
    cluster_detected, cluster_insiders = _detect_cluster(purchases)

    # Context enrichment
    enrichment = await _enrich_context(symbol, f)

    # Score the signal
    top_signal = _score_filings(purchases, enrichment, f)

    # Aggregate sector heat
    sector_heat = _compute_sector_heat(filings)

    # Write to blackboard
    if blackboard:
        blackboard.insider.update({
            "latest_filings": [_filing_summary(f) for f in filings[:20]],
            "cluster_tickers": [symbol] if cluster_detected else [],
            "top_signal": top_signal,
            "sector_heat": sector_heat,
        })

    # Determine vote
    direction, confidence = _signal_to_vote(
        purchases, cluster_detected, top_signal, enrichment, cfg,
    )

    reasoning_parts = [
        f"Filings={len(filings)} (purchases={len(purchases)})",
    ]
    if cluster_detected:
        reasoning_parts.append(f"CLUSTER BUY ({len(cluster_insiders)} insiders)")
    if top_signal:
        reasoning_parts.append(f"top_score={top_signal.get('score', 0):.2f}")
    if enrichment.get("near_earnings"):
        reasoning_parts.append("pre-earnings")
    if enrichment.get("recent_downgrade"):
        reasoning_parts.append("post-downgrade")

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=", ".join(reasoning_parts),
        weight=cfg.get("weight_insider_agent", 0.85),
        metadata={
            "data_available": True,
            "filing_count": len(filings),
            "purchase_count": len(purchases),
            "cluster_detected": cluster_detected,
            "cluster_insiders": cluster_insiders,
            "top_signal": top_signal,
            "enrichment": enrichment,
        },
    )


def _signal_to_vote(
    purchases: List[Dict], cluster: bool, top_signal: Optional[Dict],
    enrichment: Dict, cfg: Dict,
) -> Tuple[str, float]:
    """Convert insider signal to directional vote."""
    if not purchases:
        return "hold", 0.15

    base_confidence = 0.45

    # Purchase count boost
    if len(purchases) >= 3:
        base_confidence += 0.1
    elif len(purchases) >= 1:
        base_confidence += 0.05

    # Cluster buy is the strongest signal (~doubles confidence per academic research)
    if cluster:
        base_confidence += 0.2

    # Top signal score boost
    if top_signal and top_signal.get("score", 0) > 0.7:
        base_confidence += 0.1

    # Context enrichment boosts
    if enrichment.get("near_earnings") and enrichment.get("recent_downgrade"):
        # Insider buying before earnings after downgrade = highest conviction
        base_confidence += 0.1
    if enrichment.get("high_short_interest"):
        base_confidence += 0.05

    # Insiders buy → bullish signal
    direction = "buy"
    confidence = min(0.9, base_confidence)

    return direction, confidence


async def _fetch_insider_filings(symbol: str) -> List[Dict[str, Any]]:
    """Fetch Form 4 filings from SEC EDGAR or data providers."""
    # Try Unusual Whales insider data first (already integrated)
    try:
        from app.services.unusual_whales_service import get_insider_trades
        filings = await get_insider_trades(symbol)
        if filings:
            return filings
    except Exception:
        pass

    # Try SEC EDGAR XBRL feed
    try:
        from app.services.sec_edgar_service import get_form4_filings
        return await get_form4_filings(symbol)
    except Exception:
        pass

    # Try FinViz insider data (already integrated)
    try:
        from app.services.finviz_service import get_insider_trading
        return await get_insider_trading(symbol)
    except Exception:
        pass

    return []


def _is_purchase(filing: Dict) -> bool:
    """Check if a filing represents an open-market purchase."""
    txn_type = str(filing.get("transaction_type", "")).lower()
    # Filter for direct purchases, exclude grants/exercises/gifts
    purchase_keywords = ("purchase", "buy", "p-purchase", "acquisition")
    exclude_keywords = ("grant", "exercise", "gift", "award", "conversion")

    if any(kw in txn_type for kw in exclude_keywords):
        return False
    return any(kw in txn_type for kw in purchase_keywords) or txn_type == "p"


def _detect_cluster(
    purchases: List[Dict],
) -> Tuple[bool, List[str]]:
    """Detect cluster buys: 2+ insiders purchasing within 7-day window."""
    if len(purchases) < _CLUSTER_MIN_INSIDERS:
        return False, []

    # Group by insider name and check time window
    insiders = set()
    dates = []
    for p in purchases:
        name = p.get("insider_name") or p.get("owner_name") or p.get("name", "unknown")
        insiders.add(name)
        date_str = p.get("filing_date") or p.get("transaction_date") or p.get("date")
        if date_str:
            try:
                if isinstance(date_str, str):
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else:
                    dt = date_str
                dates.append(dt)
            except Exception:
                pass

    if len(insiders) < _CLUSTER_MIN_INSIDERS:
        return False, []

    # Check if purchases are within the cluster window
    if dates:
        dates.sort()
        window = timedelta(days=_CLUSTER_WINDOW_DAYS)
        if (dates[-1] - dates[0]) <= window:
            return True, list(insiders)

    # If no dates available but multiple insiders, still flag
    if len(insiders) >= _CLUSTER_MIN_INSIDERS:
        return True, list(insiders)

    return False, []


async def _enrich_context(symbol: str, features: Dict) -> Dict[str, Any]:
    """Cross-reference with earnings dates, analyst downgrades, short interest."""
    enrichment: Dict[str, Any] = {}

    # Check if near earnings
    try:
        from app.services.benzinga_service import get_next_earnings_date
        earnings_date = await get_next_earnings_date(symbol)
        if earnings_date:
            days_to_earnings = (earnings_date - datetime.now(timezone.utc)).days
            enrichment["near_earnings"] = 0 < days_to_earnings <= 14
            enrichment["days_to_earnings"] = days_to_earnings
    except Exception:
        enrichment["near_earnings"] = False

    # Check for recent analyst downgrades
    try:
        from app.services.finviz_service import get_analyst_actions
        actions = await get_analyst_actions(symbol)
        recent_downgrades = [
            a for a in (actions or [])
            if "downgrade" in str(a.get("action", "")).lower()
        ]
        enrichment["recent_downgrade"] = len(recent_downgrades) > 0
    except Exception:
        enrichment["recent_downgrade"] = False

    # Check short interest
    try:
        short_interest = features.get("short_interest_ratio", 0)
        enrichment["high_short_interest"] = short_interest > 10  # Days to cover > 10
    except Exception:
        enrichment["high_short_interest"] = False

    # Distance from 52-week high (~36% of predictive power per academic research)
    high_52w = features.get("high_52w", 0) or features.get("52w_high", 0)
    last_close = features.get("last_close", 0) or features.get("close", 0)
    if high_52w and last_close:
        enrichment["pct_from_52w_high"] = (last_close - high_52w) / high_52w
    else:
        enrichment["pct_from_52w_high"] = 0

    return enrichment


def _score_filings(
    purchases: List[Dict], enrichment: Dict, features: Dict,
) -> Optional[Dict[str, Any]]:
    """Score insider filings with composite weighting."""
    if not purchases:
        return None

    best_score = 0.0
    best_filing = None

    for p in purchases:
        score = 0.0

        # Role weight
        role = str(p.get("insider_title") or p.get("owner_title") or p.get("role", "")).lower()
        role_weight = 0.7
        for keyword, weight in _ROLE_WEIGHTS.items():
            if keyword in role:
                role_weight = weight
                break
        score += role_weight * 0.25

        # Purchase size relative to holdings
        txn_value = float(p.get("transaction_value", 0) or p.get("value", 0))
        if txn_value > 1_000_000:
            score += 0.25
        elif txn_value > 500_000:
            score += 0.20
        elif txn_value > 100_000:
            score += 0.15
        elif txn_value > 10_000:
            score += 0.10

        # Distance from 52-week high (strongest predictor)
        pct_from_high = enrichment.get("pct_from_52w_high", 0)
        if pct_from_high < -0.3:  # 30%+ below 52w high
            score += 0.25
        elif pct_from_high < -0.15:
            score += 0.15
        elif pct_from_high < -0.05:
            score += 0.10

        # Context bonuses
        if enrichment.get("near_earnings"):
            score += 0.10
        if enrichment.get("recent_downgrade"):
            score += 0.10
        if enrichment.get("high_short_interest"):
            score += 0.05

        if score > best_score:
            best_score = score
            best_filing = p

    if best_filing:
        return {
            "score": round(best_score, 2),
            "insider": best_filing.get("insider_name") or best_filing.get("owner_name", "unknown"),
            "role": best_filing.get("insider_title") or best_filing.get("owner_title", ""),
            "value": float(best_filing.get("transaction_value", 0) or best_filing.get("value", 0)),
        }
    return None


def _compute_sector_heat(filings: List[Dict]) -> Dict[str, float]:
    """Aggregate insider buying by sector."""
    sector_buys: Dict[str, float] = {}
    for f in filings:
        if not _is_purchase(f):
            continue
        sector = f.get("sector", "unknown")
        value = float(f.get("transaction_value", 0) or f.get("value", 0))
        sector_buys[sector] = sector_buys.get(sector, 0) + value
    return sector_buys


def _filing_summary(filing: Dict) -> Dict[str, Any]:
    """Create a compact filing summary for blackboard storage."""
    return {
        "insider": filing.get("insider_name") or filing.get("owner_name", ""),
        "title": filing.get("insider_title") or filing.get("owner_title", ""),
        "type": filing.get("transaction_type", ""),
        "value": float(filing.get("transaction_value", 0) or filing.get("value", 0)),
        "date": str(filing.get("filing_date") or filing.get("transaction_date") or ""),
    }
