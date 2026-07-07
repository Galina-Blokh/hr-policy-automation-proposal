from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass
class DocumentPage:
    doc_id: str
    title: str
    source_path: str
    page_number: int
    text: str


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
    return slug or "document"


def load_pdf(path: Path) -> list[DocumentPage]:
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
