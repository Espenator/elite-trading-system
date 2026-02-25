#!/usr/bin/env python3
"""
Session Monitor for OpenClaw
1-Hour Candle Intraday Session Monitoring

Monitors the key trading sessions (9:30-12:00 AM ET power window)
for entry signals on watchlist candidates using 1H candle data.

Sessions:
  - Pre-market: 7:00-9:30 AM ET (gap analysis)
  - Power Hour: 9:30-10:30 AM ET (primary entries)
  - Morning: 10:30-12:00 PM ET (secondary entries)
  - Midday: 12:00-2:00 PM ET (avoid, low volume)
  - Afternoon: 2:00-4:00 PM ET (trend continuation only)
"""
import logging
from datetime import datetime, time
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

# ========== SESSION WINDOWS ==========
SESSIONS = {
  "PRE_MARKET": {"start": time(7, 0), "end": time(9, 30), "tradeable": False, "label": "Pre-Market"},
  "POWER_HOUR": {"start": time(9, 30), "end": time(10, 30), "tradeable": True, "label": "Power Hour"},
  "MORNING": {"start": time(10, 30), "end": time(12, 0), "tradeable": True, "label": "Morning"},
  "MIDDAY": {"start": time(12, 0), "end": time(14, 0), "tradeable": False, "label": "Midday (Avoid)"},
  "AFTERNOON": {"start": time(14, 0), "end": time(16, 0), "tradeable": True, "label": "Afternoon"},
}

# ========== ENTRY SIGNAL THRESHOLDS ==========
MIN_1H_VOLUME_RATIO = 1.3    # 1H volume must be 1.3x avg
MIN_1H_BODY_PCT = 0.5        # Candle body >= 50% of range
MAX_UPPER_WICK_PCT = 0.30    # Upper wick < 30% of range
MIN_RANGE_ATR_RATIO = 0.5    # 1H range >= 50% of daily ATR


