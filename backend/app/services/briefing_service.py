"""Morning briefing service — top trade ideas with entry/stop/target for TradingView.

Uses regime-adaptive thresholds (55/65/75) and Kelly-ranked signals.
Produces trade ideas with ATR-based stops and R-multiple targets (2R, 3R).
BriefingService orchestrates: morning briefing, position review, weekly review, Slack formatting.

Used by GET /api/v1/briefing/morning, /positions, /weekly, /tradingview, /push-webhook.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.config.regime_thresholds import get_regime_config

logger = logging.getLogger(__name__)

# Default ATR proxy as fraction of price when no ATR in data (2%)
DEFAULT_ATR_PCT = 0.02
# R-multiples for targets
R_TARGET1 = 2.0
R_TARGET2 = 3.0
# Regime display mapping (HMM/bayesian names -> brief labels)
REGIME_TO_STATE = {
    "trending_bull": "bull",
    "low_vol_grind": "bull",
    "BULLISH": "bull",
    "GREEN": "bull",
    "trending_bear": "bear",
    "BEARISH": "bear",
    "RED": "bear",
    "mean_revert": "sideways",
    "transition": "sideways",
    "NEUTRAL": "sideways",
    "YELLOW": "sideways",
    "high_vol_crisis": "crisis",
    "CRISIS": "crisis",
}


def _compute_stop_targets(
    entry: float,
    direction: str,
    stop: float = 0.0,
    atr_pct: float = DEFAULT_ATR_PCT,
) -> tuple:
    """Compute stop and target1/target2 from entry. Returns (stop, target1, target2)."""
    if entry <= 0:
        return 0.0, 0.0, 0.0
    if stop and stop > 0 and (
        (direction.lower() in ("long", "buy") and stop < entry)
        or (direction.lower() in ("short", "sell") and stop > entry)
    ):
        r = abs(entry - stop)
    else:
        r = entry * atr_pct
    if direction.lower() in ("short", "sell"):
        target1 = entry - R_TARGET1 * r
        target2 = entry - R_TARGET2 * r
        stop_val = stop if stop > 0 else entry + r
    else:
        target1 = entry + R_TARGET1 * r
        target2 = entry + R_TARGET2 * r
        stop_val = stop if stop > 0 else entry - r
    return stop_val, target1, target2


class BriefingService:
    """Orchestrator for morning briefing, position review, weekly review, and Slack formatting."""

    def __init__(self):
        self._last_briefing_time: Optional[str] = None

    def format_tradingview_levels(
        self,
        signal: Dict[str, Any],
        atr: float,
    ) -> Dict[str, Any]:
        """Compute entry_zone, stop_loss, target_1, target_2, position_size_pct from signal.

        entry_zone: [current_price * 0.998, current_price * 1.002]
        stop: entry - (2.0 * ATR) for longs, entry + (2.0 * ATR) for shorts
        target_1: entry + (2 * risk), target_2: entry + (3 * risk)
        """
        entry_price = float(signal.get("entry") or signal.get("price") or 0)
        if entry_price <= 0:
            return {}
        direction = (signal.get("direction") or signal.get("action") or "buy").lower()
        if direction == "long":
            direction = "buy"
        elif direction == "short":
            direction = "sell"
        atr_val = atr if atr and atr > 0 else entry_price * DEFAULT_ATR_PCT
        risk = 2.0 * atr_val
        if direction == "sell":
            stop_loss = entry_price + risk
            target_1 = entry_price - R_TARGET1 * risk
            target_2 = entry_price - R_TARGET2 * risk
        else:
            stop_loss = entry_price - risk
            target_1 = entry_price + R_TARGET1 * risk
            target_2 = entry_price + R_TARGET2 * risk
        entry_zone = [
            round(entry_price * 0.998, 2),
            round(entry_price * 1.002, 2),
        ]
        risk_per_share = abs(entry_price - stop_loss)
        reward_risk = (abs(target_1 - entry_price) / risk_per_share) if risk_per_share > 0 else 0

        position_size_pct = 0.0
        try:
            from app.services.kelly_position_sizer import KellyPositionSizer
            sizer = KellyPositionSizer(max_allocation=0.10)
            score = signal.get("score") or 65
            conf = min(1.0, max(0.0, (score / 100.0) if score > 1 else score))
            kelly = sizer.calculate(
                win_rate=conf,
                avg_win_pct=0.035,
                avg_loss_pct=0.015,
            )
            position_size_pct = round(kelly.final_pct * 100, 2)
        except Exception as e:
            logger.debug("Kelly sizer in format_tradingview_levels: %s", e)

        return {
            "entry_zone": entry_zone,
            "stop_loss": round(stop_loss, 2),
            "target_1": round(target_1, 2),
            "target_2": round(target_2, 2),
            "position_size_pct": position_size_pct,
            "risk_per_share": round(risk_per_share, 2),
            "reward_risk_ratio": round(reward_risk, 2),
        }

    async def generate_morning_briefing(
        self,
        as_of: Optional[date] = None,
        top_n: int = 5,
        notify_slack: bool = False,
        push_webhook: bool = False,
    ) -> Dict[str, Any]:
        """Generate full morning briefing: regime, portfolio, positions, trade_ideas, calendar.

        Filters signals: score >= regime threshold (GREEN=55, YELLOW=65, RED/CRISIS=75),
        confidence >= 0.4, excludes symbols with open positions, ranks by Kelly edge × confidence.
        """
        if as_of is None:
            as_of = date.today()
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat()

        # Regime from Bayesian regime or fallback
        regime_state = "bull"
        vix = 0.0
        regime_confidence = 0.5
        signal_threshold = 55
        try:
            from app.council.regime.bayesian_regime import get_bayesian_regime
            bayes = get_bayesian_regime()
            rd = bayes.to_dict()
            dom = rd.get("dominant_regime", "trending_bull")
            regime_state = REGIME_TO_STATE.get(dom, "sideways")
            regime_confidence = float(rd.get("dominant_probability", 0.5))
            regime_key = "GREEN" if regime_state == "bull" else "YELLOW" if regime_state == "sideways" else "RED"
            if regime_state == "crisis":
                regime_key = "CRISIS"
            cfg = get_regime_config(regime_key)
            signal_threshold = int(cfg.get("gate_threshold", 65))
        except Exception as e:
            logger.debug("Regime from bayesian_regime: %s", e)
        try:
            from app.services.fred_service import get_fred_service
            fred = get_fred_service()
            if hasattr(fred, "get_latest_macro_snapshot"):
                snap = await fred.get_latest_macro_snapshot()
                vix = float(snap.get("vix", 0) or 0)
        except Exception as e:
            logger.debug("VIX from FRED: %s", e)

        # Portfolio: heat, value, daily PnL, drawdown
        portfolio_value = 100000.0
        heat_pct = 0.0
        open_positions_count = 0
        daily_pnl = 0.0
        drawdown_pct = 0.0
        try:
            from app.services.alpaca_service import alpaca_service
            account = await alpaca_service.get_account()
            if account:
                portfolio_value = float(account.get("equity", 100000))
            positions = await alpaca_service.get_positions() or []
            open_positions_count = len(positions)
            total_mv = sum(abs(float(p.get("market_value", 0))) for p in positions)
            heat_pct = round((total_mv / portfolio_value * 100), 1) if portfolio_value > 0 else 0
            daily_pnl = sum(float(p.get("unrealized_pl", 0)) for p in positions)
        except Exception as e:
            logger.debug("Portfolio/positions for briefing: %s", e)
        try:
            from app.api.v1.risk import drawdown_check_status
            dd = await drawdown_check_status()
            daily_pct = float(dd.get("daily_pnl_pct", 0) or 0)
            drawdown_pct = round(min(0, daily_pct), 2)  # drawdown is negative when equity is down
        except Exception as e:
            logger.debug("Drawdown for briefing: %s", e)

        # Positions (enriched)
        positions_list: List[Dict[str, Any]] = []
        try:
            positions_list = await self.get_position_review()
        except Exception as e:
            logger.debug("Position review in briefing: %s", e)

        open_symbols = {p.get("symbol", "").upper() for p in positions_list}

        # Trade ideas from signals API
        ideas: List[Dict[str, Any]] = []
        try:
            from app.api.v1.signals import get_signals
            data = await get_signals(as_of=as_of)
        except Exception as e:
            logger.warning("Briefing get_signals failed: %s", e)
            data = {}
        if isinstance(data, dict):
            raw_signals = data.get("signals", [])
        else:
            raw_signals = getattr(data, "signals", []) or []
        for s in raw_signals:
            score = s.get("score") or 0
            if score < signal_threshold:
                continue
            symbol = (s.get("symbol") or "").upper()
            if not symbol or symbol in open_symbols:
                continue
            conf = (score / 100.0) if score > 1 else float(s.get("confidence", 0.5))
            if conf < 0.4:
                continue
            direction = (s.get("direction") or "LONG").upper()
            action = "buy" if direction == "LONG" else "sell"
            entry = float(s.get("entry") or 0)
            stop = float(s.get("stop") or 0)
            if entry <= 0:
                continue
            atr_proxy = entry * DEFAULT_ATR_PCT
            levels = self.format_tradingview_levels(
                {"entry": entry, "price": entry, "direction": action, "score": score},
                atr_proxy,
            )
            kelly_frac = levels.get("position_size_pct", 0) / 100.0
            ideas.append({
                "symbol": symbol,
                "direction": action,
                "score": round(score),
                "confidence": round(conf, 2),
                "kelly_fraction": round(kelly_frac, 4),
                "entry_zone": levels.get("entry_zone", [entry, entry]),
                "stop_loss": levels.get("stop_loss", 0),
                "target_1": levels.get("target_1", 0),
                "target_2": levels.get("target_2", 0),
                "position_size_pct": levels.get("position_size_pct", 0),
                "risk_per_share": levels.get("risk_per_share", 0),
                "reward_risk_ratio": levels.get("reward_risk_ratio", 2.0),
                "regime": regime_state,
                "council_decision_id": s.get("council_decision_id") or "",
                "top_agents": s.get("top_agents", []) or ["regime", "momentum", "flow"][:3],
                "risk_notes": f"Portfolio heat at {heat_pct}%",
            })
        ideas.sort(key=lambda x: (x.get("score") or 0) * (x.get("confidence") or 0), reverse=True)
        ideas = ideas[:top_n]

        # Calendar events (stub: could integrate earnings calendar)
        calendar_events: List[Dict[str, Any]] = []

        # Optional: push webhook and Slack
        webhook_sent = False
        slack_sent = False
        if push_webhook and ideas:
            try:
                from app.services.tradingview_bridge import get_tradingview_bridge
                bridge = get_tradingview_bridge()
                if hasattr(bridge, "push_signals"):
                    result = await bridge.push_signals(ideas)
                    webhook_sent = result.get("sent", False)
                else:
                    result = await bridge.push_signals_to_webhook(ideas)
                    webhook_sent = result.get("pushed_count", 0) > 0
            except Exception as e:
                logger.warning("Webhook push in briefing: %s", e)
        if notify_slack and ideas:
            try:
                from app.services.slack_notification_service import get_slack_service
                slack = get_slack_service()
                text = self.format_slack_briefing({
                    "regime": {"state": regime_state, "vix": vix, "confidence": regime_confidence, "signal_threshold": signal_threshold},
                    "portfolio": {"total_value": portfolio_value, "heat_pct": heat_pct, "open_positions": open_positions_count},
                    "positions": positions_list,
                    "trade_ideas": ideas,
                    "calendar_events": calendar_events,
                })
                if text and getattr(slack, "_post_message", None):
                    slack_sent = await slack._post_message(slack._default_channel or "#trade-alerts", text)
            except Exception as e:
                logger.warning("Slack briefing: %s", e)

        try:
            from app.core.message_bus import MessageBus
            bus = MessageBus.get_instance()
            await bus.publish("briefing.generated", {"timestamp": timestamp, "ideas_count": len(ideas)})
        except Exception as e:
            logger.debug("MessageBus briefing.generated: %s", e)

        self._last_briefing_time = timestamp
        return {
            "timestamp": timestamp,
            "regime": {
                "state": regime_state,
                "vix": vix,
                "confidence": round(regime_confidence, 2),
                "signal_threshold": signal_threshold,
            },
            "portfolio": {
                "total_value": round(portfolio_value, 2),
                "heat_pct": heat_pct,
                "open_positions": open_positions_count,
                "daily_pnl": round(daily_pnl, 2),
                "drawdown_pct": drawdown_pct,
            },
            "positions": positions_list,
            "trade_ideas": ideas,
            "calendar_events": calendar_events,
            "webhook_sent": webhook_sent,
            "slack_sent": slack_sent,
        }

    async def get_position_review(self) -> List[Dict[str, Any]]:
        """Enriched position list: unrealized P&L, R-multiple, days held, distance to stop, attention flags."""
        result: List[Dict[str, Any]] = []
        try:
            from app.services.alpaca_service import alpaca_service
            positions = await alpaca_service.get_positions() or []
        except Exception as e:
            logger.debug("get_position_review positions: %s", e)
            return result
        for p in positions:
            symbol = (p.get("symbol") or "").upper()
            qty = float(p.get("qty", 0))
            side = "long" if qty > 0 else "short"
            entry_price = float(p.get("avg_entry_price", 0))
            current_price = float(p.get("current_price") or p.get("market_value", 0) / abs(qty) if qty else 0)
            unrealized_pnl = float(p.get("unrealized_pl", 0))
            stop_loss = float(p.get("stop_loss") or 0)
            if not stop_loss and entry_price > 0:
                atr = entry_price * DEFAULT_ATR_PCT
                stop_loss = entry_price - 2 * atr if side == "long" else entry_price + 2 * atr
            risk_per_share = abs(entry_price - stop_loss) if stop_loss else entry_price * DEFAULT_ATR_PCT
            if risk_per_share > 0:
                if side == "long":
                    r_multiple = (current_price - entry_price) / risk_per_share
                else:
                    r_multiple = (entry_price - current_price) / risk_per_share
            else:
                r_multiple = 0.0
            days_held = 0
            try:
                from datetime import datetime
                opened = p.get("opened_at") or p.get("created_at")
                if opened:
                    if isinstance(opened, str) and "T" in opened:
                        opened_dt = datetime.fromisoformat(opened.replace("Z", "+00:00"))
                    else:
                        opened_dt = datetime.now(timezone.utc)
                    days_held = (datetime.now(timezone.utc) - opened_dt).days
            except Exception:
                pass
            dist_to_stop = abs(current_price - stop_loss) if stop_loss else 0
            near_stop = risk_per_share > 0 and (dist_to_stop / risk_per_share) <= 0.5
            # Regime vs direction: long in bear/crisis or short in bull may need review
            current_regime = "bull"
            try:
                from app.council.regime.bayesian_regime import get_bayesian_regime
                dom = get_bayesian_regime().to_dict().get("dominant_regime", "trending_bull")
                current_regime = REGIME_TO_STATE.get(dom, "sideways")
            except Exception:
                pass
            regime_mismatch = (
                (current_regime in ("bear", "crisis") and side == "long")
                or (current_regime == "bull" and side == "short")
            )
            needs_attention = near_stop or days_held > 18 or regime_mismatch
            attention_reason = None
            if near_stop:
                attention_reason = "within 0.5R of stop"
            elif days_held > 18:
                attention_reason = "held > 18 days"
            elif regime_mismatch:
                attention_reason = "regime changed since entry"
            result.append({
                "symbol": symbol,
                "direction": side,
                "entry_price": round(entry_price, 2),
                "current_price": round(current_price, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "r_multiple": round(r_multiple, 2),
                "days_held": days_held,
                "stop_loss": round(stop_loss, 2),
                "needs_attention": needs_attention,
                "attention_reason": attention_reason,
            })
        return result

    async def generate_weekly_review(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Weekly review: council decisions, trade outcomes, P&L, win rate, Brier, best/worst trades."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=7)
        total_pnl = 0.0
        win_count = 0
        total_trades = 0
        avg_r_multiple = 0.0
        max_drawdown = 0.0
        sharpe_approx = 0.0
        best_trades: List[Dict] = []
        worst_trades: List[Dict] = []
        regime_transitions: List[Dict] = []
        agent_brier: Dict[str, float] = {}
        try:
            from app.data.storage import get_conn
            conn = get_conn()
            try:
                df = conn.execute("""
                    SELECT * FROM trade_outcomes
                    WHERE exit_date >= ? AND exit_date <= ?
                """, [str(start_date), str(end_date)]).fetchdf()
                if df is not None and not df.empty and "pnl" in df.columns:
                    total_pnl = float(df["pnl"].sum())
                    total_trades = len(df)
                    wins = (df["pnl"] > 0).sum()
                    win_count = int(wins)
                    if "r_multiple" in df.columns:
                        avg_r_multiple = float(df["r_multiple"].mean())
                    for _, row in df.nlargest(5, "r_multiple").iterrows():
                        best_trades.append({"symbol": row.get("symbol"), "r_multiple": float(row.get("r_multiple", 0)), "pnl": float(row.get("pnl", 0))})
                    for _, row in df.nsmallest(5, "r_multiple").iterrows():
                        worst_trades.append({"symbol": row.get("symbol"), "r_multiple": float(row.get("r_multiple", 0)), "pnl": float(row.get("pnl", 0))})
            except Exception as e:
                logger.debug("Weekly review trade_outcomes: %s", e)
            try:
                from app.council.calibration import get_calibration_tracker
                cal = get_calibration_tracker()
                agent_brier = cal.get_all_calibration() or {}
                agent_brier = {k: v.get("brier_score") for k, v in agent_brier.items() if v.get("brier_score") is not None}
            except Exception as e:
                logger.debug("Weekly review Brier: %s", e)
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Weekly review DuckDB: %s", e)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        return {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_pnl": round(total_pnl, 2),
            "win_rate_pct": round(win_rate, 1),
            "total_trades": total_trades,
            "avg_r_multiple": round(avg_r_multiple, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "sharpe_approx": round(sharpe_approx, 2),
            "best_trades": best_trades[:5],
            "worst_trades": worst_trades[:5],
            "regime_transitions": regime_transitions,
            "agent_brier": agent_brier,
        }

    def format_slack_briefing(self, briefing: Dict[str, Any]) -> str:
        """Format morning briefing as Slack-compatible markdown with emoji regime."""
        regime = briefing.get("regime", {})
        state = regime.get("state", "sideways")
        emoji = "🟢" if state == "bull" else "🟡" if state == "sideways" else "🔴" if state == "bear" else "⚫"
        port = briefing.get("portfolio", {})
        lines = [
            f"{emoji} *Morning Briefing* — Regime: {state.upper()}",
            f"Portfolio: ${port.get('total_value', 0):,.0f} | Heat: {port.get('heat_pct', 0)}% | Positions: {port.get('open_positions', 0)}",
            "",
        ]
        for idea in briefing.get("trade_ideas", [])[:5]:
            lines.append(f"• *{idea.get('symbol')}* {idea.get('direction', 'buy').upper()} | Entry {idea.get('entry_zone', [0])[0]} | Stop {idea.get('stop_loss')} | T1 {idea.get('target_1')} | T2 {idea.get('target_2')}")
        if briefing.get("calendar_events"):
            lines.append("")
            lines.append("_Calendar:_ " + ", ".join(f"{e.get('symbol')} {e.get('type')}" for e in briefing["calendar_events"][:3]))
        return "\n".join(lines)

    def format_slack_weekly(self, review: Dict[str, Any]) -> str:
        """Format weekly review as Slack markdown."""
        lines = [
            "*Weekly Review*",
            f"P&L: ${review.get('total_pnl', 0):,.2f} | Win rate: {review.get('win_rate_pct', 0)}% | Trades: {review.get('total_trades', 0)}",
            f"Avg R-multiple: {review.get('avg_r_multiple', 0)}",
        ]
        for t in review.get("best_trades", [])[:3]:
            lines.append(f"  Best: {t.get('symbol')} R={t.get('r_multiple')} PnL=${t.get('pnl', 0):.2f}")
        for t in review.get("worst_trades", [])[:3]:
            lines.append(f"  Worst: {t.get('symbol')} R={t.get('r_multiple')} PnL=${t.get('pnl', 0):.2f}")
        return "\n".join(lines)


_briefing_service: Optional[BriefingService] = None


def get_briefing_service() -> BriefingService:
    """Return the BriefingService singleton."""
    global _briefing_service
    if _briefing_service is None:
        _briefing_service = BriefingService()
    return _briefing_service


# Backward compatibility: module-level generate_morning_briefing
async def generate_morning_briefing(
    as_of: Optional[date] = None,
    top_n: int = 5,
    regime: str = "GREEN",
) -> Dict[str, Any]:
    """Generate morning briefing (legacy shape: as_of, regime, ideas)."""
    svc = get_briefing_service()
    full = await svc.generate_morning_briefing(as_of=as_of, top_n=top_n)
    ideas = []
    for idea in full.get("trade_ideas", []):
        ideas.append({
            "ticker": idea.get("symbol"),
            "symbol": idea.get("symbol"),
            "action": idea.get("direction"),
            "direction": idea.get("direction", "buy").upper(),
            "price": idea.get("entry_zone", [0])[0],
            "entry": idea.get("entry_zone", [0])[0],
            "stop": idea.get("stop_loss"),
            "target1": idea.get("target_1"),
            "target2": idea.get("target_2"),
            "score": idea.get("score"),
            "confidence": idea.get("confidence"),
            "message": f"Council {idea.get('confidence', 0):.0%} confidence",
            "regime": idea.get("regime"),
        })
    return {
        "as_of": str(as_of or date.today()),
        "regime": regime,
        "ideas": ideas,
    }
