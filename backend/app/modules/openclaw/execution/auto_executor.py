#!/usr/bin/env python3
"""
Auto Executor for OpenClaw v2.0 - Tier 3 Execution Agent

Consumes SIGNAL_READY events from streaming_engine.py and the Blackboard,
places bracket orders via alpaca_client.py, and feeds outcomes back to memory.

Swarm Integration:
- Subscribes to Topic.EXECUTION_ORDERS from the Blackboard
- Publishes Topic.TRADE_OUTCOMES after each execution
- Integrates with memory.py for the self-learning flywheel
- Uses ET timezone for market hours validation
- Robust imports with try/except fallbacks

Fixes from Issue #1:
- Fixed import: log_trade instead of PerformanceTracker class
- Added memory.py integration (record_signal / record_outcome)
- Market hours now use ET timezone via ZoneInfo
- Try/except around all critical imports
"""
import asyncio
import json
import logging
import os
from datetime import datetime, time as dt_time
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

# Robust imports with graceful fallbacks
try:
    from alpaca_client import AlpacaClient
except ImportError:
    AlpacaClient = None

try:
    from position_sizer import calculate_position_size
except ImportError:
    calculate_position_size = None

try:
    from fom_expected_moves import get_expected_move
except ImportError:
    get_expected_move = None

try:
    from performance_tracker import log_trade
except ImportError:
    log_trade = None

try:
    from memory import trade_memory
except ImportError:
    trade_memory = None

try:
    from streaming_engine import get_blackboard, BlackboardMessage, Topic
except ImportError:
    get_blackboard = None
    BlackboardMessage = None
    Topic = None

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")

# ========== SETTINGS ==========
MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "10"))
MIN_SCORE_TO_EXECUTE = float(os.getenv("MIN_SCORE_TO_EXECUTE", "75"))
EXECUTION_TIMEOUT_SECS = int(os.getenv("EXECUTION_TIMEOUT_SECS", "10"))
ATR_STOP_MULTIPLIER = float(os.getenv("ATR_STOP_MULTIPLIER", "1.5"))
RR_RATIO = float(os.getenv("RR_RATIO", "2.0"))
MAX_RETRY_PRICE_OFFSET = float(os.getenv("MAX_RETRY_PRICE_OFFSET", "0.3"))
ACCOUNT_RISK_PCT = float(os.getenv("ACCOUNT_RISK_PCT", "2.0"))  # 2% risk per trade
SLACK_TRADE_DESK_CHANNEL = os.getenv("OC_TRADE_DESK_CHANNEL", "C0AF9RW7W94")

# ========== EXECUTION LOG ==========
_execution_log_path = "data/execution_log_{}.json".format(
    datetime.now(ET).strftime("%Y%m%d")
)
_daily_trade_count = 0
_daily_reset_date = datetime.now(ET).date()


def _reset_daily_counter():
    global _daily_trade_count, _daily_reset_date
    today = datetime.now(ET).date()
    if today != _daily_reset_date:
        _daily_trade_count = 0
        _daily_reset_date = today


def _log_execution(entry: Dict):
    """Append execution record to daily JSON log."""
    os.makedirs("data", exist_ok=True)
    records = []
    if os.path.exists(_execution_log_path):
        try:
            with open(_execution_log_path) as f:
                records = json.load(f)
        except Exception:
            records = []
    records.append(entry)
    try:
        with open(_execution_log_path, "w") as f:
            json.dump(records, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"[AutoExec] Failed to write execution log: {e}")


def calculate_em_based_targets(entry_price: float, expected_move_pct: float, side: str = "buy") -> tuple:
    """Calculate take-profit targets based on FOM expected move."""
    if not expected_move_pct or expected_move_pct <= 0:
        return None, None
    em_dollars = entry_price * (expected_move_pct / 100.0)
    direction = 1 if side.lower() == "buy" else -1
    target1 = round(entry_price + direction * em_dollars * 0.5, 2)
    target2 = round(entry_price + direction * em_dollars, 2)
    return target1, target2


def calculate_risk_based_size(equity: float, entry_price: float,
                              stop_price: float, risk_pct: float = None) -> int:
    """
    Calculate position size based on account risk percentage.
    Default: 2% of equity risked per trade.
    """
    risk_pct = risk_pct or ACCOUNT_RISK_PCT
    risk_dollars = equity * (risk_pct / 100.0)
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share <= 0:
        return 0
    shares = int(risk_dollars / risk_per_share)
    # Cap at 10% of equity in single position
    max_shares = int((equity * 0.10) / entry_price) if entry_price > 0 else 0
    return min(shares, max_shares)


