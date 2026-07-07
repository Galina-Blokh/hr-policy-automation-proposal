"""LLM chat completion with provider fallback.

Primary path uses OpenAI for answer generation. If OpenAI fails (rate limit,
outage, auth error), the client automatically retries with Groq so the
prototype remains usable during demos.
"""

from __future__ import annotations

import logging

from groq import Groq
from openai import OpenAI

from src.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Generate grounded answers using OpenAI with Groq as fallback."""

    def __init__(self) -> None:
        self._openai: OpenAI | None = None
        self._groq: Groq | None = None

        if settings.openai_api_key:
            self._openai = OpenAI(api_key=settings.openai_api_key)
        if settings.groq_api_key:
            self._groq = Groq(api_key=settings.groq_api_key)

        if not self._openai and not self._groq:
            raise RuntimeError("At least one of OPENAI_API_KEY or GROQ_API_KEY is required.")

    def complete(self, system_prompt: str, user_prompt: str) -> tuple[str, str]:
        """Run a chat completion with temperature 0 for deterministic output.

        Parameters
        ----------
        system_prompt:
            Guardrail instructions defining cite-or-refuse behavior.
        user_prompt:
            Retrieved context excerpts and the employee question.

        Returns
        -------
        tuple[str, str]
            `(answer_text, provider_name)` where provider is `"openai"` or
            `"groq"`.

        Raises
        ------
        RuntimeError
            If all configured providers fail.
        """
        errors: list[str] = []

        if self._openai:
            try:
                response = self._openai.chat.completions.create(
                    model=settings.openai_llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0,
                )
                content = response.choices[0].message.content or ""
                return content.strip(), "openai"
            except Exception as exc:  # noqa: BLE001 — collect and try fallback
                errors.append(f"OpenAI: {exc}")
                logger.warning("OpenAI completion failed, trying Groq fallback: %s", exc)

        if self._groq:
            try:
                response = self._groq.chat.completions.create(
                    model=settings.groq_llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0,
                )
                content = response.choices[0].message.content or ""
                return content.strip(), "groq"
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Groq: {exc}")

        raise RuntimeError("All LLM providers failed. " + " | ".join(errors))