class SessionMonitor:
  """Monitor 1H candles for entry signals during key sessions."""

  def __init__(self):
    self.data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

  def get_current_session(self) -> Optional[Dict]:
    """Determine which trading session we're currently in."""
    now_et = datetime.now(ET).time()
    for session_id, session in SESSIONS.items():
      if session["start"] <= now_et < session["end"]:
        return {"id": session_id, **session}
    return None

  def is_entry_window(self) -> bool:
    """Check if current time is within a tradeable entry window."""
    session = self.get_current_session()
    return session is not None and session["tradeable"]

  def fetch_1h_bars(self, symbol: str, lookback_days: int = 5) -> List[Dict]:
    """Fetch 1H bars from Alpaca for candle analysis."""
    try:
      from datetime import timedelta
      end = datetime.now(ET)
      start = end - timedelta(days=lookback_days)

      request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Hour,
        start=start,
        end=end,
      )
      bars = self.data_client.get_stock_bars(request)
      bar_list = bars[symbol] if symbol in bars else []

      result = []
      for bar in bar_list:
        result.append({
          "timestamp": bar.timestamp,
          "open": float(bar.open),
          "high": float(bar.high),
          "low": float(bar.low),
          "close": float(bar.close),
          "volume": int(bar.volume),
        })
      return result
    except Exception as e:
      logger.error(f"Error fetching 1H bars for {symbol}: {e}")
      return []

  def analyze_candle(self, candle: Dict) -> Dict:
    """Analyze a single 1H candle for entry signal quality."""
    o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
    full_range = h - l if h != l else 0.001
    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    is_bullish = c > o

    body_pct = body / full_range
    upper_wick_pct = upper_wick / full_range
    lower_wick_pct = lower_wick / full_range

    # Classify candle type
    candle_type = "neutral"
    if body_pct >= 0.7 and is_bullish:
      candle_type = "strong_bull"  # Elephant bar
    elif body_pct >= 0.5 and is_bullish:
      candle_type = "bull"
    elif body_pct >= 0.7 and not is_bullish:
      candle_type = "strong_bear"
    elif body_pct >= 0.5 and not is_bullish:
      candle_type = "bear"
    elif body_pct < 0.3:
      candle_type = "doji"  # Indecision
    elif lower_wick_pct >= 0.6:
      candle_type = "hammer"  # Reversal signal
    elif upper_wick_pct >= 0.6:
      candle_type = "shooting_star"

    return {
      "type": candle_type,
      "bullish": is_bullish,
      "body_pct": round(body_pct, 3),
      "upper_wick_pct": round(upper_wick_pct, 3),
      "lower_wick_pct": round(lower_wick_pct, 3),
      "range": round(full_range, 2),
      "volume": candle["volume"],
    }

  def check_entry_signal(self, symbol: str, daily_atr: float = 0) -> Dict:
    """Check if a symbol has a valid 1H entry signal right now."""
    session = self.get_current_session()
    if not session:
      return {"signal": False, "reason": "Market closed"}
    if not session["tradeable"]:
      return {"signal": False, "reason": f"Non-tradeable session: {session['label']}"}

    bars = self.fetch_1h_bars(symbol, lookback_days=5)
    if len(bars) < 5:
      return {"signal": False, "reason": "Insufficient 1H data"}

    latest = bars[-1]
    analysis = self.analyze_candle(latest)

    # Calculate average volume from prior bars
    prior_volumes = [b["volume"] for b in bars[:-1]]
    avg_volume = sum(prior_volumes) / len(prior_volumes) if prior_volumes else 1
    volume_ratio = latest["volume"] / avg_volume if avg_volume > 0 else 0

    # Entry signal scoring
    score = 0
    reasons = []

    # 1. Bullish candle type
    if analysis["type"] in ("strong_bull", "bull"):
      score += 30
      reasons.append(f"Bullish candle: {analysis['type']}")
    elif analysis["type"] == "hammer":
      score += 25
      reasons.append("Hammer reversal candle")
    else:
      reasons.append(f"Candle type: {analysis['type']}")

    # 2. Volume confirmation
    if volume_ratio >= MIN_1H_VOLUME_RATIO:
      score += 25
      reasons.append(f"Volume {volume_ratio:.1f}x avg")
    elif volume_ratio >= 1.0:
      score += 10
      reasons.append(f"Volume {volume_ratio:.1f}x avg (ok)")
    else:
      reasons.append(f"Low volume {volume_ratio:.1f}x")

    # 3. Body quality (clean candle, small wicks)
    if analysis["body_pct"] >= MIN_1H_BODY_PCT:
      score += 15
      reasons.append(f"Strong body {analysis['body_pct']:.0%}")

    if analysis["upper_wick_pct"] <= MAX_UPPER_WICK_PCT:
      score += 10
      reasons.append("Clean close (small upper wick)")

    # 4. ATR confirmation (if provided)
    if daily_atr > 0:
      range_atr = analysis["range"] / daily_atr
      if range_atr >= MIN_RANGE_ATR_RATIO:
        score += 20
        reasons.append(f"Range {range_atr:.0%} of ATR")
      else:
        reasons.append(f"Weak range {range_atr:.0%} of ATR")

    # 5. Session bonus
    if session["id"] == "POWER_HOUR":
      score += 10
      reasons.append("Power Hour bonus +10")
    elif session["id"] == "AFTERNOON":
      score -= 5
      reasons.append("Afternoon penalty -5")

    # Determine signal
    signal = score >= 60
    tier = "STRONG" if score >= 80 else "MODERATE" if score >= 60 else "WEAK"

    return {
      "signal": signal,
      "score": score,
      "tier": tier,
      "session": session["label"],
      "candle": analysis,
      "volume_ratio": round(volume_ratio, 2),
      "reasons": reasons,
    }

  def scan_watchlist(self, symbols: List[str], daily_atrs: Dict[str, float] = None) -> List[Dict]:
    """Scan entire watchlist for entry signals."""
    if daily_atrs is None:
      daily_atrs = {}

    results = []
    for symbol in symbols:
      atr = daily_atrs.get(symbol, 0)
      signal = self.check_entry_signal(symbol, daily_atr=atr)
      signal["symbol"] = symbol
      results.append(signal)

    # Sort by score descending
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results

  def format_signal_alert(self, signal: Dict) -> str:
    """Format a signal for Slack notification."""
    if not signal.get("signal"):
      return ""

    symbol = signal.get("symbol", "???")
    score = signal.get("score", 0)
    tier = signal.get("tier", "UNKNOWN")
    session = signal.get("session", "")
    candle = signal.get("candle", {})
    vol = signal.get("volume_ratio", 0)

    emoji = "\U0001f7e2" if tier == "STRONG" else "\U0001f7e1"  # green/yellow circle
    return (
      f"{emoji} *1H Entry Signal: {symbol}*\n"
      f"  Score: {score}/100 ({tier})\n"
      f"  Session: {session}\n"
      f"  Candle: {candle.get('type', 'n/a')} | Body: {candle.get('body_pct', 0):.0%}\n"
      f"  Volume: {vol:.1f}x average\n"
      f"  Reasons: {', '.join(signal.get('reasons', []))}\n"
    )


# ========== MODULE-LEVEL CONVENIENCE ==========

def check_session_entries(symbols: List[str], daily_atrs: Dict[str, float] = None) -> List[Dict]:
  """Convenience function for pipeline use."""
  monitor = SessionMonitor()
  return monitor.scan_watchlist(symbols, daily_atrs)

def get_current_session() -> Optional[Dict]:
  """Get the current trading session info."""
  monitor = SessionMonitor()
  return monitor.get_current_session()
