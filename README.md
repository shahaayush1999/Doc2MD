# Doc2MD

Doc2MD measures how faithfully an AI model reconstructs a PDF as one Markdown document. The target is exhaustive recovery of the document's information and reading experience: text, hierarchy, tables, forms, state changes, charts, diagrams, images, annotations, and spatial or directional relationships. It is not a summarization benchmark.

## Canonical benchmark

The official suite is manifest schema 2, version 1.0.0: **5 cases and 84 pages** under `benchmark/`. Each case contains:

```text
benchmark/cases/<case-id>/source.pdf
benchmark/cases/<case-id>/gold.md
benchmark/cases/<case-id>/facts.json
benchmark/cases/<case-id>/spec.md
```

The cases cover PFAS laboratory validation, technical spatial coordination, a genuinely long clinical-site packet, semiconductor lot disposition, and malformed-office PDF recovery. See [docs/case-challenge-profile.md](docs/case-challenge-profile.md) for the boundary of each case.

Official inference sends each `source.pdf` directly to the provider as a native PDF. The harness records the provider's documented ingestion mode for interpretation, but does not convert the input to page images or apply a capability gate to the score.

P21 uses four committed SEM-style raster fixtures. Benchmark generation only resizes and annotates those fixed PNG bytes; it never calls an image service. They are test fixtures, not real microscopy evidence. Their provenance is documented in `scripts/benchmark_cases/assets/README.md`.

P23 is intentionally malformed. Its genuine DOCX-to-LibreOffice export contains severe visible overlap and clipping while retaining legitimate, recoverable native PDF text. That damage is the challenge, not a generator defect: do not “repair” its layout during routine visual QA.

## Setup

Install the JavaScript and Python environments, then create a local environment file:

```bash
npm install
uv sync
cp .env.example .env.local
```

Set `OPENAI_API_KEY` and either `GOOGLE_VERTEX_API_KEY` or the documented Google Vertex ADC variables in `.env.local`. API-key runs of candidates with an explicit Vertex location also require `GOOGLE_VERTEX_PROJECT`; this lets the harness use the project-scoped endpoint instead of silently falling back to the key's regional Express endpoint. Never commit that file. Benchmark generation also requires LibreOffice (`soffice`) and `qpdf` for P23; rendered-page inspection and native-layer exposure measurement require Poppler's `pdftoppm` and `pdftotext`.

## Generate and validate

```bash
npm run generate
npm run validate
npm run render
npm run audit:corpus
npm run audit:text-layer
npm run audit:reference
npm run check
```

`npm run generate` builds into a staging directory, validates the staged corpus, promotes it to `benchmark/`, validates it again, and restores the previous corpus if promotion fails. It accepts the canonical `benchmark/` path or a child of `tmp/`, never an arbitrary repository directory. The committed image fixtures make raster content reproducible without paid generation.

`npm run validate` checks manifest and artifact integrity. `npm run render` adds page rendering under `tmp/pdfs/benchmark/` for human inspection. `npm run audit:corpus` joins the physical PDFs, manifest, gold, and facts and reports raw pooled budgets separately from their effective shares under equal-case scoring. `npm run audit:text-layer` extracts every PDF's native text one page at a time and limits each facts region to its declared anchor pages before applying the scorer's deterministic typed policies. It reports exact recovered leaf harm and effective region budget, unresolved and contradictory leaves, qualitative term-only potential, declaration mismatches, and equal-case suite exposure in `reports/text-layer-exposure-audit.json`. This is leakage/exposure evidence, not a model score; qualitative potential always requires human review. `npm run audit:reference` proves that the canonical reference supports every scored leaf in its declared section. P23's hidden native layer is measured even though its visible page is intentionally malformed. Hard declaration contradictions fail the command and `npm run check`.

`npm run preflight`, which is included in `npm run check`, validates every facts contract, provider capability declaration, PDF, reference, and page anchor; any validator warning is release-blocking.

Automated validation cannot establish visual or semantic correctness. Every generated revision still needs all-page visual inspection and a source-to-gold/facts audit. The complete release checklist is in [docs/release-criteria.md](docs/release-criteria.md). The redesign objective and saturation diagnosis are in [docs/benchmark-objective.md](docs/benchmark-objective.md) and [docs/redesign-audit-and-plan.md](docs/redesign-audit-and-plan.md). The current one-draw result and launch verdict are in [docs/benchmark-redesign-validation-2026-07-10.md](docs/benchmark-redesign-validation-2026-07-10.md). The older [benchmark audit](docs/benchmark-audit-2026-07-10.md) is explicitly historical.

## Run the benchmark

The default command runs the two inexpensive anchor models:

```bash
npm run bench
```

The default anchors are:

- `openai-gpt-5-nano`
- `vertex-gemini-3.1-flash-lite`

Select either anchor explicitly when debugging only one model:

```bash
npm run bench -- --model openai-gpt-5-nano
```

Normal benchmark iteration is restricted to the two anchors. Every paid inference entrypoint enforces that allowlist. A non-anchor model is fail-closed unless an approved final-validation checkpoint id beginning with `final-validation:` is supplied both through `--final-validation-authorization` and the `DOC2MD_FINAL_VALIDATION_AUTHORIZATION` environment variable. Selecting a model name alone is never sufficient. Do not run other registered candidates or premium models during corpus/scorer development.

Each selected model is processed completely before the next model. Within that model, every case runs as an independent inference-then-evaluation pipeline and all case pipelines start concurrently. A fast case begins evaluation immediately instead of waiting for the slowest inference. There are no concurrency tuning settings for the benchmark pipeline.

