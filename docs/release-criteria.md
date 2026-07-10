# Benchmark Release Criteria

A corpus or scoring-contract revision is release-ready only when every applicable gate below passes. Passing code checks alone is not sufficient.

## 1. Canonical identity

- `benchmark/manifest.json` is schema 2, suite `official`, and references exactly 7 cases / 49 pages under `benchmark/`.
- Every case has a readable `source.pdf` plus current `gold.md`, `facts.json`, and `spec.md` files.
- Every release command and document points to the one canonical suite and current case inventory.
- A clean regeneration produces the intended corpus, and the transactional generator leaves the previous corpus intact if validation fails.

## 2. Artifact and visual QA

- `npm run generate`, `npm run validate`, `npm run render`, and `npm run preflight` finish with zero errors and zero warnings.
- A reviewer inspects every rendered page at readable scale for clipping, overlap, illegible text, implausible layout, broken tables, and low-resolution imagery.
- A second source-to-reference pass verifies exact calculations, dates, IDs, units, directions, table bindings, chronology, totals, and draft/final precedence.
- P20/P21 image regions use the documented committed synthetic fixtures; they do not imply real utility or semiconductor evidence.
- P23 is the documented exception to normal layout quality: its visible corruption remains intentional, all required native text is recoverable, and source order is preserved.

## 3. Facts and scorer QA

- Every fact region has a valid page anchor, bounded region budget, explicit open/closed-world status, unique leaf IDs, and appropriate harm/partial-credit settings.
- The candidate-grounded evaluator sees audited obligations plus numbered candidate lines, requires nonblank line evidence for every non-missing leaf, and cannot see PDF/gold answers; exact PDF, gold, facts, candidate, and rendered-prompt hashes still bind the score cache.
- `npm run audit:scorer` shows that a faithful reconstruction scores materially above the known leaf-only counterfactual, repeated seeded judgments are acceptably stable, and the counterfactual receives no scored unsupported claim in addition to its leaf penalties.
- Unit tests cover signed incorrect/unsupported penalties, strict evaluator envelopes, cache tampering, aggregation arithmetic, and stale-cohort rejection.

## 4. Harness and cohort integrity

- `npm run typecheck`, `npm test`, and `npm run check` pass from the release worktree.
- Run, score, summary, and report artifacts are written atomically and remain protected by the expected locks.
- Every published model has all 21 inference slots (7 cases × 3 samples). A scoreable response-level model failure remains an explicit zero; provider/transport invocation errors, evaluator failures, and missing or stale artifacts make the summary incomplete.
- Summary arithmetic is equal-case and sample-first, and the report accepts only summaries matching the current benchmark, model, pricing, scorer, and byte-level cohort fingerprints.

## 5. Model and cost policy during iteration

- Run the two default anchors first: `openai-gpt-5-nano` and `vertex-gemini-3.1-flash-lite`.
- Add lower-cost registered models explicitly with repeated `--model` flags after anchor health is confirmed.
- Defer models with an observed or projected mean inference cost of at least USD 1 per model/case/sample call until the corpus and scoring contract are stable, unless a deliberate premium run is approved.
- Record pricing version, requested and resolved model IDs, token usage, estimated inference cost, evaluator cost, failures, and any provider-mode caveats. Do not mix inference and evaluator spend.

## 6. Release record

Record the commit or worktree revision, tool versions, validation commands, corpus hash/fingerprint, scorer contract fingerprint, model cohort, and any intentional exceptions. A human should sign off on the all-page visual audit and semantic audit before publishing scores.
