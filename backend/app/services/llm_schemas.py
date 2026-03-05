"""Pydantic models for LLM request/response/telemetry."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Provider(str, Enum):
    """Available LLM providers across infrastructure."""
    OLLAMA_SMALL = "ollama:small"      # PC-1, mistral-7b, <200ms
    OLLAMA_LARGE = "ollama:large"      # PC-2, llama3-70b, ~2-5s
    PERPLEXITY = "perplexity:sonar-pro"  # Cloud, web-grounded
    CLAUDE = "claude:claude-sonnet"    # Cloud, deep reasoning


class RoutingDecision(BaseModel):
    """Record of a routing decision for analytics."""
    task_type: str
    agent_name: str
    stage: int
    tier_selected: Provider
    prompt_complexity: float = Field(ge=0.0, le=1.0)
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    accuracy_score: Optional[float] = None  # backfilled from OutcomeTracker
    council_decision_id: str = ""
    router_reason: str = ""  # why this provider was chosen
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RoutingResult(BaseModel):
    """Result of a routed LLM call."""
    content: str
    provider: Provider
    model: str
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    citations: List[str] = Field(default_factory=list)
    fallback_used: bool = False
    error: str = ""
    routing_decision: Optional[RoutingDecision] = None


class AdaptiveRoutingStats(BaseModel):
    """Per-agent, per-provider adaptive routing statistics."""
    agent_name: str
    provider: str
    avg_accuracy: float = 0.5
    avg_latency_ms: float = 0.0
    total_cost: float = 0.0
    call_count: int = 0


# Agent → default provider mapping based on stage
AGENT_DEFAULT_PROVIDERS: Dict[str, Provider] = {
    # Stage 1 perception — local first (fast, private, zero-cost)
    "market_perception": Provider.OLLAMA_SMALL,
    "flow_perception": Provider.OLLAMA_SMALL,
    "social_perception": Provider.OLLAMA_SMALL,
    "news_catalyst": Provider.OLLAMA_SMALL,
    "youtube_knowledge": Provider.OLLAMA_SMALL,
    "intermarket": Provider.OLLAMA_SMALL,
    "regime": Provider.OLLAMA_SMALL,
    # Stage 2 technical — local small (mostly numerical)
    "rsi": Provider.OLLAMA_SMALL,
    "bbv": Provider.OLLAMA_SMALL,
    "ema_trend": Provider.OLLAMA_SMALL,
    "relative_strength": Provider.OLLAMA_SMALL,
    "cycle_timing": Provider.OLLAMA_SMALL,
    # Stage 3-6 — cloud for deep reasoning
    "hypothesis": Provider.CLAUDE,
    "strategy": Provider.CLAUDE,
    "risk": Provider.CLAUDE,
    "execution": Provider.OLLAMA_LARGE,
    "critic": Provider.CLAUDE,
    # Debate agents (Phase 2) — cloud for reasoning depth
    "bull_debater": Provider.CLAUDE,
    "bear_debater": Provider.CLAUDE,
    "red_team": Provider.OLLAMA_LARGE,
}

# Escalation path: if primary fails or accuracy is low
ESCALATION_CHAIN: Dict[Provider, Provider] = {
    Provider.OLLAMA_SMALL: Provider.OLLAMA_LARGE,
    Provider.OLLAMA_LARGE: Provider.PERPLEXITY,
    Provider.PERPLEXITY: Provider.CLAUDE,
    Provider.CLAUDE: Provider.CLAUDE,  # no further escalation
}