Every model/case has exactly one development sample slot:

```text
runs/<model>/<case>/samples/001/prediction.md
runs/<model>/<case>/samples/001/result.json
runs/<model>/<case>/samples/001/score.json
```

Run and score writes are atomic and protected by per-sample locks; the full command also takes a benchmark lock. Immediately before any paid inference request, the runner creates a read-only, create-once marker under `samples/001/attempts/<run-key>.json`. If a process crashes, persistence fails, or a current artifact is damaged after that reservation, the marker remains and the harness refuses to issue another draw for the same run key. There is no normal `--force` overwrite path. A changed PDF, prompt, model configuration, or hashed transport protocol creates a different run key and therefore a separately auditable attempt marker.

A cached prediction is reused only when its sample identity, PDF bytes, prompt, model configuration, input protocol, provider transport/SDK contract, provider mode, attempt-marker hash, and recorded prediction hash are current. The sample-count protocol is hashed too, so artifacts from the retired three-sample protocol are not accepted as current one-sample runs. A change to one case invalidates that case without needlessly rerunning unchanged cases. Pricing can be refreshed from existing token usage without paying for another inference call. Altered, partial, malformed, or legacy artifacts are rejected. All selected case pipelines start together, and the harness waits for every started pipeline to settle before releasing its benchmark lock or surfacing a failure.

The logical stochastic cohort remains exactly one draw per model/case. SDK transport retries may retry a failed request within that same reserved draw; run artifacts and summaries record logical generation calls, actual transport request attempts, and retry counts separately. Transport retries are never interpreted as extra cohort samples.

The individual stages remain available for debugging:

```bash
npm run run -- --model openai-gpt-5-nano --case P15-architecture-floorplan-diagrams
npm run score -- openai-gpt-5-nano
npm run summary -- openai-gpt-5-nano
npm run report
```

When the anchors are run separately, the first command produces the currently available anchor report and the second automatically reloads both current anchor summaries to produce the combined comparison. Standalone `npm run report` is anchor-only by default. Detailed exact arithmetic remains in the JSON audit artifacts; normal benchmark console output and the HTML report use restrained stakeholder-facing score precision.

## Scoring contract

The evaluator is `vertex-gemini-3.1-flash-lite`. It receives the page-anchored audited fact obligations and a numbered view of the candidate Markdown. The source PDF and reference Markdown remain hashed benchmark-contract inputs and are audited against the facts, but they are intentionally withheld from the scoring call so their answers cannot leak into candidate credit.

Facts schema 3 gives every region typed source anchors, a gold-section link, modality and capability metadata, a text-only-recoverability flag, and a bounded evidence budget. Atomic leaves have canonical claim identities and typed evidence policies for scalars, exact table bindings, form states, ordered records, directed edges, source precedence, and visual descriptions. There is no generic partial-credit status. The evaluator labels every leaf `correct`, `missing`, or `incorrect`; every non-missing status must cite existing, nonblank candidate lines and then pass a deterministic evidence gate. Missing information earns no credit, while wrong bindings, values, units, direction, state, or source precedence earn negative credit. An extra assertion receives a penalty only when a structured closed-world region proves it absent. Wrong expected values remain leaf errors and cannot be double-charged. Signed regional utility stays visible for audit; only the public case score is clamped to 0–100.

Before publishing model results, run the scorer counterfactual audit:

```bash
npm run audit:scorer
```

It evaluates the canonical reference and one controlled instance each of omission, substitution, table misbinding, closed-world hallucination, and wrong source precedence. Every resulting judgment is human-reviewed. Because each variant is run once, the artifact makes no repeatability claim. It records benchmark, audit-input, and scoring-contract fingerprints in `reports/scorer-audit.json`.

The scoring cache covers the exact run outcome, PDF, prediction, reference, facts, rendered evaluator prompt, evaluator transport configuration, and versioned scorer implementation. Score artifacts record resolved evaluator metadata, and summaries reject cohorts that mix resolved evaluator revisions. A scoreable provider response that explicitly records a response-level model failure is retained as a valid zero-score sample. A provider invocation or transport exception writes no result and leaves the cohort incomplete, as does an evaluator failure, missing artifact, or stale artifact.

## Aggregation and reporting

Aggregation is equal-case across the single complete development cohort: each case contributes equally and cases are not page-weighted. A one-sample run is a directional observation, not a reliability estimate. Summaries and reports therefore record standard deviation, minimum, and maximum as unavailable rather than manufacturing a zero deviation or a one-point “range.” Scores are displayed with restrained precision, and small movements must not drive benchmark tuning. Repeated runs are reserved for an explicitly approved final-validation checkpoint.

Summaries record exact benchmark, inference, scoring, model-configuration, pricing, and cohort-artifact fingerprints. A summary is publishable only when every expected sample is present and current. Report generation recomputes arithmetic and freshness, rejects stale or incomplete summaries, and performs no model calls.

Outputs are written to:

```text
runs/<model>/summary.json
runs/<model>/summary.official.json
reports/index.html
```

The report keeps reconstruction fidelity separate from estimated inference cost, summed model-call duration, output tokens, and failure counts. It includes evidence-budget-weighted capability and modality diagnostics to explain the observed anchor gap. It explicitly states that the development score comes from one stochastic sample and makes no repeatability or reliability claim. Evaluator cost and telemetry remain recorded in the summary for auditability.
