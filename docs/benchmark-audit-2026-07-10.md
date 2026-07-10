# Benchmark Audit and Iteration Record — 2026-07-10

> **Historical baseline:** This file records the superseded saturated corpus and its six-model, three-sample experiment. It is retained to explain why the benchmark is being rebuilt; it does not describe the current development protocol. Current development uses only GPT-5 Nano and Gemini 3.1 Flash-Lite, one sample per model/case, and reports no SD/range or reliability estimate. The old run artifacts are invalid under the current sample-protocol fingerprint.

## Executive verdict

The rebuilt Doc2MD suite is a defensible development benchmark for faithful, end-to-end PDF-to-Markdown reconstruction. Its corpus, facts contract, inference cache, scorer, aggregation, and report now have explicit integrity checks. It is useful for comparing provider PDF pipelines, finding truncation and reliability failures, and separating the cheapest models from stronger low-cost models.

It is not yet a decisive frontier leaderboard. Five of the six current models score from 92.4 to 99.4, and the two development anchors are separated by 6.3 points. That compression is reported rather than manipulated away. The current evidence does not justify claiming that sub-point differences among strong models are universal capability differences; premium models remain deferred until a deliberate checkpoint.

## Canonical corpus identity

- Manifest: schema 2, suite `official`, version `0.2.0`.
- Inventory: 7 cases, 49 pages, 117 scored regions, and 1,946 atomic leaves.
- Partial credit: explicitly permitted on 136 qualitative or genuinely divisible leaves; exact values, cells, units, directions, and state bindings remain strict.
- Artifact contract: every case contains only `source.pdf`, `gold.md`, `facts.json`, and `spec.md` at its exact canonical path.
- Benchmark fingerprint: `a9ac15a416c15fffe399a1180482a79ab2334b3b7b4b3926d5f8c9d5748b436e`.
- Full `benchmark/` content digest: `c99e9353a470c1b8b31cb5d03ea8bc3be85e519dc9438839dd6534cad39d1280`. This is the SHA-256 of the sorted per-file SHA-256 listing.
- A clean `npm run generate` reproduced the same content digest byte-for-byte.

### Reproducibility environment

- Rebuild commit: `8cde48f08c16540ba54fd787d8784a3bb42bc911` on `main`, based on `b2a128bfc8431a6fb87d597dd75d6f62b1abeac1`.
- Node.js `v22.22.3`; npm `10.9.8`.
- uv `0.11.18`; Python `3.11.15`.
- LibreOffice `26.2.2.2`; qpdf `12.3.2`; pdftoppm `26.04.0`.

| Case | Pages | Regions | Leaves | Primary contribution |
| --- | ---: | ---: | ---: | --- |
| P07 launch readiness | 7 | 16 | 211 | Cross-functional dependencies, heatmaps, ledgers, and controlling draft/final state |
| P12 PFAS validation | 7 | 19 | 517 | Equations, calibration, continuation tables, chromatograms, reinjection, and uncertainty |
| P15 architecture | 6 | 16 | 174 | Floorplan geometry, rack elevations, directed topology, schedules, and RFI revision |
| P17 clinical monitoring | 9 | 15 | 419 | Longitudinal chronology, lab flags, deviations, accountability, form marks, and corrections |
| P20 utility outage | 8 | 17 | 244 | SCADA/switching order, one-line topology, restoration dependencies, DER state, and field evidence |
| P21 semiconductor disposition | 8 | 19 | 271 | Wafer maps, metrology/SPC, recipe conflict, SEM-style evidence, MRB state, and release logic |
| P23 malformed office export | 4 | 15 | 110 | Legitimate native-text recovery from a visibly corrupt DOCX-to-LibreOffice PDF export |

The previous P22 pharmaceutical case was removed because its primary regulated-release contribution overlapped P17 and P21 and added disproportionate length without enough unique signal.

## Corpus and visual audit

