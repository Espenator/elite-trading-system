"""GEX (Gamma Exposure) Agent — options market maker hedging flow analysis.

P0 Academic Edge Agent. Computes dealer gamma exposure levels to identify
volatility regimes and dynamic support/resistance from options market structure.

Key levels computed:
- Gamma Flip Level: where net dealer gamma crosses from positive to negative
- Call Wall: highest call gamma strike (resistance)
- Put Wall: highest put gamma strike (support)
- Max Pain: strike where total option value expires worthless (pinning target)

Academic basis: 68% of SPX sessions close inside GEX-predicted range.
Data sources: Unusual Whales (already integrated), CBOE options chain.

Council integration:
- strategy_agent reads call_wall/put_wall as dynamic support/resistance
- risk_agent reads gex.regime for position sizing adjustments
- execution_agent avoids market orders near gamma flip level
"""
import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "gex_agent"


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Analyze gamma exposure and max pain to determine market structure bias."""
    cfg = get_agent_thresholds()
    f = features.get("features", features)
    blackboard = context.get("blackboard")

    # Fetch options chain data
    chain = await _fetch_options_chain(symbol)
    last_price = float(f.get("last_close", 0)) or float(f.get("close", 0))

    if not chain or last_price == 0:
        if blackboard:
            blackboard.gex["regime"] = "neutral"
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No options chain data available for GEX analysis",
            weight=cfg.get("weight_gex_agent", 0.9),
            metadata={"data_available": False},
        )

    # Compute GEX levels
    net_gamma, gamma_by_strike = _compute_gex(chain, last_price)
    gamma_flip = _find_gamma_flip(gamma_by_strike, last_price)
    call_wall = _find_call_wall(chain)
    put_wall = _find_put_wall(chain)
    max_pain = _compute_max_pain(chain)
    pin_prob = _compute_pin_probability(last_price, max_pain, chain)

    # Determine GEX regime
    if net_gamma > 0:
        gex_regime = "long_gamma"
    elif net_gamma < 0:
        gex_regime = "short_gamma"
    else:
        gex_regime = "neutral"

    # Write to blackboard
    if blackboard:
        blackboard.gex.update({
            "net_gamma": net_gamma,
            "gamma_flip": gamma_flip,
            "call_wall": call_wall,
            "put_wall": put_wall,
            "max_pain": max_pain,
            "pin_probability": pin_prob,
            "regime": gex_regime,
        })

    # Determine vote
    direction, confidence = _gex_to_vote(
        last_price, net_gamma, gex_regime, gamma_flip,
        call_wall, put_wall, max_pain, pin_prob, cfg,
    )

    reasoning = (
        f"GEX regime={gex_regime}, net_gamma={net_gamma:+.1f}M, "
        f"gamma_flip={gamma_flip:.2f}, "
        f"call_wall={call_wall:.2f}, put_wall={put_wall:.2f}, "
        f"max_pain={max_pain:.2f}, pin_prob={pin_prob:.0%}"
    )

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        weight=cfg.get("weight_gex_agent", 0.9),
        metadata={
            "data_available": True,
            "net_gamma": net_gamma,
            "gamma_flip": gamma_flip,
            "call_wall": call_wall,
            "put_wall": put_wall,
            "max_pain": max_pain,
            "pin_probability": pin_prob,
            "gex_regime": gex_regime,
        },
    )


def _gex_to_vote(
    price: float, net_gamma: float, regime: str, gamma_flip: float,
    call_wall: float, put_wall: float, max_pain: float,
    pin_prob: float, cfg: Dict,
) -> Tuple[str, float]:
    """Convert GEX levels to a directional vote."""
    direction = "hold"
    confidence = 0.4

    # In long gamma, market tends to mean-revert → range-bound
    if regime == "long_gamma":
        # Price near put_wall = support, lean bullish
        if put_wall > 0 and price <= put_wall * 1.01:
            direction = "buy"
            confidence = 0.65
        # Price near call_wall = resistance, lean bearish
        elif call_wall > 0 and price >= call_wall * 0.99:
            direction = "sell"
            confidence = 0.6
        else:
            direction = "hold"
            confidence = 0.5  # Dampened volatility → range-bound

    # In short gamma, moves are amplified
    elif regime == "short_gamma":
        # Price below gamma flip = momentum sell
        if gamma_flip > 0 and price < gamma_flip:
            direction = "sell"
            confidence = 0.7
        # Price above gamma flip = momentum buy
        elif gamma_flip > 0 and price > gamma_flip:
            direction = "buy"
            confidence = 0.65
        else:
            direction = "hold"
            confidence = 0.45

    # Max pain pinning near expiry
    if pin_prob > 0.6:
        if max_pain > 0:
            dist_to_max_pain = (max_pain - price) / price if price > 0 else 0
            if dist_to_max_pain > 0.005:
                direction = "buy"  # Price should drift up toward max pain
                confidence = max(confidence, 0.55 + pin_prob * 0.2)
            elif dist_to_max_pain < -0.005:
                direction = "sell"  # Price should drift down toward max pain
                confidence = max(confidence, 0.55 + pin_prob * 0.2)

    return direction, min(0.9, confidence)


async def _fetch_options_chain(symbol: str) -> List[Dict[str, Any]]:
    """Fetch options chain from Unusual Whales or CBOE data pipeline."""
    try:
        from app.services.unusual_whales_service import get_options_chain
        return await get_options_chain(symbol)
    except ImportError as e:
        logger.warning("Failed to import Unusual Whales options chain: %s", e)
    except Exception as e:
        logger.debug("Unusual Whales options chain not available for %s: %s", symbol, e)

    # Fallback: try CBOE data
    try:
        from app.services.cboe_service import get_options_chain as cboe_chain
        return await cboe_chain(symbol)
    except Exception:
        pass

    # Fallback: try feature data for pre-computed GEX
    return []


def _compute_gex(chain: List[Dict], spot: float) -> Tuple[float, Dict[float, float]]:
    """Compute net GEX and per-strike gamma exposure.

    GEX = Σ (OI × gamma × contract_multiplier × spot_price)
    Calls contribute positive gamma, puts contribute negative gamma for dealers.
    """
    gamma_by_strike: Dict[float, float] = {}
    total_gex = 0.0

    for opt in chain:
        strike = float(opt.get("strike", 0))
        oi = int(opt.get("open_interest", 0))
        gamma = float(opt.get("gamma", 0))
        opt_type = opt.get("option_type", "").lower()
        multiplier = int(opt.get("contract_size", 100))

        if strike == 0 or oi == 0 or gamma == 0:
            continue

        # Dealers are short options → calls give positive gamma, puts negative
        if opt_type in ("call", "c"):
            gex = oi * gamma * multiplier * spot / 1_000_000
        elif opt_type in ("put", "p"):
            gex = -oi * gamma * multiplier * spot / 1_000_000
        else:
            continue

        gamma_by_strike[strike] = gamma_by_strike.get(strike, 0) + gex
        total_gex += gex

    return round(total_gex, 2), gamma_by_strike


def _find_gamma_flip(gamma_by_strike: Dict[float, float], spot: float) -> float:
    """Find the price level where net gamma crosses from positive to negative."""
    if not gamma_by_strike:
        return 0.0

    strikes = sorted(gamma_by_strike.keys())
    cumulative = 0.0
    flip_level = 0.0

    for strike in strikes:
        prev_cum = cumulative
        cumulative += gamma_by_strike[strike]
        if prev_cum >= 0 and cumulative < 0:
            flip_level = strike
            break
        elif prev_cum < 0 and cumulative >= 0:
            flip_level = strike

    return flip_level if flip_level > 0 else spot


def _find_call_wall(chain: List[Dict]) -> float:
    """Find strike with highest call gamma (resistance)."""
    max_gamma = 0.0
    wall_strike = 0.0
    for opt in chain:
        if opt.get("option_type", "").lower() not in ("call", "c"):
            continue
        oi = int(opt.get("open_interest", 0))
        gamma = float(opt.get("gamma", 0))
        total = oi * gamma
        if total > max_gamma:
            max_gamma = total
            wall_strike = float(opt.get("strike", 0))
    return wall_strike


def _find_put_wall(chain: List[Dict]) -> float:
    """Find strike with highest put gamma (support)."""
    max_gamma = 0.0
    wall_strike = 0.0
    for opt in chain:
        if opt.get("option_type", "").lower() not in ("put", "p"):
            continue
        oi = int(opt.get("open_interest", 0))
        gamma = float(opt.get("gamma", 0))
        total = oi * gamma
        if total > max_gamma:
            max_gamma = total
            wall_strike = float(opt.get("strike", 0))
    return wall_strike


def _compute_max_pain(chain: List[Dict]) -> float:
    """Compute max pain — strike where total option value expires worthless.

    For each candidate strike, sum the intrinsic value of all options.
    Max pain is the strike that minimizes this total.
    """
    if not chain:
        return 0.0

    strikes = sorted({float(opt.get("strike", 0)) for opt in chain if opt.get("strike")})
    if not strikes:
        return 0.0

    min_pain = float("inf")
    max_pain_strike = strikes[0]

    for candidate in strikes:
        total_pain = 0.0
        for opt in chain:
            strike = float(opt.get("strike", 0))
            oi = int(opt.get("open_interest", 0))
            opt_type = opt.get("option_type", "").lower()

            if opt_type in ("call", "c"):
                itm = max(0, candidate - strike)
            elif opt_type in ("put", "p"):
                itm = max(0, strike - candidate)
            else:
                continue

            total_pain += itm * oi * 100  # contract multiplier

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = candidate

    return max_pain_strike


def _compute_pin_probability(
    price: float, max_pain: float, chain: List[Dict],
) -> float:
    """Estimate pinning probability based on distance to max pain and time to expiry.

    Pinning is strongest when:
    1. Price is close to max pain
    2. Expiration is imminent (same day or next day)
    3. High open interest at max pain strike
    """
    if price == 0 or max_pain == 0:
        return 0.0

    # Distance factor: closer to max pain = higher pin probability
    distance_pct = abs(price - max_pain) / price
    distance_score = max(0, 1.0 - distance_pct * 20)  # Linear decay, 0 at 5% away

    # Time factor: check if nearest expiry is today/tomorrow
    time_score = 0.5  # Default moderate
    if chain:
        try:
            from datetime import date
            today = date.today()
            nearest_dte = None
            for opt in chain:
                exp = opt.get("expiration_date") or opt.get("expiry")
                if exp:
                    if isinstance(exp, str):
                        exp_date = datetime.fromisoformat(exp.replace("Z", "+00:00")).date()
                    elif isinstance(exp, datetime):
                        exp_date = exp.date()
                    else:
                        continue
                    dte = (exp_date - today).days
                    if nearest_dte is None or dte < nearest_dte:
                        nearest_dte = dte
            if nearest_dte is not None:
                if nearest_dte <= 0:
                    time_score = 1.0  # Expiration day
                elif nearest_dte == 1:
                    time_score = 0.8
                elif nearest_dte <= 3:
                    time_score = 0.5
                else:
                    time_score = 0.2
        except Exception:
            pass

    return round(min(1.0, distance_score * time_score), 2)
