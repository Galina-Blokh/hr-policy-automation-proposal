"""Streamlit web UI for HR policy Q&A.

Provides a chat interface on top of the cite-or-refuse RAG pipeline.
Run with: streamlit run src/ui.py
"""

from __future__ import annotations

import streamlit as st

from src.config import settings
from src.query import QueryResponse, answer_question
from src.store import VectorStore

EXAMPLE_QUESTIONS = [
    "What is the company policy on remote work?",
    "When does vacation accrual start?",
    "What is the sick leave policy?",
    "How many vacation days do I have left?",
]


def _check_vector_store() -> int:
    """Return the number of indexed chunks, or 0 if the store is unavailable."""
    try:
        return VectorStore().count
    except Exception:  # noqa: BLE001 — show friendly UI message instead of traceback
        return 0


def _render_citations(citations: list[dict]) -> None:
    """Render source document citations below an answer."""
    if not citations:
        return
    with st.expander("Sources", expanded=True):
        for cite in citations:
            st.markdown(
                f"- **{cite['title']}** — {cite['section']} "
                f"(page {cite['page_number']}, `{cite['chunk_id']}`)"
            )


def _render_response(response: QueryResponse) -> None:
    """Render a structured query response in the chat panel."""
    if response.status == "answered":
        st.success("Answer verified from policy documents")
        st.markdown(response.answer)
        _render_citations(response.citations)
    else:
        st.warning("Unable to verify from policy documents")
        st.markdown(response.answer)

    meta_parts = [f"Retrieval score: `{response.retrieval_score:.2f}`"]
    if response.provider:
        meta_parts.append(f"LLM: `{response.provider}`")
    if response.reason:
        meta_parts.append(f"Reason: `{response.reason}`")
    st.caption(" · ".join(meta_parts))


def _submit_question(question: str) -> None:
    """Run the RAG pipeline and append the exchange to session history."""
    st.session_state.messages.append({"role": "user", "content": question})
    try:
        response = answer_question(question)
        st.session_state.messages.append({"role": "assistant", "response": response})
    except Exception as exc:  # noqa: BLE001
        st.session_state.messages.append({"role": "assistant", "error": str(exc)})


def _render_message(message: dict) -> None:
    """Render one message from session history."""
    if message["role"] == "assistant" and "response" in message:
        _render_response(message["response"])
    elif message["role"] == "assistant" and "error" in message:
        st.error(f"Query failed: {message['error']}")
    else:
        st.markdown(message["content"])


def _run_question(question: str, chunk_count: int) -> None:
    """Validate and submit a question, then rerun the app."""
    cleaned = question.strip()
    if not cleaned:
        return
    if chunk_count == 0:
        st.session_state["ui_error"] = "Ingest policy PDFs before asking questions."
        st.rerun()
    with st.spinner("Searching policy documents…"):
        _submit_question(cleaned)
    st.rerun()


def _render_input_area(chunk_count: int) -> None:
    """Render the question input pinned above conversation history."""
    st.subheader("Ask a question")

    with st.form("question_form", clear_on_submit=True):
        prompt = st.text_area(
            "Question",
            placeholder="e.g. What is the company policy on remote work?",
            label_visibility="collapsed",
            height=80,
        )
        submitted = st.form_submit_button("Ask", type="primary", use_container_width=True)

    if submitted:
        _run_question(prompt, chunk_count)

    st.caption("Try an example:")
    for index, example in enumerate(EXAMPLE_QUESTIONS):
        if st.button(
            example,
            key=f"example-{index}",
            use_container_width=True,
            disabled=chunk_count == 0,
        ):
            _run_question(example, chunk_count)


def main() -> None:
    """Streamlit application entry point."""
    st.set_page_config(
        page_title="HR Policy Assistant",
        page_icon="📋",
        layout="centered",
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.title("HR Policy Assistant")
    st.markdown(
        "Ask questions about company HR policies. Answers are generated **only** "
        "from ingested handbook documents, with citations — or the assistant refuses."
    )

    chunk_count = _check_vector_store()

    with st.sidebar:
        st.header("About")
        st.markdown(
            "This prototype uses **Guardrailed RAG** (Option 2): retrieve policy "
            "text, answer with citations, or refuse when unsure."
        )
        st.divider()
        st.subheader("Indexed documents")
        if chunk_count > 0:
            st.metric("Policy chunks", chunk_count)
        else:
            st.error("Vector store is empty.")
            st.code("python -m src.ingest --source data", language="bash")
            st.caption("Run ingestion before asking questions.")

        if st.session_state.messages:
            st.divider()
            if st.button("Clear chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

        st.divider()
        st.caption(f"Contact for escalations: {settings.hr_contact_email}")

    if chunk_count == 0:
        st.info("Ingest HR policy PDFs to enable Q&A. See sidebar for the command.")
        return

    ui_error = st.session_state.pop("ui_error", None)
    if ui_error:
        st.error(ui_error)

    # Input stays above all conversation history on every rerun.
    _render_input_area(chunk_count)

    st.divider()
    st.subheader("Conversation")

    if not st.session_state.messages:
        st.caption("No questions yet. Use the input above to get started.")
    else:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                _render_message(message)


def launch() -> None:
    """Launch the Streamlit server (used by the `hr-ui` console script)."""
    import subprocess
    import sys
    from pathlib import Path

    ui_path = Path(__file__).resolve()
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(ui_path), "--server.headless", "true"],
        check=True,
    )


if __name__ == "__main__":
    main()