All 49 page renders were inspected during the rebuild. The final automated secondary audit is recorded in `tmp/page-audit/final-audit.json` under protocol `page-quality-v3-ai7.0.11-vertex5.0.7`.

- No page contains extraction-facing or benchmark-facing language.
- P07, P12, P15, P17, P20, and P21 have no remaining release-blocking visual issue.
- P23 pages 1–4 are intentionally flagged `shouldFixBeforeBenchmarking`: the visible overlap and clipping are the genuine malformed-export challenge, while the native PDF text remains recoverable. This exception is documented and must not be silently repaired.
- P20/P21 use seven committed synthetic raster fixtures. They are test fixtures, not real utility or semiconductor evidence. Their provenance is documented in `scripts/benchmark_cases/assets/README.md`.
- The final page audit cost recorded in its artifact is USD 0.028550.

The seven raster fixtures were generated once with the built-in image-generation workflow to provide realistic utility field-condition and SEM-style defect imagery. Benchmark generation itself is offline and deterministic: it only reads the committed PNG bytes.

## Scoring correction and validation

The frozen scoring contract is `atomic-region-candidate-grounded-v5`, fingerprint `afb73412f336473dfa5456185f8001ec4315b1fda81af36cc4fc433053268bf3`.

The evaluator receives audited atomic obligations and numbered candidate lines. It does not receive the source PDF or gold Markdown, preventing answer leakage. Every non-missing judgment must cite real, nonblank candidate lines. Exact generated table obligations receive an additional deterministic evidence gate. Incorrect expected values remain leaf errors; unsupported claims are limited to proven closed-world absences, so the same defect cannot be charged twice.

The controlled scorer audit in `reports/scorer-audit.json` passes all checks:

| Fixture | Three scores | Mean | Spread |
| --- | --- | ---: | ---: |
| Canonical reference | 100, 100, 100 | 100.000 | 0.000 |
| Eight controlled D17 substitutions | 67.396, 66.979, 66.979 | 67.118 | 0.417 |
| Complete page-2 omission | 75, 75, 75 | 75.000 | 0.000 |

The counterfactual receives leaf penalties without a duplicate unsupported-claim penalty. The recorded scorer-audit cost is USD 0.081598.

## Current anchor and lower-cost cohort

Every published model has 21 current inference artifacts and 21 valid evaluator artifacts. Aggregation is equal-case and sample-first: each sample slot averages the seven cases, then the reported mean, sample SD, minimum, and maximum are computed across the three full-suite sample scores.

| Rank | Model | Role | Score | Full-suite SD | Three-sample range | Inference cost, 21 calls | Evaluator cost | Length finishes |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `vertex-gemini-3-flash-preview` | lower-cost candidate, preview | 99.4 | 0.109 | 99.378–99.567 | $0.242951 | $0.499641 | 0 |
| 2 | `vertex-gemini-3.1-flash-lite` | good development anchor, public preview | 98.7 | 1.097 | 97.486–99.615 | $0.115133 | $0.470439 | 0 |
| 3 | `openai-gpt-5.4-mini` | lower-cost candidate | 98.3 | 1.344 | 96.744–99.100 | $0.274394 | $0.493305 | 0 |
| 4 | `openai-gpt-5.4-nano` | lower-cost candidate | 96.3 | 1.401 | 95.153–97.840 | $0.078743 | $0.492589 | 0 |
| 5 | `openai-gpt-5-nano` | weak/cheap development anchor | 92.4 | 0.725 | 91.854–93.233 | $0.019793 | $0.458985 | 0 |
| 6 | `vertex-gemini-2.5-flash-lite` | deprecation control | 88.9 | 7.814 | 79.838–93.735 | $0.056986 | $0.519257 | 2 |

The published six-model cohort represents 126 inference calls and 126 valid evaluator artifacts. Two judgments required one retry each, for 128 evaluator attempts in total; there are zero provider-call failures and zero final evaluator failures. Current successful artifacts record USD 0.788000 of inference cost and USD 2.934216 of evaluator cost, including those evaluator retries. These are artifact costs, not a claim about all historical iteration, failed probes, or superseded runs.

