"""Cycle Timing Agent — day-of-week, month seasonality, and cycle phase.

Inspired by smarttrading.club Cycles and Timing section.
Detects dominant cycle phase, seasonal edges, and wave structure
to add timing context to council decisions.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "cycle_timing"
WEIGHT = 0.7


async def evaluate(
      symbol: str,
      timeframe: str,
      features: Dict[str, Any],
      context: Dict[str, Any],
) -> AgentVote:
      """Evaluate cycle phase and seasonal timing edges."""
      f = features.get("features", features)

    now = datetime.now(timezone.utc)
    day_of_week = now.weekday()
    month = now.month

    ret_1d = float(f.get("return_1d", 0))
    ret_5d = float(f.get("return_5d", 0))
    ret_20d = float(f.get("return_20d", 0))
    pct_from_high = float(f.get("pct_from_20d_high", 0))
    pct_from_low = float(f.get("pct_from_20d_low", 0))
    rsi = float(f.get("ind_rsi_14", 50))

    score = 0
    reasons = []

    # Day-of-week seasonality (well-documented Monday/Friday effects)
    dow_edges = {
              0: -0.3,  # Monday: historically weak
              1: 0.1,   # Tuesday: slight positive
              2: 0.1,   # Wednesday: slight positive
              3: 0.2,   # Thursday: positive
              4: 0.2,   # Friday: positive (pre-weekend positioning)
    }
    dow_edge = dow_edges.get(day_of_week, 0)
    dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if abs(dow_edge) >= 0.2:
              if dow_edge > 0:
                            score += 1
    else:
            score -= 1
              reasons.append(f"DOW edge: {dow_names[day_of_week]} ({dow_edge:+.1f})")

    # Monthly seasonality (November-April historically stronger)
    bullish_months = {11, 12, 1, 2, 3, 4}
    bearish_months = {5, 6, 9}
    if month in bullish_months:
              score += 1
              reasons.append(f"Bullish seasonal month ({month})")
elif month in bearish_months:
        score -= 1
        reasons.append(f"Bearish seasonal month ({month})")

    # Cycle phase from price position within recent range
    range_position = 0.5
    if pct_from_high != 0 or pct_from_low != 0:
              total_range = abs(pct_from_high) + abs(pct_from_low)
              if total_range > 0:
                            range_position = abs(pct_from_low) / total_range

          if range_position <= 0.15:
                    phase = "bottom"
                    score += 2
                    reasons.append(f"Cycle phase=bottom (pos={range_position:.2f})")
elif range_position <= 0.35:
        phase = "rising"
        score += 1
        reasons.append(f"Cycle phase=rising (pos={range_position:.2f})")
elif range_position >= 0.85:
        phase = "top"
        score -= 2
        reasons.append(f"Cycle phase=top (pos={range_position:.2f})")
elif range_position >= 0.65:
        phase = "falling"
        score -= 1
        reasons.append(f"Cycle phase=falling (pos={range_position:.2f})")
else:
        phase = "mid"
        reasons.append(f"Cycle phase=mid (pos={range_position:.2f})")

    # Momentum reversal at cycle extremes
    if phase == "bottom" and ret_1d > 0.005:
              score += 1
              reasons.append("Momentum confirming cycle bottom reversal")
elif phase == "top" and ret_1d < -0.005:
        score += -1
        reasons.append("Momentum confirming cycle top reversal")

    if score >= 3:
              direction = "buy"
              confidence = min(0.75, 0.35 + score * 0.07)
elif score <= -3:
        direction = "sell"
        confidence = min(0.75, 0.35 + abs(score) * 0.07)
elif score >= 1:
        direction = "buy"
        confidence = 0.3 + score * 0.04
elif score <= -1:
        direction = "sell"
        confidence = 0.3 + abs(score) * 0.04
else:
        direction = "hold"
        confidence = 0.25

    return AgentVote(
              agent_name=NAME,
              direction=direction,
              confidence=round(min(0.8, confidence), 2),
              reasoning="; ".join(reasons[:5]),
              weight=WEIGHT,
              metadata={
                            "phase": phase,
                            "range_position": round(range_position, 3),
                            "day_of_week": day_of_week,
                            "month": month,
                            "dow_edge": dow_edge,
                            "score": score,
              },
    )
