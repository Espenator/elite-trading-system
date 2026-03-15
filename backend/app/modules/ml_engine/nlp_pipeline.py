"""GPU Channel 9 — FinBERT NLP Pipeline for real-time news sentiment.

Routes news batches to PC2 GPU for FinBERT inference. Scores 100+ news items
per minute. Falls back to Ollama one-shot sentiment when FinBERT unavailable.

Publishes scored events to `perception.sentiment` MessageBus topic so all
council agents have real-time NLP sentiment signals.

Usage:
    from app.modules.ml_engine.nlp_pipeline import get_nlp_pipeline
    pipeline = get_nlp_pipeline()
    scores = await pipeline.score_batch([
        {"symbol": "AAPL", "text": "Apple beats earnings expectations"},
        {"symbol": "TSLA", "text": "Tesla faces regulatory probe"},
    ])
"""
import asyncio
import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# GPU Channel 9: FinBERT on CUDA
_FINBERT_MODEL = None
_FINBERT_TOKENIZER = None
_FINBERT_DEVICE = None
_FINBERT_AVAILABLE = False


def _load_finbert():
    """Lazy-load FinBERT model onto GPU."""
    global _FINBERT_MODEL, _FINBERT_TOKENIZER, _FINBERT_DEVICE, _FINBERT_AVAILABLE
    if _FINBERT_MODEL is not None:
        return _FINBERT_AVAILABLE

    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        model_name = "ProsusAI/finbert"
        _FINBERT_TOKENIZER = AutoTokenizer.from_pretrained(model_name)
        _FINBERT_MODEL = AutoModelForSequenceClassification.from_pretrained(model_name)
        _FINBERT_DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
        _FINBERT_MODEL.to(_FINBERT_DEVICE)
        _FINBERT_MODEL.eval()
        _FINBERT_AVAILABLE = True
        logger.info("FinBERT NLP pipeline loaded on %s", _FINBERT_DEVICE)
    except ImportError:
        logger.info("FinBERT unavailable (transformers not installed) — Ollama fallback active")
        _FINBERT_AVAILABLE = False
    except Exception as e:
        logger.warning("FinBERT load failed: %s — Ollama fallback active", e)
        _FINBERT_AVAILABLE = False

    return _FINBERT_AVAILABLE


class NLPPipeline:
    """Real-time financial NLP scoring pipeline."""

    def __init__(self):
        self._score_history: deque = deque(maxlen=1000)
        self._batch_size = 16  # FinBERT batch size for GPU

    async def score_batch(
        self, items: List[Dict[str, str]], publish: bool = True
    ) -> List[Dict[str, Any]]:
        """Score a batch of news items for sentiment.

        Args:
            items: List of {"symbol": str, "text": str, ...}
            publish: Whether to publish to MessageBus

        Returns:
            List of {"symbol": str, "text": str, "sentiment": str,
                     "score": float, "confidence": float, "method": str}
        """
        if not items:
            return []

        t0 = time.monotonic()

        if _load_finbert():
            results = await asyncio.to_thread(self._score_finbert, items)
        else:
            results = await self._score_ollama_fallback(items)

        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        logger.info(
            "NLP pipeline: scored %d items in %.1fms (method=%s)",
            len(results), latency_ms,
            results[0].get("method", "unknown") if results else "none",
        )

        # Publish to MessageBus
        if publish and results:
            try:
                from app.core.message_bus import get_message_bus
                bus = get_message_bus()
                if bus._running:
                    await bus.publish("perception.sentiment", {
                        "type": "nlp_batch",
                        "scores": results,
                        "count": len(results),
                        "latency_ms": latency_ms,
                        "source": "finbert" if _FINBERT_AVAILABLE else "ollama",
                    })
            except Exception:
                pass

        self._score_history.extend(results)
        return results

    def _score_finbert(self, items: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Score using FinBERT on GPU (sync, runs in thread)."""
        import torch

        results = []
        texts = [item.get("text", "")[:512] for item in items]  # FinBERT max 512 tokens

        for i in range(0, len(texts), self._batch_size):
            batch_texts = texts[i:i + self._batch_size]
            batch_items = items[i:i + self._batch_size]

            inputs = _FINBERT_TOKENIZER(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(_FINBERT_DEVICE)

            with torch.no_grad():
                outputs = _FINBERT_MODEL(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)

            # FinBERT labels: positive, negative, neutral
            labels = ["positive", "negative", "neutral"]
            for j, (item, prob) in enumerate(zip(batch_items, probs)):
                pred_idx = int(torch.argmax(prob))
                sentiment = labels[pred_idx]
                score = float(prob[0]) - float(prob[1])  # positive - negative = [-1, 1]
                results.append({
                    "symbol": item.get("symbol", ""),
                    "text": item.get("text", "")[:200],
                    "sentiment": sentiment,
                    "score": round(score, 4),
                    "confidence": round(float(prob[pred_idx]), 4),
                    "method": "finbert_gpu" if _FINBERT_DEVICE == "cuda:0" else "finbert_cpu",
                })

        return results

    async def _score_ollama_fallback(
        self, items: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Fallback: score via Ollama one-shot sentiment."""
        results = []
        try:
            from app.services.llm_router import get_llm_router, Tier
            router = get_llm_router()

            async def _score_one(item):
                text = item.get("text", "")[:300]
                try:
                    result = await router.route_with_fallback(
                        tier=Tier.BRAINSTEM,
                        messages=[
                            {"role": "system", "content": "Classify financial sentiment. Reply with ONLY one word: positive, negative, or neutral."},
                            {"role": "user", "content": text},
                        ],
                        task="sentiment_classify",
                        temperature=0.0,
                        max_tokens=10,
                    )
                    sentiment = (result.content or "neutral").strip().lower()
                    if sentiment not in ("positive", "negative", "neutral"):
                        sentiment = "neutral"
                    score = 0.5 if sentiment == "positive" else (-0.5 if sentiment == "negative" else 0.0)
                    return {
                        "symbol": item.get("symbol", ""),
                        "text": text[:200],
                        "sentiment": sentiment,
                        "score": score,
                        "confidence": 0.6,
                        "method": "ollama",
                    }
                except Exception:
                    return {
                        "symbol": item.get("symbol", ""),
                        "text": text[:200],
                        "sentiment": "neutral",
                        "score": 0.0,
                        "confidence": 0.0,
                        "method": "fallback",
                    }

            results = await asyncio.gather(*[_score_one(item) for item in items[:20]])
        except Exception as e:
            logger.debug("Ollama NLP fallback failed: %s", e)
            for item in items:
                results.append({
                    "symbol": item.get("symbol", ""),
                    "sentiment": "neutral",
                    "score": 0.0,
                    "confidence": 0.0,
                    "method": "fallback",
                })

        return results

    def get_status(self) -> Dict[str, Any]:
        return {
            "finbert_available": _FINBERT_AVAILABLE,
            "device": _FINBERT_DEVICE,
            "scored_total": len(self._score_history),
            "recent_scores": list(self._score_history)[-5:],
        }


# Singleton
_pipeline: Optional[NLPPipeline] = None


def get_nlp_pipeline() -> NLPPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = NLPPipeline()
    return _pipeline
