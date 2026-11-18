# Property Intelligence AI — Evaluation & Benchmark Suite

This directory contains the automated evaluation framework used to evaluate retrieval accuracy, answer correctness, hallucination resistance, and source attribution for the Property Intelligence AI assistant.

## Benchmark Design

The evaluation suite comprises **25 rigorous test cases** across diverse categories:

| Category | Description | Primary Goal |
|---|---|---|
| `darglobal_riyadh` | Luxury villa projects in Riyadh | Grounded retrieval of Neptune, Mouawad, Trump Mansions |
| `darglobal_dubai` | Branded residences in Business Bay & Dubai Canal | Brand partnerships (Pagani, Missoni, W Hotels) |
| `darglobal_partners` | Luxury designer and automotive partnerships | Identifying co-branding (Lamborghini, Pagani, Aston Martin) |
| `darglobal_spain` | European coastal developments in Costa del Sol | Tierra Viva villas & Benahavís details |
| `darglobal_oman` | AIDA cliffside master community in Muscat | Trump Golf, Marriott Residences, Fendi Casa |
| `corporate_profile` | LSE listing (LSE: DAR), CEO (Ziad El Chaar), parent company | Corporate accuracy |
| `golden_visa` | Freehold ownership and residency qualification | Policy accuracy across UAE, Spain, Oman |
| `wasalt_riyadh` | Riyadh residential marketplace listings | Filtering and price reporting |
| `wasalt_jeddah` | Jeddah rental listings and Al Nuzha district | District and rental pricing intelligence |
| `platform_comparison` | Comparing DarGlobal vs Wasalt | Architectural distinction (Developer vs Marketplace) |
| `pricing_intelligence` | Comparing numerical property prices across markets | Accuracy in currency (SAR vs AED vs EUR) and figures |
| `hallucination_prevention` | Adversarial / ungrounded queries (Mars, Antarctica, Tesla) | Strict negative testing: verifying the model admits absence |

## Evaluation Metrics

1. **Retrieval Accuracy (%)**: Verifies that the hybrid retriever returns relevant documents and property payloads for legitimate domain questions.
2. **Answer Correctness (%)**: Checks that the generated completion contains expected factual entities and answers the user's intent.
3. **Hallucination Avoidance (%)**: Evaluates whether the system declines to hallucinate details for non-existent entities (e.g., properties on Mars, Antarctica listings, fake partnerships).
4. **Source Attribution Rate (%)**: Ensures answers are accompanied by verified source URLs and platforms (`darglobal.co.uk`, `wasalt.sa`).
5. **Response Latency (s)**: Tracks end-to-end execution time including embedding computation, vector search, and OpenRouter inference.

## Running the Benchmark

```bash
# From repository root:
python -m eval.run_eval
```

Results are logged in real-time and persisted as structured JSON to `eval/evaluation_results.json`.
