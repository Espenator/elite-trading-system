#!/usr/bin/env python3
"""
LLM Client for OpenClaw v1.1
Hybrid local-first (Ollama) + Perplexity API fallback.

Routing logic:
    - LOCAL tasks: scoring, trade rationale, pattern analysis, summarization
    - PERPLEXITY tasks: live web search, SEC filings, news sentiment, earnings
    - AUTO: tries local first, falls back to Perplexity on failure

Requires:
    - Ollama running locally: https://ollama.com  then: ollama pull qwen3:14b
    - Perplexity API key for web-connected queries

See config.py for all LLM settings.

Fixes from Issue #5:
    - Token bucket rate limiter for API calls
    - TTL response cache keyed on prompt hash
    - Ollama health check cached for 5 minutes (was 30s)
    - Configurable timeouts from config.py
    - analyze_candidates warns when truncating to max_candidates
    - parse_json_response() for structured output extraction
"""
import hashlib
import json
import logging
import re
import time
import threading
from typing import Optional, Dict, Any, List

import requests

logger = logging.getLogger(__name__)


# =========== RATE LIMITER (Issue #5 fix) ===========
class TokenBucketRateLimiter:
    """Simple token bucket rate limiter for API calls."""

    def __init__(self, tokens_per_second: float = 1.0, max_tokens: int = 5):
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self._tokens = float(max_tokens)
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 30.0) -> bool:
        """Wait until a token is available. Returns False on timeout."""
        deadline = time.time() + timeout
        while True:
            with self._lock:
                now = time.time()
                elapsed = now - self._last_refill
                self._tokens = min(
                    self.max_tokens,
                    self._tokens + elapsed * self.tokens_per_second
                )
                self._last_refill = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True
            if time.time() >= deadline:
                return False
            time.sleep(0.1)


# =========== RESPONSE CACHE (Issue #5 fix) ===========
class TTLCache:
    """Simple TTL cache for LLM responses keyed on prompt hash."""

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 200):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._cache: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _hash_key(prompt: str, task: str, system_prompt: str = None) -> str:
        raw = f"{task}:{system_prompt or ''}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, prompt: str, task: str, system_prompt: str = None) -> Optional[Dict]:
        key = self._hash_key(prompt, task, system_prompt)
        with self._lock:
            entry = self._cache.get(key)
            if entry and (time.time() - entry['ts']) < self.ttl:
                logger.debug('[LLM-CACHE] Hit for key %s', key)
                return entry['data']
            if entry:
                del self._cache[key]
        return None

    def put(self, prompt: str, task: str, data: Dict, system_prompt: str = None):
        key = self._hash_key(prompt, task, system_prompt)
        with self._lock:
            if len(self._cache) >= self.max_entries:
                oldest_key = min(self._cache, key=lambda k: self._cache[k]['ts'])
                del self._cache[oldest_key]
            self._cache[key] = {'data': data, 'ts': time.time()}

    def clear(self):
        with self._lock:
            self._cache.clear()


# =========== JSON RESPONSE PARSER (Issue #5 fix) ===========
def parse_json_response(text: str) -> Optional[Dict]:
    """Attempt to extract JSON from LLM response text.

    Handles common patterns:
    - Pure JSON response
    - JSON in markdown code blocks
    - JSON embedded in natural language

    Returns parsed dict/list or None if no valid JSON found.
    """
    if not text:
        return None

    # Try direct parse
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, TypeError):
        pass

    # Try extracting from markdown code blocks
    patterns = [
        r'```json\s*\n(.*?)\n\s*```',
        r'```\s*\n(.*?)\n\s*```',
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
        r'\[.*\]',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1) if match.lastindex else match.group())
            except (json.JSONDecodeError, TypeError, IndexError):
                continue

    return None


# =========== TASK ROUTING ===========
# Which tasks should use which backend
LOCAL_TASKS = {
    "score_analysis",      # Analyze composite score components
    "trade_rationale",     # Generate trade entry/exit reasoning
    "pattern_analysis",    # Chart pattern interpretation
    "summarize_scan",      # Summarize daily scan results
    "regime_analysis",     # Analyze market regime data
    "risk_assessment",     # Position risk evaluation
    "watchlist_filter",    # Filter/rank watchlist candidates
    "scout_screening",  # Sovereign GPU fast pre-screen
}

