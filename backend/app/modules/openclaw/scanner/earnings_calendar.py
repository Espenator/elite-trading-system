#!/usr/bin/env python3
"""
Earnings Calendar for OpenClaw
Earnings Date Checking & Trade Safety Filter

Checks upcoming earnings dates to:
  - Block entries within 3 days before earnings (avoid binary events)
  - Flag candidates with upcoming earnings for risk adjustment
  - Apply earnings penalty in composite scoring
  - Provide earnings context in trade alerts

Uses yfinance for earnings date lookups.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

# ========== EARNINGS CONFIG ==========
EARNINGS_BLOCK_DAYS = 3       # Block entries within 3 days before earnings
EARNINGS_WARNING_DAYS = 7     # Warn within 7 days
EARNINGS_PENALTY_SCORE = -10  # Score penalty for earnings proximity


class EarningsCalendar:
  """Check earnings dates and provide safety filters."""

  def __init__(self):
    self._cache: Dict[str, Dict] = {}  # symbol -> {date, fetched_at}

  def get_next_earnings(self, symbol: str) -> Optional[Dict]:
    """Get next earnings date for a symbol using yfinance."""
    # Check cache (valid for 24 hours)
    if symbol in self._cache:
      cached = self._cache[symbol]
      if (datetime.now(ET) - cached["fetched_at"]).total_seconds() < 86400:
        return cached

    try:
      import yfinance as yf
      ticker = yf.Ticker(symbol)

      # Try earnings_dates first
      try:
        earnings_dates = ticker.earnings_dates
        if earnings_dates is not None and len(earnings_dates) > 0:
          now = datetime.now(ET)
          future_dates = []
          for date in earnings_dates.index:
            dt = date.to_pydatetime()
            if dt.tzinfo is None:
              dt = dt.replace(tzinfo=ET)
            if dt > now:
              future_dates.append(dt)

          if future_dates:
            next_date = min(future_dates)
            days_until = (next_date.date() - now.date()).days
            result = {
              "symbol": symbol,
              "earnings_date": next_date.strftime("%Y-%m-%d"),
              "days_until": days_until,
              "fetched_at": now,
              "source": "yfinance",
            }
            self._cache[symbol] = result
            return result
      except Exception:
        pass

      # Fallback: try calendar
      try:
        cal = ticker.calendar
        if cal is not None and "Earnings Date" in cal:
          earn_dates = cal["Earnings Date"]
          if isinstance(earn_dates, list) and len(earn_dates) > 0:
            next_date = earn_dates[0]
            if hasattr(next_date, "date"):
              now = datetime.now(ET)
              days_until = (next_date.date() - now.date()).days if hasattr(next_date, "date") else 999
              result = {
                "symbol": symbol,
                "earnings_date": str(next_date.date()) if hasattr(next_date, "date") else str(next_date),
                "days_until": days_until,
                "fetched_at": now,
                "source": "yfinance_calendar",
              }
              self._cache[symbol] = result
              return result
      except Exception:
        pass

      # No earnings data found
      result = {
        "symbol": symbol,
        "earnings_date": None,
        "days_until": 999,
        "fetched_at": datetime.now(ET),
        "source": "none",
      }
      self._cache[symbol] = result
      return result

    except ImportError:
      logger.warning("yfinance not installed. Run: pip install yfinance")
      return {"symbol": symbol, "earnings_date": None, "days_until": 999, "source": "error"}
    except Exception as e:
      logger.error(f"Error checking earnings for {symbol}: {e}")
      return {"symbol": symbol, "earnings_date": None, "days_until": 999, "source": "error"}

  def check_earnings_safety(self, symbol: str) -> Dict:
    """Check if it's safe to enter a trade based on earnings proximity."""
    earnings = self.get_next_earnings(symbol)
    if not earnings:
      return {"safe": True, "reason": "No earnings data", "penalty": 0}

    days = earnings.get("days_until", 999)
    earnings_date = earnings.get("earnings_date", "unknown")

    if days <= EARNINGS_BLOCK_DAYS:
      return {
        "safe": False,
        "reason": f"BLOCKED: Earnings in {days} days ({earnings_date})",
        "days_until": days,
        "earnings_date": earnings_date,
        "penalty": EARNINGS_PENALTY_SCORE,
      }
    elif days <= EARNINGS_WARNING_DAYS:
      return {
        "safe": True,
        "reason": f"WARNING: Earnings in {days} days ({earnings_date})",
        "days_until": days,
        "earnings_date": earnings_date,
        "penalty": EARNINGS_PENALTY_SCORE // 2,  # Half penalty for warning zone
      }
    else:
      return {
        "safe": True,
        "reason": f"Clear: Earnings in {days}+ days",
        "days_until": days,
        "earnings_date": earnings_date,
        "penalty": 0,
      }

  def batch_check(self, symbols: List[str]) -> Dict[str, Dict]:
    """Check earnings safety for multiple symbols."""
    results = {}
    for symbol in symbols:
      results[symbol] = self.check_earnings_safety(symbol)
    return results

  def filter_safe_candidates(self, symbols: List[str]) -> List[str]:
    """Filter out candidates too close to earnings."""
    safe = []
    for symbol in symbols:
      check = self.check_earnings_safety(symbol)
      if check["safe"]:
        safe.append(symbol)
      else:
        logger.info(f"Earnings filter removed {symbol}: {check['reason']}")
    return safe

  def format_earnings_alert(self, check: Dict) -> str:
    """Format earnings check for Slack."""
    symbol = check.get("symbol", "???")
    safe = check.get("safe", True)
    reason = check.get("reason", "")
    days = check.get("days_until", 999)

    if days <= EARNINGS_BLOCK_DAYS:
      return f"\U0001f6d1 *{symbol}*: {reason}"
    elif days <= EARNINGS_WARNING_DAYS:
      return f"\u26a0\ufe0f *{symbol}*: {reason}"
    return ""


# ========== MODULE-LEVEL CONVENIENCE ==========

def check_earnings(symbol: str) -> Dict:
  """Check earnings safety for a single symbol."""
  cal = EarningsCalendar()
  return cal.check_earnings_safety(symbol)

def filter_by_earnings(symbols: List[str]) -> List[str]:
  """Filter symbols to only those safe from earnings."""
  cal = EarningsCalendar()
  return cal.filter_safe_candidates(symbols)

def get_earnings_penalties(symbols: List[str]) -> Dict[str, Dict]:
  """Get earnings safety data for list of symbols.
  Returns dict with blocked, penalty, reason, etc. for each symbol.
  Used by daily_scanner for earnings integration.
  """
  cal = EarningsCalendar()
  results = cal.batch_check(symbols)
  enriched = {}
  for sym, data in results.items():
    enriched[sym] = {
      "blocked": not data.get("safe", True),
      "penalty": data.get("penalty", 0),
      "reason": data.get("reason", ""),
      "days_until": data.get("days_until", 999),
      "earnings_date": data.get("earnings_date"),
      "safe": data.get("safe", True),
    }
  return enriched
