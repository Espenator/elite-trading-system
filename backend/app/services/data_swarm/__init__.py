"""Data swarm — 24/7 data collection infrastructure for Embodier Trader.

Spawnable collectors for Alpaca, Unusual Whales, and FinViz Elite that keep
the Blackboard fed with pricing data 24h/day, 5.5 days/week. All agents
publish to MessageBus on data.price, data.flow, data.screener channels.
"""

from app.services.data_swarm.session_clock import (
    SourceAvailability,
    TradingSession,
    get_session_clock,
)
from app.services.data_swarm.schemas import (
    PriceUpdate,
    FlowUpdate,
    ScreenerUpdate,
    FuturesUpdate,
)
from app.services.data_swarm.health_monitor import get_health_monitor, HealthMonitor
from app.services.data_swarm.swarm_orchestrator import (
    SwarmOrchestrator,
    get_swarm_orchestrator,
)

__all__ = [
    "TradingSession",
    "SourceAvailability",
    "get_session_clock",
    "PriceUpdate",
    "FlowUpdate",
    "ScreenerUpdate",
    "FuturesUpdate",
    "get_health_monitor",
    "HealthMonitor",
    "SwarmOrchestrator",
    "get_swarm_orchestrator",
]
