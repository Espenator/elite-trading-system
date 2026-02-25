#!/usr/bin/env python3
"""
Sector Rotation Tracker for OpenClaw
Finviz-based Sector Performance Ranking & Rotation Detection

Tracks sector ETF performance across multiple timeframes to:
  - Identify leading/lagging sectors
  - Detect rotation shifts (money moving between sectors)
  - Boost candidates in hot sectors, penalize lagging ones
  - Provide sector context for the composite scorer

Sector ETFs tracked:
  XLK (Tech), XLF (Financials), XLE (Energy), XLV (Healthcare),
  XLI (Industrials), XLP (Staples), XLY (Discretionary),
  XLU (Utilities), XLRE (Real Estate), XLB (Materials), XLC (Comms)
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY

logger = logging.getLogger(__name__)

# ========== SECTOR ETF MAPPING ==========
SECTOR_ETFS = {
  "Technology": "XLK",
  "Financial": "XLF",
  "Energy": "XLE",
  "Healthcare": "XLV",
  "Industrial": "XLI",
  "Consumer Staples": "XLP",
  "Consumer Discretionary": "XLY",
  "Utilities": "XLU",
  "Real Estate": "XLRE",
  "Materials": "XLB",
  "Communication": "XLC",
}

# Reverse mapping: ETF -> sector name
ETF_TO_SECTOR = {v: k for k, v in SECTOR_ETFS.items()}

# Common stock -> sector mapping for quick lookups
STOCK_SECTOR_HINTS = {
  "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
  "GOOGL": "Communication", "META": "Communication", "NFLX": "Communication",
  "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
  "JPM": "Financial", "GS": "Financial", "BAC": "Financial",
  "XOM": "Energy", "CVX": "Energy", "SLB": "Energy",
  "UNH": "Healthcare", "JNJ": "Healthcare", "PFE": "Healthcare",
  "CAT": "Industrial", "BA": "Industrial", "GE": "Industrial",
}

# ========== ROTATION THRESHOLDS ==========
HOT_SECTOR_THRESHOLD = 2.0    # >= 2% weekly = hot
COLD_SECTOR_THRESHOLD = -2.0  # <= -2% weekly = cold
ROTATION_SHIFT_PCT = 3.0      # 3% rank change = rotation signal


class SectorRotation:
  """Track sector performance and rotation patterns."""

  def __init__(self):
    self.data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

  def get_sector_performance(self, lookback_days: int = 5) -> List[Dict]:
    """Calculate sector ETF performance over given period."""
    results = []
    etf_symbols = list(SECTOR_ETFS.values())

    try:
      from datetime import timedelta
      from zoneinfo import ZoneInfo
      ET = ZoneInfo("America/New_York")
      end = datetime.now(ET)
      start = end - timedelta(days=lookback_days + 5)  # Extra buffer for weekends

      request = StockBarsRequest(
        symbol_or_symbols=etf_symbols,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
                  feed=DataFeed.IEX,
      )
      bars = self.data_client.get_stock_bars(request)

      for sector_name, etf in SECTOR_ETFS.items():
        if etf not in bars or len(bars[etf]) < 2:
          continue

        bar_list = list(bars[etf])
        current = float(bar_list[-1].close)
        period_start = float(bar_list[0].close)
        pct_change = ((current / period_start) - 1) * 100

        # Volume trend (last bar vs avg)
        volumes = [int(b.volume) for b in bar_list]
        avg_vol = sum(volumes[:-1]) / max(len(volumes) - 1, 1)
        vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1.0

        results.append({
          "sector": sector_name,
          "etf": etf,
          "pct_change": round(pct_change, 2),
          "current_price": round(current, 2),
          "volume_ratio": round(vol_ratio, 2),
          "status": "HOT" if pct_change >= HOT_SECTOR_THRESHOLD else "COLD" if pct_change <= COLD_SECTOR_THRESHOLD else "NEUTRAL",
        })

    except Exception as e:
      logger.error(f"Error fetching sector data: {e}")

    # Sort by performance descending
    results.sort(key=lambda x: x["pct_change"], reverse=True)

    # Add rank
    for i, r in enumerate(results):
      r["rank"] = i + 1

    return results

  def get_multi_timeframe_rotation(self) -> Dict:
    """Get sector rankings across 1-week, 1-month, 3-month periods."""
    weekly = self.get_sector_performance(lookback_days=5)
    monthly = self.get_sector_performance(lookback_days=22)
    quarterly = self.get_sector_performance(lookback_days=63)

    # Detect rotation: sectors moving up in rank
    weekly_ranks = {r["sector"]: r["rank"] for r in weekly}
    monthly_ranks = {r["sector"]: r["rank"] for r in monthly}

    rotating_in = []  # Improving sectors
    rotating_out = []  # Declining sectors

    for sector in weekly_ranks:
      w_rank = weekly_ranks.get(sector, 6)
      m_rank = monthly_ranks.get(sector, 6)
      rank_change = m_rank - w_rank  # Positive = improving

      if rank_change >= 3:
        rotating_in.append({"sector": sector, "rank_improvement": rank_change})
      elif rank_change <= -3:
        rotating_out.append({"sector": sector, "rank_decline": abs(rank_change)})

    return {
      "weekly": weekly,
      "monthly": monthly,
      "quarterly": quarterly,
      "rotating_in": rotating_in,
      "rotating_out": rotating_out,
      "top_3_weekly": [r["sector"] for r in weekly[:3]],
      "bottom_3_weekly": [r["sector"] for r in weekly[-3:]],
    }

  def get_sector_score_modifier(self, symbol: str) -> Dict:
    """Get sector-based score modifier for a candidate stock."""
    sector = STOCK_SECTOR_HINTS.get(symbol)
    if not sector:
      return {"modifier": 0, "sector": "Unknown", "reason": "Sector not mapped"}

    weekly = self.get_sector_performance(lookback_days=5)
    sector_data = next((r for r in weekly if r["sector"] == sector), None)

    if not sector_data:
      return {"modifier": 0, "sector": sector, "reason": "No sector data"}

    modifier = 0
    reason = ""

    if sector_data["status"] == "HOT":
      modifier = 5
      reason = f"Hot sector ({sector}: +{sector_data['pct_change']:.1f}% weekly)"
    elif sector_data["status"] == "COLD":
      modifier = -5
      reason = f"Cold sector ({sector}: {sector_data['pct_change']:.1f}% weekly)"
    elif sector_data["rank"] <= 3:
      modifier = 3
      reason = f"Top 3 sector ({sector}: rank #{sector_data['rank']})"
    elif sector_data["rank"] >= 9:
      modifier = -3
      reason = f"Bottom 3 sector ({sector}: rank #{sector_data['rank']})"

    return {
      "modifier": modifier,
      "sector": sector,
      "etf": sector_data["etf"],
      "pct_change": sector_data["pct_change"],
      "rank": sector_data["rank"],
      "status": sector_data["status"],
      "reason": reason,
    }

  def format_sector_report(self, rotation_data: Dict) -> str:
    """Format sector rotation report for Slack."""
    lines = ["*Sector Rotation Report*\n"]

    # Weekly rankings
    lines.append("*Weekly Performance:*")
    for r in rotation_data.get("weekly", []):
      emoji = "\U0001f525" if r["status"] == "HOT" else "\U0001f9ca" if r["status"] == "COLD" else "\u2796"
      lines.append(f"  {emoji} #{r['rank']} {r['sector']} ({r['etf']}): {r['pct_change']:+.1f}%")

    # Rotation signals
    if rotation_data.get("rotating_in"):
      lines.append("\n*Rotating IN (gaining strength):*")
      for r in rotation_data["rotating_in"]:
        lines.append(f"  \u2B06 {r['sector']} (+{r['rank_improvement']} ranks)")

    if rotation_data.get("rotating_out"):
      lines.append("\n*Rotating OUT (losing strength):*")
      for r in rotation_data["rotating_out"]:
        lines.append(f"  \u2B07 {r['sector']} (-{r['rank_decline']} ranks)")

    return "\n".join(lines)


# ========== MODULE-LEVEL CONVENIENCE ==========

def get_sector_rankings() -> List[Dict]:
  """Get current sector rankings."""
  tracker = SectorRotation()
  return tracker.get_sector_performance()

def get_rotation_report() -> Dict:
  """Get full multi-timeframe rotation report."""
  tracker = SectorRotation()
  return tracker.get_multi_timeframe_rotation()

def get_sector_modifier(symbol: str) -> Dict:
  """Get sector score modifier for a stock."""
  tracker = SectorRotation()
  return tracker.get_sector_score_modifier(symbol)
