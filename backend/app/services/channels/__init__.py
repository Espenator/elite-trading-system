"""Continuous Discovery Firehose (channel agents + router).

This package is the "sensory nervous system" layer:
- Ingest from external sources (stream/poll/webhook)
- Normalize into SensoryEvent
- Route/publish into MessageBus topics (swarm.idea, market_data.*, ingest.*)
"""
from __future__ import annotations

from app.services.channels.schemas import SensoryEvent, SensorySource, SensoryEventType, DataQuality
from app.services.channels.router import SensoryRouter
from app.services.channels.base_channel_agent import BaseChannelAgent, RetryPolicy, CircuitBreaker
from app.services.channels.alpaca_channel_agent import AlpacaChannelAgent
from app.services.channels.discord_channel_agent import DiscordChannelAgent
from app.services.channels.orchestrator import (
    ChannelsOrchestrator,
    get_channels_orchestrator,
    ensure_orchestrator_started,
)

__all__ = [
    "SensoryEvent",
    "SensorySource",
    "SensoryEventType",
    "DataQuality",
    "SensoryRouter",
    "BaseChannelAgent",
    "RetryPolicy",
    "CircuitBreaker",
    "AlpacaChannelAgent",
    "DiscordChannelAgent",
    "ChannelsOrchestrator",
    "get_channels_orchestrator",
    "ensure_orchestrator_started",
]
