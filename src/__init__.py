"""Guardrailed Knowledge RAG for HR policy Q&A.

This package implements Option 2 from the project proposal: a document-centric
Retrieval-Augmented Generation (RAG) pipeline that answers HR policy questions
from ingested PDF handbooks with strict cite-or-refuse guardrails.

Modules
-------
config      Application settings loaded from environment variables.
documents   PDF loading and page extraction.
chunker     Token-based text segmentation with overlap.
embeddings  OpenAI embedding client for vectorization.
store       ChromaDB vector store wrapper (local, persistent).
llm         Chat completion with OpenAI primary and Groq fallback.
prompts     Guardrail prompt templates for the LLM.
ingest      Offline pipeline: PDF → chunks → embeddings → store.
query       Online pipeline: retrieve → generate → cite-or-refuse.
eval        Golden Q&A evaluation runner.
ui          Streamlit web chat interface.

Example
-------
>>> # python -m src.ingest --source data
>>> # python -m src.query "What is the remote work policy?" --pretty
"""

__all__ = [
    "config",
    "documents",
    "chunker",
    "embeddings",
    "store",
    "llm",
    "prompts",
    "ingest",
    "query",
    "eval",
    "ui",
]
