# Doc2MD redesign validation — 2026-07-10

## Verdict

The rebuilt five-case benchmark is suitable for continued benchmark development and cheap-anchor comparison. It is not saturated: the one-draw development scores are **26.1 for GPT-5 Nano** and **55.9 for Gemini 3.1 Flash-Lite**, an observed **29.8-point gap**. Gemini is materially better on every case, and no single case supplies a majority of the separation.

This is not yet a repeatability or final leaderboard claim. Each model was run exactly once per case, so there is no measured variance. Gemini also lands slightly below the 60–80 diagnostic band. Its misses were inspected and are substantive—especially spatial relations, raster/form state, image morphology, mixed-source joins, and exhaustive long-packet detail—so the benchmark was not weakened or reweighted to move the score. Repeated validation remains a separate checkpoint requiring explicit approval.

## What changed from the retired benchmarks

There were two different failure states, and their score gaps should not be conflated:

| Benchmark state | Nano | Gemini 3.1 Flash Lite | Gap | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Original handoff suite | 39.1 | 93.4 | 54.3 | Strong separation, but materially confounded by raster imbalance, coarse compound facts, cap cliffs, page weighting, and truncation sensitivity. |
| Retired saturated suite | 92.4 | 98.7 | 6.3 | Construct loss and scorer false positives made the weak anchor appear nearly solved. Its sample-001 gap was only about 5.3 points. |
| Current redesign | 26.1 | 55.9 | 29.8 | Unsaturated, equal-case, atomic, mixed-modality, and broadly separated. |

The earlier 54.3-point delta came down for two kinds of reasons.

Some reduction was legitimate. Removing broad compound facts, page-weight dominance, length caps, and global score cliffs removed artificial leverage where one truncation or one judge label could swing a case by tens of points.

The later collapse to 6.3 points was not legitimate capability convergence. The retired 49-page corpus exposed native text on every page, had no full-page scans, and contained only 6,286 extracted words. Its nominal long case was nine pages and 1,219 extracted words. Clean tables dominated: 1,518 of 1,946 leaves were table leaves, and table/text/structure regions controlled most of the score. Several supposedly visual answers were repeated in captions, tables, or final prose. At most about 5.88 score points depended on unique raster evidence. The scorer also demonstrably credited absent P17 values and states. These changes disproportionately raised Nano by turning visual reconstruction into clean-text/table recovery.

The present 29.8-point gap therefore should not be read as an attempt to restore the old 54.3. It is the separation that remains after removing both the old suite's artificial cliffs and the saturated suite's construct leakage.

## Implemented corpus

- 5 cases, 84 pages, 200 scored regions, 1,205 atomic leaves, and 372 raw evidence-budget units.
- 47 native-only pages, 19 full-page raster pages, and 18 mixed pages.
- 12,490 extracted native-text words across the suite.
- P17 is a genuine 48-page longitudinal packet: 28 native-only, 12 full-raster, and 8 mixed pages, with 8,108 extracted words and meaningful obligations through page 48.
- Effective modality shares under equal-case scoring are 47.20% native text, 29.90% raster, 12.60% mixed, 7.99% vector geometry, and 2.31% native-layer recovery.
- Declared text-only-recoverable evidence is 47.20% under equal-case weighting, but page-anchored deterministic extraction recovers only 18.57% exactly. Exact plus semantic-term potential is 19.85%; semantic potential is not treated as proven recovery.
- P07 and P20 were retired as standalone cases. Their useful precedence, chronology, redline, and dependency patterns were consolidated into harder retained cases. P12, P15, P17, P21, and P23 each own a distinct primary challenge.

## One-draw anchor result

| Case | Pages | GPT-5 Nano | Gemini 3.1 Flash Lite | Gap | Contribution to 29.8-point suite gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| P12 PFAS validation | 12 | 31.4 | 58.6 | 27.1 | 5.4 |
| P15 architecture and diagrams | 10 | 9.0 | 37.2 | 28.2 | 5.6 |
| P17 clinical monitoring | 48 | 6.5 | 40.3 | 33.8 | 6.8 |
| P21 semiconductor disposition | 9 | 5.9 | 54.9 | 49.0 | 9.8 |
| P23 malformed native-layer recovery | 5 | 77.5 | 88.5 | 10.9 | 2.2 |
| **Equal-case suite** | **84** | **26.1** | **55.9** | **29.8** | **29.8** |

P21 contributes 32.9% of the raw case-gap sum, P17 22.7%, P15 18.9%, P12 18.2%, and P23 7.3%. The result is therefore not a single-case artifact. P23 is intentionally easier for both anchors and tests a unique malformed-export/native-layer recovery capability; equal-case aggregation limits it to 20% of the suite.

Diagnostic slices are evidence-budget-weighted pooled diagnostics, not additive contributions to the official equal-case score. The largest Gemini-minus-Nano differences are:

| Diagnostic | Gap |
| --- | ---: |
| Table reconstruction | +55.3 |
| Native-text reconstruction | +45.0 |
| Form state | +36.8 |
| Precise recall | +28.8 |
| Raster evidence | +26.7 |
| Long-context coherence | +22.5 |
| Source precedence | +22.2 |
| Image description | +15.2 |
| Low-quality scans | +10.7 |
| Cross-page joins | +8.3 |
| Chart/diagram/spatial | +7.8 |

