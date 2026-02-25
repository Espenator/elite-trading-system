#!/usr/bin/env python3
"""
agent_short_basket_compiler.py - Hunter-Killer Swarm: Execution Formatter
OpenClaw Hierarchical Synthesis Architecture - Tier 3

Takes the top 3 weakest tickers from agent_relative_weakness,
checks margin/borrow availability via Alpaca, and formats precise
short-trade execution payloads with entry zones and stop losses.

Publishes to: Topic.EXECUTION_ORDERS
Subscribes to: Topic.SCORED_SIGNALS
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from streaming_engine import (
    Blackboard, BlackboardMessage, Topic, get_blackboard,
)

try:
    from alpaca_client import get_account, get_asset, get_positions
except ImportError:
    get_account = None
    get_asset = None
    get_positions = None

try:
    from config import DEFAULT_RISK_PCT, MAX_DAILY_LOSS_PCT
except ImportError:
    DEFAULT_RISK_PCT = 1.5
    MAX_DAILY_LOSS_PCT = 2.0

logger = logging.getLogger(__name__)

MAX_SHORT_BASKET_SIZE = 3
STOP_LOSS_ATR_MULTIPLE = 1.5
DEFAULT_STOP_PCT = 0.02  # 2% above entry if no ATR available
MAX_BORROW_FEE_PCT = 25.0  # Skip hard-to-borrow stocks


class ShortBasketCompilerAgent:
    """
    Execution formatter: compiles the final short basket with
    precise entry zones, stop losses, and position sizing.
    """

    AGENT_ID = "short_basket_compiler"

    def __init__(self, blackboard: Blackboard):
        self.bb = blackboard
        self._last_basket: List[Dict] = []
        self._stats = {
            "baskets_compiled": 0,
            "tickers_checked": 0,
            "tickers_rejected": 0,
            "orders_formatted": 0,
        }
        logger.info("[ShortBasketCompiler] Initialized - Execution formatter ready")

    # ----------------------------------------------------------
    # Alpaca Margin / Borrow Checks
    # ----------------------------------------------------------
    async def _check_shortable(self, ticker: str) -> Dict[str, Any]:
        """
        Check if a ticker is shortable via Alpaca.
        Returns borrow status, fee estimate, and tradability.
        """
        result = {
            "ticker": ticker,
            "shortable": False,
            "easy_to_borrow": False,
            "tradable": False,
            "borrow_fee_est": 0.0,
            "reason": "",
        }

        if not get_asset:
            # Simulate if alpaca_client not available
            result["shortable"] = True
            result["easy_to_borrow"] = True
            result["tradable"] = True
            result["borrow_fee_est"] = 0.5
            result["reason"] = "simulated_check"
            return result

        try:
            asset = get_asset(ticker)
            if asset is None:
                result["reason"] = "asset_not_found"
                return result

            tradable = getattr(asset, "tradable", False)
            shortable = getattr(asset, "shortable", False)
            etb = getattr(asset, "easy_to_borrow", False)

            result["tradable"] = bool(tradable)
            result["shortable"] = bool(shortable)
            result["easy_to_borrow"] = bool(etb)

            # Estimate borrow fee (ETB stocks are cheap, HTB are expensive)
            if etb:
                result["borrow_fee_est"] = 0.5
            elif shortable:
                result["borrow_fee_est"] = 8.0  # Conservative HTB estimate
            else:
                result["borrow_fee_est"] = 999.0

            if not tradable:
                result["reason"] = "not_tradable"
            elif not shortable:
                result["reason"] = "not_shortable"
            elif result["borrow_fee_est"] > MAX_BORROW_FEE_PCT:
                result["reason"] = f"borrow_fee_too_high_{result['borrow_fee_est']}pct"
                result["shortable"] = False
            else:
                result["reason"] = "passed"

        except Exception as e:
            logger.error(f"[ShortBasketCompiler] Asset check error for {ticker}: {e}")
            result["reason"] = f"api_error: {e}"

        return result

    # ----------------------------------------------------------
    # Entry / Stop / Size Calculation
    # ----------------------------------------------------------
    def _compute_trade_levels(self, candidate: Dict) -> Dict[str, Any]:
        """
        Compute precise entry zone, stop loss, and targets
        for a short trade based on candidate data.
        """
        price = float(candidate.get("price", 0))
        sma50 = float(candidate.get("sma50", 0))

        if price <= 0:
            return {}

        # Entry zone: slight fade below current price
        entry_zone = round(price * 0.998, 2)

        # Stop loss: above the 50 SMA or 2% above entry
        if sma50 > 0 and sma50 > price:
            stop_loss = round(sma50 * 1.005, 2)  # Just above 50 SMA
        else:
            stop_loss = round(entry_zone * (1 + DEFAULT_STOP_PCT), 2)

        # Risk per share
        risk_per_share = stop_loss - entry_zone
        if risk_per_share <= 0:
            risk_per_share = entry_zone * DEFAULT_STOP_PCT

        # Targets: 1.5:1 and 3:1 risk-reward
        target_1 = round(entry_zone - (risk_per_share * 1.5), 2)
        target_2 = round(entry_zone - (risk_per_share * 3.0), 2)

        # Risk-reward ratio
        rr_ratio = round((entry_zone - target_2) / risk_per_share, 1) if risk_per_share > 0 else 0

        return {
            "entry_zone": entry_zone,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "risk_per_share": round(risk_per_share, 2),
            "risk_reward": rr_ratio,
        }

    def _compute_position_size(self, trade_levels: Dict, account_equity: float) -> int:
        """Calculate shares to short based on risk budget."""
        risk_budget = account_equity * (DEFAULT_RISK_PCT / 100.0)
        risk_per_share = trade_levels.get("risk_per_share", 0)

        if risk_per_share <= 0:
            return 0

        shares = int(risk_budget / risk_per_share)
        # Cap at 5% of account equity per position
        max_shares = int((account_equity * 0.05) / trade_levels.get("entry_zone", 1))
        return min(shares, max_shares, 500)  # Hard cap at 500 shares

    # ----------------------------------------------------------
    # Basket Compilation
    # ----------------------------------------------------------
    async def _compile_basket(self, candidates: List[Dict]) -> List[Dict]:
        """
        Take top candidates, validate shortability, compute levels,
        and produce the final execution basket.
        """
        basket = []
        account_equity = 100_000.0  # Default; overridden if Alpaca available

        if get_account:
            try:
                acct = get_account()
                account_equity = float(getattr(acct, "equity", 100_000))
            except Exception as e:
                logger.warning(f"[ShortBasketCompiler] Account fetch error: {e}")

        for candidate in candidates[:MAX_SHORT_BASKET_SIZE + 2]:  # Check extras in case some fail
            if len(basket) >= MAX_SHORT_BASKET_SIZE:
                break

            ticker = candidate.get("ticker", "")
            if not ticker:
                continue

            self._stats["tickers_checked"] += 1

            # Check shortability
            borrow_check = await self._check_shortable(ticker)
            if not borrow_check["shortable"]:
                self._stats["tickers_rejected"] += 1
                logger.info(
                    f"[ShortBasketCompiler] SKIP {ticker}: "
                    f"{borrow_check['reason']}"
                )
                continue

            # Compute trade levels
            levels = self._compute_trade_levels(candidate)
            if not levels:
                continue

            # Compute position size
            shares = self._compute_position_size(levels, account_equity)
            if shares <= 0:
                continue

            order = {
                "ticker": ticker,
                "action": "short",
                "entry_zone": levels["entry_zone"],
                "stop_loss": levels["stop_loss"],
                "target_1": levels["target_1"],
                "target_2": levels["target_2"],
                "risk_per_share": levels["risk_per_share"],
                "risk_reward": levels["risk_reward"],
                "shares": shares,
                "notional_value": round(levels["entry_zone"] * shares, 2),
                "weakness_score": candidate.get("weakness_score", 0),
                "sector": candidate.get("sector", ""),
                "borrow_status": borrow_check["reason"],
                "borrow_fee_est": borrow_check["borrow_fee_est"],
                "compiled_at": datetime.now().isoformat(),
            }

            basket.append(order)
            self._stats["orders_formatted"] += 1

        return basket

    # ----------------------------------------------------------
    # Publication
    # ----------------------------------------------------------
    async def _publish_basket(self, basket: List[Dict]) -> None:
        """Publish the compiled short basket to EXECUTION_ORDERS."""
        self._last_basket = basket

        payload = {
            "signal_type": "short_basket",
            "basket": basket,
            "basket_size": len(basket),
            "total_notional": sum(o["notional_value"] for o in basket),
            "compiled_at": datetime.now().isoformat(),
        }

        await self.bb.publish(BlackboardMessage(
            topic=Topic.EXECUTION_ORDERS,
            payload=payload,
            source_agent=self.AGENT_ID,
            priority=1,  # Highest - these are actionable
            ttl_seconds=300,
        ))

        for order in basket:
            logger.info(
                f"[ShortBasketCompiler] ORDER: {order['ticker']} "
                f"SHORT {order['shares']} shares @ {order['entry_zone']} "
                f"| Stop: {order['stop_loss']} | RR: {order['risk_reward']}:1"
            )

    # ----------------------------------------------------------
    # Main Event Loop
    # ----------------------------------------------------------
    async def run(self) -> None:
        """Listen for weakness scan results and compile short baskets."""
        signals_q = await self.bb.subscribe(
            Topic.SCORED_SIGNALS, self.AGENT_ID
        )
        logger.info(
            "[ShortBasketCompiler] Subscribed to scored_signals. "
            "Waiting for weakness candidates..."
        )

        while True:
            try:
                msg = await asyncio.wait_for(signals_q.get(), timeout=10.0)

                if not isinstance(msg, BlackboardMessage) or msg.is_expired():
                    continue

                payload = msg.payload
                signal_type = payload.get("signal_type", "")

                # Only process weakness scan results
                if signal_type != "relative_weakness_scan":
                    continue

                candidates = payload.get("candidates", [])
                if not candidates:
                    continue

                logger.info(
                    f"[ShortBasketCompiler] Received {len(candidates)} "
                    f"weakness candidates. Compiling basket..."
                )

                basket = await self._compile_basket(candidates)

                if basket:
                    self._stats["baskets_compiled"] += 1
                    await self._publish_basket(basket)
                else:
                    logger.warning(
                        "[ShortBasketCompiler] No shortable candidates passed checks"
                    )

            except asyncio.TimeoutError:
                await self.bb.heartbeat(self.AGENT_ID)
            except asyncio.CancelledError:
                logger.info("[ShortBasketCompiler] Shutting down")
                break
            except Exception as e:
                logger.error(f"[ShortBasketCompiler] Loop error: {e}")
                await asyncio.sleep(5)

    def get_status(self) -> Dict:
        return {
            "agent_id": self.AGENT_ID,
            "last_basket": self._last_basket,
            "stats": dict(self._stats),
        }
