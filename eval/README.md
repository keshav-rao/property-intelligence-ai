# Evaluation

`run_eval.py` replays short conversations from `test_cases.json` against a running API and checks the last reply.

```bash
python eval/run_eval.py                      # local API on :8000
python eval/run_eval.py https://chat.example.com
```

| Check | What it verifies |
|---|---|
| intent / platform | The message was understood and routed to DarGlobal or Wasalt correctly |
| results | Enough matches, all within budget and in the requested city, expected projects present |
| links | The right official page is offered (live Wasalt search, auctions, DarGlobal project page) |
| UI blocks | Comparison table or enquiry form appears when it should |
| answer must contain | Grounded facts, e.g. "Doha" for Les Vagues |
| answer must NOT contain | Invented prices for DarGlobal, echoed contact details, invented people |

Categories: guided search, one-shot search, rentals, change of mind, DarGlobal by brand and by country, project questions,
price honesty, comparison, navigation, knowledge, lead capture, privacy and out-of-scope questions.

Results are written to `evaluation_results.json` (summary + per-case answers and latency). The fast, LLM-free behaviour tests
live in `backend/tests/` (`python -m pytest -q`).
