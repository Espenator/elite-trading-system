"""EMA Trend Agent — EMA cascade pattern classification.

Inspired by smarttrading.club EMA5/10/20 cascade and pattern codes:
UT=UpTrend, SU=StartUp, GU=GatherUp, DT=DownTrend, SD=StartDown,
GD=GatherDown, CR=Crash, RB=Rebound. Computes trend level scoring.
"""

import logging
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "ema_trend"
WEIGHT = 1.1


def _classify_ema_pattern(ema5: float, ema10: float, ema20: float, price: float) -> str:
      """Classify EMA cascade into smarttrading.club pattern codes."""
      if ema5 <= 0 or ema10 <= 0 or ema20 <= 0 or price <= 0:
                return "UNKNOWN"
            if price > ema5 > ema10 > ema20:
                      return "UT"
                  if price > ema5 > ema10 and ema10 <= ema20:
                            return "SU"
                        if price > ema5 and ema5 <= ema10:
                                  return "GU"
                              if price < ema5 < ema10 < ema20:
                                        return "DT"
                                    if price < ema5 < ema10 and ema10 >= ema20:
                                              return "SD"
                                          if price < ema5 and ema5 >= ema10:
                                                    return "GD"
                                                if price < ema5 < ema20 and ema10 > ema20:
                                                          return "CR"
                                                      if price > ema5 > ema20 and ema10 < ema20:
                                                                return "RB"
                                                            return "MIXED"


def _trend_level(ema5: float, ema10: float, ema20: float, price: float) -> int:
      """Score trend strength from -5 (strong down) to +5 (strong up)."""
    level = 0
    if price > ema5:
              level += 1
else:
        level -= 1
      if price > ema10:
                level += 1
else:
        level -= 1
      if price > ema20:
                level += 1
else:
        level -= 1
      if ema5 > ema10:
                level += 1
else:
        level -= 1
      if ema10 > ema20:
                level += 1
else:
        level -= 1
      return level


async def evaluate(
      symbol: str,
      timeframe: str,
      features: Dict[str, Any],
      context: Dict[str, Any],
) -> AgentVote:
      """Evaluate EMA cascade pattern and trend level."""
    f = features.get("features", features)

    price = float(f.get("last_close", 0))
    ema5 = float(f.get("ind_ema_5", 0) or f.get("ema_5", 0))
    ema10 = float(f.get("ind_ema_10", 0) or f.get("ema_10", 0))
    ema20 = float(f.get("ind_ema_20", 0) or f.get("ind_sma_20", 0) or f.get("ema_20", 0))
    sma_50 = float(f.get("ind_sma_50", 0))
    sma_200 = float(f.get("ind_sma_200", 0))

    pattern = _classify_ema_pattern(ema5, ema10, ema20, price)
    level = _trend_level(ema5, ema10, ema20, price)

    score = 0
    reasons = []

    # Pattern scoring
    pattern_scores = {
              "UT": 3, "SU": 2, "GU": 1, "RB": 1,
              "DT": -3, "SD": -2, "GD": -1, "CR": -2,
              "MIXED": 0, "UNKNOWN": 0,
    }
    score += pattern_scores.get(pattern, 0)
    reasons.append(f"EMA pattern={pattern} (level={level})")

    # Golden/death cross context
    if sma_50 > 0 and sma_200 > 0:
              if sma_50 > sma_200:
                            score += 1
                            reasons.append("Golden cross (SMA50>200)")
    elif sma_50 < sma_200:
            score -= 1
            reasons.append("Death cross (SMA50<200)")

    # Trend level adds granularity
    if level >= 4:
              score += 1
              reasons.append(f"Strong uptrend level={level}")
elif level <= -4:
        score -= 1
        reasons.append(f"Strong downtrend level={level}")

    if score >= 3:
              direction = "buy"
              confidence = min(0.85, 0.45 + score * 0.07)
elif score <= -3:
        direction = "sell"
        confidence = min(0.85, 0.45 + abs(score) * 0.07)
elif score >= 1:
        direction = "buy"
        confidence = 0.35 + score * 0.05
elif score <= -1:
        direction = "sell"
        confidence = 0.35 + abs(score) * 0.05
else:
        direction = "hold"
          confidence = 0.3

    return AgentVote(
              agent_name=NAME,
              direction=direction,
              confidence=round(min(0.9, confidence), 2),
              reasoning="; ".join(reasons[:5]),
              weight=WEIGHT,
              metadata={
                            "pattern": pattern,
                            "trend_level": level,
                            "ema5": round(ema5, 2),
                            "ema10": round(ema10, 2),
                            "ema20": round(ema20, 2),
                            "score": score,
              },
    )
