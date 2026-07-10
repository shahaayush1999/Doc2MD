# Doc2MD

Doc2MD measures how faithfully an AI model reconstructs a PDF as one Markdown document. The target is exhaustive recovery of the document's information and reading experience: text, hierarchy, tables, forms, state changes, charts, diagrams, images, annotations, and spatial or directional relationships. It is not a summarization benchmark.

## Canonical benchmark

The official suite is manifest schema 2, version 0.2.0: **7 cases and 49 pages** under `benchmark/`. Each case contains:

```text
benchmark/cases/<case-id>/source.pdf
benchmark/cases/<case-id>/gold.md
benchmark/cases/<case-id>/facts.json
benchmark/cases/<case-id>/spec.md
```

The cases cover product launch operations, PFAS laboratory validation, architectural coordination, clinical-site monitoring, utility outage restoration, semiconductor lot disposition, and malformed-office PDF recovery. See [docs/case-challenge-profile.md](docs/case-challenge-profile.md) for the boundary of each case.

Official inference sends each `source.pdf` directly to the provider as a native PDF. The harness records the provider's documented ingestion mode for interpretation, but does not convert the input to page images or apply a capability gate to the score.

P20 and P21 use seven committed, synthetic raster fixtures for field-photo and SEM-style regions. Benchmark generation only resizes and annotates those fixed PNG bytes; it never calls an image service. They are test fixtures, not evidence from a real utility, wafer lot, or facility. Their provenance is documented in `scripts/benchmark_cases/assets/README.md`.

P23 is intentionally malformed. Its genuine DOCX-to-LibreOffice export contains severe visible overlap and clipping while retaining legitimate, recoverable native PDF text. That damage is the challenge, not a generator defect: do not “repair” its layout during routine visual QA.

## Setup

Install the JavaScript and Python environments, then create a local environment file:

```bash
npm install
uv sync
cp .env.example .env.local
```

Set `OPENAI_API_KEY` and either `GOOGLE_VERTEX_API_KEY` or the documented Google Vertex ADC variables in `.env.local`. API-key runs of candidates with an explicit Vertex location also require `GOOGLE_VERTEX_PROJECT`; this lets the harness use the project-scoped endpoint instead of silently falling back to the key's regional Express endpoint. Never commit that file. Benchmark generation also requires LibreOffice (`soffice`) and `qpdf` for P23; rendered-page inspection requires Poppler's `pdftoppm`.

## Generate and validate

```bash
npm run generate
npm run validate
npm run render
npm run check
```

`npm run generate` builds into a staging directory, validates the staged corpus, promotes it to `benchmark/`, validates it again, and restores the previous corpus if promotion fails. It accepts the canonical `benchmark/` path or a child of `tmp/`, never an arbitrary repository directory. The committed image fixtures make raster content reproducible without paid generation.

`npm run validate` checks manifest and artifact integrity. `npm run render` adds page rendering under `tmp/pdfs/benchmark/` for human inspection. `npm run preflight`, which is included in `npm run check`, validates every facts contract, provider capability declaration, PDF, reference, and page anchor; any validator warning is release-blocking.

Automated validation cannot establish visual or semantic correctness. Every generated revision still needs all-page visual inspection and a source-to-gold/facts audit. The complete release checklist is in [docs/release-criteria.md](docs/release-criteria.md). The latest audited corpus identity, scorer controls, and anchor/candidate results are in [docs/benchmark-audit-2026-07-10.md](docs/benchmark-audit-2026-07-10.md).

## Run the benchmark

The default command runs the two inexpensive anchor models:

```bash
npm run bench
```

The default anchors are:

- `openai-gpt-5-nano`
- `vertex-gemini-3.1-flash-lite`

Select one or more registered models by repeating `--model`:

```bash
npm run bench -- --model openai-gpt-5-nano --model openai-gpt-5.4-nano
```

The current iteration policy is to establish the anchors first, then add lower-cost registered models deliberately. Models whose observed or projected mean inference cost is at least USD 1 per model/case/sample call are deferred until the corpus and scorer are stable. They remain opt-in and are not part of the default command.

