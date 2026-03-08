"""Embedding Service — sentence embeddings using local GPU inference.

Uses sentence-transformers/all-MiniLM-L6-v2 on cuda:0 for fast embedding
generation. Falls back to CPU if CUDA unavailable.

RTX Optimization: runs on PC-1 RTX GPU with ~4ms per embedding batch.
"""
import logging
import os
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Embedding engine using sentence-transformers on local GPU."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None
        self._device = None

    def _load_model(self):
        """Lazy-load the sentence transformer model."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
            import torch

            device = os.getenv("GPU_DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
            self._model = SentenceTransformer(self._model_name, device=device)
            self._device = device
            logger.info("EmbeddingEngine loaded %s on %s", self._model_name, device)
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers. "
                "Falling back to hash-based pseudo-embeddings."
            )
            self._model = "fallback"
            self._device = "cpu"

    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate normalized embeddings for a list of texts.

        Args:
            texts: List of strings to embed

        Returns:
            np.ndarray of shape (len(texts), embedding_dim), L2-normalized
        """
        self._load_model()

        if self._model == "fallback":
            return self._fallback_embed(texts)

        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return np.array(embeddings, dtype=np.float32)

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single text and return 1D array."""
        return self.embed([text])[0]

    def find_similar(
        self,
        query_embedding: np.ndarray,
        corpus_embeddings: np.ndarray,
        top_k: int = 10,
    ) -> List[tuple]:
        """Find top-k most similar embeddings by cosine similarity.

        Args:
            query_embedding: 1D normalized embedding
            corpus_embeddings: 2D array of normalized embeddings
            top_k: Number of results to return

        Returns:
            List of (index, similarity_score) tuples, sorted by score descending
        """
        if len(corpus_embeddings) == 0:
            return []

        # Cosine similarity (embeddings are already normalized)
        scores = corpus_embeddings @ query_embedding
        top_indices = np.argsort(scores)[::-1][:top_k]

        return [(int(idx), float(scores[idx])) for idx in top_indices]

    def _fallback_embed(self, texts: List[str]) -> np.ndarray:
        """Hash-based pseudo-embeddings when sentence-transformers unavailable."""
        import hashlib
        dim = 384  # same as MiniLM
        embeddings = []
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            # Extend hash to fill dimension
            extended = h * (dim // len(h) + 1)
            vec = np.frombuffer(extended[:dim * 4], dtype=np.float32)[:dim]
            vec = vec / (np.linalg.norm(vec) + 1e-8)
            embeddings.append(vec)
        return np.array(embeddings, dtype=np.float32)


# Singleton
_engine: Optional[EmbeddingEngine] = None


def get_embedding_engine() -> EmbeddingEngine:
    global _engine
    if _engine is None:
        from app.core.config import settings
        _engine = EmbeddingEngine(
            model_name=getattr(settings, "KNOWLEDGE_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        )
    return _engine
