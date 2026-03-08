"""Scout agents package — E2 of the Continuous Discovery Architecture.

12 dedicated scout agents that run continuously and publish discoveries
to ``swarm.idea``.  All scouts inherit from ``BaseScout`` in ``base.py``
and are registered with ``ScoutRegistry`` in ``registry.py``.
"""
from app.services.scouts.base import BaseScout, DiscoveryPayload
from app.services.scouts.registry import ScoutRegistry, get_scout_registry

__all__ = [
    "BaseScout",
    "DiscoveryPayload",
    "ScoutRegistry",
    "get_scout_registry",
]
