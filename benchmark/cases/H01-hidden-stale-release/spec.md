# Hidden Stale Release Card

Purpose: Ensure rendered visible card wins over invisible stale text extraction.

Source modality: Visible content is a raster card. Conflicting stale values are invisible PDF text.

Expected gold objects:
- release fields
- status/owner/budget binding
- hidden stale text policy

Scoring checklist:
- Preserve visible status, owner, budget, reason, and stamp.
- Penalize hidden APPROVED/Mira/$19,400 values.

Family: `visibility`

Tags: `hidden-text`, `raster-card`, `negative-check`
