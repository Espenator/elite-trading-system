#!/usr/bin/env python3
"""
Position Manager for OpenClaw v2.0
Trailing Stop Management & Open Position Monitoring

v2.0 Enhancements:
  - HMM regime-aware stop adjustments
  - Volatility-scaled trailing (ATR + regime)
  - Partial profit automation with Alpaca execution
  - Correlation-based portfolio heat tracking
  - Enhanced circuit breaker with drawdown memory
  - Auto-tighten on momentum fade (RSI divergence)
  - Session-aware stop behavior (no tighten in first 15 min)
  - Position aging with forced review alerts

Manages open positions with:
  - ATR-based trailing stops (regime-adaptive multiplier)
  - Target-based partial exits (T1/T2/T3) with Alpaca execution
  - Time-based stop tightening
  - Break-even automation after T1 hit
  - Daily P&L monitoring and circuit breaker
  - Portfolio-level risk management
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from zoneinfo import ZoneInfo
from pathlib import Path

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, MAX_DAILY_LOSS_PCT

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")

# ========== TRAILING STOP CONFIG ==========
DEFAULT_ATR_MULTIPLIER = 1.5
BREAKEVEN_AFTER_T1 = True
TIGHTEN_AFTER_HOURS = 2
TIGHTEN_MULTIPLIER = 1.0
MAX_HOLD_DAYS = 5

# v2.0: Regime-adaptive multipliers
REGIME_STOP_MULTIPLIERS = {
  "bull": 2.0,      # Wider stops in trending market
  "bear": 1.0,      # Tight stops in bear regime
  "neutral": 1.5,   # Default
  "volatile": 1.2,  # Slightly tight in volatile
}

# v2.0: Portfolio-level risk
MAX_PORTFOLIO_HEAT = 6.0      # Max % of portfolio at risk
MAX_CORRELATED_POSITIONS = 3  # Max positions in same sector
DRAWDOWN_MEMORY_FILE = Path("data/drawdown_memory.json")

# v2.0: Partial exit percentages
T1_EXIT_PCT = 0.33  # Sell 33% at T1
T2_EXIT_PCT = 0.50  # Sell 50% of remaining at T2
T3_EXIT_ALL = True  # Full exit at T3


@dataclass
class ManagedPosition:
  """Track a managed position with trailing stop state."""
  symbol: str
  entry_price: float
  shares: int
  side: str = "long"
  stop_price: float = 0.0
  atr: float = 0.0
  atr_multiplier: float = DEFAULT_ATR_MULTIPLIER
  target_1: float = 0.0
  target_2: float = 0.0
  target_3: float = 0.0
  t1_hit: bool = False
  t2_hit: bool = False
  t3_hit: bool = False
  shares_remaining: int = 0
  entry_time: datetime = None
  highest_price: float = 0.0
  lowest_price: float = float("inf")
  pnl_dollars: float = 0.0
  pnl_pct: float = 0.0
  status: str = "OPEN"
  # v2.0 fields
  regime: str = "neutral"
  sector: str = "unknown"
  entry_score: float = 0.0
  entry_grade: str = "C"
  rsi_at_entry: float = 50.0
  vwap_at_entry: float = 0.0
  realized_pnl: float = 0.0
  partial_exits: list = field(default_factory=list)
  stop_history: list = field(default_factory=list)
  momentum_fading: bool = False

  def __post_init__(self):
    if self.shares_remaining == 0:
      self.shares_remaining = self.shares
    if self.highest_price == 0:
      self.highest_price = self.entry_price
    if self.lowest_price == 999999.0:
      self.lowest_price = self.entry_price
    if self.entry_time is None:
      self.entry_time = datetime.now(ET)

  @property
  def hours_held(self) -> float:
    """Hours since entry."""
    if self.entry_time:
      return (datetime.now(ET) - self.entry_time).total_seconds() / 3600
    return 0.0

  @property
  def risk_dollars(self) -> float:
    """Current dollar risk = (price - stop) * shares."""
    return round((self.entry_price - self.stop_price) * self.shares_remaining, 2)

  @property
  def r_multiple(self) -> float:
    """Current R-multiple (reward relative to initial risk)."""
    initial_risk = self.entry_price - (self.entry_price - self.atr * self.atr_multiplier)
    if initial_risk <= 0:
      return 0.0
    current_gain = self.highest_price - self.entry_price
    return round(current_gain / initial_risk, 2)


class PositionManager:
  """Manage open positions with trailing stops, partial exits, and portfolio risk."""

  def __init__(self):
    self.trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
    self.data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
    self.positions: Dict[str, ManagedPosition] = {}
    self.drawdown_memory = self._load_drawdown_memory()

  def _load_drawdown_memory(self) -> Dict:
    """Load drawdown memory from disk for persistent risk tracking."""
    try:
      DRAWDOWN_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
      if DRAWDOWN_MEMORY_FILE.exists():
        with open(DRAWDOWN_MEMORY_FILE, "r") as f:
          return json.load(f)
    except Exception as e:
      logger.warning(f"Could not load drawdown memory: {e}")
    return {"peak_equity": 0, "max_drawdown_pct": 0, "consecutive_losses": 0, "last_updated": ""}

  def _save_drawdown_memory(self):
    """Persist drawdown memory to disk."""
    try:
      DRAWDOWN_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
      self.drawdown_memory["last_updated"] = datetime.now(ET).isoformat()
      with open(DRAWDOWN_MEMORY_FILE, "w") as f:
        json.dump(self.drawdown_memory, f, indent=2)
    except Exception as e:
      logger.warning(f"Could not save drawdown memory: {e}")

  def load_positions_from_alpaca(self) -> List[Dict]:
    """Load current open positions from Alpaca."""
    try:
      alpaca_positions = self.trading_client.get_all_positions()
      results = []
      for pos in alpaca_positions:
        symbol = pos.symbol
        entry = float(pos.avg_entry_price)
        qty = int(float(pos.qty))
        current = float(pos.current_price)
        pnl = float(pos.unrealized_pl)
        pnl_pct = float(pos.unrealized_plpc) * 100
        results.append({
          "symbol": symbol,
          "entry_price": entry,
          "shares": qty,
          "current_price": current,
          "pnl_dollars": round(pnl, 2),
          "pnl_pct": round(pnl_pct, 2),
          "market_value": float(pos.market_value),
        })
      return results
    except Exception as e:
      logger.error(f"Error loading Alpaca positions: {e}")
      return []

  def register_position(self, symbol: str, entry_price: float, shares: int,
                        atr: float, stop_price: float = 0,
                        t1: float = 0, t2: float = 0, t3: float = 0,
                        regime: str = "neutral", sector: str = "unknown",
                        entry_score: float = 0, entry_grade: str = "C",
                        rsi: float = 50.0, vwap: float = 0.0) -> ManagedPosition:
    """Register a new position for management with v2.0 regime awareness."""
    # v2.0: Regime-adaptive stop multiplier
    regime_mult = REGIME_STOP_MULTIPLIERS.get(regime, DEFAULT_ATR_MULTIPLIER)
    effective_mult = regime_mult

    # Adjust multiplier based on entry quality
    if entry_score >= 80:
      effective_mult *= 1.1  # Wider stop for high-conviction entries
    elif entry_score < 50:
      effective_mult *= 0.85  # Tighter stop for low-conviction

    if stop_price == 0:
      stop_price = entry_price - (atr * effective_mult)

    pos = ManagedPosition(
      symbol=symbol,
      entry_price=entry_price,
      shares=shares,
      atr=atr,
      atr_multiplier=effective_mult,
      stop_price=round(stop_price, 2),
      target_1=round(t1, 2) if t1 else round(entry_price + atr * 1.5, 2),
      target_2=round(t2, 2) if t2 else round(entry_price + atr * 2.5, 2),
      target_3=round(t3, 2) if t3 else round(entry_price + atr * 4.0, 2),
      regime=regime,
      sector=sector,
      entry_score=entry_score,
      entry_grade=entry_grade,
      rsi_at_entry=rsi,
      vwap_at_entry=vwap,
    )
    self.positions[symbol] = pos
    logger.info(f"Registered position: {symbol} {shares}@{entry_price}, "
                f"stop={pos.stop_price}, T1={pos.target_1}, T2={pos.target_2}, T3={pos.target_3}, "
                f"regime={regime}, mult={effective_mult:.2f}, score={entry_score}")
    return pos

  def _get_regime_multiplier(self, pos: ManagedPosition, current_regime: str = None) -> float:
    """Get regime-adaptive ATR multiplier for trailing stop."""
    regime = current_regime or pos.regime
    base_mult = REGIME_STOP_MULTIPLIERS.get(regime, DEFAULT_ATR_MULTIPLIER)

    # Tighten if momentum is fading
    if pos.momentum_fading:
      base_mult *= 0.75

    # Tighten based on time held
    if pos.hours_held >= TIGHTEN_AFTER_HOURS:
      base_mult = min(base_mult, TIGHTEN_MULTIPLIER)

    # Wider stops if in strong profit (let winners run)
    if pos.r_multiple >= 2.0:
      base_mult *= 1.2

    return round(base_mult, 2)

  def execute_partial_exit(self, symbol: str, qty: int, reason: str) -> Dict:
    """Execute a partial exit order through Alpaca."""
    try:
      order_request = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
      )
      order = self.trading_client.submit_order(order_request)
      logger.info(f"Partial exit executed: {symbol} SELL {qty} shares ({reason}), order_id={order.id}")
      return {
        "success": True,
        "order_id": str(order.id),
        "symbol": symbol,
        "qty": qty,
        "reason": reason,
      }
    except Exception as e:
      logger.error(f"Partial exit failed for {symbol}: {e}")
      return {"success": False, "error": str(e), "symbol": symbol, "qty": qty}

  def update_trailing_stop(self, symbol: str, current_price: float,
                           current_regime: str = None, current_rsi: float = None,
                           execute_exits: bool = False) -> Dict:
    """Update trailing stop with v2.0 regime awareness and optional auto-execution."""
    pos = self.positions.get(symbol)
    if not pos or pos.status != "OPEN":
      return {"action": "none", "reason": "No active position"}

    actions = []
    now = datetime.now(ET)

    # Update price tracking
    if current_price > pos.highest_price:
      pos.highest_price = current_price
    if current_price < pos.lowest_price:
      pos.lowest_price = current_price

    # Update P&L
    pos.pnl_dollars = round((current_price - pos.entry_price) * pos.shares_remaining, 2)
    pos.pnl_pct = round((current_price / pos.entry_price - 1) * 100, 2)

    # v2.0: Detect momentum fade via RSI divergence
    if current_rsi is not None:
      if current_price > pos.highest_price * 0.99 and current_rsi < pos.rsi_at_entry - 10:
        pos.momentum_fading = True
        actions.append({"action": "MOMENTUM_FADE_DETECTED", "rsi": current_rsi})
      elif current_rsi > pos.rsi_at_entry:
        pos.momentum_fading = False

    # v2.0: Session-aware - don't tighten in first 15 min of market
    market_open = now.replace(hour=9, minute=30, second=0)
    in_opening_range = (now - market_open).total_seconds() < 900 if now > market_open else False

    # ===== CHECK TARGETS =====
    if not pos.t1_hit and current_price >= pos.target_1:
      pos.t1_hit = True
      sell_qty = max(1, int(pos.shares_remaining * T1_EXIT_PCT))
      exit_record = {"target": "T1", "price": current_price, "qty": sell_qty, "time": now.isoformat()}
      pos.partial_exits.append(exit_record)

      if execute_exits:
        result = self.execute_partial_exit(symbol, sell_qty, "T1_HIT")
        actions.append({"action": "PARTIAL_EXIT_T1", "qty": sell_qty, "price": current_price, "executed": result.get("success", False)})
      else:
        actions.append({"action": "PARTIAL_EXIT_T1", "qty": sell_qty, "price": current_price, "executed": False})

      pos.shares_remaining -= sell_qty
      pos.realized_pnl += (current_price - pos.entry_price) * sell_qty

      if BREAKEVEN_AFTER_T1:
        pos.stop_price = pos.entry_price
        pos.stop_history.append({"type": "BREAKEVEN", "price": pos.entry_price, "time": now.isoformat()})
        actions.append({"action": "MOVE_STOP_BREAKEVEN", "new_stop": pos.entry_price})
      logger.info(f"{symbol} T1 hit at {current_price}, sold {sell_qty}, stop -> breakeven")

    if not pos.t2_hit and current_price >= pos.target_2:
      pos.t2_hit = True
      sell_qty = max(1, int(pos.shares_remaining * T2_EXIT_PCT))
      exit_record = {"target": "T2", "price": current_price, "qty": sell_qty, "time": now.isoformat()}
      pos.partial_exits.append(exit_record)

      if execute_exits:
        result = self.execute_partial_exit(symbol, sell_qty, "T2_HIT")
        actions.append({"action": "PARTIAL_EXIT_T2", "qty": sell_qty, "price": current_price, "executed": result.get("success", False)})
      else:
        actions.append({"action": "PARTIAL_EXIT_T2", "qty": sell_qty, "price": current_price, "executed": False})

      pos.shares_remaining -= sell_qty
      pos.realized_pnl += (current_price - pos.entry_price) * sell_qty

      new_stop = pos.entry_price + pos.atr
      pos.stop_price = max(pos.stop_price, new_stop)
      pos.stop_history.append({"type": "T2_TIGHTEN", "price": round(pos.stop_price, 2), "time": now.isoformat()})
      actions.append({"action": "TIGHTEN_STOP", "new_stop": round(pos.stop_price, 2)})
      logger.info(f"{symbol} T2 hit at {current_price}, sold {sell_qty}")

    if not pos.t3_hit and current_price >= pos.target_3:
      pos.t3_hit = True
      exit_record = {"target": "T3", "price": current_price, "qty": pos.shares_remaining, "time": now.isoformat()}
      pos.partial_exits.append(exit_record)

      if execute_exits:
        result = self.execute_partial_exit(symbol, pos.shares_remaining, "T3_FULL_EXIT")
        actions.append({"action": "FULL_EXIT_T3", "qty": pos.shares_remaining, "price": current_price, "executed": result.get("success", False)})
      else:
        actions.append({"action": "FULL_EXIT_T3", "qty": pos.shares_remaining, "price": current_price, "executed": False})

      pos.realized_pnl += (current_price - pos.entry_price) * pos.shares_remaining
      pos.shares_remaining = 0
      pos.status = "CLOSED_T3"
      logger.info(f"{symbol} T3 hit at {current_price}, full exit")

    # ===== ATR TRAILING STOP UPDATE =====
    if pos.status == "OPEN" and not actions:
      # v2.0: Regime-adaptive multiplier
      adaptive_mult = self._get_regime_multiplier(pos, current_regime)
      trail_stop = pos.highest_price - (pos.atr * adaptive_mult)

      # v2.0: Don't tighten during opening range
      if in_opening_range and trail_stop > pos.stop_price:
        pass  # Skip tightening in volatile open
      elif trail_stop > pos.stop_price:
        old_stop = pos.stop_price
        pos.stop_price = round(trail_stop, 2)
        pos.stop_history.append({"type": "TRAIL", "price": pos.stop_price, "time": now.isoformat()})
        actions.append({"action": "TRAIL_STOP_UP", "new_stop": pos.stop_price, "old_stop": old_stop})

    # ===== CHECK STOP HIT =====
    if pos.status == "OPEN" and current_price <= pos.stop_price:
      if execute_exits:
        result = self.execute_partial_exit(symbol, pos.shares_remaining, "STOP_HIT")
        actions.append({"action": "STOP_HIT", "qty": pos.shares_remaining, "price": current_price, "executed": result.get("success", False)})
      else:
        actions.append({"action": "STOP_HIT", "qty": pos.shares_remaining, "price": current_price, "executed": False})
      pos.realized_pnl += (current_price - pos.entry_price) * pos.shares_remaining
      pos.status = "STOPPED_OUT"
      self.drawdown_memory["consecutive_losses"] = self.drawdown_memory.get("consecutive_losses", 0) + 1
      self._save_drawdown_memory()
      logger.warning(f"{symbol} STOPPED OUT at {current_price}, stop was {pos.stop_price}")

    # v2.0: Check position aging
    if pos.status == "OPEN" and pos.hours_held >= MAX_HOLD_DAYS * 24:
      actions.append({"action": "AGING_ALERT", "hours_held": round(pos.hours_held, 1), "days": round(pos.hours_held / 24, 1)})

    return {
      "symbol": symbol,
      "current_price": current_price,
      "stop_price": pos.stop_price,
      "highest_price": pos.highest_price,
      "pnl_dollars": pos.pnl_dollars,
      "pnl_pct": pos.pnl_pct,
      "realized_pnl": round(pos.realized_pnl, 2),
      "shares_remaining": pos.shares_remaining,
      "r_multiple": pos.r_multiple,
      "hours_held": round(pos.hours_held, 1),
      "regime": pos.regime,
      "momentum_fading": pos.momentum_fading,
      "status": pos.status,
      "actions": actions,
    }

  def calculate_portfolio_heat(self) -> Dict:
    """v2.0: Calculate total portfolio risk (heat) across all positions."""
    try:
      account = self.trading_client.get_account()
      equity = float(account.equity)
      if equity <= 0:
        return {"heat_pct": 0, "positions_at_risk": 0}

      total_risk = 0.0
      sector_counts = {}
      position_risks = []

      for symbol, pos in self.positions.items():
        if pos.status != "OPEN":
          continue
        risk = pos.risk_dollars
        total_risk += abs(risk)
        sector = pos.sector
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        position_risks.append({
          "symbol": symbol,
          "risk_dollars": risk,
          "risk_pct": round(abs(risk) / equity * 100, 2),
          "sector": sector,
          "r_multiple": pos.r_multiple,
        })

      heat_pct = round(total_risk / equity * 100, 2) if equity > 0 else 0

      # Check sector concentration
      sector_warnings = []
      for sector, count in sector_counts.items():
        if count > MAX_CORRELATED_POSITIONS:
          sector_warnings.append(f"{sector}: {count} positions (max {MAX_CORRELATED_POSITIONS})")

      return {
        "heat_pct": heat_pct,
        "max_heat_pct": MAX_PORTFOLIO_HEAT,
        "heat_ok": heat_pct <= MAX_PORTFOLIO_HEAT,
        "total_risk_dollars": round(total_risk, 2),
        "equity": round(equity, 2),
        "positions_at_risk": len(position_risks),
        "position_risks": position_risks,
        "sector_warnings": sector_warnings,
        "sector_counts": sector_counts,
      }
    except Exception as e:
      logger.error(f"Portfolio heat calculation failed: {e}")
      return {"heat_pct": 0, "error": str(e)}

  def check_daily_circuit_breaker(self, account_equity: float = None) -> Dict:
    """v2.0: Enhanced circuit breaker with drawdown memory and consecutive loss tracking."""
    try:
      account = self.trading_client.get_account()
      equity = float(account.equity)
      last_equity = float(account.last_equity)
      daily_pnl = equity - last_equity
      daily_pnl_pct = (daily_pnl / last_equity) * 100 if last_equity > 0 else 0

      # Update drawdown memory
      peak = self.drawdown_memory.get("peak_equity", 0)
      if equity > peak:
        self.drawdown_memory["peak_equity"] = equity
        peak = equity

      drawdown_from_peak = ((peak - equity) / peak * 100) if peak > 0 else 0
      max_dd = self.drawdown_memory.get("max_drawdown_pct", 0)
      if drawdown_from_peak > max_dd:
        self.drawdown_memory["max_drawdown_pct"] = round(drawdown_from_peak, 2)

      consecutive_losses = self.drawdown_memory.get("consecutive_losses", 0)

      # Circuit breaker conditions
      daily_breaker = daily_pnl_pct <= -MAX_DAILY_LOSS_PCT
      drawdown_breaker = drawdown_from_peak >= MAX_DAILY_LOSS_PCT * 2  # 2x daily limit from peak
      streak_breaker = consecutive_losses >= 5  # 5 consecutive losses

      breaker_hit = daily_breaker or drawdown_breaker or streak_breaker

      # Determine severity
      if daily_breaker and drawdown_breaker:
        severity = "CRITICAL"
        action = "HALT_ALL_TRADING"
      elif daily_breaker:
        severity = "HIGH"
        action = "HALT_NEW_ENTRIES"
      elif streak_breaker:
        severity = "MEDIUM"
        action = "REDUCE_SIZE_50PCT"
      elif drawdown_breaker:
        severity = "HIGH"
        action = "HALT_NEW_ENTRIES"
      else:
        severity = "LOW"
        action = "OK"

      self._save_drawdown_memory()

      return {
        "daily_pnl": round(daily_pnl, 2),
        "daily_pnl_pct": round(daily_pnl_pct, 2),
        "max_loss_pct": MAX_DAILY_LOSS_PCT,
        "drawdown_from_peak_pct": round(drawdown_from_peak, 2),
        "max_drawdown_pct": round(self.drawdown_memory.get("max_drawdown_pct", 0), 2),
        "consecutive_losses": consecutive_losses,
        "breaker_hit": breaker_hit,
        "severity": severity,
        "action": action,
        "equity": round(equity, 2),
        "peak_equity": round(peak, 2),
      }
    except Exception as e:
      logger.error(f"Circuit breaker check failed: {e}")
      return {"breaker_hit": False, "action": "ERROR", "error": str(e)}

  def reset_consecutive_losses(self):
    """Reset consecutive loss counter (call after a winning trade)."""
    self.drawdown_memory["consecutive_losses"] = 0
    self._save_drawdown_memory()
    logger.info("Consecutive loss counter reset")

  def get_portfolio_summary(self) -> Dict:
    """Get enhanced summary of all managed positions."""
    positions = self.load_positions_from_alpaca()
    total_pnl = sum(p["pnl_dollars"] for p in positions)
    total_value = sum(p["market_value"] for p in positions)

    # v2.0: Add managed position details
    managed_details = []
    for symbol, pos in self.positions.items():
      if pos.status == "OPEN":
        managed_details.append({
          "symbol": symbol,
          "entry_price": pos.entry_price,
          "stop_price": pos.stop_price,
          "highest_price": pos.highest_price,
          "r_multiple": pos.r_multiple,
          "hours_held": round(pos.hours_held, 1),
          "pnl_dollars": pos.pnl_dollars,
          "pnl_pct": pos.pnl_pct,
          "realized_pnl": round(pos.realized_pnl, 2),
          "regime": pos.regime,
          "entry_grade": pos.entry_grade,
          "targets_hit": sum([pos.t1_hit, pos.t2_hit, pos.t3_hit]),
          "shares_remaining": pos.shares_remaining,
          "momentum_fading": pos.momentum_fading,
        })

    return {
      "open_positions": len(positions),
      "total_pnl": round(total_pnl, 2),
      "total_value": round(total_value, 2),
      "positions": positions,
      "managed_count": len([p for p in self.positions.values() if p.status == "OPEN"]),
      "managed_details": managed_details,
      "total_realized_pnl": round(sum(p.realized_pnl for p in self.positions.values()), 2),
    }

  def format_position_update(self, update: Dict) -> str:
    """Format position update for Slack with v2.0 enhanced details."""
    symbol = update.get("symbol", "???")
    pnl = update.get("pnl_dollars", 0)
    pnl_pct = update.get("pnl_pct", 0)
    stop = update.get("stop_price", 0)
    status = update.get("status", "")
    actions = update.get("actions", [])
    r_mult = update.get("r_multiple", 0)
    regime = update.get("regime", "")
    hours = update.get("hours_held", 0)

    emoji = "\U0001f7e2" if pnl >= 0 else "\U0001f534"
    lines = [f"{emoji} *{symbol}* | {status} | {regime.upper()}"]
    lines.append(f"  P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%) | R: {r_mult:.1f}R")
    lines.append(f"  Stop: ${stop:.2f} | Shares: {update.get('shares_remaining', 0)} | Hours: {hours:.1f}")

    if update.get("momentum_fading"):
      lines.append("  \u26a0\ufe0f Momentum fading - stop may tighten")

    for action in actions:
      act = action.get("action", "")
      if "EXIT" in act or "STOP_HIT" in act:
        executed = "\u2705" if action.get("executed") else "\u23f3"
        lines.append(f"  >> {executed} {act}: {action.get('qty', 0)} shares @ ${action.get('price', 0):.2f}")
      elif "STOP" in act:
        lines.append(f"  >> {act}: new stop ${action.get('new_stop', 0):.2f}")
      elif "MOMENTUM" in act:
        lines.append(f"  >> {act}: RSI={action.get('rsi', 0):.1f}")
      elif "AGING" in act:
        lines.append(f"  >> \u23f0 Position aging: {action.get('days', 0):.1f} days held")

    return "\n".join(lines)

  def format_circuit_breaker_alert(self, breaker: Dict) -> str:
    """Format circuit breaker alert for Slack."""
    severity = breaker.get("severity", "LOW")
    emojis = {"CRITICAL": "\U0001f6a8", "HIGH": "\u26a0\ufe0f", "MEDIUM": "\u26a1", "LOW": "\u2705"}
    emoji = emojis.get(severity, "")

    lines = [f"{emoji} *CIRCUIT BREAKER: {severity}*"]
    lines.append(f"  Daily P&L: ${breaker.get('daily_pnl', 0):+.2f} ({breaker.get('daily_pnl_pct', 0):+.1f}%)")
    lines.append(f"  Drawdown from peak: {breaker.get('drawdown_from_peak_pct', 0):.1f}%")
    lines.append(f"  Consecutive losses: {breaker.get('consecutive_losses', 0)}")
    lines.append(f"  Action: {breaker.get('action', 'UNKNOWN')}")
    lines.append(f"  Equity: ${breaker.get('equity', 0):,.2f} | Peak: ${breaker.get('peak_equity', 0):,.2f}")
    return "\n".join(lines)


# ========== MODULE-LEVEL CONVENIENCE ==========
def check_all_positions() -> List[Dict]:
  """Check and update all managed positions."""
  manager = PositionManager()
  positions = manager.load_positions_from_alpaca()
  return positions


def get_portfolio_summary() -> Dict:
  """Get portfolio summary."""
  manager = PositionManager()
  return manager.get_portfolio_summary()


def check_circuit_breaker() -> Dict:
  """Check daily circuit breaker status."""
  manager = PositionManager()
  return manager.check_daily_circuit_breaker()


def get_portfolio_heat() -> Dict:
  """Get portfolio heat (total risk exposure)."""
  manager = PositionManager()
  return manager.calculate_portfolio_heat()
