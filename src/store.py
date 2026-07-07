from __future__ import annotations

from dataclasses import dataclass

import chromadb

from src.chunker import TextChunk
from src.config import settings


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    title: str
    section: str
    source_path: str
    page_number: int
    text: str
    score: float


class VectorStore:
    def __init__(self) -> None:
        settings.vector_store_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(settings.vector_store_path))
        self._collection = self._client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        self._client.delete_collection(settings.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[TextChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")

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
        return self._collection.count()
