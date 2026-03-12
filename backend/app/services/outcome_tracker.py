"""OutcomeTracker — closes the feedback loop by tracking position outcomes.

Monitors open positions (real Alpaca + shadow), detects closes, computes
actual PnL, and feeds results back to:
  - council/feedback_loop.py → agent weight tuning
  - ml_engine/outcome_resolver.py → ML accuracy tracking
  - Kelly calibration → replaces heuristic win_rate with real data

Architecture:
    order.submitted event → OutcomeTracker._on_order()
        → tracks open position with entry price, side, qty, signal_score
    Position poll loop (every 30s):
        → checks Alpaca positions / shadow exit conditions
        → on close: compute PnL, r_multiple
        → feed to feedback_loop.record_outcome()
        → feed to outcome_resolver.record_outcome()
        → update rolling win/loss stats for Kelly calibration
"""
import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.services.database import db_service

logger = logging.getLogger(__name__)

CONFIG_KEY = "outcome_tracker"


class OutcomeResolutionStatus(str, Enum):
    """Explicit outcome state for integrity and learning."""
    PENDING = "pending"
    RESOLVED = "resolved"
    TIMEOUT_UNRESOLVED = "timeout_unresolved"
    UNRESOLVED_MISSING_DATA = "unresolved_missing_data"


@dataclass
class TrackedPosition:
    """A position being tracked for outcome resolution."""
    order_id: str
    symbol: str
    side: str
    qty: int
    entry_price: float
    signal_score: float
    kelly_pct: float
    regime: str
    stop_loss: Optional[float]
    take_profit: Optional[float]
    is_shadow: bool
    opened_at: float  # time.time()
    council_decision_id: str = ""  # for learning-loop: match outcome to council decision
    # Filled when closed:
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    r_multiple: float = 0.0
    closed_at: Optional[float] = None
    close_reason: str = ""  # "take_profit", "stop_loss", "manual", "timeout", "timeout_censored", "position_gone"
    is_censored: bool = False  # True = do not count toward win/loss/Kelly/weights
    resolution_status: str = OutcomeResolutionStatus.RESOLVED.value  # pending|resolved|timeout_unresolved|unresolved_missing_data
    retry_scheduled_at: Optional[float] = None  # for unresolved_missing_data retry backoff

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "signal_score": self.signal_score,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "r_multiple": self.r_multiple,
            "is_shadow": self.is_shadow,
            "close_reason": self.close_reason,
            "is_censored": self.is_censored,
            "resolution_status": self.resolution_status,
            "retry_scheduled_at": self.retry_scheduled_at,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "council_decision_id": self.council_decision_id,
        }


