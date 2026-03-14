"""Ollama HTTP client for LLM inference on PC2.

Calls Ollama's /api/generate endpoint and parses structured responses.
Falls back gracefully when Ollama is unavailable.

Dual-model strategy (via gpu_config):
  - Primary (gemma3:12b): hypothesis, trade_thesis, deep reasoning
  - Secondary (qwen3:8b): critic, fast tasks, postmortems
  - Falls back to env OLLAMA_MODEL if gpu_config unavailable
"""
import json
import logging
import os
import re
import sys
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))
VRAM_MIN_FREE_GB = float(os.getenv("VRAM_MIN_FREE_GB", "0.7"))


def check_vram_before_inference() -> bool:
    """Returns False if VRAM is critically low — prevents OOM crash.

    Checks free VRAM via PyTorch. If less than VRAM_MIN_FREE_GB (default 0.7GB)
    is available, refuses inference to protect Ollama from crashing.
    CPU-only paths always return True.
    """
    try:
        import torch
        if not torch.cuda.is_available():
            return True  # CPU path, no VRAM concern
        free_bytes, _total = torch.cuda.mem_get_info(0)
        free_gb = free_bytes / 1e9
        if free_gb < VRAM_MIN_FREE_GB:
            logger.error(
                "[vram_guard] Only %.2fGB VRAM free (min=%.1fGB) — refusing inference to prevent OOM",
                free_gb, VRAM_MIN_FREE_GB,
            )
            return False
        return True
    except ImportError:
        return True  # PyTorch not installed, can't check
    except Exception as e:
        logger.debug("[vram_guard] VRAM check failed (%s), allowing inference", e)
        return True

# Resolve Ollama URL: prefer OLLAMA_BASE_URL (explicit full URL) over OLLAMA_HOST
# because Ollama's own OLLAMA_HOST env var is often "0.0.0.0" (bind address, not connect address)
_base_url = os.getenv("OLLAMA_BASE_URL", "")
if _base_url:
    OLLAMA_URL = _base_url.rstrip("/")
else:
    _host = os.getenv("OLLAMA_HOST", "localhost")
    # Guard against Ollama's bind-address "0.0.0.0" leaking into client URL
    if _host in ("0.0.0.0", ""):
        _host = "localhost"
    _port = int(os.getenv("OLLAMA_PORT", "11434"))
    OLLAMA_URL = f"http://{_host}:{_port}"

# --- Dual-model routing via gpu_config ---
_gpu_config = None

def _get_gpu_config():
    """Lazy-load gpu_config to avoid circular imports."""
    global _gpu_config
    if _gpu_config is not None:
        return _gpu_config
    try:
        # Add backend path so we can import app.core.gpu_config
        backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
        if backend_path not in sys.path:
            sys.path.insert(0, os.path.abspath(backend_path))
        from app.core.gpu_config import get_gpu_config
        _gpu_config = get_gpu_config()
        logger.info("Loaded gpu_config: primary=%s, secondary=%s",
                     _gpu_config.primary_model.name, _gpu_config.secondary_model.name)
        return _gpu_config
    except Exception as e:
        logger.debug("gpu_config not available (%s), using env OLLAMA_MODEL", e)
        return None


def _model_for_task(task: str) -> str:
    """Route a task to the appropriate Ollama model.

    Uses gpu_config if available, otherwise falls back to OLLAMA_MODEL env var.
    """
    cfg = _get_gpu_config()
    if cfg:
        return cfg.model_for_task(task)
    return os.getenv("BRAIN_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "mistral:7b"))

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

    model = _model_for_task("hypothesis")
    logger.debug("infer_candidate_context using model=%s for %s", model, symbol)

    # VRAM OOM guard: refuse inference if VRAM critically low
    if not check_vram_before_inference():
        return {
            **_fallback_infer(),
            "risk_flags": ["vram_oom_guard"],
            "_model_used": model,
        }

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
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
                    "_model_used": model,
                }

            logger.warning("Ollama response not parseable as JSON, using raw text")
            return {
                "summary": response_text[:200],
                "confidence": 0.3,
                "risk_flags": ["unparseable_response"],
                "reasoning_bullets": [response_text[:100]],
                "_model_used": model,
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

    model = _model_for_task("critic")
    logger.debug("critic_postmortem using model=%s for trade %s", model, trade_id)

    # VRAM OOM guard
    if not check_vram_before_inference():
        return {**_fallback_critic(), "_model_used": model}

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
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
                    "_model_used": model,
                }

            return {
                "analysis": response_text[:500],
                "lessons": [],
                "performance_score": 0.0,
                "_model_used": model,
            }
    except Exception as e:
        logger.warning("Ollama critic error: %s", e)
        return _fallback_critic()


async def generate(prompt: str, task: str = "quick_hypothesis") -> Dict[str, Any]:
    """Generic Ollama generate with task-based model routing.

    Args:
        prompt: The prompt to send to Ollama.
        task: Task name for model routing (see gpu_config.py model_for_task).
              Examples: hypothesis, critic, trade_thesis, risk_check, feature_summary
    """
    model = _model_for_task(task)
    logger.debug("generate(task=%s) using model=%s", task, model)

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "")
            parsed = _parse_json_response(response_text)
            return {
                "response": parsed if parsed else response_text,
                "model": model,
                "task": task,
            }
    except Exception as e:
        logger.warning("Ollama generate error (task=%s): %s", task, e)
        return {"response": None, "model": model, "task": task, "error": str(e)}
