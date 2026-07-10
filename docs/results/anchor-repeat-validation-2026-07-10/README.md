# Anchor repeat-validation evidence

This directory preserves the evidence for the explicitly approved two-draw anchor variance check on 2026-07-10.

`draw-001.snapshot.json` was captured before any repeat inference. It embeds the exact official summaries, exact per-case scores, measured inference and evaluator spend, provider usage, cache identities, and SHA-256 hashes for every source prediction, result, score, and immutable attempt marker. The snapshot's only reported worktree difference is its own then-untracked `docs/results/` directory; its `sourceGitCommit` identifies the committed capture implementation and the benchmark under test.

The official benchmark remains a one-draw development protocol. The second observation is stored in a separately authorized validation slot and must not silently replace draw 1 or be presented as a statistically reliable variance estimate. With only two observations, the observed delta is useful as a sensitivity check, not as a stable estimate of the score distribution.