PERPLEXITY_TASKS = {
    "web_search",          # Live web search for news/events
    "sec_filings",         # SEC filing lookup and analysis
    "earnings_lookup",     # Earnings date/estimate lookup
    "news_sentiment",      # Current news sentiment analysis
    "sector_research",     # Sector/industry research
    "macro_analysis",      # Live macro economic data analysis
}

# Module-level rate limiters and cache
_local_limiter = TokenBucketRateLimiter(tokens_per_second=2.0, max_tokens=5)
_pplx_limiter = TokenBucketRateLimiter(tokens_per_second=1.0, max_tokens=3)
_response_cache = TTLCache(ttl_seconds=300, max_entries=200)

class OllamaClient:
    """Local LLM via Ollama OpenAI-compatible API."""

    def __init__(self, base_url: str = None, model: str = None, temperature: float = None):
        from config import OLLAMA_BASE_URL, LOCAL_LLM_MODEL, LLM_TEMPERATURE
        # Issue #5 fix: configurable timeout from config
        try:
            from config import OLLAMA_TIMEOUT
            self.timeout = OLLAMA_TIMEOUT
        except ImportError:
            self.timeout = 120

        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip('/')
        self.model = model or LOCAL_LLM_MODEL
        self.temperature = temperature if temperature is not None else LLM_TEMPERATURE
        self._healthy = None
        self._last_check = 0

    def is_available(self) -> bool:
        """Check if Ollama is running and model is loaded.
        Issue #5 fix: cache health check for 5 minutes (was 30s).
        """
        now = time.time()
        # Issue #5 fix: 300s cache instead of 30s
        if self._healthy is not None and (now - self._last_check) < 300:
            return self._healthy
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                models = [m.get('name', '') for m in resp.json().get('models', [])]
                base_model = self.model.split(':')[0]
                self._healthy = any(base_model in m for m in models)
                if not self._healthy:
                    logger.warning(f"[LLM] Ollama running but model '{self.model}' not found. Available: {models}")
            else:
                self._healthy = False
        except Exception:
            self._healthy = False
        self._last_check = now
        return self._healthy

    def chat(self, messages: List[Dict], temperature: float = None,
             max_tokens: int = 2048, json_mode: bool = False) -> Optional[str]:
        """Send chat completion to local Ollama."""
        # Issue #5 fix: rate limiting
        if not _local_limiter.acquire(timeout=10):
            logger.warning('[LLM-LOCAL] Rate limit exceeded')
            return None
        try:
            url = f"{self.base_url}/v1/chat/completions"
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {})
            logger.info(
                f"[LLM-LOCAL] {self.model} | "
                f"in={tokens_used.get('prompt_tokens', '?')} "
                f"out={tokens_used.get('completion_tokens', '?')}"
            )
            return content
        except requests.exceptions.ConnectionError:
            logger.warning("[LLM-LOCAL] Ollama not reachable")
            self._healthy = False
            return None
        except Exception as e:
            logger.error(f"[LLM-LOCAL] Error: {e}")
            return None


