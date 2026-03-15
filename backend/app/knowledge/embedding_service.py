"""Embedding Service — sentence embeddings using local GPU inference.

Uses sentence-transformers/all-MiniLM-L6-v2 on cuda:0 for fast embedding
generation. Falls back to CPU if CUDA unavailable.

RTX Optimization: runs on PC-1 RTX GPU with ~4ms per embedding batch.
"""
import logging
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

            # Respect EMBEDDING_DEVICE from config; auto-detect if empty
            from app.core.config import settings
            cfg_device = getattr(settings, "EMBEDDING_DEVICE", "").strip()
            if cfg_device:
                device = cfg_device
            else:
                device = "cuda:0" if torch.cuda.is_available() else "cpu"
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

        # GPU Channel 10: RTX 4080 can handle 512-batch for MiniLM-L6-v2
        # CPU stays at 32 to avoid memory pressure
        gpu_batch = 512 if self._device and "cuda" in str(self._device) else 32
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=gpu_batch,
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
        byte_len = dim * 4  # float32
        embeddings = []
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            # Extend hash to at least byte_len bytes so we get 384 float32s
            n = (byte_len // len(h)) + 1
            extended = (h * n)[:byte_len]
            vec = np.frombuffer(extended, dtype=np.float32).copy()
            if len(vec) < dim:
                vec = np.resize(vec, dim).astype(np.float32)
            norm = np.linalg.norm(vec)
            if norm < 1e-8:
                vec = np.zeros(dim, dtype=np.float32)
                vec[0] = 1.0  # ensure non-zero for normalization
            else:
                vec = vec / norm
            embeddings.append(vec.astype(np.float32))
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
