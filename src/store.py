"""ChromaDB vector store wrapper for policy chunk retrieval.

ChromaDB was chosen for the MVP because it requires no external database
infrastructure — embeddings persist locally under `data/chroma/`. For
production deployments that already run PostgreSQL, consider migrating this
module to pgvector while keeping the public interface unchanged.

See spec.md §14 (Vector Store Decision) for the full rationale.
"""

from __future__ import annotations

from dataclasses import dataclass

import chromadb

from src.chunker import TextChunk
from src.config import settings


@dataclass
class RetrievedChunk:
    """A policy chunk returned by similarity search with a relevance score.

    Attributes
    ----------
    score:
        Cosine similarity in the range [0, 1], derived from ChromaDB distance.
    """

    chunk_id: str
    doc_id: str
    title: str
    section: str
    source_path: str
    page_number: int
    text: str
    score: float


class VectorStore:
    """Persistent local vector store backed by ChromaDB.

    Uses cosine distance so that higher `score` values indicate stronger
    semantic matches between a query and a stored chunk.
    """

    def __init__(self) -> None:
        settings.vector_store_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(settings.vector_store_path))
        self._collection = self._client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        """Delete and recreate the collection (used on full re-ingestion)."""
        self._client.delete_collection(settings.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[TextChunk], embeddings: list[list[float]]) -> None:
        """Insert chunked policy text with precomputed embedding vectors.

        Parameters
        ----------
        chunks:
            Text segments produced by the chunker.
        embeddings:
            Parallel list of embedding vectors from `EmbeddingClient`.

        Raises
        ------
        ValueError
            If `chunks` and `embeddings` differ in length.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")

        # Batch inserts to stay within API and memory limits on large corpora.
        batch_size = 100
        for start in range(0, len(chunks), batch_size):
            batch_chunks = chunks[start : start + batch_size]
            batch_embeddings = embeddings[start : start + batch_size]
            self._collection.add(
                ids=[chunk.chunk_id for chunk in batch_chunks],
                embeddings=batch_embeddings,
                documents=[chunk.text for chunk in batch_chunks],
                metadatas=[
                    {
                        "doc_id": chunk.doc_id,
                        "title": chunk.title,
                        "section": chunk.section,
                        "source_path": chunk.source_path,
                        "page_number": chunk.page_number,
                    }
                    for chunk in batch_chunks
                ],
            )

    def query(self, embedding: list[float], top_k: int | None = None) -> list[RetrievedChunk]:
        """Retrieve the most semantically similar chunks to a query embedding.

        Parameters
        ----------
        embedding:
            Query vector from `EmbeddingClient.embed_texts`.
        top_k:
            Number of results to return (defaults to `settings.top_k`).

        Returns
        -------
        list[RetrievedChunk]
            Matches ordered by descending similarity score.
        """
        k = top_k or settings.top_k
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        retrieved: list[RetrievedChunk] = []
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances, strict=True):
            # ChromaDB returns cosine distance; convert to similarity for threshold checks.
            score = max(0.0, 1.0 - distance)
            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    doc_id=metadata["doc_id"],
                    title=metadata["title"],
                    section=metadata["section"],
                    source_path=metadata["source_path"],
                    page_number=int(metadata["page_number"]),
                    text=text,
                    score=score,
                )
            )
        return retrieved

    @property
    def count(self) -> int:
        """Return the number of vectors currently stored."""
        return self._collection.count()