class PerplexityClient:
    """Perplexity API client for web-connected LLM queries."""

    def __init__(self):
        from config import (
            PERPLEXITY_API_KEY, PERPLEXITY_BASE_URL,
            PERPLEXITY_SEARCH_MODEL, PERPLEXITY_REASON_MODEL,
            PERPLEXITY_DEEP_MODEL
        )
        # Issue #5 fix: configurable timeout from config
        try:
            from config import PERPLEXITY_TIMEOUT
            self.timeout = PERPLEXITY_TIMEOUT
        except ImportError:
            self.timeout = 60

        self.api_key = PERPLEXITY_API_KEY
        self.base_url = PERPLEXITY_BASE_URL
        self.search_model = PERPLEXITY_SEARCH_MODEL
        self.reason_model = PERPLEXITY_REASON_MODEL
        self.deep_model = PERPLEXITY_DEEP_MODEL

    def is_available(self) -> bool:
        """Check if Perplexity API key is configured."""
        return bool(self.api_key)

    def chat(self, messages: List[Dict], model: str = None,
             temperature: float = 0.3, max_tokens: int = 2048) -> Optional[str]:
        """Send chat completion to Perplexity API."""
        if not self.api_key:
            logger.warning("[LLM-PPLX] No API key configured")
            return None
        # Issue #5 fix: rate limiting for Perplexity
        if not _pplx_limiter.acquire(timeout=15):
            logger.warning('[LLM-PPLX] Rate limit exceeded')
            return None
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model or self.search_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {})
            logger.info(
                f"[LLM-PPLX] {payload['model']} | "
                f"in={tokens_used.get('prompt_tokens', '?')} "
                f"out={tokens_used.get('completion_tokens', '?')}"
            )
            return content
        except Exception as e:
            logger.error(f"[LLM-PPLX] Error: {e}")
            return None

    def search(self, query: str, system_prompt: str = None) -> Optional[str]:
        """Quick web search via Perplexity sonar-pro."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": query})
        return self.chat(messages, model=self.search_model)

    def reason(self, query: str, system_prompt: str = None) -> Optional[str]:
        """Deep reasoning via Perplexity sonar-reasoning-pro."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": query})
        return self.chat(messages, model=self.reason_model)


# =========== SOVEREIGN GPU SCOUT CLIENT ===========
class ScoutClient:
    """Local GPU inference for fast candidate pre-screening."""

    def __init__(self):
        from config import (
            SCOUT_MODEL_NAME, SCOUT_MODEL_PATH, SCOUT_GPU_DEVICE,
            SCOUT_MAX_TOKENS, SCOUT_TEMPERATURE, SCOUT_BATCH_SIZE,
            SCOUT_ENABLED
        )
        self.model_name = SCOUT_MODEL_NAME
        self.model_path = SCOUT_MODEL_PATH
        self.device = SCOUT_GPU_DEVICE
        self.max_tokens = SCOUT_MAX_TOKENS
        self.temperature = SCOUT_TEMPERATURE
        self.batch_size = SCOUT_BATCH_SIZE
        self.enabled = SCOUT_ENABLED
        self._healthy = None
        self._last_check = 0
        if self.enabled:
            logger.info(f"[SCOUT] Init: {self.model_name} on {self.device}")

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        now = time.time()
        if self._healthy is not None and (now - self._last_check) < 300:
            return self._healthy
        try:
            import torch
            self._healthy = torch.cuda.is_available()
        except ImportError:
            self._healthy = False
        self._last_check = now
        return self._healthy

    def screen_candidates(self, candidates: list, regime: str) -> Optional[Dict]:
        if not self.is_available() or not candidates:
            return None
        try:
            prompt = f"Regime: {regime}. Screen {len(candidates)} candidates. PASS/FAIL + confidence 0-100. JSON."
            for c in candidates[:self.batch_size]:
                prompt += f"\n  {c.get('symbol','?')}: score={c.get('composite_score',0)}"
            from config import OLLAMA_BASE_URL, LOCAL_LLM_MODEL
            url = f"{OLLAMA_BASE_URL.rstrip('/')}/v1/chat/completions"
            payload = {"model": LOCAL_LLM_MODEL, "messages": [{"role": "user", "content": prompt}],
                       "temperature": self.temperature, "max_tokens": self.max_tokens, "stream": False}
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = parse_json_response(content)
            logger.info(f"[SCOUT] Screened {len(candidates)} candidates")
            return {"raw": content, "parsed": parsed, "count": len(candidates)}
        except Exception as e:
            logger.error(f"[SCOUT] Screening error: {e}")
            return None

    def status(self) -> Dict[str, Any]:
        return {"enabled": self.enabled, "model": self.model_name,
                "device": self.device, "available": self.is_available()}


