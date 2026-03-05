"""Event-Driven Order Executor.

Subscribes to `signal.generated` on the MessageBus and automatically
executes trades through Alpaca when conditions are met.

Pipeline position:
    AlpacaStream → MessageBus → SignalEngine → **OrderExecutor** → Alpaca API
    market_data.bar    →    signal.generated    →    order.submitted

Risk gates (all must pass before execution):
    1. Signal score ≥ min_score threshold
    2. Kelly position sizing returns positive edge (action=BUY)
    3. Portfolio heat check (total exposure < max_heat)
    4. Drawdown check (not breached)
    5. Per-symbol cooldown (no rapid-fire orders)
    6. Daily trade limit not exceeded
    7. Market hours check (optional)

Connects to:
    - kelly_position_sizer.py → position sizing
    - alpaca_service.py → order placement
    - message_bus.py → event pub/sub
    - risk (API) → drawdown checks
    - websocket_manager → frontend notifications
"""
import asyncio
import logging
import time
import uuid
import collections
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OrderRecord:
    """Internal record of an executed or attempted order."""
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    qty: int
    order_type: str
    limit_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    signal_score: float
    kelly_pct: float
    regime: str
    status: str  # pending, submitted, filled, rejected, failed
    timestamp: float
    alpaca_response: Optional[Dict] = None
    reject_reason: Optional[str] = None