def build_bracket_order(ticker: str, qty: int, entry: float,
                        stop: float, target: float, side: str = "buy") -> Dict:
    """Construct bracket order parameters."""
    return {
        "symbol": ticker,
        "qty": qty,
        "side": side,
        "limit_price": round(entry, 2),
        "stop_loss_price": round(stop, 2),
        "take_profit_price": round(target, 2),
    }


def execute_signal(signal: Dict, alpaca: 'AlpacaClient',
                   risk_check_fn=None, slack_fn=None) -> Dict:
    """
    Execute a single SIGNAL_READY event.
    Runs risk check, sizes position, places bracket order, logs result,
    and records to memory for the self-learning flywheel.
    """
    global _daily_trade_count
    _reset_daily_counter()

    ticker = signal.get("ticker", "")
    score = float(signal.get("score", 0))
    entry_price = float(signal.get("entry_price", 0))
    atr = float(signal.get("atr", entry_price * 0.02))
    regime = signal.get("regime", "YELLOW")
    trigger = signal.get("trigger", "unknown")
    side = signal.get("side", "buy").lower()
    # Normalize metadata for memory/performance tracking
    source = (signal.get("source") or signal.get("session") or "auto_executor").lower()
    setup = (signal.get("setup") or signal.get("setup_type") or trigger or "unknown").lower()
    timestamp = datetime.now(ET).isoformat()

    result = {
        "timestamp": timestamp,
        "ticker": ticker,
        "signal_score": score,
        "trigger": trigger,
        "action": "skipped",
        "rejection_reason": None,
        "regime": regime,
    }

    # Guard: minimum score
    if score < MIN_SCORE_TO_EXECUTE:
        result["rejection_reason"] = f"score {score:.1f} < min {MIN_SCORE_TO_EXECUTE}"
        _log_execution(result)
        return result

    # Guard: daily trade limit
    if _daily_trade_count >= MAX_DAILY_TRADES:
        result["rejection_reason"] = "daily_trade_limit_reached"
        _log_execution(result)
        return result

    # Guard: market hours (9:30 AM - 4:00 PM ET)
    now_et = datetime.now(ET)
    market_open = dt_time(9, 30)
    market_close = dt_time(16, 0)
    if not (market_open <= now_et.time() <= market_close):
        result["rejection_reason"] = "outside_market_hours"
        _log_execution(result)
        return result

    # Calculate stop and target
    stop_price = round(entry_price - ATR_STOP_MULTIPLIER * atr, 2) if side == "buy" else round(entry_price + ATR_STOP_MULTIPLIER * atr, 2)
    stop_distance = abs(entry_price - stop_price)

    # FOM-based targets
    em_pct = 0
    if get_expected_move:
        try:
            em_data = get_expected_move(ticker)
            em_pct = em_data.get("em_pct", 0) if em_data else 0
        except Exception:
            em_pct = 0
    target1, target2 = calculate_em_based_targets(entry_price, em_pct, side)
    if target2 is None:
                target2 = round(entry_price + RR_RATIO * stop_distance, 2) if side == "buy" else round(entry_price - RR_RATIO * stop_distance, 2)

    # Risk governor check
    if risk_check_fn:
        try:
            approved, reason = risk_check_fn(ticker, entry_price, stop_price, regime)
            if not approved:
                result["action"] = "rejected"
                result["rejection_reason"] = reason
                _log_execution(result)
                msg = f":octagonal_sign: REJECTED: {ticker} | {reason} | Score: {score:.0f}"
                logger.warning(f"[AutoExec] {msg}")
                if slack_fn:
                    slack_fn(SLACK_TRADE_DESK_CHANNEL, msg)
                return result
        except Exception as e:
            logger.error(f"[AutoExec] Risk check error: {e}")

    # Position sizing - use risk-based sizing with 2% account risk
    qty = 0
    try:
        if alpaca:
            equity = alpaca.get_equity()
            # Try module position_sizer first, fallback to risk-based
            if calculate_position_size:
                sizing = calculate_position_size(
                    ticker=ticker,
                    entry_price=entry_price,
                    stop_price=stop_price,
                    account_equity=equity,
                    regime=regime,
                    score=score,
                )
                qty = sizing.get("shares", 0)
            else:
                qty = calculate_risk_based_size(equity, entry_price, stop_price)
    except Exception as e:
        logger.error(f"[AutoExec] Position sizing failed for {ticker}: {e}")
        result["rejection_reason"] = f"sizing_error: {e}"
        _log_execution(result)
        return result

    if qty <= 0:
        result["rejection_reason"] = "zero_shares_sized"
        _log_execution(result)
        return result

        # Memory flywheel: record the signal using (ticker, source, setup)
    if trade_memory:
        try:
            trade_memory.record_signal(
                                ticker, source, setup,
                                score=int(score), regime=regime,
            )
        except Exception as e:
            logger.warning(f"[AutoExec] Memory record_signal failed: {e}")

    # Place bracket order
    try:
        order_result = alpaca.place_bracket_order(
            symbol=ticker,
            qty=qty,
                            side=side,
            limit_price=entry_price,
            stop_loss_price=stop_price,
            take_profit_price=target2,
        )
    except Exception as e:
        logger.error(f"[AutoExec] Order placement failed for {ticker}: {e}")
        result["rejection_reason"] = f"order_error: {e}"
        _log_execution(result)
        return result

    if order_result.get("success"):
        _daily_trade_count += 1
        result["action"] = "executed"
        result["qty"] = qty
        result["entry"] = entry_price
        result["stop"] = stop_price
        result["target1"] = target1
        result["target2"] = target2
        result["order_id"] = order_result.get("order_id")
        result["em_pct"] = em_pct

        msg = (
            f":rocket: EXECUTING: *{ticker}* | {qty} shares | "
            f"Entry: ${entry_price:.2f} | Stop: ${stop_price:.2f} | "
            f"T1: ${target1 or 0:.2f} | T2: ${target2:.2f} | "
            f"Score: {score:.0f} | Trigger: {trigger} | EM: {em_pct:.1f}%"
        )
        logger.info(f"[AutoExec] {msg}")
        if slack_fn:
            slack_fn(SLACK_TRADE_DESK_CHANNEL, msg)

                # Performance tracker: include source/setup so memory.sync_from_journal() can backfill outcomes cleanly
        if log_trade:
            try:
                log_trade({
                    "symbol": ticker,
                    "side": side,
                    "entry_price": entry_price,
                    "shares": qty,
                    "regime": regime,
                    "entry_score": score,
                    "source": source,
                    "setup": setup,
                    "trigger": trigger,
                    "order_id": order_result.get("order_id"),
                    "session": signal.get("session", "streaming_engine"),
                })
            except Exception as e:
                logger.warning(f"[AutoExec] Performance tracker log failed: {e}")
    else:
        result["action"] = "order_failed"
        result["rejection_reason"] = order_result.get("error", "unknown")
        msg = f":x: ORDER FAILED: {ticker} | {result['rejection_reason']}"
        logger.error(f"[AutoExec] {msg}")
        if slack_fn:
            slack_fn(SLACK_TRADE_DESK_CHANNEL, msg)

    _log_execution(result)
    return result


