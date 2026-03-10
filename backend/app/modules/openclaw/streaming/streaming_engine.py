"""OpenClaw streaming engine — re-exports the canonical Blackboard service.

All OpenClaw modules that import Blackboard, get_blackboard, Topic, or
BlackboardMessage from streaming_engine now use the single canonical
implementation in app.services.blackboard_service. There is no local
blackboard; this avoids a "silent alternate brain" in OpenClaw.
"""

from app.services.blackboard_service import (
    Blackboard,
    BlackboardMessage,
    Topic,
    get_blackboard,
    set_blackboard,
)

__all__ = [
    "Blackboard",
    "BlackboardMessage",
    "Topic",
    "get_blackboard",
    "set_blackboard",
]
