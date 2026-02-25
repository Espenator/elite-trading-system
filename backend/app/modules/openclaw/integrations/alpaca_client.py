#!/usr/bin/env python3
"""
Alpaca Trading Client for OpenClaw v2.1
Full bracket order support with entry + stop-loss + take-profit.
Supports: market, limit, stop, stop-limit, bracket (OTO/OCO) orders.
Integrates with position_sizer output for automated trade placement.
Added: LLM-powered pre-trade risk check via hybrid Ollama/Perplexity.
"""
import os
import logging
from typing import Dict, Optional, List
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

try:
    from llm_client import llm_router
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)


class AlpacaClient:
    """
    Alpaca v2 trading client with bracket order support.
    All orders go to paper trading by default.
    Includes optional LLM-powered pre-trade risk assessment.
    """

    def __init__(self):
        self.client = TradingClient(
            ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True
        )
        self.account = None
        logger.info("AlpacaClient initialized (paper=True)")

    # ==================== ACCOUNT ====================

    def get_account(self):
        try:
            self.account = self.client.get_account()
            return self.account
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return None

    def get_positions(self):
        try:
            return self.client.get_all_positions()
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def get_buying_power(self):
        account = self.get_account()
        return float(account.buying_power) if account else 0

    def get_equity(self):
        account = self.get_account()
        return float(account.equity) if account else 0

    def get_open_orders(self):
        try:
            return self.client.get_orders()
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []

    # ==================== SIMPLE ORDERS ====================

    def place_market_order(self, symbol, qty, side="buy"):
        """Place a simple market order."""
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY,
            )
            order = self.client.submit_order(order_data)
            logger.info(f"Market order: {side.upper()} {qty} {symbol}")
            return {"success": True, "order": order, "order_id": str(order.id)}
        except Exception as e:
            logger.error(f"Market order failed: {e}")
            return {"success": False, "error": str(e)}

    def place_limit_order(self, symbol, qty, limit_price, side="buy"):
        """Place a limit order."""
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                limit_price=round(limit_price, 2),
                time_in_force=TimeInForce.DAY,
            )
            order = self.client.submit_order(order_data)
            logger.info(f"Limit order: {side.upper()} {qty} {symbol} @ ${limit_price:.2f}")
            return {"success": True, "order": order, "order_id": str(order.id)}
        except Exception as e:
            logger.error(f"Limit order failed: {e}")
            return {"success": False, "error": str(e)}

    def place_stop_order(self, symbol, qty, stop_price, side="sell"):
        """Place a stop order (typically for stop-loss)."""
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            order_data = StopOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                stop_price=round(stop_price, 2),
                time_in_force=TimeInForce.DAY,
            )
            order = self.client.submit_order(order_data)
            logger.info(f"Stop order: {side.upper()} {qty} {symbol} stop @ ${stop_price:.2f}")
            return {"success": True, "order": order, "order_id": str(order.id)}
        except Exception as e:
            logger.error(f"Stop order failed: {e}")
            return {"success": False, "error": str(e)}

    # ==================== BRACKET ORDERS ====================

    def place_bracket_order(
        self, symbol, qty, side="buy",
        limit_price=None, stop_loss_price=None, take_profit_price=None
    ):
        """
        Place a bracket order: entry + stop-loss + take-profit.
        Parent: market or limit buy
        Child 1: stop-loss sell (OCO)
        Child 2: take-profit limit sell (OCO)
        """
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

            tp_request = None
            if take_profit_price:
                tp_request = TakeProfitRequest(
                    limit_price=round(take_profit_price, 2)
                )

            sl_request = None
            if stop_loss_price:
                sl_request = StopLossRequest(
                    stop_price=round(stop_loss_price, 2)
                )

            if limit_price:
                order_data = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    limit_price=round(limit_price, 2),
                    time_in_force=TimeInForce.DAY,
                    order_class=OrderClass.BRACKET,
                    take_profit=tp_request,
                    stop_loss=sl_request,
                )
            else:
                order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=TimeInForce.DAY,
                    order_class=OrderClass.BRACKET,
                    take_profit=tp_request,
                    stop_loss=sl_request,
                )

            order = self.client.submit_order(order_data)
            logger.info(
                f"Bracket order: {side.upper()} {qty} {symbol} | "
                f"stop=${stop_loss_price} | tp=${take_profit_price}"
            )
            return {
                "success": True,
                "order": order,
                "order_id": str(order.id),
                "type": "bracket",
                "symbol": symbol,
                "qty": qty,
                "stop_loss": stop_loss_price,
                "take_profit": take_profit_price,
            }
        except Exception as e:
            logger.error(f"Bracket order failed for {symbol}: {e}")
            return {"success": False, "error": str(e), "symbol": symbol}

    # ==================== LLM RISK CHECK ====================

    def llm_risk_check(self, ticker, sizing, regime_state="UNKNOWN"):
        """
        Use LLM to assess trade risk before execution.
        Returns dict with 'approved' bool, 'confidence' (1-10), 'reason' string.
        Uses local Ollama for speed, falls back to Perplexity.
        """
        if not LLM_AVAILABLE:
            logger.debug("LLM not available, skipping risk check")
            return {"approved": True, "confidence": 5, "reason": "LLM unavailable - auto-approved"}

        try:
            shares = sizing.get('shares', 0)
            stop_price = sizing.get('stop_price', 0)
            entry_price = sizing.get('entry_price', 0)
            target = sizing.get('target_2', 0)
            risk_pct = sizing.get('risk_pct', 0)
            position_pct = sizing.get('position_pct', 0)

            # Get current portfolio context
            equity = self.get_equity()
            positions = self.get_positions()
            num_positions = len(positions)
            existing_symbols = [p.symbol for p in positions]

            prompt = f"""Pre-trade risk assessment for {ticker}:
- Shares: {shares}, Entry: ${entry_price:.2f}, Stop: ${stop_price:.2f}, Target: ${target:.2f}
- Risk per trade: {risk_pct:.1f}% of portfolio
- Position size: {position_pct:.1f}% of equity
- Market regime: {regime_state}
- Portfolio: ${equity:.0f} equity, {num_positions} open positions
- Existing positions: {', '.join(existing_symbols[:10]) if existing_symbols else 'none'}

Evaluate:
1. Is the risk/reward ratio acceptable? (minimum 1.5:1)
2. Is position sizing appropriate for the regime?
3. Any concentration risk with existing positions?
4. Overall confidence (1-10)?

Respond with JSON: {{"approved": true/false, "confidence": 1-10, "reason": "brief explanation"}}
Only JSON, no other text."""

            response = llm_router.chat(
                prompt,
                task_type="analysis",
                temperature=0.1
            )

            # Parse JSON from response
            import json
            # Try to extract JSON from response
            response_clean = response.strip()
            if response_clean.startswith("```"):
                response_clean = response_clean.split("```")[1]
                if response_clean.startswith("json"):
                    response_clean = response_clean[4:]
                response_clean = response_clean.strip()

            result = json.loads(response_clean)
            result['approved'] = bool(result.get('approved', True))
            result['confidence'] = int(result.get('confidence', 5))
            result['reason'] = str(result.get('reason', 'No reason given'))

            logger.info(
                f"LLM risk check {ticker}: "
                f"{'APPROVED' if result['approved'] else 'REJECTED'} "
                f"(confidence: {result['confidence']}/10) - {result['reason']}"
            )
            return result

        except Exception as e:
            logger.warning(f"LLM risk check failed for {ticker}: {e}")
            # On failure, approve by default (don't block trades due to LLM issues)
            return {"approved": True, "confidence": 5, "reason": f"Risk check error: {str(e)}"}

    # ==================== PIPELINE INTEGRATION ====================

    def execute_trade_from_sizing(self, ticker, sizing, use_bracket=True, regime_state="UNKNOWN", use_llm_check=True):
        """
        Execute a trade using position_sizer output.
        Optionally runs LLM risk check before placing order.
        Args:
            ticker: Stock symbol
            sizing: Dict from position_sizer.calculate()
            use_bracket: If True, place bracket order with stop+target
            regime_state: Current market regime for LLM context
            use_llm_check: If True, run LLM risk assessment first
        """
        if not sizing or not sizing.get('can_trade'):
            reason = sizing.get('reason', 'unknown') if sizing else 'no_sizing'
            logger.info(f"Skip {ticker}: {reason}")
            return {"success": False, "reason": reason, "symbol": ticker}

        shares = sizing['shares']
        stop_price = sizing.get('stop_price', 0)
        take_profit = sizing.get('target_2', 0)

        if shares <= 0:
            return {"success": False, "reason": "zero_shares", "symbol": ticker}

        # LLM pre-trade risk check
        llm_result = None
        if use_llm_check and LLM_AVAILABLE:
            llm_result = self.llm_risk_check(ticker, sizing, regime_state)
            if not llm_result.get('approved', True):
                logger.info(f"LLM REJECTED trade for {ticker}: {llm_result.get('reason')}")
                return {
                    "success": False,
                    "reason": "llm_risk_rejected",
                    "symbol": ticker,
                    "llm_assessment": llm_result
                }

        # Place the order
        if use_bracket and stop_price > 0 and take_profit > 0:
            result = self.place_bracket_order(
                symbol=ticker,
                qty=shares,
                side="buy",
                stop_loss_price=stop_price,
                take_profit_price=take_profit,
            )
        else:
            result = self.place_market_order(
                symbol=ticker, qty=shares, side="buy",
            )

        # Attach LLM assessment to result
        if llm_result:
            result['llm_assessment'] = llm_result

        return result

    def execute_watchlist_trades(self, watchlist, max_trades=3, regime_state="UNKNOWN"):
        """
        Execute trades for top-scored watchlist items.
        Only places orders for items with position_size data.
        Uses LLM risk check for each trade.
        """
        results = []
        trades_placed = 0

        for item in watchlist:
            if trades_placed >= max_trades:
                break

            ticker = item.get('ticker')
            sizing = item.get('position_size')
            score = item.get('composite_score', 0)

            if score < 70 or not sizing or not sizing.get('can_trade'):
                continue

            result = self.execute_trade_from_sizing(
                ticker, sizing,
                regime_state=regime_state,
                use_llm_check=True
            )
            results.append(result)

            if result.get('success'):
                trades_placed += 1
                logger.info(
                    f"Trade {trades_placed}/{max_trades}: "
                    f"{ticker} {sizing['shares']} shares "
                    f"stop=${sizing['stop_price']} tp=${sizing.get('target_2')}"
                )
            elif result.get('reason') == 'llm_risk_rejected':
                logger.info(f"LLM rejected {ticker}: {result.get('llm_assessment', {}).get('reason', '?')}")

        logger.info(f"Executed {trades_placed} trades from watchlist")
        return results

    # ==================== POSITION MANAGEMENT ====================

    def close_position(self, symbol):
        try:
            self.client.close_position(symbol)
            logger.info(f"Closed position: {symbol}")
            return {"success": True, "message": f"Closed position {symbol}"}
        except Exception as e:
            logger.error(f"Close position failed: {e}")
            return {"success": False, "error": str(e)}

    def close_all_positions(self):
        try:
            self.client.close_all_positions(cancel_orders=True)
            logger.info("Closed all positions")
            return {"success": True, "message": "Closed all positions"}
        except Exception as e:
            logger.error(f"Close all failed: {e}")
            return {"success": False, "error": str(e)}

    def cancel_all_orders(self):
        try:
            self.client.cancel_orders()
            logger.info("Cancelled all open orders")
            return {"success": True, "message": "Cancelled all orders"}
        except Exception as e:
            logger.error(f"Cancel orders failed: {e}")
            return {"success": False, "error": str(e)}

    # ==================== STATUS / SUMMARY ====================

    def get_portfolio_summary(self):
        """Get summary of account + positions for logging."""
        try:
            account = self.get_account()
            positions = self.get_positions()
            if not account:
                return {"error": "Could not get account"}

            return {
                "equity": float(account.equity),
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
                "positions_count": len(positions),
                "positions": [
                    {
                        "symbol": p.symbol,
                        "qty": float(p.qty),
                        "market_value": float(p.market_value),
                        "unrealized_pl": float(p.unrealized_pl),
                        "unrealized_plpc": float(p.unrealized_plpc),
                    }
                    for p in positions
                ],
            }
        except Exception as e:
            logger.error(f"Portfolio summary failed: {e}")
            return {"error": str(e)}


# Legacy compatibility
def place_order(symbol, qty, side="buy", order_type="market"):
    """Legacy wrapper for backwards compatibility."""
    client = AlpacaClient()
    if order_type == "market":
        return client.place_market_order(symbol, qty, side)
    return client.place_market_order(symbol, qty, side)


# Module-level instance
alpaca_client = AlpacaClient()
