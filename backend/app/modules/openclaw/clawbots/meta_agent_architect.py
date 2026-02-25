#!/usr/bin/env python3
"""
meta_agent_architect.py - The Code Generator (Meta-Agent)
OpenClaw Autonomous Meta-Evolution Layer

Generates new OpenClaw agents on the fly when market regimes change.
Prompts a local LLM to produce a complete agent specification including
a SOUL.md system prompt and skills.py code tailored to the regime.

Publishes SPAWN commands to: Topic.ALPHA_SIGNALS (meta_spawn type)
Subscribes to: Topic.REGIME_UPDATES
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from typing import Dict, Optional, Any

from streaming_engine import (
    Blackboard, BlackboardMessage, Topic, get_blackboard,
)

try:
    from llm_client import call_llm
except ImportError:
    call_llm = None

logger = logging.getLogger(__name__)

# ============================================================
# ARCHITECT LLM SYSTEM PROMPT - Code Generation Soul
# ============================================================
ARCHITECT_SYSTEM_PROMPT = """You are the OpenClaw Meta-Architect, an expert Python developer
specialized in writing autonomous trading agent modules.

When given a Market Regime, you generate a complete agent specification
that can be deployed into the OpenClaw swarm immediately.

RULES FOR CODE GENERATION:
1. IMPORTS: Only use standard library + these repo modules:
   streaming_engine (Blackboard, BlackboardMessage, Topic, get_blackboard)
   llm_client (call_llm), config, alpaca_client, finviz_scanner
2. SAFETY: Always wrap external calls in try/except. Never use eval(),
   exec(), os.system(), subprocess, or __import__. No file writes.
3. PATTERN: Follow the existing agent pattern:
   - Class with AGENT_ID, __init__(self, blackboard), async run(self)
   - Subscribe to topics, process messages, publish results
   - Include heartbeat calls and graceful CancelledError handling
4. LOGGING: Use logger = logging.getLogger(__name__)
5. NO HARDCODED SECRETS: Never embed API keys or passwords.

OUTPUT FORMAT (strict JSON):
{
  "agent_name": "agent_regime_specific_name",
  "soul_md": "A 2-3 sentence description of the agent's purpose and strategy.",
  "skills_py": "Complete Python code as a single string. Use \\n for newlines."
}

