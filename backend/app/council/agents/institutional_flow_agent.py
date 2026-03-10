"""13F Institutional Flow Tracker Agent — quarterly fund position analysis.

P2 Academic Edge Agent. Tracks institutional investment managers ($100M+ AUM)
via SEC 13F-HR filings to detect consensus positions and crowded trades.

Academic basis: Sector concentration shifts across multiple filers precede
market moves. Crowded longs (30%+ of tracked portfolios) are vulnerable
to coordinated unwinding.

Sub-agents:
- Filing Parser: Extracts position changes from 13F-HR filings
- Consensus Detector: Flags 5+ high-performing funds initiating same ticker
- Crowded Trade Detector: Flags names in 30%+ of tracked portfolios
- Sector Concentration Tracker: Monitors aggregate sector allocation shifts

Council integration: New S1 perception agent feeding institutional flow
context to strategy_agent and regime_agent.
"""
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "institutional_flow_agent"

# Thresholds
_CONSENSUS_MIN_FUNDS = 5
_CROWDED_THRESHOLD_PCT = 0.30


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Analyze 13F institutional flow for the given symbol."""
    cfg = get_agent_thresholds()
    blackboard = context.get("blackboard")

    # Fetch 13F data
    filings = await _fetch_13f_data(symbol)
    if not filings:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No 13F institutional data available",
            weight=cfg.get("weight_institutional_flow_agent", 0.7),
            metadata={"data_available": False},
        )

    # Analyze position changes
    changes = _analyze_position_changes(filings, symbol)

    # Consensus detection
    consensus_buys = _detect_consensus(changes, "buy", symbol)
    consensus_sells = _detect_consensus(changes, "sell", symbol)

    # Crowded trade detection
    crowded = _detect_crowded_trades(filings, symbol)

    # Sector rotation
    sector_rotation = _compute_sector_rotation(filings)

    # Write to blackboard
    if blackboard:
        blackboard.institutional.update({
            "consensus_buys": consensus_buys,
            "consensus_sells": consensus_sells,
            "crowded_longs": crowded,
            "sector_rotation": sector_rotation,
            "top_funds_active": len(filings),
        })

    # Vote determination
    direction, confidence = _institutional_to_vote(
        symbol, changes, consensus_buys, consensus_sells, crowded, cfg,
    )

    reasoning_parts = [f"13F filers={len(filings)}"]
    if symbol in consensus_buys:
        reasoning_parts.append("CONSENSUS BUY")
    if symbol in consensus_sells:
        reasoning_parts.append("CONSENSUS SELL")
    if symbol in crowded:
        reasoning_parts.append("CROWDED LONG (vulnerable)")
    if changes:
        net = changes.get("net_direction", "flat")
        reasoning_parts.append(f"net={net} ({changes.get('buyers', 0)}B/{changes.get('sellers', 0)}S)")

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=", ".join(reasoning_parts),
        weight=cfg.get("weight_institutional_flow_agent", 0.7),
        metadata={
            "data_available": True,
            "filer_count": len(filings),
            "changes": changes,
            "consensus_buys": consensus_buys,
            "consensus_sells": consensus_sells,
            "crowded_longs": crowded,
        },
    )


def _institutional_to_vote(
    symbol: str, changes: Dict, consensus_buys: List[str],
    consensus_sells: List[str], crowded: List[str], cfg: Dict,
) -> Tuple[str, float]:
    """Convert institutional analysis to vote."""
    direction = "hold"
    confidence = 0.35

    # Consensus buy is a strong signal
    if symbol in consensus_buys:
        direction = "buy"
        confidence = 0.7

    # Consensus sell
    if symbol in consensus_sells:
        direction = "sell"
        confidence = 0.65

    # Crowded long reduces buy confidence (vulnerable to unwind)
    if symbol in crowded and direction == "buy":
        confidence *= 0.8
        logger.info("Crowded long penalty for %s", symbol)

    # Net position changes
    if changes:
        buyers = changes.get("buyers", 0)
        sellers = changes.get("sellers", 0)
        if buyers > sellers * 2 and direction != "sell":
            direction = "buy"
            confidence = max(confidence, 0.55)
        elif sellers > buyers * 2 and direction != "buy":
            direction = "sell"
            confidence = max(confidence, 0.55)

    return direction, min(0.85, confidence)


async def _fetch_13f_data(symbol: str) -> List[Dict[str, Any]]:
    """Fetch 13F filing data from SEC EDGAR or data providers."""
    try:
        from app.services.sec_edgar_service import get_13f_filings
        return await get_13f_filings(symbol)
    except Exception:
        pass

    # Try Unusual Whales institutional flow (if available)
    try:
        from app.services.unusual_whales_service import get_institutional_flow
        return await get_institutional_flow(symbol)
    except ImportError as e:
        logger.warning("Failed to import Unusual Whales institutional flow: %s", e)
    except Exception as e:
        logger.debug("Unusual Whales institutional flow not available for %s: %s", symbol, e)

    return []


def _analyze_position_changes(
    filings: List[Dict], symbol: str,
) -> Dict[str, Any]:
    """Analyze position changes across filers."""
    buyers = 0
    sellers = 0
    new_positions = 0
    exits = 0
    total_change = 0.0

    for filing in filings:
        holdings = filing.get("holdings", [])
        for h in holdings:
            ticker = str(h.get("ticker", "") or h.get("cusip", "")).upper()
            if ticker != symbol.upper():
                continue

            change_type = str(h.get("change_type", "")).lower()
            shares_change = float(h.get("shares_change", 0))

            if change_type == "new" or shares_change > 0:
                buyers += 1
                total_change += shares_change
                if change_type == "new":
                    new_positions += 1
            elif change_type == "exit" or shares_change < 0:
                sellers += 1
                total_change += shares_change
                if change_type == "exit":
                    exits += 1

    net_direction = "flat"
    if buyers > sellers:
        net_direction = "accumulating"
    elif sellers > buyers:
        net_direction = "distributing"

    return {
        "buyers": buyers,
        "sellers": sellers,
        "new_positions": new_positions,
        "exits": exits,
        "net_direction": net_direction,
        "total_share_change": total_change,
    }


def _detect_consensus(changes, direction: str, symbol: str = "") -> List[str]:
    """Detect consensus buying or selling across top-performing funds.

    Handles both a summary dict (from _analyze_position_changes) and a raw
    list of per-filing change dicts that may come from external data providers.
    """
    if isinstance(changes, list):
        # Handle list of change dicts (e.g. from external API responses)
        symbols: List[str] = []
        for change in changes:
            if not isinstance(change, dict):
                continue
            sym = change.get("symbol", symbol) or symbol
            if not sym:
                continue
            if direction == "buy" and change.get("buyers", 0) >= _CONSENSUS_MIN_FUNDS:
                symbols.append(sym)
            elif direction == "sell" and change.get("sellers", 0) >= _CONSENSUS_MIN_FUNDS:
                symbols.append(sym)
        return [s for s in symbols if s]
    elif isinstance(changes, dict):
        # Handle summary dict from _analyze_position_changes
        sym = changes.get("symbol", symbol) or symbol
        if direction == "buy" and changes.get("buyers", 0) >= _CONSENSUS_MIN_FUNDS:
            return [sym] if sym else []
        elif direction == "sell" and changes.get("sellers", 0) >= _CONSENSUS_MIN_FUNDS:
            return [sym] if sym else []
    return []


def _detect_crowded_trades(
    filings: List[Dict], symbol: str,
) -> List[str]:
    """Detect crowded long positions (in 30%+ of tracked portfolios)."""
    if not filings:
        return []

    holders = 0
    for filing in filings:
        holdings = filing.get("holdings", [])
        for h in holdings:
            ticker = str(h.get("ticker", "") or h.get("cusip", "")).upper()
            if ticker == symbol.upper():
                holders += 1
                break

    if len(filings) > 0 and holders / len(filings) >= _CROWDED_THRESHOLD_PCT:
        return [symbol]

    return []


def _compute_sector_rotation(filings: List[Dict]) -> Dict[str, float]:
    """Compute quarter-over-quarter sector allocation shifts."""
    current_sectors: Dict[str, float] = defaultdict(float)
    prior_sectors: Dict[str, float] = defaultdict(float)

    for filing in filings:
        for h in filing.get("holdings", []):
            sector = h.get("sector", "unknown")
            value = float(h.get("value", 0))
            current_sectors[sector] += value

        for h in filing.get("prior_holdings", []):
            sector = h.get("sector", "unknown")
            value = float(h.get("value", 0))
            prior_sectors[sector] += value

    # Compute rotation (delta)
    all_sectors = set(current_sectors.keys()) | set(prior_sectors.keys())
    rotation: Dict[str, float] = {}
    for sector in all_sectors:
        current = current_sectors.get(sector, 0)
        prior = prior_sectors.get(sector, 0)
        if prior > 0:
            rotation[sector] = round((current - prior) / prior, 4)
        elif current > 0:
            rotation[sector] = 1.0  # New sector allocation

    return rotation
