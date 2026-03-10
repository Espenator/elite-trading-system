"""Typed event contract layer for the trading pipeline.

- Topic constants and payload schemas (Pydantic/dataclass).
- Event metadata: event_id, trace_id, created_at, producer, schema_version, pipeline_stage.
- publish_event / subscribe_event wrappers that validate and emit metrics.
- Startup integrity: check required subscribers for critical topics.
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, Optional, Set

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"

# ─── Topic constants (single source of truth for pipeline) ─────────────────
TOPIC_SWARM_IDEA = "swarm.idea"
TOPIC_TRIAGE_ESCALATED = "triage.escalated"
TOPIC_TRIAGE_DROPPED = "triage.dropped"
TOPIC_SWARM_RESULT = "swarm.result"
TOPIC_COUNCIL_VERDICT = "council.verdict"
TOPIC_ORDER_SUBMITTED = "order.submitted"
TOPIC_ORDER_FILLED = "order.filled"
TOPIC_OUTCOME_RESOLVED = "outcome.resolved"

PIPELINE_TOPICS: Set[str] = {
    TOPIC_SWARM_IDEA,
    TOPIC_TRIAGE_ESCALATED,
    TOPIC_TRIAGE_DROPPED,
    TOPIC_SWARM_RESULT,
    TOPIC_COUNCIL_VERDICT,
    TOPIC_ORDER_SUBMITTED,
    TOPIC_ORDER_FILLED,
    TOPIC_OUTCOME_RESOLVED,
}

# Topics that must have at least one consumer for the pipeline to function
CRITICAL_CONSUMER_TOPICS: Set[str] = {
    TOPIC_SWARM_IDEA,       # triage consumes
    TOPIC_TRIAGE_ESCALATED, # hyperswarm consumes
    TOPIC_COUNCIL_VERDICT,  # order executor consumes
    TOPIC_ORDER_SUBMITTED,  # outcome tracker consumes
}


@dataclass
class BaseEventMetadata:
    """Standard metadata on every pipeline event for tracing and audit."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    producer: str = ""
    schema_version: str = SCHEMA_VERSION
    pipeline_stage: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "created_at": self.created_at,
            "producer": self.producer,
            "schema_version": self.schema_version,
            "pipeline_stage": self.pipeline_stage,
        }


