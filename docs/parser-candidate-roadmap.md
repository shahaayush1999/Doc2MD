# Parser candidate roadmap

This is a planning and implementation note, not part of the official benchmark contract. The PDF corpus and scoring remain one general-purpose PDF-to-Markdown benchmark.

The initial local/generic-provider candidates have passed a ten-page mixed-PDF POC, are integrated into the shared runner, and have completed the five-case sample benchmark. Reducto Standard and Agentic have also completed the sample benchmark.

The current hosted batch is limited to products with a real free mode and no prepaid-credit requirement. Mistral OCR 4, LlamaParse Agentic, Firecrawl hosted `auto`, LandingAI ADE DPT-2, Upstage Document Parse Auto, Nanonets DocStrange, and Unstructured VLM are registered in the runner. Nanonets required the separate DocStrange extraction key rather than its legacy workspace-admin key. Unstructured required the active Personal Workspace key rather than the initially supplied inactive key. Google Document AI, AWS Textract, and Azure are not in this batch: Google relies on introductory cloud credits, AWS's allowance is temporary for new accounts, and Azure F0 only processes the first two pages of each PDF.

## POC results

POCs used the ten-page mixed-modality Task 2 case on the development M4 Pro Mac. Times are directional local observations, not production hardware claims. Hosted/model calls used unpaid, data-sharing access rather than paid dedicated capacity, so their timings also include provider-tier scheduling and instability and must not be treated as paid-production forecasts.

| Candidate | POC result | Approximate conversion time |
| --- | --- | ---: |
| `pdftotext` | Passed; 14,505-byte output | 0.02 s |
| `firecrawl-pdf-inspector` | Passed; 5,620-byte output | 0.04 s |
| `markitdown-base` | Passed; 8,151-byte output | 11.1 s |
| `markitdown-ocr-gpt-5.6-luna` | Passed; six successful vision calls with recorded usage | 43.8-56.3 s |
| `pymupdf4llm-default` | Passed; 7,149-byte integrated output | 1.9-2.0 s |
| `docling-standard-cpu` | Passed; 5,785-byte placeholder-image Markdown | 33.4 s warm; 86.4 s cold |
| `marker-fast-cpu` | Passed with the documented `llama.cpp` dependency | 106.7-131.1 s cold |
| `openai-gpt-5.6-luna` | Already registered and scored as the direct multimodal reference | Existing result |
| `landingai-dpt2` | Passed; 19,975-byte Markdown output with 79 chunks | 84.6 s |
| `upstage-auto` | Passed; 34,943-byte Markdown output; 2 Standard and 8 Enhanced pages | 45.6 s |
| `nanonets-docstrange` | Passed through the async endpoint; 13,830-byte Markdown output | 40.5 s provider processing |
| `unstructured-vlm-gpt4o` | Passed; 80 ordered elements across 10 pages, including 11 image elements and 7 structured HTML tables | 28.1 s |

## Five-case sample results

Conversion time excludes the common evaluator. Cost is published production conversion-API cost without free-tier discounts.

| Candidate | Score | Conversion time | Conversion cost |
| --- | ---: | ---: | ---: |
| `llamaparse-agentic` | 77.31 | 226.600 s | $1.032 |
| `reducto-agentic` | 76.12 | 314.056 s | $3.99 |
| `nanonets-docstrange` | 75.16 | 324.702 s | $0.86 |
| `reducto-standard` | 70.95 | 70.816 s | $1.995 |
| `mistral-ocr-4` | 66.97 | 22.411 s | $0.344 |
| `unstructured-vlm-gpt4o` | 64.16 | 266.316 s | $2.58 |
| `marker-fast-cpu` | 59.35 | 509.748 s | $0 |
| `upstage-auto` | 59.20 | 159.552 s | $2.36 |
| `landingai-dpt2` | 57.87 | 250.612 s | $2.58 |
| `docling-standard-cpu` | 57.00 | 356.775 s | $0 |
| `markitdown-ocr-gpt-5.6-luna` | 53.58 | 427.770 s | $0.064316 |
| `firecrawl-hosted-auto` | 42.97 | 33.324 s | $0.2752 |
| `pymupdf4llm-default` | 4.27 | 3.639 s | $0 |
| `markitdown-base` | 3.99 | 3.870 s | $0 |
| `firecrawl-pdf-inspector` | 3.10 | 0.069 s | $0 |
| `pdftotext` | 3.15 | 0.242 s | $0 |