Both anchors score 100 on the narrow native-layer-recovery primary slice and 75 on the single structure slice. Both score zero on the small reading-order slice. These zero-gap diagnostics are reported rather than hidden.

## Output and judgment review

Exactly ten logical inference calls were made: five cases for each anchor, one sample each. All ten finished with `stop`; there were ten transport attempts, zero retries, zero model failures, and zero evaluator failures. No anchor inference was redrawn after scorer, report, or documentation changes.

Current artifact-attributed telemetry:

| Model | Inference cost | Evaluator cost in current score artifacts | Output tokens | Calls / attempts |
| --- | ---: | ---: | ---: | ---: |
| GPT-5 Nano | $0.010743 | $0.146687 | 17,424 | 5 / 5 |
| Gemini 3.1 Flash Lite | $0.070113 | $0.156995 | 39,048 | 5 / 5 |

Nano produced only 949–4,218 words per case. P12 ends after a partial early-page reconstruction, P15 relies heavily on image placeholders, P17 stops with the archive still “continuing,” and P21 is superficial. P23 is its only strong case.

Gemini reconstructs all 48 P17 pages and produces 11,721 words there, but completeness of page presence is not completeness of obligations. Its remaining misses include exact visual and spatial relations in P15, image morphology in P21, form states and mixed-source bindings, and many detailed longitudinal obligations in P17. Human review of all 74 qualitative leaves agreed with the credited/missing transitions. The final Gemini P17 incorrect leaves are two genuine rule contradictions; the packet-local year-shorthand table values are now credited correctly. P21's correctly reported Wafer 07 coordinates are also credited after replacing an erroneous semantic judgment with an authoritative ordered-coordinate policy.

## Scorer validation and fixes found during calibration

The scorer contract is `atomic-region-candidate-grounded-v9`. It uses candidate-cited atomic obligations, signed incorrect harm, closed-world unsupported penalties, deterministic typed evidence gates, and equal-case aggregation. Only the public case score is clamped.

Calibration exposed and fixed three defects without rerunning anchor inference:

1. P17 source tables visibly use packet-local dates such as `12 May 16:42`, while canonical facts expand the unambiguous year to `12 May 2026 16:42`. Both literal and expanded forms are now accepted; a yearless alternative alone remains insufficient.
2. Gemini's exact P21 Wafer 07 set `D5, D6, E5` was incorrectly labeled wrong by the evaluator. That obligation now uses an authoritative ordered-coordinate policy and is credited.
3. Long-candidate validation rescanned the full candidate for every judge-reported lexical omission even though those statuses were ineligible for promotion. A minimized 120-leaf regression took 6.55 seconds before the fix and about 3.5 milliseconds afterward. Report generation also redundantly re-derived both summaries four times; it now performs one full derivation and uses byte-level cohort fingerprints for write-race checks.

Stored judgments may cross implementation-only scorer drift only when the scoring semantic version and evaluator identity match and the candidate, PDF, gold, facts, and rendered evaluator prompt hashes are all byte-identical. Any content drift still invalidates reuse. Final score artifacts were recomputed from content-identical stored judgments under the final contract.

The counterfactual scorer audit passes all seven predicates:

- Canonical reference: 100.
- Controlled omission: 75 with the intended leaves missing.
- Substitution: 97.12 with exactly two incorrect-harm units.
- Table misbinding: 99.18 with exactly two incorrect-harm units.
- Closed-world hallucination: 99.15 with one deterministic E-99 penalty.
- Wrong source precedence: 94.23 with the intended controlling-state error.
- No leaf error is double-charged as unsupported.

The six stored provider judgments cost $0.089137 and were replayed without new provider calls after the final implementation-only scorer changes. Every transition was human-reviewed.

## Corpus and release QA

- Every one of the 84 rendered pages was inspected at readable scale. No unintended clipping, overlap, or illegibility was found. P23's documented malformed export remains intentional.
- A final clean-room generation reproduced all 20 case artifacts byte-for-byte. The manifest matches after path-root normalization, and provider capabilities are byte-identical.
- The canonical reference audit supports 1,205/1,205 leaves, scores all five references at 100, and makes zero provider calls. Seventy-four semantic-only leaves remain explicitly human-reviewed.
- The text-layer audit has zero hard declaration contradictions and 90 transparent declaration-review items.
- `npm run check` passes 112 TypeScript tests, 20 Python tests, corpus audit, text-layer audit, reference audit, and preflight.
- `npm run render` previously completed with zero errors or warnings; the final scorer-only fact changes did not alter any PDF or gold bytes.
- The combined two-anchor HTML report was regenerated successfully from current summaries.

## Release status and next checkpoint

The benchmark is **unsaturated and useful for development**, with a broad, production-plausible weak-versus-good separation. It should not yet be described as statistically reliable or as a final public leaderboard. The next deliberate checkpoint is to decide whether to authorize repeated anchor runs for uncertainty measurement and whether to run a stronger model to measure remaining headroom. Neither should happen during ordinary iteration or without explicit approval.
