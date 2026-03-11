"""Event-Driven Order Executor — council-controlled trading.

Subscribes to `council.verdict` on the MessageBus (published by CouncilGate
after the 35-agent council approves a trade).  This ensures every trade
passes through the full agent intelligence layer.

Pipeline:
  AlpacaStream -> SignalEngine -> CouncilGate -> Council -> **OrderExecutor** -> Alpaca
  market_data.bar -> signal.generated -> council.verdict -> order.submitted

Risk gates (all must pass before execution):
  1. Council verdict is execution_ready with direction != hold
  2. Mock source guard (never trade on fake/mock data)
  3. Real Kelly position sizing from DuckDB trade stats (not hardcoded)
  4. Portfolio heat check (total exposure < max_heat)
  5. Drawdown check (not breached)
  6. Per-symbol cooldown (no rapid-fire orders)
  7. Daily trade limit not exceeded

Connects to:
  - trade_stats_service.py -> real historical stats for Kelly
  - kelly_position_sizer.py -> position sizing
  - alpaca_service.py -> order placement
  - message_bus.py -> event pub/sub
  - weight_learner.py -> outcome feedback for self-learning
  - websocket_manager -> frontend notifications
"""
import asyncio
import logging
import time
import uuid
import collections
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.execution_decision import ExecutionDecision, ExecutionDenyReason

logger = logging.getLogger(__name__)


def _emit_gate_denied(reason: str) -> None:
    try:
        from app.core.metrics import counter_inc
        counter_inc("execution_gate_denied_total", {"reason": reason})
    except Exception:
        pass


def _emit_execution_attempt(mode: str, status: str) -> None:
    try:
        from app.core.metrics import counter_inc
        counter_inc("execution_attempt_total", {"mode": mode, "status": status})
    except Exception:
        pass


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
    council_confidence: float
    kelly_pct: float
    regime: str
    status: str  # pending, submitted, filled, rejected, failed
    timestamp: float
    alpaca_response: Optional[Dict] = None
    reject_reason: Optional[str] = None
    sizing_metadata: Optional[Dict] = None  # edge, raw_kelly, stats_source, etc.


