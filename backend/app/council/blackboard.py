"""BlackboardState — shared context passed through the council DAG.

Replaces the raw features dict with a structured object that each
stage writes to. The blackboard is the single source of truth for
the entire council evaluation pipeline.

Usage:
    bb = BlackboardState(symbol="AAPL", raw_features=features)
    # Stage 1 agents write perceptions
    bb.perceptions["market_perception"] = vote.to_dict()
    # Stage 2 writes hypothesis
    bb.hypothesis = vote.to_dict()
    # etc.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


@dataclass
class BlackboardState:
    """Shared context for a single council evaluation.

    Created at the start of run_council() and passed through all stages.
    Each agent reads upstream data and writes its output to the appropriate field.
    """

    symbol: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_features: Dict[str, Any] = field(default_factory=dict)

    # Stage outputs — written by agents during evaluation
    perceptions: Dict[str, Any] = field(default_factory=dict)  # S1 agents write here
    hypothesis: Optional[Dict[str, Any]] = None  # S2 writes here
    strategy: Optional[Dict[str, Any]] = None  # S3 writes here
    risk_assessment: Optional[Dict[str, Any]] = None  # S4 risk writes here
    execution_plan: Optional[Dict[str, Any]] = None  # S4 execution writes here
    critic_review: Optional[Dict[str, Any]] = None  # S5 writes here

    # Identity and lifecycle
    council_decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 30  # decision expires after 30s

    # Extensible metadata (circuit breaker results, directives, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if this blackboard has exceeded its TTL."""
        elapsed = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

    @property
    def features(self) -> Dict[str, Any]:
        """Convenience accessor — returns raw_features for backward compat with agents."""
        return self.raw_features

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging, WebSocket broadcast, or postmortem storage."""
        return {
            "council_decision_id": self.council_decision_id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "perceptions": self.perceptions,
            "hypothesis": self.hypothesis,
            "strategy": self.strategy,
            "risk_assessment": self.risk_assessment,
            "execution_plan": self.execution_plan,
            "critic_review": self.critic_review,
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
        }

    def to_snapshot(self) -> Dict[str, Any]:
        """Compact snapshot for postmortem storage (excludes raw_features bulk)."""
        return {
            "council_decision_id": self.council_decision_id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "perceptions": self.perceptions,
            "hypothesis": self.hypothesis,
            "strategy": self.strategy,
            "risk_assessment": self.risk_assessment,
            "execution_plan": self.execution_plan,
            "critic_review": self.critic_review,
        }