class OutcomeTracker:
    """Tracks positions from entry to exit and feeds outcomes back."""

    POLL_INTERVAL = 30  # seconds
    SHADOW_MAX_HOLD = 5 * 24 * 3600  # 5 days max for shadow positions
    MAX_HISTORY = 2000

    # Stale threshold for shadow exit price (seconds)
    SHADOW_PRICE_STALE_SEC = 300

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._open_positions: Dict[str, TrackedPosition] = {}  # order_id -> position
        self._closed: deque = deque(maxlen=self.MAX_HISTORY)
        self._stats = self._load_stats()
        self._price_cache = None  # PriceCacheService, set in start()

    def _load_stats(self) -> Dict[str, Any]:
        """Load persistent stats from DB."""
        saved = db_service.get_config(CONFIG_KEY)
        if saved:
            return saved
        return {
            "total_tracked": 0,
            "total_resolved": 0,
            "wins": 0,
            "losses": 0,
            "scratches": 0,
            "total_pnl": 0.0,
            "win_rate": 0.5,
            "avg_win_pct": 0.035,
            "avg_loss_pct": 0.015,
            "avg_r_multiple": 0.0,
            "resolved_history": [],  # Last N outcomes for Kelly
            "shadow_price_stale_count": 0,
            "shadow_exit_checks_skipped_due_to_no_price": 0,
        }

    def _save_stats(self) -> None:
        """Persist stats to DB."""
        db_service.set_config(CONFIG_KEY, self._stats)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        if self._bus:
            await self._bus.subscribe("order.submitted", self._on_order)
            await self._bus.subscribe("order.filled", self._on_fill)
            try:
                from app.services.price_cache_service import get_price_cache
                self._price_cache = get_price_cache(self._bus)
                await self._price_cache.start()
            except Exception as e:
                logger.debug("PriceCacheService not available: %s", e)

        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info(
            "OutcomeTracker started — win_rate=%.2f avg_win=%.3f avg_loss=%.3f",
            self._stats["win_rate"],
            self._stats["avg_win_pct"],
            self._stats["avg_loss_pct"],
        )

    async def stop(self) -> None:
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        self._save_stats()
        logger.info("OutcomeTracker stopped")

    # ── Event Handlers ───────────────────────────────────────────────────────

    async def _on_order(self, data: Dict[str, Any]) -> None:
        """Handle order.submitted — start tracking this position."""
        order_id = data.get("order_id", "")
        if not order_id or order_id in self._open_positions:
            return

        is_shadow = data.get("source", "").endswith("_shadow")
        entry_price = data.get("price", 0)
        if not entry_price:
            return

        pos = TrackedPosition(
            order_id=order_id,
            symbol=data.get("symbol", ""),
            side=data.get("side", "buy"),
            qty=data.get("qty", 0),
            entry_price=entry_price,
            signal_score=data.get("signal_score", 0),
            kelly_pct=data.get("kelly_pct", 0),
            regime=data.get("regime", ""),
            stop_loss=data.get("stop_loss"),
            take_profit=data.get("take_profit"),
            is_shadow=is_shadow,
            opened_at=data.get("timestamp", time.time()),
            council_decision_id=data.get("council_decision_id", ""),
        )
        self._open_positions[order_id] = pos
        self._stats["total_tracked"] += 1
        logger.info(
            "[LEARNING-TRACE] OutcomeTracker._on_order order_id=%s symbol=%s council_decision_id=%s",
            order_id, pos.symbol, pos.council_decision_id or "(none)",
        )
        logger.info(
            "Tracking %s position: %s %s @ $%.2f (SL=$%.2f, TP=$%.2f)",
            "shadow" if is_shadow else "live",
            pos.symbol, pos.side, pos.entry_price,
            pos.stop_loss or 0, pos.take_profit or 0,
        )

    async def _on_fill(self, data: Dict[str, Any]) -> None:
        """Handle order.filled — update entry price to actual fill price."""
        order_id = data.get("order_id", "")
        fill_price = data.get("fill_price", 0)
        if order_id in self._open_positions and fill_price > 0:
            self._open_positions[order_id].entry_price = fill_price

    # ── Poll Loop ────────────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        """Periodically check positions for closes."""
        while self._running:
            try:
                await self._check_positions()
            except Exception as e:
                logger.error("OutcomeTracker poll error: %s", e)
            await asyncio.sleep(self.POLL_INTERVAL)

    async def _check_positions(self) -> None:
        """Check all tracked positions for close conditions."""
        if not self._open_positions:
            return

        # Get current Alpaca positions
        alpaca_positions = {}
        try:
            from app.services.alpaca_service import alpaca_service
            positions = await alpaca_service.get_positions()
            if positions:
                for p in positions:
                    sym = p.get("symbol", "")
                    alpaca_positions[sym] = p
        except Exception as e:
            logger.debug("Could not fetch Alpaca positions: %s", e)

        # Get current prices for shadow positions: PriceCache first, then REST fallback
        symbols_needed = [
            pos.symbol for pos in self._open_positions.values()
            if pos.is_shadow and pos.symbol not in alpaca_positions
        ]
        current_prices = {}
        if symbols_needed and self._price_cache:
            current_prices = self._price_cache.get_prices(symbols_needed)
        if symbols_needed and len(current_prices) < len(symbols_needed):
            try:
                rest_prices = await self._get_current_prices(symbols_needed)
                for k, v in rest_prices.items():
                    if k not in current_prices and v and v > 0:
                        current_prices[k] = v
            except Exception:
                pass

        closed_ids = []
        now = time.time()

        for order_id, pos in self._open_positions.items():
            if pos.is_shadow:
                # Shadow position: check SL/TP/timeout
                price = current_prices.get(pos.symbol)
                if price is not None and price > 0:
                    # Optionally track stale usage for telemetry
                    if self._price_cache and self._price_cache.is_stale(
                        pos.symbol, max_age_sec=self.SHADOW_PRICE_STALE_SEC
                    ):
                        self._stats["shadow_price_stale_count"] = (
                            self._stats.get("shadow_price_stale_count", 0) + 1
                        )
                    closed = self._check_shadow_exit(pos, price, now)
                    if closed:
                        closed_ids.append(order_id)
                elif now - pos.opened_at > self.SHADOW_MAX_HOLD:
                    # Timeout — policy from env: timeout_censored (recommended) or mark_to_market
                    self._resolve_shadow_timeout(pos, now, last_known_price=None)
                    closed_ids.append(order_id)
                else:
                    # No price available for this shadow symbol — skip exit check this cycle
                    self._stats["shadow_exit_checks_skipped_due_to_no_price"] = (
                        self._stats.get("shadow_exit_checks_skipped_due_to_no_price", 0) + 1
                    )
                    try:
                        from app.core.metrics import counter_inc
                        counter_inc("outcome_missing_data_total", {})
                    except Exception:
                        pass
            else:
                # Real position: check if still in Alpaca
                if pos.symbol not in alpaca_positions:
                    # Position is gone — it was closed (bracket SL/TP hit, or manual)
                    # Try to get the close price from closed orders
                    exit_price = await self._get_close_price(pos)
                    pos.exit_price = exit_price or pos.entry_price
                    pos.close_reason = "position_gone"
                    self._resolve_position(pos)
                    closed_ids.append(order_id)
                else:
                    # Still open — check unrealized P&L from Alpaca
                    ap = alpaca_positions[pos.symbol]
                    unrealized_pnl = float(ap.get("unrealized_pl", 0))
                    current_price = float(ap.get("current_price", pos.entry_price))
                    # Update entry price from Alpaca if we have better data
                    cost_basis = float(ap.get("avg_entry_price", 0))
                    if cost_basis > 0:
                        pos.entry_price = cost_basis

        # Remove closed positions
        for oid in closed_ids:
            pos = self._open_positions.pop(oid, None)
            if pos:
                self._closed.append(pos)

    def _check_shadow_exit(self, pos: TrackedPosition, current_price: float, now: float) -> bool:
        """Check if a shadow position should be closed."""
        if pos.side == "buy":
            # Stop loss hit
            if pos.stop_loss and current_price <= pos.stop_loss:
                pos.exit_price = pos.stop_loss
                pos.close_reason = "stop_loss"
                self._resolve_position(pos)
                return True
            # Take profit hit
            if pos.take_profit and current_price >= pos.take_profit:
                pos.exit_price = pos.take_profit
                pos.close_reason = "take_profit"
                self._resolve_position(pos)
                return True
        else:  # sell/short
            if pos.stop_loss and current_price >= pos.stop_loss:
                pos.exit_price = pos.stop_loss
                pos.close_reason = "stop_loss"
                self._resolve_position(pos)
                return True
            if pos.take_profit and current_price <= pos.take_profit:
                pos.exit_price = pos.take_profit
                pos.close_reason = "take_profit"
                self._resolve_position(pos)
                return True

        # Timeout (policy: timeout_censored or mark_to_market with last known price)
        if now - pos.opened_at > self.SHADOW_MAX_HOLD:
            self._resolve_shadow_timeout(pos, now, last_known_price=current_price)
            return True

        return False

    def _resolve_shadow_timeout(
        self, pos: TrackedPosition, now: float, last_known_price: Optional[float] = None
    ) -> None:
        """Resolve shadow position on timeout per SHADOW_TIMEOUT_POLICY (censor|mark_to_market|scratch)."""
        import os
        policy = (
            os.getenv("SHADOW_TIMEOUT_POLICY") or
            os.getenv("OUTCOME_TIMEOUT_POLICY") or
            "censor"
        ).strip().lower()
        # Map legacy/settings to policy
        if policy in ("timeout_censored", "scratch"):
            policy = "censor"
        try:
            from app.core.config import settings
            if policy == "censor" and hasattr(settings, "OUTCOME_TIMEOUT_POLICY"):
                leg = getattr(settings, "OUTCOME_TIMEOUT_POLICY", "").strip().lower()
                if leg == "mark_to_market":
                    policy = "mark_to_market"
        except Exception:
            pass

        if policy == "mark_to_market" and last_known_price is not None and last_known_price > 0:
            pos.exit_price = last_known_price
            pos.close_reason = "timeout"
            pos.is_censored = False
            pos.resolution_status = OutcomeResolutionStatus.RESOLVED.value
        else:
            # timeout_censored (recommended), or mark_to_market with no price
            pos.exit_price = pos.entry_price
            pos.close_reason = "timeout_censored"
            pos.is_censored = True
            pos.resolution_status = OutcomeResolutionStatus.TIMEOUT_UNRESOLVED.value
        self._resolve_position(pos)

    def _resolve_position(self, pos: TrackedPosition) -> None:
        """Compute PnL and feed outcome to feedback systems. Censored outcomes skip stats and learning."""
        pos.closed_at = time.time()

        # Compute PnL (always for payload)
        if pos.side == "buy":
            pos.pnl = (pos.exit_price - pos.entry_price) * pos.qty
            pos.pnl_pct = (pos.exit_price - pos.entry_price) / pos.entry_price if pos.entry_price else 0
        else:
            pos.pnl = (pos.entry_price - pos.exit_price) * pos.qty
            pos.pnl_pct = (pos.entry_price - pos.exit_price) / pos.entry_price if pos.entry_price else 0

        # Compute R-multiple (risk-adjusted return)
        if pos.stop_loss and pos.entry_price:
            risk_per_share = abs(pos.entry_price - pos.stop_loss)
            if risk_per_share > 0:
                gain_per_share = pos.exit_price - pos.entry_price if pos.side == "buy" else pos.entry_price - pos.exit_price
                pos.r_multiple = gain_per_share / risk_per_share
            else:
                pos.r_multiple = 0.0
        else:
            pos.r_multiple = pos.pnl_pct / 0.02 if pos.pnl_pct else 0.0  # Assume 2% risk

        # Classify outcome (for logging and for non-censored path)
        if pos.pnl_pct > 0.001:
            outcome = "win"
        elif pos.pnl_pct < -0.001:
            outcome = "loss"
        else:
            outcome = "scratch"

        if pos.is_censored:
            # Do NOT update win/loss/Kelly stats or learning systems
            try:
                from app.core.metrics import counter_inc
                counter_inc("outcome_resolution_total", {"status": "censored"})
            except Exception:
                pass
            logger.info(
                "Position RESOLVED (CENSORED): %s %s reason=%s resolution_status=%s — excluded from win/loss/Kelly/weights",
                pos.symbol, pos.side, pos.close_reason, pos.resolution_status,
            )
            if self._bus:
                asyncio.create_task(self._bus.publish("outcome.resolved", pos.to_dict()))
            return

        try:
            from app.core.metrics import counter_inc
            counter_inc("outcome_resolution_total", {"status": "resolved"})
        except Exception:
            pass

        # Update rolling stats (non-censored only)
        self._stats["total_resolved"] += 1
        self._stats["total_pnl"] += pos.pnl
        if outcome == "win":
            self._stats["wins"] += 1
        elif outcome == "loss":
            self._stats["losses"] += 1
        else:
            self._stats["scratches"] += 1

        # Update resolved history for Kelly (non-censored only)
        history = self._stats.get("resolved_history", [])
        history.append({
            "symbol": pos.symbol,
            "side": pos.side,
            "pnl_pct": round(pos.pnl_pct, 6),
            "r_multiple": round(pos.r_multiple, 3),
            "outcome": outcome,
            "signal_score": pos.signal_score,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        })
        self._stats["resolved_history"] = history[-500:]  # Keep last 500

        # Recompute Kelly parameters from real data
        self._recompute_kelly_params()
        self._save_stats()

        logger.info(
            "Position RESOLVED: %s %s → %s PnL=$%.2f (%.2f%%) R=%.2fR reason=%s",
            pos.symbol, pos.side, outcome, pos.pnl, pos.pnl_pct * 100,
            pos.r_multiple, pos.close_reason,
        )

        # Feed to knowledge system — update memories with trade outcome
        try:
            from app.knowledge.memory_bank import get_memory_bank
            bank = get_memory_bank()
            bank.update_outcome(
                trade_id=pos.order_id,
                r_multiple=pos.r_multiple,
                was_correct=(outcome == "win"),
            )
        except Exception as e:
            logger.debug("Knowledge memory outcome update error: %s", e)

        # Extract heuristics + rebuild knowledge graph every 10 resolved trades
        if self._stats["total_resolved"] % 10 == 0 and self._stats["total_resolved"] >= 10:
            try:
                from app.knowledge.heuristic_engine import get_heuristic_engine
                from app.knowledge.knowledge_graph import get_knowledge_graph
                he = get_heuristic_engine()
                kg = get_knowledge_graph()
                # Extract heuristics from each agent's memory bank
                new_heuristics = 0
                for agent_name in [
                    "market_perception", "regime", "rsi", "hypothesis",
                    "strategy", "risk", "flow_perception",
                ]:
                    extracted = he.extract_heuristics(agent_name)
                    new_heuristics += len(extracted)
                # Apply temporal decay based on cognitive mode
                he.apply_temporal_decay()
                # Rebuild cross-agent knowledge graph edges
                new_edges = kg.build_edges()
                if new_heuristics or new_edges:
                    logger.info(
                        "Knowledge refresh after %d outcomes: %d new heuristics, %d new edges",
                        self._stats["total_resolved"], new_heuristics, new_edges,
                    )
            except Exception as e:
                logger.debug("Knowledge refresh error: %s", e)

        # Feed to council feedback loop + trigger weight update (use council_decision_id for matching)
        try:
            from app.council.feedback_loop import record_outcome as council_record, update_agent_weights
            trade_id_for_learning = pos.council_decision_id or pos.order_id
            logger.info(
                "[LEARNING-TRACE] OutcomeTracker._resolve_position feeding outcome trade_id=%s symbol=%s outcome=%s",
                trade_id_for_learning, pos.symbol, outcome,
            )
            council_record(
                trade_id=trade_id_for_learning,
                symbol=pos.symbol,
                outcome=outcome,
                r_multiple=pos.r_multiple,
            )
            # Fire learning update on EVERY resolved outcome (not every 5th).
            # Pass outcome data so WeightLearner.update_from_outcome() fires.
            outcome_data = {
                "trade_id": trade_id_for_learning,
                "symbol": pos.symbol,
                "outcome": outcome,
                "r_multiple": pos.r_multiple,
                "pnl": getattr(pos, "pnl", 0.0),
                "confidence": getattr(pos, "confidence", 1.0),
            }
            new_weights = update_agent_weights(outcome=outcome_data)
            if new_weights:
                logger.info(
                    "Agent weights updated: %s %s (R=%.2f)",
                    pos.symbol, outcome, pos.r_multiple,
                )
        except Exception as e:
            logger.debug("Council feedback error: %s", e)

        # Postmortem feedback loop: persist closed-trade record with council context
        try:
            from app.data.duckdb_storage import duckdb_store
            from app.council.weight_learner import get_weight_learner
            decision_id = pos.council_decision_id or pos.order_id
            resolved_at_utc = datetime.now(timezone.utc).isoformat()
            decision_ctx = None
            try:
                learner = get_weight_learner()
                decision_ctx = learner.get_decision_by_trade_id(decision_id)
            except Exception:
                pass
            direction = getattr(pos, "side", "buy")
            confidence = 1.0
            agent_votes = []
            blackboard_snapshot = {}
            if decision_ctx:
                direction = decision_ctx.get("final_direction", direction)
                confidence = decision_ctx.get("final_confidence", confidence)
                agent_votes = [
                    {
                        "agent_name": v.get("agent_name", ""),
                        "direction": v.get("direction", "hold"),
                        "confidence": v.get("confidence", 0),
                        "weight": v.get("weight", 1.0),
                    }
                    for v in decision_ctx.get("votes", [])
                ]
                blackboard_snapshot = decision_ctx.get("blackboard_snapshot") or {}
            postmortem = {
                "id": decision_id,
                "council_decision_id": decision_id,
                "symbol": pos.symbol,
                "direction": direction,
                "confidence": confidence,
                "entry_price": pos.entry_price,
                "exit_price": pos.exit_price,
                "pnl": pos.pnl,
                "agent_votes": agent_votes,
                "blackboard_snapshot": blackboard_snapshot,
                "critic_analysis": "",
                "resolved_at": resolved_at_utc,
            }
            duckdb_store.insert_postmortem(postmortem)
            logger.debug("Postmortem recorded for %s %s (decision_id=%s)", pos.symbol, outcome, decision_id[:16] if decision_id else "")
        except Exception as e:
            logger.debug("Postmortem write failed: %s", e)

        # Wire SelfAwareness Bayesian tracking (Audit Bug #8)
        try:
            from app.council.self_awareness import get_self_awareness
            sa = get_self_awareness()
            profitable = outcome == "win"
            # Update all agents that participated — look up from feedback store
            agent_votes = getattr(pos, 'agent_votes', None) or {}
            if agent_votes:
                for agent_name, voted_direction in agent_votes.items():
                    sa.record_trade_outcome(agent_name, profitable)
            else:
                # No per-agent votes available; update core agents collectively
                for agent_name in [
                    "market_perception", "flow_perception", "regime", "intermarket",
                    "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
                    "hypothesis", "strategy", "risk", "execution",
                ]:
                    sa.record_trade_outcome(agent_name, profitable)
        except Exception as e:
            logger.debug("SelfAwareness tracking failed: %s", e)

        # Feed to adaptive LLM router — update accuracy for participating agents
        try:
            from app.services.adaptive_router import get_hybrid_router
            hybrid = get_hybrid_router()
            was_correct = outcome == "win"
            # Update all agents that participated in this decision
            # Find the actual routing metadata from the matching decision
            provider_map = {}
            try:
                from app.council.feedback_loop import _get_store
                store = _get_store()
                for d in reversed(store.get("decisions", [])):
                    if d.get("symbol", "").upper() == pos.symbol.upper():
                        # Extract per-agent provider from stored routing metadata
                        for vote in d.get("votes", []):
                            name = vote.get("agent_name", "")
                            meta = vote.get("metadata", {})
                            if isinstance(meta, dict) and "provider" in meta:
                                provider_map[name] = meta["provider"]
                        break
            except Exception:
                pass

            for agent_name in [
                "market_perception", "flow_perception", "regime", "intermarket",
                "social_perception", "news_catalyst", "youtube_knowledge",
                "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
                "hypothesis", "strategy", "risk", "execution", "critic",
            ]:
                provider_value = provider_map.get(agent_name, "default")
                hybrid.update_accuracy(agent_name, provider_value, was_correct)
        except Exception as e:
            logger.debug("Adaptive router accuracy update error: %s", e)

        # Feed to ML outcome resolver
        try:
            from app.modules.ml_engine.outcome_resolver import record_outcome as ml_record
            signal_date = datetime.fromtimestamp(pos.opened_at, tz=timezone.utc).strftime("%Y-%m-%d")
            ml_record(
                symbol=pos.symbol,
                signal_date=signal_date,
                outcome=1 if outcome == "win" else 0,
                prediction=1 if pos.signal_score >= 50 else 0,
            )
        except Exception as e:
            logger.debug("ML outcome resolver error: %s", e)

        # Publish event
        if self._bus:
            asyncio.create_task(self._bus.publish("outcome.resolved", pos.to_dict()))

    def _recompute_kelly_params(self) -> None:
        """Recompute win_rate, avg_win_pct, avg_loss_pct from resolved history."""
        history = self._stats.get("resolved_history", [])
        if len(history) < 5:
            return  # Not enough data

        wins = [h for h in history if h["outcome"] == "win"]
        losses = [h for h in history if h["outcome"] == "loss"]
        total = len(wins) + len(losses)
        if total == 0:
            return

        self._stats["win_rate"] = round(len(wins) / total, 4)

        if wins:
            self._stats["avg_win_pct"] = round(
                sum(h["pnl_pct"] for h in wins) / len(wins), 6
            )
        if losses:
            self._stats["avg_loss_pct"] = round(
                abs(sum(h["pnl_pct"] for h in losses) / len(losses)), 6
            )

        r_all = [h["r_multiple"] for h in history if h["r_multiple"] != 0]
        if r_all:
            self._stats["avg_r_multiple"] = round(sum(r_all) / len(r_all), 3)

                    # Per-side Kelly stats for short/long symmetry
        for side_val in ("buy", "sell"):
            side_history = [h for h in history if h.get("side") == side_val]
            side_wins = [h for h in side_history if h["outcome"] == "win"]
            side_losses = [h for h in side_history if h["outcome"] == "loss"]
            side_total = len(side_wins) + len(side_losses)
            if side_total >= 5:
                self._stats[f"win_rate_{side_val}"] = round(len(side_wins) / side_total, 4)
                if side_wins:
                    self._stats[f"avg_win_pct_{side_val}"] = round(
                        sum(h["pnl_pct"] for h in side_wins) / len(side_wins), 6
                    )
                if side_losses:
                    self._stats[f"avg_loss_pct_{side_val}"] = round(
                        abs(sum(h["pnl_pct"] for h in side_losses) / len(side_losses)), 6
                    )

    async def _get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for symbols from DuckDB or Alpaca."""
        def _fetch_prices_sync(syms):
            result = {}
            try:
                from app.data.duckdb_storage import duckdb_store
                conn = duckdb_store.get_thread_cursor()
                for sym in syms:
                    try:
                        row = conn.execute(
                            "SELECT close FROM daily_ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 1",
                            [sym],
                        ).fetchone()
                        if row:
                            result[sym] = float(row[0])
                    except Exception:
                        pass
            except Exception:
                pass
            return result

        prices = await asyncio.to_thread(_fetch_prices_sync, symbols)

        # Fallback: try Alpaca quotes
        if len(prices) < len(symbols):
            try:
                from app.services.alpaca_service import alpaca_service
                for sym in symbols:
                    if sym not in prices:
                        try:
                            quote = await alpaca_service.get_latest_quote(sym)
                            if quote:
                                ask = float(quote.get("ap", 0))
                                bid = float(quote.get("bp", 0))
                                if ask and bid:
                                    prices[sym] = (ask + bid) / 2
                        except Exception:
                            pass
            except Exception:
                pass

        return prices

    async def _get_close_price(self, pos: TrackedPosition) -> Optional[float]:
        """Try to find the actual close price from Alpaca order history."""
        try:
            from app.services.alpaca_service import alpaca_service
            order_id = pos.order_id
            if order_id.startswith("shadow-"):
                return None
            order = await alpaca_service.get_order(order_id)
            if order and order.get("status") == "filled":
                return float(order.get("filled_avg_price", 0)) or None
            # Check for related bracket leg fills
            legs = order.get("legs", []) if order else []
            for leg in legs:
                if leg.get("status") == "filled":
                    return float(leg.get("filled_avg_price", 0)) or None
        except Exception:
            pass
        return None

    # ── Public API ───────────────────────────────────────────────────────────

    def get_kelly_params(self) -> Dict[str, float]:
        """Return calibrated Kelly parameters from real outcomes."""
        return {
            "win_rate": self._stats["win_rate"],
            "avg_win_pct": self._stats["avg_win_pct"],
            "avg_loss_pct": self._stats["avg_loss_pct"],
            "sample_size": self._stats["total_resolved"],
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "open_positions": len(self._open_positions),
            "total_tracked": self._stats["total_tracked"],
            "total_resolved": self._stats["total_resolved"],
            "wins": self._stats["wins"],
            "losses": self._stats["losses"],
            "scratches": self._stats["scratches"],
            "win_rate": self._stats["win_rate"],
            "total_pnl": round(self._stats["total_pnl"], 2),
            "avg_win_pct": self._stats["avg_win_pct"],
            "avg_loss_pct": self._stats["avg_loss_pct"],
            "avg_r_multiple": self._stats["avg_r_multiple"],
            "kelly_calibrated": self._stats["total_resolved"] >= 10,
            "shadow_price_stale_count": self._stats.get("shadow_price_stale_count", 0),
            "shadow_exit_checks_skipped_due_to_no_price": self._stats.get(
                "shadow_exit_checks_skipped_due_to_no_price", 0
            ),
        }

    def get_open_positions(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._open_positions.values()]

    def get_closed_positions(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._closed[-limit:]]


# Module-level singleton
_tracker: Optional[OutcomeTracker] = None


def get_outcome_tracker() -> OutcomeTracker:
    global _tracker
    if _tracker is None:
        _tracker = OutcomeTracker()
    return _tracker