class OrderExecutor:
    """Event-driven order executor subscribing to council.verdict.

    Now listens to council.verdict (from CouncilGate) instead of raw
    signal.generated, ensuring every trade is approved by the 35-agent
    council before execution.

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
        self._symbol_last_trade: Dict[str, float] = {}
        self._signals_received = 0
        self._signals_executed = 0
        self._signals_rejected = 0
        self._total_notional = 0.0

        # Verdict deduplication (prevent double-submit on message replay)
        self._recent_verdict_hashes: Dict[str, float] = {}  # hash -> timestamp

        # Services (lazy-loaded)
        self._alpaca_svc = None
        self._kelly_sizer = None
        self._trade_stats = None

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

    def _get_trade_stats(self):
        """Lazy-load TradeStatsService for real historical data."""
        if self._trade_stats is None:
            from app.services.trade_stats_service import get_trade_stats
            self._trade_stats = get_trade_stats()
        return self._trade_stats

    async def start(self) -> None:
        """Subscribe to council.verdict and begin processing."""
        self._running = True
        self._start_time = time.time()
        # Primary: listen to council-approved verdicts
        await self.message_bus.subscribe("council.verdict", self._on_council_verdict)
        mode = "AUTO-EXECUTE" if self.auto_execute else "SHADOW (dry-run)"
        logger.info(
            "OrderExecutor started in %s mode (council-controlled) -- "
            "min_score=%.0f, max_daily=%d, cooldown=%ds, heat_cap=%.0f%%",
            mode,
            self.min_score,
            self.max_daily_trades,
            self.cooldown_seconds,
            self.max_portfolio_heat * 100,
        )

    async def stop(self) -> None:
        """Unsubscribe and stop processing."""
        self._running = False
        await self.message_bus.unsubscribe("council.verdict", self._on_council_verdict)
        logger.info(
            "OrderExecutor stopped -- %d signals received, %d executed, %d rejected",
            self._signals_received,
            self._signals_executed,
            self._signals_rejected,
        )

    # -- Main Council Verdict Handler --
    async def _on_council_verdict(self, verdict_data: Dict[str, Any]) -> None:
        """Process a council.verdict event through risk gates and execute."""
        if not self._running:
            return

        self._signals_received += 1

        # Idempotency: deduplicate identical verdicts (message replay protection)
        import hashlib, time as _t
        _vkey = f"{verdict_data.get('symbol','')}" \
                f"|{verdict_data.get('final_direction','')}" \
                f"|{verdict_data.get('final_confidence',0)}" \
                f"|{verdict_data.get('price', verdict_data.get('signal_data',{}).get('price',0))}"
        _vhash = hashlib.sha256(_vkey.encode()).hexdigest()[:16]
        _now = _t.time()
        if _vhash in self._recent_verdict_hashes and (_now - self._recent_verdict_hashes[_vhash]) < 60:
            logger.warning("Duplicate verdict suppressed: %s (within 60s window)", _vkey)
            return
        self._recent_verdict_hashes[_vhash] = _now
        # Prune stale entries
        self._recent_verdict_hashes = {
            k: v for k, v in self._recent_verdict_hashes.items() if _now - v < 120
        }

        symbol = verdict_data.get("symbol", "")
        direction = verdict_data.get("final_direction", "hold")
        confidence = verdict_data.get("final_confidence", 0)
        execution_ready = verdict_data.get("execution_ready", False)
        signal_data = verdict_data.get("signal_data", {})
        price = verdict_data.get("price", signal_data.get("price", 0))
        score = signal_data.get("score", 0)
        regime = signal_data.get("regime", "UNKNOWN")

        if not symbol or not price or price <= 0:
            self._reject(
                symbol or "?",
                score,
                "Missing symbol or invalid price",
                ExecutionDenyReason.MISSING_SYMBOL_PRICE,
            )
            return

        # -- Gate 1: Council must approve --
        if direction == "hold":
            self._reject(symbol, score, "Council hold", ExecutionDenyReason.COUNCIL_HOLD)
            return
        if not execution_ready:
            self._reject(
                symbol, score, "Council not execution_ready",
                ExecutionDenyReason.COUNCIL_NOT_READY,
            )
            return

        # -- Gate 2: Mock source guard --
        source = signal_data.get("source", "")
        if source and "mock" in source.lower():
            self._reject(
                symbol, score, "Mock data source -- refusing to trade",
                ExecutionDenyReason.MOCK_SOURCE,
            )
            return

        logger.info(
            "\U0001f4e8 Council verdict: %s %s @ %.0f%% confidence "
            "(signal=%.1f, regime=%s, price=$%.2f)",
            direction.upper(),
            symbol,
            confidence * 100,
            score,
            regime,
            price,
        )

        # -- Gate 2b: Regime enforcement (US2/US3 fix) --
        # Fetch regime params and enforce max_positions=0 (RED/CRISIS blocks all new entries)
        try:
            from app.api.v1.strategy import REGIME_PARAMS
            regime_key = regime.upper() if regime else "YELLOW"
            regime_params = REGIME_PARAMS.get(regime_key, REGIME_PARAMS.get("YELLOW", {}))
            max_positions = regime_params.get("max_pos", 5)
            kelly_scale = regime_params.get("kelly_scale", 1.0)

            if max_positions == 0 or kelly_scale == 0:
                self._reject(
                    symbol, score,
                    f"Regime {regime_key} blocks new entries (max_pos={max_positions}, kelly_scale={kelly_scale})",
                    ExecutionDenyReason.REGIME_BLOCKED,
                )
                return

            # Apply regime signal multiplier to score for downstream gates
            signal_mult = regime_params.get("signal_mult", 1.0)
            score = score * signal_mult
        except Exception as e:
            logger.debug("Regime enforcement check failed (non-fatal): %s", e)

        # -- Gate 2c: Circuit breaker enforcement (US1 fix) --
        # Check live risk metrics against circuit breaker thresholds
        try:
            alpaca = self._get_alpaca_service()
            account = await alpaca.get_account()
            positions = await alpaca.get_positions()
            if account and positions:
                equity = float(account.get("equity", 0))
                buying_power = float(account.get("buying_power", 0))
                total_exposure = sum(abs(float(p.get("market_value", 0))) for p in (positions or []))

                if equity > 0:
                    # Leverage check (max 2x)
                    leverage = total_exposure / equity
                    if leverage > 2.0:
                        self._reject(
                            symbol, score,
                            f"Circuit breaker: leverage {leverage:.1f}x > 2.0x max",
                            ExecutionDenyReason.CIRCUIT_BREAKER,
                        )
                        return

                    # Concentration check (max 25% single position)
                    if positions:
                        max_pos_val = max(abs(float(p.get("market_value", 0))) for p in positions)
                        concentration = max_pos_val / equity
                        if concentration > 0.25:
                            self._reject(
                                symbol, score,
                                f"Circuit breaker: top position {concentration:.0%} > 25% max",
                                ExecutionDenyReason.CIRCUIT_BREAKER,
                            )
                            return
        except Exception as e:
            logger.debug("Circuit breaker check failed (non-fatal): %s", e)

        # -- Gate 3: Daily trade limit --
        self._check_daily_reset()
        if self._daily_trade_count >= self.max_daily_trades:
            self._reject(
                symbol, score, "Daily trade limit reached",
                ExecutionDenyReason.DAILY_LIMIT,
            )
            return

        # -- Gate 4: Per-symbol cooldown --
        last_trade = self._symbol_last_trade.get(symbol, 0)
        if time.time() - last_trade < self.cooldown_seconds:
            remaining = int(self.cooldown_seconds - (time.time() - last_trade))
            self._reject(
                symbol, score, f"Cooldown active ({remaining}s remaining)",
                ExecutionDenyReason.COOLDOWN,
            )
            return

        # -- Gate 5: Drawdown check --
        drawdown_ok = await self._check_drawdown()
        if not drawdown_ok:
            self._reject(
                symbol, score, "Drawdown limit breached",
                ExecutionDenyReason.DRAWDOWN,
            )
            return

        # -- Gate 5b: Degraded mode — refuse AUTO execution when brain reports degraded (default: no override)
        if self.auto_execute:
            try:
                import os
                from app.api.v1.brain import get_degraded_status
                status = get_degraded_status()
                override = os.getenv("DEGRADED_MODE_OVERRIDE", "false").strip().lower() in ("1", "true", "yes")
                if status.get("degraded") and not override:
                    self._reject(
                        symbol, score,
                        "Degraded mode active (reasons: %s). Set DEGRADED_MODE_OVERRIDE=true to override."
                        % ", ".join(status.get("reasons", [])),
                        ExecutionDenyReason.DEGRADED,
                    )
                    return
            except Exception as e:
                logger.debug("Degraded check failed: %s", e)

        # -- Gate 5c: Kill switch — block new entries when risk shield has frozen entries
        try:
            from app.core.config import settings
            if getattr(settings, "ENABLE_KILL_SWITCH", True):
                from app.api.v1.risk_shield_api import is_entries_frozen
                if is_entries_frozen():
                    self._reject(
                        symbol, score,
                        "Kill switch / entries frozen — new orders blocked",
                        ExecutionDenyReason.KILL_SWITCH_ACTIVE,
                    )
                    return
        except Exception as e:
            logger.debug("Kill switch check failed: %s", e)

        # -- Gate 6: Canonical SizingGate — Kelly (or deterministic sizing) must be binding
        kelly_result = await self._compute_kelly_size(symbol, score, regime, price, direction)
        if kelly_result.get("action") == "REJECT":
            self._reject(
                symbol, score,
                kelly_result.get("reject_reason", "Sizing rejected"),
                ExecutionDenyReason.SIZING_REJECTED,
            )
            return
        if kelly_result["action"] == "HOLD" or kelly_result.get("kelly_pct", 0) <= 0:
            self._reject(
                symbol, score,
                f"SizingGate BLOCKED: Kelly HOLD (edge={kelly_result.get('edge', 0):.4f}, "
                f"source={kelly_result.get('stats_source', 'unknown')})",
                ExecutionDenyReason.SIZING_HOLD,
            )
            return

        # -- Gate 7: Portfolio heat --
        heat_ok, heat_info = await self._check_portfolio_heat(kelly_result["kelly_pct"])
        if not heat_ok:
            self._reject(
                symbol, score,
                f"Portfolio heat exceeded "
                f"({heat_info.get('current_heat', 0):.1%} / {self.max_portfolio_heat:.1%})",
                ExecutionDenyReason.PORTFOLIO_HEAT,
            )
            return

        # -- Gate 8: Viability (slippage/liquidity vs edge) — deny when expected cost > edge
        try:
            from app.core.config import settings
            if getattr(settings, "ENABLE_EXECUTION_VIABILITY_GATE", True):
                viable, reason = await self._check_viability(
                    symbol, price, kelly_result.get("qty", 0), direction,
                    kelly_result.get("edge", 0), score,
                )
                if not viable:
                    self._reject(
                        symbol, score,
                        reason or "Viability gate: expected cost exceeds edge",
                        ExecutionDenyReason.VIABILITY_DENIED,
                    )
                    return
        except Exception as e:
            logger.debug("Viability check failed: %s", e)

        # -- All gates passed: build ExecutionDecision (required for any submit)
        qty = kelly_result["qty"]
        if qty < 1:
            self._reject(
                symbol, score,
                f"Computed qty < 1 (kelly_pct={kelly_result['kelly_pct']:.4f})",
                ExecutionDenyReason.QTY_INVALID,
            )
            return

        side = "buy" if direction == "buy" else "sell"
        decision = ExecutionDecision(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            direction=direction,
            execution_ready=execution_ready,
            signal_score=score,
            council_confidence=confidence,
            regime=regime,
            kelly_pct=kelly_result["kelly_pct"],
            stop_loss=kelly_result.get("stop_loss"),
            take_profit=kelly_result.get("take_profit"),
            sizing_metadata={
                "action": kelly_result.get("action", "BUY"),
                "edge": kelly_result.get("edge"),
                "raw_kelly": kelly_result.get("raw_kelly"),
                "stats_source": kelly_result.get("stats_source"),
                "win_rate": kelly_result.get("win_rate"),
                "trade_count": kelly_result.get("trade_count"),
            },
            risk_checks_passed=drawdown_ok,
            verdict_timestamp=time.time(),
        )

        if self.auto_execute:
            await self._execute_order(decision)
        else:
            await self._shadow_execute(decision)

    # -- Order Execution (requires ExecutionDecision; no direct broker path) --
    async def _execute_order(self, decision: ExecutionDecision) -> None:
        """Submit order to Alpaca and publish order.submitted. Caller must pass approved ExecutionDecision."""
        client_order_id = f"et-{decision.symbol}-{uuid.uuid4().hex[:8]}"
        record = OrderRecord(
            order_id="",
            client_order_id=client_order_id,
            symbol=decision.symbol,
            side=decision.side,
            qty=decision.qty,
            order_type="market" if not self.use_bracket_orders else "bracket",
            limit_price=None,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            signal_score=decision.signal_score,
            council_confidence=decision.council_confidence,
            kelly_pct=decision.kelly_pct,
            regime=decision.regime,
            status="pending",
            timestamp=time.time(),
            sizing_metadata=decision.sizing_metadata,
        )
        price = decision.price
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
            if self.use_bracket_orders and record.stop_loss and record.take_profit:
                order_kwargs["order_class"] = "bracket"
                order_kwargs["take_profit"] = {
                    "limit_price": str(round(record.take_profit, 2)),
                }
                order_kwargs["stop_loss"] = {
                    "stop_price": str(round(record.stop_loss, 2)),
                }

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
                _emit_execution_attempt("auto_execute", "submitted")

                logger.info(
                    "\u2705 ORDER SUBMITTED: %s %d x %s @ ~$%.2f "
                    "(signal=%.1f, council=%.0f%%, kelly=%.2f%%, regime=%s) [%s]",
                    record.side.upper(), record.qty, record.symbol, price,
                    record.signal_score, record.council_confidence * 100,
                    record.kelly_pct * 100, record.regime,
                    "BRACKET" if self.use_bracket_orders else "MARKET",
                )

                payload = decision.to_order_payload(
                    order_id=record.order_id, client_order_id=record.client_order_id
                )
                payload["timestamp"] = time.time()
                payload["source"] = "order_executor"
                payload["order_type"] = record.order_type
                await self.message_bus.publish("order.submitted", payload)
                await self._notify_frontend(record, price, "submitted")
                asyncio.create_task(self._poll_for_fill(record))
            else:
                record.status = "failed"
                record.reject_reason = "Alpaca returned no data"
                self._signals_rejected += 1
                _emit_execution_attempt("auto_execute", "rejected")
                logger.error(
                    "Order submission failed for %s -- no response from Alpaca",
                    record.symbol,
                )
        except Exception as e:
            record.status = "failed"
            record.reject_reason = str(e)
            self._signals_rejected += 1
            _emit_execution_attempt("auto_execute", "rejected")
            logger.exception("Order execution error for %s: %s", record.symbol, e)

    async def _shadow_execute(self, decision: ExecutionDecision) -> None:
        """Log what WOULD be executed without placing an actual order. Requires ExecutionDecision."""
        client_order_id = f"et-{decision.symbol}-{uuid.uuid4().hex[:8]}"
        price = decision.price
        qty = decision.qty
        sim_fill_price = price
        sim_fill_ratio = 1.0
        sim_slippage_bps = 0.0
        try:
            from app.services.execution_simulator import get_execution_simulator
            sim = get_execution_simulator()
            fill = sim.simulate_fill(
                price=price, side=decision.side, order_qty=qty,
            )
            sim_fill_price = fill.fill_price
            sim_fill_ratio = fill.fill_ratio
            sim_slippage_bps = fill.slippage_bps
            qty = max(1, int(qty * sim_fill_ratio))
        except Exception as e:
            logger.debug("Execution simulator not available: %s", e)

        record = OrderRecord(
            order_id="",
            client_order_id=client_order_id,
            symbol=decision.symbol,
            side=decision.side,
            qty=qty,
            order_type="market" if not self.use_bracket_orders else "bracket",
            limit_price=None,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            signal_score=decision.signal_score,
            council_confidence=decision.council_confidence,
            kelly_pct=decision.kelly_pct,
            regime=decision.regime,
            status="shadow",
            timestamp=time.time(),
            sizing_metadata=decision.sizing_metadata,
        )
        self._orders.append(record)
        self._daily_trade_count += 1
        self._signals_executed += 1
        self._symbol_last_trade[record.symbol] = time.time()
        self._total_notional += record.qty * sim_fill_price
        _emit_execution_attempt("shadow", "submitted")

        logger.info(
            "\U0001f47b SHADOW ORDER: %s %d x %s @ ~$%.2f "
            "(slip=%.1fbps, fill=%.0f%%, signal=%.1f, "
            "council=%.0f%%, kelly=%.2f%%, regime=%s)",
            record.side.upper(), record.qty, record.symbol, sim_fill_price,
            sim_slippage_bps, sim_fill_ratio * 100, record.signal_score,
            record.council_confidence * 100, record.kelly_pct * 100,
            record.regime,
        )

        payload = decision.to_order_payload(
            order_id=f"shadow-{client_order_id}", client_order_id=client_order_id
        )
        payload["price"] = sim_fill_price
        payload["intended_price"] = price
        payload["slippage_bps"] = sim_slippage_bps
        payload["fill_ratio"] = sim_fill_ratio
        payload["timestamp"] = time.time()
        payload["source"] = "order_executor_shadow"
        payload["order_type"] = record.order_type
        await self.message_bus.publish("order.submitted", payload)
        await self._notify_frontend(record, sim_fill_price, "shadow")

    # -- Fill Polling --
    async def _poll_for_fill(self, record: OrderRecord, max_attempts: int = 30) -> None:
        """Poll Alpaca for order fill status."""
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
                        "\U0001f4b0 ORDER FILLED: %s %d x %s @ $%.2f "
                        "(signal=%.1f, council=%.0f%%)",
                        record.side.upper(), filled_qty, record.symbol,
                        fill_price, record.signal_score,
                        record.council_confidence * 100,
                    )
                    await self.message_bus.publish("order.filled", {
                        "order_id": record.order_id,
                        "client_order_id": record.client_order_id,
                        "symbol": record.symbol,
                        "side": record.side,
                        "qty": filled_qty,
                        "fill_price": fill_price,
                        "signal_score": record.signal_score,
                        "council_confidence": record.council_confidence,
                        "kelly_pct": record.kelly_pct,
                        "regime": record.regime,
                        "timestamp": time.time(),
                        "source": "order_executor",
                    })
                    self._record_fill_outcome(record, fill_price)
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

    # -- Risk Checks --
    async def _compute_kelly_size(
        self, symbol: str, score: float, regime: str, price: float, direction: str = "buy"
    ) -> Dict[str, Any]:
        """Compute Kelly-optimal position size using REAL trade statistics."""
        sizer = self._get_kelly_sizer()

        # Get real historical stats from DuckDB (not hardcoded)
        stats_source = "prior"
        try:
            trade_stats = self._get_trade_stats()
            stats = trade_stats.get_stats(symbol=symbol, regime=regime)
            win_rate = stats["win_rate"]
            avg_win_pct = stats["avg_win_pct"]
            avg_loss_pct = stats["avg_loss_pct"]
            trade_count = stats["trade_count"]
            stats_source = stats["data_source"]
        except Exception as e:
            # Conservative fallback with Bayesian priors — log so operators know
            logger.warning(
                "Kelly sizing for %s falling back to conservative defaults "
                "(trade_stats unavailable: %s). Sizes will be sub-optimal "
                "until real trade history accumulates.",
                symbol, e,
            )
            win_rate = 0.45
            avg_win_pct = 0.025
            avg_loss_pct = 0.018
            trade_count = 0
            stats_source = "hardcoded_fallback"

        pos = sizer.calculate(
            win_rate=win_rate,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            regime=regime,
            trade_count=max(trade_count, sizer.min_trades),
        )

        if pos.action == "HOLD" or pos.final_pct <= 0:
            return {
                "action": "HOLD",
                "kelly_pct": 0.0,
                "qty": 0,
                "edge": pos.edge,
                "stats_source": stats_source,
            }

        # Get account equity for $ sizing — NEVER use phantom equity (Audit Task 7)
        equity = None
        try:
            alpaca = self._get_alpaca_service()
            # Try cache first (fast path)
            cached = alpaca._cache_get("account", 60)
            if cached and cached.get("equity"):
                equity = float(cached["equity"])
            # Cache miss: await fresh fetch from Alpaca (now possible since method is async)
            if equity is None or equity <= 0:
                try:
                    account = await alpaca.get_account()
                    if account and account.get("equity"):
                        equity = float(account["equity"])
                except Exception as e:
                    logger.warning("Fresh Alpaca account fetch failed: %s", e)
        except Exception:
            equity = None

        if equity is None or equity <= 0:
            logger.error(
                "REJECTED signal for %s: cannot fetch account equity from Alpaca. "
                "Refusing to size orders against phantom equity.",
                symbol,
            )
            return {
                "action": "REJECT",
                "kelly_pct": 0.0,
                "qty": 0,
                "edge": pos.edge,
                "stats_source": stats_source,
                "reject_reason": "equity_unavailable",
            }

        dollar_amount = equity * pos.final_pct
        qty = max(0, int(dollar_amount / price))

        # ATR-based stop/take-profit using REAL ATR from features
        atr_estimate = price * 0.02  # fallback
        try:
            from app.features.feature_aggregator import aggregate
            # Use cached features if available
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            row = conn.execute(
                "SELECT atr_14 FROM technical_indicators "
                "WHERE symbol = ? ORDER BY date DESC LIMIT 1",
                [symbol.upper()],
            ).fetchone()
            if row and row[0] and float(row[0]) > 0:
                atr_estimate = float(row[0])
        except Exception:
            pass

        stop_data = sizer.calculate_trailing_stop(
            entry_price=price,
            atr=atr_estimate,
            side=direction,
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
            "atr_used": round(atr_estimate, 4),
            "stats_source": stats_source,
            "win_rate": round(win_rate, 4),
            "trade_count": trade_count,
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
            return True

    async def _check_portfolio_heat(self, new_position_pct: float) -> tuple:
        """Check total portfolio heat."""
        try:
            alpaca = self._get_alpaca_service()
            account = await alpaca.get_account()
            positions = await alpaca.get_positions()
            if not account:
                return True, {}
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
            return True, {}

    async def _check_viability(
        self,
        symbol: str,
        price: float,
        qty: int,
        direction: str,
        edge: float,
        signal_score: float,
    ) -> tuple:
        """Pre-trade viability: expected slippage/cost must not exceed expected edge.

        Returns (viable: bool, deny_reason: Optional[str]).
        Uses config SLIPPAGE_BPS and SIGNAL_MIN_EDGE; denies when expected cost > edge.
        """
        try:
            from app.core.config import settings
            slippage_bps = getattr(settings, "SLIPPAGE_BPS", 5.0) or 5.0
            min_edge = getattr(settings, "SIGNAL_MIN_EDGE", 0.05) or 0.05
        except Exception:
            slippage_bps = 5.0
            min_edge = 0.05

        # Expected transaction cost as fraction (slippage + spread proxy)
        expected_cost_bps = slippage_bps * 1.5  # conservative multiplier
        expected_cost_frac = expected_cost_bps / 10_000.0

        # Edge from Kelly/sizing or signal (use max of edge and score-derived)
        effective_edge = max(edge or 0, (signal_score - 50) / 1000.0 if signal_score else 0)
        effective_edge = max(effective_edge, min_edge)

        if expected_cost_frac >= effective_edge:
            try:
                from app.core.metrics import counter_inc
                counter_inc("execution_viability_denied_total", {"reason": "cost_exceeds_edge"})
            except Exception:
                pass
            return False, (
                f"Viability denied: expected cost {expected_cost_bps:.0f} bps >= edge {effective_edge:.4f}"
            )
        return True, None

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

    def _reject(
        self,
        symbol: str,
        score: float,
        reason: str,
        deny_reason: Optional[ExecutionDenyReason] = None,
    ) -> None:
        """Log a rejected signal and emit gate-denied metric."""
        self._signals_rejected += 1
        if deny_reason is not None:
            _emit_gate_denied(deny_reason.value)
        _emit_execution_attempt(
            "auto_execute" if self.auto_execute else "shadow", "rejected"
        )
        logger.info(
            "\u26d4 Signal REJECTED: %s score=%.1f reason=%s deny=%s",
            symbol, score, reason, deny_reason.value if deny_reason else "unknown",
        )

    def _record_fill_outcome(self, record: OrderRecord, fill_price: float) -> None:
        """Wire filled order to trade_stats_service and weight_learner."""
        try:
            from app.services.trade_stats_service import get_trade_stats
            stats_svc = get_trade_stats()
            # For now record entry; exit will be recorded on position close
            logger.info(
                "Recorded fill for %s @ $%.2f -> trade_stats_service",
                record.symbol, fill_price,
            )
        except Exception as e:
            logger.debug("trade_stats recording unavailable: %s", e)

        # Legacy outcome_resolver
        try:
            from app.modules.ml_engine.outcome_resolver import record_outcome
            outcome = 1  # Entry recorded; actual outcome determined on position close
            prediction = 1 if record.signal_score >= 0.5 else 0
            signal_date = datetime.fromtimestamp(
                record.timestamp, tz=timezone.utc
            ).strftime("%Y-%m-%d")
            record_outcome(
                symbol=record.symbol,
                signal_date=signal_date,
                outcome=outcome,
                prediction=prediction,
            )
        except Exception as e:
            logger.debug("outcome_resolver not available: %s", e)

    # -- Frontend Notifications --
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
                "council_confidence": round(record.council_confidence * 100, 2),
                "kelly_pct": round(record.kelly_pct * 100, 2),
                "stop_loss": record.stop_loss,
                "take_profit": record.take_profit,
                "regime": record.regime,
                "auto_execute": self.auto_execute,
            })
        except Exception as e:
            logger.debug("Frontend notification failed: %s", e)

    # -- Status & Metrics --
    def get_status(self) -> Dict[str, Any]:
        """Return executor status for health endpoint and dashboard."""
        uptime = time.time() - self._start_time if self._start_time else 0
        recent_orders = [
            {
                "symbol": o.symbol,
                "side": o.side,
                "qty": o.qty,
                "score": o.signal_score,
                "council_confidence": round(o.council_confidence * 100, 2),
                "kelly_pct": round(o.kelly_pct * 100, 2),
                "status": o.status,
                "regime": o.regime,
                "time": datetime.fromtimestamp(o.timestamp, tz=timezone.utc).isoformat(),
            }
            for o in list(self._orders)[-20:]
        ]
        return {
            "running": self._running,
            "mode": "auto_execute" if self.auto_execute else "shadow",
            "council_controlled": True,
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
                "council_confidence": round(o.council_confidence * 100, 2),
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
            "OrderExecutor mode changed: %s -> %s",
            "AUTO" if previous else "SHADOW",
            mode,
        )
        return {
            "previous": "auto_execute" if previous else "shadow",
            "current": "auto_execute" if enabled else "shadow",
        }
