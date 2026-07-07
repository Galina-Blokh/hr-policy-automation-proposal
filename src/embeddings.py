"""OpenAI embedding client for vectorizing policy text.

Embeddings are required for semantic retrieval. This prototype uses OpenAI
exclusively for embeddings because Groq does not expose an embedding API.
Generation fallback (Groq) is handled separately in `llm.py`.
"""

from __future__ import annotations

from openai import OpenAI

from src.config import settings


class EmbeddingClient:
    """Create dense vector representations of text chunks and queries."""

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings.")
        self._client = OpenAI(api_key=settings.openai_api_key)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of strings using the configured OpenAI model.

        Parameters
        ----------
        texts:
            Plain-text strings to vectorize (chunks during ingest, questions
            during query).

        Returns
        -------
        list[list[float]]
            Embedding vectors in the same order as the input texts.
        """
        if not texts:
            return []

        response = self._client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
