#!/usr/bin/env python3
"""Simple evaluation runner for DailyAccomplishments.

This lightweight harness loads a JSONL file of queries, optionally with
`expected` fields, produces simple synthetic responses (or runs a user
supplied evaluator), computes basic metrics (average length, exact-match),
and writes `results.json`.

Usage:
    python evaluation/run_evaluation.py --queries evaluation/sample_queries.jsonl --output evaluation/results.json

The script is intentionally framework-agnostic so you can plug in real
inference or agent calls where indicated.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Dict, Any, List


def load_queries(path: str) -> List[Dict[str, Any]]:
    queries = []
    if not os.path.exists(path):
        return queries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            queries.append(json.loads(line))
    return queries


def synthesize_response(query: Dict[str, Any]) -> str:
    # Placeholder: replace this with actual model/agent invocation
    text = query.get("text") or query.get("input") or ""
    return f"RESPONSE: {text}"


def evaluate(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = []
    total_len = 0
    exact_matches = 0

    for q in queries:
        response = synthesize_response(q)
        total_len += len(response)
        expected = q.get("expected")
        is_match = expected is not None and (response == expected)
        if is_match:
            exact_matches += 1
        results.append({"query": q, "response": response, "exact_match": is_match})

    metrics = {
        "count": len(queries),
        "avg_response_length": (total_len / len(queries)) if queries else 0,
        "exact_match_rate": (exact_matches / len(queries)) if queries else 0,
    }

    return {"metrics": metrics, "items": results}


def save_results(results: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", default="evaluation/sample_queries.jsonl")
    parser.add_argument("--output", default="evaluation/results.json")
    args = parser.parse_args(argv)

    queries = load_queries(args.queries)
    if not queries:
        # generate a few sample queries
        queries = [
            {"id": 1, "text": "Summarize today's accomplishments."},
            {"id": 2, "text": "List top domains visited today."},
        ]

    results = evaluate(queries)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    save_results(results, args.output)
    print(f"Wrote results to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
