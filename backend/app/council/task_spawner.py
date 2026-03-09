"""TaskSpawner — dynamic agent creation and parallel execution.

Replaces hardcoded agent imports in runner.py with a registry-based
spawner that can run agents in parallel or background.

Usage:
    spawner = TaskSpawner(blackboard)
    spawner.register("market_perception", market_perception_agent)
    votes = await spawner.spawn_parallel([
        {"agent_type": "market_perception", "symbol": "AAPL"},
        {"agent_type": "flow_perception", "symbol": "AAPL"},
    ])
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Type

from app.council.blackboard import BlackboardState
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)


class TaskSpawner:
    """Dynamic agent spawner with registry, parallel execution, and background tasks."""

    def __init__(self, blackboard: BlackboardState):
        self.blackboard = blackboard
        self._registry: Dict[str, Any] = {}  # agent_name -> agent_module
        self._running: List[asyncio.Task] = []
        self._background: List[asyncio.Task] = []

    def register(self, name: str, agent_module: Any):
        """Register an agent module in the spawner registry.

        The module must have an async `evaluate(symbol, timeframe, features, context)` function.
        """
        self._registry[name] = agent_module

    def register_all_agents(self):
        """Auto-register all 35 council agents (17 core + 18 academic edge swarm)."""
        # Core council agents (17)
        from app.council.agents import (
            market_perception_agent,
            flow_perception_agent,
            regime_agent,
            social_perception_agent,
            news_catalyst_agent,
            youtube_knowledge_agent,
            hypothesis_agent,
            strategy_agent,
            risk_agent,
            execution_agent,
            critic_agent,
            rsi_agent,
            bbv_agent,
            ema_trend_agent,
            intermarket_agent,
            relative_strength_agent,
            cycle_timing_agent,
        )
        self.register("market_perception", market_perception_agent)
        self.register("flow_perception", flow_perception_agent)
        self.register("regime", regime_agent)
        self.register("social_perception", social_perception_agent)
        self.register("news_catalyst", news_catalyst_agent)
        self.register("youtube_knowledge", youtube_knowledge_agent)
        self.register("intermarket", intermarket_agent)
        self.register("rsi", rsi_agent)
        self.register("bbv", bbv_agent)
        self.register("ema_trend", ema_trend_agent)
        self.register("relative_strength", relative_strength_agent)
        self.register("cycle_timing", cycle_timing_agent)
        self.register("hypothesis", hypothesis_agent)
        self.register("strategy", strategy_agent)
        self.register("risk", risk_agent)
        self.register("execution", execution_agent)
        self.register("critic", critic_agent)

        # Academic Edge Swarm agents (18)
        # Each import is wrapped to allow graceful degradation
        self._register_academic_edge_agents()

    def _register_academic_edge_agents(self):
        """Register all academic edge swarm agents with graceful fallback."""
        edge_agents = {
            # P0: GEX / Options Flow Swarm
            "gex_agent": "app.council.agents.gex_agent",
            # P0: Insider Filing Swarm
            "insider_agent": "app.council.agents.insider_agent",
            # P1: Earnings Tone NLP
            "earnings_tone_agent": "app.council.agents.earnings_tone_agent",
            # P1: FinBERT Social Sentiment
            "finbert_sentiment_agent": "app.council.agents.finbert_sentiment_agent",
            # P1: Supply Chain Knowledge Graph
            "supply_chain_agent": "app.council.agents.supply_chain_agent",
            # P2: 13F Institutional Flow
            "institutional_flow_agent": "app.council.agents.institutional_flow_agent",
            # P2: Congressional / Political Trading
            "congressional_agent": "app.council.agents.congressional_agent",
            # P2: Dark Pool Accumulation
            "dark_pool_agent": "app.council.agents.dark_pool_agent",
            # P3: Multi-Agent RL Portfolio Optimizer
            "portfolio_optimizer_agent": "app.council.agents.portfolio_optimizer_agent",
            # P3: Layered Memory (FinMem)
            "layered_memory_agent": "app.council.agents.layered_memory_agent",
            # P4: Alternative Data
            "alt_data_agent": "app.council.agents.alt_data_agent",
            # P4: Cross-Asset Macro Regime
            "macro_regime_agent": "app.council.agents.macro_regime_agent",
        }
        import importlib
        for name, module_path in edge_agents.items():
            try:
                module = importlib.import_module(module_path)
                self.register(name, module)
            except Exception as e:
                logger.debug("Academic edge agent '%s' not available: %s", name, e)

    async def spawn(
        self,
        agent_type: str,
        symbol: str,
        timeframe: str = "1d",
        features: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        model_tier: str = "fast",
        background: bool = False,
    ) -> Optional[AgentVote]:
        """Spawn a single agent.

        Args:
            agent_type: Registered agent name
            symbol: Ticker symbol
            timeframe: Timeframe
            features: Feature dict (defaults to blackboard.raw_features)
            context: Context dict
            model_tier: "fast" for reflexes, "deep" for LLM cortex
            background: If True, runs non-blocking (returns None immediately)

        Returns:
            AgentVote or None if background=True
        """
        module = self._registry.get(agent_type)
        if module is None:
            logger.warning("TaskSpawner: unknown agent type '%s'", agent_type)
            return AgentVote(
                agent_name=agent_type,
                direction="hold",
                confidence=0.0,
                reasoning=f"Unknown agent type: {agent_type}",
                blackboard_ref=self.blackboard.council_decision_id,
            )

        if features is None:
            features = self.blackboard.raw_features
        if context is None:
            context = {}
        context["blackboard"] = self.blackboard
        context["model_tier"] = model_tier

        if background:
            task = asyncio.create_task(self._run_agent(module, symbol, timeframe, features, context))
            self._background.append(task)
            return None

        return await self._run_agent(module, symbol, timeframe, features, context)

    async def spawn_parallel(
        self,
        agent_configs: List[Dict[str, Any]],
    ) -> List[AgentVote]:
        """Spawn multiple agents in parallel.

        Args:
            agent_configs: List of dicts with keys:
                agent_type (required), symbol (required),
                timeframe, features, context, model_tier

        Returns:
            List of AgentVotes in same order as configs
        """
        tasks = []
        for cfg in agent_configs:
            agent_type = cfg["agent_type"]
            module = self._registry.get(agent_type)
            if module is None:
                logger.warning("TaskSpawner: unknown agent '%s', skipping", agent_type)
                tasks.append(self._make_error_vote(agent_type, "Unknown agent type"))
                continue

            symbol = cfg["symbol"]
            timeframe = cfg.get("timeframe", "1d")
            features = cfg.get("features", self.blackboard.raw_features)
            context = cfg.get("context", {})
            context["blackboard"] = self.blackboard
            context["model_tier"] = cfg.get("model_tier", "fast")

            tasks.append(self._run_agent(module, symbol, timeframe, features, context))

        return list(await asyncio.gather(*tasks))

    async def _run_agent(self, module, symbol, timeframe, features, context, timeout: float = None) -> AgentVote:
        """Run a single agent with error handling, timing, and adaptive timeout.

        Args:
            timeout: If provided, overrides the adaptive timeout. If None, uses timeout reflex manager.
        """
        from app.council.reflexes.timeout_reflex import get_timeout_manager

        name = getattr(module, "NAME", getattr(module, "__name__", "unknown"))
        timeout_manager = get_timeout_manager()

        # Check if agent should be skipped due to repeated timeouts
        if timeout_manager.should_skip_agent(name):
            logger.warning("Skipping agent %s due to repeated timeout failures", name)
            return timeout_manager.create_fallback_vote(
                name, "Skipped due to repeated timeouts", self.blackboard.council_decision_id
            )

        # Get adaptive timeout if not manually specified
        if timeout is None:
            timeout = timeout_manager.get_timeout(name)

        start = time.monotonic()
        timed_out = False
        errored = False

        try:
            vote = await asyncio.wait_for(
                module.evaluate(symbol, timeframe, features, context),
                timeout=timeout,
            )
            vote.blackboard_ref = self.blackboard.council_decision_id
            elapsed = (time.monotonic() - start) * 1000
            logger.debug("Agent %s completed in %.0fms (timeout=%.1fs)", name, elapsed, timeout)

            # Record successful execution
            timeout_manager.record_execution(name, elapsed, timed_out=False, error=False)
            return vote

        except asyncio.TimeoutError:
            elapsed = (time.monotonic() - start) * 1000
            timed_out = True
            logger.warning("Agent %s timed out after %.0fms (limit=%.1fs)", name, elapsed, timeout)

            # Record timeout
            timeout_manager.record_execution(name, elapsed, timed_out=True, error=False)

            return timeout_manager.create_fallback_vote(
                name, f"Agent timeout after {elapsed:.0f}ms", self.blackboard.council_decision_id
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            errored = True
            logger.exception("Agent %s failed after %.0fms: %s", name, elapsed, e)

            # Record error
            timeout_manager.record_execution(name, elapsed, timed_out=False, error=True)

            return AgentVote(
                agent_name=name,
                direction="hold",
                confidence=0.0,
                reasoning=f"Agent error: {e}",
                blackboard_ref=self.blackboard.council_decision_id,
            )

    async def _make_error_vote(self, agent_type: str, reason: str) -> AgentVote:
        """Create an error vote for unknown/failed agents."""
        return AgentVote(
            agent_name=agent_type,
            direction="hold",
            confidence=0.0,
            reasoning=reason,
            blackboard_ref=self.blackboard.council_decision_id,
        )

    async def await_background(self) -> List[AgentVote]:
        """Wait for all background tasks to complete and return their votes."""
        if not self._background:
            return []
        results = await asyncio.gather(*self._background, return_exceptions=True)
        votes = []
        for r in results:
            if isinstance(r, AgentVote):
                votes.append(r)
            elif isinstance(r, Exception):
                logger.warning("Background agent failed: %s", r)
        self._background.clear()
        return votes

    @property
    def registered_agents(self) -> List[str]:
        """List of registered agent names."""
        return list(self._registry.keys())