RESPOND WITH VALID JSON ONLY. No markdown fences, no explanation.
"""

# Safety: patterns that must NOT appear in generated code
FORBIDDEN_PATTERNS = [
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\b__import__\s*\(",
    r"\bos\.system\s*\(",
    r"\bsubprocess\b",
    r"\bopen\s*\([^)]*['\"]w['\"]",
    r"\brm\s+-rf\b",
    r"\bshutil\.rmtree\b",
    r"\bAPI_KEY\s*=\s*['\"]",
    r"\bSECRET\s*=\s*['\"]",
]

MAX_CODE_LENGTH = 15_000  # Reject suspiciously large code blocks
SPAWN_COOLDOWN_SECONDS = 600  # Max one spawn per 10 minutes
MAX_ACTIVE_SPAWNS = 5  # Don't let the swarm grow unbounded


class MetaAgentArchitect:
    """
    Meta-layer agent that generates new trading agents
    dynamically based on market regime changes.
    """

    AGENT_ID = "meta_architect"

    def __init__(self, blackboard: Blackboard):
        self.bb = blackboard
        self._last_spawn_time: float = 0.0
        self._spawned_agents: Dict[str, Dict] = {}
        self._last_regime: str = ""
        self._stats = {
            "regimes_received": 0,
            "spawn_requests": 0,
            "code_validations_failed": 0,
            "llm_failures": 0,
        }
        logger.info("[MetaArchitect] Initialized - Code generator online")

    # ----------------------------------------------------------
    # LLM Code Generation
    # ----------------------------------------------------------
    async def _generate_agent_spec(self, regime: Dict) -> Optional[Dict]:
        """Prompt the LLM to generate a new agent for the regime."""
        if not call_llm:
            logger.warning("[MetaArchitect] llm_client not available")
            return None

        user_prompt = (
            f"Generate an OpenClaw trading agent optimized for this regime:\n"
            f"Market_Regime: {regime.get('Market_Regime')}\n"
            f"Directional_Bias: {regime.get('Directional_Bias')}\n"
            f"Conviction: {regime.get('Conviction')}\n\n"
            f"The agent should subscribe to Topic.BAR_UPDATES and "
            f"publish scored signals to Topic.SCORED_SIGNALS.\n"
            f"Output strict JSON with agent_name, soul_md, skills_py."
        )

        try:
            response = call_llm(
                task="trade_rationale",
                prompt=user_prompt,
                system_prompt=ARCHITECT_SYSTEM_PROMPT,
            )
            if not response:
                self._stats["llm_failures"] += 1
                return None

            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            spec = json.loads(text)
            return spec

        except json.JSONDecodeError as e:
            logger.error(f"[MetaArchitect] JSON parse failure: {e}")
            self._stats["llm_failures"] += 1
            return None
        except Exception as e:
            logger.error(f"[MetaArchitect] LLM error: {e}")
            self._stats["llm_failures"] += 1
            return None

    # ----------------------------------------------------------
    # Safety Validation
    # ----------------------------------------------------------
    def _validate_agent_name(self, name: str) -> bool:
        """Ensure agent name is safe for filesystem and process use."""
        if not name or len(name) > 60:
            return False
        # Only allow alphanumeric, hyphens, underscores
        if not re.match(r"^[a-z][a-z0-9_-]{2,59}$", name):
            return False
        # Block path traversal
        if ".." in name or "/" in name or "\\" in name:
            return False
        return True

    def _validate_code(self, code: str) -> tuple:
        """
        Scan generated code for forbidden patterns.
        Returns (is_safe, reason).
        """
        if not code or len(code) > MAX_CODE_LENGTH:
            return False, f"code_length_{len(code) if code else 0}"

        for pattern in FORBIDDEN_PATTERNS:
            match = re.search(pattern, code)
            if match:
                return False, f"forbidden_pattern: {match.group()}"

        # Must contain the expected class structure
        if "class " not in code:
            return False, "missing_class_definition"
        if "async def run" not in code:
            return False, "missing_async_run_method"
        if "AGENT_ID" not in code:
            return False, "missing_AGENT_ID"

        return True, "passed"

    def _validate_spec(self, spec: Dict) -> tuple:
        """Full validation of the LLM-generated agent spec."""
        name = spec.get("agent_name", "")
        if not self._validate_agent_name(name):
            return False, f"invalid_agent_name: {name}"

        soul = spec.get("soul_md", "")
        if not soul or len(soul) < 10:
            return False, "missing_or_empty_soul_md"

        code = spec.get("skills_py", "")
        is_safe, reason = self._validate_code(code)
        if not is_safe:
            return False, f"code_validation_failed: {reason}"

        return True, "passed"

    # ----------------------------------------------------------
    # Spawn Command
    # ----------------------------------------------------------
    async def _publish_spawn(self, spec: Dict) -> None:
        """Publish a SPAWN command for the swarm daemon."""
        agent_name = spec["agent_name"]
        self._spawned_agents[agent_name] = {
            "spawned_at": datetime.now().isoformat(),
            "regime": self._last_regime,
        }

        payload = {
            "signal_type": "meta_spawn",
            "command": "SPAWN",
            "agent_name": agent_name,
            "soul_md": spec["soul_md"],
            "skills_py": spec["skills_py"],
            "spawned_by": self.AGENT_ID,
            "timestamp": datetime.now().isoformat(),
        }

        await self.bb.publish(BlackboardMessage(
            topic=Topic.ALPHA_SIGNALS,
            payload=payload,
            source_agent=self.AGENT_ID,
            priority=2,
            ttl_seconds=600,
        ))

        self._stats["spawn_requests"] += 1
        logger.info(f"[MetaArchitect] SPAWN command: {agent_name}")

    # ----------------------------------------------------------
    # Main Event Loop
    # ----------------------------------------------------------
    async def run(self) -> None:
        """Listen for regime changes, generate and spawn new agents."""
        regime_q = await self.bb.subscribe(
            Topic.REGIME_UPDATES, self.AGENT_ID
        )
        logger.info("[MetaArchitect] Listening for regime changes...")

        while True:
            try:
                msg = await asyncio.wait_for(regime_q.get(), timeout=15.0)

                if not isinstance(msg, BlackboardMessage) or msg.is_expired():
                    continue

                regime = msg.payload
                current = regime.get("Market_Regime", "")
                self._stats["regimes_received"] += 1

                # Only spawn on regime CHANGE
                if current == self._last_regime:
                    continue
                self._last_regime = current

                # Cooldown
                now = time.time()
                if now - self._last_spawn_time < SPAWN_COOLDOWN_SECONDS:
                    logger.info("[MetaArchitect] Spawn cooldown active")
                    continue

                # Cap active spawns
                if len(self._spawned_agents) >= MAX_ACTIVE_SPAWNS:
                    logger.warning("[MetaArchitect] Max active spawns reached")
                    continue

                logger.info(
                    f"[MetaArchitect] Regime change to {current}. "
                    f"Generating new agent..."
                )

                spec = await self._generate_agent_spec(regime)
                if not spec:
                    continue

                is_valid, reason = self._validate_spec(spec)
                if not is_valid:
                    self._stats["code_validations_failed"] += 1
                    logger.warning(
                        f"[MetaArchitect] Spec validation FAILED: {reason}"
                    )
                    continue

                await self._publish_spawn(spec)
                self._last_spawn_time = now

            except asyncio.TimeoutError:
                await self.bb.heartbeat(self.AGENT_ID)
            except asyncio.CancelledError:
                logger.info("[MetaArchitect] Shutting down")
                break
            except Exception as e:
                logger.error(f"[MetaArchitect] Loop error: {e}")
                await asyncio.sleep(10)

    def get_status(self) -> Dict:
        return {
            "agent_id": self.AGENT_ID,
            "spawned_agents": dict(self._spawned_agents),
            "last_regime": self._last_regime,
            "stats": dict(self._stats),
        }
