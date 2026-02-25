#!/usr/bin/env python3
"""
Smart Entry Module for OpenClaw v1.0

Intelligent order entry with:
  - VWAP-relative limit pricing
  - Session/time-of-day awareness
  - Entry quality scoring (0-100)
  - RSI divergence integration
  - ATR-based stop/target calculation
  - Complete order building for alpaca_client

Integrates with:
  - technical_checker.py (VWAP, RSI, ATR data)
  - position_sizer.py (share quantity)
  - composite_scorer.py (candidate scores)
  - position_manager.py (order parameters)
"""
import logging
from datetime import datetime
from typing import Dict, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")

# ========== SESSION CONFIG ==========
SESSION_WINDOWS = {
  "pre_market":    {"start": (4, 0),  "end": (9, 30),  "quality": 0.6, "label": "Pre-Market"},
  "opening_drive": {"start": (9, 30), "end": (10, 0),  "quality": 0.7, "label": "Opening Drive"},
  "morning_prime": {"start": (10, 0), "end": (11, 30), "quality": 1.0, "label": "Morning Prime"},
  "midday_chop":   {"start": (11, 30),"end": (14, 0),  "quality": 0.5, "label": "Midday Chop"},
  "power_hour":    {"start": (14, 0), "end": (15, 30), "quality": 0.85,"label": "Power Hour"},
  "closing":       {"start": (15, 30),"end": (16, 0),  "quality": 0.4, "label": "Closing"},
  "after_hours":   {"start": (16, 0), "end": (20, 0),  "quality": 0.3, "label": "After Hours"},
}

# Entry quality thresholds
ENTRY_GRADE_THRESHOLDS = {
  "A+": 90, "A": 80, "B+": 70, "B": 60, "C+": 50, "C": 40, "D": 30, "F": 0,
}


def get_session_quality() -> Dict:
  """Determine current trading session and quality multiplier."""
  now = datetime.now(ET)
  current_minutes = now.hour * 60 + now.minute

  for session_name, config in SESSION_WINDOWS.items():
    start_min = config["start"][0] * 60 + config["start"][1]
    end_min = config["end"][0] * 60 + config["end"][1]
    if start_min <= current_minutes < end_min:
      return {
        "session": session_name,
        "label": config["label"],
        "quality": config["quality"],
        "time": now.strftime("%H:%M ET"),
        "minutes_remaining": end_min - current_minutes,
      }

  return {"session": "closed", "label": "Market Closed", "quality": 0.0, "time": now.strftime("%H:%M ET"), "minutes_remaining": 0}


def score_entry_quality(technicals: Dict, session: Dict) -> Dict:
  """Score entry quality 0-100 based on technicals and session."""
  score = 0.0
  factors = []

  # 1. Session quality (0-15 pts)
  session_pts = session.get("quality", 0.5) * 15
  score += session_pts
  factors.append(f"Session({session.get('label', '?')}): {session_pts:.0f}")

  # 2. RSI positioning (0-20 pts)
  rsi = technicals.get("rsi", 50)
  if 30 <= rsi <= 45:
    rsi_pts = 20  # Oversold bounce zone
  elif 45 < rsi <= 60:
    rsi_pts = 15  # Healthy momentum
  elif 60 < rsi <= 70:
    rsi_pts = 10  # Getting extended
  elif rsi > 70:
    rsi_pts = 3   # Overbought
  else:
    rsi_pts = 5   # Deep oversold - risky
  score += rsi_pts
  factors.append(f"RSI({rsi:.0f}): {rsi_pts}")

  # 3. VWAP relationship (0-15 pts)
  price = technicals.get("price", 0)
  vwap = technicals.get("vwap", 0)
  if price and vwap:
    vwap_pct = (price - vwap) / vwap * 100 if vwap > 0 else 0
    if -0.5 <= vwap_pct <= 1.0:
      vwap_pts = 15  # Near VWAP, ideal
    elif 1.0 < vwap_pct <= 2.0:
      vwap_pts = 10  # Slightly above
    elif vwap_pct < -0.5:
      vwap_pts = 5   # Below VWAP
    else:
      vwap_pts = 3   # Extended above VWAP
    score += vwap_pts
    factors.append(f"VWAP({vwap_pct:+.1f}%): {vwap_pts}")

  # 4. Trend alignment (0-15 pts)
  sma20 = technicals.get("sma_20", 0)
  sma200 = technicals.get("sma_200", 0)
  ema50 = technicals.get("ema_50", 0)
  trend_pts = 0
  if price and sma20 and price > sma20:
    trend_pts += 5
  if price and ema50 and price > ema50:
    trend_pts += 5
  if sma20 and sma200 and sma20 > sma200:
    trend_pts += 5
  score += trend_pts
  factors.append(f"Trend: {trend_pts}")

  # 5. Volume confirmation (0-10 pts)
  vol_ratio = technicals.get("volume_ratio", 1.0)
  if vol_ratio >= 2.0:
    vol_pts = 10
  elif vol_ratio >= 1.5:
    vol_pts = 7
  elif vol_ratio >= 1.0:
    vol_pts = 4
  else:
    vol_pts = 1
  score += vol_pts
  factors.append(f"Volume({vol_ratio:.1f}x): {vol_pts}")

  # 6. Pattern quality (0-15 pts)
  pattern_pts = 0
  if technicals.get("breakout"):
    pattern_pts += 8
  if technicals.get("basing"):
    pattern_pts += 4
  if technicals.get("channel_up"):
    pattern_pts += 5
  if technicals.get("amd_detected"):
    pattern_pts += 7
  if technicals.get("elephant_bar"):
    pattern_pts += 5
  pattern_pts = min(pattern_pts, 15)
  score += pattern_pts
  factors.append(f"Patterns: {pattern_pts}")

  # 7. ADX strength (0-10 pts)
  adx = technicals.get("adx", 20)
  if adx >= 30:
    adx_pts = 10
  elif adx >= 25:
    adx_pts = 7
  elif adx >= 20:
    adx_pts = 4
  else:
    adx_pts = 1
  score += adx_pts
  factors.append(f"ADX({adx:.0f}): {adx_pts}")

  # Cap at 100
  score = min(100, max(0, score))

  # Determine grade
  grade = "F"
  for g, threshold in ENTRY_GRADE_THRESHOLDS.items():
    if score >= threshold:
      grade = g
      break

  # Determine recommendation
  if score >= 75:
    recommendation = "limit"  # Strong setup - use limit for better fill
  elif score >= 55:
    recommendation = "limit"  # Good setup
  elif score >= 40:
    recommendation = "market" # Decent - market to ensure fill
  else:
    recommendation = "skip"   # Poor setup

  return {
    "entry_score": round(score, 1),
    "entry_grade": grade,
    "recommendation": recommendation,
    "factors": factors,
    "session": session.get("label", "Unknown"),
  }


