# Golden Q&A Evaluation Set

Regression tests for the cite-or-refuse query pipeline.

## Format

Each entry in `golden_qa.json` is an object:

```json
{
  "question": "Natural-language HR policy question",
  "expected_status": "answered | refused"
}
```

## Expected behavior

| `expected_status` | Meaning |
| :--- | :--- |
| `answered` | Policy text exists in ingested PDFs; response must include citations |
| `refused` | Question is personalized, out-of-scope, or not covered by source documents |

## Run

```powershell
.venv\Scripts\python.exe -m src.eval
```

## Interpreting failures

| Symptom | Likely cause |
| :--- | :--- |
| Expected `answered`, got `refused` with `low_retrieval_score` | Tune `REFUSAL_THRESHOLD` or improve chunking |
| Expected `answered`, got `refused` with `model_refusal` | Retrieved context insufficient; adjust prompt or `TOP_K` |
| Expected `refused`, got `answered` | Add pre-filter pattern or tighten prompt |

Update this file when adding new policy domains or changing guardrail behavior.
