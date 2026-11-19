import csv
import json

with open("evaluation/results/evaluation_results.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if int(row["score"]) < 3:
            print(f"[{row['test_id']}] Category: {row['category']} | Score: {row['score']}/4")
            print(f"  Input: {row['user_input']}")
            print(f"  Routing Pass: {row['routing_pass']} | Actual Platform: {row['actual_platform']}")
            print(f"  Filter Pass: {row['filter_pass']}")
            print(f"  Answer: {row['answer_snippet'][:120]}")
            print("-" * 50)
