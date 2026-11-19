"""
Multi-turn Conversation Evaluation Module for Property Intelligence AI.
Evaluates context memory, filter persistence, requirement accumulation,
and change-of-mind filter overrides across sequential turns.
"""
from typing import Dict, Any, List
import time
# pyrefly: ignore[missing-import]
import httpx

def run_scenario(scenario: Dict[str, Any], base_url: str = "http://localhost:3000", client: httpx.Client = None) -> Dict[str, Any]:
    """
    Execute a single multi-turn scenario sequentially with a persistent session_id.
    """
    close_client = False
    if client is None:
        client = httpx.Client(base_url=base_url, timeout=35.0)
        close_client = True

    scenario_id = scenario.get("scenario_id", "SCENARIO")
    title = scenario.get("title", "")
    turns = scenario.get("turns", [])
    
    session_id = None
    turn_results = []
    scenario_passed = True
    total_latency_ms = 0

    try:
        for turn in turns:
            turn_idx = turn.get("turn_index", 1)
            user_input = turn.get("user_input", "")
            exp_filters = turn.get("expected_filters", {})
            exp_behavior = turn.get("expected_behavior", [])

            t0 = time.perf_counter()
            payload = {"message": user_input}
            if session_id:
                payload["session_id"] = session_id

            response = client.post("/api/chat", json=payload)
            turn_latency_ms = int((time.perf_counter() - t0) * 1000)
            total_latency_ms += turn_latency_ms

            if response.status_code != 200:
                turn_results.append({
                    "turn_index": turn_idx,
                    "user_input": user_input,
                    "status_code": response.status_code,
                    "passed": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}"
                })
                scenario_passed = False
                break

            data = response.json()
            session_id = data.get("session_id", session_id)
            actual_filters = data.get("filters", {})
            actual_answer = data.get("answer", "")
            recommendations = data.get("recommendations", [])

            # Verify filters
            filter_errors = []
            if exp_filters:
                for k, v in exp_filters.items():
                    act_v = actual_filters.get(k)
                    if act_v is None:
                        # Allow string/float flexibility
                        filter_errors.append(f"Missing filter {k}: expected {v}")
                    elif isinstance(v, (int, float)) and isinstance(act_v, (int, float)):
                        if float(act_v) != float(v):
                            filter_errors.append(f"Filter value mismatch on {k}: expected {v}, got {act_v}")
                    elif str(v).lower() != str(act_v).lower():
                        filter_errors.append(f"Filter value mismatch on {k}: expected {v}, got {act_v}")

            turn_pass = len(filter_errors) == 0
            if not turn_pass:
                scenario_passed = False

            turn_results.append({
                "turn_index": turn_idx,
                "user_input": user_input,
                "latency_ms": turn_latency_ms,
                "actual_filters": actual_filters,
                "expected_filters": exp_filters,
                "filter_pass": turn_pass,
                "filter_errors": filter_errors,
                "recommendation_count": len(recommendations),
                "answer_snippet": actual_answer[:150]
            })

    except Exception as e:
        scenario_passed = False
        turn_results.append({
            "error": str(e),
            "passed": False
        })
    finally:
        if close_client:
            client.close()

    avg_turn_latency_ms = round(total_latency_ms / len(turns), 2) if turns else 0

    return {
        "scenario_id": scenario_id,
        "title": title,
        "turns_count": len(turns),
        "passed": scenario_passed,
        "total_latency_ms": total_latency_ms,
        "avg_turn_latency_ms": avg_turn_latency_ms,
        "turn_results": turn_results
    }
