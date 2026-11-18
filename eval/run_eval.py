"""Automated evaluation and benchmarking suite for Property Intelligence AI.

Evaluates test cases against:
- Retrieval Accuracy
- Answer Correctness & Keyword Grounding
- Source Attribution Rate
- Hallucination Avoidance (Unknown question handling)
- Latency (ms)

Run:
  python -m eval.run_eval
"""
from __future__ import annotations

import json
import time
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_CASES_FILE = REPO_ROOT / "eval" / "test_cases.json"
RESULTS_FILE = REPO_ROOT / "eval" / "evaluation_results.json"


def evaluate_suite() -> dict:
    with open(TEST_CASES_FILE, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    print("=" * 75, flush=True)
    print("PROPERTY INTELLIGENCE AI - AUTOMATED EVALUATION SUITE", flush=True)
    print(f"Total Test Cases: {len(test_cases)}", flush=True)
    print("=" * 75, flush=True)

    client = TestClient(app)
    results = []

    retrieval_hits = 0
    correctness_hits = 0
    grounding_hits = 0
    attribution_hits = 0
    latencies = []

    for idx, tc in enumerate(test_cases, 1):
        q = tc["question"]
        cat = tc["category"]
        expected_kw = tc.get("expected_keywords", [])
        is_negative = cat == "hallucination_prevention"

        print(f"\n[{idx:02d}/{len(test_cases)}] Category: {cat}", flush=True)
        print(f"Question: {q}", flush=True)

        t0 = time.time()
        try:
            resp = client.post("/api/chat", json={"message": q})
            latency = round(time.time() - t0, 2)
            latencies.append(latency)

            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])
                properties = data.get("properties", [])

                # 1. Retrieval check
                if not is_negative:
                    retrieval_ok = len(sources) > 0 or len(properties) > 0
                else:
                    retrieval_ok = True

                if retrieval_ok:
                    retrieval_hits += 1

                # 2. Correctness & Grounding
                a_lower = answer.lower()
                matched_kw = [kw for kw in expected_kw if kw.lower() in a_lower]

                if is_negative:
                    # In negative tests, answer must indicate unknown / not present
                    neg_indicators = ["not available", "not present", "not found", "no information", "does not have", "no record", "none", "not listed"]
                    passed_neg = any(ni in a_lower for ni in neg_indicators)
                    if passed_neg:
                        grounding_hits += 1
                        correctness_ok = True
                    else:
                        correctness_ok = False
                else:
                    correctness_ok = len(matched_kw) >= 1
                    if correctness_ok:
                        correctness_hits += 1

                # 3. Source attribution check
                if tc.get("should_have_sources"):
                    has_sources = len(sources) > 0
                    if has_sources:
                        attribution_hits += 1
                else:
                    has_sources = True

                status_label = "PASS" if correctness_ok and retrieval_ok else "PARTIAL"
                print(f"Status: {status_label} | Latency: {latency}s | Matched KW: {matched_kw} | Sources: {len(sources)}", flush=True)
                clean_ans = answer[:160].replace('\n', ' ')
                print(f"Answer snippet: {clean_ans}...", flush=True)

                results.append({
                    "id": tc["id"],
                    "category": cat,
                    "question": q,
                    "latency_sec": latency,
                    "status": status_label,
                    "retrieval_ok": retrieval_ok,
                    "correctness_ok": correctness_ok,
                    "sources_count": len(sources),
                    "matched_keywords": matched_kw,
                    "answer_preview": answer[:250]
                })

            else:
                print(f"Status: FAIL (HTTP {resp.status_code})", flush=True)
                results.append({
                    "id": tc["id"],
                    "category": cat,
                    "question": q,
                    "status": "FAIL_HTTP",
                    "error": resp.text[:200]
                })

        except Exception as e:
            print(f"Status: ERROR ({e})", flush=True)
            results.append({
                "id": tc["id"],
                "category": cat,
                "question": q,
                "status": "ERROR",
                "error": str(e)
            })

    # Summary metrics
    n_positive = len([tc for tc in test_cases if tc.get("category") != "hallucination_prevention"])
    n_negative = len([tc for tc in test_cases if tc.get("category") == "hallucination_prevention"])

    retrieval_acc = round((retrieval_hits / len(test_cases)) * 100, 1)
    correctness_rate = round((correctness_hits / n_positive) * 100, 1) if n_positive else 100.0
    grounding_rate = round((grounding_hits / n_negative) * 100, 1) if n_negative else 100.0
    attribution_rate = round((attribution_hits / n_positive) * 100, 1) if n_positive else 100.0
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    summary = {
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_test_cases": len(test_cases),
        "retrieval_accuracy_percent": retrieval_acc,
        "answer_correctness_percent": correctness_rate,
        "hallucination_avoidance_percent": grounding_rate,
        "source_attribution_percent": attribution_rate,
        "average_latency_seconds": avg_latency,
        "detailed_results": results
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 75, flush=True)
    print("EVALUATION BENCHMARK SUMMARY", flush=True)
    print("=" * 75, flush=True)
    print(f"Total Test Cases:            {len(test_cases)}", flush=True)
    print(f"Retrieval Accuracy:          {retrieval_acc}%", flush=True)
    print(f"Answer Correctness:          {correctness_rate}%", flush=True)
    print(f"Hallucination Avoidance:     {grounding_rate}%", flush=True)
    print(f"Source Attribution Rate:     {attribution_rate}%", flush=True)
    print(f"Average Response Latency:    {avg_latency}s", flush=True)
    print(f"Results saved to:            {RESULTS_FILE}", flush=True)
    print("=" * 75, flush=True)

    return summary


if __name__ == "__main__":
    evaluate_suite()
