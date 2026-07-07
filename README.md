# HR Policy Automation — Home Assignment

Proposal and prototypes for automating repetitive HR policy questions from new hires.

**Primary deliverable:** [plan.md](./plan.md) — decision framework, discovery questions, build-vs-buy analysis, and MVP scope.

---

## Repository branches

This repo separates **thinking** (proposal on `main`) from **implementation** (prototypes on feature branches).

| Branch | Status | What it contains |
| :--- | :--- | :--- |
| **`main`** | Proposal only | `plan.md` — how to approach the vague HR automation request |
| [`prototype/guardrailed-knowledge-rag`](https://github.com/Galina-Blokh/hr-policy-automation-proposal/tree/prototype/guardrailed-knowledge-rag) | **Working MVP** | Option 2 — cite-or-refuse RAG prototype |
| [`prototype/intent-driven-agentic-router`](https://github.com/Galina-Blokh/hr-policy-automation-proposal/tree/prototype/intent-driven-agentic-router) | Planned | Option 1 — intent router + HRIS routing (not yet implemented) |

---

## Prototype: `prototype/guardrailed-knowledge-rag`

Implements **Option 2 (Guardrailed Knowledge RAG)** from the proposal — the recommended starting point when HR has PDF handbooks and questions are mostly static policy text.

### What it demonstrates

- **Cite-or-refuse guardrails** — answers only from ingested policy documents, or refuses with an HR contact message
- **3-layer safety model** — personalized-question pre-filter → retrieval score gate → LLM prompt contract
- **Real PDF ingestion** — 3 sample HR handbooks chunked and indexed in ChromaDB
- **Working demo** — Streamlit web UI + CLI query interface

### What's in the branch

| Component | Description |
| :--- | :--- |
| `src/ingest.py` | PDF → chunks → OpenAI embeddings → ChromaDB |
| `src/query.py` | Retrieve → generate → cite-or-refuse response |
| `src/ui.py` | Streamlit chat UI (input at top, history below) |
| `src/eval.py` | Golden Q&A evaluation runner |
| `data/*.pdf` | Sample HR policy documents |
| `spec.md` | Technical specification |
| `README.md` | Setup and usage guide |

### Quick start (on that branch)

```powershell
git checkout prototype/guardrailed-knowledge-rag
python -m uv venv .venv --python 3.12
python -m uv pip install -e . --python .venv\Scripts\python.exe
copy .env.example .env   # add OPENAI_API_KEY and GROQ_API_KEY

.venv\Scripts\python.exe -m src.ingest --source data
.venv\Scripts\hr-ui
```

### Why Option 2 was prototyped first

Per the proposal's default recommendation: PDF handbooks were available, personalized HRIS access was not required for the MVP, and cite-or-refuse RAG is the lowest-risk way to prove value on static policy before building Option 1 or evaluating Option 3.

---

## Assignment mapping

| Deliverable | Location |
| :--- | :--- |
| Proposal (questions, build-vs-buy, MVP, metrics, risks) | `plan.md` on `main` |
| "What I deliberately did not build" | `plan.md` §7 |
| Working prototype (bonus) | `prototype/guardrailed-knowledge-rag` branch |