# --------------- BLACKBOARD PUB/SUB ---------------

def _publish_trade_outcome(result: Dict, blackboard=None) -> None:
    """Publish trade outcome back to Blackboard for learning flywheel."""
    if not blackboard or not BlackboardMessage or not Topic:
        return
    try:
        outcome_msg = BlackboardMessage(
            topic=Topic.TRADE_OUTCOMES,
            payload={
                "ticker": result.get("ticker"),
                "action": result.get("action"),
                "entry": result.get("entry"),
                "stop": result.get("stop"),
                "target1": result.get("target1"),
                "target2": result.get("target2"),
                "order_id": result.get("order_id"),
                "rejection_reason": result.get("rejection_reason"),
                "em_pct": result.get("em_pct"),
                "qty": result.get("qty"),
                "timestamp": datetime.now(ET).isoformat(),
            },
            source="auto_executor",
        )
        blackboard.publish(outcome_msg)
        logger.info(f"[AutoExec] Published trade outcome for {result.get('ticker')}")
    except Exception as e:
        logger.warning(f"[AutoExec] Failed to publish trade outcome: {e}")


async def async_blackboard_consumer(blackboard=None) -> None:
    """
    Tier 3 Blackboard consumer: subscribes to EXECUTION_ORDERS topic.
    Executes signals published by Tier 2 (composite_scorer) and publishes
    outcomes back for the learning flywheel.
    """
    if not blackboard or not get_blackboard:
        logger.warning("[AutoExec] No Blackboard available, falling back to direct mode")
        return

    bb = blackboard if blackboard else get_blackboard()

    # Initialize AlpacaClient once for the consumer lifetime
    alpaca = None
    if AlpacaClient:
        try:
            alpaca = AlpacaClient()
            logger.info("[AutoExec] AlpacaClient initialized")
        except Exception as e:
            logger.error(f"[AutoExec] AlpacaClient init failed: {e}")

    logger.info("[AutoExec] Subscribing to EXECUTION_ORDERS on Blackboard...")

    async def _handle_execution_order(msg):
        """Process a single execution order from the Blackboard."""
        try:
            payload = msg.payload if hasattr(msg, 'payload') else msg
            ticker = payload.get("ticker")
            if not ticker:
                logger.warning("[AutoExec] Received order with no ticker, skipping")
                return

            logger.info(f"[AutoExec] Received execution order for {ticker}")

            # Build signal dict matching execute_signal() expected format
            signal = {
                "ticker": ticker,
                "score": payload.get("score", 0),
                "trigger": payload.get("trigger", "blackboard"),
                "regime": payload.get("regime", "YELLOW"),
                "em_pct": payload.get("em_pct", 0),
                "entry_price": payload.get("entry_price", 0),
                "atr": payload.get("atr", 0),
                                "side": payload.get("side", "buy"),
            }

            result = execute_signal(signal, alpaca)

            # Publish outcome back for learning flywheel
            _publish_trade_outcome(result, blackboard=bb)

        except Exception as e:
            logger.error(f"[AutoExec] Blackboard handler error: {e}")

    # Subscribe to execution orders topic
    if hasattr(bb, 'subscribe'):
        try:
            if Topic:
                bb.subscribe(Topic.EXECUTION_ORDERS, _handle_execution_order)
            else:
                bb.subscribe("execution_orders", _handle_execution_order)
            logger.info("[AutoExec] Successfully subscribed to EXECUTION_ORDERS")
        except Exception as e:
            logger.error(f"[AutoExec] Failed to subscribe: {e}")

    # Keep consumer alive
    while True:
        await asyncio.sleep(1)


