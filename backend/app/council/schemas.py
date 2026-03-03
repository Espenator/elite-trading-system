"""Council schemas — shared data structures for the 8-agent debate council."""
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "direction": self.direction,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "veto": self.veto,
            "veto_reason": self.veto_reason,
            "weight": self.weight,
            "metadata": self.metadata,
        }


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

    def to_dict(self) -> Dict[str, Any]:
        return {
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
