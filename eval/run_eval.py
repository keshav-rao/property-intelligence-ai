"""End-to-end evaluation against a running API.

    python eval/run_eval.py                      # http://127.0.0.1:8000
    python eval/run_eval.py https://chat.example.com

Each case is a short conversation. The last reply is checked for: intent, platform,
expected items, price limits, official links, UI blocks (comparison / enquiry form),
answer content, and things the answer must NOT contain (invented prices, echoed
contact details, invented facts). Results go to eval/evaluation_results.json.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
HERE = Path(__file__).parent


def run_case(client: httpx.Client, case: dict) -> dict:
    sid, rep, t0 = None, None, time.time()
    for turn in case["turns"]:
        r = client.post(f"{BASE}/api/chat", json={"message": turn, "session_id": sid})
        r.raise_for_status()
        rep = r.json()
        sid = rep["session_id"]
    latency = time.time() - t0
    e, fails = case["expect"], []
    answer = rep["answer"]
    recs = rep["recommendations"]
    if "intent" in e and rep["intent"].get("name") != e["intent"]:
        fails.append(f"intent {rep['intent'].get('name')} != {e['intent']}")
    if "platform" in e and rep["intent"].get("platform") != e["platform"]:
        fails.append(f"platform {rep['intent'].get('platform')} != {e['platform']}")
    if len(recs) < e.get("min_results", 0):
        fails.append(f"only {len(recs)} results")
    if "max_results" in e and len(recs) > e["max_results"]:
        fails.append(f"{len(recs)} results, expected at most {e['max_results']}")
    if "max_price" in e and any((c.get("price") or 0) > e["max_price"] for c in recs):
        fails.append("a result is over budget")
    if "city" in e and any(c["city"] != e["city"] for c in recs):
        fails.append("a result is in another city")
    for t in e.get("titles", []):
        if not any(t.lower() in c["title"].lower() for c in recs + (rep.get("ui") or {}).get("columns", [])):
            fails.append(f"missing {t}")
    if "action_url" in e and e["action_url"] not in [a["url"] for a in rep["actions"]]:
        fails.append(f"missing link {e['action_url']}")
    if "ui" in e and (rep.get("ui") or {}).get("type") != e["ui"]:
        fails.append(f"ui {(rep.get('ui') or {}).get('type')} != {e['ui']}")
    for k, v in e.get("filters", {}).items():
        if rep["filters"].get(k) != v:
            fails.append(f"filter {k}={rep['filters'].get(k)} != {v}")
    for w in e.get("answer_has", []):
        if w.lower() not in answer.lower():
            fails.append(f"answer lacks '{w}'")
    if "answer_has_any" in e and not any(w.lower() in answer.lower() for w in e["answer_has_any"]):
        fails.append(f"answer has none of {e['answer_has_any']}")
    if "answer_lacks_regex" in e and re.search(e["answer_lacks_regex"], answer):
        fails.append(f"answer matches forbidden pattern {e['answer_lacks_regex']}")
    return {"id": case["id"], "category": case["category"], "passed": not fails, "failures": fails,
            "latency_s": round(latency, 2), "turns": len(case["turns"]), "llm": rep.get("llm"),
            "has_sources_or_links": bool(rep["sources"] or rep["actions"]), "answer": answer[:400]}


def main() -> None:
    cases = json.loads((HERE / "test_cases.json").read_text(encoding="utf-8"))
    out = []
    with httpx.Client(timeout=90) as client:
        for c in cases:
            res = run_case(client, c)
            out.append(res)
            mark = "PASS" if res["passed"] else "FAIL"
            print(f"{mark} {res['id']:<3} {res['category']:<22} {res['latency_s']:>5.1f}s  {'; '.join(res['failures'])}")
    n = len(out)
    passed = sum(r["passed"] for r in out)
    llm_used = [r for r in out if r["llm"]]
    summary = {
        "base_url": BASE,
        "cases": n,
        "passed": passed,
        "pass_rate": round(passed / n, 3),
        "answers_written_by_llm": len(llm_used),
        "with_sources_or_links": sum(r["has_sources_or_links"] for r in out),
        "avg_latency_per_conversation_s": round(sum(r["latency_s"] for r in out) / n, 2),
        "avg_latency_per_turn_s": round(sum(r["latency_s"] for r in out) / sum(r["turns"] for r in out), 2),
    }
    (HERE / "evaluation_results.json").write_text(json.dumps({"summary": summary, "results": out}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
