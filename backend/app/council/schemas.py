"""Council schemas — shared data structures for the 17-agent council.

DAG: 7 stages, 17 agents + arbiter + debate stage 5.5.
Stage 1: [market_perception, flow_perception, regime, social_perception, news_catalyst, youtube_knowledge, intermarket]
Stage 2: [rsi, bbv, ema_trend, relative_strength, cycle_timing]
Stage 3: [hypothesis]
Stage 4: [strategy]
Stage 5: [risk, execution]
Stage 5.5: [debate_engine, bull_debater, bear_debater, red_team]
Stage 6: [critic]
Stage 7: arbiter (deterministic)

Embodier Trader Being Intelligence (ETBI) cognitive extensions:
  - CognitiveMeta: tracks exploration/exploitation mode, hypothesis diversity,
    agent agreement, memory precision, and confidence calibration.
  - DecisionPacket: enriched with active_hypothesis, semantic_context,
    experimental_history, and cognitive telemetry.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import math


@dataclass
class CognitiveMeta:
    """Cognitive telemetry for a single council evaluation.

    Tracks the "quality of thinking" — not just what was decided,
    but how the decision was reached and how diverse/calibrated the reasoning was.
    """

    # Exploration vs exploitation mode
    mode: str = "exploit"  # "explore" | "exploit" | "defensive"

    # Hypothesis diversity: Shannon entropy of agent directions
    # High entropy = diverse opinions = more exploration value
    hypothesis_diversity: float = 0.0

    # Agent agreement: % of agents agreeing with final direction
    agent_agreement: float = 0.0

    # Memory precision: relevance score of recalled heuristics (0-1)
    memory_precision: float = 0.0

    # Confidence calibration: running Brier score component
    confidence_calibration: float = 0.0

    # Mode switches: count of regime transitions in rolling window
    mode_switches_24h: int = 0

    # Latency budget: total council evaluation time in ms
    total_latency_ms: float = 0.0

    # Per-stage latencies for bottleneck detection
    stage_latencies: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "hypothesis_diversity": round(self.hypothesis_diversity, 4),
            "agent_agreement": round(self.agent_agreement, 4),
            "memory_precision": round(self.memory_precision, 4),
            "confidence_calibration": round(self.confidence_calibration, 4),
            "mode_switches_24h": self.mode_switches_24h,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "stage_latencies": {k: round(v, 1) for k, v in self.stage_latencies.items()},
        }

    @staticmethod
    def compute_diversity(votes: list) -> float:
        """Shannon entropy of vote directions. Higher = more diverse opinions."""
        if not votes:
            return 0.0
        counts = {}
        for v in votes:
            d = v.direction if hasattr(v, "direction") else v.get("direction", "hold")
            counts[d] = counts.get(d, 0) + 1
        total = sum(counts.values())
        if total == 0:
            return 0.0
        entropy = 0.0
        for c in counts.values():
            p = c / total
            if p > 0:
                entropy -= p * math.log2(p)
        # Normalize to [0, 1] — max entropy for 3 classes is log2(3) ≈ 1.585
        return min(entropy / 1.585, 1.0)

    @staticmethod
    def compute_agreement(votes: list, final_direction: str) -> float:
        """Fraction of agents agreeing with the final direction."""
        if not votes:
            return 0.0
        agree = sum(
            1 for v in votes
            if (v.direction if hasattr(v, "direction") else v.get("direction")) == final_direction
        )
        return agree / len(votes)


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
    """Final council decision combining all agent votes.

    Extended with ETBI cognitive context fields for richer decision provenance:
      - cognitive: CognitiveMeta telemetry (diversity, agreement, latency, mode)
      - active_hypothesis: the LLM-generated hypothesis that influenced the decision
      - semantic_context: recalled heuristics/memories that informed reasoning
      - experimental_history: recent exploration outcomes for adaptive mode switching
    """

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

    # ── ETBI Cognitive Extensions ──────────────────────────────────────────
    cognitive: CognitiveMeta = field(default_factory=CognitiveMeta)
    active_hypothesis: Optional[Dict[str, Any]] = None  # hypothesis agent's output
    semantic_context: Optional[Dict[str, Any]] = None  # recalled heuristics/memories
    experimental_history: List[Dict[str, Any]] = field(default_factory=list)  # recent explore outcomes

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
            "cognitive": self.cognitive.to_dict(),
        }
        if self.council_decision_id:
            d["council_decision_id"] = self.council_decision_id
        if self.active_hypothesis:
            d["active_hypothesis"] = self.active_hypothesis
        if self.semantic_context:
            d["semantic_context"] = self.semantic_context
        if self.experimental_history:
            d["experimental_history"] = self.experimental_history[-10:]  # last 10
        return d