Each selected model is processed as a complete pipeline before the next model. Within a model, inference is bounded to 6 concurrent calls and evaluator scoring to 4 by default. Override those limits with `DOC2MD_INFERENCE_CONCURRENCY` and `DOC2MD_EVALUATOR_CONCURRENCY`.

Every model/case has three sample slots:

```text
runs/<model>/<case>/samples/001/prediction.md
runs/<model>/<case>/samples/001/result.json
runs/<model>/<case>/samples/001/score.json
```

Run and score writes are atomic and protected by per-sample locks; the full command also takes a benchmark lock. A cached prediction is reused only when its sample identity, PDF bytes, prompt, model configuration, input protocol, provider transport/SDK contract, provider mode, and recorded prediction hash are current. A change to one case invalidates that case without needlessly rerunning unchanged cases. Pricing can be refreshed from existing token usage without paying for another inference call. Altered, partial, malformed, or legacy artifacts are rejected, and bounded workers stop taking new paid jobs after the first infrastructure failure.

To replace otherwise valid cached inference results, pass `--force`:

```bash
npm run bench -- --model openai-gpt-5-nano --force
```

The individual stages remain available for debugging:

```bash
npm run run -- --model openai-gpt-5-nano --case P15-architecture-floorplan-diagrams
npm run score -- openai-gpt-5-nano
npm run summary -- openai-gpt-5-nano
npm run report
```

## Scoring contract

The evaluator is `vertex-gemini-3.1-flash-lite`. It receives the page-anchored audited fact obligations and a numbered view of the candidate Markdown. The source PDF and reference Markdown remain hashed benchmark-contract inputs and are audited against the facts, but they are intentionally withheld from the scoring call so their answers cannot leak into candidate credit.

Each region contains atomic leaves with explicit harm weights and intentional partial-credit permission. The evaluator must label every leaf `correct`, `partial`, `missing`, or `incorrect`, and every non-missing status must cite existing, nonblank candidate lines. Missing information earns no credit, while wrong bindings, values, units, direction, state, or source precedence earn negative credit. An extra candidate assertion receives an unsupported-claim penalty only when audited obligations declare the region closed-world and prove the assertion absent. Wrong expected values stay leaf errors and cannot be double-charged as unsupported. Signed regional utility remains visible for audit; only the public case score is clamped to 0–100.

Before publishing model results, run the paid scorer sensitivity/repeatability check:

```bash
npm run audit:scorer
```

It alternates three canonical-reference judgments, three controlled leaf-only contradictions, and three complete-section omissions. The artifact records benchmark, audit-input, and scoring-contract fingerprints in `reports/scorer-audit.json`.

The scoring cache covers the exact run outcome, PDF, prediction, reference, facts, rendered evaluator prompt, evaluator transport configuration, and versioned scorer implementation. Score artifacts record resolved evaluator metadata, and summaries reject cohorts that mix resolved evaluator revisions. A scoreable provider response that explicitly records a response-level model failure is retained as a valid zero-score sample. A provider invocation or transport exception writes no result and leaves the cohort incomplete, as does an evaluator failure, missing artifact, or stale artifact.

## Aggregation and reporting

Aggregation is equal-case and sample-first. For each of the three sample slots, the harness averages the seven current case scores equally; it then reports the mean, sample standard deviation (n−1), minimum, and maximum of those three full-suite scores. Cases are not page-weighted.

Summaries record exact benchmark, inference, scoring, model-configuration, pricing, and cohort-artifact fingerprints. A summary is publishable only when every expected sample is present and current. Report generation recomputes arithmetic and freshness, rejects stale or incomplete summaries, and performs no model calls.

Outputs are written to:

```text
runs/<model>/summary.json
runs/<model>/summary.official.json
reports/index.html
```

The report keeps reconstruction fidelity separate from estimated inference cost, summed model-call duration, output tokens, and failure counts. Evaluator cost and telemetry remain recorded in the summary for auditability.
