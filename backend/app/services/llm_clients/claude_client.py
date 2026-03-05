"""Async Claude API client — deep reasoning via Anthropic SDK."""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Async Claude API wrapper using the anthropic SDK."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> Tuple[str, str, int, int]:
        """Generate a response from Claude.

        Returns:
            Tuple of (content, model, input_tokens, output_tokens)
        """
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")

        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        # Convert OpenAI-style messages to Anthropic format
        system_text = ""
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                claude_messages.append({"role": msg["role"], "content": msg["content"]})

        if not claude_messages:
            claude_messages = [{"role": "user", "content": "Analyze."}]

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        try:
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": claude_messages,
            }
            if system_text:
                kwargs["system"] = system_text

            response = await asyncio.wait_for(
                client.messages.create(**kwargs),
                timeout=timeout,
            )

            content = response.content[0].text if response.content else ""
            return (
                content,
                self.model,
                response.usage.input_tokens,
                response.usage.output_tokens,
            )
        finally:
            await client.close()


# Singleton
_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    global _client
    if _client is None:
        from app.core.config import settings
        _client = ClaudeClient(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.ANTHROPIC_MODEL,
        )
    return _client