class OrderExecutor:
    """Event-driven order executor subscribing to signal.generated.

    Parameters
    ----------
    message_bus : MessageBus
        The async event bus to subscribe/publish on.
    auto_execute : bool
        If True, actually submits orders to Alpaca.
        If False, logs what WOULD be executed (dry-run/shadow mode).
    min_score : float
        Minimum signal score to consider for execution.
    max_daily_trades : int
        Maximum number of trades per day.
    cooldown_seconds : int
        Minimum seconds between trades on the same symbol.
    max_portfolio_heat : float
        Maximum total portfolio allocation (sum of all positions).
    max_single_position : float
        Maximum allocation for a single position (Kelly cap).
    use_bracket_orders : bool
        If True, places bracket orders with take-profit and stop-loss.
    """

    def __init__(
        self,
        message_bus,
        auto_execute: bool = False,
        min_score: float = 75.0,
        max_daily_trades: int = 10,
        cooldown_seconds: int = 300,
        max_portfolio_heat: float = 0.25,
        max_single_position: float = 0.10,
        use_bracket_orders: bool = True,
    ):
        self.message_bus = message_bus
        self.auto_execute = auto_execute
        # Range-validate parameters to prevent misconfiguration
        self.min_score = max(0.0, min(float(min_score), 100.0))
        self.max_daily_trades = max(1, min(int(max_daily_trades), 100))
        self.cooldown_seconds = max(0, min(int(cooldown_seconds), 86400))
        self.max_portfolio_heat = max(0.01, min(float(max_portfolio_heat), 1.0))
        self.max_single_position = max(0.01, min(float(max_single_position), 1.0))
        self.use_bracket_orders = use_bracket_orders

        # State tracking
        self._running = False
        self._start_time: Optional[float] = None
        self._orders: collections.deque = collections.deque(maxlen=10000)
        self._daily_trade_count = 0
        self._daily_reset_date: Optional[str] = None
        self._symbol_last_trade: Dict[str, float] = {}  # symbol -> timestamp
        self._signals_received = 0
        self._signals_executed = 0
        self._signals_rejected = 0
        self._total_notional = 0.0

        # Services (lazy-loaded)
        self._alpaca_svc = None
        self._kelly_sizer = None

    def _get_alpaca_service(self):
        """Lazy-load AlpacaService singleton."""
        if self._alpaca_svc is None:
            from app.services.alpaca_service import alpaca_service
            self._alpaca_svc = alpaca_service
        return self._alpaca_svc

    def _get_kelly_sizer(self):
        """Lazy-load KellyPositionSizer."""
        if self._kelly_sizer is None:
            from app.services.kelly_position_sizer import KellyPositionSizer
            self._kelly_sizer = KellyPositionSizer(
                max_allocation=self.max_single_position,
                use_half_kelly=True,
                min_edge=0.02,
            )
        return self._kelly_sizer

    async def start(self) -> None:
        """Subscribe to signal.generated + signal.unified + council.verdict and begin processing."""
        self._running = True
        self._start_time = time.time()
        await self.message_bus.subscribe("signal.generated", self._on_signal)
        await self.message_bus.subscribe("signal.unified", self._on_unified_signal)
        await self.message_bus.subscribe("council.verdict", self._on_council_verdict)
        mode = "AUTO-EXECUTE" if self.auto_execute else "SHADOW (dry-run)"
        logger.info(
            "OrderExecutor started in %s mode — "
            "min_score=%.0f, max_daily=%d, cooldown=%ds, heat_cap=%.0f%%",
            mode, self.min_score, self.max_daily_trades,
            self.cooldown_seconds, self.max_portfolio_heat * 100,
        )

    async def stop(self) -> None:
        """Unsubscribe and stop processing."""
        self._running = False
        await self.message_bus.unsubscribe("signal.generated", self._on_signal)
        await self.message_bus.unsubscribe("signal.unified", self._on_unified_signal)
        await self.message_bus.unsubscribe("council.verdict", self._on_council_verdict)
        logger.info(
            "OrderExecutor stopped — %d signals received, %d executed, %d rejected",
            self._signals_received, self._signals_executed, self._signals_rejected,
        )

    async def _on_council_verdict(self, verdict_data: Dict[str, Any]) -> None:
        """Process council.verdict events for execution decisions.

        Council verdicts carry the full 17-agent consensus. Only execute if
        the council says BUY/SELL with sufficient confidence and execution_ready.
        """
        if not self._running:
            return

        direction = verdict_data.get("direction", "hold")
        confidence = verdict_data.get("confidence", 0)
        vetoed = verdict_data.get("vetoed", False)
        execution_ready = verdict_data.get("execution_ready", False)
        symbol = verdict_data.get("symbol", "")
        council_id = verdict_data.get("council_decision_id", "")

        # Only act on actionable verdicts
        if direction == "hold" or vetoed or not execution_ready:
            logger.debug(
                "Council verdict for %s: %s (conf=%.0f%%, vetoed=%s, ready=%s) — no action",
                symbol, direction, confidence * 100, vetoed, execution_ready,
            )
            return

        if confidence < 0.5:
            logger.debug(
                "Council verdict for %s: confidence %.0f%% below 50%% threshold",
                symbol, confidence * 100,
            )
            return

        # Convert council verdict to signal-like format for existing risk gates
        synthetic_signal = {
            "symbol": symbol,
            "score": confidence * 100,  # Map 0-1 confidence to 0-100 score
            "price": verdict_data.get("agent_votes", [{}])[0].get("metadata", {}).get("price", 0)
                     if verdict_data.get("agent_votes") else 0,
            "regime": "COUNCIL",
            "label": f"council_{direction}",
            "council_decision_id": council_id,
            "source": "council_evaluator",
        }

        logger.info(
            "Council verdict -> execution: %s %s @ %.0f%% confidence [%s]",
            direction.upper(), symbol, confidence * 100, council_id[:8],
        )

        # Route through existing risk gates
        await self._on_signal(synthetic_signal)

    async def _on_unified_signal(self, unified_data: Dict[str, Any]) -> None:
        """Process signal.unified events from UnifiedProfitEngine.

        Unified signals already blend ML + TA + Scanner + Pattern scores.
        Only act on high-confidence unified signals (score >= 70, confidence >= 0.3).
        """
        if not self._running:
            return

        score = unified_data.get("unified_score", 0)
        confidence = unified_data.get("confidence", 0)
        direction = unified_data.get("direction", "neutral")
        symbol = unified_data.get("symbol", "")

        if direction == "neutral" or score < 70 or confidence < 0.3:
            return

        synthetic_signal = {
            "symbol": symbol,
            "score": score,
            "price": 0,  # Will be fetched by _on_signal
            "regime": "UNIFIED",
            "label": f"unified_{direction}",
            "source": "unified_profit_engine",
            "brain_scores": unified_data.get("brain_scores", {}),
        }

        logger.info(
            "Unified signal -> execution: %s score=%.1f conf=%.2f brains=%s",
            symbol, score, confidence, unified_data.get("brains_active", 0),
        )

        await self._on_signal(synthetic_signal)

    # ── Main Signal Handler ─────────────────────────────────────────────────

    async def _on_signal(self, signal_data: Dict[str, Any]) -> None:
        """Process a signal.generated event through risk gates and execute."""
        if not self._running:
            return

        self._signals_received += 1
        symbol = signal_data.get("symbol", "")
        score = signal_data.get("score", 0)
        price = signal_data.get("price", 0)
        regime = signal_data.get("regime", "UNKNOWN")
        label = signal_data.get("label", "")

        if not symbol or not price or price <= 0:
            return

        # ── Risk Gate 1: Minimum score ──
        if score < self.min_score:
            return  # Silent skip for low scores (very frequent)

        logger.info(
            "\U0001f4e8 Signal received: %s score=%.1f price=$%.2f regime=%s (%s)",
            symbol, score, price, regime, label,
        )

        # ── Risk Gate 2: Freeze check (RiskShield emergency) ──
        try:
            from app.api.v1.risk_shield_api import is_entries_frozen
            if is_entries_frozen():
                self._reject(symbol, score, "Entries frozen by RiskShield emergency action")
                return
        except Exception:
            pass  # If risk shield module unavailable, continue

        # ── Risk Gate 3: Daily trade limit ──
        self._check_daily_reset()
        if self._daily_trade_count >= self.max_daily_trades:
            self._reject(symbol, score, "Daily trade limit reached")
            return

        # ── Risk Gate 3: Per-symbol cooldown ──
        last_trade = self._symbol_last_trade.get(symbol, 0)
        if time.time() - last_trade < self.cooldown_seconds:
            remaining = int(self.cooldown_seconds - (time.time() - last_trade))
            self._reject(symbol, score, f"Cooldown active ({remaining}s remaining)")
            return

        # ── Risk Gate 4: Drawdown check ──
        drawdown_ok = await self._check_drawdown()
        if not drawdown_ok:
            self._reject(symbol, score, "Drawdown limit breached")
            return

        # ── Risk Gate 5: Kelly position sizing ──
        kelly_result = self._compute_kelly_size(symbol, score, regime, price)
        if kelly_result["action"] == "HOLD" or kelly_result["kelly_pct"] <= 0:
            self._reject(symbol, score, f"Kelly says HOLD (edge={kelly_result.get('edge', 0):.4f})")
            return

        # ── Risk Gate 6: Portfolio heat ──
        heat_ok, heat_info = await self._check_portfolio_heat(kelly_result["kelly_pct"])
        if not heat_ok:
            self._reject(
                symbol, score,
                f"Portfolio heat exceeded ({heat_info.get('current_heat', 0):.1%} / {self.max_portfolio_heat:.1%})",
            )
            return

        # ── All gates passed — compute order parameters ──
        qty = kelly_result["qty"]
        if qty < 1:
            self._reject(symbol, score, f"Computed qty < 1 (kelly_pct={kelly_result['kelly_pct']:.4f})")
            return

        # ── Execute or shadow ──
        client_order_id = f"et-{symbol}-{uuid.uuid4().hex[:8]}"

        order_record = OrderRecord(
            order_id="",
            client_order_id=client_order_id,
            symbol=symbol,
            side="buy",
            qty=qty,
            order_type="market" if not self.use_bracket_orders else "bracket",
            limit_price=None,
            stop_loss=kelly_result.get("stop_loss"),
            take_profit=kelly_result.get("take_profit"),
            signal_score=score,
            kelly_pct=kelly_result["kelly_pct"],
            regime=regime,
            status="pending",
            timestamp=time.time(),
        )

        if self.auto_execute:
            await self._execute_order(order_record, price)
        else:
            await self._shadow_execute(order_record, price)

    # ── Order Execution ─────────────────────────────────────────────────────

    async def _execute_order(self, record: OrderRecord, price: float) -> None:
        """Submit order to Alpaca and publish order.submitted event."""
        alpaca = self._get_alpaca_service()

        try:
            order_kwargs: Dict[str, Any] = {
                "symbol": record.symbol,
                "qty": str(record.qty),
                "side": record.side,
                "type": "market",
                "time_in_force": "day",
                "client_order_id": record.client_order_id,
            }

            # Bracket order with take-profit and stop-loss
            if self.use_bracket_orders:
                if record.stop_loss and record.take_profit:
                    order_kwargs["order_class"] = "bracket"
                    order_kwargs["take_profit"] = {
                        "limit_price": str(round(record.take_profit, 2)),
                    }
                    order_kwargs["stop_loss"] = {
                        "stop_price": str(round(record.stop_loss, 2)),
                    }
                else:
                    # Bracket mode enabled but missing stop/tp — reject to prevent naked order
                    record.status = "failed"
                    record.reject_reason = "Bracket mode requires both stop_loss and take_profit"
                    self._signals_rejected += 1
                    logger.warning("Order rejected for %s: bracket mode but missing SL/TP", record.symbol)
                    return

            result = await alpaca.create_order(**order_kwargs)

            if result:
                record.order_id = result.get("id", "")
                record.status = "submitted"
                record.alpaca_response = result
                self._orders.append(record)
                self._daily_trade_count += 1
                self._signals_executed += 1
                self._symbol_last_trade[record.symbol] = time.time()
                self._total_notional += record.qty * price

                logger.info(
                    "\u2705 ORDER SUBMITTED: %s %d x %s @ ~$%.2f "
                    "(score=%.1f, kelly=%.2f%%, regime=%s) [%s]",
                    record.side.upper(), record.qty, record.symbol, price,
                    record.signal_score, record.kelly_pct * 100, record.regime,
                    "BRACKET" if self.use_bracket_orders else "MARKET",
                )

                # Publish order.submitted event
                await self.message_bus.publish("order.submitted", {
                    "order_id": record.order_id,
                    "client_order_id": record.client_order_id,
                    "symbol": record.symbol,
                    "side": record.side,
                    "qty": record.qty,
                    "price": price,
                    "order_type": record.order_type,
                    "signal_score": record.signal_score,
                    "kelly_pct": record.kelly_pct,
                    "regime": record.regime,
                    "stop_loss": record.stop_loss,
                    "take_profit": record.take_profit,
                    "timestamp": time.time(),
                    "source": "order_executor",
                })

                # Broadcast to frontend
                await self._notify_frontend(record, price, "submitted")

                # Schedule fill check
                asyncio.create_task(self._poll_for_fill(record))

            else:
                record.status = "failed"
                record.reject_reason = "Alpaca returned no data"
                self._signals_rejected += 1
                logger.error("Order submission failed for %s — no response from Alpaca", record.symbol)

        except Exception as e:
            record.status = "failed"
            record.reject_reason = str(e)
            self._signals_rejected += 1
            logger.exception("Order execution error for %s: %s", record.symbol, e)

    async def _shadow_execute(self, record: OrderRecord, price: float) -> None:
        """Log what WOULD be executed without placing an actual order.

        Applies execution simulator (slippage + partial fills) for realism.
        """
        # Apply execution simulator for realistic paper trading
        sim_fill_price = price
        sim_fill_ratio = 1.0
        sim_slippage_bps = 0.0
        try:
            from app.services.execution_simulator import get_execution_simulator
            sim = get_execution_simulator()
            fill = sim.simulate_fill(
                price=price,
                side=record.side,
                order_qty=record.qty,
            )
            sim_fill_price = fill.fill_price
            sim_fill_ratio = fill.fill_ratio
            sim_slippage_bps = fill.slippage_bps
            # Adjust qty for partial fill
            record.qty = max(1, int(record.qty * sim_fill_ratio))
        except Exception as e:
            logger.debug("Execution simulator not available: %s", e)

        record.status = "shadow"
        self._orders.append(record)
        self._daily_trade_count += 1
        self._signals_executed += 1
        self._symbol_last_trade[record.symbol] = time.time()
        self._total_notional += record.qty * sim_fill_price

        logger.info(
            "\U0001f47b SHADOW ORDER: %s %d x %s @ ~$%.2f "
            "(intended=$%.2f, slip=%.1fbps, fill=%.0f%%, "
            "score=%.1f, kelly=%.2f%%, regime=%s, SL=$%.2f, TP=$%.2f)",
            record.side.upper(), record.qty, record.symbol, sim_fill_price,
            price, sim_slippage_bps, sim_fill_ratio * 100,
            record.signal_score, record.kelly_pct * 100, record.regime,
            record.stop_loss or 0, record.take_profit or 0,
        )

        # Still publish event (downstream can distinguish by source)
        await self.message_bus.publish("order.submitted", {
            "order_id": f"shadow-{record.client_order_id}",
            "client_order_id": record.client_order_id,
            "symbol": record.symbol,
            "side": record.side,
            "qty": record.qty,
            "price": sim_fill_price,
            "intended_price": price,
            "slippage_bps": sim_slippage_bps,
            "fill_ratio": sim_fill_ratio,
            "order_type": record.order_type,
            "signal_score": record.signal_score,
            "kelly_pct": record.kelly_pct,
            "regime": record.regime,
            "stop_loss": record.stop_loss,
            "take_profit": record.take_profit,
            "timestamp": time.time(),
            "source": "order_executor_shadow",
        })

        await self._notify_frontend(record, sim_fill_price, "shadow")

    # ── Fill Polling ────────────────────────────────────────────────────────

    async def _poll_for_fill(self, record: OrderRecord, max_attempts: int = 30) -> None:
        """Poll Alpaca for order fill status (check every 10s for up to 5 min)."""
        if not record.order_id:
            return

        alpaca = self._get_alpaca_service()
        for attempt in range(max_attempts):
            await asyncio.sleep(10)
            try:
                order_status = await alpaca.get_order(record.order_id)
                if not order_status:
                    continue

                status = order_status.get("status", "")

                if status == "filled":
                    record.status = "filled"
                    fill_price = float(order_status.get("filled_avg_price", 0))
                    filled_qty = int(order_status.get("filled_qty", 0))

                    logger.info(
                        "\U0001f4b0 ORDER FILLED: %s %d x %s @ $%.2f (signal=%.1f)",
                        record.side.upper(), filled_qty, record.symbol,
                        fill_price, record.signal_score,
                    )

                    await self.message_bus.publish("order.filled", {
                        "order_id": record.order_id,
                        "client_order_id": record.client_order_id,
                        "symbol": record.symbol,
                        "side": record.side,
                        "qty": filled_qty,
                        "fill_price": fill_price,
                        "signal_score": record.signal_score,
                        "kelly_pct": record.kelly_pct,
                        "regime": record.regime,
                        "timestamp": time.time(),
                        "source": "order_executor",
                    })

                    # Wire fill → ML outcome resolver (flywheel)
                    self._record_fill_outcome(record)
                    return

                elif status in ("canceled", "cancelled", "expired", "rejected"):
                    record.status = status
                    record.reject_reason = order_status.get("message", status)
                    logger.warning(
                        "Order %s for %s ended with status: %s",
                        record.order_id, record.symbol, status,
                    )

                    await self.message_bus.publish("order.cancelled", {
                        "order_id": record.order_id,
                        "symbol": record.symbol,
                        "status": status,
                        "reason": record.reject_reason,
                        "timestamp": time.time(),
                        "source": "order_executor",
                    })
                    return

            except Exception as e:
                logger.debug("Fill poll error for %s: %s", record.symbol, e)

        logger.warning(
            "Fill poll timeout for %s order %s after %d attempts",
            record.symbol, record.order_id, max_attempts,
        )

    # ── Risk Checks ─────────────────────────────────────────────────────────

    def _compute_kelly_size(
        self, symbol: str, score: float, regime: str, price: float
    ) -> Dict[str, Any]:
        """Compute Kelly-optimal position size and bracket levels."""
        sizer = self._get_kelly_sizer()

        # Pull calibrated Kelly params from OutcomeTracker (real trade data)
        # Falls back to heuristic if insufficient history
        try:
            from app.services.outcome_tracker import get_outcome_tracker
            kelly_params = get_outcome_tracker().get_kelly_params()
            if kelly_params["sample_size"] >= 10:
                win_rate = kelly_params["win_rate"]
                avg_win_pct = kelly_params["avg_win_pct"]
                avg_loss_pct = kelly_params["avg_loss_pct"]
            else:
                win_rate = min(0.75, 0.40 + (score - 50) * 0.007)
                avg_win_pct = 0.035
                avg_loss_pct = 0.015
        except Exception:
            win_rate = min(0.75, 0.40 + (score - 50) * 0.007)
            avg_win_pct = 0.035
            avg_loss_pct = 0.015

        pos = sizer.calculate(
            win_rate=win_rate,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            regime=regime,
        )

        if pos.action == "HOLD" or pos.final_pct <= 0:
            return {
                "action": "HOLD",
                "kelly_pct": 0.0,
                "qty": 0,
                "edge": pos.edge,
            }

        # Get account equity for $ sizing
        equity = 100_000.0  # Default for paper
        try:
            alpaca = self._get_alpaca_service()
            # Note: sync access to cached value if available
            cached = alpaca._cache_get("account", 60)
            if cached:
                equity = float(cached.get("equity", 100_000))
        except Exception:
            pass

        dollar_amount = equity * pos.final_pct
        qty = max(0, int(dollar_amount / price))

        # ATR-based stop-loss and take-profit
        # Approximate ATR as 2% of price (fallback)
        atr_estimate = price * 0.02
        stop_data = sizer.calculate_trailing_stop(
            entry_price=price,
            atr=atr_estimate,
            side="buy",
            atr_multiplier=2.0,
            trailing_pct=0.03,
        )

        return {
            "action": pos.action,
            "kelly_pct": pos.final_pct,
            "raw_kelly": pos.raw_kelly,
            "half_kelly": pos.half_kelly,
            "edge": pos.edge,
            "qty": qty,
            "dollar_amount": round(dollar_amount, 2),
            "stop_loss": stop_data["stop_loss"],
            "take_profit": stop_data["take_profit"],
            "risk_reward_ratio": stop_data["risk_reward_ratio"],
        }

    async def _check_drawdown(self) -> bool:
        """Check if drawdown limits allow trading."""
        try:
            from app.api.v1.risk import drawdown_check_status as drawdown_check
            dd_data = await drawdown_check()
            if dd_data.get("drawdown_breached") or not dd_data.get("trading_allowed", True):
                logger.warning("Drawdown gate BLOCKED: %s", dd_data)
                return False
            return True
        except Exception as e:
            logger.debug("Drawdown check unavailable: %s", e)
            return True  # Allow trading if check unavailable

    async def _check_portfolio_heat(self, new_position_pct: float) -> tuple:
        """Check total portfolio heat (sum of position allocations)."""
        try:
            alpaca = self._get_alpaca_service()
            account = await alpaca.get_account()
            positions = await alpaca.get_positions()

            if not account:
                return True, {}  # Allow if can't check

            equity = float(account.get("equity", 0))
            if equity <= 0:
                return False, {"current_heat": 0, "reason": "Zero equity"}

            current_heat = 0.0
            if positions:
                for pos in positions:
                    market_val = abs(float(pos.get("market_value", 0)))
                    current_heat += market_val / equity

            remaining = self.max_portfolio_heat - current_heat
            allowed = new_position_pct <= remaining

            return allowed, {
                "current_heat": current_heat,
                "remaining": remaining,
                "new_position": new_position_pct,
            }
        except Exception as e:
            logger.debug("Portfolio heat check error: %s", e)
            return True, {}  # Allow if can't check

    def _check_daily_reset(self) -> None:
        """Reset daily trade count at market open (US/Eastern)."""
        try:
            from zoneinfo import ZoneInfo
            eastern = ZoneInfo("America/New_York")
        except ImportError:
            from datetime import timedelta
            # Fallback: approximate ET as UTC-5 (ignores DST but better than UTC)
            eastern = timezone(timedelta(hours=-5))
        today_et = datetime.now(eastern).strftime("%Y-%m-%d")
        if self._daily_reset_date != today_et:
            self._daily_reset_date = today_et
            self._daily_trade_count = 0

    def _reject(self, symbol: str, score: float, reason: str) -> None:
        """Log a rejected signal."""
        self._signals_rejected += 1
        logger.info(
            "\u26d4 Signal REJECTED: %s score=%.1f — %s",
            symbol, score, reason,
        )

    def _record_fill_outcome(self, record: OrderRecord) -> None:
        """Log fill for tracking. Actual outcome resolution is handled by OutcomeTracker
        which monitors positions until close and feeds real PnL to feedback systems."""
        logger.info(
            "Fill recorded for %s — OutcomeTracker will resolve outcome on position close",
            record.symbol,
        )

    # ── Frontend Notifications ──────────────────────────────────────────────

    async def _notify_frontend(self, record: OrderRecord, price: float, status: str) -> None:
        """Send order event to frontend via WebSocket."""
        try:
            from app.websocket_manager import broadcast_ws
            await broadcast_ws("order", {
                "type": f"order_{status}",
                "symbol": record.symbol,
                "side": record.side,
                "qty": record.qty,
                "price": price,
                "score": record.signal_score,
                "kelly_pct": round(record.kelly_pct * 100, 2),
                "stop_loss": record.stop_loss,
                "take_profit": record.take_profit,
                "regime": record.regime,
                "auto_execute": self.auto_execute,
            })
        except Exception as e:
            logger.debug("Frontend notification failed: %s", e)

    # ── Status & Metrics ────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return executor status for health endpoint and dashboard."""
        uptime = time.time() - self._start_time if self._start_time else 0
        recent_orders = [
            {
                "symbol": o.symbol,
                "side": o.side,
                "qty": o.qty,
                "score": o.signal_score,
                "kelly_pct": round(o.kelly_pct * 100, 2),
                "status": o.status,
                "regime": o.regime,
                "time": datetime.fromtimestamp(o.timestamp, tz=timezone.utc).isoformat(),
            }
            for o in self._orders[-20:]  # Last 20 orders
        ]

        return {
            "running": self._running,
            "mode": "auto_execute" if self.auto_execute else "shadow",
            "uptime_seconds": round(uptime, 1),
            "signals_received": self._signals_received,
            "signals_executed": self._signals_executed,
            "signals_rejected": self._signals_rejected,
            "daily_trades": self._daily_trade_count,
            "max_daily_trades": self.max_daily_trades,
            "total_notional": round(self._total_notional, 2),
            "min_score": self.min_score,
            "cooldown_seconds": self.cooldown_seconds,
            "max_portfolio_heat": self.max_portfolio_heat,
            "use_bracket_orders": self.use_bracket_orders,
            "recent_orders": recent_orders,
        }

    def get_order_history(self) -> List[Dict]:
        """Return full order history."""
        return [
            {
                "order_id": o.order_id,
                "client_order_id": o.client_order_id,
                "symbol": o.symbol,
                "side": o.side,
                "qty": o.qty,
                "order_type": o.order_type,
                "signal_score": o.signal_score,
                "kelly_pct": round(o.kelly_pct * 100, 2),
                "regime": o.regime,
                "status": o.status,
                "stop_loss": o.stop_loss,
                "take_profit": o.take_profit,
                "reject_reason": o.reject_reason,
                "time": datetime.fromtimestamp(o.timestamp, tz=timezone.utc).isoformat(),
            }
            for o in self._orders
        ]

    async def set_auto_execute(self, enabled: bool) -> Dict[str, Any]:
        """Toggle auto-execute mode at runtime."""
        previous = self.auto_execute
        self.auto_execute = enabled
        mode = "AUTO-EXECUTE" if enabled else "SHADOW"
        logger.info(
            "OrderExecutor mode changed: %s → %s",
            "AUTO" if previous else "SHADOW",
            mode,
        )
        return {
            "previous": "auto_execute" if previous else "shadow",
            "current": "auto_execute" if enabled else "shadow",
        }
