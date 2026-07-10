# Anchor repeat-validation evidence

This directory preserves the evidence for the explicitly approved two-draw anchor variance check on 2026-07-10.

`draw-001.snapshot.json` was captured before any repeat inference. It embeds the exact official summaries, exact per-case scores, measured inference and evaluator spend, provider usage, cache identities, and SHA-256 hashes for every source prediction, result, score, and immutable attempt marker. The snapshot's only reported worktree difference is its own then-untracked `docs/results/` directory; its `sourceGitCommit` identifies the committed capture implementation and the benchmark under test.

The official benchmark remains a one-draw development protocol. The second observation is stored in a separately authorized validation slot and must not silently replace draw 1 or be presented as a statistically reliable variance estimate. With only two observations, the observed delta is useful as a sensitivity check, not as a stable estimate of the score distribution.

## Completed repeat checkpoint

The repeat checkpoint completed with 10 logical inference calls, 10 transport attempts, zero transport retries, 10 fresh valid evaluator judgments, and zero cached judgment reuse.

- GPT-5 Nano: 26.072883 to 28.152313 (+2.079430)
- Gemini 3.1 Flash-Lite: 55.883487 to 59.093465 (+3.209978)
- Anchor gap: 29.810604 to 30.941152 (+1.130547)
- Repeat spend: $0.094663 inference + $0.309230 evaluator = $0.403893
- Cumulative captured spend: $0.175520 inference + $0.612912 evaluator = $0.788431

Artifacts:

- `draw-001.snapshot.json`: pre-repeat preservation snapshot
- `draw-002.snapshot.json`: repeat preservation snapshot
- `analysis.json`: exact two-draw arithmetic and integrity audit
- `report.html`: human-readable technical report with per-value source tooltips
