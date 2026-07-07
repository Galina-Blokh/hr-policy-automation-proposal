"""Golden Q&A evaluation runner for regression testing.

Compares actual query pipeline behavior against expected outcomes defined in
`tests/golden_qa.json`. Use after prompt, threshold, or ingestion changes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.query import QueryResponse, answer_question


def run_eval(path: Path) -> dict:
    """Execute all golden Q&A cases and compute pass rate.

    Parameters
    ----------
    path:
        JSON file containing a list of `{question, expected_status}` objects.

    Returns
    -------
    dict
        Summary with total, passed, pass_rate, and per-question results.
    """
    cases = json.loads(path.read_text(encoding="utf-8"))
    results: list[dict] = []
    passed = 0

    for case in cases:
        question = case["question"]
        expected = case["expected_status"]
        response: QueryResponse = answer_question(question)
        ok = response.status == expected
        if ok:
            passed += 1
        results.append(
            {
                "question": question,
                "expected_status": expected,
                "actual_status": response.status,
                "pass": ok,
                "retrieval_score": response.retrieval_score,
                "provider": response.provider,
                "reason": response.reason,
            }
        )

    total = len(cases)
    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "results": results,
    }


def main() -> None:
    """CLI entry point for the golden evaluation set."""
    parser = argparse.ArgumentParser(description="Run golden Q&A evaluation set.")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("tests/golden_qa.json"),
        help="Path to golden Q&A JSON file.",
    )
    args = parser.parse_args()

    summary = run_eval(args.file)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