def calculate_limit_price(price: float, atr: float, vwap: float = 0) -> Dict:
  """Calculate limit price, stop loss, and take profit targets."""
  if not price or not atr:
    return {"error": "Missing price or ATR"}

  # VWAP-relative limit pricing
  if vwap and vwap > 0:
    vwap_distance = price - vwap
    if vwap_distance > 0 and vwap_distance < atr * 0.5:
      # Price near but above VWAP - bid at VWAP + small offset
      limit_price = round(vwap + atr * 0.1, 2)
    elif vwap_distance <= 0:
      # Below VWAP - bid at current price (catching the dip)
      limit_price = round(price + atr * 0.05, 2)
    else:
      # Extended above VWAP - bid slightly below current
      limit_price = round(price - atr * 0.15, 2)
  else:
    # No VWAP - bid slightly below current price
    limit_price = round(price - atr * 0.1, 2)

  # Stop loss: 1.5 ATR below entry
  stop_loss = round(limit_price - atr * 1.5, 2)

  # Take profit targets
  take_profit_1 = round(limit_price + atr * 1.5, 2)
  take_profit_2 = round(limit_price + atr * 2.5, 2)
  take_profit_3 = round(limit_price + atr * 4.0, 2)

  # Risk/reward
  risk_per_share = round(limit_price - stop_loss, 2)
  reward_per_share = round(take_profit_1 - limit_price, 2)
  reward_risk_ratio = round(reward_per_share / risk_per_share, 2) if risk_per_share > 0 else 0

  return {
    "limit_price": limit_price,
    "stop_loss": stop_loss,
    "take_profit_1": take_profit_1,
    "take_profit_2": take_profit_2,
    "take_profit_3": take_profit_3,
    "risk_per_share": risk_per_share,
    "reward_risk_ratio": reward_risk_ratio,
    "vwap_used": bool(vwap),
  }


def build_smart_order(ticker: str, technicals: Dict,
                     position_size: Dict = None) -> Dict:
  """Build a complete smart order with entry timing."""
  session = get_session_quality()
  entry = score_entry_quality(technicals, session)

  price = technicals.get("price", 0)
  atr = technicals.get("atr", 0)
  vwap = technicals.get("vwap", 0)

  if not price or not atr:
    return {"error": "Missing price or ATR", "ticker": ticker}

  pricing = calculate_limit_price(price, atr, vwap)
  qty = position_size.get("shares", 0) if position_size else 0

  return {
    "ticker": ticker,
    "side": "buy",
    "qty": qty,
    "order_type": entry["recommendation"],
    "limit_price": pricing["limit_price"],
    "stop_loss": pricing["stop_loss"],
    "take_profit": pricing["take_profit_1"],
    "take_profit_2": pricing["take_profit_2"],
    "take_profit_3": pricing["take_profit_3"],
    "risk_per_share": pricing["risk_per_share"],
    "reward_risk": pricing["reward_risk_ratio"],
    "entry_score": entry["entry_score"],
    "entry_grade": entry["entry_grade"],
    "session": session["session"],
    "factors": entry["factors"],
    "vwap_used": pricing["vwap_used"],
  }
