import json


def test_run_evaluation_creates_results(tmp_path):
    queries = [
        {"id": 1, "text": "hello world", "expected": "RESPONSE: hello world"},
    ]
    qfile = tmp_path / "queries.jsonl"
    with open(qfile, "w", encoding="utf-8") as f:
        for q in queries:
            f.write(json.dumps(q) + "\n")

    out = tmp_path / "results.json"

    # Import and run the runner
    from evaluation import run_evaluation

    rc = run_evaluation.main(["--queries", str(qfile), "--output", str(out)])
    assert rc == 0
    assert out.exists()

    data = json.load(open(out, "r", encoding="utf-8"))
    assert data["metrics"]["count"] == 1
    assert data["metrics"]["exact_match_rate"] == 1.0
