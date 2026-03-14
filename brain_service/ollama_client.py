"""Ollama HTTP client for LLM inference on PC2.

Calls Ollama's /api/generate endpoint and parses structured responses.
Falls back gracefully when Ollama is unavailable.
"""
import json
import hashlib
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
OLLAMA_MODEL = os.getenv("BRAIN_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "mistral:7b"))
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
OLLAMA_NUM_GPU = 99
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")

# REQUIRED ENV VARS FOR RTX 4080 PERFORMANCE:
# OLLAMA_FLASH_ATTENTION=1    — Ada arch Flash Attention 2 (40% memory bandwidth reduction)
# OLLAMA_NUM_PARALLEL=4       — concurrent inference slots
# OLLAMA_MAX_LOADED_MODELS=1  — keep single large model hot
# Recommended model: qwen2.5:14b-instruct-q4_K_M (fits in 14GB VRAM)

OLLAMA_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

INFER_PROMPT = """You are a trading analysis AI. Analyze the following market context and provide a structured assessment.

Symbol: {symbol}
Timeframe: {timeframe}
Regime: {regime}
Context: {context}

Features:
{feature_json}

Respond in this exact JSON format:
{{
  "summary": "brief 1-2 sentence assessment",
  "confidence": 0.0 to 1.0 float,
  "risk_flags": ["list", "of", "risk", "flags"],
  "reasoning_bullets": ["bullet1", "bullet2", "bullet3"]
}}
"""

CRITIC_PROMPT = """You are a trading critic AI. Analyze this completed trade and extract lessons.

Trade ID: {trade_id}
Symbol: {symbol}
Entry Context: {entry_context}

Outcome:
{outcome_json}

Respond in this exact JSON format:
{{
  "analysis": "detailed analysis of the trade",
  "lessons": ["lesson1", "lesson2", "lesson3"],
  "performance_score": 0.0 to 1.0 float
}}
"""


def _ollama_options() -> Dict[str, Any]:
    """Shared Ollama options for consistent GPU usage."""
    return {
        "num_gpu": OLLAMA_NUM_GPU,
        "num_ctx": OLLAMA_NUM_CTX,
    }


def _warn_if_flash_attention_not_enabled() -> None:
    if os.getenv("OLLAMA_FLASH_ATTENTION") != "1":
        logger.warning(
            "OLLAMA_FLASH_ATTENTION is not set to 1; RTX 4080 inference may be slower."
        )


def _run_gpu_warmup() -> None:
    """Best-effort warmup to pre-load model into VRAM; never raises."""
    warmup_payload = {
        "model": OLLAMA_MODEL,
        "prompt": "warmup",
        "stream": False,
        "options": _ollama_options(),
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }
    try:
        with httpx.Client(timeout=min(10, OLLAMA_TIMEOUT)) as client:
            resp = client.post(f"{OLLAMA_URL}/api/generate", json=warmup_payload)
            if resp.status_code >= 400:
                logger.warning(
                    "Ollama GPU warmup returned status %d (continuing)",
                    resp.status_code,
                )
            else:
                logger.info("Ollama GPU warmup completed for model %s", OLLAMA_MODEL)
    except Exception as e:
        logger.warning("Ollama GPU warmup skipped: %s", e)


def _fallback_infer() -> Dict[str, Any]:
    """Return low-confidence fallback when Ollama is unavailable."""
    return {
        "summary": "LLM unavailable — using fallback assessment",
        "confidence": 0.1,
        "risk_flags": ["llm_unavailable"],
        "reasoning_bullets": ["Ollama service not reachable", "Defaulting to low confidence"],
    }


def _fallback_critic() -> Dict[str, Any]:
    """Return fallback critic response when Ollama is unavailable."""
    return {
        "analysis": "LLM unavailable — no critic analysis",
        "lessons": ["Ollama service not reachable"],
        "performance_score": 0.0,
    }


def _parse_json_response(text: str) -> Optional[Dict]:
    """Try to extract JSON from LLM response text."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


async def infer_candidate_context(
    symbol: str,
    timeframe: str,
    feature_json: str,
    regime: str = "unknown",
    context: str = "",
) -> Dict[str, Any]:
    """Call Ollama to get LLM inference on a trading candidate.

    Returns dict with: summary, confidence, risk_flags, reasoning_bullets
    On error: returns fallback low-confidence response.
    """
    prompt = INFER_PROMPT.format(
        symbol=symbol,
        timeframe=timeframe,
        regime=regime,
        context=context,
        feature_json=feature_json[:2000],
    )

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": _ollama_options(),
                    "keep_alive": OLLAMA_KEEP_ALIVE,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "")

            parsed = _parse_json_response(response_text)
            if parsed:
                return {
                    "summary": str(parsed.get("summary", "No summary")),
                    "confidence": max(0.0, min(1.0, float(parsed.get("confidence", 0.5)))),
                    "risk_flags": list(parsed.get("risk_flags", [])),
                    "reasoning_bullets": list(parsed.get("reasoning_bullets", [])),
                }

            logger.warning("Ollama response not parseable as JSON, using raw text")
            return {
                "summary": response_text[:200],
                "confidence": 0.3,
                "risk_flags": ["unparseable_response"],
                "reasoning_bullets": [response_text[:100]],
            }
    except httpx.ConnectError:
        logger.warning("Ollama not reachable at %s", OLLAMA_URL)
        return _fallback_infer()
    except httpx.TimeoutException:
        logger.warning("Ollama request timed out after %ds", OLLAMA_TIMEOUT)
        return {**_fallback_infer(), "risk_flags": ["llm_timeout"]}
    except Exception as e:
        logger.exception("Ollama inference error: %s", e)
        return _fallback_infer()


async def critic_postmortem(
    trade_id: str,
    symbol: str,
    entry_context: str,
    outcome_json: str,
) -> Dict[str, Any]:
    """Call Ollama to get post-trade critic analysis.

    Returns dict with: analysis, lessons, performance_score
    """
    prompt = CRITIC_PROMPT.format(
        trade_id=trade_id,
        symbol=symbol,
        entry_context=entry_context,
        outcome_json=outcome_json[:2000],
    )

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": _ollama_options(),
                    "keep_alive": OLLAMA_KEEP_ALIVE,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "")

            parsed = _parse_json_response(response_text)
            if parsed:
                return {
                    "analysis": str(parsed.get("analysis", "No analysis")),
                    "lessons": list(parsed.get("lessons", [])),
                    "performance_score": max(
                        0.0, min(1.0, float(parsed.get("performance_score", 0.0)))
                    ),
                }

            return {
                "analysis": response_text[:500],
                "lessons": [],
                "performance_score": 0.0,
            }
    except Exception as e:
        logger.warning("Ollama critic error: %s", e)
        return _fallback_critic()


async def BatchAnalyze(
    hypothesis_prompt: str,
    critique_prompt: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run hypothesis then critique with context hash metadata.

    The critique call uses a hash of hypothesis output as metadata context,
    which helps KV cache reuse and typically lowers critique latency.
    """
    hypothesis_result: Dict[str, Any] = {"response": "", "context_hash": ""}
    critique_result: Dict[str, Any] = {"response": "", "context_hash": ""}

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            hypothesis_resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": hypothesis_prompt,
                    "stream": False,
                    "options": _ollama_options(),
                    "keep_alive": OLLAMA_KEEP_ALIVE,
                },
            )
            hypothesis_resp.raise_for_status()
            hypothesis_text = hypothesis_resp.json().get("response", "")
            hypothesis_parsed = _parse_json_response(hypothesis_text)
            hypothesis_result = hypothesis_parsed if hypothesis_parsed else {"response": hypothesis_text}

            hypothesis_blob = json.dumps(hypothesis_result, sort_keys=True)
            context_hash = hashlib.sha256(hypothesis_blob.encode("utf-8")).hexdigest()[:16]
            hypothesis_result["context_hash"] = context_hash

            critique_with_meta = (
                f"[metadata]\ncontext_hash={context_hash}\n\n{critique_prompt}"
            )
            critique_resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": critique_with_meta}],
                    "stream": False,
                    "options": _ollama_options(),
                    "keep_alive": OLLAMA_KEEP_ALIVE,
                },
            )
            critique_resp.raise_for_status()
            critique_msg = critique_resp.json().get("message", {})
            critique_text = critique_msg.get("content", "")
            critique_parsed = _parse_json_response(critique_text)
            critique_result = critique_parsed if critique_parsed else {"response": critique_text}
            critique_result["context_hash"] = context_hash
    except Exception as e:
        logger.warning("Ollama BatchAnalyze error: %s", e)
        if not hypothesis_result.get("response"):
            hypothesis_result = _fallback_infer()
        if not critique_result.get("response"):
            critique_result = _fallback_critic()
        context_hash = hypothesis_result.get("context_hash", "")
        if context_hash:
            critique_result["context_hash"] = context_hash

    return hypothesis_result, critique_result


_warn_if_flash_attention_not_enabled()
_run_gpu_warmup()
