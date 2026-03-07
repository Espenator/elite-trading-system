#!/usr/bin/env python3
"""
AMD Pattern Detector for OpenClaw
Accumulation -> Manipulation -> Distribution Pattern Detection

Detects the classic AMD cycle used by institutional traders:
  A (Accumulation): Tight range / consolidation (Asian session or pre-market)
  M (Manipulation): False breakout / stop hunt (first 30-60 min of session)
  D (Distribution): Real directional move with volume (trend continuation)

Based on 1-hour chart trading methodology from trading plan.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed
from ..config import ALPACA_API_KEY, ALPACA_SECRET_KEY

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

# ========== AMD THRESHOLDS ==========
ACCUM_MAX_RANGE_ATR = 0.4     # Accumulation range <= 40% of ATR
ACCUM_MIN_BARS = 3            # Minimum bars in consolidation
MANIP_MIN_WICK_PCT = 0.5      # Manipulation candle wick >= 50%
MANIP_MAX_BODY_PCT = 0.35     # Manipulation candle body <= 35%
DIST_MIN_BODY_PCT = 0.6       # Distribution candle body >= 60%
DIST_MIN_VOL_RATIO = 1.5      # Distribution volume >= 1.5x avg


class AMDDetector:
  """Detect Accumulation-Manipulation-Distribution patterns."""

  def __init__(self):
    self.data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

  def fetch_bars(self, symbol: str, timeframe: TimeFrame = TimeFrame.Hour,
                 lookback_days: int = 3) -> List[Dict]:
    """Fetch historical bars for analysis."""
    try:
      end = datetime.now(ET)
      start = end - timedelta(days=lookback_days)
      request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
                  feed=DataFeed.IEX,
      )
      bars = self.data_client.get_stock_bars(request)
      bar_list = bars[symbol] if symbol in bars else []

      result = []
      for bar in bar_list:
        o, h, l, c = float(bar.open), float(bar.high), float(bar.low), float(bar.close)
        full_range = h - l if h != l else 0.001
        body = abs(c - o)
        result.append({
          "timestamp": bar.timestamp,
          "open": o, "high": h, "low": l, "close": c,
          "volume": int(bar.volume),
          "range": round(full_range, 4),
          "body": round(body, 4),
          "body_pct": round(body / full_range, 3),
          "upper_wick": round(h - max(o, c), 4),
          "lower_wick": round(min(o, c) - l, 4),
          "bullish": c > o,
        })
      return result
    except Exception as e:
      logger.error(f"Error fetching bars for {symbol}: {e}")
      return []

  def detect_accumulation(self, bars: List[Dict], atr: float) -> Optional[Dict]:
    """Detect accumulation (tight range consolidation) phase."""
    if len(bars) < ACCUM_MIN_BARS:
      return None

    # Look for consecutive tight-range bars
    tight_bars = []
    for bar in bars:
      if bar["range"] <= atr * ACCUM_MAX_RANGE_ATR:
        tight_bars.append(bar)
      else:
        if len(tight_bars) >= ACCUM_MIN_BARS:
          break
        tight_bars = []

    if len(tight_bars) < ACCUM_MIN_BARS:
      return None

    range_high = max(b["high"] for b in tight_bars)
    range_low = min(b["low"] for b in tight_bars)
    avg_volume = sum(b["volume"] for b in tight_bars) / len(tight_bars)

    return {
      "phase": "ACCUMULATION",
      "bars": len(tight_bars),
      "range_high": round(range_high, 2),
      "range_low": round(range_low, 2),
      "range_width": round(range_high - range_low, 2),
      "avg_volume": int(avg_volume),
      "range_pct_atr": round((range_high - range_low) / atr, 2) if atr > 0 else 0,
    }

  def detect_manipulation(self, bar: Dict, accum_range: Dict) -> Optional[Dict]:
    """Detect manipulation (false breakout / stop hunt) candle."""
    if not accum_range:
      return None

    range_high = accum_range["range_high"]
    range_low = accum_range["range_low"]
    full_range = bar["range"]

    # Check for false breakout above (then close back inside)
    broke_above = bar["high"] > range_high
    closed_below_high = bar["close"] < range_high
    upper_wick_pct = bar["upper_wick"] / full_range if full_range > 0 else 0

    # Check for false breakout below (then close back inside)
    broke_below = bar["low"] < range_low
    closed_above_low = bar["close"] > range_low
    lower_wick_pct = bar["lower_wick"] / full_range if full_range > 0 else 0

    manipulation_type = None
    if broke_above and closed_below_high and upper_wick_pct >= MANIP_MIN_WICK_PCT:
      manipulation_type = "BEAR_TRAP"  # Fake breakout above, bullish signal
    elif broke_below and closed_above_low and lower_wick_pct >= MANIP_MIN_WICK_PCT:
      manipulation_type = "BULL_TRAP"  # Fake breakdown below, bearish signal
    elif bar["body_pct"] <= MANIP_MAX_BODY_PCT:
      # Doji-like indecision after accumulation
      manipulation_type = "INDECISION"

    if not manipulation_type:
      return None

    return {
      "phase": "MANIPULATION",
      "type": manipulation_type,
      "bar": bar,
      "broke_above": broke_above,
      "broke_below": broke_below,
      "upper_wick_pct": round(upper_wick_pct, 3),
      "lower_wick_pct": round(lower_wick_pct, 3),
      "expected_direction": "LONG" if manipulation_type == "BULL_TRAP" or (broke_above and closed_below_high) else "SHORT",
    }

  def detect_distribution(self, bar: Dict, manip: Dict, avg_volume: int) -> Optional[Dict]:
    """Detect distribution (real move) after manipulation."""
    if not manip:
      return None

    vol_ratio = bar["volume"] / avg_volume if avg_volume > 0 else 0

    # Strong directional candle with volume
    if bar["body_pct"] < DIST_MIN_BODY_PCT:
      return None
    if vol_ratio < DIST_MIN_VOL_RATIO:
      return None

    direction = "LONG" if bar["bullish"] else "SHORT"
    expected = manip.get("expected_direction", "")
    aligned = direction == expected

    return {
      "phase": "DISTRIBUTION",
      "direction": direction,
      "aligned_with_manipulation": aligned,
      "body_pct": bar["body_pct"],
      "volume_ratio": round(vol_ratio, 2),
      "bar": bar,
      "confidence": "HIGH" if aligned and vol_ratio >= 2.0 else "MODERATE" if aligned else "LOW",
    }

  def scan_for_amd(self, symbol: str, atr: float) -> Dict:
    """Full AMD pattern scan for a symbol."""
    bars = self.fetch_bars(symbol, TimeFrame.Hour, lookback_days=3)
    if len(bars) < 6:
      return {"symbol": symbol, "pattern": None, "reason": "Insufficient data"}

    # Split bars into segments for analysis
    accum = self.detect_accumulation(bars[:-2], atr)
    if not accum:
      return {"symbol": symbol, "pattern": None, "reason": "No accumulation detected"}

    avg_vol = accum["avg_volume"]
    manip = self.detect_manipulation(bars[-2], accum)
    if not manip:
      return {
        "symbol": symbol,
        "pattern": "ACCUMULATION_ONLY",
        "accumulation": accum,
        "reason": "Accumulation found, awaiting manipulation",
      }

    dist = self.detect_distribution(bars[-1], manip, avg_vol)
    if not dist:
      return {
        "symbol": symbol,
        "pattern": "AM_PENDING_D",
        "accumulation": accum,
        "manipulation": manip,
        "reason": "A+M found, awaiting distribution move",
      }

    # Full AMD pattern detected
    return {
      "symbol": symbol,
      "pattern": "AMD_COMPLETE",
      "accumulation": accum,
      "manipulation": manip,
      "distribution": dist,
      "direction": dist["direction"],
      "confidence": dist["confidence"],
      "reason": f"Full AMD pattern: {dist['direction']} ({dist['confidence']})",
    }

  def format_amd_alert(self, result: Dict) -> str:
    """Format AMD detection for Slack."""
    symbol = result.get("symbol", "???")
    pattern = result.get("pattern", "none")

    if not pattern or pattern == "none":
      return ""

    lines = [f"*AMD Pattern: {symbol}*"]
    lines.append(f"  Pattern: {pattern}")
    lines.append(f"  {result.get('reason', '')}")

    if "accumulation" in result:
      a = result["accumulation"]
      lines.append(f"  Accum: {a['bars']} bars, range ${a['range_low']}-${a['range_high']}")

    if "manipulation" in result:
      m = result["manipulation"]
      lines.append(f"  Manip: {m['type']} | Expected: {m.get('expected_direction', 'n/a')}")

    if "distribution" in result:
      d = result["distribution"]
      lines.append(f"  Dist: {d['direction']} | Vol {d['volume_ratio']}x | {d['confidence']}")

    return "\n".join(lines)


# ========== MODULE-LEVEL CONVENIENCE ==========

def scan_amd_patterns(symbols: List[str], atrs: Dict[str, float]) -> List[Dict]:
  """Scan multiple symbols for AMD patterns."""
  detector = AMDDetector()
  results = []
  for symbol in symbols:
    atr = atrs.get(symbol, 0)
    if atr > 0:
      result = detector.scan_for_amd(symbol, atr)
      if result.get("pattern"):
        results.append(result)
  return results
