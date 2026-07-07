"""Token-based text chunking for RAG ingestion.

Splits document pages into overlapping segments sized for embedding models
and retrieval. Overlap reduces the risk of splitting a policy sentence
across chunk boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from src.config import settings
from src.documents import DocumentPage


@dataclass
class TextChunk:
    """A retrievable segment of policy text with citation metadata.

    Attributes
    ----------
    chunk_id:
        Unique identifier: `{doc_id}#p{page}c{index}`.
    section:
        Human-readable location string used in citations (title + page).
    """

    chunk_id: str
    doc_id: str
    title: str
    source_path: str
    section: str
    page_number: int
    text: str


def _encoding() -> tiktoken.Encoding:
    """Return the tokenizer used to measure chunk sizes in tokens."""
    try:
        return tiktoken.encoding_for_model("gpt-4o-mini")
    except KeyError:
        # Fall back to the cl100k_base encoding used by OpenAI embedding models.
        return tiktoken.get_encoding("cl100k_base")


def _token_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into fixed-size token windows with sliding overlap.

    Parameters
    ----------
    text:
        Source text from a document page.
    chunk_size:
        Maximum tokens per chunk.
    overlap:
        Tokens shared between consecutive chunks.

    Returns
    -------
    list[str]
        Decoded text segments ready for embedding.
    """
    enc = _encoding()
    tokens = enc.encode(text)
    if not tokens:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(enc.decode(tokens[start:end]))
        if end >= len(tokens):
            break
        # Slide the window forward, preserving `overlap` tokens of context.
        start = max(end - overlap, start + 1)
    return chunks


def chunk_pages(pages: list[DocumentPage]) -> list[TextChunk]:
    """Convert document pages into embedding-ready text chunks.

    Parameters
    ----------
    pages:
        Extracted pages from `documents.load_documents`.

    Returns
    -------
    list[TextChunk]
        All chunks across all pages, each with stable IDs and citation metadata.
    """
    chunks: list[TextChunk] = []
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    for page in pages:
        segments = _token_split(page.text, chunk_size, overlap)
        for index, segment in enumerate(segments):
            chunk_id = f"{page.doc_id}#p{page.page_number:03d}c{index:03d}"
            section = f"{page.title} — page {page.page_number}"
            chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    doc_id=page.doc_id,
                    title=page.title,
                    source_path=page.source_path,
                    section=section,
                    page_number=page.page_number,
                    text=segment,
                )
            )
    return chunks
