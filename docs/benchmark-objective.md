# Doc2MD redesign objective

> Historical design brief for the benchmark rebuild. Its one-draw, anchor-only development protocol records the original iteration phase and is not the current operating procedure.

Use this as the goal prompt for the benchmark rebuild.

## Goal

Rebuild Doc2MD into an unsaturated, operationally valid benchmark for faithful PDF-to-Markdown reconstruction. Treat the current suite as raw material; there is no backward-compatibility requirement.

The benchmark must measure whether a model can turn a real native PDF into one exhaustive, faithful, machine-usable Markdown document. Correctness and recoverability matter more than visual Markdown similarity. Difficulty must come from authentic document complexity, never ambiguity, illegibility, adversarial nonsense, arbitrary caps, or score-shaping tricks.

## Outcome and calibration guardrails

- Use `openai-gpt-5-nano` as the deliberately weak, cheap development anchor.
- Use `vertex-gemini-3.1-flash-lite` as the good development anchor.
- Require a large, obvious separation across several independent capability families.
- Preserve meaningful headroom for stronger future systems; neither development anchor may saturate.
- Scores should roughly track operational usefulness in a production document-processing pipeline.
- A careful human must be able to recover every scored obligation unambiguously from the source.
- Diagnostic guardrails are roughly 20–45 for GPT-5 Nano, 60–80 for Gemini 3.1 Flash-Lite, and a gap on the order of 30 points or more. These are release guardrails, not targets to manipulate.

## Development protocol

- During normal iteration, run only the two anchors above.
- Use exactly one stochastic sample per model/case.
- Do not report fake SD, ranges, reliability, or excessive decimal precision from one draw.
- Do not run GPT-5.4 Nano, GPT-5.4 Mini, Gemini 2.5, Gemini 3 Flash, premium models, or frontier sweeps during iteration.
- Use repeated runs only when intentionally checking variance.
- Diagnose substantive omissions, misbindings, hallucinations, state loss, visual failures, and long-context failures; do not tune to a one- or two-point stochastic movement.

## Construct coverage

The official suite must test all of the following:

1. Precise recall of text, numbers, dates, IDs, units, signs, qualifiers, and states.
2. Complete row, column, header, and value bindings in tables.
3. Borderless, nested, continued, grouped, and footnoted tables.
4. Long-context completeness across a realistically long, meaningful document.
5. Entity continuity and cross-references separated by many pages.
6. Chronology, cumulative state, totals, and dependencies across sections.
7. Reading order, hierarchy, captions, footnotes, annotations, and locality.
8. Checked, unchecked, disabled, corrected, struck-out, and superseded form states.
9. Source precedence between drafts, finals, corrections, redlines, and controlling records.
10. Chart axes, legends, thresholds, colors, labels, trends, and printed values.
11. Diagram, map, floorplan, network, and directed/spatial relationships.
12. Photo and technical-image evidence bound to the correct record.
13. Born-digital native text.
14. Full-page raster and scanned material.
15. Mixed native-text and raster regions in one document.
16. Low-quality but human-readable scans, skew, compression, stamps, and handwriting-like fields.
17. Legitimate malformed-export recovery using visible content and recoverable native text.
18. Explicit downstream-machine relationships even when the Markdown representation varies.

## Corpus rules

- Build one compact official suite. Case count and page count are not goals; unique construct signal is.
- Include a deliberate mixture of born-digital, full-raster, mixed-modality, and malformed-office material. The suite must be neither nearly all raster nor clean native text on every page.
- Include at least one genuinely long packet where later-page omission, entity drift, broken continuation, lost corrections, contradiction, summarization, and output pressure arise naturally.
- Every long-document page must add plausible, scored information; no filler.
- Important visual facts must not be redundantly restated in native text.
- Text extraction alone must be insufficient for important obligations.
- Page images alone must also be insufficient for at least one legitimate malformed/native-layer recovery challenge.
- Use credible organizational genres and page flows. Documents must look authored by competent organizations, not like AI dashboards or benchmark fixtures.
- Delete, merge, replace, or harden every current case explicitly. Retain a case only if it owns a unique capability.

## Scoring contract

- Correct and complete is best; missing is a failure; incorrect is worse than missing; proven unsupported content is worse still.
- Use source-audited, page-anchored obligations that are atomic enough to localize errors without manufacturing precision.
- Require candidate evidence for every credited obligation and prevent facts, gold, or source answers from becoming candidate evidence.
- Score meaningful table, form, diagram, image, and compound-record components while preventing easy table cells from drowning consequential state or visual relations.
- Penalize wrong values, bindings, directions, states, and precedence more than omission.
- Penalize unsupported content only when absence is established, and never double-charge one defect.
- Avoid global cap cliffs, crude length caps, verbosity rewards, and character-count proxies.
- Detect summarization with explicit coverage obligations.
- Assign region budgets by downstream harm and unique capability contribution.
- Keep signed evidence auditable; bound only the public case score.
- Aggregate deliberately and never weight by page count merely because a document is long.
- Validate with controlled reference, omission, substitution, misbinding, hallucination, and source-precedence counterfactuals, then human-review stratified judgments.

## Required workflow

1. Diagnose why every current case saturates.
2. Build primary and secondary capability coverage.
3. Audit text-only recoverability and visual redundancy.
4. Record keep, harden, merge, replace, or delete disposition for every case.
5. Design the smallest consolidated suite that covers the full construct.
6. Generate and render the entire corpus before paid calls.
7. Inspect every page at readable scale.
8. Audit every fact against the source and reference.
9. Run GPT-5 Nano once, then Gemini 3.1 Flash-Lite once.
10. Inspect complete outputs and judgments, not just aggregate scores.
11. Attribute the observed gap to specific cases and capabilities.
12. Iterate only when evidence reveals a genuine construct, corpus, or scorer defect.
13. Stop broadening when every retained case has a unique reason to exist.

## Release blockers

Do not call the benchmark ready if either anchor broadly saturates; Gemini is near-perfect on most cases; GPT-5 Nano is operationally competitive; separation is driven mainly by one case, cap, malformed artifact, or truncation; most score is clean-text-accessible; visual facts are textually restated; long-context reconstruction is not genuine; any obligation is ambiguous or disagrees with source/gold; the evaluator credits omitted content; small judge changes cause score cliffs; one-sample precision is overstated; cases or pages are redundant; or the report cannot explain capability-level separation.

## Required deliverables

- Implemented consolidated benchmark.
- Case disposition record and challenge/capability matrix.
- Source PDFs, references, and atomic facts.
- One-command model, evaluator, aggregation, and report flow.
- Current one-run results for both anchors.
- Per-case failure analysis and a causal explanation of the gap.
- Honest interpretation of one-draw uncertainty.

The objective is not to make GPT-5 Nano score low. A weak model should score low because it genuinely omits, misbinds, hallucinates, truncates, loses state, or fails visual and long-context reconstruction. A good model should score substantially higher because it solves more of those real problems. Neither should saturate.