LlamaParse Agentic is the strongest parser-only service tested so far at 77.31, narrowly ahead of Reducto Agentic and Nanonets DocStrange. Mistral OCR 4 is the speed/cost standout among hosted parsers at 66.97 in 22.4 seconds and $0.344 list cost. Unstructured VLM scored 64.16: it was excellent on the long mixed clinical packet (92.01) but lost substantial structured rows and diagram bindings in Task 2 and Task 5. Marker is the strongest zero-API-cost local parser at 59.35, though its CPU conversion took 509.7 seconds on the test laptop. The direct `openai-gpt-5.6-luna` multimodal reference remains substantially higher at 88.99 while also costing less than every hosted parser API tested. The text-focused tools remain below five points because most benchmark credit requires reconstruction of raster, layout, table, form, or diagram evidence.

### Manual review corrections — 2026-08-05

Manual review found that stale and incomplete page maps, rather than candidate quality, caused several false-low scores. Mistral OCR 4 had substantial output but its older cached judgments treated printed page counters incorrectly; regrading its saved Markdown changed the overall score from 9.63 to 66.97 without repeating conversion. LlamaParse Task 5 changed from 28.00 to 52.49 after a lone footer stopped hiding the unscoped document, raising its overall score from 72.47 to 77.31. Marker Task 5 changed from 11.33 to 17.88 for the same reason. A mixed header/footer placement check left Upstage Task 5 unchanged at 8.28, confirming that its low result is genuine output corruption. Finally, explicit numbered panel sequences and Reducto's literal `Field: Controlled value` schema were credited after direct source/output inspection; this moved Nanonets Task 1 and Reducto Agentic Task 1 to 100. No parser conversion was rerun for any correction.

## Scope decisions

- Admit only released, off-the-shelf tools, plugins, documented modes, and public configuration surfaces.
- Do not patch, fork, subclass, or build a custom OCR/LLM routing or merge pipeline.
- Local candidates must run practically on a laptop or ordinary CPU VM/container. Do not run GPU-oriented models on CPU merely to make them eligible.
- Managed APIs and ordinary LLM-provider integrations are eligible. Synthetic benchmark PDFs may be sent to them.
- Treat every documented configuration as a separately named candidate.
- Do not expand the five-case sample set or create a separate parser benchmark yet.

## Initial local and generic-provider candidates

1. `pdftotext` — canonical, widely used native-text floor.
2. `firecrawl-pdf-inspector` — released Rust structured-text parser; no custom vision fallback.
3. `markitdown-base` — released local PDF-to-Markdown mode.
4. `markitdown-ocr-gpt-5.6-luna` — official OCR plugin, public `llm_client`, `llm_model`, and `llm_prompt` configuration only.
5. `pymupdf4llm-default` — released default Markdown converter, including its documented automatic OCR behavior.
6. `docling-standard-cpu` — released standard CPU pipeline, subject to a practical one-case runtime check.
7. `marker-fast-cpu` — released CPU mode, subject to a practical one-case runtime check.
8. `openai-gpt-5.6-luna` — existing direct multimodal reference already registered and scored by the benchmark.

If Docling or Marker is plainly impractical on the available laptop, record the feasibility result and omit the full-suite run rather than waiting through an artificial CPU inference workload.

## Black-box reporting

Record only:

- final benchmark score;
- end-to-end conversion wall time for the complete suite, from source input to saved Markdown predictions;
- published production conversion-API cost for the complete suite, ignoring free-tier discounts and promotional credits.

Exclude evaluator time and evaluator cost: those measure the common grading system rather than the candidate converter. For local software, report conversion-API cost as zero and identify the test machine next to the timing. Do not estimate cloud-equivalent compute cost. Do not add API-call count, peak RAM/VRAM, package size, or deployment-class metrics unless a concrete diagnostic need emerges.

## Deferred hosted-API evaluation

After the initial local/generic-provider pass, investigate and selectively test the most relevant ready-to-use hosted services. Prioritize a free trial/tier or a clearly category-leading product:

- Mistral OCR;
- LlamaParse;
- Azure AI Document Intelligence and Azure Content Understanding;
- Google Document AI;
- AWS Textract;
- Firecrawl's hosted PDF `auto` / `ocr` modes.

Before adding one, verify current pricing, trial allowance, Markdown output support, diagram/chart understanding, and whether the API is a meaningful category leader rather than a redundant OCR service.
