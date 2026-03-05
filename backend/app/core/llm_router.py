"""Hybrid LLM Router — local Ollama → cloud escalation.

Routes LLM requests through a tiered model stack:
  Tier 1: Local Ollama 3B  (fast, free, ~200ms)
  Tier 2: Local Ollama 14B (better reasoning, ~800ms)
  Tier 3: Local Ollama 32B (best local, ~2s)
  Tier 4: Claude API       (cloud fallback, ~1-3s, costs money)
  Tier 5: Perplexity Sonar (live web context, ~2-4s, costs money)

Selection logic:
  - Simple classification tasks → Tier 1
  - Agent reasoning → Tier 2/3 based on complexity
  - High-stakes or low-confidence → Tier 4 (Claude)
  - Needs live market context → Tier 5 (Perplexity)

Cost tracking enforces a daily budget ceiling for cloud calls.
If PC-2 (Ollama host) is down, automatically escalates to cloud.

Usage:
    from app.core.llm_router import get_llm_router
    router = get_llm_router()
    result = await router.route(prompt="Analyze AAPL", complexity="medium")
"""

import asyncio
import logging
import os
import time
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelTier(str, Enum):
    """LLM model tiers ordered by capability and cost."""
    LOCAL_3B = "local_3b"
    LOCAL_14B = "local_14b"
    LOCAL_32B = "local_32b"
    CLAUDE = "claude"
    PERPLEXITY = "perplexity"


@dataclass
class LLMResponse:
    """Standard response from any LLM tier."""
    text: str
    tier: ModelTier
    model_name: str
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    cached: bool = False
    error: Optional[str] = None


# Approximate cost per 1K tokens (input/output averaged)
COST_PER_1K: Dict[ModelTier, float] = {
    ModelTier.LOCAL_3B: 0.0,
    ModelTier.LOCAL_14B: 0.0,
    ModelTier.LOCAL_32B: 0.0,
    ModelTier.CLAUDE: 0.008,       # ~$8/M tokens blended
    ModelTier.PERPLEXITY: 0.005,   # ~$5/M tokens blended
}

# Model names per tier
MODEL_NAMES: Dict[ModelTier, str] = {
    ModelTier.LOCAL_3B: "llama3.2:3b",
    ModelTier.LOCAL_14B: "qwen2.5:14b",
    ModelTier.LOCAL_32B: "qwen2.5:32b",
    ModelTier.CLAUDE: "claude-sonnet-4-20250514",
    ModelTier.PERPLEXITY: "sonar-pro",
}

# Complexity → default tier mapping
COMPLEXITY_TIER: Dict[str, ModelTier] = {
    "low": ModelTier.LOCAL_3B,
    "medium": ModelTier.LOCAL_14B,
    "high": ModelTier.LOCAL_32B,
    "critical": ModelTier.CLAUDE,
    "live_context": ModelTier.PERPLEXITY,
}


