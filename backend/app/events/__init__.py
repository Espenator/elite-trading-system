"""Canonical event contracts and pipeline topic registry.

Use publish_event / subscribe_event for typed, validated, traced pipeline events.
"""
from app.events.contracts import (
    PIPELINE_TOPICS,
    TOPIC_SWARM_IDEA,
    TOPIC_TRIAGE_ESCALATED,
    TOPIC_TRIAGE_DROPPED,
    TOPIC_COUNCIL_VERDICT,
    TOPIC_ORDER_SUBMITTED,
    TOPIC_OUTCOME_RESOLVED,
    BaseEventMetadata,
    ensure_event_metadata,
    publish_event,
    subscribe_event,
    validate_payload,
    check_critical_subscribers,
    run_startup_integrity_check,
)

__all__ = [
    "PIPELINE_TOPICS",
    "TOPIC_SWARM_IDEA",
    "TOPIC_TRIAGE_ESCALATED",
    "TOPIC_TRIAGE_DROPPED",
    "TOPIC_COUNCIL_VERDICT",
    "TOPIC_ORDER_SUBMITTED",
    "TOPIC_OUTCOME_RESOLVED",
    "BaseEventMetadata",
    "ensure_event_metadata",
    "publish_event",
    "subscribe_event",
    "validate_payload",
    "check_critical_subscribers",
    "run_startup_integrity_check",
]
