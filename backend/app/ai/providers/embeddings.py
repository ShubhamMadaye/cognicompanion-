"""
CogniCompanion — Embeddings Provider Abstraction
===================================================
Abstract interface + Google Gemini text-embedding implementation.

Used by the Semantic Retriever to embed:
  - Memory descriptions (at creation time)
  - Patient queries (at query time)

Then cosine similarity search via pgvector finds the most relevant memories.
"""

import abc

import google.generativeai as genai

from app.core.config import get_settings

settings = get_settings()

# Gemini text-embedding-004 produces 768-dimensional vectors
EMBEDDING_DIMENSION = 768


class EmbeddingProvider(abc.ABC):
    """Abstract interface for embedding providers."""

    @abc.abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Return the embedding vector for the given text."""

    @abc.abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a batch of texts."""

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        """Return the embedding vector dimension."""


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self._model = settings.EMBEDDING_MODEL

    async def embed(self, text: str) -> list[float]:
        if not settings.GOOGLE_API_KEY or settings.GOOGLE_API_KEY.startswith("your-") or len(settings.GOOGLE_API_KEY.strip()) < 10:
            return []

        import asyncio

        def _sync_embed() -> list[float]:
            result = genai.embed_content(
                model=self._model,
                content=text,
                task_type="retrieval_document",
                output_dimensionality=EMBEDDING_DIMENSION,
            )
            return result["embedding"]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_embed)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import asyncio

        def _sync_embed_batch() -> list[list[float]]:
            return [
                genai.embed_content(
                    model=self._model,
                    content=text,
                    task_type="retrieval_document",
                    output_dimensionality=EMBEDDING_DIMENSION,
                )["embedding"]
                for text in texts
            ]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_embed_batch)

    @property
    def dimension(self) -> int:
        return EMBEDDING_DIMENSION


def get_embedding_provider() -> EmbeddingProvider:
    """Factory — returns the configured embedding provider."""
    return GeminiEmbeddingProvider()
