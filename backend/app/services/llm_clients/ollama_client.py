"""Async Ollama client — supports dual-PC setup (PC-1 small, PC-2 large).

PC-1: mistral-7b pinned (<200ms inference, ~4GB VRAM)
PC-2: llama3-70b-q4 (~40GB VRAM, complex tasks)
Both run with OLLAMA_CUDA_GRAPHS=1 OLLAMA_FLASH_ATTENTION=1.
Gigabit LAN means <1ms network overhead between PCs.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


@dataclass
class OllamaEndpoint:
    """A single Ollama server endpoint."""
    name: str
    base_url: str
    model: str
    healthy: bool = True
    last_check: float = 0.0
    avg_latency_ms: float = 0.0
    _latencies: List[float] = field(default_factory=list)

    def record_latency(self, ms: float):
        self._latencies.append(ms)
        if len(self._latencies) > 100:
            self._latencies = self._latencies[-100:]
        self.avg_latency_ms = sum(self._latencies) / len(self._latencies)


class OllamaClient:
    """Async Ollama client with dual-endpoint support and health checks.

    Supports two endpoints:
        - pc1 (small): http://pc1:11434 — fast inference with small models
        - pc2 (large): http://pc2:11434 — complex tasks with large models
    """

    HEALTH_CHECK_INTERVAL = 60.0  # seconds between health checks

    def __init__(
        self,
        pc1_url: str = "http://localhost:11434",
        pc1_model: str = "mistral:7b",
        pc2_url: str = "http://localhost:11434",
        pc2_model: str = "llama3:70b-q4_K_M",
    ):
        self.endpoints = {
            "small": OllamaEndpoint(name="pc1_small", base_url=pc1_url.rstrip("/"), model=pc1_model),
            "large": OllamaEndpoint(name="pc2_large", base_url=pc2_url.rstrip("/"), model=pc2_model),
        }

    async def health_check(self, endpoint_key: str = None) -> Dict[str, bool]:
        """Check health of one or all endpoints."""
        keys = [endpoint_key] if endpoint_key else list(self.endpoints.keys())
        results = {}
        for key in keys:
            ep = self.endpoints.get(key)
            if not ep:
                continue
            now = time.time()
            if now - ep.last_check < self.HEALTH_CHECK_INTERVAL and ep.healthy:
                results[key] = True
                continue
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{ep.base_url}/api/tags")
                    ep.healthy = resp.status_code == 200
                    ep.last_check = now
            except Exception:
                ep.healthy = False
                ep.last_check = now
            results[key] = ep.healthy
        return results

    async def generate(
        self,
        messages: List[Dict[str, str]],
        size: str = "small",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        json_mode: bool = False,
        timeout: float = 30.0,
    ) -> Tuple[str, str, int, int]:
        """Generate a response from an Ollama endpoint.

        Args:
            messages: OpenAI-format chat messages
            size: "small" (PC-1) or "large" (PC-2)
            temperature: Sampling temperature
            max_tokens: Max output tokens
            json_mode: Request JSON output format
            timeout: Request timeout in seconds

        Returns:
            Tuple of (content, model, input_tokens, output_tokens)
        """
        ep = self.endpoints.get(size)
        if not ep:
            raise ValueError(f"Unknown endpoint size: {size}")

        url = f"{ep.base_url}/v1/chat/completions"
        payload: Dict[str, Any] = {
            "model": ep.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        latency_ms = (time.monotonic() - t0) * 1000
        ep.record_latency(latency_ms)

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return (
            content,
            ep.model,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            key: {
                "name": ep.name,
                "base_url": ep.base_url,
                "model": ep.model,
                "healthy": ep.healthy,
                "avg_latency_ms": round(ep.avg_latency_ms, 1),
            }
            for key, ep in self.endpoints.items()
        }


# Singleton
_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    global _client
    if _client is None:
        from app.core.config import settings
        _client = OllamaClient(
            pc1_url=settings.OLLAMA_BASE_URL,
            pc1_model=getattr(settings, "OLLAMA_SMALL_MODEL", "mistral:7b"),
            pc2_url=getattr(settings, "OLLAMA_PC2_URL", settings.OLLAMA_BASE_URL),
            pc2_model=getattr(settings, "OLLAMA_LARGE_MODEL", "llama3:70b-q4_K_M"),
        )
    return _client
