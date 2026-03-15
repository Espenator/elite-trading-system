"""Satellite / Alternative Data Agent — non-traditional data source signals.

P4 Academic Edge Agent. Processes alternative data sources including
satellite imagery, geospatial data, and other non-traditional signals.

Academic basis: MIT Sloan study showed parking lot satellite imagery
predicted earnings with 85% accuracy. 78% of hedge funds now use
alternative data. This agent serves as the integration point for
future alt data providers.

Council integration: New alt_data_agent providing supplementary signals.
Expensive and long-term — deferred until earlier phases prove profitable.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "alt_data_agent"


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Analyze alternative data sources for the given symbol."""
    cfg = get_agent_thresholds()
    blackboard = context.get("blackboard")

    # Collect signals from available alt data providers
    signals: List[Dict[str, Any]] = []
    sources: List[str] = []
    f = features.get("features", features) if features else {}

    # B5: SqueezeMetrics DIX/GEX as dark pool alt data (zero new API calls)
    dix = f.get("uw_dark_pool_index") or f.get("dix")
    gex = f.get("uw_gex") or f.get("gex")
    if dix is not None or gex is not None:
        dix_val = float(dix) if dix is not None else 0.0
        gex_val = float(gex) if gex is not None else 0.0
        dp_signal = "bullish" if dix_val > 45 else ("bearish" if dix_val < 40 else "neutral")
        dp_direction = "buy" if dp_signal == "bullish" else ("sell" if dp_signal == "bearish" else "hold")
        signals.append({
            "source": "dark_pool", "dix": dix_val, "gex": gex_val,
            "signal": dp_signal, "direction": dp_direction, "confidence": 0.5,
        })
        sources.append("dark_pool")

    # Satellite / geospatial data
    sat_signal = await _fetch_satellite_data(symbol)
    if sat_signal:
        signals.append(sat_signal)
        sources.append("satellite")

    # Web traffic / app download data
    web_signal = await _fetch_web_traffic_data(symbol)
    if web_signal:
        signals.append(web_signal)
        sources.append("web_traffic")

    # Credit card transaction data
    cc_signal = await _fetch_credit_card_data(symbol)
    if cc_signal:
        signals.append(cc_signal)
        sources.append("credit_card")

    # Job posting data (hiring = growth signal)
    jobs_signal = await _fetch_job_posting_data(symbol)
    if jobs_signal:
        signals.append(jobs_signal)
        sources.append("job_postings")

    if not signals:
        if blackboard:
            blackboard.alt_data.update({
                "signals": [],
                "confidence": 0.0,
                "sources": [],
            })
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No alternative data sources available (P4 — future integration)",
            weight=cfg.get("weight_alt_data_agent", 0.5),
            metadata={"data_available": False, "sources": []},
        )

    # Aggregate signals
    direction, confidence = _aggregate_alt_signals(signals)

    # Write to blackboard
    if blackboard:
        blackboard.alt_data.update({
            "signals": signals,
            "confidence": confidence,
            "sources": sources,
        })

    reasoning = f"Alt data: {len(signals)} signals from {','.join(sources)}"

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        weight=cfg.get("weight_alt_data_agent", 0.5),
        metadata={
            "data_available": True,
            "signal_count": len(signals),
            "sources": sources,
            "signals": signals,
        },
    )


def _aggregate_alt_signals(signals: List[Dict]) -> Tuple[str, float]:
    """Aggregate multiple alt data signals into a single vote."""
    if not signals:
        return "hold", 0.1

    bullish = 0
    bearish = 0
    total_confidence = 0.0

    for sig in signals:
        direction = sig.get("direction", "hold")
        conf = float(sig.get("confidence", 0.3))
        if direction == "buy":
            bullish += conf
        elif direction == "sell":
            bearish += conf
        total_confidence += conf

    avg_confidence = total_confidence / max(1, len(signals))

    if bullish > bearish:
        return "buy", min(0.8, avg_confidence)
    elif bearish > bullish:
        return "sell", min(0.8, avg_confidence)
    return "hold", 0.3


async def _fetch_satellite_data(symbol: str) -> Optional[Dict]:
    """Fetch satellite / geospatial data. Stub for future providers."""
    try:
        from app.services.orbital_insight_service import get_satellite_signal
        return await get_satellite_signal(symbol)
    except (ImportError, Exception):
        return None


async def _fetch_web_traffic_data(symbol: str) -> Optional[Dict]:
    """Fetch web traffic / app download signals."""
    try:
        from app.services.similarweb_service import get_traffic_signal
        return await get_traffic_signal(symbol)
    except (ImportError, Exception):
        return None


async def _fetch_credit_card_data(symbol: str) -> Optional[Dict]:
    """Fetch credit card transaction trend data."""
    try:
        from app.services.credit_card_service import get_spending_signal
        return await get_spending_signal(symbol)
    except (ImportError, Exception):
        return None


async def _fetch_job_posting_data(symbol: str) -> Optional[Dict]:
    """Fetch job posting growth signals."""
    try:
        from app.services.job_posting_service import get_hiring_signal
        return await get_hiring_signal(symbol)
    except (ImportError, Exception):
        return None
