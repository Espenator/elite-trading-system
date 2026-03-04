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
        """Auto-register all 8 council agents."""
        from app.council.agents import (
            market_perception_agent,
            flow_perception_agent,
            regime_agent,
            hypothesis_agent,
            strategy_agent,
            risk_agent,
            execution_agent,
            critic_agent,
        )
        self.register("market_perception", market_perception_agent)
        self.register("flow_perception", flow_perception_agent)
        self.register("regime", regime_agent)
        self.register("hypothesis", hypothesis_agent)
        self.register("strategy", strategy_agent)
        self.register("risk", risk_agent)
        self.register("execution", execution_agent)
        self.register("critic", critic_agent)

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

    async def _run_agent(self, module, symbol, timeframe, features, context) -> AgentVote:
        """Run a single agent with error handling and timing."""
        name = getattr(module, "NAME", getattr(module, "__name__", "unknown"))
        start = time.monotonic()
        try:
            vote = await module.evaluate(symbol, timeframe, features, context)
            vote.blackboard_ref = self.blackboard.council_decision_id
            elapsed = (time.monotonic() - start) * 1000
            logger.debug("Agent %s completed in %.0fms", name, elapsed)
            return vote
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.exception("Agent %s failed after %.0fms: %s", name, elapsed, e)
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
