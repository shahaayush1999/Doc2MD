# Benchmark Release Criteria

A corpus or scoring-contract revision is release-ready only when every applicable gate below passes. Passing code checks alone is not sufficient.

## 1. Canonical identity

- `benchmark/manifest.json` is schema 2, suite `official`, and references exactly 5 cases / 84 pages under `benchmark/`.
- Every case has a readable `source.pdf` plus current `gold.md`, `facts.json`, and `spec.md` files.
- Every release command and document points to the one canonical suite and current case inventory.
- A clean regeneration produces the intended corpus, and the transactional generator leaves the previous corpus intact if validation fails.

## 2. Artifact and visual QA

- `npm run generate`, `npm run validate`, `npm run render`, and `npm run preflight` finish with zero errors and zero warnings.
- A reviewer inspects every rendered page at readable scale for clipping, overlap, illegible text, implausible layout, broken tables, and low-resolution imagery.
- A second source-to-reference pass verifies exact calculations, dates, IDs, units, directions, table bindings, chronology, totals, and draft/final precedence.
- P21 image regions use the documented committed SEM-style fixtures; they do not imply real microscopy evidence.
- P23 is the documented exception to normal layout quality: its visible corruption remains intentional, all required native text is recoverable, and source order is preserved.
- `npm run audit:text-layer` measures P23's native layer from the PDF itself rather than inferring recoverability from the malformed visible page.

## 3. Facts and scorer QA

- Every facts file is schema 3. Every region has a label, one or more page/layer anchors, a gold-section link, modality, primary capability axis, text-only-recoverability flag, bounded evidence budget, unique canonical claim IDs, and typed leaf evidence policies. There is no partial-credit status.
- `npm run audit:corpus` passes with zero errors or warnings and reports both raw pooled budgets and equal-case effective shares by modality, region kind, primary capability axis, and declared text-only recoverability.
- `npm run audit:reference` self-scores all five canonical references at 100 with every leaf evidence-supported in its declared gold section. Semantic-only leaves remain explicitly flagged for human review.
- `npm run audit:text-layer` passes with zero hard `textOnlyRecoverable` declaration contradictions. Its report scopes extracted text to each region's anchor pages, separates exact typed-policy recovery from qualitative term-only potential, preserves unresolved and contradictory leaves, and computes suite exposure as an equal-case mean rather than a pooled-budget rate. Treat the result only as native-layer exposure evidence, never as a model score or reliability estimate.
- The candidate-grounded evaluator sees audited obligations plus numbered candidate lines, requires nonblank line evidence for every non-missing leaf, and cannot see PDF/gold answers; exact PDF, gold, facts, candidate, and rendered-prompt hashes still bind the score cache.
- `npm run audit:scorer` exercises reference, omission, substitution, table misbinding, closed-world hallucination, and source-precedence counterfactuals once each. The evidence-gated score must order them sensibly, and a human must review every resulting judgment. One draw is not reported as a stability estimate.
- Unit tests cover signed incorrect/unsupported penalties, strict evaluator envelopes, cache tampering, aggregation arithmetic, and stale-cohort rejection.

## 4. Harness and cohort integrity

- `npm run typecheck`, `npm test`, and `npm run check` pass from the release worktree.
- Run, score, summary, and report artifacts are written atomically and remain protected by the expected locks. Every paid inference run key has a create-once attempt marker; a missing/corrupt result with an existing marker fails closed instead of silently redrawing.
- Every development anchor has all 5 inference slots (5 cases × 1 sample). A scoreable response-level model failure remains an explicit zero; provider/transport invocation errors, evaluator failures, and missing or stale artifacts make the summary incomplete. Artifacts from the retired three-sample protocol and retired cases are stale under the current protocol fingerprint.
- Summary arithmetic is equal-case across the complete one-sample cohort, and the report accepts only summaries matching the current benchmark, model, pricing, scorer, and byte-level cohort fingerprints.
- One-sample summaries and reports leave SD/range unavailable, use restrained score precision, and make no repeatability or reliability claim. Logical draws and transport request attempts/retries are reported separately; retries never become cohort samples. Repeated final validation requires explicit approval after the benchmark is otherwise stable.

## 5. Model and cost policy during iteration

- During iteration, run only the two default anchors: `openai-gpt-5-nano` and `vertex-gemini-3.1-flash-lite`.
- Do not run other registered candidates, premium models, or repeated anchor cohorts until a deliberate final-validation checkpoint is explicitly approved. Non-anchor inference requires a matching prefixed checkpoint id from both the CLI and `DOC2MD_FINAL_VALIDATION_AUTHORIZATION`; a model id alone must remain insufficient.
- Record pricing version, requested and resolved model IDs, token usage, estimated inference cost, evaluator cost, failures, and any provider-mode caveats. Do not mix inference and evaluator spend.

## 6. Release record

Record the commit or worktree revision, tool versions, validation commands, corpus hash/fingerprint, scorer contract fingerprint, model cohort, and any intentional exceptions. A human should sign off on the all-page visual audit and semantic audit before publishing scores.
