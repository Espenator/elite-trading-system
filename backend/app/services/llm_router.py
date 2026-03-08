"""
Multi-Tier LLM Router — unified async routing across Ollama, Perplexity, and Claude.

Three tiers:
    brainstem  — Ollama (local, <500ms, free)
    cortex     — Perplexity Sonar Pro (web-grounded, <3s)
    deep_cortex — Claude (deep reasoning, <10s)

Features:
    - Automatic fallback chains per tier
    - Per-provider circuit breaker (3 fails in 60s → skip 5 min)
    - Rate limiting per provider
    - Cost tracking in DuckDB
    - Task-to-tier routing map

Usage:
    from app.services.llm_router import get_llm_router
    router = get_llm_router()
    result = await router.route("brainstem", messages, task="regime_classification")
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# ── Tier definitions ──────────────────────────────────────────────────────────

class Tier(str, Enum):
    BRAINSTEM = "brainstem"
    CORTEX = "cortex"
    DEEP_CORTEX = "deep_cortex"


# Task → optimal tier mapping
TASK_TIER_MAP: Dict[str, Tier] = {
    # Brainstem (fast, local)
    "regime_classification": Tier.BRAINSTEM,
    "signal_scoring": Tier.BRAINSTEM,
    "feature_summary": Tier.BRAINSTEM,
    "quick_hypothesis": Tier.BRAINSTEM,
    "risk_check": Tier.BRAINSTEM,
    # Cortex (web-grounded)
    "news_analysis": Tier.CORTEX,
    "earnings_context": Tier.CORTEX,
    "sector_rotation": Tier.CORTEX,
    "macro_context": Tier.CORTEX,
    "fear_greed_context": Tier.CORTEX,
    "institutional_flow": Tier.CORTEX,
    "pattern_context": Tier.CORTEX,
    "breaking_news": Tier.CORTEX,
    "geopolitical_scan": Tier.CORTEX,
    # Deep cortex (reasoning)
    "strategy_critic": Tier.DEEP_CORTEX,
    "strategy_evolution": Tier.DEEP_CORTEX,
    "deep_postmortem": Tier.DEEP_CORTEX,
    "trade_thesis": Tier.DEEP_CORTEX,
    "overnight_analysis": Tier.DEEP_CORTEX,
    "directive_evolution": Tier.DEEP_CORTEX,
    "pattern_interpretation": Tier.DEEP_CORTEX,
}

# Fallback chains: if primary fails, try these in order
FALLBACK_CHAINS: Dict[Tier, List[Tier]] = {
    Tier.BRAINSTEM: [Tier.CORTEX, Tier.DEEP_CORTEX],
    Tier.CORTEX: [Tier.DEEP_CORTEX, Tier.BRAINSTEM],
    Tier.DEEP_CORTEX: [Tier.CORTEX, Tier.BRAINSTEM],
}

# Approximate cost per 1K tokens (input/output) for tracking
COST_PER_1K: Dict[Tier, Dict[str, float]] = {
    Tier.BRAINSTEM: {"input": 0.0, "output": 0.0},
    Tier.CORTEX: {"input": 0.003, "output": 0.015},
    Tier.DEEP_CORTEX: {"input": 0.003, "output": 0.015},
}


# ── Per-provider circuit breaker ─────────────────────────────────────────────

@dataclass
class ProviderCircuitBreaker:
    """Circuit breaker: 3 failures in 60s → skip for 5 min."""
    failure_threshold: int = 3
    failure_window: float = 60.0
    recovery_timeout: float = 300.0
    _failures: List[float] = field(default_factory=list)
    _open_until: float = 0.0

    def record_failure(self):
        now = time.time()
        self._failures.append(now)
        # Trim old failures outside window
        cutoff = now - self.failure_window
        self._failures = [t for t in self._failures if t > cutoff]
        if len(self._failures) >= self.failure_threshold:
            self._open_until = now + self.recovery_timeout
            logger.warning("Circuit breaker OPEN until %.0f", self._open_until)

    def record_success(self):
        self._failures.clear()
        self._open_until = 0.0

    def is_open(self) -> bool:
        if self._open_until == 0.0:
            return False
        if time.time() >= self._open_until:
            self._open_until = 0.0
            self._failures.clear()
            return False
        return True


# ── Rate limiter ──────────────────────────────────────────────────────────────

class AsyncRateLimiter:
    """Simple async token-bucket rate limiter."""

    def __init__(self, rate: float = 2.0, burst: int = 5):
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: float = 30.0) -> bool:
        deadline = time.time() + timeout
        while True:
            async with self._lock:
                now = time.time()
                elapsed = now - self._last_refill
                self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
                self._last_refill = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True
            if time.time() >= deadline:
                return False
            await asyncio.sleep(0.05)


# ── LLM Router ───────────────────────────────────────────────────────────────

@dataclass
class LLMResponse:
    """Standardized response from any LLM tier."""
    content: str
    tier: str
    model: str
    task: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    fallback_used: bool = False
    error: str = ""
    citations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "tier": self.tier,
            "model": self.model,
            "task": self.task,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "fallback_used": self.fallback_used,
            "error": self.error,
            "citations": self.citations,
        }


# Tier → provider name mapping for health monitor
TIER_PROVIDER_MAP: Dict[Tier, str] = {
    Tier.BRAINSTEM: "ollama",
    Tier.CORTEX: "perplexity",
    Tier.DEEP_CORTEX: "anthropic",
}


class LLMRouter:
    """Unified async LLM router with fallback, circuit breaker, and cost tracking."""

    def __init__(self):
        self._circuits: Dict[Tier, ProviderCircuitBreaker] = {
            t: ProviderCircuitBreaker() for t in Tier
        }
        self._limiters: Dict[Tier, AsyncRateLimiter] = {
            Tier.BRAINSTEM: AsyncRateLimiter(rate=20.0, burst=40),   # 4x (2-PC Ollama pool)
            Tier.CORTEX: AsyncRateLimiter(rate=3.0, burst=8),        # 3x
            Tier.DEEP_CORTEX: AsyncRateLimiter(rate=1.0, burst=4),   # 2x
        }
        self._stats: Dict[str, int] = {
            "brainstem_calls": 0, "cortex_calls": 0, "deep_cortex_calls": 0,
            "fallbacks": 0, "failures": 0, "total_cost_usd_cents": 0,
        }
        # Lazy import to avoid circular
        self._health_monitor = None

    @property
    def health_monitor(self):
        if self._health_monitor is None:
            from app.services.llm_health_monitor import get_llm_health_monitor
            self._health_monitor = get_llm_health_monitor()
        return self._health_monitor

    def get_tier_for_task(self, task: str) -> Tier:
        """Map a task name to its optimal tier."""
        return TASK_TIER_MAP.get(task, Tier.BRAINSTEM)

    async def route(
        self,
        tier: str | Tier,
        messages: List[Dict[str, str]],
        task: str = "general",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        json_mode: bool = False,
        timeout: float = None,
    ) -> LLMResponse:
        """Route a request to a specific tier."""
        if isinstance(tier, str):
            tier = Tier(tier)

        provider = TIER_PROVIDER_MAP.get(tier, tier.value)
        t0 = time.time()
        try:
            content, model, tokens_in, tokens_out, citations = await self._call_tier(
                tier, messages, temperature, max_tokens, json_mode, timeout, task=task
            )
            latency = (time.time() - t0) * 1000
            self._circuits[tier].record_success()
            self._stats[f"{tier.value}_calls"] += 1
            self.health_monitor.record_success(provider)

            # Check if circuit was previously open and just recovered
            if not self._circuits[tier].is_open():
                self.health_monitor.record_circuit_breaker_closed(provider)

            cost = self._estimate_cost(tier, tokens_in, tokens_out)
            self._stats["total_cost_usd_cents"] += int(cost * 100)

            return LLMResponse(
                content=content, tier=tier.value, model=model, task=task,
                latency_ms=latency, input_tokens=tokens_in,
                output_tokens=tokens_out, cost_usd=cost, citations=citations,
            )
        except Exception as e:
            latency = (time.time() - t0) * 1000
            self._circuits[tier].record_failure()
            self._stats["failures"] += 1
            logger.warning("LLM tier %s failed: %s", tier.value, e)

            # ── Classify error and notify health monitor ──
            err_str = str(e).lower()
            http_status = getattr(e, 'status_code', 0) or self._extract_status(err_str)

            if http_status == 429 or 'rate_limit' in err_str or 'rate limit' in err_str:
                retry_after = self._extract_retry_after(err_str)
                self.health_monitor.record_rate_limit(
                    provider, http_status=429, message=str(e)[:200],
                    retry_after=retry_after,
                )
            elif http_status in (401, 403) or 'authentication' in err_str or 'auth' in err_str or 'invalid.*key' in err_str:
                self.health_monitor.record_auth_failure(
                    provider, message=str(e)[:200], http_status=http_status or 401,
                )
            elif http_status in (529, 503) or 'overloaded' in err_str or 'capacity' in err_str:
                self.health_monitor.record_overloaded(
                    provider, message=str(e)[:200], http_status=http_status or 529,
                )
            else:
                self.health_monitor.record_failure(provider, str(e)[:200], http_status)

            # Check if circuit breaker just opened
            if self._circuits[tier].is_open():
                self.health_monitor.record_circuit_breaker_opened(provider)

            return LLMResponse(
                content="", tier=tier.value, model="", task=task,
                latency_ms=latency, error=str(e),
            )

    async def route_with_fallback(
        self,
        tier: str | Tier,
        messages: List[Dict[str, str]],
        task: str = "general",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Route with automatic fallback chain on failure."""
        if isinstance(tier, str):
            tier = Tier(tier)

        # Try primary
        result = await self.route(tier, messages, task, temperature, max_tokens, json_mode)
        if result.content and not result.error:
            return result

        # Fallback chain
        for fallback_tier in FALLBACK_CHAINS.get(tier, []):
            if self._circuits[fallback_tier].is_open():
                continue
            logger.info("Falling back from %s to %s for task %s", tier.value, fallback_tier.value, task)
            result = await self.route(fallback_tier, messages, task, temperature, max_tokens, json_mode)
            if result.content and not result.error:
                result.fallback_used = True
                self._stats["fallbacks"] += 1
                return result

        logger.error("All tiers exhausted for task %s", task)
        self.health_monitor.record_all_tiers_exhausted(task)
        return LLMResponse(
            content="", tier=tier.value, model="", task=task,
            latency_ms=0, error="all_tiers_exhausted",
        )

    async def parallel_query(
        self,
        queries: List[Dict[str, Any]],
    ) -> List[LLMResponse]:
        """Execute multiple queries across tiers in parallel.

        Each query dict: {"tier": str, "messages": [...], "task": str, ...}
        """
        tasks = []
        for q in queries:
            tasks.append(
                self.route_with_fallback(
                    tier=q["tier"],
                    messages=q["messages"],
                    task=q.get("task", "general"),
                    temperature=q.get("temperature", 0.3),
                    max_tokens=q.get("max_tokens", 2048),
                    json_mode=q.get("json_mode", False),
                )
            )
        return await asyncio.gather(*tasks)

    # ── Internal tier dispatch ────────────────────────────────────────────────

    async def _call_tier(
        self,
        tier: Tier,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        timeout: float | None,
        task: str = "general",
    ) -> tuple:
        """Dispatch to the appropriate provider. Returns (content, model, in_tok, out_tok, citations)."""
        if self._circuits[tier].is_open():
            raise RuntimeError(f"Circuit breaker open for {tier.value}")

        if not await self._limiters[tier].acquire(timeout=10):
            raise RuntimeError(f"Rate limit exceeded for {tier.value}")

        if tier == Tier.BRAINSTEM:
            return await self._call_ollama(messages, temperature, max_tokens, json_mode, timeout, task=task)
        elif tier == Tier.CORTEX:
            return await self._call_perplexity(messages, temperature, max_tokens, timeout)
        elif tier == Tier.DEEP_CORTEX:
            return await self._call_claude(messages, temperature, max_tokens, timeout)
        else:
            raise ValueError(f"Unknown tier: {tier}")

    async def _call_ollama(
        self, messages, temperature, max_tokens, json_mode, timeout,
        task: str = "general",
    ) -> tuple:
        """Call Ollama via OpenAI-compatible API with telemetry-aware routing.

        When LLMDispatcher is enabled, it determines the best node and model
        based on GPU telemetry, model pinning, and task affinity. Falls back
        to settings.OLLAMA_BASE_URL if the dispatcher is unavailable.
        """
        import httpx

        # Default: use settings
        base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        model = settings.OLLAMA_MODEL

        # Try LLMDispatcher for telemetry-aware routing
        dispatch_decision = None
        try:
            from app.services.llm_dispatcher import get_llm_dispatcher
            dispatcher = get_llm_dispatcher()
            if dispatcher._enabled:
                dispatch_decision = dispatcher.dispatch(model=model, task=task)
                base_url = dispatch_decision.target_url or base_url
                if dispatch_decision.degraded:
                    model = dispatch_decision.model
                logger.debug(
                    "LLM dispatch: %s → %s model=%s reason=%s",
                    task, base_url, model, dispatch_decision.reason,
                )
        except Exception as e:
            logger.debug("LLMDispatcher unavailable, using default: %s", e)

        url = f"{base_url}/v1/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        effective_timeout = timeout or 30.0
        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=effective_timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
            latency_ms = (time.time() - t0) * 1000

            # Report success to dispatcher
            if dispatch_decision:
                try:
                    from app.services.llm_dispatcher import get_llm_dispatcher
                    get_llm_dispatcher().report_success(base_url, latency_ms)
                except Exception:
                    pass
        except Exception as e:
            # Report error to dispatcher
            if dispatch_decision:
                try:
                    from app.services.llm_dispatcher import get_llm_dispatcher
                    get_llm_dispatcher().report_error(base_url)
                except Exception:
                    pass
            raise

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return (
            content, model,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            [],
        )

    async def _call_perplexity(
        self, messages, temperature, max_tokens, timeout
    ) -> tuple:
        """Call Perplexity Sonar Pro API."""
        import httpx

        api_key = settings.PERPLEXITY_API_KEY
        if not api_key:
            raise RuntimeError("PERPLEXITY_API_KEY not configured")

        base_url = settings.PERPLEXITY_BASE_URL.rstrip("/")
        model = settings.PERPLEXITY_MODEL
        url = f"{base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        effective_timeout = timeout or 30.0
        async with httpx.AsyncClient(timeout=effective_timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)

            # Parse rate limit headers before raise_for_status
            self._parse_rate_limit_headers(resp, "perplexity")

            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        citations = data.get("citations", [])
        return (
            content, model,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            citations,
        )

    async def _call_claude(
        self, messages, temperature, max_tokens, timeout
    ) -> tuple:
        """Call Claude API via anthropic SDK."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")

        model = settings.ANTHROPIC_MODEL

        # Convert OpenAI-style messages to Anthropic format
        system_text = ""
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                claude_messages.append({"role": msg["role"], "content": msg["content"]})

        # Ensure messages alternate user/assistant
        if not claude_messages:
            claude_messages = [{"role": "user", "content": "Analyze."}]

        client = anthropic.AsyncAnthropic(api_key=api_key)
        try:
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": claude_messages,
            }
            if system_text:
                kwargs["system"] = system_text

            effective_timeout = timeout or 60.0
            response = await asyncio.wait_for(
                client.messages.create(**kwargs),
                timeout=effective_timeout,
            )

            content = response.content[0].text if response.content else ""
            return (
                content, model,
                response.usage.input_tokens,
                response.usage.output_tokens,
                [],
            )
        finally:
            await client.close()

    # ── Rate limit header parsing ─────────────────────────────────────────────

    def _parse_rate_limit_headers(self, resp, provider: str) -> None:
        """Extract rate limit info from HTTP response headers.

        Anthropic headers: anthropic-ratelimit-requests-remaining, etc.
        Perplexity headers: x-ratelimit-remaining, x-ratelimit-limit, x-ratelimit-reset
        Generic: retry-after, x-ratelimit-remaining
        """
        h = resp.headers
        remaining = None
        limit = None
        reset_at = None

        # Anthropic-specific
        if provider == "anthropic":
            remaining = _safe_int(h.get("anthropic-ratelimit-requests-remaining"))
            limit = _safe_int(h.get("anthropic-ratelimit-requests-limit"))
            reset_str = h.get("anthropic-ratelimit-requests-reset")
            if reset_str:
                try:
                    from datetime import datetime as dt
                    reset_at = dt.fromisoformat(reset_str.replace("Z", "+00:00")).timestamp()
                except Exception:
                    pass
            # Also check token limits
            tok_remaining = _safe_int(h.get("anthropic-ratelimit-tokens-remaining"))
            tok_limit = _safe_int(h.get("anthropic-ratelimit-tokens-limit"))
            if tok_remaining is not None and tok_limit is not None and tok_limit > 0:
                tok_pct = tok_remaining / tok_limit
                if tok_pct < 0.2:
                    self.health_monitor.record_quota_warning(provider, tok_remaining, tok_limit)

        # Perplexity / generic
        else:
            remaining = _safe_int(h.get("x-ratelimit-remaining"))
            limit = _safe_int(h.get("x-ratelimit-limit"))
            reset_str = h.get("x-ratelimit-reset")
            if reset_str:
                reset_at = _safe_float(reset_str)

        if remaining is not None or limit is not None:
            self.health_monitor.update_rate_limit_headers(
                provider, remaining=remaining, limit=limit, reset_at=reset_at,
            )

    @staticmethod
    def _extract_status(err_str: str) -> int:
        """Extract HTTP status code from error string."""
        import re
        m = re.search(r'(?:status[_ ]?code|http)\s*[:=]?\s*(\d{3})', err_str)
        if m:
            return int(m.group(1))
        # Anthropic SDK puts status in the exception
        for code in (429, 401, 403, 529, 503, 500, 502):
            if str(code) in err_str:
                return code
        return 0

    @staticmethod
    def _extract_retry_after(err_str: str) -> Optional[float]:
        """Extract retry-after seconds from error string."""
        import re
        m = re.search(r'retry[- _]?after\D*(\d+\.?\d*)', err_str)
        if m:
            return float(m.group(1))
        return None

    # ── Cost estimation ───────────────────────────────────────────────────────

    def _estimate_cost(self, tier: Tier, input_tokens: int, output_tokens: int) -> float:
        costs = COST_PER_1K.get(tier, {"input": 0, "output": 0})
        return (input_tokens / 1000 * costs["input"]) + (output_tokens / 1000 * costs["output"])

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        status = {
            "enabled": settings.LLM_ROUTER_ENABLED,
            "tiers": {
                "brainstem": {
                    "model": settings.OLLAMA_MODEL,
                    "base_url": settings.OLLAMA_BASE_URL,
                    "circuit_open": self._circuits[Tier.BRAINSTEM].is_open(),
                },
                "cortex": {
                    "model": settings.PERPLEXITY_MODEL,
                    "configured": bool(settings.PERPLEXITY_API_KEY),
                    "circuit_open": self._circuits[Tier.CORTEX].is_open(),
                },
                "deep_cortex": {
                    "model": settings.ANTHROPIC_MODEL,
                    "configured": bool(settings.ANTHROPIC_API_KEY),
                    "circuit_open": self._circuits[Tier.DEEP_CORTEX].is_open(),
                },
            },
            "stats": self._stats.copy(),
        }

        # Include dispatcher status if available
        try:
            from app.services.llm_dispatcher import get_llm_dispatcher
            status["dispatcher"] = get_llm_dispatcher().get_status()
        except Exception:
            pass

        return status


# ── Singleton ─────────────────────────────────────────────────────────────────

_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """Get or create the singleton LLMRouter."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
