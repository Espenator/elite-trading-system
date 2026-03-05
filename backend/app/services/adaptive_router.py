"""Adaptive LLM Router — intelligent per-agent routing with learning.

Builds on top of the existing LLMRouter (llm_router.py) to add:
- Per-agent provider selection based on historical accuracy
- Dual-PC Ollama support (small on PC-1, large on PC-2)
- Escalation when volatility spikes or confidence is low
- DuckDB-backed call tracking and adaptive weight learning
- Cost/latency/accuracy telemetry per (agent, provider) pair
"""
import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from app.services.llm_schemas import (
    AGENT_DEFAULT_PROVIDERS,
    ESCALATION_CHAIN,
    AdaptiveRoutingStats,
    Provider,
    RoutingDecision,
    RoutingResult,
)

logger = logging.getLogger(__name__)

# Accuracy threshold: if historical accuracy for (agent, provider) < this, escalate
ACCURACY_ESCALATION_THRESHOLD = 0.45
# Minimum calls before adaptive routing kicks in
MIN_CALLS_FOR_ADAPTATION = 10


class HybridLLMRouter:
    """Intelligent per-agent LLM router that learns from trade outcomes.

    Routing policy:
        Stage 1 perception: LOCAL_SMALL first. Escalate to PERPLEXITY on
            volatility spike or low confidence. CLAUDE for multi-step synthesis.
        Stage 2 technical: LOCAL_SMALL (mostly numerical).
        Stages 3-6 (hypothesis, strategy, risk, critic): Default CLAUDE.
        Adaptive override: if historical accuracy < 0.45, auto-promote.
    """

    def __init__(self):
        self._adaptive_stats: Dict[str, Dict[str, AdaptiveRoutingStats]] = {}
        self._call_buffer: List[Dict[str, Any]] = []  # buffered for DuckDB write
        self._load_adaptive_stats()

    async def route_and_execute(
        self,
        agent_name: str,
        stage: int,
        prompt: str,
        blackboard: Any = None,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        json_mode: bool = False,
        council_decision_id: str = "",
    ) -> RoutingResult:
        """Route an agent's LLM call to the optimal provider and execute.

        Args:
            agent_name: Name of the council agent
            stage: DAG stage number (1-7)
            prompt: The user prompt to send
            blackboard: BlackboardState for context-aware routing
            system_prompt: System message
            temperature: Sampling temperature
            max_tokens: Max output tokens
            json_mode: Request JSON output
            council_decision_id: Links to the council decision

        Returns:
            RoutingResult with content, provider, latency, cost, etc.
        """
        # Determine provider
        provider = self._select_provider(agent_name, stage, blackboard)
        reason = self._explain_routing(agent_name, provider)

        # Build messages
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Execute with fallback
        t0 = time.monotonic()
        result = await self._execute_with_fallback(
            provider, messages, temperature, max_tokens, json_mode
        )
        latency_ms = (time.monotonic() - t0) * 1000

        # Build routing decision
        decision = RoutingDecision(
            task_type=f"stage_{stage}_{agent_name}",
            agent_name=agent_name,
            stage=stage,
            tier_selected=result.provider,
            prompt_complexity=self._estimate_complexity(prompt),
            latency_ms=latency_ms,
            cost_usd=result.cost_usd,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            council_decision_id=council_decision_id,
            router_reason=reason,
        )
        result.routing_decision = decision

        # Buffer for DuckDB persistence
        self._buffer_call(decision)

        # Store routing metadata in blackboard
        if blackboard and hasattr(blackboard, "metadata"):
            trace_key = f"{agent_name}_routing"
            blackboard.metadata[trace_key] = {
                "provider": result.provider.value,
                "latency_ms": round(latency_ms, 1),
                "cost_usd": round(result.cost_usd, 6),
                "fallback_used": result.fallback_used,
            }
            # Append to llm_trace list
            traces = blackboard.metadata.get("llm_trace", [])
            traces.append({
                "agent": agent_name,
                "provider": result.provider.value,
                "latency_ms": round(latency_ms, 1),
            })
            blackboard.metadata["llm_trace"] = traces

        return result

    def update_accuracy(
        self, agent_name: str, provider_value: str, was_correct: bool
    ) -> None:
        """Update accuracy stats for an (agent, provider) pair.

        Called by OutcomeTracker after trade resolution.
        """
        if agent_name not in self._adaptive_stats:
            self._adaptive_stats[agent_name] = {}

        stats = self._adaptive_stats[agent_name].get(provider_value)
        if not stats:
            stats = AdaptiveRoutingStats(agent_name=agent_name, provider=provider_value)
            self._adaptive_stats[agent_name][provider_value] = stats

        # Exponential moving average for accuracy
        alpha = 0.1
        new_val = 1.0 if was_correct else 0.0
        stats.avg_accuracy = stats.avg_accuracy * (1 - alpha) + new_val * alpha
        stats.call_count += 1

        self._persist_adaptive_stats(agent_name)

    # ── Internal routing logic ────────────────────────────────────────────────

    def _select_provider(
        self, agent_name: str, stage: int, blackboard: Any
    ) -> Provider:
        """Select the optimal provider for this agent."""
        # Start with default mapping
        provider = AGENT_DEFAULT_PROVIDERS.get(agent_name, Provider.OLLAMA_SMALL)

        # Check adaptive override: if accuracy is too low, escalate
        if agent_name in self._adaptive_stats:
            agent_stats = self._adaptive_stats[agent_name]
            current_key = provider.value
            if current_key in agent_stats:
                stats = agent_stats[current_key]
                if (
                    stats.call_count >= MIN_CALLS_FOR_ADAPTATION
                    and stats.avg_accuracy < ACCURACY_ESCALATION_THRESHOLD
                ):
                    escalated = ESCALATION_CHAIN.get(provider, provider)
                    logger.info(
                        "Adaptive escalation: %s from %s to %s (accuracy=%.2f)",
                        agent_name, provider.value, escalated.value, stats.avg_accuracy,
                    )
                    provider = escalated

        # Context-aware escalation for perception agents
        if blackboard and stage == 1:
            meta = getattr(blackboard, "metadata", {}) if blackboard else {}
            intel = meta.get("intelligence", {})

            # Volatility spike → escalate news/social to Perplexity
            if agent_name in ("news_catalyst", "social_perception", "youtube_knowledge"):
                features = getattr(blackboard, "raw_features", {})
                vix = features.get("features", {}).get("vix_close", 0)
                if vix and float(vix) > 30:
                    provider = Provider.PERPLEXITY
                    logger.debug("Volatility escalation for %s (VIX=%.1f)", agent_name, vix)

        return provider

    def _explain_routing(self, agent_name: str, provider: Provider) -> str:
        default = AGENT_DEFAULT_PROVIDERS.get(agent_name)
        if default == provider:
            return f"default_mapping:{agent_name}->{provider.value}"
        return f"escalated:{agent_name}->{provider.value}"

    async def _execute_with_fallback(
        self,
        provider: Provider,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> RoutingResult:
        """Execute LLM call with fallback chain on failure."""
        # Use the existing LLMRouter for actual API calls
        from app.services.llm_router import Tier, get_llm_router

        tier = self._provider_to_tier(provider)
        router = get_llm_router()

        result = await router.route(
            tier=tier,
            messages=messages,
            task="adaptive_route",
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        )

        if result.content and not result.error:
            return RoutingResult(
                content=result.content,
                provider=provider,
                model=result.model,
                latency_ms=result.latency_ms,
                tokens_in=result.input_tokens,
                tokens_out=result.output_tokens,
                cost_usd=result.cost_usd,
                citations=result.citations,
            )

        # Fallback
        fallback_provider = ESCALATION_CHAIN.get(provider, provider)
        if fallback_provider != provider:
            logger.info("Fallback from %s to %s", provider.value, fallback_provider.value)
            fallback_tier = self._provider_to_tier(fallback_provider)
            result = await router.route(
                tier=fallback_tier,
                messages=messages,
                task="adaptive_route_fallback",
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
            return RoutingResult(
                content=result.content,
                provider=fallback_provider,
                model=result.model,
                latency_ms=result.latency_ms,
                tokens_in=result.input_tokens,
                tokens_out=result.output_tokens,
                cost_usd=result.cost_usd,
                citations=result.citations,
                fallback_used=True,
                error=result.error,
            )

        return RoutingResult(
            content="",
            provider=provider,
            model="",
            latency_ms=0,
            error=result.error or "all_providers_failed",
        )

    def _provider_to_tier(self, provider: Provider) -> str:
        """Map Provider enum to existing LLMRouter Tier."""
        if provider in (Provider.OLLAMA_SMALL, Provider.OLLAMA_LARGE):
            return "brainstem"
        elif provider == Provider.PERPLEXITY:
            return "cortex"
        elif provider == Provider.CLAUDE:
            return "deep_cortex"
        return "brainstem"

    def _estimate_complexity(self, prompt: str) -> float:
        """Heuristic prompt complexity score (0.0-1.0)."""
        length = len(prompt)
        if length < 200:
            return 0.2
        elif length < 500:
            return 0.4
        elif length < 1000:
            return 0.6
        elif length < 2000:
            return 0.8
        return 1.0

    # ── Persistence ───────────────────────────────────────────────────────────

    def _buffer_call(self, decision: RoutingDecision) -> None:
        """Buffer a routing decision for batch DuckDB write."""
        self._call_buffer.append({
            "call_id": str(uuid.uuid4()),
            "ts": decision.timestamp.isoformat(),
            "agent_name": decision.agent_name,
            "stage": decision.stage,
            "provider": decision.tier_selected.value,
            "model": "",
            "latency_ms": decision.latency_ms,
            "cost_usd": decision.cost_usd,
            "tokens_in": decision.tokens_in,
            "tokens_out": decision.tokens_out,
            "router_reason": decision.router_reason,
            "council_decision_id": decision.council_decision_id,
        })
        # Flush every 20 calls
        if len(self._call_buffer) >= 20:
            self._flush_call_buffer()

    def _flush_call_buffer(self) -> None:
        """Write buffered calls to DuckDB."""
        if not self._call_buffer:
            return
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            for call in self._call_buffer:
                conn.execute("""
                    INSERT INTO llm_calls
                    (call_id, ts, agent_name, stage, provider, model, latency_ms,
                     cost_usd, tokens_in, tokens_out, router_reason, council_decision_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    call["call_id"], call["ts"], call["agent_name"], call["stage"],
                    call["provider"], call["model"], call["latency_ms"],
                    call["cost_usd"], call["tokens_in"], call["tokens_out"],
                    call["router_reason"], call["council_decision_id"],
                ])
            self._call_buffer.clear()
        except Exception as e:
            logger.debug("Failed to flush LLM call buffer: %s", e)

    def _load_adaptive_stats(self) -> None:
        """Load adaptive routing stats from DuckDB."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            rows = conn.execute(
                "SELECT agent_name, provider, avg_accuracy, avg_latency_ms, total_cost, call_count "
                "FROM adaptive_routing"
            ).fetchall()
            for row in rows:
                agent, prov, acc, lat, cost, count = row
                if agent not in self._adaptive_stats:
                    self._adaptive_stats[agent] = {}
                self._adaptive_stats[agent][prov] = AdaptiveRoutingStats(
                    agent_name=agent, provider=prov,
                    avg_accuracy=acc, avg_latency_ms=lat,
                    total_cost=cost, call_count=count,
                )
            if rows:
                logger.info("Loaded adaptive routing stats for %d agent-provider pairs", len(rows))
        except Exception as e:
            logger.debug("Adaptive stats not loaded (table may not exist): %s", e)

    def _persist_adaptive_stats(self, agent_name: str = None) -> None:
        """Persist adaptive stats to DuckDB.

        Args:
            agent_name: If provided, only persist stats for this agent.
                        Otherwise persists all stats.
        """
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            items = (
                [(agent_name, self._adaptive_stats.get(agent_name, {}))]
                if agent_name and agent_name in self._adaptive_stats
                else self._adaptive_stats.items()
            )
            for agent, providers in items:
                for prov, stats in providers.items():
                    conn.execute("""
                        INSERT OR REPLACE INTO adaptive_routing
                        (agent_name, provider, avg_accuracy, avg_latency_ms, total_cost, call_count)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, [
                        stats.agent_name, stats.provider,
                        stats.avg_accuracy, stats.avg_latency_ms,
                        stats.total_cost, stats.call_count,
                    ])
        except Exception as e:
            logger.debug("Failed to persist adaptive stats: %s", e)

    def get_status(self) -> Dict[str, Any]:
        """Return adaptive router status for dashboard."""
        stats_summary = {}
        for agent, providers in self._adaptive_stats.items():
            stats_summary[agent] = {
                prov: {
                    "accuracy": round(s.avg_accuracy, 3),
                    "latency_ms": round(s.avg_latency_ms, 1),
                    "calls": s.call_count,
                    "cost": round(s.total_cost, 4),
                }
                for prov, s in providers.items()
            }
        return {
            "adaptive_stats": stats_summary,
            "buffered_calls": len(self._call_buffer),
        }


# Singleton
_hybrid_router: Optional[HybridLLMRouter] = None


def get_hybrid_router() -> HybridLLMRouter:
    global _hybrid_router
    if _hybrid_router is None:
        _hybrid_router = HybridLLMRouter()
    return _hybrid_router
