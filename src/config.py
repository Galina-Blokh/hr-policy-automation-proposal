from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
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
        return (
            f"I cannot verify this from the current HR policy documents. "
            f"Please contact {self.hr_contact_email} for assistance."
        )


settings = Settings.from_env()
