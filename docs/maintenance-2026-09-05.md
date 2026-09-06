# Offline maintenance — 2026-09-05

The corpus and useful results are retained. Difficulty and score spread are no longer reasons to regenerate the PDFs. The comparison is a synthetic document stress test, with selected obligations and an informal single-run leaderboard.

Implemented changes:

- `npm run report` rebuilds cached results without conversion/evaluator calls. Paid runs require explicit candidates, can select cases, and support an offline `--dry-run` preview.
- Manual decisions live beside each saved prediction in `corrections.json`, apply after automatic rules, and are bound to the prediction hash. All 96 existing score records containing historical manual corrections were copied into this form using their saved final statuses and evidence; they were not rejudged.
- Automatic extra-member accusations require explicit human approval to incur a penalty. The separate paid audit was removed. Exact structured precredits and semantic batch checkpoints remain.
- Table matching no longer treats a cross-reference in another column as the target row when an explicit primary-column row identifies it.
- Page-parallel conversion checkpoints successful pages and retains stable split PDFs. A failed sibling does not discard successful responses.
- Report labels now describe fidelity and summed case conversion latency. Unsupported precise downstream-saving percentages were removed. Gold no longer adds PFAS recovery calculations absent from the PDF; its generator was synchronized without regenerating any PDF or changing facts.

The following saved scores were corrected by direct source/output review, using arithmetic only:

| Candidate / case | Before | After | Reason |
| --- | ---: | ---: | --- |
| GPT-5.4 / Task 5 | 81.81 | 83.15 | E-05 correctly preserved closure evidence and CLOSED; EX-07's reference to E-05 was mistaken for a conflicting E-05 row. Corrected two leaves using candidate lines 182/184. |
| Docling / Task 2 | 19.19 | 19.99 | Source subtitle was falsely charged as an invented checkbox option. |
| GPT-4.1 Nano / Task 2 | 22.24 | 23.04 | Source record ID EC-214-19 was falsely charged as an invented checkbox option. |
| Docling / Task 4 | 73.38 | 73.60 | EO replacing E0 is a transcription substitution, not an extra legend member. |
| Unstructured VLM / Task 3 | 92.01 | 92.51 | Two existing rows contained substituted identifiers, not additional rows. |

The last four corrections remove five extra-member penalties. Their ordinary transcription, missing, and incorrect-binding grades were preserved. PDFs, fact files, saved candidate Markdown, inference metadata, and unrelated saved score files were not changed. Existing completed score/checkpoint identities remain compatible; no paid regrade or conversion was performed.

The override files and score caches are local artifacts under the repository's existing ignored `runs/` directory. Keep them together when moving the cache. The tracked aggregate result is refreshed from these corrected scores.