class HybridLLM:
    """
    Unified LLM interface: routes to local Ollama or Perplexity based on task type.
    Local-first by default. Perplexity for web-connected tasks.
    """

    def __init__(self):
        from config import LLM_ENABLED, PERPLEXITY_ENABLED, LLM_PREFER_LOCAL
        self.local = OllamaClient() if LLM_ENABLED else None
        self.pplx = PerplexityClient() if PERPLEXITY_ENABLED else None
        self.prefer_local = LLM_PREFER_LOCAL
        self.scout = ScoutClient()
        self._stats = {"local_calls": 0, "pplx_calls": 0, "fallbacks": 0,
                       "failures": 0, "cache_hits": 0}
        logger.info(
            f"[LLM] HybridLLM initialized | "
            f"local={'ON' if self.local else 'OFF'} "
            f"pplx={'ON' if self.pplx else 'OFF'} "
            f"prefer={'local' if self.prefer_local else 'cloud'}"
        )

    def _resolve_backend(self, task: str = "auto") -> str:
        """Determine which backend to use for a given task."""
        if task in PERPLEXITY_TASKS:
            return "perplexity"
        if task in LOCAL_TASKS:
            return "local"
        # Auto: prefer local if available
        if self.prefer_local and self.local and self.local.is_available():
            return "local"
        if self.pplx and self.pplx.is_available():
            return "perplexity"
        if self.local and self.local.is_available():
            return "local"
        return "none"

    def query(self, prompt: str, task: str = "auto",
              system_prompt: str = None, temperature: float = None,
              max_tokens: int = 2048, json_mode: bool = False) -> Dict[str, Any]:
        """
        Main entry point: send a prompt to the appropriate LLM backend.

        Issue #5 fix: checks TTL cache before making API call.

        Args:
            prompt: The user/task prompt
            task: Task type for routing (see LOCAL_TASKS / PERPLEXITY_TASKS)
            system_prompt: Optional system message
            temperature: Override temperature
            max_tokens: Max response tokens
            json_mode: Request JSON output (local only)

        Returns:
            {"content": str, "backend": str, "success": bool, "error": str,
             "cached": bool, "parsed_json": dict|None}
        """
        # Issue #5 fix: check cache first
        cached = _response_cache.get(prompt, task, system_prompt)
        if cached is not None:
            self._stats["cache_hits"] += 1
            cached["cached"] = True
            return cached

        backend = self._resolve_backend(task)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        result = {"content": None, "backend": backend, "success": False,
                  "error": None, "cached": False, "parsed_json": None}

        # Try primary backend
        if backend == "local" and self.local:
            content = self.local.chat(messages, temperature=temperature,
                                     max_tokens=max_tokens, json_mode=json_mode)
            if content:
                self._stats["local_calls"] += 1
                result.update({"content": content, "success": True})
                # Issue #5 fix: attempt JSON parse
                if json_mode:
                    result["parsed_json"] = parse_json_response(content)
                _response_cache.put(prompt, task, result, system_prompt)
                return result
            # Fallback to Perplexity
            if self.pplx and self.pplx.is_available():
                logger.info(f"[LLM] Falling back to Perplexity for task '{task}'")
                content = self.pplx.chat(messages, temperature=temperature,
                                         max_tokens=max_tokens)
                if content:
                    self._stats["fallbacks"] += 1
                    self._stats["pplx_calls"] += 1
                    result.update({"content": content, "backend": "perplexity_fallback", "success": True})
                    if json_mode:
                        result["parsed_json"] = parse_json_response(content)
                    _response_cache.put(prompt, task, result, system_prompt)
                    return result

        elif backend == "perplexity" and self.pplx:
            content = self.pplx.chat(messages, temperature=temperature,
                                     max_tokens=max_tokens)
            if content:
                self._stats["pplx_calls"] += 1
                result.update({"content": content, "success": True})
                if json_mode:
                    result["parsed_json"] = parse_json_response(content)
                _response_cache.put(prompt, task, result, system_prompt)
                return result
            # Fallback to local (won't have web data but better than nothing)
            if self.local and self.local.is_available():
                logger.info(f"[LLM] Falling back to local for task '{task}'")
                content = self.local.chat(messages, temperature=temperature,
                                          max_tokens=max_tokens, json_mode=json_mode)
                if content:
                    self._stats["fallbacks"] += 1
                    self._stats["local_calls"] += 1
                    result.update({"content": content, "backend": "local_fallback", "success": True})
                    if json_mode:
                        result["parsed_json"] = parse_json_response(content)
                    _response_cache.put(prompt, task, result, system_prompt)
                    return result

        self._stats["failures"] += 1
        result["error"] = f"No LLM backend available for task '{task}'"
        logger.warning(f"[LLM] {result['error']}")
        return result

    def status(self) -> Dict[str, Any]:
        """Get current LLM status and stats."""
        return {
            "local_available": self.local.is_available() if self.local else False,
            "local_model": self.local.model if self.local else None,
            "perplexity_available": self.pplx.is_available() if self.pplx else False,
            "prefer_local": self.prefer_local,
            "stats": self._stats.copy(),
        }

    # =========== CONVENIENCE METHODS FOR OPENCLAW ===========

    def analyze_candidates(self, candidates: List[Dict], regime: str,
                           max_candidates: int = 10) -> Optional[str]:
        """LLM analysis of top scan candidates.

        Issue #5 fix: warns when truncating candidates and accepts
        configurable max_candidates parameter.
        """
        if not candidates:
            return None

        if len(candidates) > max_candidates:
            logger.warning(
                '[LLM] analyze_candidates: truncating %d candidates to %d. '
                'Set max_candidates to increase.',
                len(candidates), max_candidates
            )
        top = candidates[:max_candidates]

        prompt = (
            f"Market regime: {regime}\n"
            f"Top {len(top)} of {len(candidates)} candidates from today's scan:\n"
        )
        for c in top:
            prompt += (
                f"  {c.get('symbol','?')}: score={c.get('composite_score',0)}, "
                f"tier={c.get('tier','?')}, price=${c.get('price',0):.2f}\n"
            )
        prompt += (
            "\nAnalyze these candidates. For each, give a 1-sentence "
            "trade thesis and rate conviction 1-5. Consider the regime."
        )
        system = (
            "You are an expert swing trader assistant. Be concise and actionable. "
            "Focus on risk/reward and regime-appropriate setups."
        )
        result = self.query(prompt, task="score_analysis", system_prompt=system)
        return result.get("content")

    def get_trade_rationale(self, symbol: str, score_data: Dict,
                            regime: str) -> Optional[str]:
        """Generate trade rationale for a specific symbol."""
        prompt = (
            f"Symbol: {symbol}\n"
            f"Regime: {regime}\n"
            f"Composite Score: {score_data.get('composite_score', 0)}\n"
            f"Tier: {score_data.get('tier', 'UNKNOWN')}\n"
            f"Trend Score: {score_data.get('trend_score', 0)}/25\n"
            f"Pullback Score: {score_data.get('pullback_score', 0)}/25\n"
            f"Momentum Score: {score_data.get('momentum_score', 0)}/20\n"
            f"Pattern Score: {score_data.get('pattern_score', 0)}/10\n"
            f"Price: ${score_data.get('price', 0)}\n"
            f"Entry: ${score_data.get('suggested_entry', 0)}\n"
            f"Stop: ${score_data.get('suggested_stop', 0)}\n"
            "\nProvide: 1) Trade thesis 2) Key risk 3) Conviction (1-5)"
        )
        system = "You are an expert swing trader. Be concise. Max 3 sentences per point."
        result = self.query(prompt, task="trade_rationale", system_prompt=system)
        return result.get("content")

    def summarize_scan(self, scan_data: Dict) -> Optional[str]:
        """Generate narrative summary of daily scan results."""
        regime = scan_data.get("regime", {}).get("state", "UNKNOWN")
        candidates = scan_data.get("top_candidates", [])
        whale_alerts = scan_data.get("whale_flow_alerts", [])
        macro = scan_data.get("macro_context", {})
        prompt = (
            f"Daily Scan Summary:\n"
            f"Regime: {regime}\n"
            f"Candidates found: {len(candidates)}\n"
            f"Whale alerts: {len(whale_alerts)}\n"
            f"Fear/Greed: {macro.get('fear_greed_value', '?')} ({macro.get('fear_greed_label', '?')})\n"
            f"Top 5 symbols: {', '.join(c.get('symbol','') for c in candidates[:5])}\n"
            "\nWrite a 3-4 sentence market briefing for today's scan."
        )
        system = "You are a market analyst writing a daily briefing. Be factual and concise."
        result = self.query(prompt, task="summarize_scan", system_prompt=system)
        return result.get("content")

    def get_news_sentiment(self, symbols: List[str]) -> Optional[str]:
        """Get live news sentiment for symbols via Perplexity."""
        if not symbols:
            return None
        sym_str = ', '.join(symbols[:10])
        prompt = (
            f"What is the current news sentiment for these stocks: {sym_str}? "
            f"For each, summarize the latest headline and rate sentiment "
            f"as bullish/bearish/neutral. Include any upcoming catalysts."
        )
        system = "You are a financial news analyst. Be concise and factual."
        result = self.query(prompt, task="news_sentiment", system_prompt=system)
        return result.get("content")

    def check_earnings(self, symbols: List[str]) -> Optional[str]:
        """Check upcoming earnings dates via Perplexity."""
        if not symbols:
            return None
        sym_str = ', '.join(symbols[:15])
        prompt = (
            f"When are the next earnings dates for: {sym_str}? "
            f"List each with date, expected EPS, and whether it's before or after market."
        )
        result = self.query(prompt, task="earnings_lookup")
        return result.get("content")