### Interpretation

- Gemini 3 Flash preview is the strongest tested candidate and the most stable in this cohort. Six case means are 100; the intentionally malformed P23 averages 96.09.
- Gemini 3.1 Flash-Lite remains the best current low-cost quality anchor at 98.7 and costs less than half the tested GPT-5.4 Mini inference total.
- GPT-5.4 Nano is the strongest low-cost stable OpenAI option tested here at 96.3. Its main remaining weakness is P21 consistency.
- GPT-5 Nano is inexpensive and repeatable, but at 92.4 it no longer behaves like a very weak content-reconstruction baseline on this fair corpus.
- Gemini 2.5 Flash-Lite is not a deployment recommendation. Two 24k-token truncations on P20/P21 caused large score variance; Google also lists the stable endpoint for discontinuation on 2026-07-22.
- The narrow strong-model band is real under this scorer. Further difficulty should be added only when it represents a missing, realistic reconstruction capability—not to manufacture a target ranking.

## Harness integrity changes

- Native PDFs remain the official input. Provider-specific ingestion mode is recorded, not used as a score gate.
- Three per-case samples, per-sample keys, strict schemas, atomic writes, owner-checked locks, and prediction hashes prevent partial or mixed cache reuse.
- Model configuration, provider transport epoch, SDK versions, PDF payload mode, sampling mode, and explicit Vertex route are fingerprinted.
- Global-only Vertex candidates use a project-scoped global endpoint even under API-key authentication; a regression test prevents silent fallback to the key's regional Express route.
- Bounded worker pools stop pulling new paid jobs after the first infrastructure error and wait for already-started jobs to settle.
- Scoring, summary, and report publication revalidate current byte-level cohort fingerprints and arithmetic before atomic writes.
- Current report generation accepts exactly six current summaries and rejects the stale premium summaries.

## Deferred models

The following high-cost or premium runs were intentionally not repeated during this iteration:

- `vertex-gemini-3.5-flash`
- `vertex-gemini-3.1-pro`
- `openai-gpt-5.5`

Their older summaries do not match the current benchmark/scorer fingerprints and are excluded from `reports/index.html`. They should be run only at a deliberate frontier checkpoint.

To prevent manual consumers from mistaking ignored legacy files for current evidence, the three stale premium run directories, all retired P22 run directories, and the anchors' pre-sample-slot root artifacts were moved out of active `runs/` into `tmp/stale-runs-2026-07-10/`. They remain locally recoverable but cannot be loaded as current runs.

## Release verification

The following completed successfully on the final corpus:

- `npm run generate` with identical before/after corpus digests.
- `npm run render`: 7 cases / 49 pages, zero validation errors and warnings.
- `npm run check`: TypeScript typecheck, 42 tests, and zero-warning preflight.
- `git diff --check` after classifying generated PDF/PNG/DOCX artifacts as binary.
- Scorer-audit fingerprint equality across every current model summary.
- Static HTML report QA: six current data points, six result rows, seven case rows, no unresolved template values, truthful operating-metric labels, and no P22 data.

The in-app browser refused the local `file://` report under its URL security policy and prohibited alternate browser routing. Therefore this record does not claim a final in-app-browser visual pass. The deterministic report test and static HTML checks passed; a human should still open `reports/index.html` locally before public publication.

## Official model and pricing references

- OpenAI model pricing: <https://developers.openai.com/api/docs/models/gpt-5-nano>, <https://developers.openai.com/api/docs/models/gpt-5.4-nano>, <https://developers.openai.com/api/docs/models/gpt-5.4-mini>
- Google generative AI pricing: <https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing>
- Gemini 2.5 Flash-Lite availability/lifecycle: <https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-lite>
- Gemini 3 Flash availability: <https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-flash>