async def run(mode: str = "blackboard") -> None:
    """
    Main async entry point for the Tier 3 execution agent.
    
    Modes:
        blackboard: Subscribe to Blackboard EXECUTION_ORDERS (default)
        standalone: Run without Blackboard (legacy direct mode)
    """
    logger.info(f"[AutoExec] Starting Tier 3 Execution Agent (mode={mode})")
    logger.info(f"[AutoExec] Max daily trades: {MAX_DAILY_TRADES}")
    logger.info(f"[AutoExec] Min score: {MIN_SCORE_TO_EXECUTE}")
    logger.info(f"[AutoExec] RR ratio: {RR_RATIO}")
    logger.info(f"[AutoExec] Account risk: {ACCOUNT_RISK_PCT}%")

    if mode == "blackboard" and get_blackboard:
        try:
            bb = get_blackboard()
            logger.info("[AutoExec] Blackboard connected, entering consumer loop")
            await async_blackboard_consumer(blackboard=bb)
        except Exception as e:
            logger.error(f"[AutoExec] Blackboard consumer failed: {e}")
            logger.info("[AutoExec] Falling back to standalone mode")
    else:
        logger.info("[AutoExec] Running in standalone mode (no Blackboard)")
        logger.info("[AutoExec] Waiting for direct execute_signal() calls...")
        # In standalone mode, keep alive for direct API calls
        while True:
            await asyncio.sleep(60)


# --------------- CLI ENTRY POINT ---------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="OpenClaw Tier 3 Execution Agent (auto_executor)"
    )
    parser.add_argument(
        "--mode",
        choices=["blackboard", "standalone"],
        default="blackboard",
        help="Run mode: blackboard (subscribe to pub/sub) or standalone",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a test execution with a dummy signal",
    )
    args = parser.parse_args()

    if args.test:
        logger.info("[AutoExec] Running test execution...")
        test_signal = {
            "ticker": "AAPL",
            "score": 85.0,
            "trigger": "test_cli",
            "regime": "bullish",
            "em_pct": 2.5,
            "entry_price": 150.00,
            "atr": 3.0,
                        "side": "buy",
        }
        test_alpaca = AlpacaClient() if AlpacaClient else None
        test_result = execute_signal(test_signal, test_alpaca)
        logger.info(f"[AutoExec] Test result: {test_result}")
    else:
        try:
            asyncio.run(run(mode=args.mode))
        except KeyboardInterrupt:
            logger.info("[AutoExec] Shutting down gracefully...")
        except Exception as e:
            logger.error(f"[AutoExec] Fatal error: {e}")
            raise