# =========== MODULE-LEVEL SINGLETON ===========
_llm_instance: Optional[HybridLLM] = None


def get_llm() -> HybridLLM:
    """Get or create the global HybridLLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = HybridLLM()
    return _llm_instance


def llm_query(prompt: str, task: str = "auto", **kwargs) -> Dict[str, Any]:
    """Convenience function: query the hybrid LLM."""
    return get_llm().query(prompt, task=task, **kwargs)


def llm_status() -> Dict[str, Any]:
    """Get LLM status without creating instance if not exists."""
    if _llm_instance is None:
        return {"initialized": False}
    return {"initialized": True, **_llm_instance.status()}


# =========== CALL_LLM SHIM (for world_intel/sensorium.py compatibility) ===========
def call_llm(prompt: str, max_tokens: int = 2000, temperature: float = 0.3) -> Optional[str]:
    """
    Simple call_llm() compatibility shim.
    Used by world_intel/sensorium.py LLMThemeExtractor.
    Routes through HybridLLM auto-mode (local Ollama first, Perplexity fallback).
    Returns the response string directly, or None on failure.
    """
    result = llm_query(prompt, task="auto", max_tokens=max_tokens, temperature=temperature)
    return result.get("content") if result.get("success") else None


# =========== STANDALONE TEST ===========
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    llm = get_llm()
    print(f"LLM Status: {json.dumps(llm.status(), indent=2)}")

    # Test local
    if llm.local and llm.local.is_available():
        print("\n--- Testing Local (Ollama) ---")
        result = llm.query(
            "What are the key factors to consider when swing trading in a volatile market?",
            task="trade_rationale"
        )
        print(f"Backend: {result['backend']}")
        print(f"Cached: {result.get('cached', False)}")
        print(f"Response: {result['content'][:200] if result['content'] else 'FAILED'}...")
    else:
        print("\nLocal LLM not available. Start Ollama: ollama serve")

    # Test Perplexity
    if llm.pplx and llm.pplx.is_available():
        print("\n--- Testing Perplexity ---")
        result = llm.query(
            "What are the top market movers today?",
            task="news_sentiment"
        )
        print(f"Backend: {result['backend']}")
        print(f"Cached: {result.get('cached', False)}")
        print(f"Response: {result['content'][:200] if result['content'] else 'FAILED'}...")
    else:
        print("\nPerplexity not available. Set PERPLEXITY_API_KEY in .env")

    # Test JSON parsing
    print("\n--- Testing JSON Parser ---")
    test_cases = [
        '{"score": 85, "conviction": 4}',
        'Here is the analysis:\n```json\n{"result": "bullish"}\n```',
        'No JSON here, just text.',
    ]
    for tc in test_cases:
        parsed = parse_json_response(tc)
        print(f"  Input: {tc[:50]}... -> Parsed: {parsed}")
