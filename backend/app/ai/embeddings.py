import hashlib
import logging
from typing import List, Optional
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 768  # text-embedding-004 dimension


class EmbeddingProvider:
    """Provides vector embeddings using Gemini API with graceful local fallback."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_EMBEDDING_MODEL
        self._client = None
        self._init_gemini()

    def _init_gemini(self):
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized Google GenAI embedding client with model: {self.model}")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI embedding client: {e}")
                self._client = None
        else:
            self._client = None

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string into a 768-dimensional float vector."""
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIMENSION

        if self._client:
            try:
                response = self._client.models.embed_content(
                    model=self.model,
                    contents=text.strip(),
                )
                if hasattr(response, "embedding") and response.embedding:
                    # In google-genai response.embedding is an object with values
                    vals = response.embedding.values if hasattr(response.embedding, "values") else response.embedding
                    # Normalize vector
                    arr = np.array(vals, dtype=np.float32)
                    norm = np.linalg.norm(arr)
                    if norm > 0:
                        arr = arr / norm
                    return arr.tolist()
                elif hasattr(response, "embeddings") and response.embeddings:
                    vals = response.embeddings[0].values
                    arr = np.array(vals, dtype=np.float32)
                    norm = np.linalg.norm(arr)
                    if norm > 0:
                        arr = arr / norm
                    return arr.tolist()
            except Exception as e:
                logger.warning(f"Gemini embedding API call failed: {e}. Falling back to deterministic embedding.")

        # Deterministic semantic hash fallback when Gemini key is not configured or offline
        return self._deterministic_fallback_embed(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of text documents."""
        return [self.embed_text(t) for t in texts]

    def _deterministic_fallback_embed(self, text: str) -> List[float]:
        """Produces a deterministic normalized unit vector for offline/test environments."""
        words = text.lower().split()
        vec = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
        for i, word in enumerate(words):
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            idx = h % EMBEDDING_DIMENSION
            weight = 1.0 / (1.0 + (i * 0.1))
            vec[idx] += weight

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        else:
            vec[0] = 1.0
        return vec.tolist()


embedding_provider = EmbeddingProvider()