def ensure_event_metadata(
    data: Dict[str, Any],
    producer: str,
    pipeline_stage: str,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Inject or preserve event metadata in payload. Mutates and returns data."""
    payload = dict(data)
    existing = payload.get("_event_meta") or {}
    meta = BaseEventMetadata(
        event_id=existing.get("event_id") or str(uuid.uuid4()),
        trace_id=trace_id or existing.get("trace_id") or str(uuid.uuid4()),
        created_at=existing.get("created_at") or datetime.now(timezone.utc).isoformat(),
        producer=producer or existing.get("producer", ""),
        schema_version=existing.get("schema_version", SCHEMA_VERSION),
        pipeline_stage=pipeline_stage or existing.get("pipeline_stage", ""),
    )
    payload["_event_meta"] = meta.to_dict()
    return payload


def _minimal_validation(topic: str, data: Dict[str, Any]) -> Optional[str]:
    """Validate payload shape per topic. Returns None if ok, else error message."""
    if not isinstance(data, dict):
        return "payload must be a dict"
    if topic == TOPIC_SWARM_IDEA:
        if not data.get("symbols") and not data.get("symbol"):
            return "swarm.idea requires symbols or symbol"
    if topic == TOPIC_COUNCIL_VERDICT:
        if not data.get("symbol"):
            return "council.verdict requires symbol"
    if topic == TOPIC_ORDER_SUBMITTED:
        if not data.get("order_id") and not data.get("client_order_id"):
            return "order.submitted requires order_id or client_order_id"
        if not data.get("symbol"):
            return "order.submitted requires symbol"
    if topic == TOPIC_OUTCOME_RESOLVED:
        if not data.get("symbol") and not data.get("order_id"):
            return "outcome.resolved requires symbol or order_id"
    return None


def validate_payload(topic: str, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate payload for topic. Returns (ok, error_message)."""
    err = _minimal_validation(topic, data)
    if err:
        return False, err
    return True, None


def _emit_event_metrics(topic: str, kind: str, status: str) -> None:
    try:
        from app.core.metrics import counter_inc
        if kind == "publish":
            counter_inc("event_publish_total", {"topic": topic, "status": status})
        else:
            counter_inc("event_consume_total", {"topic": topic, "status": status})
    except Exception:
        pass


def _emit_schema_fail(topic: str) -> None:
    try:
        from app.core.metrics import counter_inc
        counter_inc("event_schema_validation_fail_total", {"topic": topic})
    except Exception:
        pass


async def publish_event(
    bus: Any,
    topic: str,
    payload: Dict[str, Any],
    producer: str,
    pipeline_stage: str = "",
    trace_id: Optional[str] = None,
    enforce_schema: bool = True,
) -> bool:
    """Publish with metadata injection and optional validation. Returns True if published."""
    if not bus:
        return False
    try:
        from app.core.config import settings
        enforce = getattr(settings, "ENFORCE_CANONICAL_PIPELINE", True) and enforce_schema
    except Exception:
        enforce = enforce_schema

    if enforce and topic in PIPELINE_TOPICS:
        ok, err = validate_payload(topic, payload)
        if not ok:
            _emit_schema_fail(topic)
            _emit_event_metrics(topic, "publish", "validation_failed")
            logger.warning("event publish validation failed topic=%s reason=%s", topic, err)
            return False

    data = ensure_event_metadata(payload, producer, pipeline_stage or topic, trace_id)
    await bus.publish(topic, data)
    _emit_event_metrics(topic, "publish", "ok")
    return True


def subscribe_event(
    bus: Any,
    topic: str,
    handler: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
    validate_on_consume: bool = True,
):
    """Return a wrapped handler that validates payload and emits consume metrics, then calls handler."""

    async def _wrapped(data: Dict[str, Any]) -> None:
        status = "ok"
        if validate_on_consume and topic in PIPELINE_TOPICS:
            ok, err = validate_payload(topic, data)
            if not ok:
                _emit_schema_fail(topic)
                _emit_event_metrics(topic, "consume", "validation_failed")
                logger.warning(
                    "event consume validation failed topic=%s reason=%s trace_id=%s",
                    topic, err, (data.get("_event_meta") or {}).get("trace_id"),
                )
                return
        try:
            await handler(data)
        except Exception as e:
            status = "error"
            raise
        finally:
            _emit_event_metrics(topic, "consume", status)

    return _wrapped


def check_critical_subscribers(bus: Any) -> tuple[bool, Dict[str, Any]]:
    """Verify required consumers are registered for critical topics.

    Returns (all_ok, details_dict). If FAIL_ON_CRITICAL_SUBSCRIBER_MISSING is True
    and a critical topic has no subscribers, all_ok is False.
    """
    try:
        from app.core.config import settings
        fail_on_missing = getattr(settings, "FAIL_ON_CRITICAL_SUBSCRIBER_MISSING", False)
    except Exception:
        fail_on_missing = False

    details: Dict[str, Any] = {"critical_topics": list(CRITICAL_CONSUMER_TOPICS), "missing": []}
    if not bus or not hasattr(bus, "_subscribers"):
        details["error"] = "bus or _subscribers not available"
        return False, details

    for topic in CRITICAL_CONSUMER_TOPICS:
        count = len(bus._subscribers.get(topic, []))
        details[topic] = count
        if count == 0:
            details["missing"].append(topic)

    all_ok = len(details["missing"]) == 0
    if fail_on_missing and not all_ok:
        logger.warning(
            "Critical subscriber check failed: missing consumers for %s (FAIL_ON_CRITICAL_SUBSCRIBER_MISSING=True)",
            details["missing"],
        )
    return all_ok, details


def run_startup_integrity_check(bus: Any) -> tuple[bool, Dict[str, Any]]:
    """Run pipeline integrity check at startup.

    If FAIL_ON_CRITICAL_SUBSCRIBER_MISSING is True and any critical topic
    has no subscriber, returns (False, details). Otherwise returns (True, details).
    Call after all services have registered their subscriptions.
    """
    all_ok, details = check_critical_subscribers(bus)
    if not all_ok:
        try:
            from app.core.config import settings
            if getattr(settings, "FAIL_ON_CRITICAL_SUBSCRIBER_MISSING", False):
                return False, details
        except Exception:
            pass
    return True, details
