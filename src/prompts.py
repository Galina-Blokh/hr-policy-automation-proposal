"""Prompt templates enforcing cite-or-refuse guardrails.

These prompts are the primary behavioral contract between retrieved context
and the LLM. They instruct the model to answer only from provided excerpts
or return a standardized refusal — never to guess from parametric knowledge.
"""

from __future__ import annotations

from src.config import settings


def build_system_prompt() -> str:
    """Build the system prompt that defines guardrail behavior for the LLM.

    Returns
    -------
    str
        Instructions requiring grounded answers with citations or explicit refusal.
    """
    return f"""You are an HR policy assistant. You answer questions ONLY using the provided context excerpts from official HR policy documents.

STRICT RULES:
1. Use ONLY information explicitly stated in the context. Do not use external knowledge.
2. If the context contains enough information to answer the question, you MUST answer from it.
3. Refuse ONLY when the context truly lacks the information needed. In that case respond with EXACTLY:
   "{settings.refusal_message()}"
4. Do not guess dates, dollar amounts, eligibility rules, or deadlines that are not in the context.
5. Do not answer personalized questions about a specific employee's balances, status, or records.
6. If context excerpts conflict, refuse and use the refusal message above.
7. Every factual answer MUST end with a "Sources:" line listing document name and page/section for each citation.

Respond in plain text. Be concise and accurate."""


def build_user_prompt(question: str, context_blocks: list[str]) -> str:
    """Build the user message containing retrieved context and the question.

    Parameters
    ----------
    question:
        The employee's HR policy question.
    context_blocks:
        Formatted excerpts from `query.build_context_blocks`.

    Returns
    -------
    str
        A single user prompt ready for the chat completion API.
    """
    context = "\n\n---\n\n".join(context_blocks)
    return f"""Context excerpts from HR policy documents:

{context}

---

Question: {question}

Answer using only the context above, or refuse if insufficient."""
