#!/usr/bin/env python3
"""
clawbots/__init__.py - OpenClaw Hunter-Killer Swarm Package
OpenClaw Hierarchical Synthesis Architecture

Exposes the multi-tier agent swarm for the Apex short-side pipeline:
  Tier 2: ApexOrchestratorAgent    - Global Brain / Regime Synthesizer
  Tier 3: RelativeWeaknessAgent    - Weakness Scanner
  Tier 3: ShortBasketCompilerAgent - Execution Formatter
  Meta:   MetaAgentArchitect       - Autonomous Code Generator

Usage:
    from clawbots import spawn_swarm
    agents = await spawn_swarm(blackboard)
"""

import asyncio
import logging
from typing import Dict, List, Any

from ..streaming.streaming_engine import Blackboard, get_blackboard

from .agent_apex_orchestrator import ApexOrchestratorAgent
from .agent_relative_weakness import RelativeWeaknessAgent
from .agent_short_basket_compiler import ShortBasketCompilerAgent
from .meta_agent_architect import MetaAgentArchitect

logger = logging.getLogger(__name__)

__all__ = [
    "ApexOrchestratorAgent",
    "RelativeWeaknessAgent",
    "ShortBasketCompilerAgent",
    "MetaAgentArchitect",
    "spawn_swarm",
    "shutdown_swarm",
    "get_swarm_status",
]

# Global registry for running agent instances
_active_agents: Dict[str, Any] = {}
_agent_tasks: Dict[str, asyncio.Task] = {}


async def spawn_swarm(
    blackboard: Blackboard = None,
    enable_meta: bool = True,
) -> Dict[str, Any]:
    """
    Spawn all Hunter-Killer swarm agents as concurrent async tasks.
    Returns a dict of agent_id -> agent_instance for diagnostics.

    Spawn order matters:
      1. ApexOrchestrator (must be online first to declare regimes)
      2. RelativeWeakness (waits for regime triggers)
      3. ShortBasketCompiler (waits for weakness scan results)
      4. MetaAgentArchitect (optional, listens for regime changes)
    """
    global _active_agents, _agent_tasks

    if blackboard is None:
        blackboard = get_blackboard()

    # Instantiate core agents
    apex = ApexOrchestratorAgent(blackboard)
    weakness = RelativeWeaknessAgent(blackboard)
    compiler = ShortBasketCompilerAgent(blackboard)

    _active_agents = {
        apex.AGENT_ID: apex,
        weakness.AGENT_ID: weakness,
        compiler.AGENT_ID: compiler,
    }

    # Launch core agents as concurrent tasks
    _agent_tasks = {
        apex.AGENT_ID: asyncio.create_task(
            apex.run(), name=f"clawbot_{apex.AGENT_ID}"
        ),
        weakness.AGENT_ID: asyncio.create_task(
            weakness.run(), name=f"clawbot_{weakness.AGENT_ID}"
        ),
        compiler.AGENT_ID: asyncio.create_task(
            compiler.run(), name=f"clawbot_{compiler.AGENT_ID}"
        ),
    }

    # Optional: spawn the meta-evolution layer
    if enable_meta:
        meta = MetaAgentArchitect(blackboard)
        _active_agents[meta.AGENT_ID] = meta
        _agent_tasks[meta.AGENT_ID] = asyncio.create_task(
            meta.run(), name=f"clawbot_{meta.AGENT_ID}"
        )

    logger.info(
        f"[ClawbotSwarm] Spawned {len(_active_agents)} agents: "
        f"{', '.join(_active_agents.keys())}"
    )
    return _active_agents


async def shutdown_swarm() -> None:
    """Gracefully cancel all running swarm agent tasks."""
    global _agent_tasks
    for agent_id, task in _agent_tasks.items():
        if not task.done():
            task.cancel()
            logger.info(f"[ClawbotSwarm] Cancelled {agent_id}")
    # Wait for all tasks to finish
    if _agent_tasks:
        await asyncio.gather(*_agent_tasks.values(), return_exceptions=True)
    _agent_tasks.clear()
    _active_agents.clear()
    logger.info("[ClawbotSwarm] All agents shut down")


def get_swarm_status() -> Dict[str, Any]:
    """Collect diagnostics from all active swarm agents."""
    status = {}
    for agent_id, agent in _active_agents.items():
        try:
            agent_status = agent.get_status()
            task = _agent_tasks.get(agent_id)
            agent_status["task_alive"] = task is not None and not task.done()
            status[agent_id] = agent_status
        except Exception as e:
            status[agent_id] = {"error": str(e)}
    return {
        "swarm_name": "hunter_killer",
        "agents_active": len(_active_agents),
        "agents": status,
    }
