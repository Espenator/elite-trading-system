"""Async Perplexity API client — web-grounded intelligence via Sonar Pro.

Returns citations and source_quality metadata alongside responses.
"""
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


class PerplexityClient:
    """Async Perplexity API wrapper with citation extraction."""

    def __init__(self, api_key: str, base_url: str = "https://api.perplexity.ai", model: str = "sonar-pro"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        timeout: float = 30.0,
    ) -> Tuple[str, str, int, int, List[str], float]:
        """Generate a response from Perplexity.

        Returns:
            Tuple of (content, model, input_tokens, output_tokens, citations, source_quality)
        """
        if not self.api_key:
            raise RuntimeError("PERPLEXITY_API_KEY not configured")

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        citations = data.get("citations", [])

        # Source quality heuristic: more citations from reputable sources = higher quality
        source_quality = min(1.0, len(citations) * 0.15) if citations else 0.0

        return (
            content,
            self.model,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            citations,
            source_quality,
        )


# Singleton
_client: Optional[PerplexityClient] = None


def get_perplexity_client() -> PerplexityClient:
    global _client
    if _client is None:
        from app.core.config import settings
        _client = PerplexityClient(
            api_key=settings.PERPLEXITY_API_KEY,
            base_url=settings.PERPLEXITY_BASE_URL,
            model=settings.PERPLEXITY_MODEL,
        )
    return _client
