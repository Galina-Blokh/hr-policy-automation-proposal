"""Application configuration loaded from environment variables.

Centralizes all runtime settings so modules share a single source of truth.
Values are read from a `.env` file (via python-dotenv) and process environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable runtime configuration for the RAG pipeline.

    Attributes
    ----------
    openai_api_key:
        Required for embeddings and primary LLM generation.
    groq_api_key:
        Used as fallback LLM when OpenAI generation fails.
    embedding_model:
        OpenAI embedding model identifier (e.g. text-embedding-3-small).
    openai_llm_model:
        Primary chat model for answer generation.
    groq_llm_model:
        Fallback chat model when OpenAI is unavailable.
    vector_store_path:
        Local directory for the ChromaDB persistent store.
    data_dir:
        Default directory containing source PDF policy documents.
    top_k:
        Number of chunks to retrieve per query.
    refusal_threshold:
        Minimum cosine similarity (0–1) required before invoking the LLM.
        Below this threshold the system refuses without generation.
    chunk_size:
        Target chunk length in tokens during ingestion.
    chunk_overlap:
        Token overlap between consecutive chunks to preserve context.
    hr_contact_email:
        Contact address included in refusal messages.
    collection_name:
        ChromaDB collection name for stored policy chunks.
    """

    openai_api_key: str
    groq_api_key: str
    embedding_model: str
    openai_llm_model: str
    groq_llm_model: str
    vector_store_path: Path
    data_dir: Path
    top_k: int
    refusal_threshold: float
    chunk_size: int
    chunk_overlap: int
    hr_contact_email: str
    collection_name: str = "hr_policies"

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from environment variables with sensible defaults."""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            openai_llm_model=os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini"),
            groq_llm_model=os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile"),
            vector_store_path=Path(os.getenv("VECTOR_STORE_PATH", "./data/chroma")),
            data_dir=Path(os.getenv("DATA_DIR", "./data")),
            top_k=int(os.getenv("TOP_K", "5")),
            refusal_threshold=float(os.getenv("REFUSAL_THRESHOLD", "0.40")),
            chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
            hr_contact_email=os.getenv("HR_CONTACT_EMAIL", "hr@company.com"),
        )

    def refusal_message(self) -> str:
        """Return the standardized refusal text shown to employees."""
        return (
            f"I cannot verify this from the current HR policy documents. "
            f"Please contact {self.hr_contact_email} for assistance."
        )


# Module-level singleton used across the application.
settings = Settings.from_env()
