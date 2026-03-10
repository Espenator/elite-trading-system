"""Council registry — single source of truth for agent list and DAG stages.

Used by runner, API, WeightLearner, and UI. No hardcoded agent lists elsewhere.
"""
from typing import List

# Canonical agent IDs (must match runner stage configs and weight_learner DEFAULT_WEIGHTS)
AGENTS: List[str] = [
    # Stage 1: Perception + Academic Edge
    "market_perception",
    "flow_perception",
    "regime",
    "social_perception",
    "news_catalyst",
    "youtube_knowledge",
    "intermarket",
    "gex_agent",
    "insider_agent",
    "finbert_sentiment_agent",
    "earnings_tone_agent",
    "dark_pool_agent",
    "macro_regime_agent",
    # Stage 2: Technical + Data Enrichment
    "rsi",
    "bbv",
    "ema_trend",
    "relative_strength",
    "cycle_timing",
    "supply_chain_agent",
    "institutional_flow_agent",
    "congressional_agent",
    # Stage 3
    "hypothesis",
    # Stage 4
    "strategy",
    # Stage 5: Risk + Execution
    "risk",
    "execution",
    "portfolio_optimizer_agent",
    # Post-stages
    "critic",
    "arbiter",
]

# DAG layout: list of stages, each stage is list of agent IDs (parallel within stage)
DAG_STAGES: List[List[str]] = [
    [
        "market_perception", "flow_perception", "regime", "social_perception",
        "news_catalyst", "youtube_knowledge", "intermarket",
        "gex_agent", "insider_agent", "finbert_sentiment_agent",
        "earnings_tone_agent", "dark_pool_agent", "macro_regime_agent",
    ],
    [
        "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
        "supply_chain_agent", "institutional_flow_agent", "congressional_agent",
    ],
    ["hypothesis"],
    ["strategy"],
    ["risk", "execution", "portfolio_optimizer_agent"],
    ["critic"],
    ["arbiter"],
]


def get_agent_count() -> int:
    return len(AGENTS)


def get_agents() -> List[str]:
    return list(AGENTS)


def get_dag_stages() -> List[List[str]]:
    return [list(s) for s in DAG_STAGES]
