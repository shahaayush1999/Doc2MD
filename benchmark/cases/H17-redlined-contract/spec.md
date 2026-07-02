# Redlined Data Processing Addendum

Purpose: Recover current contract text while preserving redline semantics and margin comments.

Source modality: Raster-only contract excerpt with insertions, deletions, and side comments.

Expected gold objects:
- current clause text
- deleted text marked deleted
- inserted text current
- margin comments
- signature block

Scoring checklist:
- Do not treat deleted 30 calendar days as current.
- Preserve 10 business days and 400 days.
- Keep comments as comments.

Family: `layout`

Tags: `raster-only`, `redline`, `contract`, `margin-comments`, `deleted-text`
