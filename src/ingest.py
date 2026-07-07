"""Offline ingestion pipeline: PDF → chunks → embeddings → vector store.

Run this module after adding or updating policy PDFs in `data/`. Re-ingestion
replaces the entire ChromaDB collection by default to avoid stale chunks.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.chunker import chunk_pages
from src.config import settings
from src.documents import load_documents
from src.embeddings import EmbeddingClient
from src.store import VectorStore


def ingest(source: Path, reset: bool = True) -> dict:
    """Ingest HR policy PDFs into the local vector store.

    Pipeline stages:
    1. Load and extract text from PDF pages.
    2. Split pages into overlapping token chunks.
    3. Embed chunks via OpenAI.
    4. Persist vectors and metadata in ChromaDB.

    Parameters
    ----------
    source:
        Path to a PDF file or directory of PDFs.
    reset:
        When True, wipe the existing collection before inserting new vectors.

    Returns
    -------
    dict
        Summary statistics printed by the CLI (document/page/chunk counts).
    """
    pages = load_documents(source)
    chunks = chunk_pages(pages)

    embedder = EmbeddingClient()
    store = VectorStore()
    if reset:
        store.reset()

    # Embed in batches to respect OpenAI input limits and reduce round trips.
    batch_size = 64
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        embeddings = embedder.embed_texts([chunk.text for chunk in batch])
        store.add_chunks(batch, embeddings)

    return {
        "source": str(source),
        "documents": len({page.doc_id for page in pages}),
        "pages": len(pages),
        "chunks": len(chunks),
        "vector_store": str(settings.vector_store_path),
        "stored_vectors": store.count,
    }


def main() -> None:
    """CLI entry point for document ingestion."""
    parser = argparse.ArgumentParser(description="Ingest HR policy PDFs into the vector store.")
    parser.add_argument(
        "--source",
        type=Path,
        default=settings.data_dir,
        help="PDF file or directory containing PDFs (default: DATA_DIR)",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Append to existing vector store instead of replacing it.",
    )
    args = parser.parse_args()

    summary = ingest(args.source, reset=not args.no_reset)
    print("Ingestion complete:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
