"""Ollama HTTP client for LLM inference on PC2.

Calls Ollama's /api/generate endpoint and parses structured responses.
Falls back gracefully when Ollama is unavailable.
"""
import json
import logging
import os
import re
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))

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
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
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
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
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
