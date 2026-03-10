"""Firehose — canonical sensory event layer.

Normalizes external sources into SensoryEvent and routes to MessageBus topics
(market_data.bar, swarm.idea, perception.*). Agents run under the orchestrator
with queue, backoff, and circuit breaker support.
"""
from app.services.firehose.schemas import SensoryEvent

__all__ = ["SensoryEvent"]
