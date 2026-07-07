"""Online query pipeline with cite-or-refuse guardrails.

Implements a three-layer safety model:
1. Pre-filter — block personalized questions before retrieval.
2. Retrieval gate — refuse when similarity score is below threshold.
3. LLM guardrail — prompt-enforced grounding with post-check for refusal text.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass

from src.config import settings
from src.embeddings import EmbeddingClient
from src.llm import LLMClient
from src.prompts import build_system_prompt, build_user_prompt
from src.store import RetrievedChunk, VectorStore

# Regex patterns for questions that require HRIS data, not static policy text.
PERSONALIZED_PATTERNS = [
    r"\bmy\b.*\b(balance|pto|vacation days|leave days|enrollment status)\b",
    r"\bhow many (pto|vacation|leave) days do i have\b",
    r"\bwhat is my\b",
    r"\bdo i have\b.*\b(days|leave|balance)\b",
]


@dataclass
class QueryResponse:
    """Structured response returned by the query pipeline.

    Attributes
    ----------
    status:
        Either `"answered"` or `"refused"`.
    citations:
        Source document references (empty when refused).
    retrieval_score:
        Best cosine similarity among retrieved chunks (0 if not retrieved).
    provider:
        LLM provider used (`"openai"`, `"groq"`, or None if LLM not called).
    reason:
        Machine-readable refusal cause for logging and evaluation.
    """

    question: str
    status: str
    answer: str
    citations: list[dict]
    retrieval_score: float
    provider: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict:
        """Serialize the response to a JSON-compatible dictionary."""
        return asdict(self)


def is_personalized_question(question: str) -> bool:
    """Detect questions that require individual employee data (Layer 1 guardrail)."""
    lowered = question.lower()
    return any(re.search(pattern, lowered) for pattern in PERSONALIZED_PATTERNS)


def build_context_blocks(chunks: list[RetrievedChunk]) -> list[str]:
    """Format retrieved chunks as labeled context blocks for the LLM prompt."""
    blocks: list[str] = []
    for chunk in chunks:
        blocks.append(
            f"[{chunk.title} | {chunk.section} | chunk {chunk.chunk_id}]\n{chunk.text}"
        )
    return blocks


def extract_citations(chunks: list[RetrievedChunk]) -> list[dict]:
    """Build deduplicated citation records from retrieved chunks."""
    seen: set[str] = set()
    citations: list[dict] = []
    for chunk in chunks:
        if chunk.chunk_id in seen:
            continue
        seen.add(chunk.chunk_id)
        citations.append(
            {
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "section": chunk.section,
                "chunk_id": chunk.chunk_id,
                "page_number": chunk.page_number,
            }
        )
    return citations


def is_refusal(answer: str) -> bool:
    """Detect whether the LLM returned the standardized refusal message."""
    normalized = answer.strip().lower()
    refusal = settings.refusal_message().strip().lower()
    return normalized == refusal or normalized.startswith("i cannot verify this from the current hr policy")


def answer_question(question: str) -> QueryResponse:
    """Answer an HR policy question using the full RAG + guardrail pipeline.

    Parameters
    ----------
    question:
        Natural-language question from an employee.

    Returns
    -------
    QueryResponse
        Structured result with status, answer text, citations, and metadata.

    Raises
    ------
    RuntimeError
        If the vector store has not been populated via ingestion.
    """
    # Layer 1: refuse personalized questions without retrieval or LLM calls.
    if is_personalized_question(question):
        return QueryResponse(
            question=question,
            status="refused",
            answer=settings.refusal_message(),
            citations=[],
            retrieval_score=0.0,
            provider=None,
            reason="personalized_question",
        )

    embedder = EmbeddingClient()
    store = VectorStore()
    if store.count == 0:
        raise RuntimeError("Vector store is empty. Run `python -m src.ingest` first.")

    query_embedding = embedder.embed_texts([question])[0]
    retrieved = store.query(query_embedding)
    best_score = retrieved[0].score if retrieved else 0.0

    # Layer 2: refuse when retrieval confidence is too low to ground an answer.
    if not retrieved or best_score < settings.refusal_threshold:
        return QueryResponse(
            question=question,
            status="refused",
            answer=settings.refusal_message(),
            citations=[],
            retrieval_score=best_score,
            provider=None,
            reason="low_retrieval_score",
        )

    # Layer 3: LLM generation with cite-or-refuse prompt contract.
    llm = LLMClient()
    context_blocks = build_context_blocks(retrieved)
    raw_answer, provider = llm.complete(
        build_system_prompt(),
        build_user_prompt(question, context_blocks),
    )

    if is_refusal(raw_answer):
        return QueryResponse(
            question=question,
            status="refused",
            answer=settings.refusal_message(),
            citations=[],
            retrieval_score=best_score,
            provider=provider,
            reason="model_refusal",
        )

    citations = extract_citations(retrieved)
    return QueryResponse(
        question=question,
        status="answered",
        answer=raw_answer,
        citations=citations,
        retrieval_score=best_score,
        provider=provider,
    )


def main() -> None:
    """CLI entry point for single-turn policy Q&A."""
    parser = argparse.ArgumentParser(description="Query HR policy documents with cite-or-refuse RAG.")
    parser.add_argument("question", type=str, help="HR policy question")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    args = parser.parse_args()

    response = answer_question(args.question)
    payload = response.to_dict()
    if args.pretty:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload))


if __name__ == "__main__":
    main()
