# HR Policy Automation — Guardrailed Knowledge RAG

> **Branch:** `prototype/guardrailed-knowledge-rag`  
> **Status:** Working MVP — CLI prototype with cite-or-refuse guardrails  
> **Proposal:** [plan.md](./plan.md) · **Technical spec:** [spec.md](./spec.md)

A document-centric Retrieval-Augmented Generation (RAG) system that answers repetitive HR policy questions from verified PDF handbooks — with strict **cite-or-refuse** behavior to prevent hallucinated policy answers.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Usage](#usage)
5. [Configuration](#configuration)
6. [Response Format](#response-format)
7. [Project Structure](#project-structure)
8. [Guardrail Model](#guardrail-model)
9. [Evaluation](#evaluation)
10. [Design Decisions](#design-decisions)
11. [Scope Boundaries](#scope-boundaries)
12. [Troubleshooting](#troubleshooting)

---

## Overview

### Problem

HR teams spend hours each week answering the same policy questions from new hires — vacation accrual, expense rules, benefits deadlines. The stakeholder request was vague: *"Can we automate this somehow?"*

The real need is **safe question deflection** — not a chatbot that sounds helpful but invents policy.

### Solution

This prototype (Option 2 from the proposal) ingests HR PDF handbooks, retrieves relevant passages via semantic search, and generates answers **only** from retrieved context. When context is insufficient, it refuses and directs the employee to HR.

### When to use this approach

| Good fit | Poor fit |
| :--- | :--- |
| Static policy text in existing PDFs | Personalized data ("my PTO balance") |
| Privacy-sensitive document handling | Need Slack bot live in 1 week |
| Compliance risk on wrong answers | Policies scattered / undocumented |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     OFFLINE — Ingestion                         │
│  data/*.pdf  →  documents  →  chunker  →  embeddings  →  store │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                           data/chroma/ (ChromaDB)
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                      ONLINE — Query                             │
│  question  →  embed  →  retrieve top-K  →  LLM  →  response   │
│                     ↑ guardrails at 3 layers ↑                  │
└─────────────────────────────────────────────────────────────────┘
```

| Layer | Module | Responsibility |
| :--- | :--- | :--- |
| Load | `documents.py` | Extract text from PDF pages |
| Chunk | `chunker.py` | Token-based segmentation with overlap |
| Embed | `embeddings.py` | OpenAI vectorization |
| Store | `store.py` | ChromaDB persistent vector index |
| Generate | `llm.py` | OpenAI primary → Groq fallback |
| Guard | `prompts.py`, `query.py` | Cite-or-refuse contract |

---

## Quick Start

### Prerequisites

| Requirement | Notes |
| :--- | :--- |
| [uv](https://docs.astral.sh/uv/) | Package manager; install via `pip install uv` |
| Python 3.12 | Downloaded automatically by uv |
| OpenAI API key | Required for embeddings and primary LLM |
| Groq API key | Recommended fallback for LLM generation |

### Install

```powershell
git clone https://github.com/Galina-Blokh/hr-policy-automation-proposal.git
cd hr-policy-automation-proposal
git checkout prototype/guardrailed-knowledge-rag

python -m uv venv .venv --python 3.12
python -m uv pip install -e . --python .venv\Scripts\python.exe

copy .env.example .env
# Edit .env with your OPENAI_API_KEY and GROQ_API_KEY
```

### First run

```powershell
# 1. Ingest PDFs from data/
.venv\Scripts\python.exe -m src.ingest --source data

# 2. Ask a question
.venv\Scripts\python.exe -m src.query "What is the company policy on remote work?" --pretty

# 3. Run evaluation
.venv\Scripts\python.exe -m src.eval
```

---

## Usage

### Ingest documents

```powershell
.venv\Scripts\python.exe -m src.ingest --source data
```

| Flag | Description |
| :--- | :--- |
| `--source PATH` | PDF file or directory (default: `DATA_DIR`) |
| `--no-reset` | Append to existing store instead of replacing |

**Current corpus:** 3 PDFs → 144 pages → 187 chunks.

### Query

```powershell
.venv\Scripts\python.exe -m src.query "When does vacation accrual start?" --pretty
```

| Flag | Description |
| :--- | :--- |
| `--pretty` | Human-readable indented JSON output |

### Evaluate

```powershell
.venv\Scripts\python.exe -m src.eval
.venv\Scripts\python.exe -m src.eval --file tests/golden_qa.json
```

---

## Configuration

All settings are loaded from `.env`. See [.env.example](./.env.example) for the full list.

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | — | Embeddings + primary LLM (**required**) |
| `GROQ_API_KEY` | — | Fallback LLM when OpenAI fails |
| `REFUSAL_THRESHOLD` | `0.40` | Min similarity score to attempt an answer |
| `TOP_K` | `5` | Chunks retrieved per query |
| `CHUNK_SIZE` | `500` | Tokens per chunk during ingestion |
| `HR_CONTACT_EMAIL` | `hr@company.com` | Shown in refusal messages |

---

## Response Format

Every query returns JSON with the following schema:

```json
{
  "question": "string",
  "status": "answered | refused",
  "answer": "string",
  "citations": [
    {
      "doc_id": "string",
      "title": "string",
      "section": "string",
      "chunk_id": "string",
      "page_number": 23
    }
  ],
  "retrieval_score": 0.635,
  "provider": "openai | groq | null",
  "reason": "personalized_question | low_retrieval_score | model_refusal | null"
}
```

| `reason` value | Meaning |
| :--- | :--- |
| `personalized_question` | Blocked before retrieval (Layer 1) |
| `low_retrieval_score` | No sufficiently similar chunks (Layer 2) |
| `model_refusal` | LLM determined context was insufficient (Layer 3) |
| `null` | Question was answered successfully |

---

## Project Structure

```
censor-app/
├── plan.md                 # Full proposal (3 strategic options)
├── spec.md                 # Technical specification
├── README.md               # This file
├── pyproject.toml          # uv / Python 3.12 dependencies
├── .env.example            # Environment template (never commit .env)
├── data/
│   ├── *.pdf               # Source HR policy documents
│   └── chroma/             # Generated vector store (gitignored)
├── src/
│   ├── config.py           # Settings from environment
│   ├── documents.py        # PDF loading
│   ├── chunker.py          # Token-based chunking
│   ├── embeddings.py       # OpenAI embeddings
│   ├── store.py            # ChromaDB wrapper
│   ├── llm.py              # OpenAI → Groq fallback
│   ├── prompts.py          # Guardrail prompt templates
│   ├── ingest.py           # Offline ingestion CLI
│   ├── query.py            # Online query CLI
│   └── eval.py             # Golden Q&A evaluation
└── tests/
    └── golden_qa.json      # Expected answer/refusal cases
```

---

## Guardrail Model

Three independent layers prevent unsafe answers:

| Layer | Where | Trigger | Action |
| :--- | :--- | :--- | :--- |
| **1. Pre-filter** | `query.py` | Personalized question patterns | Refuse immediately |
| **2. Retrieval gate** | `query.py` | Similarity < `REFUSAL_THRESHOLD` | Refuse without LLM call |
| **3. LLM contract** | `prompts.py` | Context insufficient | Model returns refusal text |

Refusal message (configurable via `HR_CONTACT_EMAIL`):

```
I cannot verify this from the current HR policy documents.
Please contact hr@company.com for assistance.
```

---

## Evaluation

Golden Q&A set at `tests/golden_qa.json` validates:

- Policy questions receive **answered** responses with citations
- Personalized / out-of-scope questions receive **refused** responses
- No fabricated policy text on refusal cases

**Current MVP result:** 6/8 passed (75%) on the starter eval set.

---

## Design Decisions

### Why ChromaDB?

Chosen for zero-infrastructure local persistence during MVP. The vector store is isolated in `src/store.py` and can be swapped for pgvector in production without changing ingest/query logic. See [spec.md §14](./spec.md#14-vector-store-decision).

### Why OpenAI + Groq?

| Capability | Provider | Rationale |
| :--- | :--- | :--- |
| Embeddings | OpenAI only | Groq has no embedding API |
| Generation | OpenAI → Groq | Primary quality; fallback resilience |

### Why no UI?

CLI-first MVP keeps engineering focus on accuracy and guardrails. A FastAPI or Streamlit layer is Phase 4 in the spec.

---

## Scope Boundaries

Deliberately **not** included in this MVP:

| Excluded | Reason |
| :--- | :--- |
| Multi-turn conversation memory | Single-turn Q&A sufficient for policy lookups |
| HRIS write-back | Read-only Q&A; no Workday/ADP mutations |
| Custom web UI | CLI proves core value; UI is a follow-up |
| Production auth / SSO | Local prototype only |

---

## Troubleshooting

| Issue | Solution |
| :--- | :--- |
| `Vector store is empty` | Run `python -m src.ingest --source data` first |
| `OPENAI_API_KEY is required` | Add key to `.env` and restart |
| All queries refused | Lower `REFUSAL_THRESHOLD` (e.g. `0.35`); re-ingest |
| OpenAI fails but Groq works | Check logs; Groq fallback activates automatically |
| Poor answer quality | Increase `TOP_K`; verify PDF text extraction quality |

---

## Branches

| Branch | Description |
| :--- | :--- |
| `main` | Proposal document only |
| **`prototype/guardrailed-knowledge-rag`** | This RAG prototype |
| `prototype/intent-driven-agentic-router` | Option 1 — intent router + HRIS |

---

## License & Context

Internal evaluation prototype for the HR policy automation exercise. See [plan.md](./plan.md) for the full stakeholder proposal and decision framework.
