"""Congressional / Political Trading Agent — legislative trade monitoring.

P2 Academic Edge Agent. Monitors congressional trade disclosures for
informational advantages tied to committee assignments and regulatory exposure.

Academic basis: Pre-STOCK Act Congress earned 9.5% Carhart alpha/year with
leadership positions earning 13.5%. Post-Act, leadership positions and
committee assignments continue to correlate with outperformance.

Sub-agents:
- Filing Scraper: Monitors Capitol Trades API and Senate Stock Watcher
- Committee Context: Maps member committees to traded company regulatory exposure
- Cluster Detection: Multiple members from same committee trading same sector
- Signal Scoring: Weights by committee relevance, trade size, member seniority

Council integration: Enriches flow_perception_agent metadata.
"""
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "congressional_agent"

# Committee-to-sector relevance mapping
_COMMITTEE_SECTOR_MAP = {
    "armed services": {"defense", "aerospace", "military"},
    "finance": {"banking", "insurance", "fintech", "financial"},
    "energy": {"oil", "gas", "energy", "renewable", "solar", "utilities"},
    "health": {"healthcare", "pharma", "biotech", "medical"},
    "commerce": {"tech", "telecom", "retail", "consumer"},
    "agriculture": {"agriculture", "food", "farming"},
    "banking": {"banking", "financial", "fintech", "insurance"},
    "judiciary": {"legal", "tech", "social media"},
    "intelligence": {"defense", "cybersecurity", "tech"},
    "appropriations": {"defense", "infrastructure", "construction"},
    "transportation": {"airlines", "shipping", "logistics", "rail"},
}

# Seniority weights
_SENIORITY_WEIGHTS = {
    "speaker": 2.0,
    "majority leader": 1.8,
    "minority leader": 1.7,
    "committee chair": 1.6,
    "ranking member": 1.5,
    "whip": 1.4,
    "senator": 1.2,
    "representative": 1.0,
}


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Analyze congressional trading activity for the given symbol."""
    cfg = get_agent_thresholds()
    f = features.get("features", features)
    blackboard = context.get("blackboard")

    # Fetch congressional trades
    trades = await _fetch_congressional_trades(symbol)
    if not trades:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No congressional trading data available",
            weight=cfg.get("weight_congressional_agent", 0.6),
            metadata={"data_available": False, "trade_count": 0},
        )

    # Committee context enrichment
    committee_signals = _analyze_committee_relevance(trades, symbol, f)

    # Cluster detection
    cluster_sectors = _detect_clusters(trades)

    # Score signals
    top_signal = _score_trades(trades, committee_signals)

    # Write to blackboard
    if blackboard:
        blackboard.congressional.update({
            "recent_trades": [_trade_summary(t) for t in trades[:20]],
            "committee_signals": committee_signals,
            "cluster_sectors": cluster_sectors,
            "top_signal": top_signal,
        })

    # Vote determination
    direction, confidence = _congressional_to_vote(
        trades, committee_signals, top_signal, cfg,
    )

    reasoning_parts = [f"Congressional trades={len(trades)}"]
    if committee_signals:
        reasoning_parts.append(f"{len(committee_signals)} committee-relevant signals")
    if cluster_sectors:
        reasoning_parts.append(f"cluster in {list(cluster_sectors.keys())[:3]}")
    if top_signal:
        reasoning_parts.append(f"top: {top_signal.get('member', '')} ({top_signal.get('score', 0):.2f})")

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=", ".join(reasoning_parts),
        weight=cfg.get("weight_congressional_agent", 0.6),
        metadata={
            "data_available": True,
            "trade_count": len(trades),
            "committee_signals": committee_signals,
            "cluster_sectors": cluster_sectors,
            "top_signal": top_signal,
        },
    )


def _congressional_to_vote(
    trades: List[Dict], committee_signals: List[Dict],
    top_signal: Optional[Dict], cfg: Dict,
) -> Tuple[str, float]:
    """Convert congressional analysis to vote."""
    if not trades:
        return "hold", 0.15

    # Count buy vs sell trades
    buys = sum(1 for t in trades if _is_buy(t))
    sells = len(trades) - buys

    base_confidence = 0.4

    if buys > sells:
        direction = "buy"
        base_confidence += 0.1 * min(3, buys - sells)
    elif sells > buys:
        direction = "sell"
        base_confidence += 0.1 * min(3, sells - buys)
    else:
        direction = "hold"

    # Committee relevance boost
    if committee_signals:
        base_confidence += 0.1

    # Top signal score boost
    if top_signal and top_signal.get("score", 0) > 0.7:
        base_confidence += 0.1

    return direction, min(0.8, base_confidence)


async def _fetch_congressional_trades(symbol: str) -> List[Dict[str, Any]]:
    """Fetch congressional trade disclosures."""
    # Try Capitol Trades API
    try:
        from app.services.capitol_trades_service import get_trades_by_ticker
        trades = await get_trades_by_ticker(symbol)
        if trades:
            return trades
    except Exception:
        pass

    # Try Senate Stock Watcher
    try:
        from app.services.senate_stock_watcher_service import get_ticker_trades
        return await get_ticker_trades(symbol)
    except Exception:
        pass

    return []


def _is_buy(trade: Dict) -> bool:
    """Check if trade is a purchase."""
    direction = str(trade.get("type", "") or trade.get("transaction_type", "")).lower()
    return direction in ("purchase", "buy", "p")


def _analyze_committee_relevance(
    trades: List[Dict], symbol: str, features: Dict,
) -> List[Dict[str, Any]]:
    """Map member committee assignments to traded company's sector."""
    signals: List[Dict] = []
    sector = str(features.get("sector", "") or "").lower()

    for trade in trades:
        committees = trade.get("committees", [])
        if isinstance(committees, str):
            committees = [committees]

        for committee in committees:
            committee_lower = committee.lower()
            for committee_key, related_sectors in _COMMITTEE_SECTOR_MAP.items():
                if committee_key in committee_lower:
                    # Check if the traded company's sector is relevant
                    if sector and any(s in sector for s in related_sectors):
                        signals.append({
                            "member": trade.get("member_name", ""),
                            "committee": committee,
                            "sector_match": sector,
                            "trade_type": "buy" if _is_buy(trade) else "sell",
                            "relevance": "high",
                        })
                    break

    return signals


