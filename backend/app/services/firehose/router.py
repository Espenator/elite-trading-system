"""Maps SensoryEvent to MessageBus topics and publishes."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.services.firehose.schemas import SensoryEvent, SensorySource

logger = logging.getLogger(__name__)


def route(event: SensoryEvent) -> list[tuple[str, Dict[str, Any]]]:
    """Return list of (topic, payload) to publish. Caller publishes to bus."""
    out: list[tuple[str, Dict[str, Any]]] = []
    if event.topic_hint:
        if event.topic_hint == "market_data.bar":
            out.append(("market_data.bar", event.to_market_bar()))
        elif event.topic_hint == "swarm.idea":
            out.append(("swarm.idea", event.to_swarm_idea()))
        else:
            out.append((event.topic_hint, event.payload))
        return out

    if event.source == SensorySource.ALPACA_STREAM and "close" in event.payload:
        out.append(("market_data.bar", event.to_market_bar()))
    else:
        out.append(("swarm.idea", event.to_swarm_idea()))
    return out