class HybridLLMRouter:
    """Routes LLM requests to the optimal model tier.

    Parameters
    ----------
    ollama_host : str
        Hostname/IP of the Ollama server (PC-2).
    ollama_port : int
        Port for Ollama API.
    claude_api_key : str
        Anthropic API key for cloud fallback.
    perplexity_api_key : str
        Perplexity API key for live context.
    daily_budget_usd : float
        Maximum daily spend on cloud APIs.
    """

    def __init__(
        self,
        ollama_host: Optional[str] = None,
        ollama_port: int = 11434,
        claude_api_key: Optional[str] = None,
        perplexity_api_key: Optional[str] = None,
        daily_budget_usd: float = 5.0,
    ):
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "localhost")
        self.ollama_port = int(os.getenv("OLLAMA_PORT", str(ollama_port)))
        self.ollama_base = f"http://{self.ollama_host}:{self.ollama_port}"
        self.claude_api_key = claude_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.perplexity_api_key = perplexity_api_key or os.getenv("PERPLEXITY_API_KEY", "")
        self.daily_budget_usd = float(os.getenv("LLM_DAILY_BUDGET_USD", str(daily_budget_usd)))

        # Cost tracking
        self._daily_spend: float = 0.0
        self._daily_reset_date: Optional[str] = None
        self._request_count: int = 0
        self._tier_counts: Dict[ModelTier, int] = {t: 0 for t in ModelTier}
        self._total_latency_ms: float = 0.0

        # Health state
        self._ollama_healthy: bool = True
        self._last_ollama_check: float = 0.0
        self._ollama_check_interval: float = 30.0  # seconds

        logger.info(
            "HybridLLMRouter initialized: ollama=%s:%d, claude=%s, perplexity=%s, budget=$%.2f/day",
            self.ollama_host,
            self.ollama_port,
            "configured" if self.claude_api_key else "not set",
            "configured" if self.perplexity_api_key else "not set",
            self.daily_budget_usd,
        )

    async def route(
        self,
        prompt: str,
        complexity: str = "medium",
        system_prompt: Optional[str] = None,
        force_tier: Optional[ModelTier] = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Route a prompt to the optimal LLM tier.

        Parameters
        ----------
        prompt : str
            The user/agent prompt.
        complexity : str
            One of "low", "medium", "high", "critical", "live_context".
        system_prompt : str, optional
            System message for the LLM.
        force_tier : ModelTier, optional
            Override automatic tier selection.
        max_tokens : int
            Max response tokens.
        temperature : float
            Sampling temperature.

        Returns
        -------
        LLMResponse with the model's output and metadata.
        """
        self._check_daily_reset()

        # Determine tier
        tier = force_tier or COMPLEXITY_TIER.get(complexity, ModelTier.LOCAL_14B)

        # If Ollama is down, escalate local tiers to cloud
        if tier in (ModelTier.LOCAL_3B, ModelTier.LOCAL_14B, ModelTier.LOCAL_32B):
            if not await self._check_ollama_health():
                logger.warning("Ollama unavailable, escalating to cloud")
                tier = ModelTier.CLAUDE if self.claude_api_key else tier

        # Budget gate for cloud tiers
        if tier in (ModelTier.CLAUDE, ModelTier.PERPLEXITY):
            if self._daily_spend >= self.daily_budget_usd:
                logger.warning(
                    "Daily budget exhausted ($%.2f/$%.2f), falling back to local",
                    self._daily_spend, self.daily_budget_usd,
                )
                tier = ModelTier.LOCAL_32B if self._ollama_healthy else ModelTier.LOCAL_14B

        # Dispatch
        start = time.monotonic()
        try:
            if tier in (ModelTier.LOCAL_3B, ModelTier.LOCAL_14B, ModelTier.LOCAL_32B):
                response = await self._call_ollama(
                    prompt, system_prompt, tier, max_tokens, temperature
                )
            elif tier == ModelTier.CLAUDE:
                response = await self._call_claude(
                    prompt, system_prompt, max_tokens, temperature
                )
            elif tier == ModelTier.PERPLEXITY:
                response = await self._call_perplexity(
                    prompt, system_prompt, max_tokens, temperature
                )
            else:
                response = LLMResponse(
                    text="", tier=tier, model_name="unknown",
                    latency_ms=0, error=f"Unknown tier: {tier}",
                )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.exception("LLM call failed (tier=%s): %s", tier, e)
            response = LLMResponse(
                text="", tier=tier,
                model_name=MODEL_NAMES.get(tier, "unknown"),
                latency_ms=elapsed, error=str(e),
            )

        # Track metrics
        self._request_count += 1
        self._tier_counts[response.tier] = self._tier_counts.get(response.tier, 0) + 1
        self._total_latency_ms += response.latency_ms
        self._daily_spend += response.cost_usd

        return response

    async def _call_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        tier: ModelTier,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Call local Ollama server."""
        import httpx

        model = MODEL_NAMES[tier]
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.ollama_base}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        elapsed = (time.monotonic() - start) * 1000
        text = data.get("message", {}).get("content", "")
        tokens_in = data.get("prompt_eval_count", 0)
        tokens_out = data.get("eval_count", 0)

        return LLMResponse(
            text=text,
            tier=tier,
            model_name=model,
            latency_ms=round(elapsed, 1),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=0.0,
        )

    async def _call_claude(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Call Anthropic Claude API."""
        import httpx

        if not self.claude_api_key:
            return LLMResponse(
                text="", tier=ModelTier.CLAUDE,
                model_name=MODEL_NAMES[ModelTier.CLAUDE],
                latency_ms=0, error="ANTHROPIC_API_KEY not configured",
            )

        messages = [{"role": "user", "content": prompt}]
        body: Dict[str, Any] = {
            "model": MODEL_NAMES[ModelTier.CLAUDE],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system_prompt:
            body["system"] = system_prompt

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.claude_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        elapsed = (time.monotonic() - start) * 1000
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        tokens_in = data.get("usage", {}).get("input_tokens", 0)
        tokens_out = data.get("usage", {}).get("output_tokens", 0)
        cost = ((tokens_in + tokens_out) / 1000) * COST_PER_1K[ModelTier.CLAUDE]

        return LLMResponse(
            text=text,
            tier=ModelTier.CLAUDE,
            model_name=MODEL_NAMES[ModelTier.CLAUDE],
            latency_ms=round(elapsed, 1),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=round(cost, 6),
        )

    async def _call_perplexity(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Call Perplexity Sonar API for live web context."""
        import httpx

        if not self.perplexity_api_key:
            return LLMResponse(
                text="", tier=ModelTier.PERPLEXITY,
                model_name=MODEL_NAMES[ModelTier.PERPLEXITY],
                latency_ms=0, error="PERPLEXITY_API_KEY not configured",
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL_NAMES[ModelTier.PERPLEXITY],
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        elapsed = (time.monotonic() - start) * 1000
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        tokens_in = data.get("usage", {}).get("prompt_tokens", 0)
        tokens_out = data.get("usage", {}).get("completion_tokens", 0)
        cost = ((tokens_in + tokens_out) / 1000) * COST_PER_1K[ModelTier.PERPLEXITY]

        return LLMResponse(
            text=text,
            tier=ModelTier.PERPLEXITY,
            model_name=MODEL_NAMES[ModelTier.PERPLEXITY],
            latency_ms=round(elapsed, 1),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=round(cost, 6),
        )

    async def _check_ollama_health(self) -> bool:
        """Check if Ollama server is reachable (cached for 30s)."""
        now = time.time()
        if now - self._last_ollama_check < self._ollama_check_interval:
            return self._ollama_healthy

        self._last_ollama_check = now
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.ollama_base}/api/tags")
                self._ollama_healthy = resp.status_code == 200
        except Exception:
            self._ollama_healthy = False

        return self._ollama_healthy

    def _check_daily_reset(self) -> None:
        """Reset daily spend at midnight UTC."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._daily_reset_date != today:
            self._daily_reset_date = today
            self._daily_spend = 0.0

    def get_status(self) -> Dict[str, Any]:
        """Return router status for health endpoint."""
        avg_latency = (
            self._total_latency_ms / self._request_count
            if self._request_count > 0
            else 0
        )
        return {
            "ollama_host": f"{self.ollama_host}:{self.ollama_port}",
            "ollama_healthy": self._ollama_healthy,
            "claude_configured": bool(self.claude_api_key),
            "perplexity_configured": bool(self.perplexity_api_key),
            "daily_budget_usd": self.daily_budget_usd,
            "daily_spend_usd": round(self._daily_spend, 4),
            "budget_remaining_usd": round(self.daily_budget_usd - self._daily_spend, 4),
            "total_requests": self._request_count,
            "tier_counts": {t.value: c for t, c in self._tier_counts.items()},
            "avg_latency_ms": round(avg_latency, 1),
        }


# Module-level singleton
_router_instance: Optional[HybridLLMRouter] = None


def get_llm_router() -> HybridLLMRouter:
    """Get or create the global HybridLLMRouter singleton."""
    global _router_instance
    if _router_instance is None:
        _router_instance = HybridLLMRouter()
    return _router_instance