def _detect_clusters(trades: List[Dict]) -> Dict[str, List[str]]:
    """Identify when multiple members from same committee trade same sector."""
    committee_traders: Dict[str, List[str]] = defaultdict(list)

    for trade in trades:
        committees = trade.get("committees", [])
        if isinstance(committees, str):
            committees = [committees]
        member = trade.get("member_name", "unknown")

        for committee in committees:
            committee_traders[committee.lower()].append(member)

    # Filter to committees with 2+ unique traders
    clusters: Dict[str, List[str]] = {}
    for committee, members in committee_traders.items():
        unique = list(set(members))
        if len(unique) >= 2:
            clusters[committee] = unique

    return clusters


def _score_trades(
    trades: List[Dict], committee_signals: List[Dict],
) -> Optional[Dict[str, Any]]:
    """Score trades by committee relevance, size, and seniority."""
    if not trades:
        return None

    best_score = 0.0
    best_trade = None

    for trade in trades:
        score = 0.0

        # Seniority weight
        title = str(trade.get("member_title", "") or trade.get("position", "")).lower()
        for keyword, weight in _SENIORITY_WEIGHTS.items():
            if keyword in title:
                score += weight * 0.2
                break
        else:
            score += 0.2  # Base weight

        # Trade size
        amount = str(trade.get("amount", "") or trade.get("range", "")).lower()
        if "$1,000,001" in amount or "over $1m" in amount:
            score += 0.3
        elif "$500,001" in amount or "$250,001" in amount:
            score += 0.2
        elif "$100,001" in amount:
            score += 0.15
        else:
            score += 0.1

        # Committee relevance
        member = trade.get("member_name", "")
        if any(s.get("member") == member for s in committee_signals):
            score += 0.3

        if score > best_score:
            best_score = score
            best_trade = trade

    if best_trade:
        return {
            "member": best_trade.get("member_name", ""),
            "party": best_trade.get("party", ""),
            "type": "buy" if _is_buy(best_trade) else "sell",
            "amount": best_trade.get("amount", ""),
            "score": round(best_score, 2),
        }
    return None


def _trade_summary(trade: Dict) -> Dict[str, Any]:
    """Create compact trade summary for blackboard."""
    return {
        "member": trade.get("member_name", ""),
        "party": trade.get("party", ""),
        "type": "buy" if _is_buy(trade) else "sell",
        "amount": trade.get("amount", ""),
        "date": str(trade.get("transaction_date", "") or trade.get("disclosure_date", "")),
    }
