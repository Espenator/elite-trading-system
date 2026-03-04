"""Council schemas — shared data structures for the 11-agent debate council."""
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentVote:
    """Individual agent's vote in the council."""

    agent_name: str
    direction: str  # "buy" | "sell" | "hold"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    veto: bool = False
    veto_reason: str = ""
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    blackboard_ref: str = ""  # council_decision_id linking vote to blackboard

    def __post_init__(self):
        if self.direction not in {"buy", "sell", "hold"}:
            raise ValueError(f"direction must be 'buy', 'sell', or 'hold', got '{self.direction}'")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        if self.weight <= 0:
            raise ValueError(f"weight must be > 0, got {self.weight}")

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "agent_name": self.agent_name,
            "direction": self.direction,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "veto": self.veto,
            "veto_reason": self.veto_reason,
            "weight": self.weight,
            "metadata": self.metadata,
        }
        if self.blackboard_ref:
            d["blackboard_ref"] = self.blackboard_ref
        return d


@dataclass
class DecisionPacket:
    """Final council decision combining all agent votes."""

    symbol: str
    timeframe: str
    timestamp: str
    votes: List[AgentVote]
    final_direction: str  # "buy" | "sell" | "hold"
    final_confidence: float
    vetoed: bool
    veto_reasons: List[str]
    risk_limits: Dict[str, Any]
    execution_ready: bool
    council_reasoning: str
    council_decision_id: str = ""  # links to BlackboardState

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "votes": [v.to_dict() for v in self.votes],
            "final_direction": self.final_direction,
            "final_confidence": self.final_confidence,
            "vetoed": self.vetoed,
            "veto_reasons": self.veto_reasons,
            "risk_limits": self.risk_limits,
            "execution_ready": self.execution_ready,
            "council_reasoning": self.council_reasoning,
            "vote_count": len(self.votes),
        }
        if self.council_decision_id:
            d["council_decision_id"] = self.council_decision_id
        return d
