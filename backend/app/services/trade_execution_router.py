"""Production-safe trade execution router — sits between council.verdict and OrderExecutor.

Receives approved council decisions, enforces pre-trade checks, persists requests/results
for auditability, and forwards only validated verdicts to the executor. Fail-closed:
invalid or expired decisions cannot execute.

Pre-trade checks:
  - council_decision_id present
  - decision not expired (default 30s)
  - market hours valid (NYSE extended 4 AM–8 PM ET, weekdays)
  - no risk/execution veto (vetoed=False, no veto_reasons from VETO_AGENTS)
  - symbol, side, price validated
  - idempotency: already-completed decision_id is not re-submitted

Paper vs live: router does not switch mode; OrderExecutor and AlpacaService use
TRADING_MODE / ALPACA_BASE_URL. Router only records mode in audit for clarity.
"""
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from app.services.execution_audit_store import get_execution_audit_store
from app.services.execution_decision import (
    ExecutionDenyReason,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# Decision age beyond which we reject (seconds)
DECISION_EXPIRY_SECONDS = 30


def _parse_verdict_timestamp(verdict_data: Dict[str, Any]) -> Optional[float]:
    """Parse verdict timestamp to Unix seconds. DecisionPacket uses ISO timestamp."""
    ts = verdict_data.get("timestamp")
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        t = float(ts)
        if 1e9 <= t <= 2e10:  # unix seconds (2001–2036)
            return t
        return None
    try:
        s = str(ts).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.timestamp()
    except Exception:
        return None


def _is_market_open() -> Tuple[bool, Optional[str]]:
    """True if within NYSE extended hours (4 AM–8 PM ET, weekdays). Returns (ok, reason_if_closed)."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:
        return False, "Market closed: weekend"
    hour = now_et.hour
    if hour < 4 or hour >= 20:
        return False, f"Market closed: off-hours (ET hour={hour})"
    return True, None


def validate_verdict(verdict_data: Dict[str, Any], expiry_seconds: int = DECISION_EXPIRY_SECONDS) -> ValidationResult:
    """Run pre-trade checks on verdict. Fail-closed: any failure returns valid=False."""
    # 1. council_decision_id present
    decision_id = (verdict_data.get("council_decision_id") or "").strip()
    if not decision_id:
        return ValidationResult(
            valid=False,
            error_code=ExecutionDenyReason.DECISION_ID_MISSING.value,
            error_message="council_decision_id is required",
        )

    # 2. Decision not expired
    verdict_ts = _parse_verdict_timestamp(verdict_data)
    now = time.time()
    if verdict_ts is None:
        # No timestamp — fail closed (treat as stale)
        return ValidationResult(
            valid=False,
            error_code=ExecutionDenyReason.DECISION_EXPIRED.value,
            error_message="verdict timestamp missing",
        )
    if now - verdict_ts > expiry_seconds:
        return ValidationResult(
            valid=False,
            error_code=ExecutionDenyReason.DECISION_EXPIRED.value,
            error_message=f"decision expired (age={now - verdict_ts:.0f}s > {expiry_seconds}s)",
        )

    # 3. Market hours
    market_ok, reason = _is_market_open()
    if not market_ok:
        return ValidationResult(
            valid=False,
            error_code=ExecutionDenyReason.MARKET_CLOSED.value,
            error_message=reason or "Market closed",
        )

    # 4. No veto (risk/execution)
    if verdict_data.get("vetoed") is True:
        reasons = verdict_data.get("veto_reasons") or []
        return ValidationResult(
            valid=False,
            error_code=ExecutionDenyReason.VETOED.value,
            error_message="Council vetoed: " + ("; ".join(reasons) if reasons else "vetoed=True"),
        )

    # 5. Symbol, direction, price
    symbol = (verdict_data.get("symbol") or "").strip()
    if not symbol:
        return ValidationResult(
            valid=False,
            error_code=ExecutionDenyReason.MISSING_SYMBOL_PRICE.value,
            error_message="symbol missing",
        )
    direction = (verdict_data.get("final_direction") or "hold").lower()
    if direction not in ("buy", "sell"):
        return ValidationResult(
            valid=False,
            error_code=ExecutionDenyReason.COUNCIL_HOLD.value,
            error_message=f"invalid direction: {direction}",
        )
    signal_data = verdict_data.get("signal_data") or {}
    price = verdict_data.get("price") or signal_data.get("price") or signal_data.get("close") or 0
    try:
        price = float(price)
    except (TypeError, ValueError):
        price = 0
    if not price or price <= 0:
        return ValidationResult(
            valid=False,
            error_code=ExecutionDenyReason.MISSING_SYMBOL_PRICE.value,
            error_message="invalid or missing price",
        )

    return ValidationResult(valid=True)


class TradeExecutionRouter:
    """Validates council verdicts, persists audit, forwards only valid verdicts to executor."""

    def __init__(
        self,
        message_bus,
        expiry_seconds: int = DECISION_EXPIRY_SECONDS,
        audit_path=None,
    ):
        self.message_bus = message_bus
        self.expiry_seconds = expiry_seconds
        self.audit = get_execution_audit_store(audit_path=audit_path)
        self._running = False
        self._subscribed_validated = False
        self._subscribed_result = False

    async def start(self) -> None:
        """Subscribe to council.verdict and execution.result. Validate and forward verdicts."""
        from app.core.message_bus import MessageBus
        if getattr(self.message_bus, "subscribe", None) is None:
            logger.warning("TradeExecutionRouter: message_bus has no subscribe")
            return
        await self.message_bus.subscribe("council.verdict", self._on_council_verdict)
        self._subscribed_validated = True
        await self.message_bus.subscribe("execution.result", self._on_execution_result)
        self._subscribed_result = True
        self._running = True
        logger.info(
            "TradeExecutionRouter started (expiry=%ds, fail-closed)",
            self.expiry_seconds,
        )

    async def stop(self) -> None:
        """Unsubscribe and stop."""
        self._running = False
        if self._subscribed_validated and hasattr(self.message_bus, "unsubscribe"):
            await self.message_bus.unsubscribe("council.verdict", self._on_council_verdict)
        if self._subscribed_result and hasattr(self.message_bus, "unsubscribe"):
            await self.message_bus.unsubscribe("execution.result", self._on_execution_result)
        self._subscribed_validated = False
        self._subscribed_result = False
        logger.info("TradeExecutionRouter stopped")

    async def _on_council_verdict(self, verdict_data: Dict[str, Any]) -> None:
        """Validate verdict, persist request, and forward only if valid and not duplicate."""
        if not self._running:
            return
        decision_id = (verdict_data.get("council_decision_id") or "").strip()
        symbol = (verdict_data.get("symbol") or "").strip()
        direction = (verdict_data.get("final_direction") or "hold").lower()
        side = "buy" if direction == "buy" else "sell"

        # Idempotency: already completed for this decision?
        if self.audit.is_already_completed(decision_id):
            logger.info(
                "TradeExecutionRouter: duplicate verdict suppressed (already completed): %s",
                decision_id[:16] if decision_id else "?",
            )
            return

        validation = validate_verdict(verdict_data, expiry_seconds=self.expiry_seconds)
        if not validation.valid:
            self.audit.record_request(
                council_decision_id=decision_id or "unknown",
                symbol=symbol or "?",
                side=side,
                status="rejected",
                reason=validation.error_message,
                error_code=validation.error_code,
            )
            logger.info(
                "TradeExecutionRouter: verdict rejected %s — %s",
                decision_id[:16] if decision_id else symbol,
                validation.error_message,
            )
            return

        # Persist pending request then forward
        self.audit.record_request(
            council_decision_id=decision_id,
            symbol=symbol,
            side=side,
            status="pending",
        )
        await self.message_bus.publish("execution.validated_verdict", verdict_data)
        logger.debug(
            "TradeExecutionRouter: forwarded validated verdict %s %s",
            decision_id[:16],
            symbol,
        )

    async def _on_execution_result(self, result_data: Dict[str, Any]) -> None:
        """Persist execution result for audit."""
        if not self._running:
            return
        try:
            self.audit.record_result(
                council_decision_id=result_data.get("council_decision_id", ""),
                success=result_data.get("success", False),
                order_id=result_data.get("order_id", ""),
                client_order_id=result_data.get("client_order_id", ""),
                symbol=result_data.get("symbol", ""),
                side=result_data.get("side", ""),
                error_code=result_data.get("error_code"),
                error_message=result_data.get("error_message"),
                mode=result_data.get("mode", "paper"),
                payload={k: v for k, v in result_data.items() if k not in (
                    "council_decision_id", "success", "order_id", "client_order_id",
                    "symbol", "side", "error_code", "error_message", "mode",
                )},
            )
        except Exception as e:
            logger.warning("TradeExecutionRouter: failed to persist execution result: %s", e)
