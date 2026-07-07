# HR Policy Automation — Guardrailed Knowledge RAG

A working prototype for **Option 2** from the [project proposal](./plan.md): answer repetitive HR policy questions from verified handbook PDFs, with a hard **cite-or-refuse** guardrail to prevent hallucinated policy answers.

**Branch:** `prototype/guardrailed-knowledge-rag`

---

## The Problem

HR teams spend hours each week answering the same policy questions from new hires — vacation accrual rules, expense limits, benefits enrollment deadlines. The stakeholder asked to "automate this somehow."

The real need is not a chatbot that *sounds* helpful. It is a system that **deflects repetitive questions safely** — one that never invents a benefits deadline or misstates an expense rule.

---

## Why This Approach?

| When RAG is the right fit | When it is not |
| :--- | :--- |
| Questions are mostly **static policy text** | Employees ask "how many PTO days do **I** have?" (needs HRIS — see Option 1) |
| HR already has **PDF handbooks** | Policies are scattered or undocumented |
| **Privacy** requires docs stay in your cloud | You need a solution live in Slack within 1 week (see Option 3) |

**Build vs. buy:** Custom build (Python + ChromaDB in private cloud). Documents are ingested locally; only embeddings and LLM calls use external APIs.

---

## How It Works

```
 PDFs in data/
         │
         ▼
    ┌─────────┐
    │ Ingest  │  chunk → embed (OpenAI) → ChromaDB
    └─────────┘
         │
         ▼
    ┌─────────┐     User question
    │ Retrieve│ ◄──────────────────
    └─────────┘
         │ top-K chunks (cosine similarity)
         ▼
    ┌─────────┐
    │   LLM   │  OpenAI primary → Groq fallback
    └─────────┘
         │
    ┌────┴────┐
    ▼         ▼
 Answer    Refuse
 + cites   "Contact hr@company.com"
```

### Guardrails

1. **Personalized questions** (e.g. "my PTO balance") → refused before retrieval.
2. **Low retrieval score** → refused without calling the LLM.
3. **LLM prompt** → answer only from context, or refuse explicitly.
4. **Every answer** includes source document citations.

---

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (installed via `pip install uv` if needed)
- Python 3.12 (uv downloads it automatically)
- API keys in `.env`:
  - `OPENAI_API_KEY` — required for embeddings and primary LLM
  - `GROQ_API_KEY` — fallback LLM if OpenAI fails

### Install

```powershell
git checkout prototype/guardrailed-knowledge-rag
python -m uv venv .venv --python 3.12
python -m uv pip install -e . --python .venv\Scripts\python.exe
copy .env.example .env   # add your API keys
```

### Ingest policy PDFs

Place PDF files in `data/`, then run:

```powershell
.venv\Scripts\python.exe -m src.ingest --source data
```

Current corpus (3 documents, 187 chunks):

- `Employee-Handbook.pdf`
- `Kenya-Revised-Policy-Manual-2023-11th-draft-PO-edits-Final.pdf`
- `Small_Business_Administration_Employee_polich_Template.pdf`

### Ask a question

```powershell
.venv\Scripts\python.exe -m src.query "What is the company policy on remote work?" --pretty
```

Example response:

```json
{
  "status": "answered",
  "answer": "Remote working refers to working from a non-office location...",
  "citations": [
    { "doc_id": "employee-handbook", "section": "Employee Handbook — page 23", "page_number": 23 }
  ],
  "retrieval_score": 0.635,
  "provider": "openai"
}
```

Refusal example:

```powershell
.venv\Scripts\python.exe -m src.query "How many vacation days do I have left?" --pretty
```

### Run evaluation

```powershell
.venv\Scripts\python.exe -m src.eval
```

Golden Q&A set: `tests/golden_qa.json`

---

## Project Layout

| Path | Purpose |
| :--- | :--- |
| [plan.md](./plan.md) | Full proposal — all 3 options |
| [spec.md](./spec.md) | Technical specification |
| `data/*.pdf` | HR policy source documents |
| `data/chroma/` | Local vector store (generated, gitignored) |
| `src/ingest.py` | PDF → chunks → embeddings → ChromaDB |
| `src/query.py` | Retrieve → LLM → cite-or-refuse response |
| `src/llm.py` | OpenAI primary, Groq fallback |
| `tests/golden_qa.json` | Eval set for answer/refusal behavior |

---

## LLM Fallback Strategy

| Step | Provider | Notes |
| :--- | :--- | :--- |
| Embeddings | **OpenAI only** | `text-embedding-3-small` |
| Generation | **OpenAI** → **Groq** | Tries `gpt-4o-mini` first; falls back to `llama-3.3-70b-versatile` on failure |

Configure models in `.env` — see [.env.example](./.env.example).

---

## What We Deliberately Did Not Build

- **Multi-turn memory** — single-turn Q&A only
- **HRIS write-back** — read-only Q&A, no Workday/ADP mutations
- **Custom web UI** — CLI only; Slack/Teams integration is a follow-up

---

## Success Metrics

| Metric | MVP result |
| :--- | :--- |
| Citation rate (answered queries) | 100% include sources |
| Refusal on personalized questions | 100% |
| Golden Q&A pass rate | 75% on starter set (6/8) |

See [spec.md](./spec.md) for full acceptance criteria.

---

## Branches

| Branch | Approach |
| :--- | :--- |
| `main` | Proposal document |
| **`prototype/guardrailed-knowledge-rag`** *(current)* | This RAG prototype |
| `prototype/intent-driven-agentic-router` | Intent router + HRIS (Option 1) |

For the full decision framework, see [plan.md](./plan.md).
