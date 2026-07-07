"""PDF document loading for HR policy handbooks.

Extracts per-page text from PDF files and attaches stable identifiers
used downstream for chunking, citation, and vector-store metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass
class DocumentPage:
    """A single page extracted from an HR policy PDF.

    Attributes
    ----------
    doc_id:
        URL-safe slug derived from the filename (stable across re-ingestion).
    title:
        Human-readable document title for citations.
    source_path:
        Absolute or relative path to the source PDF file.
    page_number:
        1-based page index within the PDF.
    text:
        Extracted plain text for the page (empty pages are skipped).
    """

    doc_id: str
    title: str
    source_path: str
    page_number: int
    text: str


def slugify(name: str) -> str:
    """Convert a filename stem into a stable, filesystem-safe document ID."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
    return slug or "document"


def load_pdf(path: Path) -> list[DocumentPage]:
    """Load all non-empty pages from a single PDF file.

    Parameters
    ----------
    path:
        Path to a `.pdf` policy document.

    Returns
    -------
    list[DocumentPage]
        One record per page that contains extractable text.
    """
    reader = PdfReader(str(path))
    doc_id = slugify(path.stem)
    title = path.stem.replace("-", " ").replace("_", " ")
    pages: list[DocumentPage] = []

    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(
                DocumentPage(
                    doc_id=doc_id,
                    title=title,
                    source_path=str(path),
                    page_number=index,
                    text=text,
                )
            )
    return pages


def load_documents(source: Path) -> list[DocumentPage]:
    """Load PDF pages from a file or all PDFs in a directory.

    Parameters
    ----------
    source:
        Path to a single PDF or a directory containing `*.pdf` files.

    Returns
    -------
    list[DocumentPage]
        Combined pages from all matched PDF files, sorted by filename.

    Raises
    ------
    FileNotFoundError
        If no PDF files are found at the given path.
    """
    if source.is_file():
        paths = [source]
    else:
        paths = sorted(source.glob("*.pdf"))

    if not paths:
        raise FileNotFoundError(f"No PDF files found at {source}")

    pages: list[DocumentPage] = []
    for path in paths:
        pages.extend(load_pdf(path))
    return pages
