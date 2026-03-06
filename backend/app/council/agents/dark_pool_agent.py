"""Dark Pool Accumulation Detector Agent — institutional dark venue analysis.

P2 Academic Edge Agent. Monitors dark pool activity for institutional
accumulation/distribution signals via DIX and per-ticker dark flow.

Academic basis: DIX > 45% signals net institutional accumulation (bullish).
Combining dark pool signals with options sweeps achieves ~75-80% win rates
vs 60% for either signal alone.

Sub-agents:
- DIX/GEX Monitor: Tracks SqueezeMetrics DIX crossing 45% threshold
- Per-Ticker Dark Flow: Individual ticker dark pool volume anomalies
- Divergence Detector: Dark pool accumulation vs declining price
- Confirmation: Cross-references with options flow for multi-source confirmation

Council integration: Enriches flow_perception_agent as secondary signal.
"""
import logging
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "dark_pool_agent"

# DIX thresholds (SqueezeMetrics)
_DIX_BULLISH_THRESHOLD = 0.45
_DIX_BEARISH_THRESHOLD = 0.40

# Rolling DIX history for 20-day average
_dix_history: List[float] = []


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Analyze dark pool activity for the given symbol."""
    cfg = get_agent_thresholds()
    f = features.get("features", features)
    blackboard = context.get("blackboard")

    # Fetch dark pool data
    dp_data = await _fetch_dark_pool_data(symbol)
    dix_data = await _fetch_dix_data()

    if not dp_data and not dix_data:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No dark pool data available",
            weight=cfg.get("weight_dark_pool_agent", 0.7),
            metadata={"data_available": False},
        )

    # DIX analysis
    dix_value = float(dix_data.get("dix", 0)) if dix_data else 0.0
    dix_20d_avg = _update_dix_history(dix_value)
    dix_signal = _classify_dix(dix_value, dix_20d_avg)

    # Per-ticker dark flow analysis
    ticker_dark_flow = _analyze_ticker_flow(dp_data, symbol)

    # Divergence detection (dark pool vs price action)
    divergence_detected = _detect_divergence(
        ticker_dark_flow, f, symbol,
    )
    divergence_tickers = [symbol] if divergence_detected else []

    # Options flow confirmation
    confirmed = await _check_options_confirmation(symbol, dix_signal, context)

    # Write to blackboard
    if blackboard:
        blackboard.dark_pool.update({
            "dix": dix_value,
            "dix_20d_avg": dix_20d_avg,
            "dix_signal": dix_signal,
            "ticker_dark_flow": ticker_dark_flow,
            "divergence_tickers": divergence_tickers,
        })

    # Vote determination
    direction, confidence = _dark_pool_to_vote(
        dix_signal, ticker_dark_flow, divergence_detected, confirmed, cfg,
    )

    reasoning_parts = [f"DIX={dix_value:.1%} (20d avg={dix_20d_avg:.1%})"]
    reasoning_parts.append(f"signal={dix_signal}")
    if ticker_dark_flow:
        vol_ratio = ticker_dark_flow.get("volume_ratio", 1.0)
        reasoning_parts.append(f"ticker dark vol={vol_ratio:.1f}x avg")
    if divergence_detected:
        reasoning_parts.append("PRICE-DARK DIVERGENCE (accumulation)")
    if confirmed:
        reasoning_parts.append("options flow CONFIRMS")

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=", ".join(reasoning_parts),
        weight=cfg.get("weight_dark_pool_agent", 0.7),
        metadata={
            "data_available": True,
            "dix": dix_value,
            "dix_20d_avg": dix_20d_avg,
            "dix_signal": dix_signal,
            "ticker_dark_flow": ticker_dark_flow,
            "divergence": divergence_detected,
            "options_confirmed": confirmed,
        },
    )


def _dark_pool_to_vote(
    dix_signal: str, ticker_flow: Dict,
    divergence: bool, confirmed: bool, cfg: Dict,
) -> Tuple[str, float]:
    """Convert dark pool analysis to vote."""
    direction = "hold"
    confidence = 0.4

    # DIX-based signal
    if dix_signal == "bullish_accumulation":
        direction = "buy"
        confidence = 0.6
    elif dix_signal == "distribution":
        direction = "sell"
        confidence = 0.55

    # Per-ticker dark flow boost
    if ticker_flow:
        flow_direction = ticker_flow.get("direction", "neutral")
        if flow_direction == "accumulation" and direction != "sell":
            direction = "buy"
            confidence = max(confidence, 0.55)
        elif flow_direction == "distribution" and direction != "buy":
            direction = "sell"
            confidence = max(confidence, 0.55)

    # Divergence = highest alpha signal
    if divergence and direction == "buy":
        confidence = min(0.85, confidence + 0.15)

    # Options confirmation boosts win rate to 75-80%
    if confirmed and direction != "hold":
        confidence = min(0.85, confidence + 0.1)

    return direction, confidence


async def _fetch_dark_pool_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch per-ticker dark pool data from Unusual Whales."""
    try:
        from app.services.unusual_whales_service import get_dark_pool_flow
        return await get_dark_pool_flow(symbol)
    except Exception:
        pass
    return None


async def _fetch_dix_data() -> Optional[Dict[str, Any]]:
    """Fetch DIX/GEX from SqueezeMetrics."""
    try:
        from app.services.squeezemetrics_service import get_dix_gex
        return await get_dix_gex()
    except Exception:
        pass

    # Try cached DIX data
    try:
        from app.services.market_data_cache import get_cached_dix
        return await get_cached_dix()
    except Exception:
        pass

    return None


def _update_dix_history(dix_value: float) -> float:
    """Update rolling DIX history and compute 20-day average."""
    global _dix_history

    if dix_value > 0:
        _dix_history.append(dix_value)
        if len(_dix_history) > 20:
            _dix_history = _dix_history[-20:]

    if _dix_history:
        return round(statistics.mean(_dix_history), 4)
    return dix_value


def _classify_dix(dix: float, dix_avg: float) -> str:
    """Classify DIX signal."""
    if dix == 0:
        return "neutral"

    if dix >= _DIX_BULLISH_THRESHOLD:
        return "bullish_accumulation"
    elif dix <= _DIX_BEARISH_THRESHOLD:
        return "distribution"

    # Check for divergence from average
    if dix_avg > 0 and dix > dix_avg * 1.05:
        return "bullish_accumulation"
    elif dix_avg > 0 and dix < dix_avg * 0.95:
        return "distribution"

    return "neutral"


def _analyze_ticker_flow(
    dp_data: Optional[Dict], symbol: str,
) -> Dict[str, Any]:
    """Analyze per-ticker dark pool flow."""
    if not dp_data:
        return {}

    dark_volume = float(dp_data.get("dark_pool_volume", 0) or dp_data.get("volume", 0))
    avg_volume = float(dp_data.get("avg_dark_volume", 0) or dp_data.get("avg_volume", 1))
    dark_pct = float(dp_data.get("dark_pool_pct", 0))

    if avg_volume == 0:
        avg_volume = 1

    volume_ratio = dark_volume / avg_volume if avg_volume > 0 else 1.0

    # Determine direction
    direction = "neutral"
    if volume_ratio > 1.5 and dark_pct > 0.35:
        # High dark pool volume = likely institutional accumulation
        net_flow = float(dp_data.get("net_flow", 0) or dp_data.get("buy_volume", 0) - dp_data.get("sell_volume", 0))
        if net_flow > 0:
            direction = "accumulation"
        elif net_flow < 0:
            direction = "distribution"
        else:
            direction = "accumulation"  # Default assumption for high dark pool activity

    return {
        "dark_volume": dark_volume,
        "avg_volume": avg_volume,
        "volume_ratio": round(volume_ratio, 2),
        "dark_pct": dark_pct,
        "direction": direction,
    }


def _detect_divergence(
    ticker_flow: Dict, features: Dict, symbol: str,
) -> bool:
    """Detect divergence: dark pool accumulation while price declining/flat.

    This is the highest-alpha pattern — institutional buying while retail sells.
    """
    if not ticker_flow:
        return False

    flow_direction = ticker_flow.get("direction", "neutral")
    if flow_direction != "accumulation":
        return False

    # Check if price is declining or flat
    ret_1d = float(features.get("return_1d", 0))
    ret_5d = float(features.get("return_5d", 0))

    # Accumulation + declining price = bullish divergence
    return ret_5d < -0.01 or (ret_1d < 0 and ret_5d < 0)


async def _check_options_confirmation(
    symbol: str, dix_signal: str, context: Dict,
) -> bool:
    """Cross-reference dark pool with options flow for confirmation.

    Combined signals achieve 75-80% win rate vs 60% for either alone.
    """
    blackboard = context.get("blackboard")
    if not blackboard:
        return False

    # Check flow_perception for options flow alignment
    flow_data = blackboard.perceptions.get("flow_perception", {})
    if not flow_data:
        return False

    flow_direction = flow_data.get("direction", "hold")

    # Confirmation: dark pool bullish + call sweeps
    if dix_signal == "bullish_accumulation" and flow_direction == "buy":
        return True
    # Confirmation: dark pool distribution + put sweeps
    if dix_signal == "distribution" and flow_direction == "sell":
        return True

    return False
